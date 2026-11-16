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
from models.task import EvaluatorName


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
                "taskId": "code_01_is_even",
                "name": "Parity Determination",
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
    assert "| **Pass@1 Rate** | **100.0%** | >= 80.0% | PASS |" in md
    assert "Parity Determination" in md
    assert "pytest_execution" in md
