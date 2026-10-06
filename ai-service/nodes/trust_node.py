"""
LangGraph Node 5: Trust Lifecycle Engine (trust_node.py)
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)

Implements Asymmetric Exponential Moving Average (A-EMA):
    - Success (R >= 0.80): S_{t+1} = 0.85 * S_t + 0.15 * 1.0 (Steady climb)
    - Failure (R <= 0.30): S_{t+1} = 0.70 * S_t + 0.30 * 0.0 (Aggressive drop)
    - Quarantine (S < 0.35): Automatically deprecates memory to eliminate negative transfer.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Sequence

from models.experience import (
    Experience,
    ExperienceMatch,
    ExperienceStatus,
    TrustHistoryRecord,
)
from models.task import TrustUpdate

logger = logging.getLogger("ai_service.nodes.trust_node")


ALPHA_SUCCESS = 0.85
BETA_FAILURE = 0.70
GAMMA_NEUTRAL = 0.80
QUARANTINE_THRESHOLD = 0.35


def compute_next_trust(
    current_trust: float,
    outcome_score: float,
) -> tuple[float, str]:
    """
    Computes updated trust score using Asymmetric EMA.
    Returns (new_trust_score, update_reason).
    """
    old_trust = max(0.0, min(1.0, float(current_trust)))
    score = max(0.0, min(1.0, float(outcome_score)))

    if score >= 0.80:
        # Success: Steady, controlled climb (alpha = 0.85)
        new_trust = (ALPHA_SUCCESS * old_trust) + ((1.0 - ALPHA_SUCCESS) * 1.0)
        reason = f"Success reward (R={score:.2f}, alpha={ALPHA_SUCCESS})"
    elif score <= 0.30:
        # Failure: Aggressive downward penalty (beta = 0.70)
        new_trust = (BETA_FAILURE * old_trust) + ((1.0 - BETA_FAILURE) * 0.0)
        reason = f"Failure penalty (R={score:.2f}, beta={BETA_FAILURE})"
    else:
        # Neutral / Partial completion
        new_trust = (GAMMA_NEUTRAL * old_trust) + ((1.0 - GAMMA_NEUTRAL) * score)
        reason = f"Neutral outcome adjustment (R={score:.2f}, gamma={GAMMA_NEUTRAL})"

    # Bound strictly within [0.0, 1.0] and round to 4 decimals
    bounded_trust = round(max(0.0, min(1.0, new_trust)), 4)
    return bounded_trust, reason


def update_experience_trust(
    experience: Experience,
    outcome_score: float,
    execution_id: str | None = None,
    quarantine_threshold: float = QUARANTINE_THRESHOLD,
) -> tuple[Experience, TrustHistoryRecord, TrustUpdate]:
    """
    Updates an experience model's trust score, increments usage counters,
    checks the deprecation boundary, and generates an audit record.
    """
    old_trust = experience.trust_score
    new_trust, reason = compute_next_trust(old_trust, outcome_score)
    delta = round(new_trust - old_trust, 4)

    # Increment usage statistics
    experience.uses_count += 1
    if outcome_score >= 0.80:
        experience.successes_count += 1
        # Promote candidate to active upon verified success
        if experience.status == ExperienceStatus.CANDIDATE:
            experience.status = ExperienceStatus.ACTIVE
            reason += " | Promoted from candidate to active"
    elif outcome_score <= 0.30:
        experience.failures_count += 1

    # Apply Theorem 1 Quarantine Cutoff
    if new_trust < quarantine_threshold:
        experience.status = ExperienceStatus.DEPRECATED
        reason += f" | Quarantined below theta={quarantine_threshold}"

    experience.trust_score = new_trust
    experience.updated_at = datetime.now(timezone.utc)

    # Create immutable audit ledger record
    audit_record = TrustHistoryRecord(
        experience_id=experience.id,
        execution_id=execution_id,
        old_trust=old_trust,
        new_trust=new_trust,
        delta=delta,
        reason=reason,
    )

    # Create lightweight client update
    trust_update = TrustUpdate(
        experience_id=experience.id,
        old_score=old_trust,
        new_score=new_trust,
        delta=delta,
        reason=reason,
    )

    return experience, audit_record, trust_update


def trust_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph StateGraph node function for trust lifecycle updates.
    Evaluates outcome score and updates all experiences retrieved for the task.
    """
    outcome_score = state.get("outcome_score", 0.50)
    execution_id = state.get("task_id")
    raw_matches = state.get("retrieved_experiences", [])

    updated_experiences: list[Experience] = []
    audit_records: list[TrustHistoryRecord] = []
    trust_updates: list[TrustUpdate] = []

    for item in raw_matches:
        if isinstance(item, ExperienceMatch):
            exp = item.experience
        elif isinstance(item, Experience):
            exp = item
        else:
            continue

        updated_exp, record, update = update_experience_trust(
            experience=exp,
            outcome_score=outcome_score,
            execution_id=execution_id,
        )
        updated_experiences.append(updated_exp)
        audit_records.append(record)
        trust_updates.append(update)

    return {
        "updated_experiences": updated_experiences,
        "trust_history_records": audit_records,
        "trust_updates": trust_updates,
    }


async def async_trust_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Asynchronous StateGraph node function for trust lifecycle updates and new experience registration.
    """
    import time
    start_ts = time.time()
    outcome_score = state.get("outcome_score", 0.85)
    execution_id = state.get("task_id")
    raw_matches = state.get("retrieved_memories") or state.get("retrieved_experiences", [])

    # F1: this node sits ON the retry cycle and is therefore visited once per ATTEMPT.
    # It is now PURE -- it computes trust updates but performs no I/O. Persistence
    # happens exactly once per task, from the terminal state, in
    # `ai_service.graph.execute_task`. Writing from here caused one failing task to
    # emit 3 trust_history rows and 3 counter increments (uses=3, s=2, f=1), which
    # fed straight into the ADAPTIVE retrieval gate and inflated P(reliable)
    # from 0.348 to 0.580. A retry is an attempt, not an independent observation.
    trust_updates: list[dict[str, Any]] = []

    for item in raw_matches:
        exp_dict = item.get("experience", item) if isinstance(item, dict) else item
        exp_id = exp_dict.get("id") if isinstance(exp_dict, dict) else getattr(exp_dict, "id", None)
        if not exp_id:
            continue
        old_trust = float(exp_dict.get("trustScore", exp_dict.get("trust_score", 0.75)))
        new_trust, reason = compute_next_trust(old_trust, outcome_score)
        delta = round(new_trust - old_trust, 4)
        is_quarantined = new_trust < QUARANTINE_THRESHOLD

        trust_updates.append({
            "experienceId": exp_id,
            "oldScore": old_trust,
            "newScore": new_trust,
            "delta": delta,
            "status": "quarantined" if is_quarantined else "active",
            "reason": reason,
            # Set by execute_task when the single task-level write is performed.
            "persisted": False,
        })

    candidate_exp = state.get("candidate_experience")
    new_exp_obj = None
    if candidate_exp and state.get("memory_enabled", True):
        from models.domain import TaskDomain
        from models.experience import Experience, ExperienceStatus
        domain_val = candidate_exp.get("task_domain", "general")
        try:
            task_domain_enum = TaskDomain(domain_val)
        except ValueError:
            task_domain_enum = TaskDomain.GENERAL

        new_exp_obj = Experience(
            task_domain=task_domain_enum,
            trigger_condition=candidate_exp.get("trigger_condition", ""),
            strategy_lesson=candidate_exp.get("strategy_lesson", ""),
            pitfall=candidate_exp.get("pitfall"),
            confidence=candidate_exp.get("confidence", 0.85),
            trust_score=0.75,
            status=ExperienceStatus.CANDIDATE,
        )

        # F1: the candidate is NOT written here. reflect_node also runs once per
        # attempt, so writing from this node produced one new candidate memory per
        # retry (3 rows for a single task). execute_task persists the terminal
        # candidate exactly once.

    duration_ms = int((time.time() - start_ts) * 1000)

    trace = {
        "id": f"step_trust_{int(start_ts)}",
        "type": "trust_update",
        "node": "trust_node",
        "title": "Reliability Audit & Trust Calibration",
        "detail": (
            f"Updated {len(trust_updates)} experiences via Asymmetric EMA. "
            f"{'New candidate memory stored in quarantine.' if new_exp_obj else ''}"
        ),
        "durationMs": duration_ms,
        "metadata": {
            "trustUpdates": trust_updates,
            "newExperienceCreated": new_exp_obj is not None,
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    return {
        "trust_updates": trust_updates,
        "new_experience": new_exp_obj,
        "trajectory": trajectory,
        "status": "completed",
    }
