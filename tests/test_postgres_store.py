"""
Tests for PostgreSQL (pgvector) and Supabase Multi-Engine Experience Memory Persistence.
Validates:
- DDL schema generation and HNSW index creation
- pgvector cosine distance operator (<=>) and query semantics
- F3 counter invariants on trust updates (uses, successes, failures)
- Supabase REST RPC match_experiences and resilient cosine fallback
- get_memory_store() factory resolution and graceful fallbacks
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ai_service.memory.store import (
    BaseMemoryStore,
    PostgresMemoryStore,
    SQLiteMemoryStore,
    SupabaseMemoryStore,
    get_memory_store,
)
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience, ExperienceStatus as ExpStatus


@pytest.mark.asyncio
async def test_postgres_memory_store_init_and_ddl():
    """Verify PostgresMemoryStore initializes tables with vector(384) and HNSW index."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)
    await store.init_db()

    # Verify DDL calls
    execute_calls = [call.args[0] for call in mock_conn.execute.call_args_list]
    assert any("CREATE EXTENSION IF NOT EXISTS vector" in q for q in execute_calls)
    assert any("embedding vector(384)" in q for q in execute_calls)
    assert any("hnsw" in q.lower() for q in execute_calls)


@pytest.mark.asyncio
async def test_postgres_memory_store_add_experience():
    """Verify add_experience writes experience with embedding vector to Postgres."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)
    store._initialized = True

    exp = Experience(
        id="exp-pg-001",
        task_domain=TaskDomain.CODING,
        trigger_condition="High concurrency PostgreSQL connection pool exhaustion",
        strategy_lesson="Use asyncpg connection pooling with max_size bounds",
        pitfall="Do not open unbounded connections per request",
        confidence=0.90,
        trust_score=0.85,
        uses_count=10,
        successes_count=9,
        failures_count=1,
        status=ExpStatus.ACTIVE,
        embedding=[0.1] * 384,
    )

    exp_id = await store.add_experience(exp)
    assert exp_id == "exp-pg-001"
    assert mock_conn.execute.called

    query, *args = mock_conn.execute.call_args.args
    assert "INSERT INTO experiences" in query
    assert "ON CONFLICT (id) DO UPDATE" in query
    assert args[0] == "exp-pg-001"
    assert args[2] == "coding"
    assert len(args[12]) == 384


@pytest.mark.asyncio
async def test_postgres_memory_store_search_similar_pgvector():
    """Verify pgvector <=> cosine similarity query execution and record mapping."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    mock_row = {
        "id": "exp-pg-001",
        "user_id": None,
        "task_domain": "coding",
        "trigger_condition": "High concurrency connection pool",
        "strategy_lesson": "Use bounded connection pool",
        "pitfall": None,
        "confidence": 0.90,
        "trust_score": 0.85,
        "uses_count": 5,
        "successes_count": 5,
        "failures_count": 0,
        "status": "active",
        "embedding": [0.1] * 384,
        "source_task_id": None,
        "created_at": "2026-10-13T00:00:00Z",
        "updated_at": "2026-10-13T00:00:00Z",
        "similarity": 0.92,
    }
    mock_conn.fetch.return_value = [mock_row]

    store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)
    store._initialized = True

    results = await store.search_similar([0.1] * 384, domain=TaskDomain.CODING, top_k=3)
    assert len(results) == 1
    exp, sim = results[0]
    assert exp.id == "exp-pg-001"
    assert pytest.approx(sim, abs=1e-3) == 0.92

    query = mock_conn.fetch.call_args.args[0]
    assert "<=>" in query
    assert "1 - (embedding <=> $1) AS similarity" in query


@pytest.mark.asyncio
async def test_postgres_memory_store_update_trust_f3_invariants():
    """Verify F3 counter updates and audit ledger entries in Postgres."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Mock transaction context manager
    mock_tx = MagicMock()
    mock_tx.__aenter__ = AsyncMock(return_value=None)
    mock_tx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=mock_tx)

    mock_conn.fetchrow.return_value = {
        "trust_score": 0.75,
        "status": "active",
        "uses_count": 4,
        "successes_count": 3,
        "failures_count": 1,
    }

    store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)
    store._initialized = True

    # 1. Success observation (binary_outcome=1)
    record = await store.update_trust(
        experience_id="exp-pg-001",
        new_trust=0.82,
        reason="Verified success",
        execution_id="exec-001",
        binary_outcome=1,
    )
    assert record.experience_id == "exp-pg-001"
    assert pytest.approx(record.delta, abs=1e-3) == 0.07

    # Check update SQL args: uses_inc=1, succ_inc=1, fail_inc=0
    update_call = mock_conn.execute.call_args_list[0]
    u_sql, *u_args = update_call.args
    assert "UPDATE experiences SET" in u_sql
    assert u_args[0] == 0.82  # new_trust
    assert u_args[2] == 1     # uses_inc
    assert u_args[3] == 1     # successes_inc
    assert u_args[4] == 0     # failures_inc

    # Check trust_history insertion
    insert_call = mock_conn.execute.call_args_list[1]
    i_sql, *i_args = insert_call.args
    assert "INSERT INTO trust_history" in i_sql
    assert i_args[1] == "exp-pg-001"


@pytest.mark.asyncio
async def test_supabase_memory_store_search_similar_rpc():
    """Verify SupabaseMemoryStore calls RPC match_experiences endpoint."""
    store = SupabaseMemoryStore(
        url="https://xyzproject.supabase.co",
        anon_key="test-anon-key",
    )

    fake_rpc_response = [
        {
            "id": "exp-sb-001",
            "task_domain": "analysis",
            "trigger_condition": "Financial time series gaps",
            "strategy_lesson": "Forward fill max 2 steps",
            "pitfall": None,
            "confidence": 0.85,
            "trust_score": 0.80,
            "uses_count": 8,
            "successes_count": 7,
            "failures_count": 1,
            "status": "active",
            "similarity": 0.88,
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_rpc_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        results = await store.search_similar([0.1] * 384, domain=TaskDomain.ANALYSIS, top_k=2)
        assert len(results) == 1
        exp, sim = results[0]
        assert exp.id == "exp-sb-001"
        assert pytest.approx(sim, abs=1e-3) == 0.88
        assert mock_post.called
        assert mock_post.call_args.args[0] == "/rest/v1/rpc/match_experiences"


def test_get_memory_store_factory():
    """Verify get_memory_store() factory handles sqlite, postgres, and supabase selections."""
    # 1. SQLite default
    store1 = get_memory_store(engine="sqlite", auto_seed=False)
    assert isinstance(store1, SQLiteMemoryStore)

    # 2. Postgres with URL
    store2 = get_memory_store(engine="postgres", database_url="postgresql://localhost/test", auto_seed=False)
    assert isinstance(store2, PostgresMemoryStore)

    # 3. Postgres without URL falls back safely to SQLite
    store3 = get_memory_store(engine="postgres", database_url=None, auto_seed=False)
    assert isinstance(store3, SQLiteMemoryStore)

    # 4. Supabase with URL and Key
    store4 = get_memory_store(
        engine="supabase",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        auto_seed=False,
    )
    assert isinstance(store4, SupabaseMemoryStore)
