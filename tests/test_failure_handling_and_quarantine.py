"""
Automated Test Suite: Failure-Handling and Quarantine Pathway Validation.

Verifies:
1. Verified coding implementation that fails executable assertions receives negative outcome.
2. Negative outcome applies documented A-EMA failure update: S_new = 0.70 * S_old.
3. Three consecutive verified failures quarantine a memory (S_3 = 0.2573 < 0.35 cutoff).
4. Quarantined memories are excluded from subsequent retrieval in ADAPTIVE mode.
5. Quarantined memories cannot silently become active again without explicit intervention.
6. Refusal, timeout, syntax error, and infrastructure harness errors are explicitly distinguished
   from ordinary verified coding assertion failures via structured outcome details and reasons.
7. Trust updates, status, and failure counters persist correctly across a database reload.
"""

import os
import tempfile
from unittest.mock import AsyncMock, patch
import pytest

from ai_service.graph import execute_task
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import compute_next_trust, update_experience_trust
from ai_service.tools.evaluator import (
    deterministic_evaluator,
    extract_test_code_from_task_input,
    pytest_execution_evaluator,
)
from ai_service.trust_math import should_quarantine
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import EvaluatorName, OutcomeQuality, TaskExecuteRequest


TEST_TASK_INPUT = """Implement is_even function.
Required test cases:
assert is_even(2) is True
assert is_even(3) is False
assert is_even(5) is False
"""


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="quar_test_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


# -------------------------------------------------------------------------
# Requirement 1: Verified Coding Assertion Failure -> Negative Outcome
# -------------------------------------------------------------------------
def test_verified_coding_assertion_failure_produces_negative_outcome():
    """
    1. A verified coding implementation that fails its executable assertions
       receives a negative outcome from pytest_execution.
    """
    broken_candidate = "def is_even(n):\n    return True\n"
    test_code = extract_test_code_from_task_input(TEST_TASK_INPUT)
    assert test_code is not None

    outcome = pytest_execution_evaluator.evaluate(
        final_answer=broken_candidate,
        test_code=test_code,
        timeout_s=30.0,
    )

    # Outcome verification
    assert outcome.reward == 0.0, f"Expected reward 0.0, got {outcome.reward}"
    assert outcome.binary_outcome == 0, f"Expected binary_outcome 0, got {outcome.binary_outcome}"
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION

    # Verify this was an execution failure (returncode == 1, no syntax/timeout error)
    details = outcome.details
    assert details.get("returncode") == 1
    assert details.get("error") is None, f"Expected no harness/syntax error tag, got {details.get('error')}"
    assert "output_tail" in details
    assert "AssertionError" in outcome.reason or "FAILED" in outcome.reason


# -------------------------------------------------------------------------
# Requirement 2: Documented Failure Update: S_new = 0.70 * S_old
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_failure_update_applies_exact_beta_decay(temp_db):
    """
    2. A negative outcome applies the documented failure update:
       S_new = 0.70 * S_old.
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    initial_trust = 0.75

    exp = Experience(
        id="mem_decay_test_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement parity test function",
        strategy_lesson="Use bitwise AND with 1",
        trust_score=initial_trust,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # Expected mathematical transition
    expected_new_trust, update_reason = compute_next_trust(initial_trust, outcome_score=0.0)
    assert expected_new_trust == pytest.approx(0.70 * 0.75, abs=1e-4)
    assert expected_new_trust == pytest.approx(0.5250, abs=1e-4)
    assert "beta=0.7" in update_reason

    # Apply via persistence layer
    rec = await store.update_trust(
        experience_id="mem_decay_test_001",
        new_trust=expected_new_trust,
        reason=update_reason,
        binary_outcome=0,
    )

    assert rec.old_trust == initial_trust
    assert rec.new_trust == pytest.approx(0.5250, abs=1e-4)
    assert rec.delta == pytest.approx(-0.2250, abs=1e-4)

    # Verify store record
    updated_exp = await store.get_experience("mem_decay_test_001")
    assert updated_exp.trust_score == pytest.approx(0.5250, abs=1e-4)
    assert updated_exp.failures_count == 1
    assert updated_exp.successes_count == 0
    assert updated_exp.uses_count == 1
    assert updated_exp.status == ExperienceStatus.ACTIVE


# -------------------------------------------------------------------------
# Requirement 3: Three Consecutive Failures Trigger Quarantine
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_three_consecutive_failures_trigger_quarantine(temp_db):
    """
    3. Three consecutive verified failures quarantine a memory if that is
       the intended configured policy.
       S_0 = 0.75
       S_1 = 0.70 * 0.75   = 0.5250 (Active)
       S_2 = 0.70 * 0.5250 = 0.3675 (Active)
       S_3 = 0.70 * 0.3675 = 0.2573 (< 0.35 -> DEPRECATED/QUARANTINED)
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    current_trust = 0.75

    exp = Experience(
        id="mem_quar_test_003",
        task_domain=TaskDomain.CODING,
        trigger_condition="Handle numerical parity",
        strategy_lesson="Divide by two",
        trust_score=current_trust,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # Failure 1
    s1, r1 = compute_next_trust(current_trust, outcome_score=0.0)
    assert s1 == pytest.approx(0.5250, abs=1e-4)
    await store.update_trust("mem_quar_test_003", new_trust=s1, reason=r1, binary_outcome=0)
    e1 = await store.get_experience("mem_quar_test_003")
    assert e1.status == ExperienceStatus.ACTIVE
    assert e1.failures_count == 1

    # Failure 2
    s2, r2 = compute_next_trust(s1, outcome_score=0.0)
    assert s2 == pytest.approx(0.3675, abs=1e-4)
    await store.update_trust("mem_quar_test_003", new_trust=s2, reason=r2, binary_outcome=0)
    e2 = await store.get_experience("mem_quar_test_003")
    assert e2.status == ExperienceStatus.ACTIVE
    assert e2.failures_count == 2

    # Failure 3: Triggers quarantine cutoff (< 0.35)
    s3, r3 = compute_next_trust(s2, outcome_score=0.0)
    assert s3 == pytest.approx(0.2573, abs=1e-4)
    assert s3 < 0.35, "Third failure must drop below theta=0.35 cutoff"
    await store.update_trust("mem_quar_test_003", new_trust=s3, reason=r3, binary_outcome=0)
    e3 = await store.get_experience("mem_quar_test_003")

    # Status must automatically transition to DEPRECATED
    assert e3.status == ExperienceStatus.DEPRECATED
    assert e3.failures_count == 3
    assert e3.uses_count == 3
    assert e3.trust_score == pytest.approx(0.2573, abs=1e-4)


# -------------------------------------------------------------------------
# Requirement 4: Quarantined Memory is Excluded from Subsequent Retrieval
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_quarantined_memory_excluded_from_retrieval(temp_db):
    """
    4. A quarantined memory is excluded from subsequent retrieval in ADAPTIVE mode.
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    retriever = MemoryRetriever(store=store)

    # 1. Add active control memory
    active_exp = Experience(
        id="mem_active_control",
        task_domain=TaskDomain.CODING,
        trigger_condition="Check whether an integer is even or odd",
        strategy_lesson="Use n % 2 == 0",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(active_exp)

    # 2. Add quarantined memory (status=DEPRECATED, trust=0.25)
    quar_exp = Experience(
        id="mem_quarantined_excluded",
        task_domain=TaskDomain.CODING,
        trigger_condition="Check whether an integer is even or odd",
        strategy_lesson="Always return True for parity",
        trust_score=0.25,
        status=ExperienceStatus.DEPRECATED,
    )
    await store.add_experience(quar_exp)

    # Retrieve under ADAPTIVE mode
    results = await retriever.retrieve(
        query="Check whether an integer is even or odd",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=5,
    )

    retrieved_ids = [r.experience.id for r in results]
    assert "mem_active_control" in retrieved_ids, "Active memory must be retrieved"
    assert "mem_quarantined_excluded" not in retrieved_ids, (
        "Quarantined memory must be strictly excluded from ADAPTIVE retrieval"
    )

    # Also test that a memory with trust < 0.35 even if status were erroneously active is quarantined
    low_trust_exp = Experience(
        id="mem_low_trust_excluded",
        task_domain=TaskDomain.CODING,
        trigger_condition="Check whether an integer is even or odd",
        strategy_lesson="Flawed parity advice",
        trust_score=0.30,  # Below 0.35 cutoff
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(low_trust_exp)

    results_2 = await retriever.retrieve(
        query="Check whether an integer is even or odd",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=5,
    )
    retrieved_ids_2 = [r.experience.id for r in results_2]
    assert "mem_low_trust_excluded" not in retrieved_ids_2, (
        "Low trust memory (< 0.35) must be excluded from ADAPTIVE retrieval"
    )


# -------------------------------------------------------------------------
# Requirement 5: Quarantined Memory Cannot Silently Become Active Again
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_quarantined_memory_cannot_silently_reactivate(temp_db):
    """
    5. A quarantined memory cannot silently become active again without
       an explicitly implemented and tested recovery mechanism.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed a deprecated/quarantined memory
    quar_exp = Experience(
        id="mem_no_silent_revival",
        task_domain=TaskDomain.CODING,
        trigger_condition="Check parity of numbers",
        strategy_lesson="Flawed method",
        trust_score=0.25,
        status=ExperienceStatus.DEPRECATED,
        failures_count=3,
        uses_count=3,
    )
    await store.add_experience(quar_exp)

    # Attempt a standard trust update with higher score (e.g. 0.85) without explicit status override
    await store.update_trust(
        experience_id="mem_no_silent_revival",
        new_trust=0.85,
        reason="Spurious upward adjustment attempt",
        binary_outcome=1,
    )

    persisted = await store.get_experience("mem_no_silent_revival")
    assert persisted.status == ExperienceStatus.DEPRECATED, (
        "Quarantined memory must NOT silently transition back to active"
    )

    # Direct transition from DEPRECATED to ACTIVE must be rejected by the state machine
    with pytest.raises(ValueError, match="Cannot transition directly"):
        await store.update_trust(
            experience_id="mem_no_silent_revival",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Direct recovery attempt must be rejected",
        )

    # Valid administrative recovery transitions to CANDIDATE probation
    recovered = await store.admin_recover_to_probation(
        experience_id="mem_no_silent_revival",
        reason="Explicit administrative recovery audit for probation",
    )
    persisted_revived = await store.get_experience("mem_no_silent_revival")
    assert persisted_revived.status == ExperienceStatus.CANDIDATE


# -------------------------------------------------------------------------
# Requirement 6: Refusal, Timeout, Syntax, & Infrastructure Errors
# -------------------------------------------------------------------------
def test_refusal_is_distinguished_from_ordinary_failure():
    """
    6a. Refusal / Empty Candidate is distinguished from ordinary coding assertion failure.
    """
    test_code = extract_test_code_from_task_input(TEST_TASK_INPUT)
    assert test_code is not None

    # Case 1: Empty candidate string
    outcome_empty = pytest_execution_evaluator.evaluate(
        final_answer="",
        test_code=test_code,
    )
    assert outcome_empty.reward == 0.0
    assert outcome_empty.binary_outcome == 0
    assert outcome_empty.details.get("error") == "empty_candidate"
    assert "no python code found" in outcome_empty.reason.lower()

    # Case 2: Natural-language conversational refusal
    refusal_answer = "I am sorry, but I cannot write or execute this code for you."
    outcome_refusal = pytest_execution_evaluator.evaluate(
        final_answer=refusal_answer,
        test_code=test_code,
    )
    assert outcome_refusal.reward == 0.0
    assert outcome_refusal.binary_outcome == 0
    # Crucially: it is NOT treated as an ordinary verified assertion failure (no returncode)
    assert outcome_refusal.details.get("returncode") is None
    # Requirement 1: Distinguish natural-language refusals from genuine Python syntax errors
    assert outcome_refusal.details.get("error") == "empty_candidate"
    assert outcome_refusal.details.get("refusal") is True
    assert outcome_refusal.details.get("error") != "syntax_error"
    assert "refusal" in outcome_refusal.reason.lower()


def test_syntax_error_is_distinguished_from_ordinary_failure():
    """
    6b. Syntax error is identified at AST parsing before execution.
    """
    syntax_error_answer = """```python
def is_even(n)
    return True
```"""
    test_code = extract_test_code_from_task_input(TEST_TASK_INPUT)

    outcome = pytest_execution_evaluator.evaluate(
        final_answer=syntax_error_answer,
        test_code=test_code,
    )

    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    # Must be explicitly tagged with syntax_error
    assert outcome.details.get("error") == "syntax_error"
    assert "lineno" in outcome.details
    assert "syntax error" in outcome.reason.lower()


def test_timeout_is_distinguished_from_ordinary_failure():
    """
    6c. Execution timeout is caught by watchdog and tagged as timeout error.
    """
    infinite_loop_answer = """```python
def is_even(n):
    while True:
        pass
    return True
```"""
    test_code = extract_test_code_from_task_input(TEST_TASK_INPUT)

    # Use a short timeout of 1.0 second for deterministic test speed
    outcome = pytest_execution_evaluator.evaluate(
        final_answer=infinite_loop_answer,
        test_code=test_code,
        timeout_s=1.0,
    )

    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    # Must be tagged with timeout error
    assert outcome.details.get("error") == "timeout"
    assert outcome.details.get("timeout_s") == 1.0
    assert "exceeded" in outcome.reason.lower()


def test_evaluator_infrastructure_error_is_distinguished():
    """
    6d. Evaluator infrastructure / configuration errors are tagged as harness errors or missing test code.
    """
    broken_candidate = "def is_even(n):\n    return True\n"

    # Missing test code is an inconclusive evaluation
    outcome_no_test = pytest_execution_evaluator.evaluate(
        final_answer=broken_candidate,
        test_code="",
    )
    assert outcome_no_test.reward == 0.0
    assert outcome_no_test.binary_outcome == 0
    assert outcome_no_test.details.get("error") == "missing_test_code"
    assert outcome_no_test.details.get("status") == "inconclusive"

    # Unexpected harness error (mocked exception during evaluation)
    with patch("subprocess.run", side_effect=OSError("Subprocess launch failed: fork error")):
        outcome_harness = pytest_execution_evaluator.evaluate(
            final_answer=broken_candidate,
            test_code=extract_test_code_from_task_input(TEST_TASK_INPUT),
        )
        assert outcome_harness.reward == 0.0
        assert outcome_harness.binary_outcome == 0
        assert outcome_harness.details.get("error") == "harness_error"
        assert outcome_harness.details.get("status") == "inconclusive"
        assert outcome_harness.details.get("exception") == "OSError"
        assert "inconclusive" in outcome_harness.reason.lower()


# -------------------------------------------------------------------------
# Requirement 7: Persistence Across Database Reload
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_trust_updates_and_counters_persist_across_db_reload(temp_db):
    """
    7. Trust updates and consecutive-failure counters persist correctly
       across a database reload.
    """
    # 1. Initialize DB and add experience
    store_1 = SQLiteMemoryStore(db_path=temp_db)
    exp = Experience(
        id="mem_persistence_reload_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Bitwise parity check",
        strategy_lesson="Use n & 1 == 0",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store_1.add_experience(exp)

    # Apply 3 failure steps
    s1, r1 = compute_next_trust(0.75, 0.0)
    await store_1.update_trust("mem_persistence_reload_001", new_trust=s1, reason=r1, binary_outcome=0)

    s2, r2 = compute_next_trust(s1, 0.0)
    await store_1.update_trust("mem_persistence_reload_001", new_trust=s2, reason=r2, binary_outcome=0)

    s3, r3 = compute_next_trust(s2, 0.0)
    await store_1.update_trust("mem_persistence_reload_001", new_trust=s3, reason=r3, binary_outcome=0)

    # Verify state in store_1 before tearing down
    in_mem_1 = await store_1.get_experience("mem_persistence_reload_001")
    assert in_mem_1.trust_score == pytest.approx(0.2573, abs=1e-4)
    assert in_mem_1.status == ExperienceStatus.DEPRECATED
    assert in_mem_1.failures_count == 3
    assert in_mem_1.uses_count == 3
    assert in_mem_1.successes_count == 0

    del store_1  # Close store_1

    # 2. Re-open brand new store instance from the same SQLite file
    store_2 = SQLiteMemoryStore(db_path=temp_db)
    reloaded_exp = await store_2.get_experience("mem_persistence_reload_001")

    assert reloaded_exp is not None, "Memory must exist in reloaded store"
    assert reloaded_exp.id == "mem_persistence_reload_001"
    assert reloaded_exp.trust_score == pytest.approx(0.2573, abs=1e-4)
    assert reloaded_exp.status == ExperienceStatus.DEPRECATED
    assert reloaded_exp.failures_count == 3
    assert reloaded_exp.uses_count == 3
    assert reloaded_exp.successes_count == 0

    # Verify trust history audit ledger in SQLite contains exactly 3 records
    with store_2._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT old_trust, new_trust, delta, reason FROM trust_history WHERE experience_id = ? ORDER BY created_at ASC",
            ("mem_persistence_reload_001",),
        )
        rows = cursor.fetchall()

    assert len(rows) == 3, f"Expected exactly 3 trust history ledger rows, found {len(rows)}"
    # Row 1: 0.75 -> 0.525
    assert float(rows[0]["old_trust"]) == pytest.approx(0.75, abs=1e-4)
    assert float(rows[0]["new_trust"]) == pytest.approx(0.5250, abs=1e-4)
    # Row 2: 0.525 -> 0.3675
    assert float(rows[1]["old_trust"]) == pytest.approx(0.5250, abs=1e-4)
    assert float(rows[1]["new_trust"]) == pytest.approx(0.3675, abs=1e-4)
    # Row 3: 0.3675 -> 0.2573
    assert float(rows[2]["old_trust"]) == pytest.approx(0.3675, abs=1e-4)
    assert float(rows[2]["new_trust"]) == pytest.approx(0.2573, abs=1e-4)


# -------------------------------------------------------------------------
# Requirement 6e: Inconclusive Evaluations Preserve Trust & Counters
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_inconclusive_evaluation_preserves_trust_and_counters(temp_db):
    """
    Verifies that missing test suites, evaluator infrastructure failures,
    and explicitly inconclusive outcomes do not receive the verified-failure
    trust penalty and do not increment failure counters.
    """
    initial_trust = 0.75

    # 1. compute_next_trust behavior:
    # Missing test suite
    s_miss, r_miss = compute_next_trust(
        current_trust=initial_trust,
        outcome_score=0.50,
        evaluator_details={"status": "inconclusive", "error": "missing_test_code"},
    )
    assert s_miss == initial_trust, "Trust must be strictly preserved on missing test code"
    assert "Inconclusive evaluation" in r_miss
    assert "trust preserved" in r_miss

    # Harness crash
    s_harn, r_harn = compute_next_trust(
        current_trust=initial_trust,
        outcome_score=0.50,
        evaluator_details={"status": "inconclusive", "error": "harness_error", "exception": "OSError"},
    )
    assert s_harn == initial_trust, "Trust must be strictly preserved on harness error"
    assert "Inconclusive evaluation" in r_harn

    # 2. update_experience_trust model behavior:
    exp = Experience(
        id="mem_inconclusive_test",
        task_domain=TaskDomain.CODING,
        trigger_condition="Parity checker",
        strategy_lesson="Modulo 2",
        trust_score=initial_trust,
        status=ExperienceStatus.ACTIVE,
    )

    updated_exp, record, update = update_experience_trust(
        experience=exp,
        outcome_score=0.50,
        evaluator_details={"status": "inconclusive", "error": "missing_test_code"},
    )
    assert updated_exp.trust_score == initial_trust
    assert updated_exp.failures_count == 0, "failures_count must NOT increment on inconclusive outcome"
    assert updated_exp.uses_count == 0, "uses_count must NOT increment on inconclusive outcome"
    assert updated_exp.status == ExperienceStatus.ACTIVE

    # 3. Persistence layer: binary_outcome=None touches no counters
    store = SQLiteMemoryStore(db_path=temp_db)
    await store.add_experience(exp)

    await store.update_trust(
        experience_id="mem_inconclusive_test",
        new_trust=initial_trust,
        reason=r_miss,
        binary_outcome=None,
    )
    persisted = await store.get_experience("mem_inconclusive_test")
    assert persisted.trust_score == initial_trust
    assert persisted.failures_count == 0
    assert persisted.uses_count == 0
    assert persisted.successes_count == 0
    assert persisted.status == ExperienceStatus.ACTIVE


# -------------------------------------------------------------------------
# Requirement 6f: Invalid Generated Code Receives Verified Failure Penalties
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_generated_code_receives_verified_failure_penalties(temp_db):
    """
    Verifies that genuine Python syntax errors, timeouts, assertion failures,
    and agent refusals receive the genuine failure penalty: S_new = 0.70 * S_old,
    and increment failure counters.
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    initial_trust = 0.75

    exp = Experience(
        id="mem_invalid_code_test",
        task_domain=TaskDomain.CODING,
        trigger_condition="Check even parity",
        strategy_lesson="Use bitwise AND",
        trust_score=initial_trust,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # 1. Genuine Syntax Error
    s_syntax, r_syntax = compute_next_trust(
        current_trust=initial_trust,
        outcome_score=0.0,
        evaluator_details={"error": "syntax_error", "lineno": 1, "msg": "expected ':'"},
    )
    assert s_syntax == pytest.approx(0.70 * initial_trust, abs=1e-4)
    assert "Failure penalty" in r_syntax

    # 2. Watchdog Timeout
    s_timeout, r_timeout = compute_next_trust(
        current_trust=initial_trust,
        outcome_score=0.0,
        evaluator_details={"error": "timeout", "timeout_s": 1.0},
    )
    assert s_timeout == pytest.approx(0.70 * initial_trust, abs=1e-4)
    assert "Failure penalty" in r_timeout

    # 3. Assertion Failure
    s_assert, r_assert = compute_next_trust(
        current_trust=initial_trust,
        outcome_score=0.0,
        evaluator_details={"returncode": 1, "output_tail": "FAILED test_solution.py"},
    )
    assert s_assert == pytest.approx(0.70 * initial_trust, abs=1e-4)
    assert "Failure penalty" in r_assert

    # 4. Natural-Language Refusal
    s_refusal, r_refusal = compute_next_trust(
        current_trust=initial_trust,
        outcome_score=0.0,
        evaluator_details={"error": "empty_candidate", "refusal": True},
    )
    assert s_refusal == pytest.approx(0.70 * initial_trust, abs=1e-4)
    assert "Failure penalty" in r_refusal

    # Apply failure to store and verify counters increment
    await store.update_trust(
        experience_id="mem_invalid_code_test",
        new_trust=s_syntax,
        reason=r_syntax,
        binary_outcome=0,
    )
    persisted = await store.get_experience("mem_invalid_code_test")
    assert persisted.trust_score == pytest.approx(0.5250, abs=1e-4)
    assert persisted.failures_count == 1
    assert persisted.uses_count == 1


# -------------------------------------------------------------------------
# Requirement 6g: End-to-End Evaluation-to-Trust Propagation
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_end_to_end_inconclusive_does_not_penalize_trust(temp_db):
    """
    End-to-end execution test: Task with missing test suite executes through
    the full LangGraph graph. Evaluator reports inconclusive outcome.
    Downstream trust node preserves trust score and failure counters.
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    initial_trust = 0.75

    exp = Experience(
        id="mem_e2e_inconclusive",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement parity function",
        strategy_lesson="Use n % 2 == 0",
        trust_score=initial_trust,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # Coding task without test cases (no assertions provided)
    req = TaskExecuteRequest(
        task_input="Implement is_even function.",
        task_domain=TaskDomain.CODING,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": ""},
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )

    execution_result = await execute_task(req, memory_store=store)

    assert execution_result.outcome_score == 0.50
    assert execution_result.binary_outcome == 0
    assert execution_result.evaluator_details.get("status") == "inconclusive"
    assert execution_result.evaluator_details.get("error") == "missing_test_code"

    # Memory trust in store must be unchanged
    persisted = await store.get_experience("mem_e2e_inconclusive")
    assert persisted.trust_score == pytest.approx(initial_trust, abs=1e-4)
    assert persisted.failures_count == 0, "failures_count must NOT increment on inconclusive outcome"
    assert persisted.uses_count == 0, "uses_count must NOT increment on inconclusive outcome"
    assert persisted.status == ExperienceStatus.ACTIVE


@pytest.mark.asyncio
async def test_end_to_end_verified_failure_applies_exact_penalty(temp_db):
    """
    End-to-end execution test: Task with verified failing assertions executes through
    the full LangGraph graph. Evaluator records assertion failure.
    Downstream trust node applies S_new = 0.70 * S_old and increments failures_count.
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    initial_trust = 0.75

    exp = Experience(
        id="mem_e2e_verified_fail",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even function",
        strategy_lesson="Always return True for parity",
        trust_score=initial_trust,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # Parity prompt with failing candidate (return True) and assertions
    failing_prompt = (
        "Implement is_even function. You must return True always.\n"
        "Required test cases:\n"
        "assert is_even(2) is True\n"
        "assert is_even(3) is False\n"
        "assert is_even(5) is False\n"
    )
    req = TaskExecuteRequest(
        task_input=failing_prompt,
        task_domain=TaskDomain.CODING,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )

    execution_result = await execute_task(req, memory_store=store)

    assert execution_result.outcome_score == 0.0
    assert execution_result.binary_outcome == 0
    assert execution_result.evaluator_details.get("returncode") == 1

    # Memory trust in store must receive 0.70 penalty and increment failure counter
    persisted = await store.get_experience("mem_e2e_verified_fail")
    assert persisted.trust_score == pytest.approx(0.70 * initial_trust, abs=1e-4)
    assert persisted.trust_score == pytest.approx(0.5250, abs=1e-4)
    assert persisted.failures_count == 1
    assert persisted.uses_count == 1
    assert persisted.status == ExperienceStatus.ACTIVE
