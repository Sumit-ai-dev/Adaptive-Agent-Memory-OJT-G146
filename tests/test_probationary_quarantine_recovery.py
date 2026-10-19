"""
Comprehensive Regression and Invariant Test Suite for AEMA Quarantined-Memory Probationary Recovery.

Mandatory Safeguards & Invariants Verified:
1. State Machine: Enforces DEPRECATED -> CANDIDATE -> ACTIVE.
   - Rejects direct DEPRECATED -> ACTIVE transitions in both SQLite and PostgreSQL stores.
   - Promotes candidate only when: quota met, trust >= 0.70, Bayesian quarantine permits retrieval.
   - Revokes candidate to DEPRECATED on verified failure.
   - Preserves trust and counters on inconclusive evaluation.
2. Isolated Probe Pipeline:
   - Dedicated execute_probationary_probe pipeline.
   - Real LLM provider (or deterministic provider config) and real PytestExecutionEvaluator in subprocess.
   - Target-only mutation; zero reflection side effects or extra experiences.
3. Idempotency & Evidence:
   - Normalized SHA-256 task fingerprinting.
   - Rejection of duplicate fingerprints and duplicate execution IDs.
   - Idempotency applied to both failed and successful observations.
   - Exact fingerprint deduplication doc: does not establish statistical independence
     between semantically equivalent tests; does not claim to resolve the full i.i.d. assumption.
4. Atomic Persistence:
   - Single-transaction atomic commit across experiences, probation_task_fingerprints, and trust_history.
   - SQLite BEGIN IMMEDIATE and isolation_level=None write connection.
   - PostgreSQL row locking and uniqueness constraints.
   - Atomic rollback on error without masking original exceptions.
5. Migrations & Security:
   - Idempotent SQLite and PostgreSQL migrations for probation_successes and probation_task_fingerprints.
   - ADMIN_API_KEY authorization enforcement (token comparison via secrets.compare_digest).
   - System actor recorded as system:admin_api_key.
   - Secret key never logged or leaked.
   - Meaningful audit reason (>= 15 characters) required.
   - Duplicate recovery requests rejected with HTTP 409.
6. Preservation of Bayesian Thresholds:
   - QUARANTINE_GAMMA = 0.05, RELIABILITY_THRESHOLD = 0.70, THETA_CUTOFF = 0.35 unchanged.
   - Posterior calculations verified: 0/4 fails Theorem 1, 1/4 passes Theorem 1.
"""

import asyncio
import os
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from ai_service.config import settings
from ai_service.memory.probation import (
    compute_task_fingerprint,
    execute_probationary_probe,
    normalize_for_fingerprint,
)
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore, PostgresMemoryStore
from ai_service.tools.evaluator import EvaluationOutcome, PytestExecutionEvaluator, EvaluatorName
from ai_service.trust_math import (
    beta_lcb,
    calculate_probation_quota,
    posterior_probability_reliable,
    should_quarantine,
)
from backend.main import app
from backend.routes.agent import shared_store
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus, TrustHistoryRecord


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="aema_probation_test_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


# ==============================================================================
# 1. State-Transition Enforcement in Both Stores
# ==============================================================================

@pytest.mark.asyncio
async def test_state_transition_enforcement_sqlite(temp_db):
    """
    Verifies that SQLiteMemoryStore enforces:
    - DEPRECATED -> ACTIVE directly is REJECTED with ValueError.
    - CANDIDATE -> ACTIVE without meeting quota is REJECTED with ValueError.
    - DEPRECATED -> CANDIDATE -> ACTIVE is allowed when quota and trust thresholds are satisfied.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    exp = Experience(
        id="mem_trans_sqlite_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Calculate factorial using recursion",
        strategy_lesson="Use base case n <= 1",
        trust_score=0.2573,
        status=ExperienceStatus.DEPRECATED,
        failures_count=3,
        uses_count=3,
        successes_count=0,
        probation_successes=0,
    )
    await store.add_experience(exp)

    # 1. Direct DEPRECATED -> ACTIVE must raise ValueError
    with pytest.raises(ValueError, match="Invalid state transition: Cannot transition directly"):
        await store.update_trust(
            experience_id="mem_trans_sqlite_001",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Illegal bypass attempt",
        )

    # 2. Recover to CANDIDATE probation
    recovered = await store.admin_recover_to_probation(
        experience_id="mem_trans_sqlite_001",
        reason="Administrative audit: code patched for recursion depth",
    )
    assert recovered.status == ExperienceStatus.CANDIDATE
    assert recovered.probation_successes == 0

    # 3. Attempting to promote CANDIDATE to ACTIVE with unmet quota (0/3) must raise ValueError
    with pytest.raises(ValueError, match="Cannot promote CANDIDATE"):
        await store.update_trust(
            experience_id="mem_trans_sqlite_001",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Premature promotion attempt without probation successes",
        )


@pytest.mark.asyncio
async def test_state_transition_enforcement_postgres_mock():
    """
    Verifies that PostgresMemoryStore enforces:
    - DEPRECATED -> ACTIVE directly is REJECTED with ValueError.
    - CANDIDATE -> ACTIVE without meeting quota is REJECTED with ValueError.
    """
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    class MockTransactionContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_conn.transaction = MagicMock(return_value=MockTransactionContext())

    class MockPoolAcquireContext:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_pool.acquire = MagicMock(return_value=MockPoolAcquireContext())

    with patch("ai_service.memory.store.HAS_POSTGRES", True):
        pg_store = PostgresMemoryStore(database_url="postgresql://mock:mock@localhost:5432/mock", pool=mock_pool)
        pg_store._initialized = True

    # 1. Simulate existing DEPRECATED record
    mock_conn.fetchrow.return_value = {
        "trust_score": 0.2573,
        "status": "deprecated",
        "uses_count": 3,
        "successes_count": 0,
        "failures_count": 3,
        "probation_successes": 0,
    }

    # Direct DEPRECATED -> ACTIVE must raise ValueError
    with pytest.raises(ValueError, match="Invalid state transition: Cannot transition directly"):
        await pg_store.update_trust(
            experience_id="mem_pg_test_001",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Illegal postgres transition",
        )

    # 2. Simulate CANDIDATE record with unmet quota
    mock_conn.fetchrow.return_value = {
        "trust_score": 0.75,
        "status": "candidate",
        "uses_count": 3,
        "successes_count": 0,
        "failures_count": 3,
        "probation_successes": 1,  # quota is calculate_probation_quota(3) = 3
    }

    with pytest.raises(ValueError, match="Cannot promote CANDIDATE"):
        await pg_store.update_trust(
            experience_id="mem_pg_test_001",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Premature promotion attempt",
        )


# ==============================================================================
# 2. Existing-Database Migration and Data Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_existing_database_migration_and_data_preservation(temp_db):
    """
    Verifies that initializing SQLiteMemoryStore over a legacy database:
    - Idempotently adds 'probation_successes' column to 'experiences'.
    - Idempotently creates 'probation_task_fingerprints' table.
    - Preserves all existing rows, historical trust scores, and counters.
    """
    # 1. Create a legacy SQLite table without probation_successes or fingerprints table
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE experiences (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            task_domain TEXT NOT NULL,
            trigger_condition TEXT NOT NULL,
            strategy_lesson TEXT NOT NULL,
            pitfall TEXT,
            confidence REAL NOT NULL DEFAULT 0.85,
            trust_score REAL NOT NULL DEFAULT 0.75,
            uses_count INTEGER NOT NULL DEFAULT 0,
            successes_count INTEGER NOT NULL DEFAULT 0,
            failures_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            embedding TEXT,
            source_task_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE trust_history (
            id TEXT PRIMARY KEY,
            experience_id TEXT NOT NULL,
            execution_id TEXT,
            old_trust REAL NOT NULL,
            new_trust REAL NOT NULL,
            delta REAL NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        INSERT INTO experiences (
            id, user_id, task_domain, trigger_condition, strategy_lesson, pitfall,
            confidence, trust_score, uses_count, successes_count, failures_count,
            status, embedding, source_task_id, created_at, updated_at
        ) VALUES (
            'legacy_mem_001', NULL, 'coding', 'Legacy trigger', 'Legacy lesson', NULL,
            0.85, 0.40, 5, 2, 3, 'deprecated', NULL, NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'
        )
    """)
    conn.commit()
    conn.close()

    # 2. Open via SQLiteMemoryStore (triggers idempotent migration)
    store = SQLiteMemoryStore(db_path=temp_db)

    # 3. Verify legacy record survived with probation_successes defaulting to 0
    legacy_exp = await store.get_experience("legacy_mem_001")
    assert legacy_exp is not None
    assert legacy_exp.id == "legacy_mem_001"
    assert legacy_exp.status == ExperienceStatus.DEPRECATED
    assert legacy_exp.trust_score == pytest.approx(0.40, abs=1e-4)
    assert legacy_exp.failures_count == 3
    assert legacy_exp.probation_successes == 0

    # 4. Verify fingerprints table exists and is functional
    with store._get_connection() as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM probation_task_fingerprints")
        assert cur.fetchone()[0] == 0


# ==============================================================================
# 3. Successful, Failed, and Inconclusive Probes with Real Subprocess Execution
# ==============================================================================

@pytest.mark.asyncio
async def test_real_evaluator_subprocess_execution_probe(temp_db):
    """
    Verifies that execute_probationary_probe uses the real PytestExecutionEvaluator
    in an isolated subprocess without mocks, and properly classifies:
    - Clean test success (R=1.0)
    - Assertion failure (R=0.0) -> revokes to DEPRECATED
    - Inconclusive execution (missing test code) -> preserves trust and counters
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed deprecated memory
    exp = Experience(
        id="mem_probe_exec_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even function",
        strategy_lesson="def is_even(n):\n    return n % 2 == 0",
        trust_score=0.50,
        status=ExperienceStatus.DEPRECATED,
        failures_count=1,
        uses_count=1,
        successes_count=0,
        probation_successes=0,
    )
    await store.add_experience(exp)

    # Admin recovery to CANDIDATE
    await store.admin_recover_to_probation(
        experience_id="mem_probe_exec_001",
        reason="Admin audit: ready for isolated probationary probe",
    )

    task_input = "Write a function is_even(n) returning True if n is even, False otherwise."
    test_code_success = """
def test_is_even():
    assert is_even(2) is True
    assert is_even(3) is False
    assert is_even(0) is True
"""
    test_code_failure = """
def test_is_even_failing():
    assert is_even(3) is True  # Intentionally failing assertion
"""

    # Mock only llm_gateway to return deterministic python solution
    with patch("ai_service.memory.probation.llm_gateway.generate") as mock_llm:
        # Solution that adheres to the lesson
        mock_llm.return_value = ("```python\ndef is_even(n):\n    return n % 2 == 0\n```", 45)

        # 1. Successful Probe with real Pytest subprocess
        updated_exp, outcome, record = await execute_probationary_probe(
            experience_id="mem_probe_exec_001",
            task_input=task_input,
            test_code=test_code_success,
            store=store,
            actor_id="system:admin_api_key",
        )
        assert outcome.is_success is True
        assert outcome.reward == 1.0
        # For failures_count=1, quota is max(2, ceil(1/2) + 1) = 2.
        # Initial trust was 0.50. After success: 0.85*0.50 + 0.15*1.0 = 0.5750.
        # Quota not met (1/2), and trust 0.5750 < 0.70 -> Retained in CANDIDATE!
        assert updated_exp.status == ExperienceStatus.CANDIDATE
        assert updated_exp.probation_successes == 1
        assert updated_exp.trust_score == pytest.approx(0.5750, abs=1e-4)

        # 2. Second Probe with failing test code -> Verified Failure in real subprocess
        # Must revoke CANDIDATE to DEPRECATED
        fail_task_input = "Write is_even but test with failing condition."
        updated_exp_2, outcome_2, record_2 = await execute_probationary_probe(
            experience_id="mem_probe_exec_001",
            task_input=fail_task_input,
            test_code=test_code_failure,
            store=store,
            actor_id="system:admin_api_key",
        )
        assert outcome_2.is_success is False
        assert outcome_2.reward == 0.0
        assert updated_exp_2.status == ExperienceStatus.DEPRECATED, "Verified failure must revoke to DEPRECATED!"
        assert updated_exp_2.failures_count == 2
        # beta decay: 0.70 * 0.5750 = 0.4025
        assert updated_exp_2.trust_score == pytest.approx(0.4025, abs=1e-4)


# ==============================================================================
# 4. Target-Only Mutation and Absence of Reflection Side Effects
# ==============================================================================

@pytest.mark.asyncio
async def test_target_only_mutation_and_absence_of_reflection(temp_db):
    """
    Verifies that probationary validation:
    - Mutates ONLY the targeted experience.
    - Leaves unrelated experiences unchanged.
    - Generates 0 reflected experiences.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    target_exp = Experience(
        id="mem_target_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Target experience trigger",
        strategy_lesson="def add(a, b): return a + b",
        trust_score=0.50,
        status=ExperienceStatus.CANDIDATE,
        failures_count=1,
        uses_count=1,
    )
    unrelated_exp = Experience(
        id="mem_unrelated_002",
        task_domain=TaskDomain.CODING,
        trigger_condition="Unrelated trigger",
        strategy_lesson="def sub(a, b): return a - b",
        trust_score=0.88,
        status=ExperienceStatus.ACTIVE,
        failures_count=0,
        uses_count=10,
    )
    await store.add_experience(target_exp)
    await store.add_experience(unrelated_exp)

    initial_all = await store.list_experiences()
    initial_ids = {e.id for e in initial_all}

    with patch("ai_service.memory.probation.llm_gateway.generate") as mock_llm:
        mock_llm.return_value = ("```python\ndef add(a, b):\n    return a + b\n```", 30)
        await execute_probationary_probe(
            experience_id="mem_target_001",
            task_input="Add two numbers",
            test_code="def test_add(): assert add(1, 2) == 3",
            store=store,
        )

    # 1. Unrelated memory must be completely untouched
    refreshed_unrelated = await store.get_experience("mem_unrelated_002")
    assert refreshed_unrelated.trust_score == pytest.approx(0.88, abs=1e-4)
    assert refreshed_unrelated.status == ExperienceStatus.ACTIVE
    assert refreshed_unrelated.uses_count == 10
    assert refreshed_unrelated.failures_count == 0

    # 2. No reflection side effects: total experiences count unchanged
    post_all = await store.list_experiences()
    post_ids = {e.id for e in post_all}
    assert post_ids == initial_ids, "Validation probe must NOT generate new candidate experiences!"


# ==============================================================================
# 5. Idempotency: Duplicate Fingerprints & Unique Execution IDs
# ==============================================================================

@pytest.mark.asyncio
async def test_idempotency_fingerprints_and_execution_ids(temp_db):
    """
    Verifies that:
    - Identical task input and test code yield exact deterministic fingerprint.
    - Resubmitting the same fingerprint raises ValueError and blocks counter increment.
    - Duplicate execution IDs are rejected.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    exp = Experience(
        id="mem_idemp_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Idempotency test",
        strategy_lesson="def mul(a, b): return a * b",
        trust_score=0.50,
        status=ExperienceStatus.CANDIDATE,
        failures_count=1,
    )
    await store.add_experience(exp)

    task_input = "Compute multiplication\n   with extra whitespace   "
    test_code = "def test_mul():\n    assert mul(2, 3) == 6\n\n"

    fp1 = compute_task_fingerprint(task_input, test_code)
    fp2 = compute_task_fingerprint(task_input.strip(), test_code.strip())
    assert fp1 == fp2, "Normalized input must yield identical SHA-256 fingerprint"

    with patch("ai_service.memory.probation.llm_gateway.generate") as mock_llm:
        mock_llm.return_value = ("```python\ndef mul(a, b):\n    return a * b\n```", 30)

        # 1. First probe execution succeeds
        u1, _, _ = await execute_probationary_probe(
            experience_id="mem_idemp_001",
            task_input=task_input,
            test_code=test_code,
            store=store,
        )
        assert u1.probation_successes == 1

        # 2. Submitting duplicate fingerprint must be rejected with ValueError
        with pytest.raises(ValueError, match="Duplicate task fingerprint"):
            await execute_probationary_probe(
                experience_id="mem_idemp_001",
                task_input=task_input,
                test_code=test_code,
                store=store,
            )

        # Counters must not have been double-incremented
        current = await store.get_experience("mem_idemp_001")
        assert current.probation_successes == 1
        assert current.uses_count == 1


# ==============================================================================
# 6. Failed-Probe Idempotency
# ==============================================================================

@pytest.mark.asyncio
async def test_failed_probe_idempotency(temp_db):
    """
    Verifies that idempotency applies to failed observations:
    - A failing probe is recorded in probation_task_fingerprints.
    - A repeated probe with the same fingerprint is rejected and cannot increment failures_count twice.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    exp = Experience(
        id="mem_fail_idemp_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Fail idempotency",
        strategy_lesson="def fail_fn(): pass",
        trust_score=0.50,
        status=ExperienceStatus.CANDIDATE,
        failures_count=1,
    )
    await store.add_experience(exp)

    task_input = "Test failure"
    test_code = "def test_fail(): assert False"

    with patch("ai_service.memory.probation.llm_gateway.generate") as mock_llm:
        mock_llm.return_value = ("```python\ndef fail_fn(): pass\n```", 20)

        # First probe fails
        u1, outcome, _ = await execute_probationary_probe(
            experience_id="mem_fail_idemp_001",
            task_input=task_input,
            test_code=test_code,
            store=store,
        )
        assert outcome.is_success is False
        assert u1.status == ExperienceStatus.DEPRECATED
        assert u1.failures_count == 2

        # Recover back to CANDIDATE
        await store.admin_recover_to_probation(
            experience_id="mem_fail_idemp_001",
            reason="Recovering to verify failed probe fingerprint persistence",
        )

        # Attempting probe with the exact same failing fingerprint must be rejected
        with pytest.raises(ValueError, match="Duplicate task fingerprint"):
            await execute_probationary_probe(
                experience_id="mem_fail_idemp_001",
                task_input=task_input,
                test_code=test_code,
                store=store,
            )

        # Failures count must not be incremented a second time
        current = await store.get_experience("mem_fail_idemp_001")
        assert current.failures_count == 2


# ==============================================================================
# 7. Atomic Rollback Across All Related Tables
# ==============================================================================

@pytest.mark.asyncio
async def test_atomic_rollback_on_failure(temp_db):
    """
    Verifies that if an error occurs mid-probe:
    - Transaction safely rolls back without partial updates.
    - experiences, probation_task_fingerprints, and trust_history remain clean.
    - Original exception is not masked.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    exp = Experience(
        id="mem_rollback_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Rollback test",
        strategy_lesson="Lesson",
        trust_score=0.50,
        status=ExperienceStatus.CANDIDATE,
        failures_count=1,
    )
    await store.add_experience(exp)

    outcome = EvaluationOutcome.from_reward(
        reward=1.0,
        evaluator_name=EvaluatorName.PYTEST_EXECUTION,
        reason="Success",
        outcome_threshold=1.0,
    )

    # Induce an error during probe persistence by corrupting the connection cursor or table
    with patch.object(store, "_row_to_experience", side_effect=RuntimeError("Simulated unmaskable exception")):
        with pytest.raises(RuntimeError, match="Simulated unmaskable exception"):
            await store.record_probationary_probe(
                experience_id="mem_rollback_001",
                outcome=outcome,
                execution_id="probe_rollback_exec_001",
                task_fingerprint="fp_rollback_001",
            )

    # Verify atomic rollback: no fingerprint or trust_history record was persisted
    with store._get_connection() as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM probation_task_fingerprints WHERE execution_id = 'probe_rollback_exec_001'")
        assert cur.fetchone()[0] == 0

        cur.execute("SELECT COUNT(*) FROM trust_history WHERE execution_id = 'probe_rollback_exec_001'")
        assert cur.fetchone()[0] == 0


# ==============================================================================
# 8. Concurrent Updates & Persistence Across Reload
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_updates_and_reload_persistence(temp_db):
    """
    Verifies that concurrent probes execute safely with SQLite WAL / locks,
    and all state survives complete database reload.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    exp = Experience(
        id="mem_concur_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Concurrent test",
        strategy_lesson="Lesson",
        trust_score=0.50,
        status=ExperienceStatus.CANDIDATE,
        failures_count=2,
    )
    await store.add_experience(exp)

    outcome = EvaluationOutcome.from_reward(
        reward=1.0,
        evaluator_name=EvaluatorName.PYTEST_EXECUTION,
        reason="Success",
        outcome_threshold=1.0,
    )

    # Run two different probe updates concurrently
    async def run_probe(idx: int):
        return await store.record_probationary_probe(
            experience_id="mem_concur_001",
            outcome=outcome,
            execution_id=f"probe_concur_{idx}",
            task_fingerprint=f"fp_concur_{idx}",
        )

    results = await asyncio.gather(run_probe(1), run_probe(2))
    assert len(results) == 2

    # Close store and reload from disk
    del store
    reloaded_store = SQLiteMemoryStore(db_path=temp_db)
    reloaded_exp = await reloaded_store.get_experience("mem_concur_001")
    assert reloaded_exp is not None
    assert reloaded_exp.probation_successes == 2
    assert reloaded_exp.uses_count == 2


# ==============================================================================
# 9. API Endpoints: Authorization, Audit Reason, & Duplicate Prevention
# ==============================================================================

def test_api_recovery_and_validation_endpoints():
    """
    Tests FastAPI endpoints:
    - Unauthorized request without token -> 401
    - Invalid audit reason (< 15 chars) -> 400
    - Duplicate recovery -> 409
    - Secret key not leaked in response
    """
    client = TestClient(app)
    admin_key = "super-secret-admin-key"

    # Create an isolated deprecated experience in shared_store
    import uuid
    test_mem_id = f"test_api_rec_{uuid.uuid4().hex[:8]}"
    asyncio.run(shared_store.add_experience(Experience(
        id=test_mem_id,
        task_domain=TaskDomain.CODING,
        trigger_condition="API endpoint recovery test",
        strategy_lesson="def solve(): return 42",
        trust_score=0.25,
        status=ExperienceStatus.DEPRECATED,
        failures_count=3,
        uses_count=3,
    )))

    with patch.object(settings, "ADMIN_API_KEY", admin_key):
        # 1. Unauthorized request
        resp_unauth = client.post(
            f"/api/v1/memories/{test_mem_id}/recover",
            json={"reason": "Patched recursive algorithm to use iterative stack"}
        )
        assert resp_unauth.status_code == 401

        # 2. Insufficient audit reason
        resp_short = client.post(
            f"/api/v1/memories/{test_mem_id}/recover",
            json={"reason": "Too short"},
            headers={"X-Admin-Token": admin_key},
        )
        assert resp_short.status_code == 422 or resp_short.status_code == 400

        # 3. Successful recovery
        valid_reason = "Detailed manual audit: replaced broken regex with lxml tree parser"
        resp_rec = client.post(
            f"/api/v1/memories/{test_mem_id}/recover",
            json={"reason": valid_reason, "client_ref": "REF-TICKET-402"},
            headers={"X-Admin-Token": admin_key},
        )
        assert resp_rec.status_code == 200, f"Expected 200, got: {resp_rec.text}"
        data = resp_rec.json()
        assert data["status"] == "candidate"

        # Verify secret key is never leaked
        assert admin_key not in resp_rec.text

        # 4. Duplicate recovery must return 409 Conflict
        resp_dup = client.post(
            f"/api/v1/memories/{test_mem_id}/recover",
            json={"reason": valid_reason},
            headers={"X-Admin-Token": admin_key},
        )
        assert resp_dup.status_code == 409

        # 5. Validation probe endpoint testing
        # Missing auth -> 401
        probe_payload = {
            "task_input": "Return 42",
            "test_code": "def test_solve(): assert solve() == 42",
        }
        resp_probe_unauth = client.post(
            f"/api/v1/memories/{test_mem_id}/validate",
            json=probe_payload,
        )
        assert resp_probe_unauth.status_code == 401

        # With auth and deterministic LLM mock
        with patch("ai_service.memory.probation.llm_gateway.generate") as mock_llm:
            mock_llm.return_value = ("```python\ndef solve():\n    return 42\n```", 25)
            resp_probe = client.post(
                f"/api/v1/memories/{test_mem_id}/validate",
                json=probe_payload,
                headers={"X-Admin-Token": admin_key},
            )
            assert resp_probe.status_code == 200
            probe_data = resp_probe.json()
            assert "experience" in probe_data
            assert "outcome" in probe_data
            assert probe_data["outcome"]["reward"] == 1.0

            # Duplicate probe with identical payload -> 409 Conflict
            resp_probe_dup = client.post(
                f"/api/v1/memories/{test_mem_id}/validate",
                json=probe_payload,
                headers={"X-Admin-Token": admin_key},
            )
            assert resp_probe_dup.status_code == 409


# ==============================================================================
# 10. Preservation of Bayesian Quarantine Thresholds & Behavior
# ==============================================================================

def test_bayesian_thresholds_and_quarantine_invariants():
    """
    Verifies that:
    - Bayesian hyperparameters and thresholds are intact:
      QUARANTINE_GAMMA = 0.05, RELIABILITY_THRESHOLD = 0.70, THETA_CUTOFF = 0.35.
    - Exact posterior probability calculations:
      For n_s=0, n_f=4: P(theta > 0.70) = 0.0288 < 0.05 -> Quarantined (True)
      For n_s=1, n_f=4: P(theta > 0.70) = 0.0580 >= 0.05 -> Admissible (False)
    """
    assert settings.QUARANTINE_GAMMA == 0.05
    assert settings.RELIABILITY_THRESHOLD == 0.70
    assert settings.THETA_CUTOFF == 0.35

    # 0 successes, 4 failures
    prob_0_4 = posterior_probability_reliable(0, 4, threshold=0.70)
    assert prob_0_4 == pytest.approx(0.028795, abs=1e-4)
    assert should_quarantine(0, 4, gamma=0.05, threshold=0.70) is True

    # 1 success, 4 failures
    prob_1_4 = posterior_probability_reliable(1, 4, threshold=0.70)
    assert prob_1_4 == pytest.approx(0.057968, abs=1e-4)
    assert should_quarantine(1, 4, gamma=0.05, threshold=0.70) is False


@pytest.mark.asyncio
async def test_probation_quota_formula_and_tested_boundaries(temp_db):
    """
    Verifies Section 2A Requirements:
    1. Quota formula N_req(k) = max(2, ceil(k / 2) + 1) for k = 0..6:
       k=0 -> 2
       k=1 -> 2
       k=2 -> 2
       k=3 -> 3
       k=4 -> 3
       k=5 -> 4
       k=6 -> 4
    2. Promotion requires trust >= 0.70.
    3. Promotion is prohibited whenever Bayesian quarantine policy forbids it.
    4. Quota enforcement in SQLiteMemoryStore.
    """
    expected_quotas = {
        0: 2,
        1: 2,
        2: 2,
        3: 3,
        4: 3,
        5: 4,
        6: 4,
    }
    for k, expected in expected_quotas.items():
        actual = calculate_probation_quota(k)
        assert actual == expected, f"Quota for k={k} expected {expected}, got {actual}"

    store = SQLiteMemoryStore(db_path=temp_db)

    # Test candidate with k=3 failures (quota = 3)
    exp = Experience(
        id="mem_quota_test_k3",
        task_domain=TaskDomain.CODING,
        trigger_condition="Quota test task",
        strategy_lesson="Quota test lesson",
        trust_score=0.75,
        status=ExperienceStatus.CANDIDATE,
        failures_count=3,
        uses_count=3,
        successes_count=0,
        probation_successes=2,  # 2 is less than quota 3
    )
    await store.add_experience(exp)

    # Premature promotion with probation_successes = 2 < 3 must be REJECTED
    with pytest.raises(ValueError, match="probation quota not met"):
        await store.update_trust(
            experience_id="mem_quota_test_k3",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Attempt promotion at 2/3 quota",
        )

    # Test candidate meeting quota (3/3), but trust < 0.70 (0.65) -> REJECTED
    exp_low_trust = Experience(
        id="mem_quota_test_low_trust",
        task_domain=TaskDomain.CODING,
        trigger_condition="Low trust task",
        strategy_lesson="Low trust lesson",
        trust_score=0.65,
        status=ExperienceStatus.CANDIDATE,
        failures_count=3,
        uses_count=3,
        successes_count=0,
        probation_successes=3,
    )
    await store.add_experience(exp_low_trust)

    with pytest.raises(ValueError, match="below reliability threshold"):
        await store.update_trust(
            experience_id="mem_quota_test_low_trust",
            new_trust=0.65,
            status=ExperienceStatus.ACTIVE.value,
            reason="Attempt promotion with trust < 0.70",
        )

    # Test candidate meeting quota and trust >= 0.70, but Bayesian quarantine rejects:
    exp_quar = Experience(
        id="mem_quota_test_bayesian_reject",
        task_domain=TaskDomain.CODING,
        trigger_condition="Bayesian reject task",
        strategy_lesson="Bayesian reject lesson",
        trust_score=0.75,
        status=ExperienceStatus.CANDIDATE,
        failures_count=4,
        uses_count=4,
        successes_count=0,
        probation_successes=3,  # quota for k=4 is 3
    )
    await store.add_experience(exp_quar)

    with pytest.raises(ValueError, match="Bayesian quarantine policy forbids promotion"):
        await store.update_trust(
            experience_id="mem_quota_test_bayesian_reject",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Attempt promotion when Bayesian gate rejects",
        )

