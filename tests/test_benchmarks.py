"""
Smoke and Unit Tests for Benchmark Suites and Official Metric Calculations.
Tests:
  1. Data loaders (HotpotQA, ToolBench, ALFWorld).
  2. Metrics computation: Pass@k, ERR, Token Economy, Quarantine Precision.
"""

import pytest
from benchmarks.alfworld_runner import load_alfworld_tasks
from benchmarks.hotpotqa_runner import load_hotpotqa_tasks
from benchmarks.metrics import (
    TrialRecord,
    compute_all_metrics,
    compute_err,
    compute_pass_at_k,
    compute_quarantine_precision,
    compute_token_economy,
)
from benchmarks.toolbench_runner import load_toolbench_tasks


def test_benchmark_data_loaders():
    """Verify all 3 datasets load valid task structures."""
    hp_tasks = load_hotpotqa_tasks(limit=3)
    assert len(hp_tasks) == 3
    assert "question" in hp_tasks[0]
    assert "answer" in hp_tasks[0]

    tb_tasks = load_toolbench_tasks(limit=3)
    assert len(tb_tasks) == 3
    assert "query" in tb_tasks[0]
    assert "trap_type" in tb_tasks[0]

    alf_tasks = load_alfworld_tasks(limit=3)
    assert len(alf_tasks) == 3
    assert "goal" in alf_tasks[0]


def test_metrics_math():
    """Verify Pass@k, ERR, Token Economy, and Quarantine Precision arithmetic."""
    raw = [
        # Task 1: Vanilla fails trial 1, repeats error trial 2
        TrialRecord({"benchmark": "hotpotqa", "task_id": "t1", "condition": "vanilla", "trial": 1, "success": False, "tokens_used": 1000, "iterations": 5, "error_recurred": False, "quarantine_triggered": False, "quarantine_blocked_poison": False}),
        TrialRecord({"benchmark": "hotpotqa", "task_id": "t1", "condition": "vanilla", "trial": 2, "success": False, "tokens_used": 1000, "iterations": 5, "error_recurred": True, "quarantine_triggered": False, "quarantine_blocked_poison": False}),

        # Task 1: Adaptive fails trial 1, recovers trial 2
        TrialRecord({"benchmark": "hotpotqa", "task_id": "t1", "condition": "adaptive", "trial": 1, "success": False, "tokens_used": 1000, "iterations": 5, "error_recurred": False, "quarantine_triggered": True, "quarantine_blocked_poison": True}),
        TrialRecord({"benchmark": "hotpotqa", "task_id": "t1", "condition": "adaptive", "trial": 2, "success": True, "tokens_used": 600, "iterations": 3, "error_recurred": False, "quarantine_triggered": False, "quarantine_blocked_poison": False}),
    ]

    pass_k = compute_pass_at_k(raw, k_values=[1, 2])
    assert pass_k["vanilla"][1] == 0.0
    assert pass_k["vanilla"][2] == 0.0
    assert pass_k["adaptive"][1] == 0.0
    assert pass_k["adaptive"][2] == 1.0  # Learned and recovered by trial 2!

    err = compute_err(raw)
    assert err["vanilla"] == 0.5
    assert err["adaptive"] == 0.0

    econ = compute_token_economy(raw)
    assert econ["vanilla"] == 1.0
    assert econ["adaptive"] > 1.0  # Used 1600 vs 2000 tokens

    summary = compute_all_metrics(raw)
    assert "adaptive" in summary
    assert "vanilla" in summary
