"""
Comprehensive unit and integration test suite for MemoryAgentBench Evaluator and Pilot Manifests.
Verifies:
1. Strict equivalence with official HUST-AI-HYZ/MemoryAgentBench evaluation logic.
2. Exact Match, Substring Exact Match, and Token F1 calculations.
3. Output parsing ('Answer:' extraction vs direct responses).
4. Conflict Resolution diagnostic metrics (obsolete fact intrusion detection).
5. Manifest integrity and data validation for the 25 CR and 25 AR pilot tasks.
6. Zero condition leakage (blind to agent condition and trial).
"""

import json
from pathlib import Path
import pytest

from benchmarks.evaluators.memoryagentbench_evaluator import (
    MemoryAgentBenchEvaluator,
    drqa_exact_match_score,
    extract_xml_answer,
    f1_score,
    normalize_answer,
    parse_output,
    substring_exact_match_score,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "benchmarks" / "data" / "memoryagentbench"


# ============================================================================
# 1. TEXT NORMALIZATION & BASE SCORING TESTS
# ============================================================================

def test_official_text_normalization():
    # Article removal (a, an, the)
    assert normalize_answer("The Fairly OddParents") == "fairly oddparents"
    assert normalize_answer("a rugby union match") == "rugby union match"
    assert normalize_answer("An Apple") == "apple"

    # Punctuation removal
    assert normalize_answer("pesäpallo.") == "pesäpallo"
    assert normalize_answer("Washington, D.C.") == "washington dc"
    assert normalize_answer("Free as a Bird's") == "free as birds"

    # Whitespace collapse & lowercase
    assert normalize_answer("  University   of   Pisa \n\t ") == "university of pisa"


def test_official_token_f1():
    # Perfect match
    f1, prec, rec = f1_score("University of California, Berkeley", "University of California, Berkeley")
    assert f1 == 1.0
    assert prec == 1.0
    assert rec == 1.0

    # Partial match
    # Pred: "10th century", GT: "in the 10th and 11th centuries"
    # Norm Pred: "10th century" (2 tokens: 10th, century)
    # Norm GT: "in 10th and 11th centuries" (5 tokens)
    # Common: "10th" (1), "century" != "centuries", so 1 common token
    f1, prec, rec = f1_score("10th century", "in the 10th and 11th centuries")
    assert prec == 0.5  # 1 / 2
    assert rec == 0.2   # 1 / 5
    assert f1 == pytest.approx((2 * 0.5 * 0.2) / (0.5 + 0.2))

    # Special answers: yes/no
    f1, _, _ = f1_score("yes", "no")
    assert f1 == 0.0


def test_substring_exact_match():
    # Target appears as substring
    assert substring_exact_match_score("The sport was created in India.", "India") == 1.0
    assert substring_exact_match_score("Answer: pesäpallo is the answer", "pesäpallo") == 1.0

    # Target does not appear
    assert substring_exact_match_score("The sport was created in England.", "India") == 0.0

    # Punctuation and case invariance
    assert substring_exact_match_score("Located in Washington, D.C.!", "Washington DC") == 1.0


def test_parse_output():
    # Prefix extraction
    assert parse_output("Answer: India") == "India"
    assert parse_output("The analysis is long.\nAnswer: pesäpallo\nDone.") == "pesäpallo"
    assert parse_output("ANSWER: University of California, Berkeley") == "University of California, Berkeley"

    # Direct line without prefix
    assert parse_output("India\nSome follow up") == "India"


# ============================================================================
# 1B. XML ANSWER EXTRACTION & REGRESSION TESTS
# ============================================================================

def test_extract_xml_answer():
    # Standard tags
    assert extract_xml_answer("<answer>London</answer>") == "London"
    # Multiline and whitespace stripping
    assert extract_xml_answer("Thinking...\n<answer>\n  London\n</answer>") == "London"
    # Case-insensitive tag matching
    assert extract_xml_answer("<ANSWER>Paris</ANSWER>") == "Paris"
    assert extract_xml_answer("<Answer>New Delhi</Answer>") == "New Delhi"
    # Unclosed tag at end of response (e.g. truncated generation)
    assert extract_xml_answer("The result is <answer>London") == "London"
    # Whitespace-only inside tag falls back to None
    assert extract_xml_answer("<answer>   </answer>") is None
    # No tag falls back to None
    assert extract_xml_answer("Answer: London") is None
    assert extract_xml_answer("") is None

    # parse_output integration with XML tags and Answer: prefix
    assert parse_output("Thought process...\n<answer>London</answer>") == "London"
    assert parse_output("Thought process...\n<answer>Answer: London</answer>") == "London"


def test_token_f1_with_xml_tags():
    # Verify XML tags do NOT contaminate normalized tokens with 'answer'
    assert normalize_answer("<answer>London</answer>") == "london"
    assert normalize_answer("<answer> pesäpallo </answer>") == "pesäpallo"

    # Perfect token F1 between XML-wrapped output and clean ground truth
    f1, prec, rec = f1_score("<answer>London</answer>", "London")
    assert f1 == 1.0
    assert prec == 1.0
    assert rec == 1.0

    # Multi-word ground truth
    f1, prec, rec = f1_score(
        "<answer>University of California, Berkeley</answer>",
        "University of California, Berkeley",
    )
    assert f1 == 1.0
    assert prec == 1.0
    assert rec == 1.0


def test_substring_exact_match_negation_and_obsolescence():
    # Negated target must return 0.0
    assert substring_exact_match_score("The answer is not Paris", "Paris") == 0.0
    assert substring_exact_match_score("It is no longer Paris", "Paris") == 0.0
    assert substring_exact_match_score("Paris is not the answer", "Paris") == 0.0
    assert substring_exact_match_score("Paris is incorrect", "Paris") == 0.0

    # Compound sentence with negation: affirmative target matches, negated does not
    pred = "The answer is not Paris, it is London."
    assert substring_exact_match_score(pred, "London") == 1.0
    assert substring_exact_match_score(pred, "Paris") == 0.0

    # Concession and obsolescence: superseded target does not match, updated target matches
    pred_concession = "Although previously Paris, it is now London."
    assert substring_exact_match_score(pred_concession, "London") == 1.0
    assert substring_exact_match_score(pred_concession, "Paris") == 0.0

    pred_superseded = "Paris was superseded by London."
    assert substring_exact_match_score(pred_superseded, "London") == 1.0
    assert substring_exact_match_score(pred_superseded, "Paris") == 0.0

    pred_originally = "It was originally Paris, but later changed to London."
    assert substring_exact_match_score(pred_originally, "London") == 1.0
    assert substring_exact_match_score(pred_originally, "Paris") == 0.0

    # Word boundary enforcement: substrings inside other words must not match
    assert substring_exact_match_score("Indiaindia", "India") == 0.0
    assert substring_exact_match_score("cardinal", "car") == 0.0
    assert substring_exact_match_score("The car is blue.", "car") == 1.0


# ============================================================================
# 2. EVALUATOR COMPREHENSIVE INTEGRATION TESTS
# ============================================================================

def test_evaluator_correct_prediction():
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "cr_test_01",
        "ground_truth_answers": ["India"],
        "obsolete_answers": ["England"],
        "question": "Which country was rugby union created in?"
    }

    outcome = evaluator.evaluate(task, "Answer: India")
    assert outcome.passed is True
    assert outcome.score == 1.0
    assert outcome.metrics["official"]["substring_exact_match"] == 1.0
    assert outcome.metrics["official"]["exact_match"] == 1.0
    assert outcome.metrics["official"]["token_f1"] == 1.0
    assert outcome.metrics["aema_diagnostics"]["is_obsolete_fact_intrusion"] is False
    assert outcome.failure_reason is None


def test_evaluator_conflict_resolution_obsolete_fact_detection():
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "cr_test_02",
        "ground_truth_answers": ["India"],
        "obsolete_answers": ["England"],
        "question": "Which country was rugby union created in?"
    }

    # Agent recalled the obsolete fact (England) instead of updated fact (India)
    outcome = evaluator.evaluate(task, "Answer: England")
    assert outcome.passed is False
    assert outcome.score == 0.0
    assert outcome.metrics["official"]["substring_exact_match"] == 0.0
    assert outcome.metrics["aema_diagnostics"]["is_obsolete_fact_intrusion"] is True
    assert "recalled superseded obsolete fact" in outcome.failure_reason


def test_evaluator_telemetry_isolation():
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "ar_test_01",
        "ground_truth_answers": ["France"],
        "question": "In what country is Normandy located?"
    }
    telemetry = {
        "quarantined_memory_ids": ["mem_old_1", "mem_old_2"],
        "active_memory_ids": ["mem_active_1"]
    }

    outcome = evaluator.evaluate(task, "Normandy is in France.", execution_metadata=telemetry)
    assert outcome.passed is True
    assert outcome.metrics["official"]["substring_exact_match"] == 1.0
    # Telemetry is strictly placed in diagnostics, not modifying official metrics
    assert outcome.metrics["aema_diagnostics"]["quarantined_count"] == 2
    assert outcome.metrics["aema_diagnostics"]["quarantine_applied"] is True


def test_evaluator_zero_condition_bias():
    evaluator = MemoryAgentBenchEvaluator()
    import inspect
    sig = inspect.signature(evaluator.evaluate)
    param_names = list(sig.parameters.keys())
    assert "condition" not in param_names
    assert "condition_name" not in param_names
    assert "trial" not in param_names
    assert "trial_index" not in param_names


def test_evaluator_xml_answer_and_scratchpad_reasoning():
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "cr_test_03",
        "ground_truth_answers": ["India"],
        "obsolete_answers": ["England"],
        "question": "Which country was rugby union created in?"
    }

    # Model reasons about England in scratchpad, but declares India in <answer> tag
    output = (
        "Let me evaluate the facts step by step.\n"
        "Fact 100 stated that rugby union was created in England.\n"
        "However, Fact 186 explicitly updated this: rugby union was created in India.\n"
        "Therefore, England is outdated and the current correct answer is India.\n"
        "<answer>India</answer>"
    )

    outcome = evaluator.evaluate(task, output)
    assert outcome.passed is True
    assert outcome.score == 1.0
    assert outcome.metrics["official"]["exact_match"] == 1.0
    assert outcome.metrics["official"]["substring_exact_match"] == 1.0
    assert outcome.metrics["official"]["token_f1"] == 1.0
    assert outcome.metrics["aema_diagnostics"]["is_obsolete_fact_intrusion"] is False
    assert outcome.failure_reason is None


def test_evaluator_obsolete_intrusion_prevention_with_scratchpad_reasoning():
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "cr_test_04",
        "ground_truth_answers": ["India"],
        "obsolete_answers": ["England"],
        "question": "Which country was rugby union created in?"
    }

    # Case 1: Model rejects obsolete England in reasoning, but answers with wrong non-obsolete answer
    output_wrong_new = (
        "Fact 100 stated England, but that fact is obsolete.\n"
        "I am not sure of the new country, but guessing France.\n"
        "<answer>France</answer>"
    )
    outcome1 = evaluator.evaluate(task, output_wrong_new)
    assert outcome1.passed is False
    assert outcome1.score == 0.0
    assert outcome1.metrics["aema_diagnostics"]["is_obsolete_fact_intrusion"] is False
    assert outcome1.failure_reason == "Prediction did not match ground truth"

    # Case 2: Model declares the obsolete fact inside <answer>
    output_declared_obsolete = (
        "Fact 100 stated England, and Fact 186 stated India.\n"
        "I will stick with the earlier historical fact.\n"
        "<answer>England</answer>"
    )
    outcome2 = evaluator.evaluate(task, output_declared_obsolete)
    assert outcome2.passed is False
    assert outcome2.score == 0.0
    assert outcome2.metrics["aema_diagnostics"]["is_obsolete_fact_intrusion"] is True
    assert "recalled superseded obsolete fact" in outcome2.failure_reason


# ============================================================================
# 3. PILOT MANIFEST INTEGRITY TESTS
# ============================================================================

def test_pilot_conflict_resolution_manifest_exists_and_valid():
    cr_path = DATA_DIR / "pilot_conflict_resolution_25.json"
    assert cr_path.exists(), f"Missing manifest: {cr_path}"

    with open(cr_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("benchmark") == "MemoryAgentBench"
    assert data.get("competency") == "Conflict_Resolution"
    assert data.get("total_pilot_tasks") == 25
    tasks = data.get("tasks", [])
    assert len(tasks) == 25

    for idx, t in enumerate(tasks):
        assert "task_id" in t
        assert "question" in t
        assert "ground_truth_answers" in t
        assert len(t["ground_truth_answers"]) > 0
        assert t["pilot_subset"] is True


def test_pilot_accurate_retrieval_manifest_exists_and_valid():
    ar_path = DATA_DIR / "pilot_accurate_retrieval_25.json"
    assert ar_path.exists(), f"Missing manifest: {ar_path}"

    with open(ar_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("benchmark") == "MemoryAgentBench"
    assert data.get("competency") == "Accurate_Retrieval"
    assert data.get("total_pilot_tasks") == 25
    tasks = data.get("tasks", [])
    assert len(tasks) == 25

    for idx, t in enumerate(tasks):
        assert "task_id" in t
        assert "question" in t
        assert "ground_truth_answers" in t
        assert len(t["ground_truth_answers"]) > 0
        assert t["pilot_subset"] is True
