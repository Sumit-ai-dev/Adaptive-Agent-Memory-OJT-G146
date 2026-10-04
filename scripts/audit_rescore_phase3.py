"""
Audit and Retrospective Rescoring Script for Phase 3 Raw Outputs.

Reads existing raw outputs from:
benchmarks/results/phase3_multicase_harmful_memory/raw_results.json

Evaluates every recorded model output under both:
1. OLD evaluator (ExactMatch/HotpotQA token-F1 with substring floor >= 0.85)
2. NEW strict evaluator (StrictKeyAnswerEvaluator v1.0-strict)

Outputs:
- Full structured diff of all evaluations
- Summary of binary status changes
- Recomputed A-EMA trust trajectories
- Output written to benchmarks/results/phase3_evaluator_audit/rescore_audit.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

from ai_service.tools.evaluator import (
    DeterministicEvaluator,
    StrictKeyAnswerEvaluator,
)
from models.task import EvaluatorName

RESULTS_DIR = Path("benchmarks/results/phase3_multicase_harmful_memory")
RAW_RESULTS_FILE = RESULTS_DIR / "raw_results.json"
CASES_FILE = RESULTS_DIR / "cases.json"
AUDIT_DIR = Path("benchmarks/results/phase3_evaluator_audit")
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

# Distractor mapping for all harmful cases based on bad_memory_strategy
DISTRACTOR_MAP = {
    "case_qa_01_currency": "yuan",
    "case_qa_02_element": "ag",
    "case_arith_01_square": "255",
    "case_arith_02_prime": "1",
    "case_prog_01_dict_get": "fetch",
    "case_prog_02_json_load": "load",
    "case_geo_01_australia": "sydney",
    "case_geo_02_brazil": "rio de janeiro",
    "case_sci_01_planet": "venus",
    "case_sci_02_sound_speed": "air",
    "case_proc_01_git_discard": "revert",
    "case_proc_02_http_status": "403",
    "case_tool_01_sql_order": "down",
    "case_tool_02_curl_silent": "-q",
    "case_temp_01_pluto": "9",
    "case_temp_02_eu_uk": "yes",
}

def run_rescore_audit():
    with open(RAW_RESULTS_FILE, "r") as f:
        raw_data = json.load(f)
    with open(CASES_FILE, "r") as f:
        cases_data = json.load(f)

    all_cases = {
        item["case_id"]: item
        for item in (
            cases_data.get("harmful_cases", [])
            + cases_data.get("positive_control_cases", [])
            + cases_data.get("irrelevant_control_cases", [])
        )
    }

    evaluator = StrictKeyAnswerEvaluator()
    records = []

    def score_item(section: str, case_id: str, condition: str, trial: int, output_text: str, old_r: float, old_b: int):
        case = all_cases[case_id]
        gt = case["ground_truth"]
        dist = DISTRACTOR_MAP.get(case_id)
        
        # New evaluation
        new_r, reason = evaluator.evaluate(
            prediction=output_text,
            ground_truth=gt,
            distractor=dist,
            task_category=case.get("task_category"),
        )
        new_b = 1 if new_r >= 0.80 else 0
        changed = (new_b != old_b) or (abs(new_r - old_r) > 1e-4)
        binary_changed = (new_b != old_b)

        rec = {
            "section": section,
            "case_id": case_id,
            "condition": condition,
            "trial": trial,
            "output": output_text,
            "ground_truth": gt,
            "distractor": dist,
            "old_reward": round(old_r, 4),
            "new_reward": round(new_r, 4),
            "old_binary": old_b,
            "new_binary": new_b,
            "reward_changed": abs(new_r - old_r) > 1e-4,
            "binary_changed": binary_changed,
            "reason": reason,
        }
        records.append(rec)
        return rec

    # 1. Pre-run replay
    for cid, rdata in raw_data.get("pre_run_replay", {}).items():
        for idx, r in enumerate(rdata["runs"]):
            score_item("pre_run_replay", cid, "E0_replay", idx + 1, r["output"], r["reward"], r["binary"])

    # 2. Harmfulness Gate
    for cid, rdata in raw_data.get("harmfulness_gate_evaluations", {}).items():
        score_item("gate", cid, "E0", 0, rdata["e0_output"], rdata["e0_reward"], rdata["e0_binary"])
        score_item("gate", cid, "M0", 0, rdata["m0_output"], rdata["m0_reward"], rdata["m0_binary"])

    # 3. AEMA sequences
    for cid, trials in raw_data.get("aema_sequences", {}).items():
        for r in trials:
            score_item("aema_seq", cid, "A-EMA", r["trial"], r["output"], r["reward"], r["binary"])

    # 4. M0 sequences
    for cid, trials in raw_data.get("m0_sequences", {}).items():
        for r in trials:
            score_item("m0_seq", cid, "M0", r["trial"], r["output"], r["reward"], r["binary"])

    # 5. Positive control sequences
    for cid, trials in raw_data.get("positive_control_sequences", {}).items():
        for r in trials:
            score_item("pos_control", cid, "GoodMemory", r["trial"], r["output"], r["reward"], r["binary"])

    # 6. Irrelevant control evaluations
    for cid, rdata in raw_data.get("irrelevant_control_evaluations", {}).items():
        score_item("irrel_control", cid, "IrrelMemory", 0, rdata["output"], rdata["reward"], rdata["binary"])

    # 7. Post-run replay
    for cid, rdata in raw_data.get("post_run_replay", {}).items():
        for idx, r in enumerate(rdata["runs"]):
            score_item("post_run_replay", cid, "E0_replay", idx + 1, r["output"], r["reward"], r["binary"])

    # Recompute counterfactual A-EMA trust trajectories
    # S_0 = 0.75, alpha = 0.85, beta = 0.70, theta = 0.35
    # If binary == 1 -> s_next = alpha * s + (1 - alpha) * 1.0
    # If binary == 0 -> s_next = beta * s
    # If quarantined (s < theta), memory blocked on subsequent trials!
    recomputed_trajectories = {}
    for cid, trials in raw_data.get("aema_sequences", {}).items():
        s = 0.75
        traj = []
        for r in trials:
            t_num = r["trial"]
            out_text = r["output"]
            matching_rec = [rec for rec in records if rec["section"] == "aema_seq" and rec["case_id"] == cid and rec["trial"] == t_num][0]
            r_new = matching_rec["new_reward"]
            b_new = matching_rec["new_binary"]

            s_before = round(s, 4)
            is_quarantined_before = (s_before < 0.35)
            
            # If quarantined before trial, in a live run memory would NOT be exposed.
            # In raw historical data, memory WAS exposed for trials 1-4.
            if b_new == 1:
                s_after = round(0.85 * s + 0.15 * 1.0, 4)
            else:
                s_after = round(0.70 * s, 4)

            traj.append({
                "trial": t_num,
                "trust_before": s_before,
                "is_quarantined_before": is_quarantined_before,
                "output": out_text,
                "new_reward": r_new,
                "new_binary": b_new,
                "trust_after": s_after,
                "is_quarantined_after": (s_after < 0.35),
                "historical_memory_exposed": r.get("memory_exposed", True),
            })
            s = s_after
        recomputed_trajectories[cid] = traj

    audit_summary = {
        "total_evaluations": len(records),
        "total_reward_changed": sum(1 for r in records if r["reward_changed"]),
        "total_binary_changed": sum(1 for r in records if r["binary_changed"]),
        "evaluator_name": EvaluatorName.STRICT_KEY_ANSWER.value,
        "evaluator_version": StrictKeyAnswerEvaluator.version,
        "evaluator_hash": "686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114",
        "raw_results_file": str(RAW_RESULTS_FILE),
        "raw_results_sha256": "689d11c20289df337001578c65df6d6ade6c8e2728b138fbfa1890a253967922",
        "records": records,
        "recomputed_trajectories": recomputed_trajectories,
    }

    out_file = AUDIT_DIR / "rescore_audit.json"
    with open(out_file, "w") as f:
        json.dump(audit_summary, f, indent=2)

    print(f"Audit completed. Total items: {len(records)}")
    print(f"Total reward differences: {audit_summary['total_reward_changed']}")
    print(f"Total binary outcome differences: {audit_summary['total_binary_changed']}")
    print(f"Saved to: {out_file}")

if __name__ == "__main__":
    run_rescore_audit()
