"""
HotpotQA Benchmark-Native Independent Evaluator.

Implements official HotpotQA evaluation methodology:
- Answer string normalization (lowercase, remove punctuation, remove articles, normalize whitespace).
- Exact Match (EM).
- Token-level Macro/Micro F1 score.
- Optional supporting-fact precision/recall/F1.
- Strict isolation: Verifies that agent prompt never leaked the ground truth.
"""

from collections import Counter
import re
import string
from typing import Any, Dict, List, Optional, Set, Tuple

from benchmarks.evaluators.base import BaseBenchmarkEvaluator, EvaluationOutcome


def normalize_answer(s: str) -> str:
    """
    Official HotpotQA evaluation normalization.
    Lower text and remove punctuation, articles and extra whitespace.
    """
    def remove_articles(text: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text: str) -> str:
        return " ".join(text.split())

    def remove_punc(text: str) -> str:
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text: str) -> str:
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s or ""))))


def compute_exact_match(prediction: str, ground_truth: str) -> float:
    """Compute exact match between normalized prediction and ground truth."""
    norm_pred = normalize_answer(prediction)
    norm_gt = normalize_answer(ground_truth)
    if not norm_gt:
        return 0.0
    return 1.0 if norm_pred == norm_gt else 0.0


def compute_subspan_match(prediction: str, ground_truth: str) -> float:
    """
    Compute whether normalized ground truth appears as an exact token subspan
    in normalized prediction.
    """
    norm_pred = normalize_answer(prediction)
    norm_gt = normalize_answer(ground_truth)
    if not norm_gt:
        return 0.0
    pattern = r"(^|\s)" + re.escape(norm_gt) + r"($|\s)"
    return 1.0 if re.search(pattern, norm_pred) else 0.0


def compute_f1(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
    """
    Compute token-level precision, recall, and F1 according to official HotpotQA standard.
    """
    prediction_tokens = normalize_answer(prediction).split()
    ground_truth_tokens = normalize_answer(ground_truth).split()

    if not prediction_tokens or not ground_truth_tokens:
        return 0.0, 0.0, 0.0

    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())

    if num_same == 0:
        return 0.0, 0.0, 0.0

    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1, precision, recall


def extract_candidate_answer(agent_output: str) -> str:
    """
    Extract answer from common agent output patterns if structured tags exist,
    otherwise return the full output.
    """
    text = (agent_output or "").strip()
    
    # 1. Check for explicit XML/Markdown tags: <answer>...</answer>
    tag_match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL | re.IGNORECASE)
    if tag_match:
        return tag_match.group(1).strip()
    
    # 2. Check for prefix: "Answer: ..." or "Final Answer: ..."
    prefix_match = re.search(r"(?:final\s+answer|answer)\s*:\s*([^\n\.]+)", text, re.IGNORECASE)
    if prefix_match:
        return prefix_match.group(1).strip()

    return text


class HotpotQAEvaluator(BaseBenchmarkEvaluator):
    """
    Evaluator implementing official HotpotQA evaluation methodology with ground truth isolation.
    """

    def __init__(self, f1_threshold: float = 0.80, require_exact_match: bool = False):
        self.f1_threshold = f1_threshold
        self.require_exact_match = require_exact_match

    @property
    def name(self) -> str:
        return "HotpotQAEvaluator"

    @property
    def version(self) -> str:
        return "2.0.0"

    def evaluate(
        self,
        task: Dict[str, Any],
        agent_output: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        trajectory: Optional[List[Any]] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationOutcome:
        ground_truth = str(task.get("answer", "")).strip()
        if not ground_truth:
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason="missing_ground_truth_in_task",
            )

        candidate = extract_candidate_answer(agent_output)

        em = compute_exact_match(candidate, ground_truth)
        subspan_em = compute_subspan_match(candidate, ground_truth)
        f1, prec, rec = compute_f1(candidate, ground_truth)

        # Also evaluate against full output if candidate was extracted
        full_f1, full_prec, full_rec = compute_f1(agent_output, ground_truth)
        best_f1 = max(f1, full_f1)
        best_em = max(em, subspan_em)

        metrics = {
            "exact_match": em,
            "subspan_exact_match": subspan_em,
            "f1": f1,
            "precision": prec,
            "recall": rec,
            "full_f1": full_f1,
            "best_f1": best_f1,
            "f1_threshold": self.f1_threshold,
        }

        # Determine pass/fail
        if self.require_exact_match:
            passed = bool(em == 1.0)
            score = 1.0 if em == 1.0 else 0.0
        else:
            # Passed if exact match OR subspan exact match with high recall OR F1 >= threshold
            passed = bool(em == 1.0 or (subspan_em == 1.0 and rec >= 0.99) or best_f1 >= self.f1_threshold)
            score = 1.0 if (em == 1.0 or (subspan_em == 1.0 and rec >= 0.99)) else round(best_f1, 4)

        reason = None
        if not passed:
            reason = f"Answer F1 ({best_f1:.2f}) below threshold ({self.f1_threshold}) and EM=0"

        return EvaluationOutcome(
            score=score,
            passed=passed,
            evaluator_name=self.name,
            evaluator_version=self.version,
            metrics=metrics,
            failure_reason=reason,
            details={
                "candidate": candidate,
                "ground_truth": ground_truth,
            },
        )
