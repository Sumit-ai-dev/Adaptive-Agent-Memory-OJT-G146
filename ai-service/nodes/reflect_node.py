"""
LangGraph Node 4: reflect_node
Distills completed execution trajectories into structured procedural tuples:
  {trigger_condition, strategy_lesson, pitfall, confidence}
Saves candidate experiences into quarantine status for empirical validation.
"""

import json
import time
from typing import Any, Dict

from ai_service.config import settings
from ai_service.context.token_budget import calculate_token_cost, count_tokens
from ai_service.llm_client import llm_gateway, resolve_provider_config
from models.domain import TaskDomain
from models.experience import ExperienceStatus
from models.state import AgentState


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
        # Parse JSON
        parsed = json.loads(raw_json)
        candidate_exp = {
            "task_domain": domain,
            "trigger_condition": parsed.get("trigger_condition", f"Tasks similar to: {task_input[:50]}"),
            "strategy_lesson": parsed.get("strategy_lesson", "Follow verified step-by-step reasoning constraints."),
            "pitfall": parsed.get("pitfall", "Avoid relying on uncorroborated single-source facts."),
            "confidence": float(parsed.get("confidence", 0.85)),
            "status": ExperienceStatus.CANDIDATE.value,
        }
    except Exception:
        has_provider_error = True
        candidate_exp = {
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
    trace = {
        "id": f"step_reflect_{int(start_ts)}",
        "type": "reflection",
        "node": "reflect_node",
        "title": "Structured Experience Distillation",
        "detail": (
            f"Distilled candidate experience tuple for domain '{domain}'. "
            f"Strategy: '{candidate_exp['strategy_lesson'][:70]}...'. "
            f"Pitfall: '{candidate_exp['pitfall'][:70]}...'. "
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
