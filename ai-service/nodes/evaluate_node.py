"""
LangGraph Node 3: evaluate_node

Deterministically evaluates execution trajectories against objective correctness
criteria, producing the F3 outcome contract: a continuous reward R_t in [0.0, 1.0]
AND the binary outcome derived from it at an explicitly recorded threshold.

This node is the single authority on whether an attempt succeeded. The trust layer
consumes that decision; it never re-derives it.

F1: this node sits ON the retry cycle, so it runs once per ATTEMPT. It appends an
AttemptRecord per visit. Only the terminal attempt supplies the task-level outcome
that reaches a memory's evidence counters -- that selection happens once, in
`ai_service.graph.execute_task`, outside the cycle.
"""

import time
from typing import Any, Dict

from ai_service.tools.evaluator import (
    EvaluationOutcome,
    EvaluatorName,
    deterministic_evaluator,
)
from models.state import AgentState
from models.task import DEFAULT_OUTCOME_THRESHOLD, OutcomeQuality


async def evaluate_node(state: AgentState) -> Dict[str, Any]:
    start_ts = time.time()
    final_answer = state.get("final_answer", "")
    tool_calls = state.get("tool_calls", [])
    negative_pitfall = state.get("negative_pitfall")
    positive_strategy = state.get("positive_strategy")
    task_input = state.get("task_input", "")
    threshold = float(state.get("outcome_threshold") or DEFAULT_OUTCOME_THRESHOLD)

    if final_answer.startswith("Execution encountered a model provider error:"):
        outcome = EvaluationOutcome.from_reward(
            reward=0.50,
            evaluator_name=EvaluatorName.HEURISTIC_RUBRIC,
            reason=f"Inconclusive: Model provider execution failed ({final_answer[:120]}). Trust preserved.",
            outcome_threshold=threshold,
            details={"status": "inconclusive", "error": "provider_error"},
        )
    else:
        # Evaluator comes from explicit selection, directives, or task domain
        outcome = deterministic_evaluator.evaluate(
            final_answer=final_answer,
            evaluator=state.get("evaluator"),
            evaluator_config=state.get("evaluator_config") or {},
            tool_calls=tool_calls,
            negative_pitfall=negative_pitfall,
            positive_strategy=positive_strategy,
            task_input=task_input,
            task_domain=state.get("task_domain"),
            outcome_threshold=threshold,
        )

    score = outcome.reward
    reason = outcome.reason

    # Retained for backwards compatibility with existing consumers/UI.
    quality = (
        OutcomeQuality.POSITIVE.value
        if score >= 0.80
        else (OutcomeQuality.NEUTRAL.value if score >= 0.50 else OutcomeQuality.NEGATIVE.value)
    )
    duration_ms = int((time.time() - start_ts) * 1000)

    # F1: one AttemptRecord per visit. `loop_count` was incremented by execute_node
    # immediately upstream, so it is this attempt's 1-based index.
    attempt_index = int(state.get("loop_count", 1) or 1)
    attempts = list(state.get("attempts", []))
    attempts.append({
        "attempt_index": attempt_index,
        "reward": score,
        "binary_outcome": outcome.binary_outcome,
        "outcome_threshold": outcome.outcome_threshold,
        "evaluator_name": outcome.evaluator_name.value,
        "reason": reason,
        "tokens_used": int(state.get("tokens_used", 0) or 0),
        "is_terminal": False,  # resolved once, in execute_task, after the cycle ends
        "details": outcome.details or {},
    })

    trace = {
        "id": f"step_eval_{int(start_ts)}_{attempt_index}",
        "type": "thought",
        "node": "evaluate_node",
        "title": f"Deterministic Outcome Evaluation (Attempt {attempt_index})",
        "detail": (
            f"Attempt {attempt_index}: R = {score:.2f} -> binary={outcome.binary_outcome} "
            f"(threshold={outcome.outcome_threshold}, evaluator={outcome.evaluator_name.value}). {reason}"
        ),
        "durationMs": duration_ms,
        "metadata": {
            "attemptIndex": attempt_index,
            "outcomeScore": score,
            "binaryOutcome": outcome.binary_outcome,
            "outcomeThreshold": outcome.outcome_threshold,
            "outcomeQuality": quality,
            "evaluator": outcome.evaluator_name.value,
            "evaluatorVersion": outcome.evaluator_version,
            "evaluatorDetails": outcome.details or {},
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    return {
        "outcome_score": score,
        "outcome_quality": quality,
        "evaluator_reason": reason,
        "binary_outcome": outcome.binary_outcome,
        "outcome_threshold": outcome.outcome_threshold,
        "evaluator_name": outcome.evaluator_name.value,
        "evaluator_version": outcome.evaluator_version,
        "evaluator_details": outcome.details or {},
        "attempts": attempts,
        "trajectory": trajectory,
        "status": "reflecting",
    }
