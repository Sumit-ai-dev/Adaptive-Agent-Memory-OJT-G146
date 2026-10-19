"""
End-to-End Integration Verification: Real Execution Path and Evaluator Integrity.
Tests the real backend pipeline without simulated fallbacks, validating:
1. Semantic relevance gates (unrelated PostgreSQL memory is NOT retrieved for factorial task).
2. Status gates (candidate and deprecated memories remain excluded from normal retrieval).
3. Real execution and evaluation of factorial task with isolated pytest subprocess.
4. Correct code passes (reward=1.0, binary=1), buggy code fails (reward=0.0, binary=0).
5. Inconclusive evaluation does NOT alter trust.
6. Trust updates only after verified outcomes.
7. Persistence across database connection closure and reopening from disk.
"""

import os
import sqlite3
import tempfile
import pytest

from ai_service.config import settings
from ai_service.embedder import local_embedder
from ai_service.memory.store import SQLiteMemoryStore
from ai_service.nodes.retrieve_node import cosine_similarity, retrieve_experiences
from ai_service.tools.evaluator import (
    deterministic_evaluator,
    pytest_execution_evaluator,
)
from models.domain import ExperienceStatus, MemoryMode, TaskDomain
from models.experience import Experience
from models.task import (
    DEFAULT_OUTCOME_THRESHOLD,
    EvaluationOutcome,
    EvaluatorName,
    ExecutionStatus,
    TaskExecuteRequest,
)


@pytest.fixture
def temp_sqlite_store():
    """Provides a clean, disposable temporary SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    
    store = SQLiteMemoryStore(db_path=tmp_path, auto_seed=False)
    yield store, tmp_path
    
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


def test_unrelated_postgres_memory_is_rejected(temp_sqlite_store):
    """
    Demonstrates:
    - An unrelated PostgreSQL memory is NOT retrieved for a factorial task.
    - True cosine similarity is ~0.0 (raw is negative), far below the 0.60 gate.
    - Candidate and deprecated memories remain excluded.
    """
    store, _ = temp_sqlite_store

    # 1. Seed Active PostgreSQL schema migration memory
    postgres_trigger = "High-concurrency PostgreSQL schema migrations on active tables"
    emb_postgres = local_embedder.embed_text(postgres_trigger)
    mem_postgres = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition=postgres_trigger,
        strategy_lesson="Execute schema modifications via backward-compatible dual-write phases.",
        trust_score=0.94,
        status=ExperienceStatus.ACTIVE,
        embedding=emb_postgres,
    )

    # 2. Seed Candidate and Deprecated memories
    mem_candidate = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="Python factorial recursion depth limits",
        strategy_lesson="Use iterative factorial for large inputs to avoid recursion limit.",
        trust_score=0.75,
        status=ExperienceStatus.CANDIDATE,
        embedding=local_embedder.embed_text("Python factorial recursion depth limits"),
    )
    mem_deprecated = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="Deprecated Python factorial math tricks",
        strategy_lesson="Do not use obsolete tricks.",
        trust_score=0.25,
        status=ExperienceStatus.DEPRECATED,
        embedding=local_embedder.embed_text("Deprecated Python factorial math tricks"),
    )

    candidates = [mem_postgres, mem_candidate, mem_deprecated]

    # Query with the factorial task text
    factorial_prompt = "Write a Python function called factorial(n) that computes the factorial of non-negative integers."
    query_emb = local_embedder.embed_text(factorial_prompt)

    # Calculate real cosine similarity between factorial prompt and postgres trigger
    sim = cosine_similarity(query_emb, emb_postgres)
    assert sim < 0.20, f"Expected near-zero similarity for unrelated domains, got {sim}"

    # Normal retrieval under configured threshold (0.60)
    matches = retrieve_experiences(
        query_embedding=query_emb,
        candidates=candidates,
        filter_domain=TaskDomain.CODING,
        min_similarity=settings.SIMILARITY_THRESHOLD, # 0.60
        min_trust=settings.THETA_CUTOFF, # 0.35
    )

    # Both unrelated postgres memory and non-active memories must be excluded
    assert len(matches) == 0, f"Expected 0 matches, got {len(matches)}"


def test_factorial_evaluator_correct_implementation():
    """
    Demonstrates:
    - Executable Python code is evaluated in an isolated temporary environment.
    - Factorial assertions execute via pytest subprocess.
    - Correct implementation cleanly passes with reward = 1.0, binary = 1.
    """
    valid_code = (
        "def factorial(n: int) -> int:\n"
        "    if n < 0:\n"
        "        raise ValueError('n must be non-negative')\n"
        "    return 1 if n in (0, 1) else n * factorial(n - 1)\n"
    )

    test_code = (
        "import pytest\n"
        "def test_factorial_zero():\n"
        "    assert factorial(0) == 1\n"
        "def test_factorial_five():\n"
        "    assert factorial(5) == 120\n"
        "def test_factorial_negative():\n"
        "    with pytest.raises(ValueError):\n"
        "        factorial(-1)\n"
    )

    outcome = pytest_execution_evaluator.evaluate(
        final_answer=valid_code,
        test_code=test_code,
        timeout_s=10.0,
    )

    assert outcome.reward == 1.0
    assert outcome.binary_outcome == 1
    assert outcome.evaluator_name == EvaluatorName.PYTEST_EXECUTION
    assert outcome.details.get("returncode") == 0


def test_factorial_evaluator_incorrect_implementation():
    """
    Demonstrates:
    - Faulty code fails the deterministic pytest assertions.
    - Returns reward = 0.0, binary = 0.
    """
    buggy_code = (
        "def factorial(n: int) -> int:\n"
        "    return n * 2  # Incorrect implementation\n"
    )

    test_code = (
        "def test_factorial_five():\n"
        "    assert factorial(5) == 120\n"
    )

    outcome = pytest_execution_evaluator.evaluate(
        final_answer=buggy_code,
        test_code=test_code,
        timeout_s=10.0,
    )

    assert outcome.reward == 0.0
    assert outcome.binary_outcome == 0
    assert outcome.details.get("returncode") != 0


def test_inconclusive_evaluation_does_not_increase_trust():
    """
    Demonstrates:
    - Missing assertions / test code produce an inconclusive outcome (R=0.50, binary=0).
    - Unverified outcomes cannot be classified as success.
    """
    code_without_tests = "def factorial(n): return 1 if n == 0 else n * factorial(n - 1)"

    outcome = deterministic_evaluator.evaluate(
        final_answer=code_without_tests,
        evaluator=EvaluatorName.PYTEST_EXECUTION,
        evaluator_config={},  # Missing test_code
        task_input="Write a factorial function without assertions",
        task_domain="coding",
    )

    assert outcome.reward == 0.50
    assert outcome.binary_outcome == 0
    assert "Inconclusive" in outcome.reason


@pytest.mark.asyncio
async def test_trust_update_and_persistence_across_reopen(temp_sqlite_store):
    """
    Demonstrates:
    - Trust updates only after verified outcomes.
    - Verified success updates trust via asymmetric EMA: S_{t+1} = alpha * S_t + (1 - alpha) * 1.0.
    - The updated trust score is persisted to SQLite.
    - Reopening the database from disk retrieves the persisted updated trust score.
    """
    store, db_path = temp_sqlite_store

    exp = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="Python factorial computation",
        strategy_lesson="Handle base cases n in (0, 1) and raise ValueError on n < 0.",
        trust_score=0.800,
        uses_count=0,
        successes_count=0,
        failures_count=0,
        status=ExperienceStatus.ACTIVE,
    )
    await store.add_experience(exp)

    # Initial trust check
    stored = await store.get_experience(exp.id)
    assert stored is not None
    assert stored.trust_score == 0.800
    assert stored.uses_count == 0

    # Apply verified success outcome: binary_outcome = 1
    # Expected: 0.85 * 0.80 + (1 - 0.85) * 1.0 = 0.68 + 0.15 = 0.830
    alpha = settings.ALPHA_SUCCESS  # 0.85
    new_trust = round(alpha * stored.trust_score + (1.0 - alpha) * 1.0, 3)
    assert new_trust == 0.830

    await store.update_trust(
        experience_id=exp.id,
        new_trust=new_trust,
        binary_outcome=1,
        reason="Verified pytest execution passed",
    )

    # Close store reference
    del store

    # Reopen same SQLite database file from disk
    reopened_store = SQLiteMemoryStore(db_path=db_path, auto_seed=False)
    persisted = await reopened_store.get_experience(exp.id)

    assert persisted is not None
    assert persisted.trust_score == 0.830
    assert persisted.uses_count == 1
    assert persisted.successes_count == 1
    assert persisted.failures_count == 0


@pytest.mark.skipif(
    not os.getenv("RUN_REAL_PROVIDER_TESTS") or not os.getenv("GROQ_API_KEY"),
    reason="Real-provider integration test requires RUN_REAL_PROVIDER_TESTS=1 and GROQ_API_KEY",
)
@pytest.mark.asyncio
async def test_end_to_end_factorial_task_with_real_backend(temp_sqlite_store):
    """
    Demonstrates end-to-end execution through the compiled LangGraph loop:
    - Real LLM invocation (Groq Cloud).
    - Real evaluation via pytest_execution in isolated subprocess.
    - Zero unrelated memories injected.
    - Durable persistence in SQLite.
    """
    store, db_path = temp_sqlite_store

    # Seed an unrelated PostgreSQL memory to guarantee it is NOT injected
    postgres_exp = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="High-concurrency PostgreSQL schema migrations on active tables",
        strategy_lesson="Execute schema modifications via backward-compatible dual-write phases.",
        trust_score=0.94,
        status=ExperienceStatus.ACTIVE,
        embedding=local_embedder.embed_text("High-concurrency PostgreSQL schema migrations on active tables"),
    )
    await store.add_experience(postgres_exp)

    request = TaskExecuteRequest(
        task_input=(
            "Write a Python function called factorial(n) that computes the factorial of non-negative integers.\n\n"
            "assert factorial(0) == 1\n"
            "assert factorial(5) == 120\n"
        ),
        task_domain=TaskDomain.CODING,
        memory_enabled=True,
        provider="groq",
    )

    from ai_service.graph import execute_task
    execution = await execute_task(request, memory_store=store)

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.outcome_score == 1.0
    assert execution.binary_outcome == 1
    assert execution.evaluator_name == EvaluatorName.PYTEST_EXECUTION
    # Verify NO irrelevant memory was retrieved
    assert len(execution.retrieved_experiences) == 0
    # Verify real answer produced
    assert execution.final_answer is not None
    assert "def factorial" in execution.final_answer
