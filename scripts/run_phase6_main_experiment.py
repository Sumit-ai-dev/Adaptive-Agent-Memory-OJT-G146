"""
Phase 6 Main Experiment Runner: 432-Inference Frozen Main Study.

Evaluates the frozen 12-case mixed suite across 3 conditions with 4 sequential trials each over 3 seeds:
- 12 Cases from benchmarks/manifests/phase6_case_manifest.json:
    - Group 1: 6 Primary Harmful-Memory Cases
    - Group 2: 5 Resistance / False-Quarantine Control Cases
    - Group 3: 1 Baseline-Failure Boundary Case
- 3 Conditions:
    1. E0: No Memory (stateless baseline)
    2. M0: Static Memory (persistent memory + retrieval, StaticTrustPolicy with S=0.75, no trust decay)
    3. A-EMA: Adaptive Memory (persistent memory + retrieval, AEMAPolicy with alpha=0.85, beta=0.70, theta=0.35)
- 4 Sequential Trials per case/condition/seed
- 3 Random Seeds: 42, 43, 44
- Total Inferences: 12 * 3 * 4 * 3 = 432
- Model: Ollama qwen2.5:1.5b, temperature=0.0
- Evaluator: StrictKeyAnswerEvaluator (1.0-strict, hash: 686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114)

Outputs:
- benchmarks/results/phase6_main/raw_inferences.jsonl (append-only ledger)
- benchmarks/results/phase6_main/phase6_results.json (structured summary with checksums)
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
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_service.config import settings
from ai_service.experiment.memory_bank import MemoryBank, MemoryRecord
from ai_service.experiment.run_context import RunContext
from ai_service.graph import execute_task
from ai_service.nodes.trust_node import QUARANTINE_THRESHOLD
from ai_service.trust.aema import AEMAPolicy, StaticTrustPolicy
from models.domain import MemoryMode, TaskDomain
from models.provider import ModelProvider
from models.task import EvaluatorName, TaskExecuteRequest

RESULTS_DIR = REPO_ROOT / "benchmarks" / "results" / "phase6_main"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_FILE = REPO_ROOT / "benchmarks" / "manifests" / "phase6_case_manifest.json"
PHASE5_RESULTS_FILE = REPO_ROOT / "benchmarks" / "results" / "phase5_validation" / "phase5_results.json"
RAW_JSONL_FILE = RESULTS_DIR / "raw_inferences.jsonl"
STRUCTURED_JSON_FILE = RESULTS_DIR / "phase6_results.json"

SEEDS = [42, 43, 44]
CONDITIONS = ["E0", "M0", "A-EMA"]


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


async def run_phase6(rerun_all: bool = False):
    settings.MAX_CYCLICAL_LOOPS = 1
    total_start = time.time()

    print("==================================================================")
    print("STARTING PHASE 6: 432-INFERENCE MAIN EXPERIMENT")
    print("==================================================================")

    # 1. Load frozen manifest
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    with open(MANIFEST_FILE, "rb") as f:
        manifest_hash = hashlib.sha256(f.read()).hexdigest()

    cases = manifest_data["cases"]
    print(f"Loaded frozen manifest from: {MANIFEST_FILE}")
    print(f"Manifest Hash (SHA-256): {manifest_hash}")
    print(f"Total Cases: {len(cases)} across 3 analysis groups")
    print(f"Seeds: {SEEDS} | Conditions: {CONDITIONS} | Trials: 4")
    print(f"Target Total Inferences: 12 * 3 * 4 * 3 = 432")

    existing_inferences: Dict[str, Dict[str, Any]] = {}

    # Load from raw_jsonl if resuming
    if RAW_JSONL_FILE.exists() and not rerun_all:
        try:
            with open(RAW_JSONL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        inf = json.loads(line)
                        k = f"{inf['case_id']}::{inf['condition']}::{inf['seed']}::{inf['trial']}"
                        existing_inferences[k] = inf
            print(f"Resuming from existing JSONL: {len(existing_inferences)} records loaded.")
        except Exception as e:
            print(f"Warning: could not parse existing JSONL ({e})")

    # If seed 42 not in existing_inferences and phase5_results.json exists, load seed 42 from Phase 5
    if not rerun_all and PHASE5_RESULTS_FILE.exists():
        try:
            with open(PHASE5_RESULTS_FILE, "r", encoding="utf-8") as f:
                p5_data = json.load(f)
                p5_added = 0
                for inf in p5_data.get("all_inferences", []):
                    k = f"{inf['case_id']}::{inf['condition']}::42::{inf['trial']}"
                    if k not in existing_inferences:
                        rec = dict(inf)
                        rec["seed"] = 42
                        existing_inferences[k] = rec
                        p5_added += 1
            if p5_added > 0:
                print(f"Imported {p5_added} verified Seed 42 inferences from Phase 5 validation.")
        except Exception as e:
            print(f"Warning: could not import Phase 5 results ({e})")

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

    # Open raw JSONL file in append mode
    jsonl_fh = open(RAW_JSONL_FILE, "a", encoding="utf-8")
    inference_counter = 0

    def save_checkpoint():
        # Compute aggregate summaries
        overall_summary = {
            c: {"successes": 0, "total": 0, "rewards": []} for c in CONDITIONS
        }
        per_seed_summary = {
            s: {c: {"successes": 0, "total": 0, "rewards": []} for c in CONDITIONS}
            for s in SEEDS
        }
        group_summary = {
            "group_1_primary_harmful": {c: {"successes": 0, "total": 0, "rewards": []} for c in CONDITIONS},
            "group_2_resistance_control": {c: {"successes": 0, "total": 0, "rewards": []} for c in CONDITIONS},
            "group_3_baseline_failure": {c: {"successes": 0, "total": 0, "rewards": []} for c in CONDITIONS},
        }

        case_group_map = {c["case_id"]: c["analysis_group"] for c in cases}

        for inf in all_inferences:
            c = inf["condition"]
            s = inf["seed"]
            cid = inf["case_id"]
            grp = case_group_map.get(cid, "unknown")

            overall_summary[c]["successes"] += inf["binary_result"]
            overall_summary[c]["total"] += 1
            overall_summary[c]["rewards"].append(inf["reward"])

            if s in per_seed_summary:
                per_seed_summary[s][c]["successes"] += inf["binary_result"]
                per_seed_summary[s][c]["total"] += 1
                per_seed_summary[s][c]["rewards"].append(inf["reward"])

            if grp in group_summary:
                group_summary[grp][c]["successes"] += inf["binary_result"]
                group_summary[grp][c]["total"] += 1
                group_summary[grp][c]["rewards"].append(inf["reward"])

        summary = {
            "manifest": {
                "manifest_file": str(MANIFEST_FILE),
                "manifest_hash": manifest_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "n_inferences": len(all_inferences),
                "total_target_inferences": 432,
                "wall_clock_seconds": round(time.time() - total_start, 2),
                "provider": "ollama",
                "model": "qwen2.5:1.5b",
                "temperature": 0.0,
                "seeds": SEEDS,
                "evaluator_name": EvaluatorName.STRICT_KEY_ANSWER.value,
                "evaluator_version": "1.0-strict",
                "evaluator_hash": "686bd43c10db85409f1b8f4137c979405162abaacd98827b4d67cec5acf1b114",
            },
            "overall_summary": {
                c: {
                    "success_rate": round(stats["successes"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
                    "successes": stats["successes"],
                    "total": stats["total"],
                    "mean_reward": round(sum(stats["rewards"]) / len(stats["rewards"]), 4) if stats["rewards"] else 0.0,
                }
                for c, stats in overall_summary.items()
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
                for s, s_data in per_seed_summary.items()
            },
            "group_summary": {
                grp: {
                    c: {
                        "success_rate": round(stats["successes"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
                        "successes": stats["successes"],
                        "total": stats["total"],
                        "mean_reward": round(sum(stats["rewards"]) / len(stats["rewards"]), 4) if stats["rewards"] else 0.0,
                    }
                    for c, stats in grp_data.items()
                }
                for grp, grp_data in group_summary.items()
            },
            "all_inferences": all_inferences,
        }
        with open(STRUCTURED_JSON_FILE, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

    # Main Execution Loop: Seeds -> Cases -> Conditions -> Trials
    for seed in SEEDS:
        print(f"\n##################################################################")
        print(f"SEED {seed} / {SEEDS}")
        print(f"##################################################################")

        for case in cases:
            cid = case["case_id"]
            grp = case["analysis_group"]
            prompt = case["task_prompt"]
            gt = case["ground_truth"]
            dist = case["distractor"]
            bad_mem_id = case["bad_memory_id"]

            print(f"\n--- Case: {cid} (Group: {grp}, Seed: {seed}) ---")

            rec_bad = MemoryRecord(
                memory_id=bad_mem_id,
                domain=TaskDomain.GENERAL,
                trigger=case["bad_memory_trigger"],
                strategy=case["bad_memory_strategy"],
                pitfall=case["bad_memory_pitfall"],
                initial_trust=0.75,
            )
            bank_bad = MemoryBank([rec_bad], bank_id=f"p6_bank_{cid}_{seed}").ensure_embeddings()
            bank_empty = MemoryBank([], bank_id=f"p6_empty_{cid}_{seed}").ensure_embeddings()

            # ------------------------------------------------------------
            # 1. Condition E0 (4 sequential trials)
            # ------------------------------------------------------------
            run_e0 = RunContext(
                bank=bank_empty,
                policy=StaticTrustPolicy(initial_trust=0.75),
                top_k=1,
                evaluator_name=EvaluatorName.STRICT_KEY_ANSWER.value,
                provider="ollama",
                temperature=0.0,
                seed=seed,
            )
            for t in range(1, 5):
                inference_counter += 1
                ckey = f"{cid}::E0::{seed}::{t}"

                if ckey in existing_inferences:
                    rec = dict(existing_inferences[ckey])
                    rec["inference_id"] = inference_counter
                    rec["seed"] = seed
                    rec["analysis_group"] = grp
                    all_inferences.append(rec)
                    if ckey not in jsonl_keys_on_disk:
                        jsonl_fh.write(json.dumps(rec) + "\n")
                        jsonl_fh.flush()
                        jsonl_keys_on_disk.add(ckey)
                    print(f"  E0 T{t} [CACHED]: Out={repr(rec['model_output'][:30])} R={rec['reward']:.2f} B={rec['binary_result']}")
                    continue

                t_start = time.time()
                req = build_request(prompt, memory_enabled=False, ground_truth=gt, distractor=dist, seed=seed)
                res = await execute_task(req, run_context=run_e0)
                latency_ms = int((time.time() - t_start) * 1000)

                retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                binary = int(res.binary_outcome if res.binary_outcome is not None else 0)

                rec = {
                    "inference_id": inference_counter,
                    "case_id": cid,
                    "analysis_group": grp,
                    "condition": "E0",
                    "seed": seed,
                    "trial": t,
                    "model_output": res.final_output.strip() if res.final_output else "",
                    "reward": reward,
                    "binary_result": binary,
                    "retrieved_memory_ids": retrieved_ids,
                    "memory_exposed": len(retrieved_ids) > 0,
                    "retrieval_count": len(retrieved_ids),
                    "trust_before": None,
                    "trust_after": None,
                    "quarantine_status": False,
                    "latency_ms": latency_ms,
                    "tokens_used": res.tokens_used or 0,
                    "evaluator_name": str(res.evaluator_name),
                    "evaluator_version": res.evaluator_version or "1.0-strict",
                    "reason": res.attempts[-1].reason if res.attempts else "",
                    "error": None,
                }
                all_inferences.append(rec)
                jsonl_fh.write(json.dumps(rec) + "\n")
                jsonl_fh.flush()
                save_checkpoint()
                print(f"  E0 T{t}: Out={repr(rec['model_output'][:30])} R={reward:.2f} B={binary} ({latency_ms}ms)")

            # ------------------------------------------------------------
            # 2. Condition M0 (4 sequential trials)
            # ------------------------------------------------------------
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
                ckey = f"{cid}::M0::{seed}::{t}"

                if ckey in existing_inferences:
                    rec = dict(existing_inferences[ckey])
                    rec["inference_id"] = inference_counter
                    rec["seed"] = seed
                    rec["analysis_group"] = grp
                    all_inferences.append(rec)
                    if ckey not in jsonl_keys_on_disk:
                        jsonl_fh.write(json.dumps(rec) + "\n")
                        jsonl_fh.flush()
                        jsonl_keys_on_disk.add(ckey)
                    print(f"  M0 T{t} [CACHED]: Out={repr(rec['model_output'][:30])} R={rec['reward']:.2f} B={rec['binary_result']}")
                    continue

                t_start = time.time()
                trust_before = run_m0.trust_state.get(bad_mem_id).extra["trust_score"]
                req = build_request(prompt, memory_enabled=True, ground_truth=gt, distractor=dist, seed=seed)
                res = await execute_task(req, run_context=run_m0)
                latency_ms = int((time.time() - t_start) * 1000)

                trust_after = run_m0.trust_state.get(bad_mem_id).extra["trust_score"]
                retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                binary = int(res.binary_outcome if res.binary_outcome is not None else 0)

                rec = {
                    "inference_id": inference_counter,
                    "case_id": cid,
                    "analysis_group": grp,
                    "condition": "M0",
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
                    "quarantine_status": False,
                    "latency_ms": latency_ms,
                    "tokens_used": res.tokens_used or 0,
                    "evaluator_name": str(res.evaluator_name),
                    "evaluator_version": res.evaluator_version or "1.0-strict",
                    "reason": res.attempts[-1].reason if res.attempts else "",
                    "error": None,
                }
                all_inferences.append(rec)
                jsonl_fh.write(json.dumps(rec) + "\n")
                jsonl_fh.flush()
                save_checkpoint()
                print(f"  M0 T{t}: Out={repr(rec['model_output'][:30])} R={reward:.2f} B={binary} Exp={rec['memory_exposed']} ({latency_ms}ms)")

            # ------------------------------------------------------------
            # 3. Condition A-EMA (4 sequential trials)
            # ------------------------------------------------------------
            policy_aema = AEMAPolicy(initial_trust=0.75)
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
                ckey = f"{cid}::A-EMA::{seed}::{t}"

                if ckey in existing_inferences:
                    rec = dict(existing_inferences[ckey])
                    rec["inference_id"] = inference_counter
                    rec["seed"] = seed
                    rec["analysis_group"] = grp
                    all_inferences.append(rec)
                    if ckey not in jsonl_keys_on_disk:
                        jsonl_fh.write(json.dumps(rec) + "\n")
                        jsonl_fh.flush()
                        jsonl_keys_on_disk.add(ckey)
                    print(f"  A-EMA T{t} [CACHED]: Out={repr(rec['model_output'][:30])} R={rec['reward']:.2f} B={rec['binary_result']}")
                    continue

                t_start = time.time()
                trust_before = run_aema.trust_state.get(bad_mem_id).extra["trust_score"]
                req = build_request(prompt, memory_enabled=True, ground_truth=gt, distractor=dist, seed=seed)
                res = await execute_task(req, run_context=run_aema)
                latency_ms = int((time.time() - t_start) * 1000)

                trust_after = run_aema.trust_state.get(bad_mem_id).extra["trust_score"]
                retrieved_ids = [m["experience"]["id"] for m in (res.retrieved_memories or [])]
                reward = float(res.outcome_score if res.outcome_score is not None else 0.0)
                binary = int(res.binary_outcome if res.binary_outcome is not None else 0)

                rec = {
                    "inference_id": inference_counter,
                    "case_id": cid,
                    "analysis_group": grp,
                    "condition": "A-EMA",
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
                    "quarantine_status": (trust_after < QUARANTINE_THRESHOLD),
                    "latency_ms": latency_ms,
                    "tokens_used": res.tokens_used or 0,
                    "evaluator_name": str(res.evaluator_name),
                    "evaluator_version": res.evaluator_version or "1.0-strict",
                    "reason": res.attempts[-1].reason if res.attempts else "",
                    "error": None,
                }
                all_inferences.append(rec)
                jsonl_fh.write(json.dumps(rec) + "\n")
                jsonl_fh.flush()
                save_checkpoint()
                print(f"  A-EMA T{t}: S={trust_before:.4f}->{trust_after:.4f} (Q={rec['quarantine_status']}) R={reward:.2f} B={binary} Exp={rec['memory_exposed']} ({latency_ms}ms)")

    jsonl_fh.close()
    save_checkpoint()
    total_time = round(time.time() - total_start, 2)

    # Compute final SHA-256 hashes
    with open(RAW_JSONL_FILE, "rb") as f:
        jsonl_hash = hashlib.sha256(f.read()).hexdigest()
    with open(STRUCTURED_JSON_FILE, "rb") as f:
        struct_hash = hashlib.sha256(f.read()).hexdigest()

    print("\n==================================================================")
    print(f"PHASE 6 MAIN EXPERIMENT COMPLETE in {total_time}s")
    print(f"Total Inferences: {len(all_inferences)} / 432")
    print(f"Raw JSONL: {RAW_JSONL_FILE} (SHA-256: {jsonl_hash})")
    print(f"Structured JSON: {STRUCTURED_JSON_FILE} (SHA-256: {struct_hash})")
    print("==================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun-all", action="store_true", help="Force rerun all 432 inferences")
    args = parser.parse_args()
    asyncio.run(run_phase6(rerun_all=args.rerun_all))
