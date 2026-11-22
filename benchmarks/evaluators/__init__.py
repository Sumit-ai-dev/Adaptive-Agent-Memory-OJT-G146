"""
Independent Evaluation Architecture for AEMA Empirical Benchmarks.

Provides decoupled, objective evaluators for HotpotQA, ToolBench, ALFWorld,
and custom suites. Evaluators operate strictly on model outputs and ground truth,
with zero awareness of agent condition (vanilla, naive_rag, adaptive) or trial count.
"""

from benchmarks.evaluators.base import BaseBenchmarkEvaluator, EvaluationOutcome
from benchmarks.evaluators.hotpotqa_evaluator import HotpotQAEvaluator
from benchmarks.evaluators.toolbench_evaluator import ToolBenchEvaluator

__all__ = [
    "BaseBenchmarkEvaluator",
    "EvaluationOutcome",
    "HotpotQAEvaluator",
    "ToolBenchEvaluator",
]
