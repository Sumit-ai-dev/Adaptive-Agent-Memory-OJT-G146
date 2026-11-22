"""
ToolBench Adversarial Benchmark Runner (Research-Grade).

Evaluates conditions (Vanilla, Naive RAG, Symmetric, Adaptive) under adversarial tool traps:
- Deprecated parameter traps.
- Multi-step dependency traps.
- Hallucination bait.
Evaluated via independent ToolBenchEvaluator using tool call extraction and schema verification.
Zero condition-specific or trial-index overrides. Real wall-clock timing and token metering.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from benchmarks.evaluators.toolbench_evaluator import ToolBenchEvaluator
from benchmarks.telemetry import estimate_tokens_fallback, TrialTelemetryRecord
from models.domain import ExperienceStatus, MemoryMode, TaskDomain
from models.experience import Experience
from models.task import TaskExecuteRequest

logger = logging.getLogger("benchmarks.toolbench")

CONDITION_MODE_MAP = {
    "vanilla": MemoryMode.OFF,
    "naive_rag": MemoryMode.NAIVE,
    "recency": MemoryMode.RECENCY,
    "symmetric": MemoryMode.SYMMETRIC,
    "adaptive": MemoryMode.ADAPTIVE,
}

TOOLBENCH_DATA_PATH = Path(__file__).parent / "data" / "toolbench" / "toolbench_adversarial_30.json"


def load_toolbench_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    if not TOOLBENCH_DATA_PATH.exists():
        raise FileNotFoundError(f"ToolBench dataset not found at {TOOLBENCH_DATA_PATH}")
    with open(TOOLBENCH_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks = data.get("tasks", [])
    return tasks[:limit]


async def seed_adversarial_poison(store: SQLiteMemoryStore, task: Dict[str, Any]) -> None:
    """
    Seed an initial adversarial poisoned memory (e.g. outdated/wrong API call)
    to test whether Naive RAG falls for it while Adaptive Memory quarantines it.
    """
    trap_desc = task.get("trap_description", "Use deprecated parameter")
    wrong_call = json.dumps(task.get("wrong_call", {}))
    task_id = task.get("id", "tb")

    poison_exp = Experience(
        id=f"poison_{task_id}",
        task_domain=TaskDomain.CODING,
        trigger_condition=task.get("query", ""),
        strategy_lesson=f"Always execute: {wrong_call}. Trap info: {trap_desc}",
        pitfall=f"Do not use valid call; force parameter trap: {trap_desc}",
        trust_score=0.50,
        uses_count=1,
        successes_count=0,
        failures_count=1,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(poison_exp)


async def run_toolbench_trial(
    task: Dict[str, Any],
    condition_name: str,
    trial: int,
    memory_store: SQLiteMemoryStore,
    evaluator: Optional[ToolBenchEvaluator] = None,
    previous_trial_failed: bool = False,
    seed: Optional[int] = 42,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> TrialTelemetryRecord:
    evaluator = evaluator or ToolBenchEvaluator()
    task_id = str(task.get("id", "tb_unknown"))
    query = task.get("query", "")
    mode = CONDITION_MODE_MAP[condition_name]

    # Clean prompt: ONLY task query and tool specifications.
    # NEVER leak correct call or validation criteria here.
    prompt = (
        f"Task: {query}\n"
        f"Available Tools: {json.dumps(task.get('tools', []))}\n"
        f"Instruction: Return the exact JSON tool call required to perform this task. "
        f"Ensure all parameter names strictly adhere to the current tool specification."
    )

    req = TaskExecuteRequest(
        task_input=prompt,
        task_domain=TaskDomain.CODING,
        memory_enabled=(mode != MemoryMode.OFF),
        memory_mode=mode,
        model=model,
        provider=provider,
        seed=seed,
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
        tool_calls=result.tool_calls or [],
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
            if "poison" in exp_id:
                quarantine_blocked_poison = True

    record = TrialTelemetryRecord(
        benchmark="toolbench",
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
        model=model or getattr(result, "model", None) or "default",
        provider=provider or getattr(result, "provider", None) or "default",
        seed=seed,
        failure_reason=eval_outcome.failure_reason,
        evaluator_metrics=eval_outcome.metrics,
        tool_calls=result.tool_calls or [],
    )
    return record


async def run_toolbench_benchmark(
    tasks_limit: int = 5,
    conditions: Optional[List[str]] = None,
    max_trials: int = 3,
    telemetry_path: Optional[str] = None,
    seed_poison: bool = True,
) -> List[Dict[str, Any]]:
    conditions = conditions or ["vanilla", "naive_rag", "symmetric", "adaptive"]
    tasks = load_toolbench_tasks(tasks_limit)
    evaluator = ToolBenchEvaluator()
    all_records: List[Dict[str, Any]] = []

    print(f"\n[ToolBench] Starting benchmark with {len(tasks)} adversarial tasks across conditions: {conditions} (max_trials={max_trials})")

    for cond in conditions:
        print(f"  --> Condition: {cond}")
        store_path = f"data/test_toolbench_{cond}.db"
        if os.path.exists(store_path):
            try:
                os.remove(store_path)
            except OSError:
                pass
        store = SQLiteMemoryStore(db_path=store_path)

        for task in tasks:
            # Seed adversarial poison if enabled (except for vanilla where memory is ignored)
            if seed_poison and cond != "vanilla":
                await seed_adversarial_poison(store, task)

            prev_failed = False
            for trial in range(1, max_trials + 1):
                rec = await run_toolbench_trial(
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
    records = asyncio.run(run_toolbench_benchmark(tasks_limit=2, max_trials=2))
    print(f"Completed {len(records)} research-grade ToolBench trial records.")
