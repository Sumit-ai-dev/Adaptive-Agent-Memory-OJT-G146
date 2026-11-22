"""
Unit and Integration Tests for Research-Grade Benchmark Architecture.

Verifies:
1. Ground-truth isolation (evaluators have access, agent prompts do not).
2. Evaluator independence (zero condition name or trial index bias).
3. ToolBench trap detection (deprecated parameters trigger failure objectively).
4. HotpotQA official evaluation semantics (normalization, Exact Match, Token F1).
5. Authentic telemetry (wall-clock latency, token collection, zero synthetic multipliers).
"""

import inspect
import json
import pytest

from benchmarks.evaluators.base import BaseBenchmarkEvaluator, EvaluationOutcome
from benchmarks.evaluators.hotpotqa_evaluator import (
    compute_exact_match,
    compute_f1,
    extract_candidate_answer,
    HotpotQAEvaluator,
    normalize_answer,
)
from benchmarks.evaluators.toolbench_evaluator import (
    extract_tool_calls_from_text,
    normalize_call_representation,
    ToolBenchEvaluator,
)
from benchmarks.telemetry import estimate_tokens_fallback, TrialTelemetryRecord


class TestEvaluatorArchitecture:
    def test_base_evaluator_contract(self):
        """BaseBenchmarkEvaluator cannot be instantiated without implementing evaluate."""
        with pytest.raises(TypeError):
            BaseBenchmarkEvaluator()  # type: ignore

    def test_evaluation_outcome_immutability(self):
        """EvaluationOutcome is frozen and cannot be mutated after evaluation."""
        outcome = EvaluationOutcome(
            score=1.0,
            passed=True,
            evaluator_name="test",
            evaluator_version="1.0.0",
        )
        with pytest.raises(Exception):
            outcome.score = 0.5  # type: ignore

    def test_evaluator_signature_isolation(self):
        """Evaluator evaluate() method signature MUST NOT accept condition_name or trial."""
        for evaluator_cls in [HotpotQAEvaluator, ToolBenchEvaluator]:
            sig = inspect.signature(evaluator_cls.evaluate)
            params = sig.parameters
            assert "condition_name" not in params, f"{evaluator_cls.__name__} must not accept condition_name"
            assert "condition" not in params, f"{evaluator_cls.__name__} must not accept condition"
            assert "trial" not in params, f"{evaluator_cls.__name__} must not accept trial"


class TestHotpotQAEvaluator:
    def test_normalization(self):
        """Verifies official HotpotQA text normalization rules."""
        assert normalize_answer("The United States of America.") == "united states of america"
        assert normalize_answer("  A   quick, brown fox!  ") == "quick brown fox"
        assert normalize_answer("an Apple") == "apple"

    def test_exact_match(self):
        """Verifies exact match computation."""
        assert compute_exact_match("Paris", "Paris") == 1.0
        assert compute_exact_match("paris", "Paris.") == 1.0
        assert compute_exact_match("The Paris", "Paris") == 1.0
        assert compute_exact_match("London", "Paris") == 0.0

    def test_token_f1(self):
        """Verifies token-level precision, recall, and F1."""
        # Exact match yields 1.0 F1
        f1, p, r = compute_f1("Albert Einstein", "Albert Einstein")
        assert f1 == 1.0 and p == 1.0 and r == 1.0

        # Partial overlap (note 'a' is stripped by official normalize_answer)
        f1, p, r = compute_f1("Albert Einstein was a physicist", "Albert Einstein")
        assert p == 0.5  # 2 matching tokens / 4 pred tokens ("albert", "einstein", "was", "physicist")
        assert r == 1.0  # 2 matching tokens / 2 gt tokens
        expected_f1 = (2 * 0.5 * 1.0) / (0.5 + 1.0)
        assert abs(f1 - expected_f1) < 1e-4

        # Zero overlap
        f1, p, r = compute_f1("Isaac Newton", "Albert Einstein")
        assert f1 == 0.0

    def test_answer_tag_extraction(self):
        """Verifies candidate answer extraction from XML and markdown patterns."""
        output1 = "After researching, the answer is: <answer>Marie Curie</answer>."
        assert extract_candidate_answer(output1) == "Marie Curie"

        output2 = "Final Answer: Warsaw, Poland."
        assert extract_candidate_answer(output2) == "Warsaw, Poland"

    def test_evaluation_outcome_pass_fail(self):
        """Evaluator correctly passes accurate answers and rejects incorrect answers."""
        evaluator = HotpotQAEvaluator(f1_threshold=0.80)
        task = {
            "id": "hp_001",
            "question": "What is the capital of France?",
            "answer": "Paris",
        }

        # Accurate answer
        outcome_pass = evaluator.evaluate(task, "The capital of France is Paris.")
        assert outcome_pass.passed is True
        assert outcome_pass.score >= 0.80

        # Incorrect answer
        outcome_fail = evaluator.evaluate(task, "The capital of France is Berlin.")
        assert outcome_fail.passed is False
        assert outcome_fail.score == 0.0
        assert outcome_fail.failure_reason is not None


class TestToolBenchEvaluator:
    @pytest.fixture
    def sample_task(self):
        return {
            "id": "tb_dep_001",
            "query": "Search for AI safety news.",
            "trap_type": "deprecated_param",
            "trap_description": "Use 'recency' instead of 'days'",
            "correct_call": {
                "tool": "web_search",
                "params": {"query": "AI safety news", "days": 7},
            },
            "wrong_call": {
                "tool": "web_search",
                "params": {"query": "AI safety news", "recency": 7},
            },
            "expected_error": "TypeError: unexpected keyword argument 'recency'",
        }

    def test_trap_detection(self, sample_task):
        """Agent falling for adversarial trap must fail objectively."""
        evaluator = ToolBenchEvaluator()

        # Agent output containing the deprecated trap parameter
        trap_output = '{"tool": "web_search", "params": {"query": "AI safety news", "recency": 7}}'
        outcome = evaluator.evaluate(sample_task, trap_output)

        assert outcome.passed is False
        assert outcome.score == 0.0
        assert outcome.metrics["trap_triggered"] is True
        assert "trap_triggered" in (outcome.failure_reason or "")

    def test_valid_tool_call(self, sample_task):
        """Agent using the valid, non-deprecated parameter passes."""
        evaluator = ToolBenchEvaluator()

        valid_output = '```json\n{"tool": "web_search", "params": {"query": "AI safety news", "days": 7}}\n```'
        outcome = evaluator.evaluate(sample_task, valid_output)

        assert outcome.passed is True
        assert outcome.score == 1.0
        assert outcome.metrics["trap_triggered"] is False
        assert outcome.metrics["valid_call_found"] is True

    def test_zero_trial_index_influence(self, sample_task):
        """
        Critical integrity test: An erroneous call must NEVER pass regardless
        of trial count or iteration.
        """
        evaluator = ToolBenchEvaluator()
        trap_output = '{"tool": "web_search", "params": {"query": "AI safety news", "recency": 7}}'

        # Evaluating 5 consecutive times produces identically failed results
        for trial in range(1, 6):
            outcome = evaluator.evaluate(sample_task, trap_output)
            assert outcome.passed is False, f"Trial {trial} must NOT pass with trap call!"
            assert outcome.score == 0.0


class TestPromptAndTelemetryIntegrity:
    def test_hotpotqa_prompt_isolation(self):
        """Verify hotpotqa_runner does NOT leak ground truth in task prompt."""
        from benchmarks.hotpotqa_runner import run_hotpotqa_trial
        source = inspect.getsource(run_hotpotqa_trial)
        assert "[Ground Truth Reference:" not in source, "Ground truth leaked in hotpotqa prompt!"
        assert "ground_truth" not in source.split("task_input=")[1].split(",")[0], (
            "task_input must not reference ground_truth!"
        )

    def test_toolbench_prompt_isolation(self):
        """Verify toolbench_runner does NOT leak correct parameter call in prompt."""
        from benchmarks.toolbench_runner import run_toolbench_trial
        source = inspect.getsource(run_toolbench_trial)
        assert "[Validation Criteria:" not in source, "Validation criteria leaked in toolbench prompt!"
        assert "correct_call" not in source.split("task_input=")[1].split(",")[0], (
            "task_input must not reference correct_call!"
        )

    def test_no_hardcoded_condition_rules(self):
        """Verify toolbench_runner has NO condition-specific success logic."""
        from benchmarks.toolbench_runner import run_toolbench_trial
        source = inspect.getsource(run_toolbench_trial)
        assert 'condition_name == "adaptive"' not in source, "Condition favoritism found in toolbench_runner!"
        assert 'trial >= 2' not in source, "Trial-index override found in toolbench_runner!"
        assert 'trial >= 3' not in source, "Trial-index override found in toolbench_runner!"

    def test_token_estimation_fallback(self):
        """Fallback token estimator produces deterministic, non-zero token counts."""
        tokens = estimate_tokens_fallback("What is the capital of France?")
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_telemetry_record_serialization(self):
        """TrialTelemetryRecord serializes cleanly to JSON and preserves all fields."""
        rec = TrialTelemetryRecord(
            benchmark="hotpotqa",
            task_id="hp_01",
            condition="adaptive",
            trial=1,
            success=True,
            score=0.95,
            evaluator_name="HotpotQAEvaluator",
            evaluator_version="2.0.0",
            tokens_used=1450,
            prompt_tokens=1100,
            completion_tokens=350,
            token_count_estimated=False,
            latency_ms=452.3,
            iterations=1,
            error_recurred=False,
            quarantine_triggered=False,
            quarantine_blocked_poison=False,
        )
        data = json.loads(rec.to_json())
        assert data["benchmark"] == "hotpotqa"
        assert data["tokens_used"] == 1450
        assert data["token_count_estimated"] is False
        assert data["latency_ms"] == 452.3
        assert data["score"] == 0.95
