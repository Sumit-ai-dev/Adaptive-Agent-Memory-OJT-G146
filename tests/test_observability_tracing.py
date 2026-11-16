"""
Unit and Integration Tests for Distributed Tracing & Token Cost Tracking (Issue #36).
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)
"""

from unittest.mock import MagicMock, patch
import pytest

from ai_service.config import settings
from ai_service.graph import execute_task
from ai_service.observability.tracer import (
    ObservabilityTracer,
    create_task_tracer,
)
from models.domain import MemoryMode, TaskDomain
from models.provider import ModelProvider
from models.task import ExecutionStatus, TaskExecuteRequest


def test_tracer_fallback_mode_when_unconfigured():
    """Observability tracer operates with zero overhead when Langfuse keys are absent."""
    tracer = create_task_tracer(
        task_id="task_test_123",
        session_id="session_456",
        task_domain="coding",
        memory_mode="adaptive",
        provider="mock",
        model="mock",
    )

    assert tracer.task_id == "task_test_123"
    assert tracer.trace_id.startswith("trace_task_test_123")
    assert tracer.trace_url is None
    assert tracer.get_callbacks() == []

    tracer.record_node_span("retrieve_node", duration_ms=45, prompt_tokens=0, completion_tokens=0)
    tracer.record_node_span("execute_node", duration_ms=120, prompt_tokens=50, completion_tokens=25, step_cost_usd=0.0001)

    summary = tracer.finish_trace(
        status="completed",
        outcome_score=0.95,
        total_tokens=75,
        prompt_tokens=50,
        completion_tokens=25,
        total_cost_usd=0.0001,
    )

    assert summary["traceId"] == tracer.trace_id
    assert summary["status"] == "completed"
    assert summary["tokensUsed"] == 75
    assert summary["nodeLatenciesMs"]["retrieve_node"] == 45
    assert summary["nodeLatenciesMs"]["execute_node"] == 120


def test_tracer_with_mock_langfuse_callback():
    """Tracer attaches Langfuse callback handler and resolves trace ID and dashboard URL."""
    mock_handler = MagicMock()
    mock_handler.get_trace_id.return_value = "lf_trace_abc123"
    mock_handler.get_trace_url.return_value = "https://cloud.langfuse.com/project/proj_1/traces/lf_trace_abc123"

    tracer = ObservabilityTracer(
        task_id="task_test_lf",
        session_id="sess_1",
        callback_handler=mock_handler,
    )

    assert tracer.trace_id == "lf_trace_abc123"
    assert tracer.trace_url == "https://cloud.langfuse.com/project/proj_1/traces/lf_trace_abc123"
    assert tracer.get_callbacks() == [mock_handler]

    tracer.flush()
    mock_handler.flush.assert_called_once()


def test_tracer_flush_swallows_collector_network_errors():
    """Remote telemetry transport errors during flush do not crash the agent pipeline."""
    mock_handler = MagicMock()
    mock_handler.flush.side_effect = RuntimeError("Langfuse server timeout 504")

    tracer = ObservabilityTracer(
        task_id="task_test_err",
        callback_handler=mock_handler,
    )

    # Must complete safely without propagating RuntimeError
    tracer.flush()


def test_tracer_cloud_url_construction_when_keys_present():
    """Tracer generates standard cloud trace URL when credentials exist even if SDK handler is absent."""
    with patch.object(settings, "LANGFUSE_PUBLIC_KEY", "pk-lf-test"), \
         patch.object(settings, "LANGFUSE_SECRET_KEY", "sk-lf-test"), \
         patch.object(settings, "LANGFUSE_HOST", "https://cloud.langfuse.com"):
        tracer = create_task_tracer(
            task_id="task_cloud_test",
            task_domain="reasoning",
        )
        assert tracer.trace_url is not None
        assert "cloud.langfuse.com" in tracer.trace_url
        assert tracer.trace_id in tracer.trace_url


def test_tracer_disabled_via_settings():
    """Tracer returns empty no-op handler when OBSERVABILITY_ENABLED is false."""
    with patch.object(settings, "OBSERVABILITY_ENABLED", False):
        tracer = create_task_tracer(task_id="task_disabled")
        assert tracer.get_callbacks() == []
        assert tracer.trace_url is None


@pytest.mark.asyncio
async def test_end_to_end_execution_populates_observability_metadata():
    """End-to-end task execution emits distributed trace identifiers and node latencies."""
    req = TaskExecuteRequest(
        task_input="Write a python function to compute fibonacci sequence",
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.OFF,
        provider="mock",
        model="mock",
    )

    execution = await execute_task(req, memory_store=None)

    # Verify TaskExecution level trace fields
    assert execution.trace_id is not None
    assert execution.trace_id.startswith("trace_")
    assert execution.status == ExecutionStatus.COMPLETED

    # Verify ExecutionMetadata level trace fields and granular node spans
    meta = execution.execution_metadata
    assert meta is not None
    assert meta.trace_id == execution.trace_id
    assert isinstance(meta.node_latencies_ms, dict)
    # The 5 nodes in the execution cycle must be tracked in node_latencies_ms
    assert "retrieve_node" in meta.node_latencies_ms
    assert "execute_node" in meta.node_latencies_ms
    assert "evaluate_node" in meta.node_latencies_ms
    assert "reflect_node" in meta.node_latencies_ms
    assert "trust_node" in meta.node_latencies_ms

    for node_name in ["retrieve_node", "execute_node", "evaluate_node", "reflect_node", "trust_node"]:
        assert meta.node_latencies_ms[node_name] >= 0

    # Verify token breakdown and cost
    assert meta.prompt_tokens > 0
    assert meta.completion_tokens > 0
    assert meta.total_cost_usd >= 0.0
