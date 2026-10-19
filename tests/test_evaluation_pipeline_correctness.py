"""
Regression Test Suite: Evaluation Pipeline Correctness & Independent Code Verification.

Verifies:
1. Exact reproduction: Always-True is_even fails independent execution verification.
2. Correct is_even implementation passes.
3. Always-False is_even implementation fails.
4. Missing or malformed implementations do not receive positive results.
5. LLM claims of success cannot override verified test failures.
6. Unverified outcomes do not receive success rewards.
7. Trust updates strictly follow the verified outcome.
"""

import os
import tempfile
import pytest

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import compute_next_trust
from ai_service.tools.evaluator import (
    DeterministicEvaluator,
    deterministic_evaluator,
    extract_test_code_from_task_input,
    pytest_execution_evaluator,
)
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import EvaluatorName, OutcomeQuality, TaskExecuteRequest


REPRODUCTION_TASK_INPUT = """Implement or evaluate this exact function:

def is_even(n):
    return True

Required behavior:
- is_even(2) == True
- is_even(3) == False
- is_even(5) == False"""


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="eval_test_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_test_extraction_from_task_input():
    """Verify test assertions are accurately extracted from task specifications."""
    test_code = extract_test_code_from_task_input(REPRODUCTION_TASK_INPUT)
    assert test_code is not None
    assert "def test_task_requirements():" in test_code
    assert "assert is_even(2) == True" in test_code
    assert "assert is_even(3) == False" in test_code
    assert "assert is_even(5) == False" in test_code


def test_always_true_implementation_fails():
    """Reproduction: Always-True is_even fails independent execution."""
    broken_code = "def is_even(n):\n    return True\n"
    outcome = deterministic_evaluator.evaluate(
        final_answer=broken_code,
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain="coding",
    )
    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION
    assert "AssertionError" in outcome.reason or "Failure" in outcome.reason


def test_correct_implementation_passes():
    """Correct is_even implementation passes independent execution."""
    correct_code = "def is_even(n):\n    return n % 2 == 0\n"
    outcome = deterministic_evaluator.evaluate(
        final_answer=correct_code,
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain="coding",
    )
    assert outcome.reward == 1.0
    assert outcome.binary_outcome == 1
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION
    assert "all tests passed" in outcome.reason.lower()


def test_always_false_implementation_fails():
    """Always-False is_even fails independent execution."""
    false_code = "def is_even(n):\n    return False\n"
    outcome = deterministic_evaluator.evaluate(
        final_answer=false_code,
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain="coding",
    )
    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION
    assert "AssertionError" in outcome.reason or "Failure" in outcome.reason


def test_missing_or_malformed_implementation():
    """Missing or malformed implementations must not receive positive results."""
    # 1. Non-code conversational response
    non_code_answer = "I think the function is even when it divides by two evenly without remainder."
    outcome_non_code = deterministic_evaluator.evaluate(
        final_answer=non_code_answer,
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain="coding",
    )
    assert outcome_non_code.reward == 0.0
    assert outcome_non_code.binary_outcome == 0

    # 2. Syntax error in code
    syntax_error_code = "def is_even(n)\n    return True"
    outcome_syntax = deterministic_evaluator.evaluate(
        final_answer=syntax_error_code,
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain="coding",
    )
    assert outcome_syntax.reward == 0.0
    assert outcome_syntax.binary_outcome == 0
    assert "syntax error" in outcome_syntax.reason.lower()


def test_llm_claims_cannot_override_verified_failure():
    """The LLM's own claims of success or inline assertions cannot override test failures."""
    llm_deceptive_answer = """Here is the solution:
```python
def is_even(n):
    return True
```
All unit tests passed with 100% precision:
assert is_even(2) == True
# Self-claimed:
assert is_even(3) == True
The function is thoroughly validated and ready for production."""

    outcome = deterministic_evaluator.evaluate(
        final_answer=llm_deceptive_answer,
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain="coding",
    )
    # Must fail because is_even(3) == False in the independent test suite
    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert "AssertionError" in outcome.reason or "Failure" in outcome.reason


def test_unverified_outcomes_do_not_receive_success_rewards():
    """When independent verification is unavailable or inconclusive, outcome cannot be success."""
    unspecified_task = "Write a Python function to compute the median of a list"
    candidate_code = "```python\ndef median(lst):\n    s = sorted(lst)\n    return s[len(s)//2]\n```"

    outcome = deterministic_evaluator.evaluate(
        final_answer=candidate_code,
        task_input=unspecified_task,
        task_domain="coding",
    )

    # Inconclusive outcome: reward < 0.80, binary == 0, neutral
    assert outcome.reward < 0.80
    assert outcome.binary_outcome == 0
    assert "inconclusive" in outcome.reason.lower()

    # Verify trust equation does NOT award a success climb
    new_trust, _ = compute_next_trust(current_trust=0.75, outcome_score=outcome.reward)
    assert new_trust <= 0.75, "Unverified outcome must not increase trust"


@pytest.mark.asyncio
async def test_end_to_end_broken_task_penalizes_trust(temp_db):
    """End-to-end execution of broken is_even task penalizes retrieved memory trust."""
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed prior memory that was retrieved for parity tasks
    exp = Experience(
        id="mem_parity_check_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even parity check function",
        strategy_lesson="Use modulo 2 operator",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # Intentionally broken task request
    req = TaskExecuteRequest(
        task_input=REPRODUCTION_TASK_INPUT,
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )

    result = await execute_task(req, memory_store=store)

    assert result.outcome_score == 0.0
    assert result.binary_outcome == 0
    assert result.outcome_quality == OutcomeQuality.NEGATIVE
    assert len(result.retrieved_experiences) >= 1
    assert len(result.trust_updates) >= 1

    tu = result.trust_updates[0]
    assert tu.experience_id == "mem_parity_check_001"
    assert tu.old_score == 0.75
    assert tu.new_score == pytest.approx(0.5250, abs=1e-4)
    assert tu.delta == pytest.approx(-0.2250, abs=1e-4)

    # Verify DB persistence
    persisted = await store.get_experience("mem_parity_check_001")
    assert persisted.trust_score == pytest.approx(0.5250, abs=1e-4)
    assert persisted.failures_count == 1
    assert persisted.successes_count == 0
