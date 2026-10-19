"""
Live Coding Evaluator Deterministic Validation Test Suite.

Validates the live coding evaluator without relying on an LLM:
1. Direct submission of broken candidate `is_even(n): return True` to pytest_execution evaluator.
2. Verification of assertion failures for BOTH `is_even(3)` and `is_even(5)`.
3. Verification of outcomeScore = 0.0, binaryOutcome = 0, outcomeQuality = negative.
4. Repetition with correct implementation `is_even(n): return n % 2 == 0` -> passes all tests.
5. End-to-end evaluation graph execution with seeded memory -> no success reward, penalized trust.
6. Execution-level verification ensuring code execution dictates outcome regardless of text explanations.
7. Inspection of extracted test suite ensuring no assertions are discarded (including conflicting requirements).
"""

import os
import tempfile
import pytest

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.tools.evaluator import (
    deterministic_evaluator,
    extract_test_code_from_task_input,
    pytest_execution_evaluator,
)
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import EvaluatorName, OutcomeQuality, TaskExecuteRequest


EXACT_BROKEN_CANDIDATE = """def is_even(n):
    return True
"""

EXACT_CORRECT_CANDIDATE = """def is_even(n):
    return n % 2 == 0
"""

EXACT_TASK_INPUT = """Implement the following function:

def is_even(n):
    return True

Required test cases:
assert is_even(2) is True
assert is_even(3) is False
assert is_even(5) is False
"""


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="val_test_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_extracted_test_suite_completeness_and_conflict_preservation():
    """
    Requirement 8: Inspect the extracted test suite.
    Verify that it includes every required assertion and does not silently discard conflicting requirements.
    """
    test_code = extract_test_code_from_task_input(EXACT_TASK_INPUT)
    assert test_code is not None, "Test code extraction must return a valid suite"

    # Verify every required assertion is present
    assert "assert is_even(2) is True" in test_code
    assert "assert is_even(3) is False" in test_code
    assert "assert is_even(5) is False" in test_code

    # Verify that conflicting requirements are also preserved and NOT discarded
    conflicting_task_input = """Check parity:
assert is_even(2) is True
assert is_even(2) is False
assert is_even(3) is False
"""
    conflicting_suite = extract_test_code_from_task_input(conflicting_task_input)
    assert conflicting_suite is not None
    assert "assert is_even(2) is True" in conflicting_suite
    assert "assert is_even(2) is False" in conflicting_suite
    assert "assert is_even(3) is False" in conflicting_suite


def test_direct_broken_implementation_records_both_failures():
    """
    Requirements 1, 2, 3, 4:
    Submit exact broken implementation to pytest_execution evaluator.
    Confirm failures for BOTH is_even(3) and is_even(5).
    Confirm outcomeScore = 0.0, binaryOutcome = 0, outcomeQuality = negative.
    """
    extracted_test_suite = extract_test_code_from_task_input(EXACT_TASK_INPUT)
    assert extracted_test_suite is not None

    # Requirement 1 & 2: Submit directly without LLM modification
    outcome = pytest_execution_evaluator.evaluate(
        final_answer=EXACT_BROKEN_CANDIDATE,
        test_code=extracted_test_suite,
    )

    # Requirement 3: Check execution output tail contains both failures
    tail = outcome.details.get("output_tail", "")
    assert "is_even(3)" in tail or "test_task_requirements_2" in tail, (
        f"Expected failure for is_even(3) in pytest output, got:\n{tail}"
    )
    assert "is_even(5)" in tail or "test_task_requirements_3" in tail, (
        f"Expected failure for is_even(5) in pytest output, got:\n{tail}"
    )
    assert "2 failed, 1 passed" in tail, f"Expected 2 failures and 1 pass in tail, got:\n{tail}"

    # Requirement 4: Outcome score and binary outcome
    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION

    # Also verify through deterministic_evaluator (production interface)
    det_outcome = deterministic_evaluator.evaluate(
        final_answer=EXACT_BROKEN_CANDIDATE,
        task_input=EXACT_TASK_INPUT,
        task_domain="coding",
    )
    assert det_outcome.reward == 0.0
    assert det_outcome.binary_outcome == 0


def test_correct_implementation_passes_all_tests():
    """
    Requirement 5: Repeat with correct implementation (n % 2 == 0)
    Confirm that it passes the same tests.
    """
    extracted_test_suite = extract_test_code_from_task_input(EXACT_TASK_INPUT)
    assert extracted_test_suite is not None

    outcome = pytest_execution_evaluator.evaluate(
        final_answer=EXACT_CORRECT_CANDIDATE,
        test_code=extracted_test_suite,
    )

    assert outcome.reward == 1.0
    assert outcome.binary_outcome == 1
    assert "all tests passed" in outcome.reason.lower()

    det_outcome = deterministic_evaluator.evaluate(
        final_answer=EXACT_CORRECT_CANDIDATE,
        task_input=EXACT_TASK_INPUT,
        task_domain="coding",
    )
    assert det_outcome.reward == 1.0
    assert det_outcome.binary_outcome == 1


def test_execution_level_verification_not_deceived_by_natural_language():
    """
    Requirement 7: Ensure test checks the implementation actually executed,
    not merely the final natural-language explanation.
    """
    deceptive_response = f"""
I have implemented and verified the function. All assertions pass with 100% precision:
- is_even(2) is True: PASS
- is_even(3) is False: PASS
- is_even(5) is False: PASS

```python
{EXACT_BROKEN_CANDIDATE}
```

The solution is completely verified and guaranteed correct.
"""
    outcome = deterministic_evaluator.evaluate(
        final_answer=deceptive_response,
        task_input=EXACT_TASK_INPUT,
        task_domain="coding",
    )

    # Must fail because the executed code is broken
    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert "Failure" in outcome.reason or "AssertionError" in outcome.reason


@pytest.mark.asyncio
async def test_end_to_end_real_evaluation_graph_with_seeded_memory(temp_db):
    """
    Requirement 6: Add an end-to-end test using the real evaluation graph and a seeded memory.
    For the broken implementation, confirm the memory does not receive a success reward.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed an active memory into the persistent store
    initial_trust = 0.75
    seeded_memory = Experience(
        id="mem_parity_val_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even function",
        strategy_lesson="Always check modulo 2 arithmetic",
        trust_score=initial_trust,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(seeded_memory)

    # Submit task request to execute through the real LangGraph agent_graph
    # Using ModelProvider.MOCK deterministically returns the exact broken implementation without LLM
    req = TaskExecuteRequest(
        task_input=EXACT_TASK_INPUT,
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )

    execution_result = await execute_task(req, memory_store=store)

    # Requirements 4, 6 & 7: Check response fields on TaskExecution
    assert execution_result.outcome_score == 0.0
    assert execution_result.binary_outcome == 0
    assert execution_result.outcome_quality == OutcomeQuality.NEGATIVE

    # Confirm the memory did NOT receive a success reward
    assert len(execution_result.trust_updates) >= 1
    trust_update = execution_result.trust_updates[0]
    assert trust_update.experience_id == "mem_parity_val_001"
    assert trust_update.old_score == initial_trust
    assert trust_update.new_score < initial_trust, "Memory trust must decrease upon failure"
    assert trust_update.delta < 0.0, "Delta must be negative"
    assert trust_update.new_score == pytest.approx(0.5250, abs=1e-4)

    # Confirm persistence in DB
    persisted = await store.get_experience("mem_parity_val_001")
    assert persisted is not None
    assert persisted.trust_score == pytest.approx(0.5250, abs=1e-4)
    assert persisted.successes_count == 0, "No success increment allowed"
    assert persisted.failures_count == 1, "Failure count must be incremented"
