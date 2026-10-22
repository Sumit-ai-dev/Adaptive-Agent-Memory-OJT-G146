"""
LangGraph 5-Node Cyclical Cognitive Architecture Assembler.
Compiles the stateful StateGraph:
  START -> retrieve_node -> execute_node -> evaluate_node -> reflect_node -> trust_node
With conditional self-healing loop: if R < 0.80 and loop < max_loops, route back to execute_node!
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from langgraph.graph import END, START, StateGraph

from ai_service.config import settings
from ai_service.nodes.evaluate_node import evaluate_node
from ai_service.nodes.execute_node import execute_node
from ai_service.nodes.reflect_node import reflect_node
from ai_service.nodes.retrieve_node import async_retrieve_node, retrieve_node
from ai_service.nodes.trust_node import async_trust_node, trust_node
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceMatch
from models.state import AgentState
from models.task import (
    DEFAULT_OUTCOME_THRESHOLD,
    AttemptRecord,
    ChatMessage,
    ExecutionMetadata,
    ExecutionStatus,
    ExecutionStepTrace,
    OutcomeQuality,
    TaskExecuteRequest,
    TaskExecution,
    TrustUpdateSummary,
)

logger = logging.getLogger("ai_service.graph")


def should_loop_or_finish(state: AgentState) -> str:
    """
    Cyclical routing decision:
    If the task failed (R < 0.80) and we haven't reached loop limit, re-execute with new constraints!
    """
    # If the execution encountered an infrastructure/provider error or is inconclusive, do not loop
    eval_details = state.get("evaluator_details") or {}
    if eval_details.get("status") == "inconclusive" or eval_details.get("error") in ("missing_test_code", "harness_error", "provider_error"):
        return END

    score = state.get("outcome_score", 1.0)
    loop_count = state.get("loop_count", 1)
    max_loops = state.get("max_loops", settings.MAX_CYCLICAL_LOOPS)

    if score < 0.80 and loop_count < max_loops:
        return "execute_node"
    return END


def build_agent_graph():
    """
    Builds and compiles the 5-node cyclical LangGraph StateGraph.
    """
    builder = StateGraph(AgentState)

    # 1. Add all 5 nodes
    builder.add_node("retrieve_node", async_retrieve_node)
    builder.add_node("execute_node", execute_node)
    builder.add_node("evaluate_node", evaluate_node)
    builder.add_node("reflect_node", reflect_node)
    builder.add_node("trust_node", async_trust_node)

    # 2. Add sequential pipeline edges
    builder.add_edge(START, "retrieve_node")
    builder.add_edge("retrieve_node", "execute_node")
    builder.add_edge("execute_node", "evaluate_node")
    builder.add_edge("evaluate_node", "reflect_node")
    builder.add_edge("reflect_node", "trust_node")

    # 3. Add cyclical conditional feedback edge from trust_node
    builder.add_conditional_edges(
        "trust_node",
        should_loop_or_finish,
        {
            "execute_node": "execute_node",
            END: END,
        },
    )

    return builder.compile()


# Compiled LangGraph instance
agent_graph = build_agent_graph()


def _record_run_evidence(
    run: Any,
    request: TaskExecuteRequest,
    final_state: Dict[str, Any],
    task_id: str,
    task_index: int,
    attempt_dicts: list,
    task_reward: float,
    task_binary: int,
    task_threshold: float,
    task_evaluator: Optional[str],
    total_latency_ms: int,
) -> None:
    """
    Step 1: apply exactly one task-level observation per exposed memory and append the
    corresponding append-only evidence.

    Trust state is written to the RUN, never to the memory bank. Memory content is
    untouched regardless of outcome.
    """
    from ai_service.experiment.evidence import AttemptEvidence, ExposureRecord
    from ai_service.experiment.run_context import params_hash
    from ai_service.trust.base import Observation

    retrieved = final_state.get("retrieved_memories") or []
    attempts_ev = [
        AttemptEvidence(
            attempt_index=a["attempt_index"],
            reward=a["reward"],
            binary_outcome=a["binary_outcome"],
            outcome_threshold=a["outcome_threshold"],
            evaluator_name=a.get("evaluator_name"),
            tokens_used=a.get("tokens_used", 0),
            is_terminal=a.get("is_terminal", False),
        )
        for a in attempt_dicts
    ]
    pp_hash = params_hash(dict(run.policy.params))
    common = dict(
        run_id=run.run_id,
        task_id=task_id,
        task_index=task_index,
        condition_id=run.condition_id,
        policy_name=run.policy.name,
        policy_params_hash=pp_hash,
        bank_hash=run.bank.bank_hash,
        domain=request.task_domain.value if hasattr(request.task_domain, "value") else str(request.task_domain),
        reward=task_reward,
        binary_outcome=task_binary,
        outcome_threshold=task_threshold,
        evaluator_name=task_evaluator,
        n_attempts=len(attempts_ev),
        attempts=attempts_ev,
        prompt_tokens=int(final_state.get("tokens_used", 0) or 0),
        latency_ms=total_latency_ms,
        # Baseline is written at record-creation time from an OBSERVED E0 execution,
        # so historical records are never mutated after the fact. Stays None when no
        # E0 result exists -- it is never estimated.
        stateless_reward=run.baseline_reward,
        stateless_binary=run.baseline_binary,
    )

    if not retrieved:
        # No memory injected: still logged, so fallback is explicit rather than inferred.
        run.exposures.append(ExposureRecord(
            memory_id=None,
            exposure_id=f"{task_id}:none",
            fallback_occurred=True,
            injected=False,
            **common,
        ))
        return

    seen: set[str] = set()
    for item in retrieved:
        exp = item.get("experience", {})
        mem_id = exp.get("id")
        if not mem_id or mem_id in seen:
            continue
        seen.add(mem_id)

        observation = Observation(
            memory_id=mem_id,
            task_id=task_id,
            run_id=run.run_id,
            task_index=task_index,
            reward=task_reward,
            binary_outcome=task_binary,
            outcome_threshold=task_threshold,
            similarity=item.get("similarityScore"),
            domain=common["domain"],
            evaluator_name=task_evaluator,
        )
        before, after = run.trust_state.apply(observation)

        record = run.bank.get(mem_id)
        run.exposures.append(ExposureRecord(
            memory_id=mem_id,
            exposure_id=f"{task_id}:{mem_id}",
            memory_content_hash=record.content_hash if record else None,
            similarity=item.get("similarityScore"),
            composite_score=item.get("compositeScore"),
            candidate_count=len(run.bank),
            admissible_count=len(retrieved),
            passed_trust_gate=True,
            gate_reason=item.get("gateReason", ""),
            fallback_occurred=False,
            injected=True,
            policy_state_before=before.to_dict(),
            policy_state_after=after.to_dict(),
            **common,
        ))


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    """Formats an event and payload into valid SSE text/event-stream message format."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _build_initial_state(
    request: TaskExecuteRequest,
    memory_store: Optional[Any] = None,
    run_context: Optional[Any] = None,
) -> Tuple[AgentState, str, str, int, float]:
    """Constructs the initial AgentState, correlation IDs, and timing for graph execution."""
    start_time = time.time()
    exec_id = f"exec_{uuid.uuid4().hex[:8]}"
    task_id = f"task_{uuid.uuid4().hex[:8]}"

    # Step 1: when a RunContext is supplied, retrieval and trust state are run-scoped.
    policy_retriever = None
    task_index = 0
    if run_context is not None:
        from ai_service.experiment.retrieval import PolicyBackedRetriever

        policy_retriever = PolicyBackedRetriever(run=run_context, ranker=run_context.ranker)
        task_index = run_context.next_task_index()

    # Format conversational history messages if supplied
    history_messages: List[Dict[str, str]] = []
    if request.messages:
        for m in request.messages:
            history_messages.append({"role": m.role, "content": m.content})

    initial_state: AgentState = {
        "execution_id": exec_id,
        "task_id": task_id,
        "session_id": request.session_id,
        "task_input": request.task_input,
        "messages": history_messages,
        "task_domain": request.task_domain.value if hasattr(request.task_domain, "value") else str(request.task_domain),
        "memory_enabled": request.memory_enabled,
        "memory_mode": request.memory_mode.value if hasattr(request.memory_mode, "value") else str(request.memory_mode),
        "provider": request.provider.value if request.provider and hasattr(request.provider, "value") else request.provider,
        "model": request.model,
        "api_key": request.api_key,
        "memory_store": memory_store,
        "policy_retriever": policy_retriever,
        "top_k": run_context.top_k if run_context is not None else 2,
        "temperature": (
            run_context.temperature if run_context is not None else request.temperature
        ),
        "seed": run_context.seed if run_context is not None else request.seed,
        "max_tokens": (
            run_context.max_tokens if run_context is not None else request.max_tokens
        ),
        "evaluator": request.evaluator.value if request.evaluator is not None else None,
        "evaluator_config": dict(request.evaluator_config or {}),
        "outcome_threshold": (
            run_context.requested_outcome_threshold if run_context is not None
            else request.outcome_threshold
        ),
        "retrieved_memories": [],
        "tool_calls": [],
        "trajectory": [],
        "attempts": [],
        "tokens_used": 0,
        "loop_count": 0,
        "max_loops": settings.MAX_CYCLICAL_LOOPS,
        "start_time": start_time,
        "status": "starting",
    }
    return initial_state, exec_id, task_id, task_index, start_time


async def _finalize_execution(
    final_state: Dict[str, Any],
    request: TaskExecuteRequest,
    memory_store: Optional[Any],
    run_context: Optional[Any],
    exec_id: str,
    task_id: str,
    task_index: int,
    start_time: float,
) -> TaskExecution:
    """Persists outcomes and packages the final AgentState into a typed TaskExecution object."""
    total_latency_ms = int((time.time() - start_time) * 1000)

    attempt_dicts = list(final_state.get("attempts", []))
    for a in attempt_dicts:
        a["is_terminal"] = False
    if attempt_dicts:
        attempt_dicts[-1]["is_terminal"] = True
        terminal = attempt_dicts[-1]
        task_reward = float(terminal["reward"])
        task_binary = int(terminal["binary_outcome"])
        task_threshold = float(terminal["outcome_threshold"])
        task_evaluator = terminal.get("evaluator_name")
        terminal_details = terminal.get("details") or {}
    else:
        task_reward = float(final_state.get("outcome_score", 0.0) or 0.0)
        task_threshold = float(final_state.get("outcome_threshold") or DEFAULT_OUTCOME_THRESHOLD)
        task_binary = 1 if task_reward >= task_threshold else 0
        task_evaluator = final_state.get("evaluator_name")
        terminal_details = final_state.get("evaluator_details") or {}

    attempt_records = [AttemptRecord(**a) for a in attempt_dicts]

    raw_trust_updates = list(final_state.get("trust_updates", []))

    if run_context is not None:
        _record_run_evidence(
            run=run_context,
            request=request,
            final_state=final_state,
            task_id=task_id,
            task_index=task_index,
            attempt_dicts=attempt_dicts,
            task_reward=task_reward,
            task_binary=task_binary,
            task_threshold=task_threshold,
            task_evaluator=task_evaluator,
            total_latency_ms=total_latency_ms,
        )
        for u in raw_trust_updates:
            u["persisted"] = True

        new_exp_obj = final_state.get("new_experience")
        if new_exp_obj is not None and run_context.memory_write_enabled and memory_store is not None:
            try:
                await memory_store.add_experience(new_exp_obj)
            except Exception:
                logger.error("Failed to persist candidate experience.", exc_info=True)

    elif memory_store is not None:
        is_inconclusive = (
            terminal_details.get("status") == "inconclusive"
            or terminal_details.get("error") in ("missing_test_code", "harness_error", "provider_error")
        )

        seen_experience_ids: set[str] = set()
        for u in raw_trust_updates:
            exp_id = u.get("experienceId")
            if not exp_id or exp_id in seen_experience_ids:
                continue
            seen_experience_ids.add(exp_id)
            try:
                await memory_store.update_trust(
                    experience_id=exp_id,
                    new_trust=float(u.get("newScore", 0.75)),
                    reason=u.get("reason"),
                    execution_id=task_id,
                    binary_outcome=None if is_inconclusive else task_binary,
                )
                u["persisted"] = True
            except Exception:
                logger.error(
                    "Failed to persist task-level trust update for experience '%s'.",
                    exp_id,
                    exc_info=True,
                )

        for step in final_state.get("trajectory", []):
            if step.get("node") == "trust_node" and step.get("metadata", {}).get("trustUpdates"):
                for upd in step["metadata"]["trustUpdates"]:
                    if upd.get("experienceId") in seen_experience_ids:
                        upd["persisted"] = True

        new_exp_obj = final_state.get("new_experience")
        if new_exp_obj is not None:
            try:
                await memory_store.add_experience(new_exp_obj)
            except Exception:
                logger.error("Failed to persist candidate experience.", exc_info=True)

    # Format trajectory step traces
    traces = []
    for t in final_state.get("trajectory", []):
        traces.append(ExecutionStepTrace(
            id=t.get("id", str(uuid.uuid4())),
            type=t.get("type", "thought"),
            node=t.get("node"),
            title=t.get("title", ""),
            detail=t.get("detail", ""),
            duration_ms=t.get("durationMs"),
            tools_called=t.get("toolsCalled"),
            metadata=t.get("metadata"),
        ))

    trust_updates = []
    for u in raw_trust_updates:
        trust_updates.append(TrustUpdateSummary(
            experience_id=u.get("experienceId", ""),
            old_score=float(u.get("oldScore", 0.75)),
            new_score=float(u.get("newScore", 0.75)),
            delta=float(u.get("delta", 0.0)),
            status=u.get("status"),
        ))

    retrieved_exp_matches = []
    for item in final_state.get("retrieved_memories", []):
        try:
            if isinstance(item, ExperienceMatch):
                retrieved_exp_matches.append(item)
            elif isinstance(item, dict):
                exp_data = item.get("experience", {})
                sim = float(item.get("similarityScore", item.get("similarity", 0.0)))
                comp = float(item.get("compositeScore", item.get("composite_score", sim)))
                if isinstance(exp_data, dict):
                    exp_obj = Experience.model_validate(exp_data)
                elif isinstance(exp_data, Experience):
                    exp_obj = exp_data
                else:
                    continue
                retrieved_exp_matches.append(ExperienceMatch(
                    experience=exp_obj,
                    similarity=sim,
                    composite_score=comp,
                ))
        except Exception:
            logger.warning("Could not convert retrieved memory item to ExperienceMatch", exc_info=True)

    score = task_reward
    if score >= 0.80:
        quality = OutcomeQuality.POSITIVE
    elif score >= 0.50:
        quality = OutcomeQuality.NEUTRAL
    else:
        quality = OutcomeQuality.NEGATIVE

    final_messages: list[ChatMessage] = []
    for m in final_state.get("messages", []):
        if isinstance(m, dict) and "role" in m and "content" in m:
            try:
                final_messages.append(ChatMessage(role=m["role"], content=m["content"]))
            except Exception:
                pass

    return TaskExecution(
        id=exec_id,
        execution_id=exec_id,
        task_id=task_id,
        session_id=request.session_id,
        messages=final_messages,
        task_input=request.task_input,
        task_domain=request.task_domain,
        memory_enabled=request.memory_enabled,
        memory_mode=request.memory_mode,
        status=ExecutionStatus.COMPLETED,
        final_output=final_state.get("final_answer"),
        final_answer=final_state.get("final_answer"),
        reflection_lesson=final_state.get("candidate_experience", {}).get("strategy_lesson") if final_state.get("candidate_experience") else None,
        new_experience_created=final_state.get("new_experience_created", False),
        new_experience=final_state.get("new_experience"),
        retrieved_experiences=retrieved_exp_matches,
        retrieved_memories=final_state.get("retrieved_memories", []),
        trust_updates=trust_updates,
        trajectory=traces,
        tokens_used=final_state.get("tokens_used", 120),
        latency_ms=total_latency_ms,
        outcome_quality=quality,
        outcome_score=score,
        binary_outcome=task_binary,
        outcome_threshold=task_threshold,
        evaluator_name=task_evaluator,
        evaluator_version=final_state.get("evaluator_version"),
        evaluator_details=terminal_details or final_state.get("evaluator_details") or {},
        attempts=attempt_records,
        n_attempts=len(attempt_records),
        execution_metadata=ExecutionMetadata(
            latency_ms=total_latency_ms,
            steps_count=len(traces),
            tool_calls_count=len(final_state.get("tool_calls", [])),
            outcome_score=score,
            tokens_used=final_state.get("tokens_used", 120),
            loop_count=final_state.get("loop_count", 1),
        ),
    )


async def execute_task(
    request: TaskExecuteRequest,
    memory_store: Optional[Any] = None,
    run_context: Optional[Any] = None,
) -> TaskExecution:
    """
    High-level entry point to execute an agent task through the compiled LangGraph.
    Returns complete TaskExecution record compatible with both REST API and React dashboard.
    """
    initial_state, exec_id, task_id, task_index, start_time = _build_initial_state(
        request, memory_store, run_context
    )

    final_state = await agent_graph.ainvoke(initial_state)

    return await _finalize_execution(
        final_state=final_state,
        request=request,
        memory_store=memory_store,
        run_context=run_context,
        exec_id=exec_id,
        task_id=task_id,
        task_index=task_index,
        start_time=start_time,
    )


async def execute_task_stream(
    request: TaskExecuteRequest,
    memory_store: Optional[Any] = None,
    run_context: Optional[Any] = None,
) -> AsyncGenerator[str, None]:
    """
    Streams task execution through the 5-node LangGraph cognitive cycle using Server-Sent Events (SSE).
    Yields real-time events for node transitions, token chunks, empirical verification, and final execution.
    """
    initial_state, exec_id, task_id, task_index, start_time = _build_initial_state(
        request, memory_store, run_context
    )

    yield _format_sse("start", {
        "execution_id": exec_id,
        "task_id": task_id,
        "session_id": request.session_id,
        "task_input": request.task_input,
        "task_domain": request.task_domain.value if hasattr(request.task_domain, "value") else str(request.task_domain),
        "memory_enabled": request.memory_enabled,
        "memory_mode": request.memory_mode.value if hasattr(request.memory_mode, "value") else str(request.memory_mode),
    })

    running_state: Dict[str, Any] = dict(initial_state)

    try:
        async for chunk in agent_graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                running_state.update(node_update)

                if node_name == "retrieve_node":
                    retrieved = node_update.get("retrieved_memories", [])
                    yield _format_sse("node_complete", {
                        "node": "retrieve_node",
                        "title": "Memory Retrieval",
                        "retrieved_count": len(retrieved),
                        "retrieved_memories": retrieved,
                        "positive_strategy": node_update.get("positive_strategy"),
                        "negative_pitfall": node_update.get("negative_pitfall"),
                    })

                elif node_name == "execute_node":
                    solution = node_update.get("final_answer") or node_update.get("solution") or ""
                    # Stream token chunks for responsive live typing effect
                    if solution:
                        words = solution.split(" ")
                        chunk_size = 2
                        for i in range(0, len(words), chunk_size):
                            part = " ".join(words[i : i + chunk_size]) + (" " if i + chunk_size < len(words) else "")
                            yield _format_sse("token", {"chunk": part})
                            await asyncio.sleep(0.01)

                    yield _format_sse("node_complete", {
                        "node": "execute_node",
                        "title": "Task Execution",
                        "final_answer": solution,
                        "tool_calls": node_update.get("tool_calls", []),
                    })

                elif node_name == "evaluate_node":
                    score = node_update.get("outcome_score", 0.0)
                    yield _format_sse("node_complete", {
                        "node": "evaluate_node",
                        "title": "Empirical Verification",
                        "outcome_score": score,
                        "evaluator_name": node_update.get("evaluator_name"),
                        "evaluator_details": node_update.get("evaluator_details", {}),
                    })

                elif node_name == "reflect_node":
                    cand = node_update.get("candidate_experience") or {}
                    yield _format_sse("node_complete", {
                        "node": "reflect_node",
                        "title": "Experiential Reflection",
                        "candidate_experience": cand,
                    })

                elif node_name == "trust_node":
                    updates = node_update.get("trust_updates", [])
                    yield _format_sse("node_complete", {
                        "node": "trust_node",
                        "title": "Trust Calibration",
                        "trust_updates": updates,
                    })

        final_execution = await _finalize_execution(
            final_state=running_state,
            request=request,
            memory_store=memory_store,
            run_context=run_context,
            exec_id=exec_id,
            task_id=task_id,
            task_index=task_index,
            start_time=start_time,
        )

        yield _format_sse("done", {
            "execution_id": exec_id,
            "status": "completed",
            "result": final_execution.model_dump(by_alias=True),
        })

    except Exception as exc:
        logger.error("Error during streaming execution in graph: %s", exc, exc_info=True)
        yield _format_sse("error", {"message": str(exc), "execution_id": exec_id})
