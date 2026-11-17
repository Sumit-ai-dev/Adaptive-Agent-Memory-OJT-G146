"""
Distributed Tracing, Observability & Token Cost Tracking Engine.
Author: Sakshi Kasat (Memory Intelligence & Trust Lead)

Provides production-grade OpenTelemetry and Langfuse distributed tracing integration
for the 5-node cyclical LangGraph cognitive workflow:
    retrieve_node -> execute_node -> evaluate_node -> reflect_node -> trust_node

Key Capabilities:
1. Wraps LangGraph execution with Langfuse CallbackHandler when configured.
2. Captures granular node execution spans, latencies, token counts, and USD costs.
3. Provides deterministic fail-safe fallback when credentials are absent or offline.
4. Generates direct web URLs to execution traces on the observability dashboard.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from ai_service.config import settings

logger = logging.getLogger("ai_service.observability.tracer")

# Graceful dynamic import for Langfuse
try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler
except ImportError:
    LangfuseCallbackHandler = None

# Graceful dynamic import for LangSmith
try:
    from langchain_core.tracers import LangChainTracer
except ImportError:
    LangChainTracer = None


class ObservabilityTracer:
    """
    Manages distributed tracing lifecycle, Langfuse/LangSmith callbacks,
    and granular per-node span telemetry for LangGraph executions.
    """

    def __init__(
        self,
        task_id: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        callback_handler: Optional[Any] = None,
        langsmith_handler: Optional[Any] = None,
    ) -> None:
        self.task_id = task_id
        self.session_id = session_id
        self.user_id = user_id
        self.metadata = dict(metadata or {})
        self.tags = list(tags or [])
        self.start_ts = time.time()
        self.node_spans: Dict[str, Dict[str, Any]] = {}
        self.node_latencies_ms: Dict[str, int] = {}
        self.langfuse_handler = callback_handler
        self.langsmith_handler = langsmith_handler

        # Derive trace ID and trace URL
        if self.langfuse_handler is not None and hasattr(self.langfuse_handler, "get_trace_id"):
            try:
                self.trace_id = self.langfuse_handler.get_trace_id() or f"trace_{task_id}"
            except Exception:
                self.trace_id = f"trace_{task_id}"
        else:
            self.trace_id = f"trace_{task_id}_{uuid.uuid4().hex[:6]}"

        # Only construct remote trace URL when a valid collector handler was actually initialized
        if self.langfuse_handler is not None:
            if hasattr(self.langfuse_handler, "get_trace_url"):
                try:
                    self.trace_url = self.langfuse_handler.get_trace_url()
                except Exception:
                    self.trace_url = None
            else:
                self.trace_url = None

            if not self.trace_url and settings.LANGFUSE_HOST and settings.LANGFUSE_PUBLIC_KEY:
                host_clean = settings.LANGFUSE_HOST.rstrip("/")
                self.trace_url = f"{host_clean}/project/default/traces/{self.trace_id}"
        else:
            # Without an active remote trace handler, returning a link to an uncreated trace is misleading.
            self.trace_url = None

    def get_callbacks(self) -> List[Any]:
        """
        Returns list of callback handlers to inject into LangGraph StateGraph config.
        """
        callbacks: List[Any] = []
        if self.langfuse_handler is not None:
            callbacks.append(self.langfuse_handler)
        if self.langsmith_handler is not None:
            callbacks.append(self.langsmith_handler)
        return callbacks

    def record_node_span(
        self,
        node_name: str,
        duration_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        step_cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Records node execution duration and resource expenditure.
        Accumulates duration, token usage, and cost across cyclical loop retries.
        """
        prev_latency = self.node_latencies_ms.get(node_name, 0)
        accumulated_duration = prev_latency + duration_ms
        self.node_latencies_ms[node_name] = accumulated_duration

        prev_span = self.node_spans.get(node_name, {})
        prev_prompt = prev_span.get("promptTokens", 0)
        prev_comp = prev_span.get("completionTokens", 0)
        prev_cost = prev_span.get("stepCostUsd", 0.0)
        prev_visits = prev_span.get("visits", 0)

        self.node_spans[node_name] = {
            "durationMs": accumulated_duration,
            "promptTokens": prev_prompt + prompt_tokens,
            "completionTokens": prev_comp + completion_tokens,
            "totalTokens": prev_prompt + prev_comp + prompt_tokens + completion_tokens,
            "stepCostUsd": round(prev_cost + step_cost_usd, 6),
            "visits": prev_visits + 1,
            "metadata": metadata or {},
        }

    def finish_trace(
        self,
        status: str = "completed",
        outcome_score: Optional[float] = None,
        total_tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Finalizes trace metadata and returns consolidated observability summary.
        """
        duration_ms = int((time.time() - self.start_ts) * 1000)
        summary = {
            "traceId": self.trace_id,
            "traceUrl": self.trace_url,
            "status": status,
            "durationMs": duration_ms,
            "outcomeScore": outcome_score,
            "tokensUsed": total_tokens,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalCostUsd": total_cost_usd,
            "nodeLatenciesMs": dict(self.node_latencies_ms),
        }
        self.flush()
        return summary

    def flush(self) -> None:
        """
        Safely flushes buffered spans to remote collectors without raising exceptions.
        """
        if self.langfuse_handler is not None and hasattr(self.langfuse_handler, "flush"):
            try:
                self.langfuse_handler.flush()
            except Exception as e:
                logger.debug(f"Langfuse flush caught non-fatal exception: {e}")

        if self.langsmith_handler is not None and hasattr(self.langsmith_handler, "wait_for_futures"):
            try:
                self.langsmith_handler.wait_for_futures()
            except Exception as e:
                logger.debug(f"LangSmith flush caught non-fatal exception: {e}")


def create_task_tracer(
    task_id: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    task_domain: Optional[str] = None,
    memory_mode: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> ObservabilityTracer:
    """
    Factory function to initialize an ObservabilityTracer for an agent execution.
    Inspects environment settings and initializes Langfuse/LangSmith callback handlers if configured.
    Falls back gracefully to local non-blocking telemetry when unconfigured.
    """
    if not settings.OBSERVABILITY_ENABLED:
        logger.debug("Observability tracing is disabled via settings.")
        return ObservabilityTracer(task_id=task_id, session_id=session_id, user_id=user_id)

    combined_metadata: Dict[str, Any] = dict(metadata or {})
    if task_domain:
        combined_metadata["task_domain"] = task_domain
    if memory_mode:
        combined_metadata["memory_mode"] = memory_mode
    if provider:
        combined_metadata["provider"] = provider
    if model:
        combined_metadata["model"] = model

    combined_tags: List[str] = list(tags or [])
    if task_domain and task_domain not in combined_tags:
        combined_tags.append(task_domain)
    if memory_mode and memory_mode not in combined_tags:
        combined_tags.append(memory_mode)

    handler = None
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        if LangfuseCallbackHandler is not None:
            try:
                handler = LangfuseCallbackHandler(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                    session_id=session_id,
                    user_id=user_id,
                    tags=combined_tags,
                    metadata=combined_metadata,
                )
                logger.info(f"Initialized Langfuse callback handler for task '{task_id}'.")
            except Exception as e:
                logger.warning(f"Could not initialize LangfuseCallbackHandler ({e}). Falling back to local tracing.")
                handler = None
        else:
            logger.debug("Langfuse package is not installed; operating in local tracing mode.")

    langsmith_handler = None
    if settings.LANGSMITH_TRACING:
        if settings.LANGSMITH_API_KEY:
            import os
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            if settings.LANGSMITH_PROJECT:
                os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        if LangChainTracer is not None:
            try:
                langsmith_handler = LangChainTracer(
                    project_name=settings.LANGSMITH_PROJECT or "default",
                )
                logger.info(f"Initialized LangSmith tracer for task '{task_id}'.")
            except Exception as e:
                logger.warning(f"Could not initialize LangChainTracer ({e}).")
                langsmith_handler = None
        else:
            logger.debug("LangChainTracer is not installed; operating in local tracing mode.")

    return ObservabilityTracer(
        task_id=task_id,
        session_id=session_id,
        user_id=user_id,
        metadata=combined_metadata,
        tags=combined_tags,
        callback_handler=handler,
        langsmith_handler=langsmith_handler,
    )
