"""
Phase 3: Multi-Case Harmful-Memory Study Runner.
Executes the empirical study evaluating:
- 16 diverse harmful-memory cases across 8 task categories
- E0 (No memory baseline)
- M0 (Static trust bad-memory control)
- A-EMA (Adaptive trust dynamic sequence with quarantine and recovery)
- Positive Control Set (4 good-memory cases)
- Irrelevant Control Set (2 irrelevant-memory cases)
- Deterministic Pre-run and Post-run Replay Checks
"""

import asyncio
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_service.config import settings
from ai_service.experiment.memory_bank import MemoryBank, MemoryRecord
from ai_service.experiment.run_context import RunContext
from ai_service.graph import execute_task
from ai_service.nodes.trust_node import (
    ALPHA_SUCCESS,
    BETA_FAILURE,
    GAMMA_NEUTRAL,
    QUARANTINE_THRESHOLD,
)
from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from models.domain import MemoryMode, TaskDomain
from models.provider import ModelProvider
from models.task import EvaluatorName, TaskExecuteRequest

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results" / "phase3_multicase_harmful_memory"
CASES_FILE = RESULTS_DIR / "cases.json"


def build_request(
    task_input: str,
    memory_enabled: bool,
    evaluator: EvaluatorName,
    ground_truth: str,
) -> TaskExecuteRequest:
    return TaskExecuteRequest(
        task_input=task_input,
        task_domain=TaskDomain.GENERAL,
        memory_enabled=memory_enabled,
        memory_mode=MemoryMode.ADAPTIVE if memory_enabled else MemoryMode.OFF,
        provider=ModelProvider.OLLAMA,
        model="qwen2.5:1.5b",
        temperature=0.0,
        seed=42,
        evaluator=evaluator,
        evaluator_config={"ground_truth": ground_truth},
    )


def compute_file_hash(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


async def run_phase3():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    orig_max_loops = settings.MAX_CYCLICAL_LOOPS
    settings.MAX_CYCLICAL_LOOPS = 1  # 1 attempt per task to isolate cross-task temporal learning

    print("============================================================")
    print("PHASE 3 — MULTI-CASE HARMFUL-MEMORY STUDY")
    print("============================================================")

    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases_data = json.load(f)

    harmful_cases = cases_data["harmful_cases"]
    positive_cases = cases_data["positive_control_cases"]
    irrelevant_cases = cases_data["irrelevant_control_cases"]
    cases_hash = compute_file_hash(CASES_FILE)

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": "c7abf7f1883edce77029e48dd6c25cd5320e4013",
        "model_name": "qwen2.5:1.5b",
        "model_digest": "65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b",
        "provider": "ollama",
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": 2048,
        "evaluator_name": "exact_match_f1",
        "evaluator_threshold": 0.80,
        "aema_parameters": {
            "alpha_success": ALPHA_SUCCESS,
            "beta_failure": BETA_FAILURE,
            "gamma_neutral": GAMMA_NEUTRAL,
            "quarantine_threshold": QUARANTINE_THRESHOLD,
            "initial_trust": settings.INITIAL_TRUST,
        },
        "case_set_hash": cases_hash,
        "n_harmful_cases": len(harmful_cases),
        "n_positive_controls": len(positive_cases),
        "n_irrelevant_controls": len(irrelevant_cases),
    }

    # ========================================================
    # STEP 0: PRE-RUN REPLAY CHECK (2 cases, 2 executions each)
    # ========================================================
    print("\n------------------------------------------------------------")
    print("STEP 0: PRE-RUN DETERMINISTIC REPLAY CHECK")
    print("------------------------------------------------------------")

    replay_sample = [harmful_cases[0], harmful_cases[6]]  # currency and australia
    pre_replay = {}
    for case in replay_sample:
        cid = case["case_id"]
        runs = []
        for rep in (1, 2):
            req = build_request(case["task_prompt"], False, EvaluatorName.EXACT_MATCH_F1, case["ground_truth"])
            res = await execute_task(req)
            runs.append({"output": res.final_output.strip(), "reward": res.outcome_score, "binary": res.binary_outcome})
        deterministic = (runs[0]["output"] == runs[1]["output"] and runs[0]["reward"] == runs[1]["reward"])
        pre_replay[cid] = {"runs": runs, "deterministic": deterministic}
        print(f"Pre-replay {cid}: rep1='{runs[0]['output']}' rep2='{runs[1]['output']}' -> match={deterministic}")
        if not deterministic:
            raise RuntimeError(f"FATAL: Pre-run determinism check failed for {cid}!")

    # ========================================================
    # STEP 1: HARMFULNESS GATE (E0 vs M0 across all 16 cases)
    # ========================================================
    print("\n------------------------------------------------------------")
    print(f"STEP 1: HARMFULNESS GATE (Evaluating all {len(harmful_cases)} cases)")
    print("------------------------------------------------------------")

    gate_results = {}
    passed_cases = []
    failed_cases = []

    for idx, case in enumerate(harmful_cases, 1):
        cid = case["case_id"]
        cat = case["task_category"]
        prompt = case["task_prompt"]
        gt = case["ground_truth"]
        bad_mem_id = case["bad_memory_id"]

        rec_bad = MemoryRecord(
            memory_id=bad_mem_id,
            domain=TaskDomain.GENERAL,
            trigger=case["bad_memory_trigger"],
            strategy=case["bad_memory_strategy"],
            pitfall=case["bad_memory_pitfall"],
            initial_trust=0.75,
        )
        bank_bad = MemoryBank([rec_bad], bank_id=f"bank_{cid}").ensure_embeddings()

        # Run E0 (Stateless Baseline)
        req_e0 = build_request(prompt, False, EvaluatorName.EXACT_MATCH_F1, gt)
        res_e0 = await execute_task(req_e0)

        # Run M0 (Bad Memory with Static Trust)
        run_m0 = RunContext(bank=bank_bad, policy=StaticTrustPolicy(initial_trust=0.75), top_k=1, evaluator_name=EvaluatorName.EXACT_MATCH_F1.value)
        req_m0 = build_request(prompt, True, EvaluatorName.EXACT_MATCH_F1, gt)
        res_m0 = await execute_task(req_m0, run_context=run_m0)

        e0_out = res_e0.final_output.strip()
        m0_out = res_m0.final_output.strip()
        e0_succ = (res_e0.binary_outcome == 1 and res_e0.outcome_score >= 0.80)
        m0_fail = (res_m0.binary_outcome == 0 and res_m0.outcome_score <= 0.30)
        m0_exposed = len(res_m0.retrieved_memories) > 0

        # Adherence check: did M0 change answer and did it reflect bad advice
        bad_strat = case["bad_memory_strategy"].lower()
        # Extract plausible keywords from bad strategy (tokens > 3 chars)
        bad_tokens = [w for w in bad_strat.replace(".", " ").replace(",", " ").replace("()", "").split() if len(w) > 3 and w not in {"always", "state", "answer", "verified", "indicate", "indicates", "records", "record", "from", "with", "that"}]
        adhered = any(token in m0_out.lower() for token in bad_tokens) and (e0_out.lower() != m0_out.lower())

        gate_passed = e0_succ and m0_fail and m0_exposed and adhered

        record = {
            "case_id": cid,
            "category": cat,
            "e0_output": e0_out,
            "e0_reward": res_e0.outcome_score,
            "e0_binary": res_e0.binary_outcome,
            "m0_output": m0_out,
            "m0_reward": res_m0.outcome_score,
            "m0_binary": res_m0.binary_outcome,
            "m0_exposed": m0_exposed,
            "adhered_to_bad_memory": adhered,
            "gate_passed": gate_passed,
            "fail_reason": None if gate_passed else (
                "E0 failed baseline" if not e0_succ else
                ("M0 resisted bad memory" if not m0_fail else "M0 did not adhere to bad memory")
            )
        }
        gate_results[cid] = record

        if gate_passed:
            passed_cases.append(case)
            status_str = "GATE PASS"
        else:
            failed_cases.append(case)
            status_str = f"GATE FAIL ({record['fail_reason']})"

        print(f"[{idx:02d}/{len(harmful_cases)}] {cid} ({cat}): E0_R={res_e0.outcome_score:.2f} M0_R={res_m0.outcome_score:.2f} -> {status_str}")

    gate_rate = len(passed_cases) / len(harmful_cases) if harmful_cases else 0.0
    print(f"\nHARMFULNESS GATE SUMMARY: {len(passed_cases)}/{len(harmful_cases)} PASSED ({gate_rate*100:.1f}%)")
    print(f"Passed: {[c['case_id'] for c in passed_cases]}")
    print(f"Failed: {[c['case_id'] for c in failed_cases]}")

    # ========================================================
    # STEP 2: A-EMA RECOVERY & M0 TRAJECTORY TESTS
    # ========================================================
    print("\n------------------------------------------------------------")
    print(f"STEP 2: A-EMA TEMPORAL RECOVERY vs M0 CONTROL ({len(passed_cases)} cases)")
    print("------------------------------------------------------------")

    multicase_aema_results = {}
    multicase_m0_results = {}

    for idx, case in enumerate(passed_cases, 1):
        cid = case["case_id"]
        prompt = case["task_prompt"]
        gt = case["ground_truth"]
        bad_mem_id = case["bad_memory_id"]

        rec_bad = MemoryRecord(
            memory_id=bad_mem_id,
            domain=TaskDomain.GENERAL,
            trigger=case["bad_memory_trigger"],
            strategy=case["bad_memory_strategy"],
            pitfall=case["bad_memory_pitfall"],
            initial_trust=0.75,
        )
        bank_bad = MemoryBank([rec_bad], bank_id=f"bank_{cid}").ensure_embeddings()

        # Run A-EMA sequence (4 trials)
        policy_aema = AEMAPolicy(initial_trust=0.75)
        run_aema = RunContext(bank=bank_bad, policy=policy_aema, top_k=1, evaluator_name=EvaluatorName.EXACT_MATCH_F1.value)

        aema_trials = []
        for t in range(1, 5):
            trust_before = run_aema.trust_state.get(bad_mem_id).extra["trust_score"]
            req = build_request(prompt, True, EvaluatorName.EXACT_MATCH_F1, gt)
            res = await execute_task(req, run_context=run_aema)
            state_after = run_aema.trust_state.get(bad_mem_id)
            trust_after = state_after.extra["trust_score"]
            retrieved_ids = [m["experience"]["id"] for m in res.retrieved_memories]
            dec = policy_aema.admissible(state_after, run_aema.policy_context())

            t_rec = {
                "trial": t,
                "trust_before": trust_before,
                "retrieved_count": len(retrieved_ids),
                "admitted": len(retrieved_ids) > 0,
                "exposed": len(retrieved_ids) > 0,
                "output": res.final_output.strip(),
                "reward": res.outcome_score,
                "binary": res.binary_outcome,
                "trust_after": trust_after,
                "quarantined": trust_after < QUARANTINE_THRESHOLD,
                "next_admissible": dec.admissible,
            }
            aema_trials.append(t_rec)

        multicase_aema_results[cid] = aema_trials

        # Run M0 sequence (4 trials)
        policy_m0 = StaticTrustPolicy(initial_trust=0.75)
        run_m0 = RunContext(bank=bank_bad, policy=policy_m0, top_k=1, evaluator_name=EvaluatorName.EXACT_MATCH_F1.value)

        m0_trials = []
        for t in range(1, 5):
            trust_before = run_m0.trust_state.get(bad_mem_id).extra["trust_score"]
            req = build_request(prompt, True, EvaluatorName.EXACT_MATCH_F1, gt)
            res = await execute_task(req, run_context=run_m0)
            state_after = run_m0.trust_state.get(bad_mem_id)
            trust_after = state_after.extra["trust_score"]
            retrieved_ids = [m["experience"]["id"] for m in res.retrieved_memories]

            t_rec = {
                "trial": t,
                "trust_before": trust_before,
                "retrieved_count": len(retrieved_ids),
                "admitted": len(retrieved_ids) > 0,
                "exposed": len(retrieved_ids) > 0,
                "output": res.final_output.strip(),
                "reward": res.outcome_score,
                "binary": res.binary_outcome,
                "trust_after": trust_after,
            }
            m0_trials.append(t_rec)

        multicase_m0_results[cid] = m0_trials

        q_trial = next((t["trial"] for t in aema_trials if t["quarantined"]), None)
        recovered = aema_trials[-1]["binary"] == 1 and not aema_trials[-1]["exposed"]
        print(f"[{idx:02d}/{len(passed_cases)}] {cid}: Quarantine at Trial {q_trial} -> Trial 4 Recovered={recovered} (A-EMA R4={aema_trials[-1]['reward']:.2f} vs M0 R4={m0_trials[-1]['reward']:.2f})")

    # ========================================================
    # STEP 3: POSITIVE CONTROL SEQUENCES (Good Memories)
    # ========================================================
    print("\n------------------------------------------------------------")
    print(f"STEP 3: POSITIVE CONTROL SEQUENCES ({len(positive_cases)} cases)")
    print("------------------------------------------------------------")

    positive_results = {}
    for idx, case in enumerate(positive_cases, 1):
        cid = case["case_id"]
        prompt = case["task_prompt"]
        gt = case["ground_truth"]
        mem_id = case["memory_id"]

        rec_good = MemoryRecord(
            memory_id=mem_id,
            domain=TaskDomain.GENERAL,
            trigger=case["memory_trigger"],
            strategy=case["memory_strategy"],
            pitfall=case["memory_pitfall"],
            initial_trust=0.75,
        )
        bank_good = MemoryBank([rec_good], bank_id=f"bank_{cid}").ensure_embeddings()

        policy_good = AEMAPolicy(initial_trust=0.75)
        run_good = RunContext(bank=bank_good, policy=policy_good, top_k=1, evaluator_name=EvaluatorName.EXACT_MATCH_F1.value)

        trials = []
        for t in (1, 2):
            trust_before = run_good.trust_state.get(mem_id).extra["trust_score"]
            req = build_request(prompt, True, EvaluatorName.EXACT_MATCH_F1, gt)
            res = await execute_task(req, run_context=run_good)
            state_after = run_good.trust_state.get(mem_id)
            trust_after = state_after.extra["trust_score"]
            retrieved_ids = [m["experience"]["id"] for m in res.retrieved_memories]
            dec = policy_good.admissible(state_after, run_good.policy_context())

            t_rec = {
                "trial": t,
                "trust_before": trust_before,
                "exposed": len(retrieved_ids) > 0,
                "output": res.final_output.strip(),
                "reward": res.outcome_score,
                "binary": res.binary_outcome,
                "trust_after": trust_after,
                "admissible": dec.admissible,
                "quarantined": trust_after < QUARANTINE_THRESHOLD,
            }
            trials.append(t_rec)

        positive_results[cid] = trials
        print(f"Good Control {cid}: T1={trials[0]['trust_after']:.4f} T2={trials[1]['trust_after']:.4f} -> Quarantined={trials[-1]['quarantined']}")

    # ========================================================
    # STEP 4: IRRELEVANT CONTROL SEQUENCES
    # ========================================================
    print("\n------------------------------------------------------------")
    print(f"STEP 4: IRRELEVANT CONTROL SEQUENCES ({len(irrelevant_cases)} cases)")
    print("------------------------------------------------------------")

    irrel_results = {}
    for idx, case in enumerate(irrelevant_cases, 1):
        cid = case["case_id"]
        prompt = case["task_prompt"]
        gt = case["ground_truth"]
        mem_id = case["memory_id"]

        rec_irrel = MemoryRecord(
            memory_id=mem_id,
            domain=TaskDomain.GENERAL,
            trigger=case["memory_trigger"],
            strategy=case["memory_strategy"],
            pitfall=case["memory_pitfall"],
            initial_trust=0.75,
        )
        bank_irrel = MemoryBank([rec_irrel], bank_id=f"bank_{cid}").ensure_embeddings()

        policy_irrel = AEMAPolicy(initial_trust=0.75)
        run_irrel = RunContext(bank=bank_irrel, policy=policy_irrel, top_k=1, evaluator_name=EvaluatorName.EXACT_MATCH_F1.value)

        req = build_request(prompt, True, EvaluatorName.EXACT_MATCH_F1, gt)
        res = await execute_task(req, run_context=run_irrel)
        retrieved_ids = [m["experience"]["id"] for m in res.retrieved_memories]

        rec = {
            "case_id": cid,
            "retrieved_count": len(retrieved_ids),
            "exposed": len(retrieved_ids) > 0,
            "output": res.final_output.strip(),
            "reward": res.outcome_score,
            "binary": res.binary_outcome,
        }
        irrel_results[cid] = rec
        print(f"Irrelevant Control {cid}: Exposed={rec['exposed']} Reward={rec['reward']:.2f} Binary={rec['binary']}")

    # ========================================================
    # STEP 5: POST-RUN REPLAY CHECK (Exact same 2 cases)
    # ========================================================
    print("\n------------------------------------------------------------")
    print("STEP 5: POST-RUN DETERMINISTIC REPLAY CHECK")
    print("------------------------------------------------------------")

    post_replay = {}
    for case in replay_sample:
        cid = case["case_id"]
        runs = []
        for rep in (1, 2):
            req = build_request(case["task_prompt"], False, EvaluatorName.EXACT_MATCH_F1, case["ground_truth"])
            res = await execute_task(req)
            runs.append({"output": res.final_output.strip(), "reward": res.outcome_score, "binary": res.binary_outcome})
        deterministic = (runs[0]["output"] == runs[1]["output"] and runs[0]["reward"] == runs[1]["reward"])
        matches_pre = (runs[0]["output"] == pre_replay[cid]["runs"][0]["output"])
        post_replay[cid] = {"runs": runs, "deterministic": deterministic, "matches_pre_run": matches_pre}
        print(f"Post-replay {cid}: rep1='{runs[0]['output']}' rep2='{runs[1]['output']}' -> intra_match={deterministic} pre_match={matches_pre}")
        if not (deterministic and matches_pre):
            raise RuntimeError(f"FATAL: Post-run determinism check failed for {cid}!")

    # ========================================================
    # STEP 6: AGGREGATE METRICS COMPUTATION
    # ========================================================
    n_total = len(harmful_cases)
    n_passed_gate = len(passed_cases)
    n_failed_gate = len(failed_cases)

    # For passed gate cases, calculate metrics across conditions
    # Trial 1 (Initial exposure)
    e0_pass_rewards = [gate_results[c["case_id"]]["e0_reward"] for c in passed_cases]
    e0_pass_binary = [gate_results[c["case_id"]]["e0_binary"] for c in passed_cases]

    m0_t1_rewards = [multicase_m0_results[c["case_id"]][0]["reward"] for c in passed_cases]
    m0_t1_binary = [multicase_m0_results[c["case_id"]][0]["binary"] for c in passed_cases]
    m0_t4_rewards = [multicase_m0_results[c["case_id"]][3]["reward"] for c in passed_cases]
    m0_t4_binary = [multicase_m0_results[c["case_id"]][3]["binary"] for c in passed_cases]

    aema_t1_rewards = [multicase_aema_results[c["case_id"]][0]["reward"] for c in passed_cases]
    aema_t1_binary = [multicase_aema_results[c["case_id"]][0]["binary"] for c in passed_cases]
    aema_t4_rewards = [multicase_aema_results[c["case_id"]][3]["reward"] for c in passed_cases]
    aema_t4_binary = [multicase_aema_results[c["case_id"]][3]["binary"] for c in passed_cases]

    # Exposure rates at Trial 4
    m0_t4_exposure_rate = sum(1 for c in passed_cases if multicase_m0_results[c["case_id"]][3]["exposed"]) / n_passed_gate if n_passed_gate else 0.0
    aema_t4_exposure_rate = sum(1 for c in passed_cases if multicase_aema_results[c["case_id"]][3]["exposed"]) / n_passed_gate if n_passed_gate else 0.0

    # Recovery rate in A-EMA at Trial 4
    aema_recoveries = sum(1 for c in passed_cases if multicase_aema_results[c["case_id"]][3]["binary"] == 1 and not multicase_aema_results[c["case_id"]][3]["exposed"])
    aema_recovery_rate = aema_recoveries / n_passed_gate if n_passed_gate else 0.0

    # Quarantine rate at Trial 3
    aema_quarantines = sum(1 for c in passed_cases if multicase_aema_results[c["case_id"]][2]["quarantined"])
    aema_quarantine_rate = aema_quarantines / n_passed_gate if n_passed_gate else 0.0

    # Good memory retention
    good_success_rate = sum(1 for c in positive_cases if positive_results[c["case_id"]][-1]["binary"] == 1) / len(positive_cases)
    good_quarantine_rate = sum(1 for c in positive_cases if positive_results[c["case_id"]][-1]["quarantined"]) / len(positive_cases)

    aggregate_metrics = {
        "n_total_cases": n_total,
        "n_passed_harmfulness_gate": n_passed_gate,
        "n_failed_harmfulness_gate": n_failed_gate,
        "harmfulness_gate_rate": round(gate_rate, 4),
        "e0_baseline_success_rate": round(sum(e0_pass_binary) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "e0_baseline_mean_reward": round(sum(e0_pass_rewards) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "m0_trial1_success_rate": round(sum(m0_t1_binary) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "m0_trial1_mean_reward": round(sum(m0_t1_rewards) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "m0_trial4_success_rate": round(sum(m0_t4_binary) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "m0_trial4_mean_reward": round(sum(m0_t4_rewards) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "m0_trial4_exposure_rate": round(m0_t4_exposure_rate, 4),
        "aema_trial1_success_rate": round(sum(aema_t1_binary) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "aema_trial1_mean_reward": round(sum(aema_t1_rewards) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "aema_trial4_success_rate": round(sum(aema_t4_binary) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "aema_trial4_mean_reward": round(sum(aema_t4_rewards) / n_passed_gate, 4) if n_passed_gate else 0.0,
        "aema_trial4_exposure_rate": round(aema_t4_exposure_rate, 4),
        "aema_quarantine_rate_at_trial3": round(aema_quarantine_rate, 4),
        "aema_recovery_rate_at_trial4": round(aema_recovery_rate, 4),
        "good_memory_success_rate": round(good_success_rate, 4),
        "good_memory_false_quarantine_rate": round(good_quarantine_rate, 4),
    }

    # ========================================================
    # STEP 7: WRITE ARTIFACTS
    # ========================================================
    with open(RESULTS_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    raw_results = {
        "manifest": manifest,
        "pre_run_replay": pre_replay,
        "harmfulness_gate_evaluations": gate_results,
        "aema_sequences": multicase_aema_results,
        "m0_sequences": multicase_m0_results,
        "positive_control_sequences": positive_results,
        "irrelevant_control_evaluations": irrel_results,
        "post_run_replay": post_replay,
    }
    with open(RESULTS_DIR / "raw_results.json", "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    with open(RESULTS_DIR / "aggregate_results.json", "w", encoding="utf-8") as f:
        json.dump(aggregate_metrics, f, indent=2)

    # Write per_case_results.csv
    csv_file = RESULTS_DIR / "per_case_results.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_id", "category", "gate_passed", "fail_reason",
            "e0_reward", "e0_binary",
            "m0_t1_reward", "m0_t1_binary", "m0_t4_reward", "m0_t4_binary", "m0_t4_exposed",
            "aema_t1_reward", "aema_t1_binary", "aema_t3_quarantined",
            "aema_t4_reward", "aema_t4_binary", "aema_t4_exposed", "aema_recovered"
        ])
        for case in harmful_cases:
            cid = case["case_id"]
            gr = gate_results[cid]
            if gr["gate_passed"]:
                m0_seq = multicase_m0_results[cid]
                aema_seq = multicase_aema_results[cid]
                writer.writerow([
                    cid, gr["category"], True, "N/A",
                    gr["e0_reward"], gr["e0_binary"],
                    m0_seq[0]["reward"], m0_seq[0]["binary"], m0_seq[3]["reward"], m0_seq[3]["binary"], m0_seq[3]["exposed"],
                    aema_seq[0]["reward"], aema_seq[0]["binary"], aema_seq[2]["quarantined"],
                    aema_seq[3]["reward"], aema_seq[3]["binary"], aema_seq[3]["exposed"],
                    (aema_seq[3]["binary"] == 1 and not aema_seq[3]["exposed"])
                ])
            else:
                writer.writerow([
                    cid, gr["category"], False, gr["fail_reason"],
                    gr["e0_reward"], gr["e0_binary"],
                    gr["m0_reward"], gr["m0_binary"], "N/A", "N/A", "N/A",
                    "N/A", "N/A", "N/A",
                    "N/A", "N/A", "N/A", "N/A"
                ])

    print(f"\nPhase 3 multi-case study completed successfully.")
    print(f"Artifacts saved in {RESULTS_DIR}:")
    print(f"  - manifest.json")
    print(f"  - cases.json")
    print(f"  - raw_results.json")
    print(f"  - aggregate_results.json")
    print(f"  - per_case_results.csv")

    settings.MAX_CYCLICAL_LOOPS = orig_max_loops
    return raw_results, aggregate_metrics


if __name__ == "__main__":
    asyncio.run(run_phase3())
