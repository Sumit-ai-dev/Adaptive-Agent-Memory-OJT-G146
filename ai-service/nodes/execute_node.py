"""
LangGraph Node 2: Task Execution Engine (execute_node.py)

Injects bilateral experience constraints into the prompt:
    - Positive Strategy (+sigma): verified successful actions from top memories.
    - Negative Pitfall (-pi): critical operational errors to avoid.
Dispatches generation through the Universal BYOK LLM gateway (Groq, Gemini, Ollama, OpenAI, or Mock).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_service.nodes.execute_node")

from ai_service.config import settings
from ai_service.context.compactor import compact_memory_context
from ai_service.context.token_budget import calculate_token_cost, count_tokens
from ai_service.llm_client import llm_gateway, resolve_provider_config
from ai_service.security import (
    detect_prompt_injection_heuristic,
    format_bilateral_constraints,
    security_audit_logger,
)
from models.provider import ModelProvider, ProviderConfig
from models.state import AgentState

try:
    from ai_service.tools.search import search_tool
except ImportError:
    search_tool = None


async def execute_node(state: AgentState | Dict[str, Any]) -> Dict[str, Any]:
    """
    Asynchronous LangGraph node function for task execution.
    Applies bilateral prompt constraints and routes execution through the LLM gateway.
    """
    start_ts = time.time()
    task_input = state.get("task_input", "")
    positive_strategy = state.get("positive_strategy")
    negative_pitfall = state.get("negative_pitfall")
    loop_count = state.get("loop_count", 0) + 1

    # Cumulative budget circuit breaker: abort if prior loops breached ceilings (Issue #38)
    prev_tokens = state.get("tokens_used", 0)
    prev_cost = state.get("total_cost_usd", 0.0)
    if prev_cost >= settings.MAX_TASK_COST_USD or prev_tokens >= settings.MAX_TASK_TOKENS:
        budget_err = (
            f"Execution halted by safety circuit breaker: Cumulative task expenditure exceeded budget "
            f"(${prev_cost:.4f} >= ${settings.MAX_TASK_COST_USD:.4f} or {prev_tokens} >= {settings.MAX_TASK_TOKENS} tokens)."
        )
        logger.warning(budget_err)
        trace = {
            "id": f"step_execute_cost_breaker_{int(start_ts)}",
            "type": "thought",
            "node": "execute_node",
            "title": "Cost/Token Circuit Breaker Tripped",
            "detail": budget_err,
            "durationMs": int((time.time() - start_ts) * 1000),
            "metadata": {
                "budgetExceeded": True,
                "tokensUsed": prev_tokens,
                "maxTaskTokens": settings.MAX_TASK_TOKENS,
                "totalCostUsd": prev_cost,
                "maxTaskCostUsd": settings.MAX_TASK_COST_USD,
            },
        }
        trajectory = list(state.get("trajectory", []))
        trajectory.append(trace)
        return {
            "final_answer": budget_err,
            "status": "failed",
            "budget_exceeded": True,
            "budget_error": budget_err,
            "tokens_used": prev_tokens,
            "total_cost_usd": prev_cost,
            "loop_count": loop_count,
            "trajectory": trajectory,
        }

    # Deterministic context compaction: guarantee injected memory <= MAX_RETRIEVED_MEMORY_TOKENS (800)
    comp_res = compact_memory_context(
        positive_strategy=positive_strategy,
        negative_pitfall=negative_pitfall,
        max_tokens=settings.MAX_RETRIEVED_MEMORY_TOKENS,
    )
    positive_strategy = comp_res.positive_strategy
    negative_pitfall = comp_res.negative_pitfall

    # Formulate System Prompt with Bilateral Constraints
    system_prompt_parts = [
        "You are an elite, proactive autonomous language agent with persistent experiential memory.",
        "Solve the user's task rigorously, providing accurate, verifiable, and structured answers.",
    ]

    # Heuristic prompt injection detection on task input (OWASP LLM01)
    has_injection, matched_pattern = detect_prompt_injection_heuristic(task_input)
    if has_injection:
        security_audit_logger.record_event(
            event_type="PROMPT_INJECTION_DETECTED",
            severity="MEDIUM",
            details={"pattern": matched_pattern, "source": "task_input"},
        )

    # Format bilateral memory injections with sanitized XML tags and reference boundaries
    constraint_sections = format_bilateral_constraints(
        positive_strategy=positive_strategy,
        negative_pitfall=negative_pitfall,
    )
    system_prompt_parts.extend(constraint_sections)

    system_prompt = "\n".join(system_prompt_parts)

    # Optional tool invocation for factual queries if search tool available
    tool_calls: List[Dict[str, Any]] = list(state.get("tool_calls", []))
    tools_called_names: List[str] = []

    if search_tool is not None and (
        "who" in task_input.lower()
        or "which" in task_input.lower()
        or "research" in str(state.get("task_domain", ""))
    ):
        try:
            search_res = await search_tool.execute(task_input)
            tool_calls.append(search_res)
            tools_called_names.append("duckduckgo_search")
            task_input_with_context = f"{task_input}\n\nSearch Context:\n{search_res.get('output', '')}"
        except Exception:
            task_input_with_context = task_input
    else:
        task_input_with_context = task_input

    # Build conversation history from state (preserving user/assistant sequence)
    conversation_history: List[Dict[str, str]] = []
    raw_history = state.get("messages", [])
    if raw_history:
        for msg in raw_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                role = str(msg["role"]).strip().lower()
                # Skip prior system messages from history so our fresh AEMA system prompt
                # with bilateral constraints (+sigma, -pi) remains authoritative at index 0.
                if role == "system":
                    continue
                conversation_history.append({"role": role, "content": str(msg["content"])})

    # Assemble prompt sequence:
    # 1. System prompt with AEMA bilateral constraints (+sigma, -pi)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # 2. Historical conversation messages (if any)
    # Check if the final message in conversation_history already matches task_input_with_context or task_input
    last_msg = conversation_history[-1] if conversation_history else None
    is_duplicate_user = (
        last_msg is not None
        and last_msg.get("role") == "user"
        and (
            last_msg.get("content") == task_input_with_context
            or last_msg.get("content") == task_input
        )
    )

    if not is_duplicate_user:
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": task_input_with_context})
    else:
        # History already ends with current user prompt; pass without duplicating
        messages.extend(conversation_history[:-1])
        messages.append({"role": "user", "content": task_input_with_context})

    # Calculate prompt tokens across all assembled messages
    prompt_tokens = sum(count_tokens(m.get("content", "")) for m in messages)

    # Prompt ceiling circuit breaker (Issue #38: MAX_PROMPT_TOKENS = 4096)
    if prompt_tokens > settings.MAX_PROMPT_TOKENS:
        # First attempt: dynamically compact conversation history if present
        if len(messages) > 2:
            logger.info("Prompt tokens (%d) exceed ceiling (%d). Truncating older history...", prompt_tokens, settings.MAX_PROMPT_TOKENS)
            # Retain system prompt (index 0) and final user prompt (index -1)
            messages = [messages[0], messages[-1]]
            prompt_tokens = sum(count_tokens(m.get("content", "")) for m in messages)

        # If still exceeding ceiling even after history pruning, trip circuit breaker
        if prompt_tokens > settings.MAX_PROMPT_TOKENS:
            budget_err = (
                f"Execution rejected by safety circuit breaker: Prompt context exceeded maximum allowable limit "
                f"({prompt_tokens} > {settings.MAX_PROMPT_TOKENS} tokens)."
            )
            logger.warning(budget_err)
            trace = {
                "id": f"step_execute_prompt_breaker_{int(start_ts)}",
                "type": "thought",
                "node": "execute_node",
                "title": "Prompt Token Ceiling Circuit Breaker Tripped",
                "detail": budget_err,
                "durationMs": int((time.time() - start_ts) * 1000),
                "metadata": {
                    "budgetExceeded": True,
                    "promptTokens": prompt_tokens,
                    "maxPromptTokens": settings.MAX_PROMPT_TOKENS,
                },
            }
            trajectory = list(state.get("trajectory", []))
            trajectory.append(trace)
            return {
                "final_answer": budget_err,
                "status": "failed",
                "budget_exceeded": True,
                "budget_error": budget_err,
                "tokens_used": prev_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": 0,
                "total_cost_usd": prev_cost,
                "loop_count": loop_count,
                "trajectory": trajectory,
                "messages": messages,
                "outcome_score": 0.0,
            }

    # S8: single shared resolver, so every call site in the graph dispatches with
    # the run's declared provider/model/temperature.
    provider_config, requested_temperature = resolve_provider_config(state)

    # Call Universal LLM Gateway with error-safe handling. Passing `temperature` explicitly overrides the
    # config default; passing None leaves the config/provider default in force.
    try:
        final_answer, tokens = await llm_gateway.generate(
            messages, config=provider_config, temperature=requested_temperature,
        )
    except Exception as e:
        logger.error(f"Universal LLM gateway call failed in execute_node: {e}", exc_info=True)
        final_answer = f"Execution encountered a model provider error: {str(e)}"
        tokens = 0

    completion_tokens = count_tokens(final_answer)
    step_tokens = tokens if tokens > 0 else (prompt_tokens + completion_tokens)

    # Compute USD cost for this step
    prov_name = provider_config.provider.value if provider_config and provider_config.provider else (state.get("provider") or "groq")
    mod_name = provider_config.model if provider_config and provider_config.model else (state.get("model") or "openai/gpt-oss-120b")
    step_cost = calculate_token_cost(
        provider=prov_name,
        model=mod_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    duration_ms = int((time.time() - start_ts) * 1000)

    # Build stepper telemetry trace
    trace = {
        "id": f"step_execute_{int(start_ts)}",
        "type": "action" if tools_called_names else "thought",
        "node": "execute_node",
        "title": f"Task Execution (Loop {loop_count})",
        "detail": (
            f"Executed reasoning with bilateral constraints (+strategy, -pitfall). "
            f"Tools called: {', '.join(tools_called_names) if tools_called_names else 'direct reasoning'}. "
            f"Tokens consumed: {step_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens}, cost: ${step_cost:.5f})."
        ),
        "durationMs": duration_ms,
        "toolsCalled": tools_called_names,
        "metadata": {
            "loopCount": loop_count,
            "tokensUsed": step_tokens,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "stepCostUsd": step_cost,
            "hasStrategy": positive_strategy is not None,
            "hasPitfall": negative_pitfall is not None,
            "wasMemoryCompacted": comp_res.was_compacted,
            "compactedMemoryTokens": comp_res.compacted_tokens,
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    accumulated_tokens = state.get("tokens_used", 0) + step_tokens
    accumulated_prompt_tokens = state.get("prompt_tokens", 0) + prompt_tokens
    accumulated_completion_tokens = state.get("completion_tokens", 0) + completion_tokens
    accumulated_cost = round(state.get("total_cost_usd", 0.0) + step_cost, 6)

    updated_messages = list(messages)
    updated_messages.append({"role": "assistant", "content": final_answer})

    return {
        "final_answer": final_answer,
        "tool_calls": tool_calls,
        "tokens_used": accumulated_tokens,
        "prompt_tokens": accumulated_prompt_tokens,
        "completion_tokens": accumulated_completion_tokens,
        "total_cost_usd": accumulated_cost,
        "cost_usd": accumulated_cost,
        "budget_exceeded": False,
        "loop_count": loop_count,
        "trajectory": trajectory,
        "messages": updated_messages,
        "status": "evaluating",
    }


def sync_execute_node(state: AgentState | Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper for execute_node for test harnesses and sync runners.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Running inside an active loop (e.g. jupyter, pytest-asyncio)
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(execute_node(state))
        finally:
            new_loop.close()
    else:
        return asyncio.run(execute_node(state))
