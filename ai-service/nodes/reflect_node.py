"""
LangGraph Node 4: reflect_node
Distills completed execution trajectories into structured procedural tuples:
  {trigger_condition, strategy_lesson, pitfall, confidence}
Saves candidate experiences into quarantine status for empirical validation.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from ai_service.config import settings
from ai_service.context.token_budget import calculate_token_cost, count_tokens
from ai_service.llm_client import llm_gateway, resolve_provider_config
from models.domain import TaskDomain
from models.experience import ExperienceStatus
from models.state import AgentState

logger = logging.getLogger(__name__)


def normalize_reflection_text(val: Any, fallback: str = "") -> str:
    """
    Safely extract and normalize reflection values into clean, meaningful text.
    Handles strings, dicts, nested dicts, lists, numbers, and nulls.
    Avoids producing raw Python string representations like "{'key': 'value'}".
    """
    if val is None:
        return fallback

    if isinstance(val, str):
        cleaned = val.strip()
        return cleaned if cleaned else fallback

    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return str(val)

    if isinstance(val, list):
        items = [normalize_reflection_text(item, fallback="") for item in val]
        items = [i for i in items if i]
        return ". ".join(items) if items else fallback

    if isinstance(val, dict):
        if not val:
            return fallback

        # If dict has only 1 key, extract the inner value directly
        if len(val) == 1:
            only_val = next(iter(val.values()))
            res = normalize_reflection_text(only_val, fallback="")
            if res:
                return res

        # If multiple keys, format human-readably: e.g. "Action: ... Reason: ..."
        parts = []
        for k, v in val.items():
            norm_v = normalize_reflection_text(v, fallback="")
            if not norm_v:
                continue
            clean_k = str(k).replace("_", " ").strip().capitalize()
            if norm_v.lower().startswith(clean_k.lower() + ":"):
                parts.append(norm_v)
            else:
                parts.append(f"{clean_k}: {norm_v}")

        return ". ".join(parts) if parts else fallback

    s = str(val).strip()
    return s if s else fallback


def normalize_reflection_confidence(val: Any, default: float = 0.85) -> float:
    """Safely parse confidence score into a float clamped between 0.0 and 1.0."""
    if val is None:
        return default
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        score = float(val)
    elif isinstance(val, str):
        try:
            score = float(val.strip().rstrip("%"))
            if score > 1.0 and score <= 100.0:
                score /= 100.0
        except ValueError:
            val_lower = val.lower().strip()
            if "high" in val_lower:
                score = 0.85
            elif "medium" in val_lower or "moderate" in val_lower:
                score = 0.70
            elif "low" in val_lower:
                score = 0.40
            else:
                score = default
    elif isinstance(val, dict):
        inner_score = val.get("score") or val.get("value") or val.get("confidence")
        return normalize_reflection_confidence(inner_score, default=default)
    elif isinstance(val, (list, tuple)) and len(val) > 0:
        return normalize_reflection_confidence(val[0], default=default)
    else:
        score = default

    return max(0.0, min(1.0, score))


def normalize_reflection_payload(
    parsed: Any,
    task_input: str,
    domain: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate and normalize arbitrary LLM reflection output into a strictly typed candidate experience.
    Ensures trigger_condition, strategy_lesson, and pitfall are strings, confidence is a float [0, 1].
    """
    if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
        parsed = parsed[0]

    if not isinstance(parsed, dict):
        parsed = {}

    # Check for root wrapper keys like {"reflection": {...}} or {"experience": {...}}
    for wrapper in ("reflection", "experience", "candidate_experience", "candidate", "response", "data", "result"):
        if wrapper in parsed and isinstance(parsed[wrapper], dict):
            inner = parsed[wrapper]
            if any(k in inner for k in ("strategy_lesson", "trigger_condition", "pitfall", "confidence")):
                parsed = inner
                break

    safe_task_prefix = str(task_input)[:50] if task_input else "general"

    trigger = normalize_reflection_text(
        parsed.get("trigger_condition"),
        fallback=f"Tasks similar to: {safe_task_prefix}",
    )
    strategy = normalize_reflection_text(
        parsed.get("strategy_lesson"),
        fallback="Follow verified step-by-step reasoning constraints.",
    )
    pitfall = normalize_reflection_text(
        parsed.get("pitfall"),
        fallback="Avoid relying on uncorroborated single-source facts.",
    )
    confidence = normalize_reflection_confidence(
        parsed.get("confidence"),
        default=0.85,
    )

    return {
        "user_id": user_id,
        "task_domain": domain,
        "trigger_condition": trigger,
        "strategy_lesson": strategy,
        "pitfall": pitfall,
        "confidence": confidence,
        "status": ExperienceStatus.CANDIDATE.value,
    }


async def reflect_node(state: AgentState) -> Dict[str, Any]:
    start_ts = time.time()
    task_input = state.get("task_input", "")
    domain = state.get("task_domain", "general")
    final_answer = state.get("final_answer", "")
    outcome_score = state.get("outcome_score", 0.5)

    # Short-circuit: do not run reflection or generate candidate memories if task budget was exceeded
    if state.get("budget_exceeded") is True or state.get("budget_error"):
        trace = {
            "id": f"step_reflect_skip_{int(start_ts)}",
            "type": "thought",
            "node": "reflect_node",
            "title": "Reflection Skipped (Budget Exceeded)",
            "detail": "Reflection distillation skipped because task budget was exceeded.",
            "durationMs": int((time.time() - start_ts) * 1000),
            "metadata": {"budgetExceeded": True},
        }
        trajectory = list(state.get("trajectory", []))
        trajectory.append(trace)
        return {
            "candidate_experience": None,
            "new_experience_created": False,
            "trajectory": trajectory,
            "status": "updating_trust",
        }

    prompt = (
        f"You are the Reflection Engine for an autonomous agent with persistent experiential memory.\n"
        f"Analyze this completed task execution:\n"
        f"Task: {task_input}\n"
        f"Domain: {domain}\n"
        f"Final Output: {final_answer[:400]}\n"
        f"Outcome Score (R): {outcome_score:.2f}\n\n"
        f"Extract a structured experience tuple in valid JSON format with keys:\n"
        f"- 'trigger_condition': General applicability predicate (when to recall this lesson)\n"
        f"- 'strategy_lesson': Actionable positive operational directive (+sigma)\n"
        f"- 'pitfall': Critical negative pitfall to avoid (-pi)\n"
        f"- 'confidence': Float between 0.0 and 1.0"
    )

    messages = [
        {"role": "system", "content": "You extract concise, actionable procedural memory tuples in JSON."},
        {"role": "user", "content": prompt},
    ]

    # S8: reflection uses the run's declared provider/model/temperature like every other call site.
    provider_config, requested_temperature = resolve_provider_config(state)
    prompt_tokens = sum(count_tokens(m.get("content", "")) for m in messages)

    candidate_exp = None
    has_provider_error = False
    raw_json = ""
    gen_tokens = 0
    try:
        raw_json, gen_tokens = await llm_gateway.generate(
            messages, config=provider_config, json_mode=True,
            temperature=requested_temperature,
        )
        # Parse JSON safely and normalize structured types
        parsed = json.loads(raw_json)
        candidate_exp = normalize_reflection_payload(
            parsed=parsed,
            task_input=task_input,
            domain=domain,
            user_id=state.get("user_id"),
        )
    except Exception as exc:
        logger.warning(f"Reflection LLM generation or parsing error: {exc}. Using safe candidate fallback.")
        has_provider_error = True
        candidate_exp = {
            "user_id": state.get("user_id"),
            "task_domain": domain,
            "trigger_condition": f"Tasks involving: {task_input[:50]}",
            "strategy_lesson": "Verify domain constraints and validate output syntax against expectations.",
            "pitfall": "Do not skip preliminary boundary condition validation.",
            "confidence": 0.80,
            "status": ExperienceStatus.CANDIDATE.value,
        }

    # Track tokens and compute cost for reflection LLM call
    if has_provider_error:
        completion_tokens = 0
        step_tokens = 0
        step_cost = 0.0
    else:
        completion_tokens = count_tokens(raw_json)
        step_tokens = gen_tokens if gen_tokens > 0 else (prompt_tokens + completion_tokens)
        prov_name = provider_config.provider.value if provider_config and provider_config.provider else (state.get("provider") or "groq")
        mod_name = provider_config.model if provider_config and provider_config.model else (state.get("model") or "openai/gpt-oss-120b")
        step_cost = calculate_token_cost(
            provider=prov_name,
            model=mod_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    accumulated_tokens = state.get("tokens_used", 0) + step_tokens
    accumulated_prompt_tokens = state.get("prompt_tokens", 0) + (0 if has_provider_error else prompt_tokens)
    accumulated_completion_tokens = state.get("completion_tokens", 0) + completion_tokens
    accumulated_cost = round(state.get("total_cost_usd", 0.0) + step_cost, 6)

    is_budget_exceeded = (
        state.get("budget_exceeded", False)
        or accumulated_cost >= settings.MAX_TASK_COST_USD
        or accumulated_tokens >= settings.MAX_TASK_TOKENS
    )

    duration_ms = int((time.time() - start_ts) * 1000)

    # Build stepper trace
    strat_snippet = str(candidate_exp.get("strategy_lesson") or "")[:70]
    pit_snippet = str(candidate_exp.get("pitfall") or "")[:70]
    trace = {
        "id": f"step_reflect_{int(start_ts)}",
        "type": "reflection",
        "node": "reflect_node",
        "title": "Structured Experience Distillation",
        "detail": (
            f"Distilled candidate experience tuple for domain '{domain}'. "
            f"Strategy: '{strat_snippet}...'. "
            f"Pitfall: '{pit_snippet}...'. "
            f"Tokens consumed: {step_tokens} (cost: ${step_cost:.5f})."
        ),
        "durationMs": duration_ms,
        "metadata": {
            "candidate": candidate_exp,
            "tokensUsed": step_tokens,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "stepCostUsd": step_cost,
            "totalCostUsd": accumulated_cost,
            "budgetExceeded": is_budget_exceeded,
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    return {
        "candidate_experience": candidate_exp,
        "new_experience_created": candidate_exp is not None,
        "trajectory": trajectory,
        "tokens_used": accumulated_tokens,
        "prompt_tokens": accumulated_prompt_tokens,
        "completion_tokens": accumulated_completion_tokens,
        "total_cost_usd": accumulated_cost,
        "cost_usd": accumulated_cost,
        "budget_exceeded": is_budget_exceeded,
        "status": "updating_trust",
    }

