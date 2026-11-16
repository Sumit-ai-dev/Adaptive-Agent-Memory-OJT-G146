"""
Unit and Integration Tests for Automated LLM Regression Benchmarking Suite (Issue #37).
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)
"""

import pytest

from benchmarks.ci_eval_suite import (
    FROZEN_REGRESSION_TASKS,
    format_markdown_report,
    run_ci_eval_suite,
)
from models.domain import TaskDomain
from models.task import EvaluatorName, TaskExecuteRequest


def test_frozen_regression_tasks_structure():
    """Validates the 10 representative frozen regression tasks across categories."""
    assert len(FROZEN_REGRESSION_TASKS) == 10

    categories = [t["category"] for t in FROZEN_REGRESSION_TASKS]
    assert categories.count("coding") == 5
    assert categories.count("reasoning") == 3
    assert categories.count("tool_execution") == 2

    for t in FROZEN_REGRESSION_TASKS:
        assert "id" in t
        assert "name" in t
        assert "category" in t
        assert "domain" in t
        assert "evaluator" in t
        assert "input" in t
        assert "evaluator_config" in t
        assert isinstance(t["evaluator_config"], dict)


@pytest.mark.asyncio
async def test_run_ci_eval_suite_all_pass():
    """Runs the 10 frozen regression tasks with mock provider and asserts 100% pass rate."""
    report = await run_ci_eval_suite(
        provider="mock",
        model="mock",
        min_pass_rate=0.80,
    )

    assert report["totalTasks"] == 10
    assert report["passedTasks"] == 10
    assert report["failedTasks"] == 0
    assert report["passRate"] == 1.0
    assert report["isGatePassed"] is True
    assert report["avgLatencyMs"] > 0
    assert len(report["tasks"]) == 10

    for task_res in report["tasks"]:
        assert task_res["passed"] is True
        assert task_res["binaryOutcome"] == 1
        assert task_res["score"] >= 0.80
        assert task_res["latencyMs"] >= 0


@pytest.mark.asyncio
async def test_run_ci_eval_suite_threshold_breach():
    """Validates that isGatePassed is False when pass rate fails to meet strict threshold."""
    report = await run_ci_eval_suite(
        provider="mock",
        model="mock",
        min_pass_rate=1.05,  # Unattainable threshold
    )

    assert report["isGatePassed"] is False


def test_format_markdown_report():
    """Validates GitHub Flavored Markdown report structure and contents."""
    mock_report = {
        "timestamp": "2026-11-16T08:00:00Z",
        "provider": "mock",
        "model": "mock",
        "totalTasks": 10,
        "passedTasks": 10,
        "failedTasks": 0,
        "passRate": 1.0,
        "minPassRate": 0.80,
        "isGatePassed": True,
        "avgLatencyMs": 150,
        "totalDurationMs": 1500,
        "totalTokens": 2000,
        "promptTokens": 1500,
        "completionTokens": 500,
        "totalCostUsd": 0.0,
        "tasks": [
            {
                "taskId": "code_01_fibonacci",
                "name": "Fibonacci Sequence",
                "category": "coding",
                "evaluator": "pytest_execution",
                "score": 1.0,
                "passed": True,
                "latencyMs": 100,
            }
        ],
    }

    md = format_markdown_report(mock_report)
    assert "## CI LLM Regression Benchmark Report: PASS (PASSED)" in md
    assert "**Pass Rate**: `100.0%`" in md
    assert "Fibonacci Sequence" in md
    assert "<= $0.05000" in md
    assert "pytest_execution" in md


def test_provider_enum_normalization_for_ci_eval():
    """ModelProvider enum instance is normalized to lowercase string (PR #88 Copilot Finding 2)."""
    from models.provider import ModelProvider
    req = TaskExecuteRequest(
        task_input="test prompt",
        task_domain=TaskDomain.GENERAL,
        provider=ModelProvider.MOCK,
    )
    assert req.provider == "mock"


def test_trust_node_neutral_on_budget_exceeded():
    """Trust updates treat budget-exceeded executions as inconclusive (PR #88 Copilot Finding 5)."""
    from ai_service.nodes.trust_node import compute_next_trust, update_experience_trust
    from models.experience import Experience, ExperienceStatus

    exp = Experience(
        id="exp_test_budget",
        task_domain=TaskDomain.GENERAL,
        trigger_condition="test condition",
        strategy_lesson="test lesson",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )

    next_trust, reason = compute_next_trust(
        current_trust=0.75,
        outcome_score=0.10,
        evaluator_details={"status": "inconclusive", "error": "budget_exceeded"},
    )
    assert next_trust == 0.75
    assert "Inconclusive evaluation" in reason

    updated_exp, _, _ = update_experience_trust(
        experience=exp,
        outcome_score=0.10,
        evaluator_details={"status": "inconclusive", "error": "budget_exceeded"},
    )
    # Usage and failure counters must not increment for budget exhaustion
    assert updated_exp.trust_score == 0.75
    assert updated_exp.uses_count == 0


def test_record_node_span_accumulates_cyclical_latency():
    """Tracer accumulates latency, tokens, and cost across cyclical loop visits (PR #88 Copilot Finding 6)."""
    from ai_service.observability.tracer import ObservabilityTracer

    tracer = ObservabilityTracer(task_id="task_cyclical_accum")
    # First visit (attempt 1)
    tracer.record_node_span("execute_node", duration_ms=100, prompt_tokens=50, completion_tokens=20, step_cost_usd=0.0001)
    # Second visit (attempt 2 after retry)
    tracer.record_node_span("execute_node", duration_ms=150, prompt_tokens=60, completion_tokens=30, step_cost_usd=0.00015)

    span = tracer.node_spans["execute_node"]
    assert span["durationMs"] == 250
    assert span["promptTokens"] == 110
    assert span["completionTokens"] == 50
    assert span["totalTokens"] == 160
    assert span["stepCostUsd"] == 0.00025
    assert span["visits"] == 2
    assert tracer.node_latencies_ms["execute_node"] == 250
