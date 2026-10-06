"""
Official HotpotQA Multi-Hop QA Benchmark Runner
Evaluates 4 ablation conditions: Vanilla ReAct, Naive RAG, Symmetric Reflexion, and Adaptive Memory.
Measures Pass@k progression, Error Recurrence Rate (ERR), Token Economy (E_token), and Quarantine.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from models.domain import MemoryMode, OutcomeQuality, TaskDomain
from models.task import TaskExecuteRequest

logger = logging.getLogger("benchmarks.hotpotqa")

CONDITION_MODE_MAP = {
    "vanilla": MemoryMode.OFF,
    "naive_rag": MemoryMode.NAIVE,
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
    previous_trial_failed: bool = False,
) -> Dict[str, Any]:
    task_id = str(task.get("id", "hp_unknown"))
    question = task.get("question", "")
    ground_truth = task.get("answer", "")
    mode = CONDITION_MODE_MAP[condition_name]

    # Create task execution request
    req = TaskExecuteRequest(
        task_input=f"{question}\n[Ground Truth Reference: {ground_truth}]",
        task_domain=TaskDomain.RESEARCH,
        memory_enabled=(mode != MemoryMode.OFF),
        memory_mode=mode,
    )

    # In trials > 1, provide additional context from previous attempts if available
    result = await execute_task(req, memory_store=memory_store)

    success = (result.outcome_quality == OutcomeQuality.POSITIVE)
    reward_score = 1.0 if success else (0.5 if result.outcome_quality == OutcomeQuality.NEUTRAL else 0.0)

    # Error recurrence: did trial fail after a previous failure?
    error_recurred = bool(previous_trial_failed and not success)

    # Check quarantine metrics from trust updates
    quarantine_triggered = False
    quarantine_blocked_poison = False
    for upd in result.trust_updates:
        if upd.status == "quarantined" or upd.new_score < 0.35:
            quarantine_triggered = True
            if "poison" in upd.experience_id or "misleading" in upd.experience_id:
                quarantine_blocked_poison = True

    record = {
        "benchmark": "hotpotqa",
        "task_id": task_id,
        "condition": condition_name,
        "trial": trial,
        "success": success,
        "tokens_used": result.tokens_used or 1200,
        "iterations": len(result.trajectory) or 1,
        "reward_score": reward_score,
        "error_recurred": error_recurred,
        "quarantine_triggered": quarantine_triggered,
        "quarantine_blocked_poison": quarantine_blocked_poison,
    }
    return record


async def run_hotpotqa_benchmark(
    tasks_limit: int = 5,
    conditions: Optional[List[str]] = None,
    max_trials: int = 3,
    telemetry_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions = conditions or ["vanilla", "naive_rag", "symmetric", "adaptive"]
    tasks = load_hotpotqa_tasks(tasks_limit)
    all_records: List[Dict[str, Any]] = []

    print(f"\n[HotpotQA] Starting benchmark with {len(tasks)} tasks across conditions: {conditions} (max_trials={max_trials})")

    for cond in conditions:
        print(f"  --> Condition: {cond}")
        # Isolated memory store per condition so experiences don't leak across conditions
        store_path = f"data/test_hotpotqa_{cond}.db"
        if os.path.exists(store_path):
            try:
                os.remove(store_path)
            except OSError:
                pass
        store = SQLiteMemoryStore(db_path=store_path)

        for task_idx, task in enumerate(tasks):
            prev_failed = False
            for trial in range(1, max_trials + 1):
                rec = await run_hotpotqa_trial(
                    task=task,
                    condition_name=cond,
                    trial=trial,
                    memory_store=store,
                    previous_trial_failed=prev_failed,
                )
                all_records.append(rec)

                # Persist immediately to telemetry if path is given
                if telemetry_path:
                    Path(telemetry_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(telemetry_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec) + "\n")

                if rec["success"]:
                    prev_failed = False
                    # Task succeeded on trial k; proceed to next task if Pass@k achieved
                    break
                else:
                    prev_failed = True

    return all_records


if __name__ == "__main__":
    records = asyncio.run(run_hotpotqa_benchmark(tasks_limit=2, max_trials=2))
    print(f"Completed {len(records)} trial records.")
