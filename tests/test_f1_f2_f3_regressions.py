"""
F1 / F2 / F3 Correctness Regression Suite.

F1  A retry is an ATTEMPT, not an independent learning observation.
    One task produces N attempts but exactly ONE task-level outcome, one trust
    write, one counter increment, and one candidate memory.

F2  Evaluator selection is explicit at task level. `task_domain == "coding"` no
    longer forces the tool-call validator. Deterministic Python tasks are scored
    by actually executing a frozen test suite.

F3  The evaluator is the sole authority on success/failure. A trust policy consumes
    the outcome; it never defines it. successes + failures == task-level observations.

These are engineering-correctness tests. They assert nothing about which trust
mechanism is appropriate, and they do not depend on A-EMA's arithmetic.
"""

import asyncio
import os
import tempfile

import pytest

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import (
    ALPHA_SUCCESS,
    BETA_FAILURE,
    GAMMA_NEUTRAL,
    QUARANTINE_THRESHOLD,
    compute_next_trust,
)
from ai_service.tools.evaluator import (
    DeterministicEvaluator,
    deterministic_evaluator,
    extract_python_code,
    pytest_execution_evaluator,
)
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import (
    DEFAULT_OUTCOME_THRESHOLD,
    RESEARCH_GRADE_EVALUATORS,
    EvaluationOutcome,
    EvaluatorName,
    TaskExecuteRequest,
)

SEED_TRIGGER = "Fixing RecursionError in deep binary tree traversal"
SEED_TASK = "Fix the RecursionError raised by my recursive binary tree traversal function"

TEST_SUITE = (
    "from solution import add\n"
    "def test_add_positive():\n"
    "    assert add(2, 3) == 5\n"
    "def test_add_identity():\n"
    "    assert add(-1, 1) == 0\n"
)
CORRECT_CODE = "```python\ndef add(a, b):\n    return a + b\n```"
INCORRECT_CODE = "```python\ndef add(a, b):\n    return a - b\n```"


def _fresh_store() -> SQLiteMemoryStore:
    fd, path = tempfile.mkstemp(suffix=".db", prefix="f123_")
    os.close(fd)
    os.remove(path)
    return SQLiteMemoryStore(db_path=path)


def _seed_memory(**overrides) -> Experience:
    base = dict(
        id="mem_seed_001",
        task_domain=TaskDomain.CODING,
        trigger_condition=SEED_TRIGGER,
        strategy_lesson="Convert the recursion to an iterative traversal using collections.deque.",
        pitfall="Do not raise sys.setrecursionlimit.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    base.update(overrides)
    return Experience(**base)


# ==============================================================================
# F2 -- explicit evaluator selection
# ==============================================================================

def test_f2_coding_domain_no_longer_implies_toolbench():
    """The defect: `task_domain == "coding"` routed every program to the trap validator."""
    chosen = DeterministicEvaluator.resolve_evaluator(evaluator=None, task_input="Fix the recursion bug")
    assert chosen == EvaluatorName.HEURISTIC

    outcome = deterministic_evaluator.evaluate(
        final_answer="def walk(root):\n    return []",
        task_input="Fix the recursion bug",
    )
    assert outcome.evaluator_name != EvaluatorName.TOOLBENCH_TRAP
    assert outcome.reward != 0.10 or "Zero tool calls" not in outcome.reason


def test_f2_reward_no_longer_depends_on_incidental_json_braces():
    """
    Previously: an answer containing a double-quoted JSON object scored 0.92 while the
    same answer with a Python dict literal scored 0.10, purely from quote style.
    """
    answers = [
        "Use collections.deque for an iterative traversal.",
        "def walk(root):\n    seen = {'a': 1}\n    return seen",
        'Use this config: {"mode": "iterative", "limit": 1000}',
    ]
    rewards = [
        deterministic_evaluator.evaluate(final_answer=a, task_input="Fix the recursion bug").reward
        for a in answers
    ]
    assert max(rewards) - min(rewards) < 0.30, f"quote style still swings reward: {rewards}"


def test_f2_explicit_selection_overrides_inference():
    chosen = DeterministicEvaluator.resolve_evaluator(
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        task_input="Do it\n[Validation Criteria: Must match valid parameters: {\"m\": 1}]",
    )
    assert chosen == EvaluatorName.PYTEST_EXECUTION


def test_f2_toolbench_tasks_still_use_toolbench_evaluator():
    """Explicit selection."""
    outcome = deterministic_evaluator.evaluate(
        final_answer="Executed command.",
        evaluator=EvaluatorName.TOOLBENCH_TRAP,
        tool_calls=[{"name": "run", "args": {"mode": "fast"}, "status": "success"}],
        evaluator_config={"expected_valid_params": {"mode": "fast"}},
    )
    assert outcome.evaluator_name == EvaluatorName.TOOLBENCH_TRAP
    assert outcome.reward >= 0.90


def test_f2_toolbench_directive_inference_preserved():
    """The embedded bracket marker must still route to ToolBench without explicit selection."""
    outcome = deterministic_evaluator.evaluate(
        final_answer="Executed command.",
        task_input='Execute task\n[Validation Criteria: Must match valid parameters: {"mode": "fast"}]',
        tool_calls=[{"name": "run", "args": {"mode": "fast"}, "status": "success"}],
    )
    assert outcome.evaluator_name == EvaluatorName.TOOLBENCH_TRAP
    assert outcome.reward >= 0.90


def test_f2_ground_truth_directive_inference_preserved():
    outcome = deterministic_evaluator.evaluate(
        final_answer="The founder was Ada Lovelace.",
        task_input="Who wrote the first algorithm?\n[Ground Truth Reference: Ada Lovelace]",
    )
    assert outcome.evaluator_name == EvaluatorName.EXACT_MATCH_F1
    assert outcome.reward >= 0.85


def test_f2_heuristic_is_excluded_from_research_grade_evaluators():
    assert EvaluatorName.HEURISTIC not in RESEARCH_GRADE_EVALUATORS
    assert EvaluatorName.PYTEST_EXECUTION in RESEARCH_GRADE_EVALUATORS
    assert EvaluatorName.EXACT_MATCH_F1 in RESEARCH_GRADE_EVALUATORS
    assert EvaluatorName.TOOLBENCH_TRAP in RESEARCH_GRADE_EVALUATORS


# ==============================================================================
# F2 -- pytest execution evaluator
# ==============================================================================

def test_f2_correct_python_code_passes_deterministically():
    outcome = pytest_execution_evaluator.evaluate(
        final_answer=CORRECT_CODE, test_code=TEST_SUITE, timeout_s=30
    )
    assert outcome.reward == 1.0
    assert outcome.binary_outcome == 1
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION
    assert outcome.details["returncode"] == 0


def test_f2_incorrect_python_code_fails_deterministically():
    outcome = pytest_execution_evaluator.evaluate(
        final_answer=INCORRECT_CODE, test_code=TEST_SUITE, timeout_s=30
    )
    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert outcome.details["returncode"] != 0


def test_f2_same_candidate_same_tests_gives_same_outcome():
    runs = [
        pytest_execution_evaluator.evaluate(final_answer=CORRECT_CODE, test_code=TEST_SUITE, timeout_s=30)
        for _ in range(3)
    ]
    assert {r.reward for r in runs} == {1.0}
    assert {r.binary_outcome for r in runs} == {1}

    bad = [
        pytest_execution_evaluator.evaluate(final_answer=INCORRECT_CODE, test_code=TEST_SUITE, timeout_s=30)
        for _ in range(3)
    ]
    assert {r.reward for r in bad} == {0.0}


def test_f2_pytest_binarisation_is_exact():
    """reward is 0.0/1.0 and the threshold is 1.0, so binary == reward with no slack."""
    good = pytest_execution_evaluator.evaluate(final_answer=CORRECT_CODE, test_code=TEST_SUITE, timeout_s=30)
    assert good.outcome_threshold == 1.0
    assert float(good.binary_outcome) == good.reward


def test_f2_infinite_loop_is_killed_by_timeout():
    # The test suite must import `solution` so the non-terminating module body actually runs.
    outcome = pytest_execution_evaluator.evaluate(
        final_answer="```python\nwhile True:\n    pass\n```",
        test_code="import solution\ndef test_noop():\n    assert True\n",
        timeout_s=3,
    )
    assert outcome.reward == 0.0
    assert outcome.details.get("error") == "timeout"


def test_f2_missing_test_code_is_a_configuration_failure():
    outcome = pytest_execution_evaluator.evaluate(final_answer=CORRECT_CODE, test_code="")
    assert outcome.reward == 0.0
    assert outcome.details.get("error") == "missing_test_code"


def test_f2_code_extraction_handles_fences_and_bare_code():
    assert "def add" in extract_python_code(CORRECT_CODE)
    assert "```" not in extract_python_code(CORRECT_CODE)
    assert extract_python_code("def f():\n    return 1").startswith("def f")
    assert extract_python_code("") == ""


def test_f2_candidate_cannot_see_the_host_working_directory():
    """The subprocess runs in a throwaway dir; repo files must not be importable."""
    outcome = pytest_execution_evaluator.evaluate(
        final_answer="```python\nimport solution_sentinel_should_not_exist\n```",
        test_code="from solution import *\ndef test_x():\n    assert True\n",
        timeout_s=20,
    )
    assert outcome.reward == 0.0


# ==============================================================================
# F3 -- the frozen outcome contract
# ==============================================================================

def test_f3_binarisation_invariant_is_enforced():
    ok = EvaluationOutcome.from_reward(reward=0.9, evaluator_name=EvaluatorName.HEURISTIC)
    assert ok.binary_outcome == 1
    assert ok.outcome_threshold == DEFAULT_OUTCOME_THRESHOLD

    low = EvaluationOutcome.from_reward(reward=0.5, evaluator_name=EvaluatorName.HEURISTIC)
    assert low.binary_outcome == 0

    with pytest.raises(Exception):
        EvaluationOutcome(
            reward=0.2, binary_outcome=1, outcome_threshold=0.80,
            evaluator_name=EvaluatorName.HEURISTIC,
        )


def test_f3_continuous_reward_is_always_preserved():
    outcome = EvaluationOutcome.from_reward(reward=0.63, evaluator_name=EvaluatorName.HEURISTIC)
    assert outcome.reward == 0.63          # not collapsed to the binary value
    assert outcome.binary_outcome == 0
    assert outcome.binary_outcome == (1 if outcome.reward >= outcome.outcome_threshold else 0)


def test_f3_counters_follow_the_evaluator_not_the_trust_delta():
    """
    Discriminating case. trust 0.30 with R=0.60 moves trust UP (delta >= 0), so the old
    `delta >= 0 -> success` rule recorded a SUCCESS. The evaluator says R=0.60 is below
    threshold, so it is a FAILURE. The evaluator must win.
    """
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory(trust_score=0.30))

        new_trust, _ = compute_next_trust(0.30, 0.60)
        assert new_trust > 0.30, "precondition: trust must increase so delta >= 0"

        await store.update_trust(
            experience_id="mem_seed_001",
            new_trust=new_trust,
            reason="neutral outcome",
            binary_outcome=0,          # evaluator says failure
        )
        exp = await store.get_experience("mem_seed_001")
        assert exp.failures_count == 1, "evaluator outcome must drive the counter"
        assert exp.successes_count == 0
        assert exp.uses_count == 1

    asyncio.run(_run())


def test_f3_zero_delta_is_not_silently_a_success():
    """The F1 no-op writes had delta == 0 and were counted as successes."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory(trust_score=0.50))
        await store.update_trust(
            experience_id="mem_seed_001", new_trust=0.50, binary_outcome=0,
        )
        exp = await store.get_experience("mem_seed_001")
        assert exp.successes_count == 0
        assert exp.failures_count == 1

    asyncio.run(_run())


def test_f3_administrative_update_is_not_an_observation():
    """binary_outcome=None => trust/status may change, but no counter is touched."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        await store.update_trust(
            experience_id="mem_seed_001", new_trust=0.0, reason="manual_deletion",
        )
        exp = await store.get_experience("mem_seed_001")
        assert exp.trust_score == 0.0
        assert exp.uses_count == 0
        assert exp.successes_count == 0
        assert exp.failures_count == 0

    asyncio.run(_run())


def test_f3_invalid_binary_outcome_is_rejected():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        with pytest.raises(ValueError):
            await store.update_trust(
                experience_id="mem_seed_001", new_trust=0.5, binary_outcome=2,
            )

    asyncio.run(_run())


def test_f3_successes_plus_failures_equals_uses():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        for outcome in (1, 0, 1, 1, 0):
            exp = await store.get_experience("mem_seed_001")
            new_trust, _ = compute_next_trust(exp.trust_score, 1.0 if outcome else 0.0)
            await store.update_trust(
                experience_id="mem_seed_001", new_trust=new_trust, binary_outcome=outcome,
            )
        exp = await store.get_experience("mem_seed_001")
        assert exp.uses_count == 5
        assert exp.successes_count + exp.failures_count == exp.uses_count
        assert exp.successes_count == 3
        assert exp.failures_count == 2

    asyncio.run(_run())


# ==============================================================================
# F1 -- attempts vs task-level outcome
# ==============================================================================

def _run_failing_task_with_retries(store):
    """Drives the retry loop: pytest_execution on a MOCK answer always fails."""
    return execute_task(
        TaskExecuteRequest(
            task_input=SEED_TASK,
            task_domain=TaskDomain.CODING,
            memory_enabled=True,
            memory_mode=MemoryMode.ADAPTIVE,
            provider=ModelProvider.MOCK,
            evaluator=EvaluatorName.PYTEST_EXECUTION,
            evaluator_config={"test_code": TEST_SUITE, "timeout_s": 30},
        ),
        memory_store=store,
    )


def test_f1_retries_produce_many_attempts_but_one_task_outcome():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        result = await _run_failing_task_with_retries(store)

        assert result.n_attempts >= 2, "precondition: the retry loop must have engaged"
        assert len(result.attempts) == result.n_attempts

        terminal = [a for a in result.attempts if a.is_terminal]
        assert len(terminal) == 1, "exactly one attempt may be terminal"
        assert terminal[0].attempt_index == result.n_attempts
        assert result.outcome_score == terminal[0].reward
        assert result.binary_outcome == terminal[0].binary_outcome

    asyncio.run(_run())


def test_f1_retries_do_not_multiply_trust_evidence():
    """The core defect: 3 attempts previously wrote 3 trust rows and uses=3, s=2, f=1."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        result = await _run_failing_task_with_retries(store)
        assert result.n_attempts >= 2

        exp = await store.get_experience("mem_seed_001")
        assert exp.uses_count == 1, f"one task must yield one observation, got {exp.uses_count}"
        assert exp.successes_count + exp.failures_count == 1
        assert exp.failures_count == 1

        with store._get_connection() as conn:
            rows = conn.execute(
                "SELECT COUNT(*) AS n FROM trust_history WHERE experience_id = ?",
                ("mem_seed_001",),
            ).fetchone()
        assert rows["n"] == 1, f"expected 1 trust_history row, got {rows['n']}"

    asyncio.run(_run())


def test_f1_retries_create_exactly_one_candidate_memory():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        result = await _run_failing_task_with_retries(store)
        assert result.n_attempts >= 2

        all_exps = await store.list_experiences()
        candidates = [e for e in all_exps if e.status == ExperienceStatus.CANDIDATE]
        assert len(candidates) == 1, f"one task must yield one candidate, got {len(candidates)}"
        assert len(all_exps) == 2

    asyncio.run(_run())


def test_f1_per_attempt_diagnostics_are_retained():
    """Retry capability is preserved -- attempt detail must not be discarded."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        result = await _run_failing_task_with_retries(store)

        indices = [a.attempt_index for a in result.attempts]
        assert indices == sorted(indices)
        assert indices == list(range(1, result.n_attempts + 1))
        for a in result.attempts:
            assert 0.0 <= a.reward <= 1.0
            assert a.binary_outcome in (0, 1)
            assert a.evaluator_name == EvaluatorName.PYTEST_EXECUTION

    asyncio.run(_run())


def test_f1_retry_capability_is_not_disabled():
    """MAX_CYCLICAL_LOOPS must not have been reduced to 1 to make accounting convenient."""
    from ai_service.config import settings
    assert settings.MAX_CYCLICAL_LOOPS > 1


def test_f1_trust_node_performs_no_io():
    """trust_node sits on the cycle and must stay pure; persistence lives in execute_task."""
    import importlib
    import inspect

    # NB: `from ai_service.nodes import trust_node` resolves to the re-exported
    # FUNCTION, not the module -- import the module explicitly.
    module = importlib.import_module("ai_service.nodes.trust_node")
    src = inspect.getsource(module.async_trust_node)
    assert "update_trust(" not in src
    assert "add_experience(" not in src


def test_f1_single_attempt_task_still_records_one_observation():
    """Guards against the dedup logic skipping the non-retry path."""
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        result = await execute_task(
            TaskExecuteRequest(
                task_input=SEED_TASK,
                task_domain=TaskDomain.CODING,
                memory_enabled=True,
                memory_mode=MemoryMode.ADAPTIVE,
                provider=ModelProvider.MOCK,
                evaluator=EvaluatorName.HEURISTIC,
            ),
            memory_store=store,
        )
        assert result.n_attempts >= 1
        exp = await store.get_experience("mem_seed_001")
        assert exp.uses_count == 1

    asyncio.run(_run())


def test_f1_memory_off_records_no_observation():
    async def _run():
        store = _fresh_store()
        await store.add_experience(_seed_memory())
        await execute_task(
            TaskExecuteRequest(
                task_input=SEED_TASK,
                task_domain=TaskDomain.CODING,
                memory_enabled=False,
                memory_mode=MemoryMode.OFF,
                provider=ModelProvider.MOCK,
                evaluator=EvaluatorName.HEURISTIC,
            ),
            memory_store=store,
        )
        exp = await store.get_experience("mem_seed_001")
        assert exp.uses_count == 0
        assert exp.trust_score == 0.75

    asyncio.run(_run())


# ==============================================================================
# Guard: the trust mechanism itself is unchanged
# ==============================================================================

def test_aema_constants_and_arithmetic_are_unchanged():
    assert ALPHA_SUCCESS == 0.85
    assert BETA_FAILURE == 0.70
    assert GAMMA_NEUTRAL == 0.80
    assert QUARANTINE_THRESHOLD == 0.35

    assert compute_next_trust(0.75, 0.95)[0] == pytest.approx(0.85 * 0.75 + 0.15, abs=1e-4)
    assert compute_next_trust(0.75, 0.10)[0] == pytest.approx(0.70 * 0.75, abs=1e-4)
    assert compute_next_trust(0.75, 0.60)[0] == pytest.approx(0.80 * 0.75 + 0.20 * 0.60, abs=1e-4)


def test_no_new_trust_mechanism_was_introduced():
    """
    Step 1 added the TrustPolicy abstraction and experiment infrastructure (approved).
    It must NOT have added a new MECHANISM. Beta-Bernoulli / SPRT remain forbidden as
    policies, and the registry must expose only the ported A-EMA plus the no-op static
    policy used to express similarity-only retrieval.

    NB: `ai_service.trust_math` (Beta/LCB) is PRE-EXISTING and is still used by the
    legacy ADAPTIVE retrieval scoring. Preserving it is required to avoid changing
    retrieval behaviour; it is not reachable from TrustPolicy.
    """
    import pathlib

    from ai_service.trust.registry import available_policies

    assert available_policies() == ["aema", "static"]

    root = pathlib.Path(__file__).resolve().parents[1]
    # NB: `ConditionSpec` is approved Step-1.5 harness infrastructure (E0/E1 declaration)
    # and is no longer banned. What remains banned is any new trust MECHANISM.
    banned = [
        "BetaBernoulliPolicy",
        "SPRTPolicy",
        "sequential_probability_ratio",
    ]
    targets = []
    for sub in ("ai-service", "models", "backend"):
        targets.extend((root / sub).rglob("*.py"))

    for path in targets:
        if "__pycache__" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in banned:
            assert token not in text, f"{token} found in {path.relative_to(root)}"
