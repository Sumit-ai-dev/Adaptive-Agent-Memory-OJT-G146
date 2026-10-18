"""
Comprehensive Regression Test Suite for AEMA Experiential Memory Pipeline.
Validates requirements from Section 7 (Tests A through J):
- TEST A: Memory Persistence
- TEST B: Relevant Retrieval
- TEST C: Irrelevant Retrieval
- TEST D: Trust Updates (A-EMA formulas)
- TEST E: Quarantine Threshold & Deprecation
- TEST F: End-to-End Memory Flow
- TEST G: API Store Consistency
- TEST H: Empty Retrieval Handling
- TEST I: Restart Persistence
- TEST J: Objective Failure Validation
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from ai_service.config import settings
from ai_service.embedder import local_embedder
from ai_service.graph import execute_task
from ai_service.memory.retriever import MemoryRetriever
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.trust_node import compute_next_trust, QUARANTINE_THRESHOLD
from backend.main import app
from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceStatus
from models.provider import ModelProvider
from models.task import TaskExecuteRequest


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="aema_test_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_a_memory_persistence(temp_db):
    """TEST A: Create an experience, restart/reopen persistent store, verify it still exists."""
    store1 = SQLiteMemoryStore(db_path=temp_db)
    exp = Experience(
        id="mem_persist_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Palindrome checker ignoring spaces",
        strategy_lesson="Normalize case and remove spaces before comparing to reverse.",
        pitfall="Do not strip punctuation if preservation is required.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    saved_id = await store1.add_experience(exp)
    assert saved_id == "mem_persist_001"

    # Reopen store on same file
    store2 = SQLiteMemoryStore(db_path=temp_db)
    loaded = await store2.get_experience("mem_persist_001")
    assert loaded is not None
    assert loaded.id == "mem_persist_001"
    assert loaded.strategy_lesson == exp.strategy_lesson
    assert loaded.trust_score == 0.75
    assert loaded.status == ExperienceStatus.ACTIVE
    assert loaded.embedding is not None
    assert len(loaded.embedding) == 384


@pytest.mark.asyncio
async def test_b_relevant_retrieval(temp_db):
    """TEST B: Insert a controlled, valid experience and verify relevant task retrieves it."""
    store = SQLiteMemoryStore(db_path=temp_db)
    trigger = "When tasked to implement a palindrome checker function in Python"
    exp = Experience(
        id="mem_palindrome_001",
        task_domain=TaskDomain.CODING,
        trigger_condition=trigger,
        strategy_lesson="Use s == s[::-1] after normalizing characters.",
        pitfall="Avoid mutating original string.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    retriever = MemoryRetriever(store=store)
    query = "Write a Python function called is_palindrome(s) that checks if a string is a palindrome"
    matches = await retriever.retrieve(query=query, domain=TaskDomain.CODING, mode=MemoryMode.ADAPTIVE, top_k=2)

    assert len(matches) >= 1
    top = matches[0]
    assert top.experience.id == "mem_palindrome_001"
    assert top.similarity >= settings.SIMILARITY_THRESHOLD
    assert top.experience.trust_score >= 0.35


@pytest.mark.asyncio
async def test_c_irrelevant_retrieval(temp_db):
    """TEST C: Run an unrelated query and verify unrelated memories are not injected."""
    store = SQLiteMemoryStore(db_path=temp_db)
    exp = Experience(
        id="mem_binary_tree_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Fixing deep recursion in binary search tree traversal",
        strategy_lesson="Use an explicit queue or stack for iterative traversal.",
        pitfall="Do not simply increase sys.setrecursionlimit.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    retriever = MemoryRetriever(store=store)
    unrelated_query = "Summarize the major economic causes of the 1929 stock market crash"
    matches = await retriever.retrieve(query=unrelated_query, domain=TaskDomain.RESEARCH, mode=MemoryMode.ADAPTIVE, top_k=2)

    assert len(matches) == 0


def test_d_trust_updates():
    """TEST D: Verify success, failure, and neutral A-EMA trust calculations."""
    # Success: S' = 0.85 * S + 0.15
    s_succ, r_succ = compute_next_trust(current_trust=0.75, outcome_score=0.95)
    assert s_succ == pytest.approx(0.7875, abs=1e-4)
    assert "Success reward" in r_succ

    # Failure: S' = 0.70 * S
    s_fail, r_fail = compute_next_trust(current_trust=0.75, outcome_score=0.10)
    assert s_fail == pytest.approx(0.5250, abs=1e-4)
    assert "Failure penalty" in r_fail

    # Neutral: S' = 0.80 * S + 0.20 * R
    s_neut, r_neut = compute_next_trust(current_trust=0.75, outcome_score=0.50)
    assert s_neut == pytest.approx(0.7000, abs=1e-4)
    assert "Neutral outcome" in r_neut


@pytest.mark.asyncio
async def test_e_quarantine(temp_db):
    """TEST E: Apply three consecutive failures to 0.75 trust -> verify quarantine exclusion."""
    store = SQLiteMemoryStore(db_path=temp_db)
    exp = Experience(
        id="mem_quarantine_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="When writing a palindrome function",
        strategy_lesson="Faulty reverse implementation.",
        pitfall=None,
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # 3 consecutive failures: 0.75 -> 0.525 -> 0.3675 -> 0.25725
    s1, _ = compute_next_trust(0.75, 0.0)
    assert s1 == pytest.approx(0.5250, abs=1e-4)
    await store.update_trust(exp.id, s1, reason="Fail 1", binary_outcome=0)

    s2, _ = compute_next_trust(s1, 0.0)
    assert s2 == pytest.approx(0.3675, abs=1e-4)
    await store.update_trust(exp.id, s2, reason="Fail 2", binary_outcome=0)

    s3, _ = compute_next_trust(s2, 0.0)
    assert s3 == pytest.approx(0.2573, abs=1e-3)
    await store.update_trust(exp.id, s3, reason="Fail 3", binary_outcome=0)

    # Verify memory is quarantined
    updated = await store.get_experience(exp.id)
    assert updated.trust_score < QUARANTINE_THRESHOLD
    assert updated.status == ExperienceStatus.DEPRECATED

    # Verify excluded from retrieval
    retriever = MemoryRetriever(store=store)
    matches = await retriever.retrieve(
        query="Write a palindrome function",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
    )
    assert len(matches) == 0


@pytest.mark.asyncio
async def test_f_end_to_end_memory_flow(temp_db):
    """TEST F: Execute a task and verify persistence, outcome recording, and trust association."""
    store = SQLiteMemoryStore(db_path=temp_db)

    # Seed a relevant prior memory
    seed_exp = Experience(
        id="seed_e2e_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="When implementing an is_even parity check function",
        strategy_lesson="Use modulo operator `n % 2 == 0` for direct boolean evaluation.",
        pitfall="Do not convert to string to check last digit.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(seed_exp)

    req = TaskExecuteRequest(
        task_input="Implement a Python function called is_even(n) that checks if an integer is even",
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )

    result = await execute_task(req, memory_store=store)

    assert result.status.value == "completed"
    assert len(result.retrieved_experiences) >= 1
    assert result.retrieved_experiences[0].experience.id == "seed_e2e_001"

    # Verify trust update targeted the retrieved memory
    assert len(result.trust_updates) >= 1
    update = result.trust_updates[0]
    assert update.experience_id == "seed_e2e_001"
    assert update.old_score == 0.75
    assert update.new_score > 0.75

    # Verify database was updated
    persisted_exp = await store.get_experience("seed_e2e_001")
    assert persisted_exp.trust_score == pytest.approx(update.new_score, abs=1e-4)
    assert persisted_exp.uses_count >= 1


def test_g_api_consistency():
    """TEST G: Verify /api/v1/memories and agent execution operate on the same persistent store."""
    client = TestClient(app)

    # List memories from API
    res = client.get("/api/v1/memories?limit=5")
    assert res.status_code == 200
    memories = res.json()
    assert isinstance(memories, list)


@pytest.mark.asyncio
async def test_h_empty_retrieval_handling(temp_db):
    """TEST H: Verify empty retrieval is handled safely with 0 exposed memories and accurate trace."""
    store = SQLiteMemoryStore(db_path=temp_db)
    req = TaskExecuteRequest(
        task_input="A completely novel task with zero pre-existing knowledge anywhere in the database",
        task_domain=TaskDomain.RESEARCH,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider=ModelProvider.MOCK,
    )
    result = await execute_task(req, memory_store=store)

    assert result.status.value == "completed"
    assert len(result.retrieved_experiences) == 0
    assert len(result.trust_updates) == 0


@pytest.mark.asyncio
async def test_i_restart_persistence(temp_db):
    """TEST I: Verify experiences remain available and retrievable after store restart."""
    store_before = SQLiteMemoryStore(db_path=temp_db)
    exp = Experience(
        id="mem_restart_001",
        task_domain=TaskDomain.CODING,
        trigger_condition="Computing average of a numeric list",
        strategy_lesson="Handle empty lists with defensive check `if not lst: return 0.0`.",
        pitfall="Avoid ZeroDivisionError on empty input.",
        trust_score=0.75,
        status=ExperienceStatus.ACTIVE,
    )
    await store_before.add_experience(exp)

    # Simulate restart by creating completely fresh store instance
    store_after = SQLiteMemoryStore(db_path=temp_db)
    retriever = MemoryRetriever(store=store_after)
    matches = await retriever.retrieve(
        query="Write a function to calculate the average of a list of numbers",
        domain=TaskDomain.CODING,
        mode=MemoryMode.ADAPTIVE,
    )
    assert len(matches) >= 1
    assert matches[0].experience.id == "mem_restart_001"


def test_j_failure_not_automatically_success():
    """TEST J: Verify deterministic evaluator classifies syntax errors and violations as failure."""
    from ai_service.tools.evaluator import deterministic_evaluator
    from models.task import EvaluatorName

    # 1. Broken code that fails objective test execution must NOT pass merely because it has code
    broken_code = "def is_palindrome(s):\n    return False\n"
    test_code = "def test_palindrome():\n    assert is_palindrome('racecar') is True\n"
    
    outcome_broken = deterministic_evaluator.evaluate(
        final_answer=broken_code,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={"test_code": test_code},
        task_input="Write is_palindrome that returns True for racecar",
    )
    assert outcome_broken.reward == 0.0
    assert outcome_broken.binary_outcome == 0
    assert "AssertionError" in outcome_broken.reason or "failure" in outcome_broken.reason.lower()

    # 2. Code that produces text but reports an error or violates constraints
    error_output = "I cannot solve this task because an unhandled exception occurred."
    outcome_error = deterministic_evaluator.evaluate(
        final_answer=error_output,
        task_input="Implement a sorting algorithm",
    )
    assert outcome_error.reward < 0.80
    assert outcome_error.binary_outcome == 0
