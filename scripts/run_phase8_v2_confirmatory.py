"""
Phase 8 v2 Confirmatory Harmful-Memory Benchmark Runner.

RUNTIME-EQUIVALENCE INVARIANT:
The confirmatory experiment executes using the exact same production graph interface
as the qualification harness: `ai_service.graph.execute_task`.

Frozen Configuration:
- Config: benchmarks/manifests/phase8_v2_config.json
  (SHA-256: f401deceac562d6119bfcbd7f3ede377af171128c9c266881c8f501499fc32cb)
- Manifest: benchmarks/manifests/phase8_v2_case_manifest.json
  (SHA-256: b9f0591ea853758b7c2d4bec367159468398a3f4353c90751e2911387f39cbe3)
- Evaluator: StrictKeyAnswerEvaluator v1.0-strict
  (hash: 686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114)
- Model: Ollama qwen2.5:1.5b, temperature=0.0
- Conditions:
  * E0: Stateless Baseline (1 trial/case, memory disabled)
  * M0: Static Harmful Memory (4 sequential trials/harmful case, unmanaged)
  * A0: Adaptive Harmful Memory (4 sequential trials/harmful case, A-EMA policy)
  * P0: Adaptive Beneficial Memory (4 sequential trials/positive case, A-EMA policy)
- Seeds:
  * 42: Primary empirical seed
  * 43, 44: Deterministic reproducibility audits

Total Target Inferences:
- Per seed: 30 E0 + 96 M0 + 96 A0 + 24 P0 = 246 inferences
- Across 3 seeds: 246 * 3 = 738 inferences
"""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

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
from ai_service.tools.evaluator import StrictKeyAnswerEvaluator
from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from models.domain import MemoryMode, TaskDomain
from models.provider import ModelProvider
from models.task import EvaluatorName, TaskExecuteRequest

logger = logging.getLogger("phase8_v2_runner")

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results" / "phase8_v2_confirmatory"
CONFIG_FILE = REPO_ROOT / "benchmarks" / "manifests" / "phase8_v2_config.json"
MANIFEST_FILE = REPO_ROOT / "benchmarks" / "manifests" / "phase8_v2_case_manifest.json"
QUAL_FILE = REPO_ROOT / "benchmarks" / "manifests" / "phase8_v2_qualification_results.json"

EXPECTED_CONFIG_SHA256 = "f401deceac562d6119bfcbd7f3ede377af171128c9c266881c8f501499fc32cb"
EXPECTED_MANIFEST_SHA256 = "b9f0591ea853758b7c2d4bec367159468398a3f4353c90751e2911387f39cbe3"
EXPECTED_EVALUATOR_HASH = "686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114"

RAW_JSONL_FILE = RESULTS_DIR / "raw_inferences.jsonl"
STRUCTURED_JSON_FILE = RESULTS_DIR / "phase8_v2_results.json"
REPORT_MD_FILE = RESULTS_DIR / "PHASE8_V2_REPORT.md"
RUN_MANIFEST_FILE = RESULTS_DIR / "run_manifest.json"
INTEGRITY_REPORT_FILE = RESULTS_DIR / "integrity_report.json"
QUAL_AUDIT_FILE = RESULTS_DIR / "qualification_audit.json"

SEEDS = [42, 43, 44]
PRIMARY_SEED = 42
REPRODUCIBILITY_SEEDS = [43, 44]


def compute_file_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_prerequisites() -> Dict[str, Any]:
    """Verifies that config, manifest, and evaluator match their frozen cryptographic signatures."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file missing: {CONFIG_FILE}")
    cfg_hash = compute_file_sha256(CONFIG_FILE)
    if cfg_hash != EXPECTED_CONFIG_SHA256:
        raise ValueError(f"CONFIG HASH MISMATCH! Expected: {EXPECTED_CONFIG_SHA256}, Found: {cfg_hash}")

    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest file missing: {MANIFEST_FILE}")
    man_hash = compute_file_sha256(MANIFEST_FILE)
    if man_hash != EXPECTED_MANIFEST_SHA256:
        raise ValueError(f"MANIFEST HASH MISMATCH! Expected: {EXPECTED_MANIFEST_SHA256}, Found: {man_hash}")

    import inspect
    eval_src = inspect.getsource(StrictKeyAnswerEvaluator)
    eval_hash = hashlib.sha256(eval_src.encode("utf-8")).hexdigest()
    if eval_hash != EXPECTED_EVALUATOR_HASH:
        raise ValueError(f"EVALUATOR HASH MISMATCH! Expected: {EXPECTED_EVALUATOR_HASH}, Found: {eval_hash}")

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Verified frozen config hash (SHA-256):    {cfg_hash} [MATCH]")
    print(f"Verified frozen manifest hash (SHA-256):  {man_hash} [MATCH]")
    print(f"Verified frozen evaluator hash (SHA-256): {eval_hash} [MATCH]")
    return manifest


def build_request(
    task_input: str,
    memory_enabled: bool,
    ground_truth: str,
    distractor: Optional[str],
    seed: int,
) -> TaskExecuteRequest:
    evaluator_cfg = {"ground_truth": ground_truth}
    if distractor:
        evaluator_cfg["distractor"] = distractor
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
        evaluator_config=evaluator_cfg,
    )


def wilson_score_interval(successes: int, total: int, z: float = 1.95996) -> Dict[str, float]:
    """Computes exact 95% Wilson score confidence interval."""
    if total <= 0:
        return {"proportion": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}
    p = successes / total
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p * (1.0 - p) / total) + ((z**2) / (4.0 * total**2)))
    return {
        "proportion": round(p, 4),
        "ci_lower": round(max(0.0, center - margin), 4),
        "ci_upper": round(min(1.0, center + margin), 4),
    }


def mcnemar_exact_test(b: int, c: int) -> float:
    """Computes exact two-tailed McNemar p-value via binomial distribution."""
    n_disc = b + c
    if n_disc == 0:
        return 1.0
    k = min(b, c)
    p_one_tail = sum(math.comb(n_disc, i) * (0.5**n_disc) for i in range(k + 1))
    return min(1.0, 2.0 * p_one_tail)


async def run_confirmatory_benchmark(target_seed: Optional[int] = None, rerun_all: bool = False):
    total_start = time.time()
    manifest = verify_prerequisites()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    harmful_cases = manifest["primary_harmful_cases"]
    pos_cases = manifest["positive_control_cases"]

    if len(harmful_cases) != 24:
        raise ValueError(f"Expected exactly 24 harmful cases, found: {len(harmful_cases)}")
    if len(pos_cases) != 6:
        raise ValueError(f"Expected exactly 6 positive cases, found: {len(pos_cases)}")

    print(f"\n==================================================================")
    print("PHASE 8 v2 CONFIRMATORY BENCHMARK EXECUTION")
    print(f"Harmful Cases: {len(harmful_cases)} | Positive Controls: {len(pos_cases)}")
    print(f"Target Output Directory: {RESULTS_DIR}")
    print("==================================================================")

    seeds_to_run = [target_seed] if target_seed is not None else SEEDS
    print(f"Seeds to execute: {seeds_to_run}")

    existing_inferences: Dict[str, Dict[str, Any]] = {}
    completed_sequences: Set[Tuple[str, str, int]] = set()

    if RAW_JSONL_FILE.exists() and not rerun_all:
        try:
            with open(RAW_JSONL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        inf = json.loads(line)
                        k = f"{inf['case_id']}::{inf['condition']}::{inf['seed']}::{inf['trial']}"
                        existing_inferences[k] = inf

            counts: Dict[Tuple[str, str, int], int] = {}
            for inf in existing_inferences.values():
                seq_key = (inf["case_id"], inf["condition"], inf["seed"])
                counts[seq_key] = counts.get(seq_key, 0) + 1

            for seq_key, count in counts.items():
                cond = seq_key[1]
                expected = 1 if cond == "E0" else 4
                if count == expected:
                    completed_sequences.add(seq_key)
                else:
                    print(
                        f"Warning: Incomplete sequence detected for {seq_key} ({count}/{expected} trials). "
                        "Purging incomplete records to rerun sequence cleanly."
                    )
                    keys_to_remove = [
                        k for k, inf in existing_inferences.items()
                        if (inf["case_id"], inf["condition"], inf["seed"]) == seq_key
                    ]
                    for k in keys_to_remove:
                        del existing_inferences[k]

            print(
                f"Resuming from existing JSONL: {len(existing_inferences)} verified inferences, "
                f"{len(completed_sequences)} complete sequences."
            )
        except Exception as e:
            print(f"Warning: error loading existing JSONL ({e})")

    if not rerun_all and RAW_JSONL_FILE.exists() and len(existing_inferences) > 0:
        with open(RAW_JSONL_FILE, "w", encoding="utf-8") as f:
            for inf in existing_inferences.values():
                f.write(json.dumps(inf) + "\n")

    jsonl_fh = open(RAW_JSONL_FILE, "a", encoding="utf-8")
    all_inferences: List[Dict[str, Any]] = list(existing_inferences.values())
    inference_counter = len(all_inferences)

    evaluator = StrictKeyAnswerEvaluator()

    def save_checkpoint():
        """Computes summary metrics and updates phase8_v2_results.json."""
        condition_stats: Dict[str, Dict[str, Any]] = {
            c: {"successes": 0, "total": 0, "rewards": []} for c in ["E0", "M0", "A0", "P0"]
        }
        per_seed_stats: Dict[int, Dict[str, Any]] = {
            s: {c: {"successes": 0, "total": 0, "rewards": []} for c in ["E0", "M0", "A0", "P0"]}
            for s in SEEDS
        }

        harmful_case_ids = {c["case_id"] for c in harmful_cases}
        pos_case_ids = {c["case_id"] for c in pos_cases}
        case_level_data: Dict[str, Dict[str, Any]] = {}

        for inf in all_inferences:
            c = inf["condition"]
            s = inf["seed"]
            cid = inf["case_id"]
            bin_res = inf["binary_result"]
            r = inf["reward"]

            if c in condition_stats:
                condition_stats[c]["successes"] += bin_res
                condition_stats[c]["total"] += 1
                condition_stats[c]["rewards"].append(r)

            if s in per_seed_stats and c in per_seed_stats[s]:
                per_seed_stats[s][c]["successes"] += bin_res
                per_seed_stats[s][c]["total"] += 1
                per_seed_stats[s][c]["rewards"].append(r)

            if cid not in case_level_data:
                case_level_data[cid] = {
                    "case_id": cid,
                    "category": inf["category"],
                    "case_type": inf["case_type"],
                    "conditions": {},
                }

            if c not in case_level_data[cid]["conditions"]:
                case_level_data[cid]["conditions"][c] = {"trials": {}}

            trial_key = f"t{inf['trial']}_s{s}"
            case_level_data[cid]["conditions"][c]["trials"][trial_key] = {
                "trial": inf["trial"],
                "seed": s,
                "reward": r,
                "binary": bin_res,
                "trust_before": inf.get("trust_before"),
                "trust_after": inf.get("trust_after"),
                "quarantine": inf.get("quarantine_status", False),
                "distractor_selected": inf.get("distractor_selected", False),
            }

        # Seed 42 Primary Analysis
        s42_inf = [inf for inf in all_inferences if inf["seed"] == PRIMARY_SEED]
        m0_t1_harmful = [
            inf for inf in s42_inf
            if inf["condition"] == "M0" and inf["trial"] == 1 and inf["case_id"] in harmful_case_ids
        ]
        distractor_hits_t1 = sum(1 for inf in m0_t1_harmful if inf["distractor_selected"])
        hir = (distractor_hits_t1 / len(m0_t1_harmful)) if m0_t1_harmful else 0.0

        a0_t4_harmful = [
            inf for inf in s42_inf
            if inf["condition"] == "A0" and inf["trial"] == 4 and inf["case_id"] in harmful_case_ids
        ]
        a0_t4_recoveries = sum(1 for inf in a0_t4_harmful if inf["binary_result"] == 1)
        t4_recovery_rate = (a0_t4_recoveries / len(a0_t4_harmful)) if a0_t4_harmful else 0.0

        quarantined_cases_set = set()
        for inf in s42_inf:
            if inf["condition"] == "A0" and inf["case_id"] in harmful_case_ids:
                if inf.get("quarantine_status", False):
                    quarantined_cases_set.add(inf["case_id"])
        quarantine_rate = (len(quarantined_cases_set) / len(harmful_cases)) if harmful_cases else 0.0

        # Positive Controls
        p0_t4_pos = [
            inf for inf in s42_inf
            if inf["condition"] == "P0" and inf["trial"] == 4 and inf["case_id"] in pos_case_ids
        ]
        false_quarantined_cases = set()
        for inf in s42_inf:
            if inf["condition"] == "P0" and inf["case_id"] in pos_case_ids:
                if inf.get("quarantine_status", False):
                    false_quarantined_cases.add(inf["case_id"])
        false_quarantine_rate = (len(false_quarantined_cases) / len(pos_cases)) if pos_cases else 0.0
        p0_final_trust_scores = [inf["trust_after"] for inf in p0_t4_pos if inf.get("trust_after") is not None]

        # Wilson Confidence Intervals
        hir_ci = wilson_score_interval(distractor_hits_t1, len(m0_t1_harmful))
        recovery_ci = wilson_score_interval(a0_t4_recoveries, len(a0_t4_harmful))
        quarantine_ci = wilson_score_interval(len(quarantined_cases_set), len(harmful_cases))

        # McNemar Test: M0 Trial 4 vs A0 Trial 4 (Seed 42)
        m0_t4_dict = {
            inf["case_id"]: inf["binary_result"]
            for inf in s42_inf if inf["condition"] == "M0" and inf["trial"] == 4
        }
        a0_t4_dict = {
            inf["case_id"]: inf["binary_result"]
            for inf in s42_inf if inf["condition"] == "A0" and inf["trial"] == 4
        }
        mcnemar_b = sum(
            1 for cid in harmful_case_ids
            if m0_t4_dict.get(cid, 0) == 1 and a0_t4_dict.get(cid, 0) == 0
        )
        mcnemar_c = sum(
            1 for cid in harmful_case_ids
            if m0_t4_dict.get(cid, 0) == 0 and a0_t4_dict.get(cid, 0) == 1
        )
        mcnemar_p = mcnemar_exact_test(mcnemar_b, mcnemar_c)

        summary: Dict[str, Any] = {
            "metadata": {
                "phase": "phase8_v2_confirmatory",
                "status": "confirmatory_completed",
                "config_file": str(CONFIG_FILE),
                "config_hash": EXPECTED_CONFIG_SHA256,
                "manifest_file": str(MANIFEST_FILE),
                "manifest_hash": EXPECTED_MANIFEST_SHA256,
                "evaluator_name": EvaluatorName.STRICT_KEY_ANSWER.value,
                "evaluator_version": "1.0-strict",
                "evaluator_hash": EXPECTED_EVALUATOR_HASH,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "n_inferences": len(all_inferences),
                "total_target_inferences": len(SEEDS) * (len(harmful_cases) * 9 + len(pos_cases) * 5),
                "wall_clock_seconds": round(time.time() - total_start, 2),
                "model": "qwen2.5:1.5b",
                "provider": "ollama",
                "temperature": 0.0,
                "seeds": SEEDS,
                "primary_seed": PRIMARY_SEED,
                "reproducibility_seeds": REPRODUCIBILITY_SEEDS,
                "aema_params": {
                    "S0": 0.75,
                    "alpha_success": ALPHA_SUCCESS,
                    "beta_failure": BETA_FAILURE,
                    "gamma_neutral": GAMMA_NEUTRAL,
                    "quarantine_threshold": QUARANTINE_THRESHOLD,
                },
            },
            "primary_results_seed_42": {
                "harmful_cases_count": len(harmful_cases),
                "positive_control_cases_count": len(pos_cases),
                "e0_baseline_accuracy": {
                    "rate": round(
                        sum(1 for inf in s42_inf if inf["condition"] == "E0" and inf["case_id"] in harmful_case_ids and inf["binary_result"] == 1) / len(harmful_cases),
                        4
                    ),
                    "passed_cases": sum(1 for inf in s42_inf if inf["condition"] == "E0" and inf["case_id"] in harmful_case_ids and inf["binary_result"] == 1),
                    "total_harmful_cases": len(harmful_cases),
                },
                "harmful_influence_rate_hir": {
                    "rate": round(hir, 4),
                    "distractor_hits": distractor_hits_t1,
                    "total_eligible_cases": len(m0_t1_harmful),
                    "wilson_95_ci": hir_ci,
                },
                "m0_trial4_accuracy": {
                    "rate": round(
                        sum(1 for inf in s42_inf if inf["condition"] == "M0" and inf["trial"] == 4 and inf["case_id"] in harmful_case_ids and inf["binary_result"] == 1) / len(harmful_cases),
                        4
                    ),
                    "passed_cases": sum(1 for inf in s42_inf if inf["condition"] == "M0" and inf["trial"] == 4 and inf["case_id"] in harmful_case_ids and inf["binary_result"] == 1),
                    "total_cases": len(harmful_cases),
                },
                "a0_trial4_recovery_rate": {
                    "rate": round(t4_recovery_rate, 4),
                    "recovered_cases": a0_t4_recoveries,
                    "total_cases": len(a0_t4_harmful),
                    "wilson_95_ci": recovery_ci,
                },
                "a0_quarantine_rate": {
                    "rate": round(quarantine_rate, 4),
                    "quarantined_cases": len(quarantined_cases_set),
                    "total_cases": len(harmful_cases),
                    "wilson_95_ci": quarantine_ci,
                },
                "recovery_among_quarantined_susceptible": {
                    "rate": round(
                        sum(1 for inf in a0_t4_harmful if inf["case_id"] in quarantined_cases_set and inf["binary_result"] == 1) / len(quarantined_cases_set),
                        4
                    ) if quarantined_cases_set else 0.0,
                    "recovered": sum(1 for inf in a0_t4_harmful if inf["case_id"] in quarantined_cases_set and inf["binary_result"] == 1),
                    "total_quarantined": len(quarantined_cases_set),
                },
                "positive_control_retention": {
                    "false_quarantine_rate": round(false_quarantine_rate, 4),
                    "false_quarantined_cases": len(false_quarantined_cases),
                    "total_positive_cases": len(pos_cases),
                    "final_trust_s4_observed": [round(s, 4) for s in p0_final_trust_scores],
                    "mean_final_trust_s4": round(sum(p0_final_trust_scores) / len(p0_final_trust_scores), 4) if p0_final_trust_scores else 0.0,
                },
                "mcnemar_test_m0_vs_a0_t4": {
                    "discordant_m0_wins_b": mcnemar_b,
                    "discordant_a0_wins_c": mcnemar_c,
                    "exact_two_tailed_p_value": mcnemar_p,
                },
            },
            "condition_summary": {
                c: {
                    "success_rate": round(stats["successes"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
                    "successes": stats["successes"],
                    "total": stats["total"],
                    "mean_reward": round(sum(stats["rewards"]) / len(stats["rewards"]), 4) if stats["rewards"] else 0.0,
                }
                for c, stats in condition_stats.items()
            },
            "per_seed_summary": {
                s: {
                    c: {
                        "success_rate": round(stats["successes"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
                        "successes": stats["successes"],
                        "total": stats["total"],
                        "mean_reward": round(sum(stats["rewards"]) / len(stats["rewards"]), 4) if stats["rewards"] else 0.0,
                    }
                    for c, stats in s_data.items()
                }
                for s, s_data in per_seed_stats.items()
            },
            "case_level_data": case_level_data,
        }

        with open(STRUCTURED_JSON_FILE, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

    # =====================================================================
    # Main Execution Loop: Seeds -> Cases -> Conditions -> Trials
    # =====================================================================
    for seed in seeds_to_run:
        print(f"\n==================================================================")
        print(f"EXECUTING SEED {seed} / {seeds_to_run}")
        print(f"==================================================================")

        # -----------------------------------------------------------------
        # STEP 1: Primary Harmful Cases (24 cases)
        # -----------------------------------------------------------------
        for case in harmful_cases:
            cid = case["case_id"]
            cat = case["category"]
            prompt = case["prompt"]
            gt = case["ground_truth"]
            dist = case["distractor"]
            bad_mem_id = f"mem_{cid}"

            print(f"\n--- Primary Harmful Case: {cid} [{cat}] (Seed {seed}) ---")

            rec_bad = MemoryRecord(
                memory_id=bad_mem_id,
                domain=TaskDomain.GENERAL,
                trigger=case["bad_memory_trigger"],
                strategy=case["bad_memory_strategy"],
                pitfall=case["bad_memory_pitfall"],
                initial_trust=0.75,
            )
            bank_bad = MemoryBank([rec_bad], bank_id=f"p8v2_bank_{cid}_{seed}").ensure_embeddings()
            bank_empty = MemoryBank([], bank_id=f"p8v2_empty_{cid}_{seed}").ensure_embeddings()

            # Condition 1: E0 (1 baseline trial)
            seq_key_e0 = (cid, "E0", seed)
            if seq_key_e0 in completed_sequences:
                rec = existing_inferences[f"{cid}::E0::{seed}::1"]
                print(f"  E0 T1 [CACHED]: Out={repr(rec['model_output'][:30])} R={rec['reward']:.2f} B={rec['binary_result']}")
            else:
                inference_counter += 1
                t_start = time.time()
                run_e0 = RunContext(
                    bank=bank_empty,
                    policy=StaticTrustPolicy(initial_trust=0.75),
                    top_k=1,
                    evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                    provider="ollama",
                    temperature=0.0,
                    seed=seed,
                )
                req = build_request(prompt, memory_enabled=False, ground_truth=gt, distractor=dist, seed=seed)
                res = await execute_task(req, run_context=run_e0)
                latency_ms = int((time.time() - t_start) * 1000)

                reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                binary = int(res.binary_outcome if res.binary_outcome is not None else 0)
                model_out = res.final_output.strip() if res.final_output else ""
                
                dist_selected = (evaluator.normalize_text(dist) in evaluator.normalize_text(model_out)) if dist else False
                gt_selected = (evaluator.normalize_text(gt) in evaluator.normalize_text(model_out))

                rec = {
                    "run_id": f"phase8_v2_seed_{seed}",
                    "pair_id": f"{cid}_E0_t1_s{seed}",
                    "inference_id": inference_counter,
                    "case_id": cid,
                    "category": cat,
                    "case_type": "primary_harmful",
                    "condition": "E0",
                    "seed": seed,
                    "trial": 1,
                    "task_input": prompt,
                    "model_output": model_out,
                    "reward": reward,
                    "binary_result": binary,
                    "distractor_selected": dist_selected,
                    "ground_truth_selected": gt_selected,
                    "retrieved_memory_ids": [],
                    "memory_exposed": False,
                    "retrieval_count": 0,
                    "trust_before": None,
                    "trust_after": None,
                    "trust_state": {
                        "trust_before": None,
                        "trust_after": None,
                        "is_quarantined": False,
                    },
                    "quarantine_status": False,
                    "quarantine_state": False,
                    "latency_ms": latency_ms,
                    "latency": latency_ms / 1000.0,
                    "tokens_used": res.tokens_used or 0,
                    "token_usage": res.tokens_used or 0,
                    "evaluator_name": str(res.evaluator_name),
                    "evaluator_version": res.evaluator_version or "1.0-strict",
                    "evaluator_result": {
                        "reward": reward,
                        "outcome_score": reward,
                        "binary_outcome": binary,
                        "reason": res.attempts[-1].reason if res.attempts else "",
                    },
                    "reason": res.attempts[-1].reason if res.attempts else "",
                    "configuration_manifest_identity": {
                        "config_hash": EXPECTED_CONFIG_SHA256,
                        "manifest_hash": EXPECTED_MANIFEST_SHA256,
                        "evaluator_hash": EXPECTED_EVALUATOR_HASH,
                    },
                    "error": None,
                }
                all_inferences.append(rec)
                existing_inferences[f"{cid}::E0::{seed}::1"] = rec
                jsonl_fh.write(json.dumps(rec) + "\n")
                jsonl_fh.flush()
                completed_sequences.add(seq_key_e0)
                save_checkpoint()
                print(f"  E0 T1: Out={repr(model_out[:30])} R={reward:.2f} B={binary} ({latency_ms}ms)")

            # Condition 2: M0 (4 sequential trials, unbroken)
            seq_key_m0 = (cid, "M0", seed)
            if seq_key_m0 in completed_sequences:
                for t in range(1, 5):
                    rec = existing_inferences[f"{cid}::M0::{seed}::{t}"]
                    print(f"  M0 T{t} [CACHED]: Out={repr(rec['model_output'][:30])} R={rec['reward']:.2f} B={rec['binary_result']}")
            else:
                run_m0 = RunContext(
                    bank=bank_bad,
                    policy=StaticTrustPolicy(initial_trust=0.75),
                    top_k=1,
                    evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                    provider="ollama",
                    temperature=0.0,
                    seed=seed,
                )
                for t in range(1, 5):
                    inference_counter += 1
                    t_start = time.time()
                    trust_before = run_m0.trust_state.get(bad_mem_id).extra["trust_score"]
                    req = build_request(prompt, memory_enabled=True, ground_truth=gt, distractor=dist, seed=seed)
                    res = await execute_task(req, run_context=run_m0)
                    latency_ms = int((time.time() - t_start) * 1000)

                    trust_after = run_m0.trust_state.get(bad_mem_id).extra["trust_score"]
                    retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                    reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                    binary = int(res.binary_outcome if res.binary_outcome is not None else 0)
                    model_out = res.final_output.strip() if res.final_output else ""

                    dist_selected = (evaluator.normalize_text(dist) in evaluator.normalize_text(model_out)) if dist else False
                    gt_selected = (evaluator.normalize_text(gt) in evaluator.normalize_text(model_out))

                    rec = {
                        "run_id": f"phase8_v2_seed_{seed}",
                        "pair_id": f"{cid}_M0_t{t}_s{seed}",
                        "inference_id": inference_counter,
                        "case_id": cid,
                        "category": cat,
                        "case_type": "primary_harmful",
                        "condition": "M0",
                        "seed": seed,
                        "trial": t,
                        "task_input": prompt,
                        "model_output": model_out,
                        "reward": reward,
                        "binary_result": binary,
                        "distractor_selected": dist_selected,
                        "ground_truth_selected": gt_selected,
                        "retrieved_memory_ids": retrieved_ids,
                        "memory_exposed": len(retrieved_ids) > 0,
                        "retrieval_count": len(retrieved_ids),
                        "trust_before": trust_before,
                        "trust_after": trust_after,
                        "trust_state": {
                            "trust_before": trust_before,
                            "trust_after": trust_after,
                            "is_quarantined": False,
                        },
                        "quarantine_status": False,
                        "quarantine_state": False,
                        "latency_ms": latency_ms,
                        "latency": latency_ms / 1000.0,
                        "tokens_used": res.tokens_used or 0,
                        "token_usage": res.tokens_used or 0,
                        "evaluator_name": str(res.evaluator_name),
                        "evaluator_version": res.evaluator_version or "1.0-strict",
                        "evaluator_result": {
                            "reward": reward,
                            "outcome_score": reward,
                            "binary_outcome": binary,
                            "reason": res.attempts[-1].reason if res.attempts else "",
                        },
                        "reason": res.attempts[-1].reason if res.attempts else "",
                        "configuration_manifest_identity": {
                            "config_hash": EXPECTED_CONFIG_SHA256,
                            "manifest_hash": EXPECTED_MANIFEST_SHA256,
                            "evaluator_hash": EXPECTED_EVALUATOR_HASH,
                        },
                        "error": None,
                    }
                    all_inferences.append(rec)
                    existing_inferences[f"{cid}::M0::{seed}::{t}"] = rec
                    jsonl_fh.write(json.dumps(rec) + "\n")
                    jsonl_fh.flush()
                    print(f"  M0 T{t}: Out={repr(model_out[:30])} R={reward:.2f} B={binary} Exp={rec['memory_exposed']} ({latency_ms}ms)")
                completed_sequences.add(seq_key_m0)
                save_checkpoint()

            # Condition 3: A0 (4 sequential trials, unbroken A-EMA)
            seq_key_a0 = (cid, "A0", seed)
            if seq_key_a0 in completed_sequences:
                for t in range(1, 5):
                    rec = existing_inferences[f"{cid}::A0::{seed}::{t}"]
                    print(f"  A0 T{t} [CACHED]: S={rec['trust_before']}->{rec['trust_after']} R={rec['reward']:.2f} B={rec['binary_result']}")
            else:
                policy_aema = AEMAPolicy(
                    initial_trust=0.75,
                    quarantine_threshold=QUARANTINE_THRESHOLD,
                )
                run_aema = RunContext(
                    bank=bank_bad,
                    policy=policy_aema,
                    top_k=1,
                    evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                    provider="ollama",
                    temperature=0.0,
                    seed=seed,
                )
                for t in range(1, 5):
                    inference_counter += 1
                    t_start = time.time()
                    trust_before = run_aema.trust_state.get(bad_mem_id).extra["trust_score"]
                    req = build_request(prompt, memory_enabled=True, ground_truth=gt, distractor=dist, seed=seed)
                    res = await execute_task(req, run_context=run_aema)
                    latency_ms = int((time.time() - t_start) * 1000)

                    trust_after = run_aema.trust_state.get(bad_mem_id).extra["trust_score"]
                    retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                    reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                    binary = int(res.binary_outcome if res.binary_outcome is not None else 0)
                    model_out = res.final_output.strip() if res.final_output else ""

                    dist_selected = (evaluator.normalize_text(dist) in evaluator.normalize_text(model_out)) if dist else False
                    gt_selected = (evaluator.normalize_text(gt) in evaluator.normalize_text(model_out))
                    is_quarantined = (trust_after < QUARANTINE_THRESHOLD)

                    rec = {
                        "run_id": f"phase8_v2_seed_{seed}",
                        "pair_id": f"{cid}_A0_t{t}_s{seed}",
                        "inference_id": inference_counter,
                        "case_id": cid,
                        "category": cat,
                        "case_type": "primary_harmful",
                        "condition": "A0",
                        "seed": seed,
                        "trial": t,
                        "task_input": prompt,
                        "model_output": model_out,
                        "reward": reward,
                        "binary_result": binary,
                        "distractor_selected": dist_selected,
                        "ground_truth_selected": gt_selected,
                        "retrieved_memory_ids": retrieved_ids,
                        "memory_exposed": len(retrieved_ids) > 0,
                        "retrieval_count": len(retrieved_ids),
                        "trust_before": trust_before,
                        "trust_after": trust_after,
                        "trust_state": {
                            "trust_before": trust_before,
                            "trust_after": trust_after,
                            "is_quarantined": is_quarantined,
                        },
                        "quarantine_status": is_quarantined,
                        "quarantine_state": is_quarantined,
                        "latency_ms": latency_ms,
                        "latency": latency_ms / 1000.0,
                        "tokens_used": res.tokens_used or 0,
                        "token_usage": res.tokens_used or 0,
                        "evaluator_name": str(res.evaluator_name),
                        "evaluator_version": res.evaluator_version or "1.0-strict",
                        "evaluator_result": {
                            "reward": reward,
                            "outcome_score": reward,
                            "binary_outcome": binary,
                            "reason": res.attempts[-1].reason if res.attempts else "",
                        },
                        "reason": res.attempts[-1].reason if res.attempts else "",
                        "configuration_manifest_identity": {
                            "config_hash": EXPECTED_CONFIG_SHA256,
                            "manifest_hash": EXPECTED_MANIFEST_SHA256,
                            "evaluator_hash": EXPECTED_EVALUATOR_HASH,
                        },
                        "error": None,
                    }
                    all_inferences.append(rec)
                    existing_inferences[f"{cid}::A0::{seed}::{t}"] = rec
                    jsonl_fh.write(json.dumps(rec) + "\n")
                    jsonl_fh.flush()
                    print(
                        f"  A0 T{t}: S={trust_before:.4f}->{trust_after:.4f} (Q={is_quarantined}) "
                        f"R={reward:.2f} B={binary} Exp={rec['memory_exposed']} ({latency_ms}ms)"
                    )
                completed_sequences.add(seq_key_a0)
                save_checkpoint()

        # -----------------------------------------------------------------
        # STEP 2: Positive Control Cases (6 cases)
        # -----------------------------------------------------------------
        for case in pos_cases:
            cid = case["case_id"]
            cat = case["category"]
            prompt = case["prompt"]
            gt = case["ground_truth"]
            pos_mem_id = f"mem_{cid}"

            print(f"\n--- Positive Control Case: {cid} [{cat}] (Seed {seed}) ---")

            rec_pos = MemoryRecord(
                memory_id=pos_mem_id,
                domain=TaskDomain.GENERAL,
                trigger=case["prompt"],
                strategy=case["memory_strategy"],
                pitfall=case["memory_pitfall"],
                initial_trust=0.75,
            )
            bank_pos = MemoryBank([rec_pos], bank_id=f"p8v2_posbank_{cid}_{seed}").ensure_embeddings()
            bank_empty = MemoryBank([], bank_id=f"p8v2_emptypos_{cid}_{seed}").ensure_embeddings()

            # Condition 1: E0 (1 baseline trial)
            seq_key_e0_pos = (cid, "E0", seed)
            if seq_key_e0_pos in completed_sequences:
                rec = existing_inferences[f"{cid}::E0::{seed}::1"]
                print(f"  E0 T1 [CACHED]: Out={repr(rec['model_output'][:30])} R={rec['reward']:.2f} B={rec['binary_result']}")
            else:
                inference_counter += 1
                t_start = time.time()
                run_e0 = RunContext(
                    bank=bank_empty,
                    policy=StaticTrustPolicy(initial_trust=0.75),
                    top_k=1,
                    evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                    provider="ollama",
                    temperature=0.0,
                    seed=seed,
                )
                req = build_request(prompt, memory_enabled=False, ground_truth=gt, distractor=None, seed=seed)
                res = await execute_task(req, run_context=run_e0)
                latency_ms = int((time.time() - t_start) * 1000)

                reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                binary = int(res.binary_outcome if res.binary_outcome is not None else 0)
                model_out = res.final_output.strip() if res.final_output else ""
                gt_selected = (evaluator.normalize_text(gt) in evaluator.normalize_text(model_out))

                rec = {
                    "run_id": f"phase8_v2_seed_{seed}",
                    "pair_id": f"{cid}_E0_t1_s{seed}",
                    "inference_id": inference_counter,
                    "case_id": cid,
                    "category": cat,
                    "case_type": "positive_control",
                    "condition": "E0",
                    "seed": seed,
                    "trial": 1,
                    "task_input": prompt,
                    "model_output": model_out,
                    "reward": reward,
                    "binary_result": binary,
                    "distractor_selected": False,
                    "ground_truth_selected": gt_selected,
                    "retrieved_memory_ids": [],
                    "memory_exposed": False,
                    "retrieval_count": 0,
                    "trust_before": None,
                    "trust_after": None,
                    "trust_state": {
                        "trust_before": None,
                        "trust_after": None,
                        "is_quarantined": False,
                    },
                    "quarantine_status": False,
                    "quarantine_state": False,
                    "latency_ms": latency_ms,
                    "latency": latency_ms / 1000.0,
                    "tokens_used": res.tokens_used or 0,
                    "token_usage": res.tokens_used or 0,
                    "evaluator_name": str(res.evaluator_name),
                    "evaluator_version": res.evaluator_version or "1.0-strict",
                    "evaluator_result": {
                        "reward": reward,
                        "outcome_score": reward,
                        "binary_outcome": binary,
                        "reason": res.attempts[-1].reason if res.attempts else "",
                    },
                    "reason": res.attempts[-1].reason if res.attempts else "",
                    "configuration_manifest_identity": {
                        "config_hash": EXPECTED_CONFIG_SHA256,
                        "manifest_hash": EXPECTED_MANIFEST_SHA256,
                        "evaluator_hash": EXPECTED_EVALUATOR_HASH,
                    },
                    "error": None,
                }
                all_inferences.append(rec)
                existing_inferences[f"{cid}::E0::{seed}::1"] = rec
                jsonl_fh.write(json.dumps(rec) + "\n")
                jsonl_fh.flush()
                completed_sequences.add(seq_key_e0_pos)
                save_checkpoint()
                print(f"  E0 T1: Out={repr(model_out[:30])} R={reward:.2f} B={binary} ({latency_ms}ms)")

            # Condition 4: P0 (4 sequential trials, unbroken A-EMA)
            seq_key_p0 = (cid, "P0", seed)
            if seq_key_p0 in completed_sequences:
                for t in range(1, 5):
                    rec = existing_inferences[f"{cid}::P0::{seed}::{t}"]
                    print(f"  P0 T{t} [CACHED]: S={rec['trust_before']}->{rec['trust_after']} R={rec['reward']:.2f} B={rec['binary_result']}")
            else:
                policy_pos = AEMAPolicy(
                    initial_trust=0.75,
                    quarantine_threshold=QUARANTINE_THRESHOLD,
                )
                run_pos = RunContext(
                    bank=bank_pos,
                    policy=policy_pos,
                    top_k=1,
                    evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                    provider="ollama",
                    temperature=0.0,
                    seed=seed,
                )
                for t in range(1, 5):
                    inference_counter += 1
                    t_start = time.time()
                    trust_before = run_pos.trust_state.get(pos_mem_id).extra["trust_score"]
                    req = build_request(prompt, memory_enabled=True, ground_truth=gt, distractor=None, seed=seed)
                    res = await execute_task(req, run_context=run_pos)
                    latency_ms = int((time.time() - t_start) * 1000)

                    trust_after = run_pos.trust_state.get(pos_mem_id).extra["trust_score"]
                    retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                    reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                    binary = int(res.binary_outcome if res.binary_outcome is not None else 0)
                    model_out = res.final_output.strip() if res.final_output else ""
                    gt_selected = (evaluator.normalize_text(gt) in evaluator.normalize_text(model_out))
                    is_quarantined = (trust_after < QUARANTINE_THRESHOLD)

                    rec = {
                        "run_id": f"phase8_v2_seed_{seed}",
                        "pair_id": f"{cid}_P0_t{t}_s{seed}",
                        "inference_id": inference_counter,
                        "case_id": cid,
                        "category": cat,
                        "case_type": "positive_control",
                        "condition": "P0",
                        "seed": seed,
                        "trial": t,
                        "task_input": prompt,
                        "model_output": model_out,
                        "reward": reward,
                        "binary_result": binary,
                        "distractor_selected": False,
                        "ground_truth_selected": gt_selected,
                        "retrieved_memory_ids": retrieved_ids,
                        "memory_exposed": len(retrieved_ids) > 0,
                        "retrieval_count": len(retrieved_ids),
                        "trust_before": trust_before,
                        "trust_after": trust_after,
                        "trust_state": {
                            "trust_before": trust_before,
                            "trust_after": trust_after,
                            "is_quarantined": is_quarantined,
                        },
                        "quarantine_status": is_quarantined,
                        "quarantine_state": is_quarantined,
                        "latency_ms": latency_ms,
                        "latency": latency_ms / 1000.0,
                        "tokens_used": res.tokens_used or 0,
                        "token_usage": res.tokens_used or 0,
                        "evaluator_name": str(res.evaluator_name),
                        "evaluator_version": res.evaluator_version or "1.0-strict",
                        "evaluator_result": {
                            "reward": reward,
                            "outcome_score": reward,
                            "binary_outcome": binary,
                            "reason": res.attempts[-1].reason if res.attempts else "",
                        },
                        "reason": res.attempts[-1].reason if res.attempts else "",
                        "configuration_manifest_identity": {
                            "config_hash": EXPECTED_CONFIG_SHA256,
                            "manifest_hash": EXPECTED_MANIFEST_SHA256,
                            "evaluator_hash": EXPECTED_EVALUATOR_HASH,
                        },
                        "error": None,
                    }
                    all_inferences.append(rec)
                    existing_inferences[f"{cid}::P0::{seed}::{t}"] = rec
                    jsonl_fh.write(json.dumps(rec) + "\n")
                    jsonl_fh.flush()
                    print(
                        f"  P0 T{t}: S={trust_before:.4f}->{trust_after:.4f} (Q={is_quarantined}) "
                        f"R={reward:.2f} B={binary} Exp={rec['memory_exposed']} ({latency_ms}ms)"
                    )
                completed_sequences.add(seq_key_p0)
                save_checkpoint()

    jsonl_fh.close()
    save_checkpoint()

    print("\n==================================================================")
    print("PHASE 8 v2 CONFIRMATORY EXECUTION COMPLETED")
    print(f"Total Inferences Logged: {len(all_inferences)}")
    print(f"Raw Ledger Path: {RAW_JSONL_FILE}")
    print(f"Structured Results: {STRUCTURED_JSON_FILE}")
    print("==================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 8 v2 Confirmatory Benchmark Runner")
    parser.add_argument("--seed", type=int, default=None, help="Target a specific seed only")
    parser.add_argument("--rerun-all", action="store_true", help="Disregard cached inferences and rerun all")
    args = parser.parse_args()

    asyncio.run(run_confirmatory_benchmark(target_seed=args.seed, rerun_all=args.rerun_all))
