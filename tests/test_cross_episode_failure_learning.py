"""
Test Suite: Cross-Episode Failure Learning and Pitfall Ingestion.

Validates that:
1. Failed task execution reflections persist with CANDIDATE status in SQLite.
2. Cross-episode queries preserve Theorem 1 candidate isolation (positive strategy
   lessons are NOT admitted to active memory list).
3. Distilled failure pitfalls from CANDIDATE memories are surfaced via
   diagnostics['candidate_pitfalls'] for relevant subsequent queries.
4. The retrieve node populates negative_pitfall from candidate pitfalls,
   ensuring the agent learns from prior failures across separate tasks.
"""

import uuid
import pytest
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.retrieve_node import async_retrieve_node
from models.domain import ExperienceStatus, MemoryMode, TaskDomain
from models.experience import Experience


@pytest.mark.asyncio
async def test_cross_episode_failure_pitfall_retrieval(tmp_path):
    """
    Ensure candidate memory pitfalls from prior failures are admitted
    as negative constraints across distinct episodes without breaching candidate isolation.
    """
    db_file = str(tmp_path / "test_cross_episode.db")
    store = SQLiteMemoryStore(db_path=db_file)
    retriever = MemoryRetriever(store=store)

    # Episode 1: Task A failed due to recursion limit breach.
    # A candidate experience was recorded with a critical pitfall.
    failed_exp_id = f"exp_failure_{uuid.uuid4().hex[:8]}"
    failed_exp = Experience(
        id=failed_exp_id,
        task_domain=TaskDomain.CODING,
        trigger_condition="Graph cycle traversal with recursive DFS",
        strategy_lesson="Use iterative depth first search with an explicit stack",
        pitfall="Avoid recursion without cycle tracking: triggers Python RecursionError",
        confidence=0.75,
        trust_score=0.60,
        status=ExperienceStatus.CANDIDATE,
        successes_count=0,
        failures_count=1,
        uses_count=1,
    )
    await store.add_experience(failed_exp)

    # Episode 2: A new, separate task is executed querying related traversal logic.
    query = "Implement graph cycle detection and deep tree traversal"
    retrieved, diagnostics = await retriever.retrieve_with_diagnostics(
        query=query,
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
        top_k=3,
    )

    # 1. Candidate Isolation: Active retrieved list must NOT include the unproven strategy
    admitted_ids = [m.experience.id for m in retrieved]
    assert failed_exp_id not in admitted_ids, (
        "Unproven strategy lesson from candidate experience must not be directly admitted."
    )

    # 2. Rejection reason recorded truthfully
    assert failed_exp_id in diagnostics.get("gate_reasons", {})
    assert "inadmissible_status_candidate" in diagnostics["gate_reasons"][failed_exp_id]

    # 3. Negative constraint safely extracted for agent steering
    candidate_pitfalls = diagnostics.get("candidate_pitfalls", [])
    assert len(candidate_pitfalls) >= 1
    assert failed_exp.pitfall in candidate_pitfalls

    # 4. Ingested into agent state via async_retrieve_node
    mock_state = {
        "task_id": "task_episode_2",
        "task_input": query,
        "task_domain": "coding",
        "memory_mode": "adaptive",
        "memory_store": store,
        "memory_retriever": retriever,
        "attempt_count": 1,
    }
    state_updates = await async_retrieve_node(mock_state)

    assert "negative_pitfall" in state_updates
    assert state_updates["negative_pitfall"] == failed_exp.pitfall
