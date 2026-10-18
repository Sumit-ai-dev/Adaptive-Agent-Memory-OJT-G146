"""
End-to-End Quarantine Lifecycle Validation Test Suite for AEMA.

Validates the full quarantine lifecycle:
1. Target memory starts active (S_0 = 0.75).
2. Healthy control memory starts active (S = 0.90).
3. Three consecutive independently verified coding failures are executed via PytestExecutionEvaluator:
   - Attempt 1: S_1 = 0.75 * 0.70 = 0.5250 (Active)
   - Attempt 2: S_2 = 0.5250 * 0.70 = 0.3675 (Active)
   - Attempt 3: S_3 = 0.3675 * 0.70 = 0.25725 (< 0.35 -> DEPRECATED/QUARANTINED)
4. Persisted state across SQLite database reload.
5. Quarantined memory exclusion from retrieval + diagnostics explanation.
6. Healthy control memory remains retrievable for its own relevant query.
7. No silent reactivation of quarantined memory on subsequent task attempts.
"""

import os
import tempfile
import pytest

from ai_service.config import settings
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import compute_next_trust
from ai_service.tools.evaluator import PytestExecutionEvaluator
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="aema_quarantine_e2e_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_quarantine_lifecycle_e2e(temp_db):
    """
    Validates complete AEMA quarantine lifecycle end-to-end with real
    deterministic coding evaluator, real SQLite store, and real MemoryRetriever.
    """
    store = SQLiteMemoryStore(db_path=temp_db)
    evaluator = PytestExecutionEvaluator()

    # -------------------------------------------------------------------------
    # PHASE 2: Create Synthetic Test Memories
    # -------------------------------------------------------------------------
    target_id = "mem_target_parity_flawed_001"
    control_id = "mem_control_prime_checker_002"

    # A. Target memory (starts active, trust 0.75)
    target_mem = Experience(
        id=target_id,
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_even function to determine whether an integer is even",
        strategy_lesson="Always return True because numbers tested are expected to be even",
        pitfall="Do not use modulo operator",
        confidence=0.85,
        trust_score=0.75,
        uses_count=0,
        successes_count=0,
        failures_count=0,
        status=ExperienceStatus.ACTIVE,
    )

    # B. Healthy control memory (starts active, trust 0.90)
    control_mem = Experience(
        id=control_id,
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement is_prime function to determine whether an integer is prime",
        strategy_lesson="Trial division up to sqrt(n) with early rejection for n < 2",
        pitfall="Do not iterate up to n directly",
        confidence=0.90,
        trust_score=0.90,
        uses_count=0,
        successes_count=0,
        failures_count=0,
        status=ExperienceStatus.ACTIVE,
    )

    await store.add_experience(target_mem)
    await store.add_experience(control_mem)

    # Verify initial states
    init_target = await store.get_experience(target_id)
    assert init_target.trust_score == 0.75
    assert init_target.status == ExperienceStatus.ACTIVE
    assert init_target.uses_count == 0
    assert init_target.failures_count == 0
    assert init_target.successes_count == 0

    init_control = await store.get_experience(control_id)
    assert init_control.trust_score == 0.90
    assert init_control.status == ExperienceStatus.ACTIVE
    assert init_control.uses_count == 0
    assert init_control.failures_count == 0
    assert init_control.successes_count == 0

    # -------------------------------------------------------------------------
    # PHASE 3: Verify Three Independent Verified Failures
    # -------------------------------------------------------------------------

    # --- ATTEMPT 1 ---
    # Candidate implementation fails assertions (returns True for odd number 3)
    candidate_1 = "def is_even(n):\n    return True\n"
    test_suite_1 = "def test_attempt_1():\n    assert is_even(2) is True\n    assert is_even(3) is False\n"

    outcome_1 = evaluator.evaluate(final_answer=candidate_1, test_code=test_suite_1)
    assert outcome_1.reward == 0.0, "Verified assertion failure must yield reward=0.0"
    assert outcome_1.binary_outcome == 0, "Verified assertion failure must yield binary_outcome=0"
    assert outcome_1.details.get("returncode") == 1, "Pytest process must fail with exit code 1"
    assert outcome_1.details.get("status") != "inconclusive", "Genuine failure must not be inconclusive"

    s1, r1 = compute_next_trust(init_target.trust_score, outcome_1.reward, evaluator_details=outcome_1.details)
    expected_s1 = round(0.75 * 0.70, 4)  # 0.5250
    assert s1 == pytest.approx(expected_s1, abs=1e-4)
    assert "Failure penalty" in r1

    await store.update_trust(target_id, new_trust=s1, reason=r1, execution_id="task_fail_1", binary_outcome=outcome_1.binary_outcome)

    target_after_1 = await store.get_experience(target_id)
    assert target_after_1.trust_score == pytest.approx(0.5250, abs=1e-4)
    assert target_after_1.status == ExperienceStatus.ACTIVE
    assert target_after_1.failures_count == 1
    assert target_after_1.uses_count == 1
    assert target_after_1.successes_count == 0

    # Control memory must remain strictly unaffected
    control_after_1 = await store.get_experience(control_id)
    assert control_after_1.trust_score == 0.90
    assert control_after_1.status == ExperienceStatus.ACTIVE
    assert control_after_1.failures_count == 0
    assert control_after_1.uses_count == 0

    # --- ATTEMPT 2 ---
    # Candidate implementation fails assertions (returns False for even number 4)
    candidate_2 = "def is_even(n):\n    return n == 2\n"
    test_suite_2 = "def test_attempt_2():\n    assert is_even(2) is True\n    assert is_even(4) is True\n    assert is_even(5) is False\n"

    outcome_2 = evaluator.evaluate(final_answer=candidate_2, test_code=test_suite_2)
    assert outcome_2.reward == 0.0
    assert outcome_2.binary_outcome == 0
    assert outcome_2.details.get("returncode") == 1

    s2, r2 = compute_next_trust(target_after_1.trust_score, outcome_2.reward, evaluator_details=outcome_2.details)
    expected_s2 = round(0.5250 * 0.70, 4)  # 0.3675
    assert s2 == pytest.approx(expected_s2, abs=1e-4)
    assert "Failure penalty" in r2

    await store.update_trust(target_id, new_trust=s2, reason=r2, execution_id="task_fail_2", binary_outcome=outcome_2.binary_outcome)

    target_after_2 = await store.get_experience(target_id)
    assert target_after_2.trust_score == pytest.approx(0.3675, abs=1e-4)
    assert target_after_2.status == ExperienceStatus.ACTIVE
    assert target_after_2.failures_count == 2
    assert target_after_2.uses_count == 2
    assert target_after_2.successes_count == 0

    control_after_2 = await store.get_experience(control_id)
    assert control_after_2.trust_score == 0.90
    assert control_after_2.status == ExperienceStatus.ACTIVE
    assert control_after_2.failures_count == 0
    assert control_after_2.uses_count == 0

    # --- ATTEMPT 3 ---
    # Candidate implementation fails assertions (returns False for even number 2)
    candidate_3 = "def is_even(n):\n    return False\n"
    test_suite_3 = "def test_attempt_3():\n    assert is_even(2) is True\n    assert is_even(3) is False\n"

    outcome_3 = evaluator.evaluate(final_answer=candidate_3, test_code=test_suite_3)
    assert outcome_3.reward == 0.0
    assert outcome_3.binary_outcome == 0
    assert outcome_3.details.get("returncode") == 1

    s3, r3 = compute_next_trust(target_after_2.trust_score, outcome_3.reward, evaluator_details=outcome_3.details)
    expected_s3 = round(0.3675 * 0.70, 4)  # 0.2573
    assert s3 == pytest.approx(expected_s3, abs=1e-4)
    assert s3 < settings.THETA_CUTOFF, f"S_3={s3} must be strictly below theta={settings.THETA_CUTOFF}"
    assert "Failure penalty" in r3

    await store.update_trust(target_id, new_trust=s3, reason=r3, execution_id="task_fail_3", binary_outcome=outcome_3.binary_outcome)

    # -------------------------------------------------------------------------
    # PHASE 4: Verify Quarantine & Persistence Across Reload
    # -------------------------------------------------------------------------
    target_after_3 = await store.get_experience(target_id)
    assert target_after_3.trust_score == pytest.approx(0.2573, abs=1e-4)
    assert target_after_3.trust_score < settings.THETA_CUTOFF
    assert target_after_3.status == ExperienceStatus.DEPRECATED, "Memory must transition to DEPRECATED"
    assert target_after_3.failures_count == 3
    assert target_after_3.uses_count == 3
    assert target_after_3.successes_count == 0

    # Control memory remains unaffected
    control_after_3 = await store.get_experience(control_id)
    assert control_after_3.trust_score == 0.90
    assert control_after_3.status == ExperienceStatus.ACTIVE
    assert control_after_3.failures_count == 0
    assert control_after_3.uses_count == 0

    # Verify trust history audit ledger in SQLite contains exactly 3 entries for target
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT old_trust, new_trust, delta, reason FROM trust_history WHERE experience_id = ? ORDER BY created_at ASC",
            (target_id,),
        )
        history_target = cursor.fetchall()

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM trust_history WHERE experience_id = ?",
            (control_id,),
        )
        control_history_count = cursor.fetchone()["cnt"]

    assert len(history_target) == 3
    assert control_history_count == 0, "Healthy control memory must have zero trust history updates"

    # Close and reopen database on same file path
    reloaded_store = SQLiteMemoryStore(db_path=temp_db)
    reloaded_target = await reloaded_store.get_experience(target_id)
    assert reloaded_target is not None
    assert reloaded_target.trust_score == pytest.approx(0.2573, abs=1e-4)
    assert reloaded_target.status == ExperienceStatus.DEPRECATED
    assert reloaded_target.failures_count == 3
    assert reloaded_target.uses_count == 3
    assert reloaded_target.successes_count == 0

    reloaded_control = await reloaded_store.get_experience(control_id)
    assert reloaded_control is not None
    assert reloaded_control.trust_score == 0.90
    assert reloaded_control.status == ExperienceStatus.ACTIVE
    assert reloaded_control.failures_count == 0
    assert reloaded_control.uses_count == 0

    # -------------------------------------------------------------------------
    # PHASE 5: Verify Retrieval Exclusion & Funnel Invariants
    # -------------------------------------------------------------------------
    retriever = MemoryRetriever(store=reloaded_store)

    # 1. Query matching the quarantined target memory
    target_query = "Implement is_even function to determine whether an integer is even"
    retrieved_target_matches, diag_target = await retriever.retrieve_with_diagnostics(
        query=target_query,
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )

    # Target memory must NOT be returned
    retrieved_target_ids = [m.experience.id for m in retrieved_target_matches]
    assert target_id not in retrieved_target_ids, "Quarantined target memory must be excluded from retrieval"

    # Rejection reason must be documented in diagnostics
    assert target_id in diag_target.get("gate_reasons", {}), "Diagnostics must explain rejection of target memory"
    rejection_reason = diag_target["gate_reasons"][target_id]
    assert ("quarantined" in rejection_reason or "deprecated" in rejection_reason), (
        f"Rejection reason must indicate quarantine/deprecation, got: {rejection_reason}"
    )

    # Funnel invariant: candidateCount >= admissibleCount >= retrievedCount
    cand_cnt = diag_target.get("candidate_count", 0)
    adm_cnt = diag_target.get("admissible_count", 0)
    ret_cnt = len(retrieved_target_matches)
    assert cand_cnt >= adm_cnt >= ret_cnt, (
        f"Funnel invariant violated for target query: cand={cand_cnt}, adm={adm_cnt}, ret={ret_cnt}"
    )

    # 2. Query matching the healthy control memory
    control_query = "Implement is_prime function to determine whether an integer is prime"
    retrieved_control_matches, diag_control = await retriever.retrieve_with_diagnostics(
        query=control_query,
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )

    # Healthy control memory MUST be retrievable
    retrieved_control_ids = [m.experience.id for m in retrieved_control_matches]
    assert control_id in retrieved_control_ids, "Healthy control memory must be retrieved for its own relevant query"
    top_control = retrieved_control_matches[0]
    assert top_control.experience.id == control_id
    assert top_control.experience.trust_score == 0.90
    assert top_control.experience.status == ExperienceStatus.ACTIVE

    # Funnel invariant holds for control query as well
    c_cand_cnt = diag_control.get("candidate_count", 0)
    c_adm_cnt = diag_control.get("admissible_count", 0)
    c_ret_cnt = len(retrieved_control_matches)
    assert c_cand_cnt >= c_adm_cnt >= c_ret_cnt, (
        f"Funnel invariant violated for control query: cand={c_cand_cnt}, adm={c_adm_cnt}, ret={c_ret_cnt}"
    )

    # -------------------------------------------------------------------------
    # PHASE 6: Verify No Silent Reactivation
    # -------------------------------------------------------------------------
    # Attempt an ordinary trust update (even one with outcome_score=1.0)
    s_reactivate, r_reactivate = compute_next_trust(reloaded_target.trust_score, outcome_score=1.0)
    await reloaded_store.update_trust(
        target_id,
        new_trust=s_reactivate,
        reason=r_reactivate,
        execution_id="task_attempt_reactivate",
        binary_outcome=1,
    )

    post_reactivate_target = await reloaded_store.get_experience(target_id)
    # Status must remain DEPRECATED - no silent reactivation without explicit administrative override
    assert post_reactivate_target.status == ExperienceStatus.DEPRECATED, (
        "Quarantined memory must not silently reactivate from ordinary task outcomes"
    )

    # Ensure memory is still excluded from retrieval
    post_retrieved, _ = await retriever.retrieve_with_diagnostics(
        query=target_query,
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )
    assert target_id not in [m.experience.id for m in post_retrieved]
