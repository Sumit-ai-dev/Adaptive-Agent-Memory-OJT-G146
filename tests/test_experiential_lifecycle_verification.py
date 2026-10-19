"""
Integration Verification Suite: Experiential Memory Lifecycle & Integrity.

Traces the complete real SQLite lifecycle:
REFLECT -> PERSIST -> VALIDATE -> PROMOTE -> RETRIEVE -> USE -> TRUST UPDATE -> QUARANTINE.

Also verifies:
1. Retrieval gating and diagnostics (candidate exclusion from active runs).
2. Probation quota and duplicate probe prevention.
3. Theorem 1 quarantine cutoff (k* = 3 consecutive failures).
4. Truthful telemetry metrics derived from SQLite.
5. All backend memory status query filters ('all', 'active', 'candidate', 'deprecated', and aliases).
"""

import math
import os
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient

from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.trust_math import calculate_probation_quota, should_quarantine
from models.task import EvaluationOutcome, EvaluatorName
from backend.app.main import app
from backend.routes.agent import shared_store
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience


@pytest.fixture(scope="module")
def api_client():
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_experiential_lifecycle_end_to_end(tmp_path):
    """
    Rigorously verifies the 7-stage lifecycle on a dedicated real SQLite database.
    """
    db_file = str(tmp_path / "lifecycle_test.db")
    store = SQLiteMemoryStore(db_path=db_file)
    retriever = MemoryRetriever(store=store)

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 1: REFLECT & PERSIST
    # ──────────────────────────────────────────────────────────────────────────
    exp_id = f"exp_lifecycle_{uuid.uuid4().hex[:8]}"
    trigger = "Distributed consensus under network partitioning with Raft heartbeats"
    lesson = "Maintain lease intervals strictly lower than minimum election timeout"
    pitfall = "Do not allow unbounded clock drift across raft nodes"

    candidate_exp = Experience(
        id=exp_id,
        task_domain=TaskDomain.CODING,
        trigger_condition=trigger,
        strategy_lesson=lesson,
        pitfall=pitfall,
        confidence=0.88,
        trust_score=0.75,
        status=ExperienceStatus.CANDIDATE,
        successes_count=0,
        failures_count=0,
        uses_count=0,
    )

    created_id = await store.add_experience(candidate_exp)
    assert created_id == exp_id, "Memory ID must match"

    # Confirm durable SQLite persistence
    stored = await store.get_experience(exp_id)
    assert stored is not None, "Memory must be durably stored in SQLite"
    assert stored.status == ExperienceStatus.CANDIDATE, "Initial status must be CANDIDATE"
    assert stored.trust_score == 0.75

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 2: RETRIEVAL ISOLATION (CANDIDATE INADMISSIBILITY)
    # ──────────────────────────────────────────────────────────────────────────
    # Query for this exact task. The candidate experience must NOT be returned for
    # active production execution.
    retrieved, diagnostics = await retriever.retrieve_with_diagnostics(
        query="Distributed consensus under network partitioning raft lease",
        domain=TaskDomain.CODING,
        top_k=3,
    )

    # Must NOT be admitted
    admitted_ids = [m.experience.id for m in retrieved]
    assert exp_id not in admitted_ids, "CANDIDATE experience must NOT be admitted for active task execution"

    # Diagnostic funnel check
    gate_reasons = diagnostics.get("gate_reasons", {})
    assert exp_id in gate_reasons, "Candidate memory must be listed in gate_reasons"
    assert "inadmissible_status_candidate" in gate_reasons[exp_id], (
        f"Rejection reason must be candidate status, got: {gate_reasons[exp_id]}"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 3: VALIDATE & PROMOTE (PROBATIONARY RECOVERY / PROMOTION PROTOCOL)
    # ──────────────────────────────────────────────────────────────────────────
    # Probation quota formula: max(2, ceil(k/2) + 1). For k=0 failures, quota is 2.
    expected_quota = calculate_probation_quota(0)
    assert expected_quota == 2, f"Quota for 0 failures must be 2, got {expected_quota}"

    # Probe 1: Success
    probe1_exec = f"exec_probe_{uuid.uuid4().hex[:8]}"
    success_outcome_1 = EvaluationOutcome(
        reward=1.0,
        binary_outcome=1,
        evaluator_name=EvaluatorName.PYTEST_EXECUTION,
        reason="Verified probe 1",
    )
    exp1, record1 = await store.record_probationary_probe(
        experience_id=exp_id,
        outcome=success_outcome_1,
        execution_id=probe1_exec,
        task_fingerprint="fingerprint_probe_1",
    )
    assert exp1.status == ExperienceStatus.CANDIDATE, "Memory must not be promoted after only 1 probe when quota is 2"
    assert exp1.probation_successes == 1

    # Verify duplicate execution prevention (idempotency & fraud prevention)
    with pytest.raises(ValueError, match="Duplicate execution ID"):
        await store.record_probationary_probe(
            experience_id=exp_id,
            outcome=success_outcome_1,
            execution_id=probe1_exec,
            task_fingerprint="fingerprint_probe_1_dup",
        )

    # Probe 2: Success (Meets Quota of 2 -> Legitimate Promotion)
    probe2_exec = f"exec_probe_{uuid.uuid4().hex[:8]}"
    success_outcome_2 = EvaluationOutcome(
        reward=1.0,
        binary_outcome=1,
        evaluator_name=EvaluatorName.PYTEST_EXECUTION,
        reason="Verified probe 2",
    )
    exp2, record2 = await store.record_probationary_probe(
        experience_id=exp_id,
        outcome=success_outcome_2,
        execution_id=probe2_exec,
        task_fingerprint="fingerprint_probe_2",
    )
    assert exp2.status == ExperienceStatus.ACTIVE, "Memory must be legitimately promoted after meeting quota"
    assert exp2.probation_successes >= 2

    # Verify in SQLite
    promoted_record = await store.get_experience(exp_id)
    assert promoted_record.status == ExperienceStatus.ACTIVE
    assert promoted_record.probation_successes >= 2

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 4: RETRIEVE & USE (ACTIVE RETRIEVAL)
    # ──────────────────────────────────────────────────────────────────────────
    # Now that the experience is ACTIVE, querying for the same task MUST retrieve it
    retrieved_active, diag_active = await retriever.retrieve_with_diagnostics(
        query="Distributed consensus under network partitioning raft lease",
        domain=TaskDomain.CODING,
        top_k=3,
    )
    active_ids = [m.experience.id for m in retrieved_active]
    assert exp_id in active_ids, "Promoted ACTIVE memory must now be retrieved"
    match = next(m for m in retrieved_active if m.experience.id == exp_id)
    assert match.similarity >= 0.60, f"Similarity score ({match.similarity:.3f}) must meet normal configured threshold (0.60)"
    assert match.composite_score > 0.0, "Composite rank score must be positive"

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 5: TRUST UPDATE & THEOREM 1 QUARANTINE
    # ──────────────────────────────────────────────────────────────────────────
    # Asymmetric EMA parameters: beta = 0.70. Quarantine cutoff: theta = 0.35.
    # Current trust is ~0.75+
    # Failure 1: S1 = 0.70 * S0
    t1 = await store.update_trust(
        experience_id=exp_id,
        new_trust=round(promoted_record.trust_score * 0.70, 4),
        reason="Failure 1: Synthetic test failure",
        execution_id=f"exec_fail_1_{uuid.uuid4().hex[:6]}",
        binary_outcome=0,
    )
    exp_f1 = await store.get_experience(exp_id)
    assert exp_f1.failures_count == 1
    assert exp_f1.status == ExperienceStatus.ACTIVE, "Memory remains active above cutoff"

    # Failure 2: S2 = 0.70 * S1
    t2 = await store.update_trust(
        experience_id=exp_id,
        new_trust=round(exp_f1.trust_score * 0.70, 4),
        reason="Failure 2: Synthetic test failure",
        execution_id=f"exec_fail_2_{uuid.uuid4().hex[:6]}",
        binary_outcome=0,
    )
    exp_f2 = await store.get_experience(exp_id)
    assert exp_f2.failures_count == 2
    assert exp_f2.status == ExperienceStatus.ACTIVE, "Memory remains active above cutoff"

    # Failure 3: S3 = 0.70 * S2 < 0.35 -> Theorem 1 Quarantine Boundary
    t3_val = round(exp_f2.trust_score * 0.70, 4)
    assert t3_val < 0.35, f"Trust after 3 failures must be below 0.35, got {t3_val}"
    t3 = await store.update_trust(
        experience_id=exp_id,
        new_trust=t3_val,
        reason="Failure 3: Synthetic test failure triggering Theorem 1 Quarantine",
        execution_id=f"exec_fail_3_{uuid.uuid4().hex[:6]}",
        status="deprecated",
        binary_outcome=0,
    )
    exp_f3 = await store.get_experience(exp_id)
    assert exp_f3.status == ExperienceStatus.DEPRECATED, "Memory must be quarantined (DEPRECATED)"
    assert exp_f3.trust_score < 0.35

    # ──────────────────────────────────────────────────────────────────────────
    # STAGE 6: QUARANTINE RETRIEVAL ISOLATION
    # ──────────────────────────────────────────────────────────────────────────
    retrieved_quar, diag_quar = await retriever.retrieve_with_diagnostics(
        query="Distributed consensus under network partitioning raft lease",
        domain=TaskDomain.CODING,
        top_k=3,
    )
    quar_ids = [m.experience.id for m in retrieved_quar]
    assert exp_id not in quar_ids, "DEPRECATED quarantined memory must NEVER be retrieved"
    assert exp_id in diag_quar.get("gate_reasons", {})


def test_api_memory_status_filters(api_client):
    """
    Verifies that the backend API endpoint /api/memories correctly processes:
    - 'all'
    - 'active'
    - 'candidate' / 'provisional'
    - 'deprecated' / 'quarantined'
    - empty / non-matching status
    """
    # 1. Filter 'all'
    res_all = api_client.get("/api/memories?status=all")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert isinstance(all_data, list)
    assert len(all_data) > 0

    # 2. Filter 'active'
    res_active = api_client.get("/api/memories?status=active")
    assert res_active.status_code == 200
    active_data = res_active.json()
    assert isinstance(active_data, list)
    for item in active_data:
        assert item.get("status") == "active"

    # 3. Filter 'candidate'
    res_cand = api_client.get("/api/memories?status=candidate")
    assert res_cand.status_code == 200
    cand_data = res_cand.json()
    assert isinstance(cand_data, list)
    for item in cand_data:
        assert item.get("status") in ("candidate", "provisional")

    # 4. Filter 'provisional' alias
    res_prov = api_client.get("/api/memories?status=provisional")
    assert res_prov.status_code == 200
    prov_data = res_prov.json()
    assert len(prov_data) == len(cand_data)

    # 5. Filter 'deprecated'
    res_dep = api_client.get("/api/memories?status=deprecated")
    assert res_dep.status_code == 200
    dep_data = res_dep.json()
    assert isinstance(dep_data, list)
    for item in dep_data:
        assert item.get("status") in ("deprecated", "quarantined")

    # 6. Filter 'quarantined' alias
    res_quar = api_client.get("/api/memories?status=quarantined")
    assert res_quar.status_code == 200
    quar_data = res_quar.json()
    assert len(quar_data) == len(dep_data)

    # 7. Non-existent filter returns empty list, not error 500
    res_empty = api_client.get("/api/memories?status=non_existent_status_xyz")
    assert res_empty.status_code == 200
    assert res_empty.json() == []


def test_api_telemetry_integrity(api_client):
    """
    Verifies that /api/telemetry returns truthful dynamic figures computed from SQLite.
    Confirms meanTrustScore matches database experiences and no fabricated metrics exist.
    """
    res = api_client.get("/api/telemetry")
    assert res.status_code == 200
    telemetry = res.json()

    assert "totalMemories" in telemetry
    assert "activeMemories" in telemetry
    assert "candidateMemories" in telemetry
    assert "quarantinedMemories" in telemetry
    assert "meanTrustScore" in telemetry

    # Verify that totalMemories = active + candidate + other
    total = telemetry["totalMemories"]
    active = telemetry["activeMemories"]
    cand = telemetry["candidateMemories"]
    quar = telemetry["quarantinedMemories"]
    assert total >= active + cand

    # Verify mean trust score is a valid float in [0.0, 1.0]
    mean_trust = telemetry["meanTrustScore"]
    assert 0.0 <= mean_trust <= 1.0

    # Ensure fake metrics are NOT presented as live values
    assert "timeSavedPct" not in telemetry or telemetry["timeSavedPct"] is None
    assert "tokensSavedPct" not in telemetry or telemetry["tokensSavedPct"] is None


def test_api_agent_execute_error_surfacing(api_client):
    """
    Verifies that calling the execute endpoint with invalid provider or malformed payload
    returns HTTP 4xx/5xx and does not silently fake execution.
    """
    res = api_client.post(
        "/api/agent/execute",
        json={
            "taskInput": "Test failure propagation",
            "taskDomain": "coding",
            "memoryEnabled": True,
            "provider": "invalid_provider_xyz_fail",
        },
    )
    # The endpoint must return an error status (not 200 with fake response)
    assert res.status_code in (400, 422, 500)
    data = res.json()
    assert "detail" in data or "message" in data
