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

from ai_service.llm_client import llm_gateway, resolve_provider_config
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

    # Formulate System Prompt with Bilateral Constraints
    system_prompt_parts = [
        "You are an elite, proactive autonomous language agent with persistent experiential memory.",
        "Solve the user's task rigorously, providing accurate, verifiable, and structured answers.",
    ]

    if positive_strategy:
        system_prompt_parts.append(
            f"\n[VERIFIED OPERATIONAL STRATEGY (+sigma)]:\n{positive_strategy}"
        )

    if negative_pitfall:
        system_prompt_parts.append(
            f"\n[CRITICAL NEGATIVE CONSTRAINT - AVOID (-pi)]:\n"
            f"Under NO circumstances should you commit the following known pitfall: {negative_pitfall}"
        )

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
            f"Tokens consumed: {tokens}."
        ),
        "durationMs": duration_ms,
        "toolsCalled": tools_called_names,
        "metadata": {
            "loopCount": loop_count,
            "tokensUsed": tokens,
            "hasStrategy": positive_strategy is not None,
            "hasPitfall": negative_pitfall is not None,
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    accumulated_tokens = state.get("tokens_used", 0) + tokens

    updated_messages = list(messages)
    updated_messages.append({"role": "assistant", "content": final_answer})

    return {
        "final_answer": final_answer,
        "tool_calls": tool_calls,
        "tokens_used": accumulated_tokens,
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
