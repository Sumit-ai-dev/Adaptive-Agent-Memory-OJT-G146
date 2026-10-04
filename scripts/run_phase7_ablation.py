"""
Phase 7 Ablation Studies Runner: Mechanism Isolation Experiment.

Investigates which A-EMA mechanisms are responsible for the observed recovery:
1. A0: Full A-EMA (alpha=0.85, beta=0.70, theta=0.35, quarantine enabled)
2. A1: A-EMA without quarantine (alpha=0.85, beta=0.70, admissibility gate disabled: memory always exposed)
3. A2: Symmetric trust update (alpha=0.85, beta=0.85, theta=0.35, quarantine enabled)
4. A3 / M0: Static Memory baseline (StaticTrustPolicy, S=0.75, no decay, no quarantine)
5. E0: Stateless baseline (no memory injected)

Evaluates the 6 frozen Primary Harmful-Memory Cases from Group 1 of Phase 6:
- case_tool_01_sql_order
- case_tool_02_curl_silent
- case_geo_01_australia
- case_qa_01_currency
- case_temp_01_pluto
- case_temp_02_eu_uk

Model: Ollama qwen2.5:1.5b, temperature=0.0
Evaluator: StrictKeyAnswerEvaluator (1.0-strict, hash: 686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114)
Seeds: 42, 43, 44 (evaluated as deterministic reproducibility checks)

Outputs:
- benchmarks/results/phase7_ablation/raw_inferences.jsonl
- benchmarks/results/phase7_ablation/phase7_results.json
"""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

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
    compute_next_trust,
)
from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from ai_service.trust.base import (
    Decision,
    Observation,
    PolicyContext,
    PolicyState,
    TrustPolicy,
)
from models.domain import MemoryMode, TaskDomain
from models.provider import ModelProvider
from models.task import EvaluatorName, TaskExecuteRequest

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results" / "phase7_ablation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_FILE = REPO_ROOT / "benchmarks" / "manifests" / "phase6_case_manifest.json"
PHASE6_RAW_FILE = REPO_ROOT / "benchmarks" / "results" / "phase6_main" / "raw_inferences.jsonl"
RAW_JSONL_FILE = RESULTS_DIR / "raw_inferences.jsonl"
STRUCTURED_JSON_FILE = RESULTS_DIR / "phase7_results.json"

ABLATION_CONDITIONS = ["E0", "M0", "A0", "A1", "A2"]


# =====================================================================
# Ablation Policy Definitions
# =====================================================================

class AEMAWithoutQuarantinePolicy(AEMAPolicy):
    """
    A1: A-EMA without quarantine.
    - Update equations identical to A0 (alpha=0.85, beta=0.70).
    - Admissibility gate is disabled (always returns admissible=True).
    """
    name = "aema_no_quarantine"

    def __init__(self, initial_trust: float = 0.75):
        super().__init__(initial_trust=initial_trust, quarantine_threshold=0.0)

    @property
    def params(self) -> Dict[str, Any]:
        return {
            "alpha_success": ALPHA_SUCCESS,
            "beta_failure": BETA_FAILURE,
            "gamma_neutral": GAMMA_NEUTRAL,
            "quarantine_threshold": None,
            "quarantine_enabled": False,
            "initial_trust": self.initial_trust,
        }

    def admissible(self, state: PolicyState, ctx: PolicyContext) -> Decision:
        trust = float(state.extra.get("trust_score", self.initial_trust))
        return Decision(
            admissible=True,
            reason=f"admissible (quarantine disabled): trust {trust:.4f}",
            score=trust,
            diagnostics={"trust_score": trust, "quarantine_disabled": True},
        )


def compute_symmetric_next_trust(
    current_trust: float,
    outcome_score: float,
    alpha: float = 0.85,
    beta: float = 0.85,
    gamma: float = 0.80,
) -> tuple[float, str]:
    """Computes updated trust score using Symmetric EMA (alpha = beta = 0.85)."""
    old_trust = max(0.0, min(1.0, float(current_trust)))
    score = max(0.0, min(1.0, float(outcome_score)))

    if score >= 0.80:
        new_trust = (alpha * old_trust) + ((1.0 - alpha) * 1.0)
        reason = f"Success reward (R={score:.2f}, alpha={alpha})"
    elif score <= 0.30:
        new_trust = (beta * old_trust) + ((1.0 - beta) * 0.0)
        reason = f"Failure penalty (R={score:.2f}, beta={beta})"
    else:
        new_trust = (gamma * old_trust) + ((1.0 - gamma) * score)
        reason = f"Neutral outcome adjustment (R={score:.2f}, gamma={gamma})"

    bounded_trust = round(max(0.0, min(1.0, new_trust)), 4)
    return bounded_trust, reason


class SymmetricTrustPolicy(AEMAPolicy):
    """
    A2: Symmetric trust update.
    - Symmetric decay: alpha = beta = 0.85.
    - Quarantine enabled: theta = 0.35.
    """
    name = "symmetric_aema"

    def __init__(
        self,
        initial_trust: float = 0.75,
        quarantine_threshold: float = QUARANTINE_THRESHOLD,
        alpha_success: float = 0.85,
        beta_failure: float = 0.85,
    ):
        super().__init__(initial_trust=initial_trust, quarantine_threshold=quarantine_threshold)
        self.alpha_success = float(alpha_success)
        self.beta_failure = float(beta_failure)

    @property
    def params(self) -> Dict[str, Any]:
        return {
            "alpha_success": self.alpha_success,
            "beta_failure": self.beta_failure,
            "gamma_neutral": GAMMA_NEUTRAL,
            "quarantine_threshold": self.quarantine_threshold,
            "initial_trust": self.initial_trust,
        }

    def update(self, state: PolicyState, observation: Observation) -> PolicyState:
        old_trust = float(state.extra.get("trust_score", self.initial_trust))
        new_trust, reason = compute_symmetric_next_trust(
            old_trust,
            observation.reward,
            alpha=self.alpha_success,
            beta=self.beta_failure,
        )
        return state.with_observation(
            observation,
            trust_score=new_trust,
            last_reason=reason,
        )


def build_request(
    task_input: str,
    memory_enabled: bool,
    ground_truth: str,
    distractor: str,
    seed: int,
) -> TaskExecuteRequest:
    return TaskExecuteRequest(
        task_input=task_input,
        task_domain=TaskDomain.GENERAL,
        memory_enabled=memory_enabled,
        memory_mode=MemoryMode.ADAPTIVE if memory_enabled else MemoryMode.OFF,
        provider=ModelProvider.OLLAMA,
        model="qwen2.5:1.5b",
        temperature=0.0,
        seed=seed,
        evaluator=EvaluatorName.STRICT_KEY_ANSWER,
        evaluator_config={"ground_truth": ground_truth, "distractor": distractor},
    )


async def run_phase7(seeds: List[int], rerun_all: bool = False):
    settings.MAX_CYCLICAL_LOOPS = 1
    total_start = time.time()

    print("==================================================================")
    print("STARTING PHASE 7: ABLATION STUDIES (MECHANISM ISOLATION)")
    print("==================================================================")

    # 1. Load frozen manifest
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    with open(MANIFEST_FILE, "rb") as f:
        manifest_hash = hashlib.sha256(f.read()).hexdigest()

    all_cases = manifest_data["cases"]
    primary_case_ids = set(manifest_data["analysis_groupings"]["group_1_primary_harmful"])
    cases = [c for c in all_cases if c["case_id"] in primary_case_ids]

    print(f"Loaded frozen manifest: {MANIFEST_FILE} (SHA-256: {manifest_hash})")
    print(f"Primary Harmful-Memory Cases Selected: {len(cases)} / {len(all_cases)}")
    for c in cases:
        print(f"  - {c['case_id']}: GT='{c['ground_truth']}', Distractor='{c['distractor']}'")
    print(f"Ablation Conditions: {ABLATION_CONDITIONS}")
    print(f"Seeds: {seeds} (Deterministic reproducibility checks)")

    existing_inferences: Dict[str, Dict[str, Any]] = {}

    # Load from existing raw_jsonl if resuming
    if RAW_JSONL_FILE.exists() and not rerun_all:
        try:
            with open(RAW_JSONL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        inf = json.loads(line)
                        k = f"{inf['case_id']}::{inf['condition']}::{inf['seed']}::{inf['trial']}"
                        existing_inferences[k] = inf
            print(f"Resuming: Loaded {len(existing_inferences)} existing Phase 7 records.")
        except Exception as e:
            print(f"Warning: could not parse existing Phase 7 JSONL: {e}")

    # Import verified E0, M0, A0 from Phase 6
    if not rerun_all and PHASE6_RAW_FILE.exists():
        try:
            p6_imported = 0
            with open(PHASE6_RAW_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec["case_id"] in primary_case_ids:
                        cond = rec["condition"]
                        # Map A-EMA to A0
                        target_cond = "A0" if cond == "A-EMA" else cond
                        if target_cond in ["E0", "M0", "A0"]:
                            k = f"{rec['case_id']}::{target_cond}::{rec['seed']}::{rec['trial']}"
                            if k not in existing_inferences:
                                cpy = dict(rec)
                                cpy["condition"] = target_cond
                                existing_inferences[k] = cpy
                                p6_imported += 1
            if p6_imported > 0:
                print(f"Imported {p6_imported} verified baseline records (E0/M0/A0) from Phase 6.")
        except Exception as e:
            print(f"Warning: could not import from Phase 6 ({e})")

    all_inferences: List[Dict[str, Any]] = []
    jsonl_keys_on_disk: set[str] = set()

    if RAW_JSONL_FILE.exists() and not rerun_all:
        try:
            with open(RAW_JSONL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        inf = json.loads(line)
                        k = f"{inf['case_id']}::{inf['condition']}::{inf['seed']}::{inf['trial']}"
                        jsonl_keys_on_disk.add(k)
        except Exception:
            pass

    jsonl_fh = open(RAW_JSONL_FILE, "a", encoding="utf-8")
    inference_counter = 0

    def compute_and_save_summary():
        overall = {c: {"successes": 0, "total": 0, "t4_successes": 0, "t4_total": 0, "rewards": [], "latencies": [], "tokens": []} for c in ABLATION_CONDITIONS}
        per_seed = {s: {c: {"successes": 0, "total": 0, "t4_successes": 0, "t4_total": 0, "rewards": []} for c in ABLATION_CONDITIONS} for s in seeds}
        per_trial = {c: {t: {"successes": 0, "total": 0, "rewards": []} for t in range(1, 5)} for c in ABLATION_CONDITIONS}
        per_case = {cid: {c: {"t4_success": 0, "trials": []} for c in ABLATION_CONDITIONS} for cid in primary_case_ids}

        for inf in all_inferences:
            c = inf["condition"]
            if c not in ABLATION_CONDITIONS:
                continue
            s = inf["seed"]
            t = inf["trial"]
            cid = inf["case_id"]
            bin_res = inf["binary_result"]
            r = inf["reward"]
            lat = inf.get("latency_ms", 0)
            tok = inf.get("tokens_used", 0)

            overall[c]["successes"] += bin_res
            overall[c]["total"] += 1
            overall[c]["rewards"].append(r)
            overall[c]["latencies"].append(lat)
            overall[c]["tokens"].append(tok)

            if t == 4:
                overall[c]["t4_successes"] += bin_res
                overall[c]["t4_total"] += 1

            if s in per_seed and c in per_seed[s]:
                per_seed[s][c]["successes"] += bin_res
                per_seed[s][c]["total"] += 1
                per_seed[s][c]["rewards"].append(r)
                if t == 4:
                    per_seed[s][c]["t4_successes"] += bin_res
                    per_seed[s][c]["t4_total"] += 1

            if c in per_trial and t in per_trial[c]:
                per_trial[c][t]["successes"] += bin_res
                per_trial[c][t]["total"] += 1
                per_trial[c][t]["rewards"].append(r)

            if cid in per_case and c in per_case[cid]:
                per_case[cid][c]["trials"].append({"trial": t, "seed": s, "result": bin_res, "trust": inf.get("trust_after")})
                if t == 4 and s == 42:
                    per_case[cid][c]["t4_success"] = bin_res

        summary = {
            "metadata": {
                "manifest_file": str(MANIFEST_FILE),
                "manifest_hash": manifest_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "n_inferences": len(all_inferences),
                "wall_clock_seconds": round(time.time() - total_start, 2),
                "model": "qwen2.5:1.5b",
                "temperature": 0.0,
                "seeds": seeds,
                "evaluator_name": EvaluatorName.STRICT_KEY_ANSWER.value,
                "evaluator_version": "1.0-strict",
                "evaluator_hash": "686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114",
            },
            "overall_summary": {
                c: {
                    "cumulative_success_rate": round(d["successes"] / d["total"], 4) if d["total"] > 0 else 0.0,
                    "successes": d["successes"],
                    "total": d["total"],
                    "mean_reward": round(sum(d["rewards"]) / len(d["rewards"]), 4) if d["rewards"] else 0.0,
                    "t4_recovery_rate": round(d["t4_successes"] / d["t4_total"], 4) if d["t4_total"] > 0 else 0.0,
                    "t4_successes": d["t4_successes"],
                    "t4_total": d["t4_total"],
                    "mean_latency_ms": round(sum(d["latencies"]) / len(d["latencies"]), 1) if d["latencies"] else 0.0,
                    "mean_tokens": round(sum(d["tokens"]) / len(d["tokens"]), 1) if d["tokens"] else 0.0,
                }
                for c, d in overall.items()
            },
            "per_trial_success": {
                c: {
                    f"T{t}": {
                        "success_rate": round(d["successes"] / d["total"], 4) if d["total"] > 0 else 0.0,
                        "successes": d["successes"],
                        "total": d["total"],
                        "mean_reward": round(sum(d["rewards"]) / len(d["rewards"]), 4) if d["rewards"] else 0.0,
                    }
                    for t, d in t_dict.items()
                }
                for c, t_dict in per_trial.items()
            },
            "per_seed_summary": {
                s: {
                    c: {
                        "cumulative_success_rate": round(d["successes"] / d["total"], 4) if d["total"] > 0 else 0.0,
                        "t4_recovery_rate": round(d["t4_successes"] / d["t4_total"], 4) if d["t4_total"] > 0 else 0.0,
                    }
                    for c, d in s_dict.items()
                }
                for s, s_dict in per_seed.items()
            },
            "per_case_t4_summary": {
                cid: {c: per_case[cid][c]["t4_success"] for c in ABLATION_CONDITIONS}
                for cid in sorted(primary_case_ids)
            },
            "all_inferences": all_inferences,
        }

        with open(STRUCTURED_JSON_FILE, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

    # Main Execution Loop
    for seed in seeds:
        print(f"\n==================================================================")
        print(f"SEED {seed} / {seeds} (Deterministic Check)")
        print(f"==================================================================")

        for case in cases:
            cid = case["case_id"]
            grp = case["analysis_group"]
            prompt = case["task_prompt"]
            gt = case["ground_truth"]
            dist = case["distractor"]
            bad_mem_id = case["bad_memory_id"]

            print(f"\n--- Case: {cid} (Seed: {seed}) ---")

            rec_bad = MemoryRecord(
                memory_id=bad_mem_id,
                domain=TaskDomain.GENERAL,
                trigger=case["bad_memory_trigger"],
                strategy=case["bad_memory_strategy"],
                pitfall=case["bad_memory_pitfall"],
                initial_trust=0.75,
            )
            bank_bad = MemoryBank([rec_bad], bank_id=f"p7_bank_{cid}_{seed}").ensure_embeddings()
            bank_empty = MemoryBank([], bank_id=f"p7_empty_{cid}_{seed}").ensure_embeddings()

            # Execute all ablation conditions
            for condition in ABLATION_CONDITIONS:
                # Check if the entire 4-trial sequence is already cached
                sequence_keys = [f"{cid}::{condition}::{seed}::{trial}" for trial in range(1, 5)]
                sequence_cached = all(k in existing_inferences for k in sequence_keys)

                if sequence_cached:
                    for t in range(1, 5):
                        inference_counter += 1
                        ckey = f"{cid}::{condition}::{seed}::{t}"
                        rec = dict(existing_inferences[ckey])
                        rec["inference_id"] = inference_counter
                        rec["seed"] = seed
                        rec["condition"] = condition
                        all_inferences.append(rec)
                        if ckey not in jsonl_keys_on_disk:
                            jsonl_fh.write(json.dumps(rec) + "\n")
                            jsonl_fh.flush()
                            jsonl_keys_on_disk.add(ckey)
                        s_str = f"S={rec.get('trust_before')}->{rec.get('trust_after')}" if rec.get('trust_after') is not None else "NoTrust"
                        print(f"  {condition} T{t} [CACHED]: Out={repr(rec['model_output'][:25])} R={rec['reward']:.2f} B={rec['binary_result']} {s_str}")
                    continue

                # Run sequence fresh
                if condition == "E0":
                    bank = bank_empty
                    policy = StaticTrustPolicy(initial_trust=0.75)
                    mem_enabled = False
                elif condition == "M0":
                    bank = bank_bad
                    policy = StaticTrustPolicy(initial_trust=0.75)
                    mem_enabled = True
                elif condition == "A0":
                    bank = bank_bad
                    policy = AEMAPolicy(initial_trust=0.75, quarantine_threshold=QUARANTINE_THRESHOLD)
                    mem_enabled = True
                elif condition == "A1":
                    bank = bank_bad
                    policy = AEMAWithoutQuarantinePolicy(initial_trust=0.75)
                    mem_enabled = True
                elif condition == "A2":
                    bank = bank_bad
                    policy = SymmetricTrustPolicy(
                        initial_trust=0.75,
                        quarantine_threshold=QUARANTINE_THRESHOLD,
                        alpha_success=0.85,
                        beta_failure=0.85,
                    )
                    mem_enabled = True
                else:
                    raise ValueError(f"Unknown condition {condition}")

                run_ctx = RunContext(
                    bank=bank,
                    policy=policy,
                    top_k=1,
                    evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                    provider="ollama",
                    temperature=0.0,
                    seed=seed,
                )

                for t in range(1, 5):
                    inference_counter += 1
                    ckey = f"{cid}::{condition}::{seed}::{t}"

                    t_start = time.time()
                    trust_before = None
                    if mem_enabled and bad_mem_id in run_ctx.bank:
                        trust_before = run_ctx.trust_state.get(bad_mem_id).extra.get("trust_score", 0.75)

                    req = build_request(prompt, memory_enabled=mem_enabled, ground_truth=gt, distractor=dist, seed=seed)
                    res = await execute_task(req, run_context=run_ctx)
                    latency_ms = int((time.time() - t_start) * 1000)

                    trust_after = None
                    if mem_enabled and bad_mem_id in run_ctx.bank:
                        trust_after = run_ctx.trust_state.get(bad_mem_id).extra.get("trust_score", 0.75)

                    retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                    reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                    binary = int(res.binary_outcome if res.binary_outcome is not None else 0)

                    if condition == "A1":
                        quarantine_status = False  # Quarantine disabled
                    elif condition in ["A0", "A2"]:
                        quarantine_status = (trust_after is not None and trust_after < QUARANTINE_THRESHOLD)
                    else:
                        quarantine_status = False

                    rec = {
                        "inference_id": inference_counter,
                        "case_id": cid,
                        "analysis_group": grp,
                        "condition": condition,
                        "seed": seed,
                        "trial": t,
                        "model_output": res.final_output.strip() if res.final_output else "",
                        "reward": reward,
                        "binary_result": binary,
                        "retrieved_memory_ids": retrieved_ids,
                        "memory_exposed": len(retrieved_ids) > 0,
                        "retrieval_count": len(retrieved_ids),
                        "trust_before": trust_before,
                        "trust_after": trust_after,
                        "quarantine_status": quarantine_status,
                        "latency_ms": latency_ms,
                        "tokens_used": res.tokens_used or 0,
                        "evaluator_name": str(res.evaluator_name),
                        "evaluator_version": res.evaluator_version or "1.0-strict",
                        "reason": res.attempts[-1].reason if res.attempts else "",
                        "error": None,
                    }
                    all_inferences.append(rec)
                    existing_inferences[ckey] = rec
                    jsonl_fh.write(json.dumps(rec) + "\n")
                    jsonl_fh.flush()
                    jsonl_keys_on_disk.add(ckey)
                    compute_and_save_summary()

                    s_str = f"S={trust_before:.4f}->{trust_after:.4f} (Q={quarantine_status})" if trust_after is not None else "NoTrust"
                    print(f"  {condition} T{t}: Out={repr(rec['model_output'][:25])} R={reward:.2f} B={binary} Exp={rec['memory_exposed']} {s_str} ({latency_ms}ms)")

    # Extended Diagnostic Probe for A2 (Trials 1 to 6 on Seed 42)
    # Empirically verifies the exact recovery latency predicted by theory (k = 5 failures -> recovery at T6)
    print("\n==================================================================")
    print("RUNNING EXTENDED LATENCY PROBE FOR A2 (TRIALS 1-6, SEED 42)")
    print("==================================================================")
    for case in cases:
        cid = case["case_id"]
        grp = case["analysis_group"]
        prompt = case["task_prompt"]
        gt = case["ground_truth"]
        dist = case["distractor"]
        bad_mem_id = case["bad_memory_id"]

        ext_keys = [f"{cid}::A2_EXT::42::{trial}" for trial in range(1, 7)]
        ext_cached = all(k in existing_inferences for k in ext_keys)

        if ext_cached:
            for t in range(1, 7):
                ckey = f"{cid}::A2_EXT::42::{t}"
                rec = dict(existing_inferences[ckey])
                all_inferences.append(rec)
                print(f"  A2_EXT {cid} T{t} [CACHED]: Out={repr(rec['model_output'][:25])} R={rec['reward']:.2f} B={rec['binary_result']}")
            continue

        rec_bad = MemoryRecord(
            memory_id=bad_mem_id,
            domain=TaskDomain.GENERAL,
            trigger=case["bad_memory_trigger"],
            strategy=case["bad_memory_strategy"],
            pitfall=case["bad_memory_pitfall"],
            initial_trust=0.75,
        )
        bank_bad = MemoryBank([rec_bad], bank_id=f"p7_bank_ext_{cid}_42").ensure_embeddings()
        policy = SymmetricTrustPolicy(
            initial_trust=0.75,
            quarantine_threshold=QUARANTINE_THRESHOLD,
            alpha_success=0.85,
            beta_failure=0.85,
        )
        run_ctx = RunContext(
            bank=bank_bad,
            policy=policy,
            top_k=1,
            evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
            provider="ollama",
            temperature=0.0,
            seed=42,
        )

        for t in range(1, 7):
            ckey = f"{cid}::A2_EXT::42::{t}"
            t_start = time.time()
            trust_before = run_ctx.trust_state.get(bad_mem_id).extra.get("trust_score", 0.75)
            req = build_request(prompt, memory_enabled=True, ground_truth=gt, distractor=dist, seed=42)
            res = await execute_task(req, run_context=run_ctx)
            latency_ms = int((time.time() - t_start) * 1000)
            trust_after = run_ctx.trust_state.get(bad_mem_id).extra.get("trust_score", 0.75)

            retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
            reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
            binary = int(res.binary_outcome if res.binary_outcome is not None else 0)
            quarantine_status = (trust_after is not None and trust_after < QUARANTINE_THRESHOLD)

            rec = {
                "inference_id": len(all_inferences) + 1,
                "case_id": cid,
                "analysis_group": grp,
                "condition": "A2_EXT",
                "seed": 42,
                "trial": t,
                "model_output": res.final_output.strip() if res.final_output else "",
                "reward": reward,
                "binary_result": binary,
                "retrieved_memory_ids": retrieved_ids,
                "memory_exposed": len(retrieved_ids) > 0,
                "retrieval_count": len(retrieved_ids),
                "trust_before": trust_before,
                "trust_after": trust_after,
                "quarantine_status": quarantine_status,
                "latency_ms": latency_ms,
                "tokens_used": res.tokens_used or 0,
                "evaluator_name": str(res.evaluator_name),
                "evaluator_version": res.evaluator_version or "1.0-strict",
                "reason": res.attempts[-1].reason if res.attempts else "",
                "error": None,
            }
            all_inferences.append(rec)
            existing_inferences[ckey] = rec
            jsonl_fh.write(json.dumps(rec) + "\n")
            jsonl_fh.flush()
            jsonl_keys_on_disk.add(ckey)
            compute_and_save_summary()
            print(f"  A2_EXT {cid} T{t}: S={trust_before:.4f}->{trust_after:.4f} (Q={quarantine_status}) R={reward:.2f} B={binary} Exp={rec['memory_exposed']} ({latency_ms}ms)")

    jsonl_fh.close()
    compute_and_save_summary()
    total_time = round(time.time() - total_start, 2)

    # Final checksums
    with open(RAW_JSONL_FILE, "rb") as f:
        jsonl_hash = hashlib.sha256(f.read()).hexdigest()
    with open(STRUCTURED_JSON_FILE, "rb") as f:
        struct_hash = hashlib.sha256(f.read()).hexdigest()

    print("\n==================================================================")
    print(f"PHASE 7 ABLATION COMPLETE in {total_time}s")
    print(f"Total Inferences in Dataset: {len(all_inferences)}")
    print(f"Raw JSONL: {RAW_JSONL_FILE} (SHA-256: {jsonl_hash})")
    print(f"Structured JSON: {STRUCTURED_JSON_FILE} (SHA-256: {struct_hash})")
    print("==================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44], help="Random seeds to evaluate")
    parser.add_argument("--rerun-all", action="store_true", help="Force rerun all Phase 7 inferences")
    args = parser.parse_args()
    asyncio.run(run_phase7(seeds=args.seeds, rerun_all=args.rerun_all))
