"""
Official MemoryAgentBench Evaluator Implementation.

Faithfully implements the evaluation methodologies of MemoryAgentBench (ICLR 2026,
arXiv:2507.05257, HUST-AI-HYZ/MemoryAgentBench):
1. Text Normalization: Removes articles, punctuation, and extra whitespace.
2. Token-level F1: Computes precision, recall, and harmonic F1 over token counters.
3. Exact Match (EM): Full normalized string equality.
4. Substring Exact Match (SEM): Checks if normalized ground truth is a substring of the output.
5. Multi-Ground-Truth Max Pooling: Evaluates against all valid answers in ground-truth list.
6. Official Output Parsing: Supports 'Answer:' prefixes and direct answers.

Research Integrity Features:
- Zero condition leakage (blind to vanilla, naive_rag, recency, adaptive).
- Strict separation of Official Benchmark Metrics vs Custom AEMA Diagnostic Metrics.
- Conflict Resolution validation: Detects obsolete memory intrusion and tracks quarantine decisions.
- Cross-platform compatible (macOS, Linux, Windows).
"""

from collections import Counter
import logging
import re
import string
from typing import Any, Dict, List, Optional, Tuple, Union

from benchmarks.evaluators.base import BaseBenchmarkEvaluator, EvaluationOutcome

logger = logging.getLogger(__name__)


# ============================================================================
# OFFICIAL TEXT NORMALIZATION & SCORING UTILITIES
# Directly adopted from HUST-AI-HYZ/MemoryAgentBench/utils/eval_other_utils.py
# ============================================================================

def extract_xml_answer(text: str) -> Optional[str]:
    """
    Extract the content enclosed in <answer>...</answer> tags if present.
    Supports case-insensitive matching, multiline contents, and unclosed trailing tags.
    """
    if not text:
        return None
    # 1. Closed tag <answer>...</answer>
    match = re.search(r"<answer>(.*?)</answer>", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1).strip()
        if content:
            return content
        return None

    # 2. Unclosed tag (e.g., truncated generation without closing tag)
    if "</answer>" not in text.lower():
        unclosed_match = re.search(r"<answer>(.*)$", text, flags=re.DOTALL | re.IGNORECASE)
        if unclosed_match:
            content = unclosed_match.group(1).strip()
            if content:
                return content

    return None


def normalize_answer(answer_text: str) -> str:
    """
    Normalize text for evaluation by removing articles, punctuation, and extra whitespace.
    Official implementation from MemoryAgentBench / DensePhrases / SQuAD,
    enhanced to strip XML tags before punctuation normalization.
    """
    if not isinstance(answer_text, str):
        answer_text = str(answer_text)
    # Strip XML/HTML tags first to prevent tag names (e.g. 'answer') from leaking into word tokens
    text = re.sub(r"<[^>]+>", " ", answer_text)
    text = text.lower()
    text = "".join(char for char in text if char not in string.punctuation)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def f1_score(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
    """
    Calculate token-level F1 score between prediction and ground truth.
    Official implementation from MemoryAgentBench.
    
    Returns:
        Tuple of (f1, precision, recall)
    """
    norm_pred = normalize_answer(prediction)
    norm_gt = normalize_answer(ground_truth)

    ZERO_METRIC = (0.0, 0.0, 0.0)

    # Handle special cases for yes/no/noanswer
    special_answers = {"yes", "no", "noanswer"}
    if (norm_pred in special_answers or norm_gt in special_answers) and norm_pred != norm_gt:
        return ZERO_METRIC

    pred_tokens = norm_pred.split()
    gt_tokens = norm_gt.split()

    if not pred_tokens or not gt_tokens:
        return ZERO_METRIC

    common_tokens = Counter(pred_tokens) & Counter(gt_tokens)
    num_common = sum(common_tokens.values())

    if num_common == 0:
        return ZERO_METRIC

    precision = num_common / len(pred_tokens)
    recall = num_common / len(gt_tokens)
    f1 = (2.0 * precision * recall) / (precision + recall)

    return f1, precision, recall


def drqa_exact_match_score(prediction: str, ground_truth: str) -> float:
    """
    Check if prediction is an exact match with ground truth after normalization.
    Official DrQA / MemoryAgentBench implementation.
    """
    return float(normalize_answer(prediction) == normalize_answer(ground_truth))


OPT_MODIFIERS = r"(?:(a|an|the|actually|really|just|in|at|located in|born in)\s+)?"

PRE_NEGATION_PATTERNS = [
    re.compile(rf"\b(not|no|never|neither|isnt|wasnt|arent|werent|cannot|wont|instead of|rather than)\s+{OPT_MODIFIERS}$"),
    re.compile(rf"\b(no longer)\s+{OPT_MODIFIERS}$"),
    re.compile(rf"\b(previously|formerly|earlier|originally|historically|obsolete|superseded|outdated|prior to|before)\s+{OPT_MODIFIERS}$"),
    re.compile(rf"\b(although|though|while)\s+(?:previously|formerly|originally)\s+{OPT_MODIFIERS}$"),
]

POST_NEGATION_PATTERNS = [
    re.compile(r"^\s*(?:is|was|are|were)?\s*(?:not|no longer|isnt|wasnt|werent|arent|incorrect|false|untrue)\b"),
    re.compile(r"^\s*(?:is|was|has been)?\s*(?:obsolete|superseded|replaced|deprecated|outdated|invalid)\b"),
]


def is_negated_or_obsolete_match(norm_pred: str, start: int, end: int) -> bool:
    """
    Determine whether a matched occurrence of an entity in prediction text is
    disqualified by negation, historical concession, or obsolescence markers.
    """
    pre_window = norm_pred[max(0, start - 60):start]
    post_window = norm_pred[end:min(len(norm_pred), end + 60)]
    for pat in PRE_NEGATION_PATTERNS:
        if pat.search(pre_window):
            return True
    for pat in POST_NEGATION_PATTERNS:
        if pat.search(post_window):
            return True
    return False


def substring_exact_match_score(prediction: str, ground_truth: str) -> float:
    """
    Check if normalized ground truth is an affirmative substring of the normalized prediction.
    Official MemoryAgentBench implementation enhanced with word boundary enforcement
    and negation/obsolescence disqualification.
    """
    norm_gt = normalize_answer(ground_truth)
    norm_pred = normalize_answer(prediction)
    if not norm_gt or not norm_pred:
        return 0.0

    pattern = re.compile(rf"\b{re.escape(norm_gt)}\b")
    matches = list(pattern.finditer(norm_pred))
    if not matches:
        return 0.0

    # If at least one occurrence is affirmative (not negated or obsolete), it is an exact match
    for m in matches:
        if not is_negated_or_obsolete_match(norm_pred, m.start(), m.end()):
            return 1.0

    return 0.0


def drqa_metric_max_over_ground_truths(
    metric_function: Any, prediction: str, ground_truths: Union[str, List[Any]]
) -> float:
    """
    Calculate maximum score over multiple alternative ground truth answers.
    Official MemoryAgentBench implementation.
    """
    if isinstance(ground_truths, str):
        gt_list = [ground_truths]
    elif ground_truths and isinstance(ground_truths[0], list):
        gt_list = [gt for sublist in ground_truths for gt in sublist]
    else:
        gt_list = list(ground_truths)

    if not gt_list:
        return 0.0

    return max(float(metric_function(prediction, gt)) for gt in gt_list)


def parse_output(output_text: str, answer_prefix: str = "Answer:") -> Optional[str]:
    """
    Parse model output to extract the answer portion.
    Official implementation from MemoryAgentBench, enhanced with XML answer tag extraction.
    """
    if not output_text:
        return None

    xml_ans = extract_xml_answer(output_text)
    if xml_ans:
        clean_xml = re.sub(
            rf"^(?:{re.escape(answer_prefix)}|label:)\s*", "", xml_ans, flags=re.IGNORECASE
        ).strip()
        return clean_xml or xml_ans

    extraction_patterns = [
        re.compile(rf"(?:{re.escape(answer_prefix)}|label:)\s*(.*)(?:\n|$)", flags=re.IGNORECASE),
        re.compile(r"(?:^)(.*)(?:\n|$)"),
    ]

    for pattern in extraction_patterns:
        match = pattern.search(output_text)
        if match:
            extracted_text = match[1].strip()
            clean_answer = re.sub(
                rf"^(?:{re.escape(answer_prefix)}|label:)\s*", "", extracted_text, flags=re.IGNORECASE
            ).strip()
            if clean_answer:
                return clean_answer

    return output_text.strip() if output_text else None


# ============================================================================
# RESEARCH-GRADE MEMORY AGENT BENCH EVALUATOR
# ============================================================================

class MemoryAgentBenchEvaluator(BaseBenchmarkEvaluator):
    """
    Official MemoryAgentBench Evaluator for Accurate Retrieval & Conflict Resolution.
    """

    @property
    def name(self) -> str:
        return "memoryagentbench_evaluator"

    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(
        self,
        task: Dict[str, Any],
        agent_output: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        trajectory: Optional[List[Any]] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationOutcome:
        """
        Evaluate agent response against official ground-truth answers.
        
        Args:
            task: Task dictionary from MemoryAgentBench manifest.
            agent_output: Complete LLM generated response.
            tool_calls: Optional tool calls (unused in QA, logged if present).
            trajectory: Optional execution steps.
            execution_metadata: Optional memory telemetry (quarantine actions, retrieved IDs).
        """
        ground_truth_answers = task.get("ground_truth_answers") or task.get("answers") or []
        if isinstance(ground_truth_answers, str):
            ground_truth_answers = [ground_truth_answers]

        if not ground_truth_answers:
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason="Task contains no valid ground-truth answers",
            )

        # Extract declared XML answer if present
        xml_answer = extract_xml_answer(agent_output)
        parsed_output = parse_output(agent_output)

        if xml_answer:
            # When model explicitly provides an <answer>...</answer> tag as instructed,
            # evaluate official metrics on the declared answer to prevent scratchpad reasoning
            # from causing spurious false positives or mask errors.
            eval_target = parsed_output or xml_answer
            final_em = drqa_metric_max_over_ground_truths(
                drqa_exact_match_score, eval_target, ground_truth_answers
            )
            final_sem = drqa_metric_max_over_ground_truths(
                substring_exact_match_score, eval_target, ground_truth_answers
            )
            final_f1 = drqa_metric_max_over_ground_truths(
                lambda p, gt: f1_score(p, gt)[0], eval_target, ground_truth_answers
            )
        else:
            # 1. Compute official metrics on raw output
            raw_em = drqa_metric_max_over_ground_truths(
                drqa_exact_match_score, agent_output, ground_truth_answers
            )
            raw_sem = drqa_metric_max_over_ground_truths(
                substring_exact_match_score, agent_output, ground_truth_answers
            )
            raw_f1 = drqa_metric_max_over_ground_truths(
                lambda p, gt: f1_score(p, gt)[0], agent_output, ground_truth_answers
            )

            # 2. Compute official metrics on parsed output (Answer: prefix extraction)
            if parsed_output:
                parsed_em = drqa_metric_max_over_ground_truths(
                    drqa_exact_match_score, parsed_output, ground_truth_answers
                )
                parsed_sem = drqa_metric_max_over_ground_truths(
                    substring_exact_match_score, parsed_output, ground_truth_answers
                )
                parsed_f1 = drqa_metric_max_over_ground_truths(
                    lambda p, gt: f1_score(p, gt)[0], parsed_output, ground_truth_answers
                )

                # Official post_process rule: take max of original and parsed score
                final_em = max(raw_em, parsed_em)
                final_sem = max(raw_sem, parsed_sem)
                final_f1 = max(raw_f1, parsed_f1)
            else:
                final_em = raw_em
                final_sem = raw_sem
                final_f1 = raw_f1

        # 3. Conflict Resolution Diagnostic Metrics (Separated from Official Metrics)
        # Check if the output recalled superseded/obsolete facts rather than updated facts
        obsolete_answers = task.get("obsolete_answers") or task.get("predecessor_answers") or []
        if isinstance(obsolete_answers, str):
            obsolete_answers = [obsolete_answers]

        is_obsolete_intrusion = False
        if obsolete_answers:
            if xml_answer:
                # If XML answer is declared, check obsolete intrusion strictly on declared answer
                eval_target = parsed_output or xml_answer
                obs_sem = drqa_metric_max_over_ground_truths(
                    substring_exact_match_score, eval_target, obsolete_answers
                )
            else:
                obs_sem = drqa_metric_max_over_ground_truths(
                    substring_exact_match_score, agent_output, obsolete_answers
                )
                if parsed_output:
                    obs_sem = max(
                        obs_sem,
                        drqa_metric_max_over_ground_truths(
                            substring_exact_match_score, parsed_output, obsolete_answers
                        ),
                    )
            is_obsolete_intrusion = (obs_sem >= 1.0) and (final_sem < 1.0)

        # 4. Quarantine Decision Tracking (if telemetry provided by agent)
        quarantine_stats: Dict[str, Any] = {}
        if execution_metadata:
            quarantined_ids = execution_metadata.get("quarantined_memory_ids", [])
            active_ids = execution_metadata.get("active_memory_ids", [])
            quarantine_stats = {
                "quarantined_count": len(quarantined_ids),
                "active_count": len(active_ids),
                "quarantine_applied": len(quarantined_ids) > 0,
            }

        # 5. Primary Benchmark Score
        # Per MemoryAgentBench protocol: Substring Exact Match represents official Accuracy
        # for fact_sh, fact_mh, and ruler_qa. Exact Match represents official Accuracy for TTL (ICL).
        competency = task.get("competency", "")
        if competency == "Test_Time_Learning":
            primary_score = final_em
            passed = (final_em >= 1.0)
        else:
            primary_score = final_sem
            passed = (final_sem >= 1.0)

        failure_reason = None
        if not passed:
            if is_obsolete_intrusion:
                failure_reason = "Negative memory transfer: agent recalled superseded obsolete fact"
            else:
                failure_reason = "Prediction did not match ground truth"

        return EvaluationOutcome(
            score=primary_score,
            passed=passed,
            evaluator_name=self.name,
            evaluator_version=self.version,
            metrics={
                "official": {
                    "accuracy": final_em if competency == "Test_Time_Learning" else final_sem,
                    "exact_match": final_em,
                    "substring_exact_match": final_sem,
                    "token_f1": final_f1,
                },
                "aema_diagnostics": {
                    "is_obsolete_fact_intrusion": is_obsolete_intrusion,
                    **quarantine_stats,
                },
            },
            failure_reason=failure_reason,
            details={
                "task_id": task.get("task_id"),
                "competency": task.get("competency"),
                "sub_dataset": task.get("sub_dataset"),
                "parsed_output": parsed_output,
                "ground_truth_answers": ground_truth_answers,
                "obsolete_answers": obsolete_answers,
            },
        )
