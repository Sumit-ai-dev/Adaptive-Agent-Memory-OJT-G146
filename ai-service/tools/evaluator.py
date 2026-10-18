"""
Deterministic Reward Evaluator for Agent Task Execution.
Computes scalar reward R_t in [0.0, 1.0] across research, coding, embodied, and tool benchmarks.
Independent of LLM self-preference to eliminate self-evaluation bias.
"""

import ast
import json
import logging
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from models.task import (
    DEFAULT_OUTCOME_THRESHOLD,
    EvaluationOutcome,
    EvaluatorName,
)

logger = logging.getLogger("ai_service.tools.evaluator")

#: Default wall-clock budget for a single candidate test run.
DEFAULT_PYTEST_TIMEOUT_S: float = 15.0

#: S11: evaluators whose reward is already exactly binary, so their EFFECTIVE
#: binarisation cut-point is fixed by the evaluator rather than by the task.
#: `pytest_execution` returns reward in {0.0, 1.0}, so its threshold is 1.0 and a
#: requested 0.8 would be a different (and untrue) description of what ran.
_FIXED_EFFECTIVE_THRESHOLDS = {
    EvaluatorName.PYTEST_EXECUTION: 1.0,
}


def effective_outcome_threshold(
    evaluator: "EvaluatorName | str | None",
    requested_threshold: float = DEFAULT_OUTCOME_THRESHOLD,
) -> float:
    """
    THE single source of truth for the binarisation cut-point actually applied.

    Both the execution path and the run manifest call this, so a future evaluator
    with its own fixed threshold cannot reintroduce the S11 mismatch: it only has to
    be declared once, in `_FIXED_EFFECTIVE_THRESHOLDS`.
    """
    if evaluator is None:
        return float(requested_threshold)
    name = evaluator if isinstance(evaluator, EvaluatorName) else EvaluatorName(str(evaluator))
    return float(_FIXED_EFFECTIVE_THRESHOLDS.get(name, requested_threshold))


def extract_test_code_from_task_input(task_input: str) -> Optional[str]:
    """
    Extracts or synthesizes deterministic pytest test code from task specifications.
    Supports:
      1. Explicit test directives: [Test Code: ...], [Test Suite: ...], [Tests: ...]
      2. Markdown python blocks under test headers (e.g. ### Tests ... ```python ... ```)
      3. Bulleted or line-by-line required behavior assertions:
         - is_even(2) == True
         - is_even(3) -> False
         assert is_even(5) == False
    """
    if not task_input or not task_input.strip():
        return None

    # 1. Check for explicit test blocks
    match = re.search(
        r"\[(?:Test Code|Test Suite|Tests|Validation Tests):\s*(.*?)\s*\]",
        task_input,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        code = match.group(1).strip()
        if code:
            return code

    # 2. Check for markdown python blocks following Test/Assertion headers
    m_block = re.search(
        r"(?:###?\s*(?:Tests?|Assertions?|Test Cases|Validation))\s*\n+```(?:python|py)?\s*\n(.*?)```",
        task_input,
        re.DOTALL | re.IGNORECASE,
    )
    if m_block:
        code = m_block.group(1).strip()
        if code:
            return code

    # 3. Extract line-by-line assertions / expected behaviors
    assertions: List[str] = []
    lines = task_input.splitlines()
    pattern = re.compile(
        r"^\s*(?:[-*•]|\d+[.)])?\s*(?:assert\s+)?([a-zA-Z_]\w*\s*\([^)]*\)\s*(?:==|!=|is|is not|>=|<=|>|<)\s*[^#\n\r]+)"
    )
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith(("def ", "class ", "import ", "from ", "return ", "if ", "for ", "while ")):
            continue
        line_normalized = re.sub(r"\s*(?:->|=>)\s*", " == ", line_clean)
        m = pattern.match(line_normalized)
        if m:
            expr = m.group(1).strip().strip("`*").strip()
            if not expr.startswith("assert "):
                expr = f"assert {expr}"
            assertions.append(expr)

    if assertions:
        test_funcs = []
        for idx, a in enumerate(assertions):
            fn_name = "test_task_requirements" if idx == 0 else f"test_task_requirements_{idx+1}"
            test_funcs.append(f"def {fn_name}():\n    {a}\n")
        return "\n".join(test_funcs)

    # 4. Canonical function synthesis for common function prompts (e.g. is_even)
    if re.search(r"\bis_even\b", task_input, re.IGNORECASE):
        canonical_assertions = [
            "assert is_even(2) is True",
            "assert is_even(3) is False",
            "assert is_even(0) is True",
            "assert is_even(4) is True",
            "assert is_even(5) is False",
            "assert is_even(-2) is True",
            "assert is_even(-1) is False",
        ]
        return "\n".join(
            f"def {'test_is_even_canonical' if i == 0 else f'test_is_even_canonical_{i+1}'}():\n    {a}\n"
            for i, a in enumerate(canonical_assertions)
        )

    return None


def extract_python_code(answer: str) -> str:
    """
    Pulls runnable Python out of a model answer.

    Order: fenced ```python block -> any fenced block -> the raw answer.
    Deterministic and dependency-free; identical input always yields identical output.
    """
    if not answer:
        return ""

    fenced_py = re.findall(r"```(?:python|py)\s*\n(.*?)```", answer, re.DOTALL | re.IGNORECASE)
    if fenced_py:
        return "\n\n".join(block.strip() for block in fenced_py)

    fenced_any = re.findall(r"```\s*\n(.*?)```", answer, re.DOTALL)
    if fenced_any:
        return "\n\n".join(block.strip() for block in fenced_any)

    return answer.strip()


NATURAL_LANGUAGE_REFUSAL_PATTERN = re.compile(
    r"\b("
    r"i\s+am\s+sorry|i'm\s+sorry|i\s+apologize|apologies|"
    r"i\s+cannot|i\s+can't|i\s+am\s+unable|i'm\s+unable|unable\s+to\s+(?:generate|write|provide|fulfill|assist|complete|comply)|"
    r"cannot\s+(?:generate|write|provide|fulfill|assist|complete|comply)|"
    r"refuse\s+to|decline\s+to|"
    r"as\s+an\s+ai|as\s+a\s+language\s+model|"
    r"against\s+my\s+(?:programming|safety|guidelines|policy)"
    r")\b",
    re.IGNORECASE,
)


class PytestExecutionEvaluator:
    """
    F2: Execution-based evaluator for deterministic Python tasks.

    Writes the candidate solution and a FROZEN test suite into a throwaway directory
    and runs pytest in a subprocess. The outcome is the process exit status -- no LLM
    judgement, no string heuristics, no length scoring, no threshold to justify.

    reward is 1.0 on a clean pass and 0.0 otherwise, so `binary_outcome == reward`
    and the F3 binarisation is exact rather than approximate.
    """

    name = EvaluatorName.PYTEST_EXECUTION
    version = "1.0"

    def __init__(self, timeout_s: float = DEFAULT_PYTEST_TIMEOUT_S):
        self.timeout_s = timeout_s

    def evaluate(
        self,
        final_answer: str,
        test_code: str,
        timeout_s: Optional[float] = None,
        solution_filename: str = "solution.py",
        setup_code: str = "",
    ) -> EvaluationOutcome:
        timeout = float(timeout_s or self.timeout_s)

        if not test_code or not test_code.strip():
            return EvaluationOutcome.from_reward(
                reward=0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason="Configuration error: pytest_execution requires non-empty 'test_code'; unverified execution",
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"error": "missing_test_code", "status": "inconclusive"},
            )

        candidate = extract_python_code(final_answer)
        if not candidate.strip():
            return EvaluationOutcome.from_reward(
                reward=0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason="Failure: no Python code found in the answer",
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"error": "empty_candidate"},
            )

        # Check for natural-language refusals or absence of code markers
        is_refusal = bool(
            NATURAL_LANGUAGE_REFUSAL_PATTERN.search(candidate)
            or NATURAL_LANGUAGE_REFUSAL_PATTERN.search(final_answer)
        )
        has_code_markers = bool(re.search(r"^\s*(def|class|import|from)\b", candidate, re.MULTILINE))
        has_code_fence = "```" in final_answer

        # If it's a natural-language refusal without code definitions, classify as empty_candidate / refusal
        if is_refusal and not has_code_markers:
            return EvaluationOutcome.from_reward(
                reward=0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason="Failure: natural-language refusal; no Python code provided",
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"error": "empty_candidate", "refusal": True},
            )

        # Attempt to extract valid python block if raw text has non-code commentary
        try:
            ast.parse(candidate)
        except SyntaxError:
            m = re.search(r"((?:from\s+\S+\s+import|import\s+\S+|def\s+\w+|class\s+\w+).*?)(?:\Z)", candidate, re.DOTALL)
            if m:
                cand_lines = m.group(1).splitlines()
                for end_idx in range(len(cand_lines), 0, -1):
                    chunk = "\n".join(cand_lines[:end_idx])
                    try:
                        ast.parse(chunk)
                        candidate = chunk
                        break
                    except SyntaxError:
                        pass

        # Validate syntax
        try:
            ast.parse(candidate)
        except SyntaxError as e:
            # Distinguish genuine Python syntax error from ordinary non-code commentary
            # If the candidate was not in a code fence and has no Python declarations, it is not code.
            if not has_code_fence and not has_code_markers:
                return EvaluationOutcome.from_reward(
                    reward=0.0,
                    evaluator_name=self.name,
                    evaluator_version=self.version,
                    reason="Failure: no Python code found in the answer",
                    outcome_threshold=effective_outcome_threshold(self.name),
                    details={"error": "empty_candidate"},
                )
            return EvaluationOutcome.from_reward(
                reward=0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason=f"Failure: Syntax error in generated code: {e.msg} (line {e.lineno})",
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"error": "syntax_error", "lineno": e.lineno, "msg": e.msg},
            )

        workdir = tempfile.mkdtemp(prefix="pytest_eval_")
        try:
            if setup_code.strip():
                candidate = f"{setup_code.rstrip()}\n\n{candidate}"

            with open(os.path.join(workdir, solution_filename), "w", encoding="utf-8") as fh:
                fh.write(candidate + "\n")

            test_content = test_code
            if "from solution import" not in test_code and "import solution" not in test_code:
                test_content = (
                    "import sys\n"
                    "import os\n"
                    "sys.path.insert(0, os.path.dirname(__file__))\n"
                    "from solution import *\n\n"
                    + test_code
                )

            with open(os.path.join(workdir, "test_solution.py"), "w", encoding="utf-8") as fh:
                fh.write(test_content + "\n")

            # Minimal, reproducible environment. Bytecode writing disabled and hash
            # randomisation pinned so repeated runs of the same candidate are identical.
            env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": workdir,
                "TMPDIR": workdir,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONPATH": workdir,
            }

            proc = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "test_solution.py",
                    "-q", "--no-header",
                    "-p", "no:cacheprovider",
                    "-p", "no:randomly",
                ],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            passed = proc.returncode == 0
            tail = (proc.stdout or "")[-800:] + (proc.stderr or "")[-400:]

            if passed:
                reason = "Success: all tests passed"
            else:
                failure_summary = ""
                for line in (proc.stdout or "").splitlines():
                    if "FAILED " in line or "AssertionError" in line or "Error:" in line or "SyntaxError" in line:
                        failure_summary = line.strip()
                        break
                reason = f"Failure: {failure_summary}" if failure_summary else f"Failure: pytest exited {proc.returncode}"

            return EvaluationOutcome.from_reward(
                reward=1.0 if passed else 0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason=reason,
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"returncode": proc.returncode, "output_tail": tail},
            )

        except subprocess.TimeoutExpired:
            return EvaluationOutcome.from_reward(
                reward=0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason=f"Failure: test execution exceeded {timeout}s",
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"error": "timeout", "timeout_s": timeout},
            )
        except Exception as exc:
            logger.error("pytest_execution harness error", exc_info=True)
            return EvaluationOutcome.from_reward(
                reward=0.0,
                evaluator_name=self.name,
                evaluator_version=self.version,
                reason=f"Inconclusive: harness error ({type(exc).__name__})",
                outcome_threshold=effective_outcome_threshold(self.name),
                details={"error": "harness_error", "status": "inconclusive", "exception": type(exc).__name__},
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


pytest_execution_evaluator = PytestExecutionEvaluator()


class StrictKeyAnswerEvaluator:
    """
    Deterministic Task-Aware Strict Key-Answer Evaluator for Controlled Benchmarks.

    Measurement validity invariants:
      1. Strictly eliminates the unconditional substring-match floor (R >= 0.85).
      2. Deterministic: no LLM-as-a-judge, no non-deterministic heuristics, no first-5-token shortcuts.
      3. Task-aware: evaluates against ground truth and known distractor entities from structured task metadata.
      4. Distractor rejection: affirming the distractor in the primary clause or as the chosen answer scores as failure (R = 0.10).
      5. Subordinate/hedging rejection: mentioning the ground truth in contrastive, explanatory, or subordinate clauses
         (e.g., "DOWN. However, DESC is standard.", "Use DOWN, although DESC would normally be used.")
         while affirming the distractor does NOT constitute selecting the ground truth and scores as failure (R = 0.10).
      6. Ground truth clean selection: affirming the ground truth without affirming a distractor scores as pass (R = 1.0).
    """

    name = EvaluatorName.STRICT_KEY_ANSWER
    version = "1.0-strict"

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalizes unicode, strips markdown bold/code markers, preserves flags with leading hyphens,
        and fixes spacing.
        """
        if not text:
            return ""
        # Unicode normalization (e.g. Brasília -> Brasilia)
        text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
        text = text.lower()
        # Remove markdown bold, italic, code backticks
        text = re.sub(r"[*`_]", " ", text)
        # Retain hyphens attached to tokens (for flags like -s, -q)
        cleaned = []
        for ch in text:
            if ch in string.punctuation and ch != "-":
                cleaned.append(" ")
            else:
                cleaned.append(ch)
        return " ".join("".join(cleaned).split())

    @classmethod
    def evaluate(
        cls,
        prediction: str,
        ground_truth: str,
        distractor: Optional[str] = None,
        task_category: Optional[str] = None,
    ) -> Tuple[float, str]:
        """
        Evaluates a prediction against ground truth and known distractor.
        Returns scalar reward R_t in [0.0, 1.0] and diagnostic rationale.
        """
        if not prediction or not prediction.strip():
            return 0.0, "Failure: Output was empty"

        pred_raw = prediction.strip()
        norm_pred = cls.normalize_text(pred_raw)
        norm_gt = cls.normalize_text(ground_truth)
        norm_dist = cls.normalize_text(distractor) if distractor else None

        # 1. Exact match checks
        if norm_pred == norm_gt:
            return 1.0, f'Success: Exact match with ground truth "{ground_truth}"'
        if norm_dist and norm_pred == norm_dist:
            return 0.10, f'Failure: Explicitly selected distractor "{distractor}"'

        def contains_token(target: Optional[str], text: str) -> bool:
            if not target or not text:
                return False
            pattern = r"(?<![\w\-])" + re.escape(target) + r"(?![\w\-])"
            return bool(re.search(pattern, text))

        has_dist_full = contains_token(norm_dist, norm_pred) if norm_dist else False
        has_gt_full = contains_token(norm_gt, norm_pred)

        # Split into primary clause (first sentence / line) vs subsequent text
        sentences = [s.strip() for s in re.split(r"[.\n;]", pred_raw) if s.strip()]
        first_clause = sentences[0] if sentences else pred_raw
        norm_first = cls.normalize_text(first_clause)

        has_dist_first = contains_token(norm_dist, norm_first) if norm_dist else False
        has_gt_first = contains_token(norm_gt, norm_first)

        # Helpers to detect negation vs contrastive framing
        def is_negated(target: Optional[str], text: str, other: Optional[str] = None) -> bool:
            if not target or not text:
                return False
            other_guard = f"(?!{re.escape(other)})" if other else ""
            pattern = (
                r"\b(not|never|do not use|don\'t use|instead of|rather than|deprecated|avoid)\s+"
                r"(?: " + other_guard + r"[\w-]+\s+){0,3}" + re.escape(target)
            )
            return bool(re.search(pattern, text))

        def is_subordinated_by_contrast(target: Optional[str], text: str, other: Optional[str] = None) -> bool:
            if not target or not text:
                return False
            other_guard = f"(?!{re.escape(other)})" if other else ""
            pattern = (
                r"\b(however|although|though|recommended over|better practice than)\s+"
                r"(?: " + other_guard + r"[\w-]+\s+){0,4}" + re.escape(target)
            )
            return bool(re.search(pattern, text))

        dist_negated_first = is_negated(norm_dist, norm_first, norm_gt)
        gt_negated_first = is_negated(norm_gt, norm_first, norm_dist)

        dist_negated_full = is_negated(norm_dist, norm_pred, norm_gt)
        gt_negated_full = is_negated(norm_gt, norm_pred, norm_dist)

        gt_subordinated_full = is_subordinated_by_contrast(norm_gt, norm_pred, norm_dist)
        dist_subordinated_full = is_subordinated_by_contrast(norm_dist, norm_pred, norm_gt)

        # 2. Distractor affirmed in primary clause
        if has_dist_first and not dist_negated_first:
            return 0.10, f'Failure: Primary clause selected distractor "{distractor}"'

        # 3. Ground truth explicitly negated
        if gt_negated_full:
            return 0.10, f'Failure: Ground truth "{ground_truth}" negated in answer'

        # 4. Both distractor and ground truth appear in the output
        if has_dist_full and has_gt_full:
            # If ground truth is subordinated by contrastive markers (e.g. "However, DESC is standard")
            # and distractor is not negated, it's a failure.
            if gt_subordinated_full and not dist_negated_full:
                return 0.10, f'Failure: Ground truth "{ground_truth}" mentioned only subordinately; distractor "{distractor}" affirmed'
            # If distractor is not negated, both present means ambiguous or distractor chosen
            if not dist_negated_full:
                return 0.10, f'Failure: Distractor "{distractor}" affirmed alongside ground truth'

        # 5. Only distractor appears (no ground truth)
        if has_dist_full and not has_gt_full:
            return 0.10, f'Failure: Selected distractor "{distractor}"'

        # 6. Ground truth appears without distractor
        if has_gt_full and not has_dist_full:
            if gt_negated_full:
                return 0.10, f'Failure: Ground truth "{ground_truth}" was negated'
            return 1.0, f'Success: Ground truth "{ground_truth}" cleanly selected'

        # 7. Fallback token-level overlap without 0.85 floor
        gt_tokens = norm_gt.split()
        pred_tokens = norm_pred.split()
        if gt_tokens and all(t in pred_tokens for t in gt_tokens):
            if gt_negated_full:
                return 0.10, f'Failure: Ground truth "{ground_truth}" was negated'
            return 0.90, f'Success: Ground truth tokens contained in answer'

        return 0.10, "Failure: Answer does not match ground truth"


strict_key_answer_evaluator = StrictKeyAnswerEvaluator()


class DeterministicEvaluator:
    """
    Evaluates agent task execution trajectories against objective ground truths and invariants.
    """

    @staticmethod
    def normalize_answer(s: str) -> str:
        """Lower text and remove punctuation, articles and extra whitespace."""
        def remove_articles(text: str) -> str:
            return re.sub(r"\b(a|an|the)\b", " ", text)

        def white_space_fix(text: str) -> str:
            return " ".join(text.split())

        def remove_punc(text: str) -> str:
            exclude = set(string.punctuation)
            return "".join(ch for ch in text if ch not in exclude)

        return white_space_fix(remove_articles(remove_punc(s.lower())))

    @classmethod
    def compute_f1_score(cls, prediction: str, ground_truth: str) -> float:
        """
        Compute standard token-level F1 score (standard for HotpotQA and SQuAD).
        """
        pred_tokens = cls.normalize_answer(prediction).split()
        truth_tokens = cls.normalize_answer(ground_truth).split()

        if not pred_tokens or not truth_tokens:
            return 1.0 if pred_tokens == truth_tokens else 0.0

        common = set(pred_tokens) & set(truth_tokens)
        if not common:
            return 0.0

        num_same = sum(min(pred_tokens.count(w), truth_tokens.count(w)) for w in common)
        if num_same == 0:
            return 0.0

        precision = 1.0 * num_same / len(pred_tokens)
        recall = 1.0 * num_same / len(truth_tokens)
        f1 = (2 * precision * recall) / (precision + recall)
        return float(f1)

    @classmethod
    def compute_exact_match(cls, prediction: str, ground_truth: str) -> bool:
        """
        Exact Match (EM) binary check.
        """
        return cls.normalize_answer(prediction) == cls.normalize_answer(ground_truth)

    @classmethod
    def evaluate_hotpotqa(
        cls, prediction: str, ground_truth: str, distractors: Optional[List[str]] = None
    ) -> Tuple[float, str]:
        """
        Evaluates a HotpotQA multi-hop prediction against ground truth and distractors.
        Returns scalar reward R_t in [0.0, 1.0] and diagnostic rationale.
        """
        if not prediction or len(prediction.strip()) == 0:
            return 0.0, "Failure: Output was empty"

        norm_pred = cls.normalize_answer(prediction)
        norm_truth = cls.normalize_answer(ground_truth)

        # 1. Exact match
        if cls.compute_exact_match(prediction, ground_truth):
            return 1.0, "Success: Exact match with ground truth answer"

        # 2. Check for distractor deception
        if distractors:
            for dist in distractors:
                norm_dist = cls.normalize_answer(dist)
                if len(norm_dist) > 4:
                    pattern = r"\b" + re.escape(norm_dist) + r"\b"
                    if re.search(pattern, norm_pred):
                        return 0.10, f"Failure: Agent answer was deceived by distractor entity '{dist}'"

        # 3. Ground truth key phrase substring match
        if len(norm_truth) > 2:
            truth_pattern = r"\b" + re.escape(norm_truth) + r"\b" if len(norm_truth) <= 10 else re.escape(norm_truth)
            if re.search(truth_pattern, norm_pred):
                f1 = cls.compute_f1_score(prediction, ground_truth)
                score = round(max(0.85, min(0.98, 0.85 + 0.15 * f1)), 3)
                return score, f"Success: Ground truth key answer contained in output (F1={f1:.2f})"

        # 4. Token F1 scoring
        f1 = cls.compute_f1_score(prediction, ground_truth)
        if f1 >= 0.70:
            return round(f1, 3), f"Success: High semantic token overlap (F1={f1:.2f})"
        elif f1 >= 0.30:
            return round(f1, 3), f"Partial success: Moderate answer overlap (F1={f1:.2f})"

        return round(max(f1, 0.10), 3), f"Failure: Low answer overlap with ground truth (F1={f1:.2f})"

    @classmethod
    def evaluate_toolbench(
        cls,
        tool_calls: List[Dict[str, Any]],
        expected_avoid_params: Optional[List[str]] = None,
        expected_valid_params: Optional[Dict[str, Any]] = None,
        final_answer: Optional[str] = None,
    ) -> Tuple[float, str]:
        """
        Evaluates ToolBench execution against deprecated parameters, dependency traps, and tool errors.
        """
        # If no explicit tool_calls provided, check if final_answer contains a JSON tool call
        calls = list(tool_calls or [])
        if not calls and final_answer:
            try:
                # Look for JSON structures in final answer
                json_match = re.search(r"\{.*\}", final_answer, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    calls.append({"args": parsed, "output": "parsed_from_answer", "status": "success"})
            except Exception:
                pass

        if not calls:
            return 0.10, "Failure: Zero tool calls executed for tool-required task"

        # 1. Check for deprecated parameter traps
        if expected_avoid_params:
            for call in calls:
                call_args_str = (str(call.get("args", {})) + " " + str(call.get("output", ""))).lower()
                for bad_param in expected_avoid_params:
                    if bad_param.lower() in call_args_str:
                        return 0.15, f"Failure: Agent fell into tool trap by using deprecated param '{bad_param}'"
            if final_answer:
                for bad_param in expected_avoid_params:
                    if bad_param.lower() in final_answer.lower():
                        return 0.15, f"Failure: Agent output contained trapped parameter '{bad_param}'"

        # 2. Check tool execution runtime errors
        failed_calls = [
            c for c in calls
            if c.get("status") == "error"
            or "error" in str(c.get("output", "")).lower()
            or "exception" in str(c.get("output", "")).lower()
        ]
        if failed_calls:
            return 0.25, f"Failure: {len(failed_calls)} tool calls resulted in runtime exceptions"

        # 3. Check expected valid parameters if specified
        if expected_valid_params:
            matched_any = False
            for call in calls:
                args = call.get("args", {})
                if isinstance(args, dict):
                    if all(str(v).lower() in str(args.get(k, "")).lower() for k, v in expected_valid_params.items()):
                        matched_any = True
                        break
            if not matched_any and final_answer:
                matched_any = all(str(v).lower() in final_answer.lower() for v in expected_valid_params.values())

            if matched_any:
                return 0.95, "Success: All tool calls completed cleanly matching valid parameter criteria"
            return 0.40, "Partial failure: Tool calls succeeded but did not match expected parameter criteria"

        return 0.92, "Success: All tool calls completed cleanly without triggering traps"

    @classmethod
    def evaluate_alfworld(
        cls, environment_won: bool, steps_taken: int, max_steps: int = 30
    ) -> Tuple[float, str]:
        """
        Evaluates ALFWorld embodied goal completion.
        """
        if environment_won:
            # Efficiency bonus for fewer steps
            efficiency = max(0.50, 1.0 - (steps_taken / max_steps) * 0.25)
            return float(round(efficiency, 3)), f"Success: Goal achieved in {steps_taken} steps"
        else:
            return 0.10, f"Failure: Goal not achieved after {steps_taken} steps"

    @classmethod
    def evaluate_general_task(
        cls,
        final_answer: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        negative_pitfall: Optional[str] = None,
        positive_strategy: Optional[str] = None,
        task_input: Optional[str] = None,
        task_domain: Optional[str] = None,
        ground_truth: Optional[str] = None,
    ) -> Tuple[float, str]:
        """
        Deterministic, multi-signal heuristic evaluator for open-domain agent executions.
        Evaluates answer substantiveness, failure/refusal indicators, tool integrity,
        negative pitfall avoidance, and task relevance.
        """
        # Guard: Coding tasks cannot be rubber-stamped by heuristic length/token matching
        if task_domain in ("coding", "code"):
            return 0.50, "Inconclusive: Heuristic evaluation cannot verify code correctness. Independent test execution required."

        # 1. Check for ground truth presence first
        if ground_truth and len(ground_truth.strip()) > 0:
            return cls.evaluate_hotpotqa(prediction=final_answer, ground_truth=ground_truth)

        # 2. Check for empty or trivially short output
        if not final_answer or len(final_answer.strip()) == 0:
            return 0.0, "Failure: Output was completely empty"

        clean_answer = final_answer.strip()
        if len(clean_answer) < 15:
            return 0.10, "Failure: Output was truncated or trivially short (< 15 characters)"

        # 3. Check for explicit refusal or failure statements
        refusal_patterns = [
            r"\bi (?:do not|don'?t) know\b",
            r"\bi (?:cannot|can'?t) answer\b",
            r"\bunable to (?:answer|solve|complete|determine)\b",
            r"\bexecution failed\b",
            r"\bfatal error\b",
            r"\bunhandled exception\b",
        ]
        lower_answer = clean_answer.lower()
        if any(re.search(pat, lower_answer) for pat in refusal_patterns) and len(clean_answer) < 150:
            return 0.20, "Failure: Agent explicitly reported inability to complete task or fatal error"

        # 4. Check for degenerative repetitive loops
        tokens = lower_answer.split()
        if len(tokens) >= 12:
            unique_ratio = len(set(tokens)) / len(tokens)
            if unique_ratio < 0.25:
                return 0.15, f"Failure: Degenerative repetitive loop detected (unique token ratio {unique_ratio:.2f})"

        # 5. Check tool execution health
        calls = list(tool_calls or [])
        failed_calls = [
            c for c in calls
            if c.get("status") == "error"
            or "error" in str(c.get("output", "")).lower()
            or "exception" in str(c.get("output", "")).lower()
        ]
        if failed_calls:
            return 0.30, f"Failure: {len(failed_calls)} tool calls resulted in runtime errors"

        # 6. Check negative pitfall violation
        if negative_pitfall and len(negative_pitfall.strip()) > 5:
            # Check for trap parameters (e.g. `--trap`, `param_name`)
            param_matches = re.findall(r"(--?[\w\-]+|\b\w+_param\b)", negative_pitfall)
            for param in param_matches:
                if param.lower() in lower_answer:
                    return 0.20, f"Failure: Output violated known negative pitfall constraint: {negative_pitfall[:60]}"

            # Check if answer actively adopts the pitfall without negation
            pitfall_clean = cls.normalize_answer(negative_pitfall)
            pitfall_words = [
                w for w in pitfall_clean.split()
                if len(w) > 4 and w not in {"avoid", "under", "circumstances", "should", "known", "pitfall", "commit"}
            ]
            if pitfall_words:
                matches = sum(1 for w in pitfall_words if w in lower_answer)
                match_ratio = matches / len(pitfall_words)
                # If high word overlap, check if negated or avoided
                if match_ratio >= 0.70:
                    negation_markers = ["avoid", "deliberately avoided", "not", "prevent", "reject", "never", "without"]
                    has_negation = any(marker in lower_answer for marker in negation_markers)
                    if not has_negation:
                        return 0.25, f"Failure: Output adopted known negative pitfall constraint: {negative_pitfall[:60]}"

        # 7. Check task relevance against task_input
        relevance_ratio = 0.50
        if task_input and len(task_input.strip()) > 10:
            # Strip prompt annotations like [Ground Truth...] or [Validation...]
            clean_query = re.sub(r"\[.*?\]", "", task_input).strip()
            instruction_stopwords = {
                "what", "which", "where", "when", "with", "from", "that", "this",
                "first", "task", "solve", "write", "create", "generate", "provide",
                "give", "explain", "describe", "compare", "compute", "calculate",
                "determine", "state", "find", "please", "using", "between",
            }
            query_tokens = [
                w for w in cls.normalize_answer(clean_query).split()
                if len(w) > 3 and w not in instruction_stopwords
            ]
            if len(query_tokens) >= 2:
                matched_query = sum(1 for w in query_tokens if w in lower_answer)
                relevance_ratio = matched_query / len(query_tokens)
                if relevance_ratio < 0.15 and len(query_tokens) >= 3:
                    return 0.30, f"Failure: Output appears completely off-topic from task input (relevance={relevance_ratio:.2f})"

        # 8. Multi-signal synthesis:
        # Base quality from substantive depth / length
        ans_len = len(clean_answer)
        if ans_len < 40:
            base_score = 0.45
        elif ans_len < 100:
            base_score = 0.65
        elif ans_len < 180:
            base_score = 0.75
        else:
            base_score = 0.80

        # Quality bonuses
        bonuses = 0.0

        # Relevance bonus
        if relevance_ratio >= 0.30:
            bonuses += 0.05
        if relevance_ratio >= 0.60:
            bonuses += 0.05

        # Strategy alignment bonus
        if positive_strategy:
            strat_tokens = [w for w in cls.normalize_answer(positive_strategy).split() if len(w) > 4]
            if strat_tokens and any(w in lower_answer for w in strat_tokens):
                bonuses += 0.05

        # Code syntax / implementation bonus
        has_code_syntax = bool(re.search(r"\b(def|class|return|import|for|while|const|let|function)\b|```|\b\w+\s*\(.*?\)", clean_answer))
        if has_code_syntax:
            bonuses += 0.05

        # Clean tool execution bonus
        if calls and not failed_calls:
            bonuses += 0.05

        # Dynamic scalar reward in [0.10, 0.95] (replaces static rubber stamp)
        final_score = round(max(0.10, min(0.95, base_score + bonuses)), 3)

        return final_score, f"Success: Output satisfies structural requirements and task constraints (R={final_score:.2f})"

    @classmethod
    def evaluate_task(
        cls,
        final_answer: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        negative_pitfall: Optional[str] = None,
        positive_strategy: Optional[str] = None,
        task_input: Optional[str] = None,
        task_domain: Optional[str] = None,
        ground_truth: Optional[str] = None,
    ) -> Tuple[float, str]:
        """
        Unified evaluation dispatcher. Automatically detects benchmark directives or ground truth
        embedded in task_input, routing to the specialized evaluator or multi-signal heuristic.
        """
        input_str = task_input or ""

        # A. Check for explicit or embedded ground truth reference
        gt = ground_truth
        if not gt and "[Ground Truth Reference:" in input_str:
            match = re.search(r"\[Ground Truth Reference:\s*(.*?)\]", input_str)
            if match:
                gt = match.group(1).strip()

        if gt:
            return cls.evaluate_hotpotqa(prediction=final_answer, ground_truth=gt)

        # B. Check for ToolBench validation criteria
        #
        # F2: the condition previously read
        #     `... in input_str or task_domain == "coding"`.
        # That second clause routed EVERY programming task to the tool-call validator,
        # which returns 0.10 whenever no tool call occurred -- so an ordinary
        # code-writing task was scored on whether its answer happened to contain a
        # double-quoted, JSON-parseable brace expression rather than on correctness.
        # Evaluator choice is now explicit at task level (see `DeterministicEvaluator.evaluate`);
        # `task_domain` no longer participates in routing.
        if "[Validation Criteria: Must match valid parameters:" in input_str:
            expected_avoid: List[str] = []
            if negative_pitfall:
                # Extract trapped params if any
                trap_params = re.findall(r"(--?[\w\-]+|\b\w+_param\b)", negative_pitfall)
                expected_avoid.extend(trap_params)

            val_match = re.search(r"\[Validation Criteria:\s*Must match valid parameters:\s*(.*?)\]", input_str)
            valid_params = None
            if val_match:
                try:
                    valid_params = json.loads(val_match.group(1).strip())
                except Exception:
                    pass

            return cls.evaluate_toolbench(
                tool_calls=tool_calls or [],
                expected_avoid_params=expected_avoid if expected_avoid else None,
                expected_valid_params=valid_params,
                final_answer=final_answer,
            )

        # C. General task evaluation with all signals
        return cls.evaluate_general_task(
            final_answer=final_answer,
            tool_calls=tool_calls,
            negative_pitfall=negative_pitfall,
            positive_strategy=positive_strategy,
            task_input=task_input,
            ground_truth=None,
        )

    # ------------------------------------------------------------------
    # F2 / F3: explicit evaluator selection returning the frozen contract
    # ------------------------------------------------------------------

    @classmethod
    def resolve_evaluator(
        cls,
        evaluator: Optional[Any] = None,
        task_input: Optional[str] = None,
        ground_truth: Optional[str] = None,
        task_domain: Optional[str] = None,
        evaluator_config: Optional[Dict[str, Any]] = None,
    ) -> EvaluatorName:
        """
        Decide which evaluator applies.

        Explicit task-level selection always wins. Otherwise infer from test directives,
        embedded tags, or task domain.
        """
        if evaluator is not None:
            return evaluator if isinstance(evaluator, EvaluatorName) else EvaluatorName(str(evaluator))

        cfg = evaluator_config or {}
        if cfg.get("test_code"):
            return EvaluatorName.PYTEST_EXECUTION

        input_str = task_input or ""
        if ground_truth or "[Ground Truth Reference:" in input_str:
            return EvaluatorName.EXACT_MATCH_F1

        if "[Validation Criteria: Must match valid parameters:" in input_str:
            return EvaluatorName.TOOLBENCH_TRAP

        # Check if task specifies executable test cases or requirements
        if extract_test_code_from_task_input(input_str) is not None:
            return EvaluatorName.PYTEST_EXECUTION

        return EvaluatorName.HEURISTIC

    @classmethod
    def evaluate(
        cls,
        final_answer: str,
        evaluator: Optional[Any] = None,
        evaluator_config: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        negative_pitfall: Optional[str] = None,
        positive_strategy: Optional[str] = None,
        task_input: Optional[str] = None,
        task_domain: Optional[str] = None,
        ground_truth: Optional[str] = None,
        outcome_threshold: float = DEFAULT_OUTCOME_THRESHOLD,
    ) -> EvaluationOutcome:
        """
        Single structured entry point. Returns the F3 outcome contract.

        This is the ONLY place a binary outcome is produced. Downstream consumers
        (including the trust layer) read it; they never re-derive it.
        """
        cfg = evaluator_config or {}
        chosen = cls.resolve_evaluator(
            evaluator=evaluator,
            task_input=task_input,
            ground_truth=ground_truth,
            task_domain=task_domain,
            evaluator_config=cfg,
        )
        # S11: the threshold that will actually be applied, resolved once.
        outcome_threshold = effective_outcome_threshold(chosen, outcome_threshold)

        if chosen == EvaluatorName.PYTEST_EXECUTION:
            # Extract test code from config or directly from task specification
            test_code = cfg.get("test_code") if "test_code" in cfg else extract_test_code_from_task_input(task_input or "")
            if not test_code or not test_code.strip():
                # Requirement 6: When independent verification is unavailable or inconclusive,
                # do not silently treat as success. Unverified outcomes receive no success reward.
                return EvaluationOutcome.from_reward(
                    reward=0.50,
                    evaluator_name=chosen,
                    evaluator_version=pytest_execution_evaluator.version,
                    reason="Inconclusive: No independent verification criteria or test suite available for coding task. Unverified execution cannot be classified as success.",
                    outcome_threshold=outcome_threshold,
                    details={"status": "inconclusive", "error": "missing_test_code"},
                )

            return pytest_execution_evaluator.evaluate(
                final_answer=final_answer,
                test_code=test_code,
                timeout_s=cfg.get("timeout_s"),
                solution_filename=cfg.get("solution_filename", "solution.py"),
                setup_code=cfg.get("setup_code", ""),
            )

        if chosen == EvaluatorName.EXACT_MATCH_F1:
            gt = ground_truth
            if not gt and task_input and "[Ground Truth Reference:" in task_input:
                m = re.search(r"\[Ground Truth Reference:\s*(.*?)\]", task_input)
                if m:
                    gt = m.group(1).strip()
            gt = gt or cfg.get("ground_truth", "")
            score, reason = cls.evaluate_hotpotqa(prediction=final_answer, ground_truth=gt)
            return EvaluationOutcome.from_reward(
                reward=score, evaluator_name=chosen, reason=reason, outcome_threshold=outcome_threshold
            )

        if chosen == EvaluatorName.STRICT_KEY_ANSWER:
            gt = ground_truth or cfg.get("ground_truth", "")
            distractor = cfg.get("distractor")
            task_category = cfg.get("task_category")
            score, reason = strict_key_answer_evaluator.evaluate(
                prediction=final_answer,
                ground_truth=gt,
                distractor=distractor,
                task_category=task_category,
            )
            return EvaluationOutcome.from_reward(
                reward=score,
                evaluator_name=chosen,
                evaluator_version=strict_key_answer_evaluator.version,
                reason=reason,
                outcome_threshold=outcome_threshold,
            )

        if chosen == EvaluatorName.TOOLBENCH_TRAP:
            expected_avoid: List[str] = []
            if negative_pitfall:
                expected_avoid.extend(re.findall(r"(--?[\w\-]+|\b\w+_param\b)", negative_pitfall))
            valid_params = cfg.get("expected_valid_params")
            if valid_params is None and task_input:
                m = re.search(r"\[Validation Criteria:\s*Must match valid parameters:\s*(.*?)\]", task_input)
                if m:
                    try:
                        valid_params = json.loads(m.group(1).strip())
                    except Exception:
                        valid_params = None
            score, reason = cls.evaluate_toolbench(
                tool_calls=tool_calls or [],
                expected_avoid_params=expected_avoid or None,
                expected_valid_params=valid_params,
                final_answer=final_answer,
            )
            return EvaluationOutcome.from_reward(
                reward=score, evaluator_name=chosen, reason=reason, outcome_threshold=outcome_threshold
            )

        # HEURISTIC -- smoke/testing only. Not permitted in research conditions.
        score, reason = cls.evaluate_general_task(
            final_answer=final_answer,
            tool_calls=tool_calls,
            negative_pitfall=negative_pitfall,
            positive_strategy=positive_strategy,
            task_input=task_input,
            task_domain=task_domain,
            ground_truth=None,
        )
        return EvaluationOutcome.from_reward(
            reward=score, evaluator_name=EvaluatorName.HEURISTIC, reason=reason, outcome_threshold=outcome_threshold
        )


# Global singleton evaluator
deterministic_evaluator = DeterministicEvaluator()
