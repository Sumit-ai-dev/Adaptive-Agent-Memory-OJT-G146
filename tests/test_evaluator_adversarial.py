"""
Permanent Adversarial Unit Tests for StrictKeyAnswerEvaluator.

Verifies measurement validity and regression safety:
1. Exact correct -> PASS
2. Exact wrong (distractor) -> FAIL
3. Correct mentioned after wrong (hedging/explanation) -> FAIL
4. Correct mentioned in negation ("not DESC") -> FAIL
5. Wrong followed by correct -> FAIL
6. Correct with explanation -> PASS
7. Multiple candidate answers -> FAIL if distractor affirmed
8. Case and whitespace variation -> Correct normalization
9. Old substring bug regression guard: verifies that mentioning ground truth
   subordinately NEVER triggers an unconditional >= 0.85 floor.
"""

import pytest
from ai_service.tools.evaluator import (
    StrictKeyAnswerEvaluator,
    strict_key_answer_evaluator,
    DeterministicEvaluator,
)
from models.task import EvaluatorName, EvaluationOutcome


class TestStrictKeyAnswerEvaluatorAdversarial:
    """
    Adversarial test suite enforcing strict key answer semantics.
    """

    evaluator = StrictKeyAnswerEvaluator()

    # -------------------------------------------------------------
    # 1. Exact Correct
    # -------------------------------------------------------------
    def test_exact_correct(self):
        score, reason = self.evaluator.evaluate("DESC", ground_truth="desc", distractor="down")
        assert score == 1.0
        assert "Success" in reason

        score, reason = self.evaluator.evaluate("desc", ground_truth="desc", distractor="down")
        assert score == 1.0
        assert "Success" in reason

    # -------------------------------------------------------------
    # 2. Exact Wrong (Distractor)
    # -------------------------------------------------------------
    def test_exact_wrong(self):
        score, reason = self.evaluator.evaluate("DOWN", ground_truth="desc", distractor="down")
        assert score == 0.10
        assert "Failure" in reason

        score, reason = self.evaluator.evaluate("down", ground_truth="desc", distractor="down")
        assert score == 0.10
        assert "Failure" in reason

    # -------------------------------------------------------------
    # 3. Correct Mentioned After Wrong (Hedging / Contrastive)
    # -------------------------------------------------------------
    def test_correct_mentioned_after_wrong(self):
        cases = [
            "DOWN. However, DESC is standard.",
            "Use DOWN, although DESC would normally be used.",
            "The keyword used to sort query results in descending order in SQL is **DOWN**. However, it's important to note that using the `DESC` keyword (which stands for 'Descending') is more commonly recommended and generally considered better practice than using `DOWN`.",
            "The keyword used to sort query results in descending order in SQL is **DOWN**. However, it's important to note that according to verified operational strategies and critical negative constraints provided, using the DESC keyword (which stands for 'Descending') is recommended over the DOWN keyword due to its more widespread use and better understanding among developers and database administrators.",
        ]
        for pred in cases:
            score, reason = self.evaluator.evaluate(pred, ground_truth="desc", distractor="down")
            assert score <= 0.30, f"Expected failure for hedging answer, got score={score}: {pred}"
            assert "Failure" in reason

    # -------------------------------------------------------------
    # 4. Correct Mentioned in Negation
    # -------------------------------------------------------------
    def test_correct_mentioned_in_negation(self):
        cases = [
            "The answer is DOWN, not DESC.",
            "Use DOWN instead of DESC.",
            "Choose DOWN rather than DESC.",
            "We do not use DESC; DOWN is required.",
        ]
        for pred in cases:
            score, reason = self.evaluator.evaluate(pred, ground_truth="desc", distractor="down")
            assert score <= 0.30, f"Expected failure for negated GT, got score={score}: {pred}"
            assert "Failure" in reason

    # -------------------------------------------------------------
    # 5. Wrong Followed by Correct
    # -------------------------------------------------------------
    def test_wrong_followed_by_correct(self):
        cases = [
            "DOWN is the keyword. DESC is also an alternative.",
            "It is DOWN. Some users also use DESC.",
        ]
        for pred in cases:
            score, reason = self.evaluator.evaluate(pred, ground_truth="desc", distractor="down")
            assert score <= 0.30, f"Expected failure when primary choice is distractor, got score={score}: {pred}"

    # -------------------------------------------------------------
    # 6. Correct with Explanation
    # -------------------------------------------------------------
    def test_correct_with_explanation(self):
        cases = [
            "DESC is correct.",
            "DESC. Explanation: In SQL standard syntax, descending sort order is specified by the DESC keyword.",
            "The keyword is DESC.",
            "The standard keyword used to sort query results in descending order is DESC.",
        ]
        for pred in cases:
            score, reason = self.evaluator.evaluate(pred, ground_truth="desc", distractor="down")
            assert score >= 0.80, f"Expected success for valid explanation, got score={score}: {pred}"
            assert "Success" in reason

    # -------------------------------------------------------------
    # 7. Multiple Candidate Answers (Affirming Distractor)
    # -------------------------------------------------------------
    def test_multiple_candidate_answers(self):
        pred = "You could theoretically use DOWN or DESC, but DOWN is the designated selection here."
        score, reason = self.evaluator.evaluate(pred, ground_truth="desc", distractor="down")
        assert score <= 0.30
        assert "Failure" in reason

    # -------------------------------------------------------------
    # 8. Case and Whitespace Variation
    # -------------------------------------------------------------
    def test_case_and_whitespace_variation(self):
        assert self.evaluator.evaluate("  desc  \n", "DESC", "down")[0] == 1.0
        assert self.evaluator.evaluate("`DESC`", "desc", "down")[0] == 1.0
        assert self.evaluator.evaluate("**DESC**", "desc", "down")[0] == 1.0
        assert self.evaluator.evaluate("`DOWN`", "desc", "down")[0] == 0.10
        assert self.evaluator.evaluate("**DOWN**", "desc", "down")[0] == 0.10

    # -------------------------------------------------------------
    # 9. Other Domains: Flags, Currency, Geography, Science
    # -------------------------------------------------------------
    def test_flag_curl_silent(self):
        # GT: -s, Distractor: -q
        score, _ = self.evaluator.evaluate("-s", ground_truth="-s", distractor="-q")
        assert score == 1.0

        score, _ = self.evaluator.evaluate("-q", ground_truth="-s", distractor="-q")
        assert score == 0.10

        score, _ = self.evaluator.evaluate(
            "The command-line flag that enables silent or quiet mode in curl is `-q`.",
            ground_truth="-s",
            distractor="-q",
        )
        assert score == 0.10

    def test_currency_japan(self):
        # GT: yen, Distractor: yuan
        score, _ = self.evaluator.evaluate("Japanese Yen (JPY)", ground_truth="yen", distractor="yuan")
        assert score >= 0.80

        score, _ = self.evaluator.evaluate("Yuan", ground_truth="yen", distractor="yuan")
        assert score == 0.10

        score, _ = self.evaluator.evaluate("Yuan. However, Yen is the actual currency.", ground_truth="yen", distractor="yuan")
        assert score == 0.10

    def test_geography_australia(self):
        # GT: canberra, Distractor: sydney
        score, _ = self.evaluator.evaluate("Canberra", ground_truth="canberra", distractor="sydney")
        assert score == 1.0

        score, _ = self.evaluator.evaluate("Sydney", ground_truth="canberra", distractor="sydney")
        assert score == 0.10

        score, _ = self.evaluator.evaluate("Sydney is the capital, not Canberra.", ground_truth="canberra", distractor="sydney")
        assert score == 0.10

    # -------------------------------------------------------------
    # 10. Regression Guard Against Old Substring Floor Bug
    # -------------------------------------------------------------
    def test_old_substring_bug_regression_guard(self):
        """
        Under the old evaluate_hotpotqa bug, any mention of ground truth in text
        triggered max(0.85, ...), giving R >= 0.85 even when the answer chose DOWN.
        This test explicitly guards against that regression.
        """
        buggy_old_pass_prediction = (
            "The keyword used to sort query results in descending order in SQL is **DOWN**. "
            "However, it's important to note that using the `DESC` keyword (which stands for 'Descending') "
            "is more commonly recommended and generally considered better practice than using `DOWN`."
        )
        outcome: EvaluationOutcome = DeterministicEvaluator.evaluate(
            final_answer=buggy_old_pass_prediction,
            evaluator=EvaluatorName.STRICT_KEY_ANSWER,
            ground_truth="desc",
            evaluator_config={"distractor": "down"},
        )
        assert outcome.reward < 0.35, f"Reward {outcome.reward} violates anti-substring bug invariant!"
        assert outcome.binary_outcome == 0, "Binary outcome must be 0 (failure)!"
        assert outcome.evaluator_name == EvaluatorName.STRICT_KEY_ANSWER
        assert outcome.evaluator_version == "1.0-strict"
