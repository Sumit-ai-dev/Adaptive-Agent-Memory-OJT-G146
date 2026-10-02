"""
Comprehensive Unit Tests for Deterministic Multi-Signal Reward Evaluator (Topic 1).
Validates:
  1. 10 Known-Good Answers across domains produce R_t >= 0.80.
  2. 10 Known-Bad Answers across domains produce R_t < 0.40.
  3. Empty, truncated, and garbage answers produce R_t <= 0.15.
  4. Elimination of hardcoded 0.88 rubber stamp across heterogeneous inputs.
  5. Automatic routing via evaluate_task for benchmark directives.
"""

import pytest
from ai_service.tools.evaluator import DeterministicEvaluator, deterministic_evaluator


def test_10_known_good_answers_score_above_80():
    """
    Topic 1 Verification: Feed 10 known-good answers across domains -> should score >= 0.80.
    """
    evaluator = DeterministicEvaluator()
    good_cases = [
        # 1. HotpotQA exact match
        {
            "name": "HotpotQA exact match",
            "fn": lambda: evaluator.evaluate_hotpotqa(
                prediction="Christopher Nolan",
                ground_truth="Christopher Nolan",
            ),
        },
        # 2. HotpotQA answer containing ground truth key entity
        {
            "name": "HotpotQA key entity contained",
            "fn": lambda: evaluator.evaluate_hotpotqa(
                prediction="The film was directed by Christopher Nolan in 2010 with high acclaim.",
                ground_truth="Christopher Nolan",
            ),
        },
        # 3. HotpotQA high token F1
        {
            "name": "HotpotQA high token F1",
            "fn": lambda: evaluator.evaluate_hotpotqa(
                prediction="Iron Man was released in May 2008 before Thor in 2011.",
                ground_truth="Iron Man was released before Thor in May 2008.",
            ),
        },
        # 4. ToolBench valid parameters matching specification
        {
            "name": "ToolBench valid parameters",
            "fn": lambda: evaluator.evaluate_toolbench(
                tool_calls=[{"name": "fetch_user", "args": {"user_id": "u123", "version": "v2"}, "status": "success"}],
                expected_valid_params={"user_id": "u123", "version": "v2"},
            ),
        },
        # 5. ToolBench clean tool execution without traps
        {
            "name": "ToolBench clean execution",
            "fn": lambda: evaluator.evaluate_toolbench(
                tool_calls=[{"name": "execute_query", "args": {"limit": 10}, "status": "success", "output": "results ok"}],
                expected_avoid_params=["--legacy-mode"],
            ),
        },
        # 6. ALFWorld goal achieved efficiently
        {
            "name": "ALFWorld goal achieved",
            "fn": lambda: evaluator.evaluate_alfworld(
                environment_won=True,
                steps_taken=6,
                max_steps=30,
            ),
        },
        # 7. General research task with detailed answer and successful search tool
        {
            "name": "General research with search tool",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="Based on verified multi-hop analysis, Iron Man was officially released on May 2, 2008, while Thor premiered on May 6, 2011. Chronological order confirms Iron Man preceded Thor.",
                tool_calls=[{"name": "duckduckgo_search", "status": "success", "output": "Iron Man release date 2008"}],
                positive_strategy="Cross-reference chronological release schedules.",
                task_input="Which movie was released first, Iron Man or Thor?",
            ),
        },
        # 8. General coding task with structured function and clean syntax
        {
            "name": "General coding solution",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="To compute Fibonacci numbers in linear time, use an iterative accumulator approach avoiding redundant recursion: def fib(n): a, b = 0, 1; for _ in range(n): a, b = b, a + b; return a.",
                task_input="Write an efficient Python function to compute Fibonacci numbers.",
                positive_strategy="Use iterative dynamic programming rather than naive exponential recursion.",
            ),
        },
        # 9. General task avoiding negative pitfall
        {
            "name": "General task respecting negative constraints",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="Comparing release dates chronologically: Iron Man (2008) debuted earlier than Thor (2011). We deliberately avoid alphabetical sorting assumptions.",
                negative_pitfall="Do not assume alphabetical order matches timeline.",
                task_input="Compare release dates of Iron Man and Thor.",
            ),
        },
        # 10. Multi-signal synthesis with clear structural depth
        {
            "name": "Structured synthesis",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="1. Identify target entities: Apollo 11 and Apollo 12. 2. Verify launch dates: Apollo 11 launched July 16, 1969; Apollo 12 launched November 14, 1969. 3. Synthesize result: Apollo 11 was the earlier lunar mission.",
                task_input="Which mission launched first, Apollo 11 or Apollo 12?",
            ),
        },
    ]

    for case in good_cases:
        score, reason = case["fn"]()
        assert score >= 0.80, f"Case '{case['name']}' failed: expected score >= 0.80, got {score:.2f} ({reason})"


def test_10_known_bad_answers_score_below_40():
    """
    Topic 1 Verification: Feed 10 known-bad answers across domains -> should score < 0.40.
    """
    evaluator = DeterministicEvaluator()
    bad_cases = [
        # 1. HotpotQA wrong answer (zero overlap with ground truth)
        {
            "name": "HotpotQA incorrect answer",
            "fn": lambda: evaluator.evaluate_hotpotqa(
                prediction="Steven Spielberg directed the movie.",
                ground_truth="Christopher Nolan",
            ),
        },
        # 2. HotpotQA deceived by distractor entity
        {
            "name": "HotpotQA distractor trap",
            "fn": lambda: evaluator.evaluate_hotpotqa(
                prediction="The answer was determined to be Quentin Tarantino after reviewing records.",
                ground_truth="Christopher Nolan",
                distractors=["Quentin Tarantino", "David Fincher"],
            ),
        },
        # 3. ToolBench using deprecated parameter trap
        {
            "name": "ToolBench deprecated parameter",
            "fn": lambda: evaluator.evaluate_toolbench(
                tool_calls=[{"name": "fetch", "args": {"--legacy-mode": True, "id": 10}, "status": "success"}],
                expected_avoid_params=["--legacy-mode"],
            ),
        },
        # 4. ToolBench tool call with runtime exception
        {
            "name": "ToolBench runtime exception",
            "fn": lambda: evaluator.evaluate_toolbench(
                tool_calls=[{"name": "fetch", "args": {"id": 10}, "status": "error", "output": "ConnectionTimeout: server failed"}],
            ),
        },
        # 5. ALFWorld environment failed goal
        {
            "name": "ALFWorld goal failed",
            "fn": lambda: evaluator.evaluate_alfworld(
                environment_won=False,
                steps_taken=30,
                max_steps=30,
            ),
        },
        # 6. General task explicit refusal
        {
            "name": "General task refusal",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="I cannot answer this question because I do not know the information requested.",
                task_input="What is the capital of Atlantis?",
            ),
        },
        # 7. General task negative pitfall violation (uses forbidden parameter)
        {
            "name": "Negative pitfall violation",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="Running execution using --force-legacy-override parameter now.",
                negative_pitfall="Do not use --force-legacy-override parameter.",
                task_input="Execute database migration.",
            ),
        },
        # 8. General task with tool call failure
        {
            "name": "Tool call runtime error",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="Attempted to retrieve the data but encountered errors.",
                tool_calls=[{"name": "api_fetch", "status": "error", "output": "HTTP 500 Internal Error"}],
                task_input="Fetch latest telemetry metrics.",
            ),
        },
        # 9. General task degenerative repetition loop
        {
            "name": "Degenerative repetition loop",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="the movie was the movie was the movie was the movie was the movie was",
                task_input="Which movie was released first?",
            ),
        },
        # 10. General task completely off-topic
        {
            "name": "Off-topic answer",
            "fn": lambda: evaluator.evaluate_general_task(
                final_answer="Baking chocolate chip cookies requires flour, sugar, butter, and semi-sweet chocolate morsels baked at 375 degrees Fahrenheit.",
                task_input="What is the time complexity of quicksort in the worst case scenario?",
            ),
        },
    ]

    for case in bad_cases:
        score, reason = case["fn"]()
        assert score < 0.40, f"Case '{case['name']}' failed: expected score < 0.40, got {score:.2f} ({reason})"


def test_empty_and_garbage_answers_score_near_point_10():
    """
    Topic 1 Verification: Feed empty/garbage answers -> should score <= 0.15.
    """
    evaluator = DeterministicEvaluator()

    # Empty string
    score_empty, reason_empty = evaluator.evaluate_general_task(final_answer="")
    assert score_empty == 0.0, f"Expected 0.0 for empty answer, got {score_empty}"

    # Whitespace only
    score_ws, _ = evaluator.evaluate_general_task(final_answer="   \n\t  ")
    assert score_ws == 0.0, f"Expected 0.0 for whitespace answer, got {score_ws}"

    # Truncated answer (< 15 chars)
    score_trunc, _ = evaluator.evaluate_general_task(final_answer="yes")
    assert score_trunc <= 0.10, f"Expected <= 0.10 for truncated answer, got {score_trunc}"

    # Zero tool calls for toolbench
    score_tb_empty, _ = evaluator.evaluate_toolbench(tool_calls=[])
    assert score_tb_empty <= 0.15, f"Expected <= 0.15 for empty tool calls, got {score_tb_empty}"


def test_no_hardcoded_point_88_rubber_stamp():
    """
    Verify that scores are dynamic and continuous rather than fixed at 0.88.
    """
    evaluator = DeterministicEvaluator()

    scores = set()
    test_inputs = [
        ("Short answer with valid details.", "What is DNA?"),
        ("DNA (deoxyribonucleic acid) is a polymer composed of two polynucleotide chains that coil around each other to form a double helix carrying genetic instructions.", "What is DNA?"),
        ("A comprehensive multi-sentence breakdown of photosynthesis in C3 versus C4 plants with biochemical pathways.", "Explain C3 and C4 photosynthesis."),
    ]

    for ans, query in test_inputs:
        score, _ = evaluator.evaluate_general_task(final_answer=ans, task_input=query)
        scores.add(score)

    assert len(scores) > 1, f"Evaluator produced identical scores across diverse answers: {scores}"
    assert 0.88 not in scores or len(scores) >= 2, "Evaluator is still statically outputting 0.88"


def test_evaluate_task_unified_routing():
    """
    Verify evaluate_task parses embedded benchmark directives and routes properly.
    """
    evaluator = DeterministicEvaluator()

    # Ground truth tag embedded
    score_gt, reason_gt = evaluator.evaluate_task(
        final_answer="The founder was Ada Lovelace.",
        task_input="Who wrote the first computer algorithm?\n[Ground Truth Reference: Ada Lovelace]",
    )
    assert score_gt >= 0.85
    assert "Ground truth" in reason_gt

    # Tool criteria tag embedded
    score_tool, reason_tool = evaluator.evaluate_task(
        final_answer="Executed command.",
        task_input='Execute task\n[Validation Criteria: Must match valid parameters: {"mode": "fast"}]',
        tool_calls=[{"name": "run", "args": {"mode": "fast"}, "status": "success"}],
    )
    assert score_tool >= 0.90
    assert "parameter" in reason_tool.lower()
