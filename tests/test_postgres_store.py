"""
Tests for PostgreSQL (pgvector) and Supabase Multi-Engine Experience Memory Persistence.
Validates:
- DDL schema generation and HNSW index creation
- pgvector cosine distance operator (<=>) and query semantics
- F3 counter invariants on trust updates (uses, successes, failures)
- Supabase REST RPC match_experiences and resilient cosine fallback
- get_memory_store() factory resolution and graceful fallbacks
"""

import asyncio
from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock, patch

from ai_service.memory.store import (
    BaseMemoryStore,
    PostgresMemoryStore,
    SQLiteMemoryStore,
    SupabaseMemoryStore,
    get_memory_store,
)
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience, ExperienceStatus as ExpStatus


def test_postgres_memory_store_init_and_ddl():
    """Verify PostgresMemoryStore initializes tables with vector(384) and HNSW index."""
    async def _run():
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("ai_service.memory.store.HAS_POSTGRES", True):
            store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)
            await store.init_db()

            execute_calls = [call.args[0] for call in mock_conn.execute.call_args_list]
            assert any("CREATE EXTENSION IF NOT EXISTS vector" in q for q in execute_calls)
            assert any("embedding vector(384)" in q for q in execute_calls)
            assert any("hnsw" in q.lower() for q in execute_calls)

    asyncio.run(_run())


def test_postgres_memory_store_add_experience():
    """Verify add_experience writes experience with embedding vector to Postgres."""
    async def _run():
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("ai_service.memory.store.HAS_POSTGRES", True):
            store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)

            exp = Experience(
                id="exp-test-01",
                task_domain=TaskDomain.CODING,
                trigger_condition="High concurrency schema alter",
                strategy_lesson="Use non-blocking migrations",
                pitfall="Do not lock the entire table",
                confidence=0.95,
                trust_score=0.92,
                uses_count=10,
                successes_count=9,
                failures_count=1,
                status=ExpStatus.ACTIVE,
                embedding=[0.1] * 384,
            )

            res = await store.add_experience(exp)
            assert res == "exp-test-01"
            assert mock_conn.execute.called

            call_args = mock_conn.execute.call_args[0]
            query = call_args[0]
            params = call_args[1:]
            assert "INSERT INTO experiences" in query
            assert any(p == exp.id for p in params)

    asyncio.run(_run())


def test_postgres_memory_store_search_similar_pgvector():
    """Verify search_similar executes pgvector <=> cosine distance operator with threshold filter."""
    async def _run():
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        now = datetime.now(timezone.utc)
        mock_conn.fetch.return_value = [
            {
                "id": "exp-001",
                "user_id": "u1",
                "task_domain": "coding",
                "trigger_condition": "Migration locks",
                "strategy_lesson": "Split schema into non-blocking phases",
                "pitfall": "Blocking schema alters fail under traffic",
                "confidence": 0.96,
                "trust_score": 0.94,
                "uses_count": 20,
                "successes_count": 19,
                "failures_count": 1,
                "status": "active",
                "embedding": [0.1] * 384,
                "source_task_id": None,
                "created_at": now,
                "updated_at": now,
                "similarity": 0.88,
            }
        ]

        with patch("ai_service.memory.store.HAS_POSTGRES", True):
            store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool)
            matches = await store.search_similar(
                query_embedding=[0.2] * 384,
                domain=TaskDomain.CODING,
                top_k=5,
            )

            assert len(matches) == 1
            exp, sim = matches[0]
            assert exp.id == "exp-001"
            assert sim == 0.88
            assert exp.trust_score == 0.94

            fetch_call = mock_conn.fetch.call_args[0]
            sql = fetch_call[0]
            assert "<=>" in sql
            assert "status = 'active'" in sql

    asyncio.run(_run())


def test_postgres_memory_store_update_trust_f3_invariants():
    """Verify F3 counter invariants on update_trust."""
    async def _run():
        mock_conn = AsyncMock()
        mock_tx = MagicMock()
        mock_tx.__aenter__ = AsyncMock(return_value=None)
        mock_tx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=mock_tx)
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        mock_conn.fetchrow.return_value = {
            "trust_score": 0.90,
            "status": "active",
            "uses_count": 10,
            "successes_count": 9,
            "failures_count": 1,
        }

        with patch("ai_service.memory.store.HAS_POSTGRES", True):
            store = PostgresMemoryStore(database_url="postgresql://localhost:5432/testdb", pool=mock_pool, auto_seed=False)
            store._initialized = True
            rec = await store.update_trust(
                experience_id="exp-f3-01",
                new_trust=0.932,
                reason="Verified unit test success",
                execution_id="exec-123",
                binary_outcome=1,
            )

            assert rec is not None
            assert rec.experience_id == "exp-f3-01"
            assert rec.new_trust == 0.932
            assert mock_conn.execute.call_count == 2

            # Call 1: Experience counter updates (uses_count + 1, successes_count + 1, failures_count + 0)
            update_call = mock_conn.execute.call_args_list[0]
            update_sql = update_call.args[0]
            assert "UPDATE experiences SET" in update_sql
            assert "uses_count = uses_count + $3" in update_sql
            assert "successes_count = successes_count + $4" in update_sql
            assert "failures_count = failures_count + $5" in update_sql

            new_trust_arg, status_arg, uses_inc, succ_inc, fail_inc, _, exp_id_arg = update_call.args[1:]
            assert new_trust_arg == 0.932
            assert status_arg == "active"
            assert uses_inc == 1
            assert succ_inc == 1
            assert fail_inc == 0
            assert exp_id_arg == "exp-f3-01"

            # Call 2: Trust history record insertion
            history_call = mock_conn.execute.call_args_list[1]
            history_sql = history_call.args[0]
            assert "INSERT INTO trust_history" in history_sql
            _, exp_id_hist, exec_id_hist, old_trust_hist, new_trust_hist, delta_hist, reason_hist, _ = history_call.args[1:]
            assert exp_id_hist == "exp-f3-01"
            assert exec_id_hist == "exec-123"
            assert old_trust_hist == 0.90
            assert new_trust_hist == 0.932
            assert abs(delta_hist - 0.032) < 1e-4
            assert reason_hist == "Verified unit test success"

    asyncio.run(_run())


def test_supabase_memory_store_search_similar_rpc():
    """Verify SupabaseMemoryStore invokes match_experiences RPC."""
    async def _run():
        now = datetime.now(timezone.utc).isoformat()
        sample_row = {
            "id": "exp-supa-01",
            "user_id": "u1",
            "task_domain": "research",
            "trigger_condition": "Contradictory findings",
            "strategy_lesson": "Verify across independent DOIs",
            "pitfall": "Single unvetted preprints fail",
            "confidence": 0.92,
            "trust_score": 0.95,
            "uses_count": 15,
            "successes_count": 14,
            "failures_count": 1,
            "status": "active",
            "embedding": [0.05] * 384,
            "source_task_id": None,
            "created_at": now,
            "updated_at": now,
            "similarity": 0.91,
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [sample_row]

        store = SupabaseMemoryStore(url="https://test.supabase.co", anon_key="test-key")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            matches = await store.search_similar(
                query_embedding=[0.05] * 384,
                domain=TaskDomain.RESEARCH,
                top_k=3,
            )

            assert len(matches) == 1
            exp, sim = matches[0]
            assert exp.id == "exp-supa-01"
            assert sim == 0.91

    asyncio.run(_run())


def test_get_memory_store_factory():
    """Verify get_memory_store() factory handles sqlite, postgres, and supabase selections."""
    # 1. SQLite default
    store1 = get_memory_store(engine="sqlite", auto_seed=False)
    assert isinstance(store1, SQLiteMemoryStore)

    # 2. Postgres with patched availability
    with patch("ai_service.memory.store.HAS_POSTGRES", True):
        store2 = get_memory_store(engine="postgres", database_url="postgresql://localhost/test", auto_seed=False)
        assert isinstance(store2, PostgresMemoryStore)

    # 3. Supabase with URL and anon key
    store3 = get_memory_store(
        engine="supabase",
        supabase_url="https://test.supabase.co",
        supabase_key="test-anon-key",
        auto_seed=False,
    )
    assert isinstance(store3, SupabaseMemoryStore)

    # 4. Fallback to SQLite when Postgres is requested but asyncpg/pgvector is unavailable
    with patch("ai_service.memory.store.HAS_POSTGRES", False):
        store_pg_fallback = get_memory_store(engine="postgres", database_url="postgresql://localhost/test", auto_seed=False)
        assert isinstance(store_pg_fallback, SQLiteMemoryStore)

    # 5. Fallback to SQLite when Postgres is requested but no DATABASE_URL is supplied
    with patch("ai_service.memory.store.HAS_POSTGRES", True), patch("ai_service.config.settings.DATABASE_URL", None):
        store_no_url_fallback = get_memory_store(engine="postgres", database_url=None, auto_seed=False)
        assert isinstance(store_no_url_fallback, SQLiteMemoryStore)

    # 6. Fallback to SQLite when Supabase is requested but SUPABASE_URL / keys are missing
    with patch("ai_service.config.settings.SUPABASE_URL", None), patch("ai_service.config.settings.SUPABASE_ANON_KEY", None):
        store_supa_fallback = get_memory_store(engine="supabase", supabase_url=None, supabase_key=None, auto_seed=False)
        assert isinstance(store_supa_fallback, SQLiteMemoryStore)
