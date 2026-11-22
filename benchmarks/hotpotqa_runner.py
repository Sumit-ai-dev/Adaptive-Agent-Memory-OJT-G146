"""
HotpotQA Multi-Hop QA Benchmark Runner (Research-Grade).

Evaluates conditions (Vanilla, Naive RAG, Symmetric, Adaptive) under identical environments.
- Ground truth is strictly isolated from agent prompts.
- Evaluated via independent HotpotQAEvaluator using official Exact Match and Token F1.
- Telemetry records real wall-clock latency and genuine token usage.
- Zero condition-specific or trial-index success overrides.
"""

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from benchmarks.evaluators.hotpotqa_evaluator import HotpotQAEvaluator
from benchmarks.telemetry import estimate_tokens_fallback, TrialTelemetryRecord
from models.domain import MemoryMode, TaskDomain
from models.task import TaskExecuteRequest

logger = logging.getLogger("benchmarks.hotpotqa")

CONDITION_MODE_MAP = {
    "vanilla": MemoryMode.OFF,
    "naive_rag": MemoryMode.NAIVE,
    "recency": MemoryMode.RECENCY,
    "symmetric": MemoryMode.SYMMETRIC,
    "adaptive": MemoryMode.ADAPTIVE,
}

HOTPOTQA_DATA_PATH = Path(__file__).parent / "data" / "hotpotqa" / "hotpotqa_test_500.json"


def load_hotpotqa_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    if not HOTPOTQA_DATA_PATH.exists():
        raise FileNotFoundError(f"HotpotQA dataset not found at {HOTPOTQA_DATA_PATH}")
    with open(HOTPOTQA_DATA_PATH, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    return tasks[:limit]


async def run_hotpotqa_trial(
    task: Dict[str, Any],
    condition_name: str,
    trial: int,
    memory_store: SQLiteMemoryStore,
    evaluator: Optional[HotpotQAEvaluator] = None,
    previous_trial_failed: bool = False,
) -> TrialTelemetryRecord:
    evaluator = evaluator or HotpotQAEvaluator()
    task_id = str(task.get("id", task.get("_id", "hp_unknown")))
    question = task.get("question", "")
    mode = CONDITION_MODE_MAP[condition_name]

    # Task prompt: STRICTLY isolated, containing only the question and instructions.
    # NEVER include ground truth or validation references here.
    prompt = (
        f"Answer the following multi-hop research question accurately and concisely.\n"
        f"Question: {question}"
    )

    req = TaskExecuteRequest(
        task_input=prompt,
        task_domain=TaskDomain.RESEARCH,
        memory_enabled=(mode != MemoryMode.OFF),
        memory_mode=mode,
    )

    # Monotonic high-resolution wall-clock timing
    t0 = time.perf_counter()
    result = await execute_task(req, memory_store=memory_store)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Token metering from response
    prompt_tokens = getattr(result, "prompt_tokens", 0) or 0
    completion_tokens = getattr(result, "completion_tokens", 0) or 0
    tokens_used = getattr(result, "tokens_used", 0) or (prompt_tokens + completion_tokens)
    token_count_estimated = False

    if tokens_used <= 0:
        full_text = prompt + " " + str(result.final_answer or result.final_output or "")
        tokens_used = estimate_tokens_fallback(full_text)
        token_count_estimated = True

    # Independent objective evaluation
    eval_outcome = evaluator.evaluate(
        task=task,
        agent_output=str(result.final_answer or result.final_output or ""),
        trajectory=result.trajectory,
    )

    success = eval_outcome.passed
    score = eval_outcome.score
    error_recurred = bool(previous_trial_failed and not success)

    # Quarantine telemetry from actual trust updates
    quarantine_triggered = False
    quarantine_blocked_poison = False
    for upd in (result.trust_updates or []):
        status = getattr(upd, "status", None)
        new_score = getattr(upd, "new_score", 1.0)
        exp_id = getattr(upd, "experience_id", "")
        if status == "quarantined" or new_score < 0.35:
            quarantine_triggered = True
            if "poison" in exp_id or "misleading" in exp_id:
                quarantine_blocked_poison = True

    record = TrialTelemetryRecord(
        benchmark="hotpotqa",
        task_id=task_id,
        condition=condition_name,
        trial=trial,
        success=success,
        score=score,
        evaluator_name=evaluator.name,
        evaluator_version=evaluator.version,
        tokens_used=tokens_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        token_count_estimated=token_count_estimated,
        latency_ms=round(latency_ms, 2),
        iterations=len(result.trajectory) if result.trajectory else 1,
        error_recurred=error_recurred,
        quarantine_triggered=quarantine_triggered,
        quarantine_blocked_poison=quarantine_blocked_poison,
        failure_reason=eval_outcome.failure_reason,
        evaluator_metrics=eval_outcome.metrics,
        tool_calls=result.tool_calls or [],
    )
    return record


async def run_hotpotqa_benchmark(
    tasks_limit: int = 5,
    conditions: Optional[List[str]] = None,
    max_trials: int = 3,
    telemetry_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions = conditions or ["vanilla", "naive_rag", "symmetric", "adaptive"]
    tasks = load_hotpotqa_tasks(tasks_limit)
    evaluator = HotpotQAEvaluator()
    all_records: List[Dict[str, Any]] = []

    print(f"\n[HotpotQA] Starting benchmark with {len(tasks)} tasks across conditions: {conditions} (max_trials={max_trials})")

    for cond in conditions:
        print(f"  --> Condition: {cond}")
        store_path = f"data/test_hotpotqa_{cond}.db"
        if os.path.exists(store_path):
            try:
                os.remove(store_path)
            except OSError:
                pass
        store = SQLiteMemoryStore(db_path=store_path)

        for task in tasks:
            prev_failed = False
            for trial in range(1, max_trials + 1):
                rec = await run_hotpotqa_trial(
                    task=task,
                    condition_name=cond,
                    trial=trial,
                    memory_store=store,
                    evaluator=evaluator,
                    previous_trial_failed=prev_failed,
                )
                rec_dict = rec.to_dict()
                all_records.append(rec_dict)

                if telemetry_path:
                    Path(telemetry_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(telemetry_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec_dict) + "\n")

                if rec.success:
                    prev_failed = False
                    break
                else:
                    prev_failed = True

    return all_records


if __name__ == "__main__":
    records = asyncio.run(run_hotpotqa_benchmark(tasks_limit=2, max_trials=2))
    print(f"Completed {len(records)} research-grade HotpotQA trial records.")
