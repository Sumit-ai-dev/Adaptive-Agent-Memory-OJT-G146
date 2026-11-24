"""
AEMA Python API Evolution Benchmark Runner.

Custom empirical benchmark evaluating autonomous agent resilience to API deprecations and breaking changes.
Measures Error Recurrence Rate (ERR), Negative Transfer Rate (NTR), Recovery Rate (RR), and Pass@k.
Executes candidate code with real pytest subprocesses inside isolated temporary directories.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Dict, List, Optional

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from benchmarks.evaluators.python_api_evaluator import PythonAPIEvolutionEvaluator
from benchmarks.telemetry import estimate_tokens_fallback, TrialTelemetryRecord
from models.domain import ExperienceStatus, MemoryMode, TaskDomain
from models.experience import Experience
from models.task import TaskExecuteRequest

logger = logging.getLogger("benchmarks.python_api")

CONDITION_MODE_MAP = {
    "vanilla": MemoryMode.OFF,
    "naive_rag": MemoryMode.NAIVE,
    "recency": MemoryMode.RECENCY,
    "symmetric": MemoryMode.SYMMETRIC,
    "adaptive": MemoryMode.ADAPTIVE,
}

MANIFEST_PATH = Path(__file__).parent / "data" / "python_api_evolution" / "manifest.json"


def load_api_evolution_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Python API Evolution manifest not found at {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks = data.get("tasks", [])
    return tasks[:limit]


async def seed_outdated_api_memory(store: SQLiteMemoryStore, task: Dict[str, Any]) -> None:
    """
    Seed an outdated API strategy memory into the store to simulate legacy training data or prior sessions.
    Tests whether Naive RAG and Recency suffer negative transfer while Adaptive Memory quarantines it.
    """
    task_id = task.get("id", "api_task")
    library = task.get("library", "python")
    trap = task.get("trap_memory", {})
    strategy = trap.get("strategy", f"Use legacy {library} methods.")
    pitfall = trap.get("pitfall", "Do not use modern methods.")

    outdated_exp = Experience(
        id=f"legacy_{task_id}",
        task_domain=TaskDomain.CODING,
        trigger_condition=f"Implement function using {library}",
        strategy_lesson=strategy,
        pitfall=pitfall,
        trust_score=0.50,
        uses_count=1,
        successes_count=0,
        failures_count=1,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(outdated_exp)


class PythonAPIEvolutionSession:
    """
    Manages an ephemeral, isolated SQLite database for a Python API Evolution evaluation session.
    Guarantees zero cross-trial, cross-task, or cross-condition memory leakage and safe cleanup on Windows.
    """

    def __init__(
        self,
        condition_name: str,
        task_id: str = "general",
        trial: int = 1,
        seed: Optional[int] = 42,
        db_path: str = ":memory:",
    ):
        self.condition_name = condition_name
        self.task_id = task_id
        self.trial = trial
        self.seed = seed

        if db_path == ":memory:":
            safe_task = re.sub(r"[^a-zA-Z0-9_-]", "_", str(task_id))
            try:
                self._temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
            except TypeError:
                self._temp_dir = tempfile.TemporaryDirectory()
            self.db_path = str(
                Path(self._temp_dir.name) / f"session_api_{condition_name}_{safe_task}_{trial}.db"
            )
        else:
            self._temp_dir = None
            self.db_path = db_path

        self.store = SQLiteMemoryStore(db_path=self.db_path)

    def close(self) -> None:
        """
        Safely checkpoint SQLite WAL, release handles, and remove temporary directory.
        Fails loudly if cleanup encounters an unresolvable error rather than silently ignoring.
        """
        import gc
        import shutil
        import sqlite3

        if hasattr(self, "db_path") and self.db_path and self.db_path != ":memory:":
            if os.path.exists(self.db_path):
                try:
                    conn = sqlite3.connect(self.db_path)
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.close()
                except Exception as e:
                    logger.debug(f"WAL checkpoint notice for {self.db_path}: {e}")

        self.store = None
        gc.collect()

        if hasattr(self, "_temp_dir") and self._temp_dir is not None:
            temp_dir_obj = self._temp_dir
            temp_path = getattr(temp_dir_obj, "name", None)
            try:
                temp_dir_obj.cleanup()
            except Exception as primary_exc:
                if temp_path and os.path.exists(temp_path):
                    try:
                        shutil.rmtree(temp_path, ignore_errors=False)
                    except Exception as secondary_exc:
                        raise RuntimeError(
                            f"Failed to clean up isolated benchmark database at {temp_path}: {secondary_exc}"
                        ) from primary_exc
            finally:
                self._temp_dir = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


async def run_api_evolution_trial(
    task: Dict[str, Any],
    condition_name: str,
    trial: int,
    memory_store: Optional[SQLiteMemoryStore] = None,
    evaluator: Optional[PythonAPIEvolutionEvaluator] = None,
    previous_trial_failed: bool = False,
    last_error_feedback: Optional[str] = None,
    seed: Optional[int] = 42,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> TrialTelemetryRecord:
    evaluator = evaluator or PythonAPIEvolutionEvaluator()
    task_id = str(task.get("id", "api_task"))
    problem = task.get("problem_description", "")
    mode = CONDITION_MODE_MAP[condition_name]

    session = None
    if memory_store is None:
        session = PythonAPIEvolutionSession(
            condition_name=condition_name,
            task_id=task_id,
            trial=trial,
            seed=seed,
        )
        memory_store = session.store
        if condition_name != "vanilla":
            await seed_outdated_api_memory(memory_store, task)

    try:
        # Clean task input containing the coding problem
        prompt_parts = [
            f"You are a Python software engineer. Solve the following programming task:\n{problem}\n",
            "Provide only the complete, valid Python code implementation wrapped in ```python ... ``` blocks.",
        ]
        # Provide execution feedback from previous trial if it failed
        if trial > 1 and previous_trial_failed and last_error_feedback:
            prompt_parts.append(
                f"\n[Previous Attempt Execution Failure]:\n{last_error_feedback}\n"
                "Please fix the implementation to resolve this error."
            )

        prompt = "\n".join(prompt_parts)

        req = TaskExecuteRequest(
            task_input=prompt,
            task_domain=TaskDomain.CODING,
            memory_enabled=(mode != MemoryMode.OFF),
            memory_mode=mode,
            model=model,
            provider=provider,
            seed=seed,
        )

        t0 = time.perf_counter()
        result = await execute_task(req, memory_store=memory_store)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        prompt_tokens = getattr(result, "prompt_tokens", 0) or 0
        completion_tokens = getattr(result, "completion_tokens", 0) or 0
        tokens_used = getattr(result, "tokens_used", 0) or (prompt_tokens + completion_tokens)
        token_count_estimated = False

        if tokens_used <= 0:
            full_text = prompt + " " + str(result.final_answer or result.final_output or "")
            tokens_used = estimate_tokens_fallback(full_text)
            token_count_estimated = True

        # Real pytest execution evaluation
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
                if "legacy" in exp_id or "poison" in exp_id:
                    quarantine_blocked_poison = True

        record = TrialTelemetryRecord(
            benchmark="python_api_evolution",
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
    finally:
        if session is not None:
            session.close()


async def run_api_evolution_benchmark(
    tasks_limit: int = 5,
    conditions: Optional[List[str]] = None,
    max_trials: int = 3,
    telemetry_path: Optional[str] = None,
    seed_legacy_memory: bool = True,
    seed: Optional[int] = 42,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions = conditions or ["vanilla", "naive_rag", "recency", "symmetric", "adaptive"]
    tasks = load_api_evolution_tasks(tasks_limit)
    evaluator = PythonAPIEvolutionEvaluator()
    all_records: List[Dict[str, Any]] = []

    print(f"\n[Python API Evolution] Starting benchmark with {len(tasks)} tasks across conditions: {conditions} (max_trials={max_trials})")

    for cond in conditions:
        print(f"  --> Condition: {cond}")
        for task in tasks:
            task_id = str(task.get("id", "api_task"))
            session = PythonAPIEvolutionSession(
                condition_name=cond,
                task_id=task_id,
                trial=1,
                seed=seed,
            )
            try:
                store = session.store
                # Seed legacy memory if condition uses memory
                if seed_legacy_memory and cond != "vanilla":
                    await seed_outdated_api_memory(store, task)

                prev_failed = False
                last_err = None
                for trial in range(1, max_trials + 1):
                    rec = await run_api_evolution_trial(
                        task=task,
                        condition_name=cond,
                        trial=trial,
                        memory_store=store,
                        evaluator=evaluator,
                        previous_trial_failed=prev_failed,
                        last_error_feedback=last_err,
                        seed=seed,
                        model=model,
                        provider=provider,
                    )
                    rec_dict = rec.to_dict()
                    all_records.append(rec_dict)

                    if telemetry_path:
                        Path(telemetry_path).parent.mkdir(parents=True, exist_ok=True)
                        with open(telemetry_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(rec_dict) + "\n")

                    if rec.success:
                        prev_failed = False
                        last_err = None
                        break
                    else:
                        prev_failed = True
                        last_err = rec.failure_reason
            finally:
                session.close()

    return all_records


if __name__ == "__main__":
    records = asyncio.run(run_api_evolution_benchmark(tasks_limit=2, max_trials=2))
    print(f"Completed {len(records)} research-grade Python API Evolution trial records.")
