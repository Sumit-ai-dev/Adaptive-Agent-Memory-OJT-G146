"""
Regression test for AEMA retrieval trajectory metadata inconsistency.

Evidence from live execution exec_4a29de5c:
retrievedExperiences contains two memories:
- 8c0aa4fd-9b22-4ce7-bbc0-88d9703d5cb5
- 6368b517-6c0f-456b-8095-9726a294e43f

Trajectory metadata reports:
- retrievedCount = 2
- candidateCount = 0
- admissibleCount = 0
- fallbackOccurred = false
"""

import os
import tempfile
import pytest

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import TaskExecuteRequest


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="aema_test_retrieval_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_reproduce_retrieval_metadata_inconsistency_exec_4a29de5c(temp_db):
    """
    Reproduces the exact scenario of exec_4a29de5c:
    Two active memories are present in the SQLite store for the coding domain.
    Adaptive retrieval selects both memories.
    Checks whether candidateCount and admissibleCount reflect the retrieval funnel
    or are incorrectly 0 due to unpopulated diagnostics.
    """
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed the two exact memories from exec_4a29de5c with trigger conditions matching the task query
    mem1 = Experience(
        id="8c0aa4fd-9b22-4ce7-bbc0-88d9703d5cb5",
        task_domain=TaskDomain.CODING,
        trigger_condition="Implement Python function is_even(n) to check if n is even",
        strategy_lesson="Use n % 2 == 0 directly",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    mem2 = Experience(
        id="6368b517-6c0f-456b-8095-9726a294e43f",
        task_domain=TaskDomain.CODING,
        trigger_condition="Python function is_even(n) that checks if an integer is even",
        strategy_lesson="Use (n & 1) == 0 for parity check",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(mem1)
    await store.add_experience(mem2)

    req = TaskExecuteRequest(
        task_input="Implement a Python function called is_even(n) to check if n is even.",
        task_domain=TaskDomain.CODING,
        evaluator_config={"test_code": "assert is_even(2) is True\nassert is_even(3) is False", "timeout_s": 5.0},
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )

    result = await execute_task(req, memory_store=store)

    # Verify both memories were retrieved
    assert len(result.retrieved_experiences) == 2
    retrieved_ids = {m.experience.id for m in result.retrieved_experiences}
    assert "8c0aa4fd-9b22-4ce7-bbc0-88d9703d5cb5" in retrieved_ids
    assert "6368b517-6c0f-456b-8095-9726a294e43f" in retrieved_ids

    # Inspect the retrieval trajectory step trace
    retrieval_trace = next((t for t in result.trajectory if t.node == "retrieve_node"), None)
    assert retrieval_trace is not None, "Retrieval step must exist in trajectory"
    meta = retrieval_trace.metadata or {}

    assert meta.get("retrievedCount") == 2
    assert meta.get("fallbackOccurred") is False

    # Check whether candidateCount and admissibleCount correctly reflect the funnel:
    # candidateCount >= admissibleCount >= retrievedCount == 2
    assert meta.get("candidateCount") >= 2, (
        f"candidateCount must be at least 2 when 2 memories exist and are considered, got {meta.get('candidateCount')}"
    )
    assert meta.get("admissibleCount") >= 2, (
        f"admissibleCount must be at least 2 when 2 memories pass admission, got {meta.get('admissibleCount')}"
    )
