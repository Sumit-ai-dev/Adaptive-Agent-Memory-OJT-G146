"""
Investigation and Verification Test Suite for AEMA Quarantined-Memory Recovery Policy.

Verifies the 5 core architectural properties of memory recovery:
1. Absence of silent/automatic recovery from task feedback (DEPRECATED is an absorbing state for autonomous feedback).
2. Administrative recovery requirements (status override + trust restoration).
3. Retrieval safety: status override alone cannot bypass theta=0.35 quarantine filter in Adaptive mode.
4. Preservation of historical failure counters and append-only trust_history audit trail.
5. Persistence across database reload and retrievability after valid recovery.
6. Re-quarantine behavior: recovered memories remain subject to Asymmetric EMA decay and Theorem 1 cutoff.
"""

import os
import tempfile
import pytest

from ai_service.config import settings
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import compute_next_trust, update_experience_trust
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="aema_recovery_test_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_no_automatic_recovery_from_autonomous_feedback(temp_db):
    """
    Property 1: Evaluates whether an autonomous task outcome (even R=1.0)
    can silently or automatically un-quarantine a DEPRECATED memory.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed a deprecated memory with 3 prior failures
    quar_exp = Experience(
        id="mem_quar_auto_rec_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Calculate parity using modulo",
        strategy_lesson="Use n % 2 == 0",
        trust_score=0.2573,
        status=ExperienceStatus.DEPRECATED,
        failures_count=3,
        uses_count=3,
        successes_count=0,
    )
    await store.add_experience(quar_exp)

    # 1. Test update_experience_trust model logic
    updated_exp, record, _ = update_experience_trust(
        experience=quar_exp,
        outcome_score=1.0,
        execution_id="task_attempt_auto_recover",
    )
    # Trust may climb under alpha=0.85: 0.85*0.2573 + 0.15*1.0 = 0.3687
    assert updated_exp.trust_score > 0.35
    # BUT status MUST remain DEPRECATED (only CANDIDATE is promoted to ACTIVE)
    assert updated_exp.status == ExperienceStatus.DEPRECATED, (
        "update_experience_trust must NOT promote DEPRECATED memories to ACTIVE"
    )

    # 2. Test SQLite persistence layer logic without explicit status override
    await store.update_trust(
        experience_id="mem_quar_auto_rec_001",
        new_trust=updated_exp.trust_score,
        reason="Autonomous success outcome attempt",
        binary_outcome=1,
    )
    persisted = await store.get_experience("mem_quar_auto_rec_001")
    assert persisted.status == ExperienceStatus.DEPRECATED, (
        "SQLite store must retain DEPRECATED status on standard trust updates"
    )


@pytest.mark.asyncio
async def test_administrative_recovery_requires_trust_and_status(temp_db):
    """
    Properties 2 & 3: Evaluates administrative recovery and whether
    retrieval filters enforce safety if status is overridden without trust.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    quar_exp = Experience(
        id="mem_admin_rec_002",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even function to determine whether an integer is even",
        strategy_lesson="Use n % 2 == 0 directly",
        trust_score=0.2573,
        status=ExperienceStatus.DEPRECATED,
        failures_count=3,
        uses_count=3,
        successes_count=0,
    )
    await store.add_experience(quar_exp)

    retriever = MemoryRetriever(store=store)

    # Attempt Case A: Direct DEPRECATED -> ACTIVE is strictly rejected by state machine
    with pytest.raises(ValueError, match="Invalid state transition: Cannot transition directly"):
        await store.update_trust(
            experience_id="mem_admin_rec_002",
            new_trust=0.2573,
            status=ExperienceStatus.ACTIVE.value,
            reason="Incomplete administrative recovery (status changed, trust low)",
        )

    # Valid administrative recovery transitions to CANDIDATE probation
    recovered_cand = await store.admin_recover_to_probation(
        experience_id="mem_admin_rec_002",
        reason="Administrative audit for probationary validation testing",
    )
    assert recovered_cand.status == ExperienceStatus.CANDIDATE

    # MemoryRetriever must STILL REJECT the memory because status is CANDIDATE (and trust < 0.35)
    matches_a, diag_a = await retriever.retrieve_with_diagnostics(
        query="Implement is_even function to determine whether an integer is even",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )
    assert "mem_admin_rec_002" not in [m.experience.id for m in matches_a], (
        "Memory in candidate probation must not be retrieved in Adaptive mode"
    )
    assert "mem_admin_rec_002" in diag_a.get("gate_reasons", {})

    # Attempt Case B: Promoting CANDIDATE without meeting probation quota fails
    with pytest.raises(ValueError, match="Cannot promote CANDIDATE"):
        await store.update_trust(
            experience_id="mem_admin_rec_002",
            new_trust=0.75,
            status=ExperienceStatus.ACTIVE.value,
            reason="Unverified promotion attempt",
        )


@pytest.mark.asyncio
async def test_recovery_preserves_historical_audit_ledger_and_counters(temp_db):
    """
    Property 4: Confirms that administrative recovery does NOT erase
    historical failure counters or truncate the append-only trust_history audit ledger.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # 1. Seed active memory at 0.75
    exp = Experience(
        id="mem_history_preserved_003",
        task_domain=TaskDomain.CODING,
        trigger_condition="Check even numbers",
        strategy_lesson="Old strategy",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # 2. Apply 3 failure steps into quarantine
    s1, r1 = compute_next_trust(0.75, 0.0)
    await store.update_trust(exp.id, s1, reason=r1, binary_outcome=0)
    s2, r2 = compute_next_trust(s1, 0.0)
    await store.update_trust(exp.id, s2, reason=r2, binary_outcome=0)
    s3, r3 = compute_next_trust(s2, 0.0)
    await store.update_trust(exp.id, s3, reason=r3, binary_outcome=0)

    pre_recovery = await store.get_experience(exp.id)
    assert pre_recovery.status == ExperienceStatus.DEPRECATED
    assert pre_recovery.failures_count == 3
    assert pre_recovery.uses_count == 3
    assert pre_recovery.successes_count == 0

    # 3. Apply administrative recovery to CANDIDATE probation
    recovery_reason = "Manual audit: verified fix for edge case bug; rehabilitated to probation"
    await store.admin_recover_to_probation(
        experience_id=exp.id,
        reason=recovery_reason,
    )

    post_recovery = await store.get_experience(exp.id)
    assert post_recovery.status == ExperienceStatus.CANDIDATE
    assert post_recovery.trust_score == pytest.approx(0.2573, abs=1e-4)

    # Counter preservation: failures are NOT erased
    assert post_recovery.failures_count == 3, "Historical failure count must be preserved across recovery"
    assert post_recovery.uses_count == 3, "Historical uses count must be preserved across recovery"
    assert post_recovery.successes_count == 0

    # Audit ledger preservation: trust_history has 4 sequential records
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT old_trust, new_trust, delta, reason FROM trust_history WHERE experience_id = ? ORDER BY created_at ASC",
            (exp.id,),
        )
        rows = cursor.fetchall()

    assert len(rows) == 4, f"Expected 4 audit history rows (3 failures + 1 recovery), found {len(rows)}"
    # Verify row 4 is the recovery record
    recovery_row = rows[3]
    assert float(recovery_row["old_trust"]) == pytest.approx(0.2573, abs=1e-4)
    assert float(recovery_row["new_trust"]) == pytest.approx(0.2573, abs=1e-4)
    assert recovery_reason in recovery_row["reason"]


@pytest.mark.asyncio
async def test_recovered_memory_persists_across_db_reload_and_requarantines(temp_db):
    """
    Properties 5 & 6: Confirms that recovered status persists across SQLite
    database reload and remains fully subject to Asymmetric EMA decay and re-quarantine.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed an already-promoted recovered memory with 3 prior failures
    exp = Experience(
        id="mem_reload_requar_004",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even function to determine whether an integer is even",
        strategy_lesson="Rehabilitated modulo solution",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
        failures_count=3,
        uses_count=3,
        probation_successes=3,
    )
    await store.add_experience(exp)

    del store  # Close initial connection

    # 1. Re-open database from disk
    reloaded_store = SQLiteMemoryStore(db_path=temp_db)
    reloaded_exp = await reloaded_store.get_experience("mem_reload_requar_004")
    assert reloaded_exp is not None
    assert reloaded_exp.status == ExperienceStatus.ACTIVE
    assert reloaded_exp.trust_score == 0.75
    assert reloaded_exp.failures_count == 3

    # Verify retrievability from reloaded store
    retriever = MemoryRetriever(store=reloaded_store)
    matches, diag = await retriever.retrieve_with_diagnostics(
        query="Implement is_even function to determine whether an integer is even",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )
    assert "mem_reload_requar_004" in [m.experience.id for m in matches]
    assert diag["candidate_count"] >= diag["admissible_count"] >= len(matches)

    # 2. Verify Re-Quarantine: If the recovered memory fails again, it decays and re-quarantines
    # Failure 4 (from 0.75 -> 0.525)
    s4, r4 = compute_next_trust(0.75, 0.0)
    await reloaded_store.update_trust(exp.id, s4, reason=r4, binary_outcome=0)
    e4 = await reloaded_store.get_experience(exp.id)
    assert e4.status == ExperienceStatus.ACTIVE
    assert e4.failures_count == 4

    # Failure 5 (from 0.525 -> 0.3675)
    s5, r5 = compute_next_trust(s4, 0.0)
    await reloaded_store.update_trust(exp.id, s5, reason=r5, binary_outcome=0)
    e5 = await reloaded_store.get_experience(exp.id)
    assert e5.status == ExperienceStatus.ACTIVE
    assert e5.failures_count == 5

    # Failure 6 (from 0.3675 -> 0.2573 < 0.35) -> Re-quarantined!
    s6, r6 = compute_next_trust(s5, 0.0)
    await reloaded_store.update_trust(exp.id, s6, reason=r6, binary_outcome=0)
    e6 = await reloaded_store.get_experience(exp.id)
    assert e6.trust_score == pytest.approx(0.2573, abs=1e-4)
    assert e6.status == ExperienceStatus.DEPRECATED, "Must automatically re-quarantine when S < 0.35"
    assert e6.failures_count == 6
    assert e6.uses_count == 6

    # Verify exclusion after re-quarantine
    re_matches, re_diag = await retriever.retrieve_with_diagnostics(
        query="Implement is_even function to determine whether an integer is even",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )
    assert "mem_reload_requar_004" not in [m.experience.id for m in re_matches]
    assert "mem_reload_requar_004" in re_diag.get("gate_reasons", {})
