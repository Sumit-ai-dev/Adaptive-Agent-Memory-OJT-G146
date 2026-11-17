import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator

from ai_service.llm_client import UniversalLLMClient, ProviderConfig
from ai_service.memory.store import SQLiteMemoryStore, BaseMemoryStore
from models.task import (
    TaskExecuteRequest,
    TaskExecution,
)
from models.domain import (
    TaskDomain,
    MemoryMode,
    ExecutionStatus,
)


@pytest.mark.asyncio
async def test_llm_client_generate_stream():
    """Verify UniversalLLMClient.generate_stream emits chunks as an async generator."""
    client = UniversalLLMClient()
    config = ProviderConfig(provider="mock", model="mock-model", api_key="mock-key")
    messages = [{"role": "user", "content": "Write a python function to compute fibonacci"}]

    chunks = []
    async for chunk in client.generate_stream(messages, config=config):
        chunks.append(chunk)

    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert len(full_text) > 0


@pytest.mark.asyncio
async def test_execute_task_stream_realtime_events():
    """Verify execute_task_stream yields real-time token events and node completions."""
    from ai_service.graph import execute_task_stream

    request = TaskExecuteRequest(
        task_input="Compute the depth of a binary tree safely",
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        provider="mock",
        user_id="test-stream-user",
    )

    events_received = []
    tokens_received = []

    async for sse_event in execute_task_stream(request):
        lines = sse_event.strip().split("\n")
        event_name = None
        data_payload = None
        for line in lines:
            if line.startswith("event: "):
                event_name = line[7:].strip()
            elif line.startswith("data: "):
                data_payload = json.loads(line[6:].strip())

        if event_name:
            events_received.append(event_name)
        if event_name == "token" and data_payload:
            tokens_received.append(data_payload.get("chunk", ""))

    assert "start" in events_received
    assert "node_complete" in events_received
    assert "token" in events_received
    assert len(tokens_received) > 0
    assert "done" in events_received


@pytest.mark.asyncio
async def test_sqlite_execution_persistence(tmp_path):
    """Verify SQLiteMemoryStore saves, retrieves, lists, and filters task executions."""
    db_file = str(tmp_path / "test_exec.db")
    store = SQLiteMemoryStore(db_path=db_file, auto_seed=False)

    exec1 = TaskExecution(
        id="exec-001",
        execution_id="exec-001",
        task_id="task-001",
        session_id="session-alpha",
        user_id="user-123",
        task_input="Test task input 1",
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        status=ExecutionStatus.COMPLETED,
        outcome_score=0.95,
        latency_ms=120,
        tokens_used=150,
        created_at=datetime.now(timezone.utc),
    )

    exec2 = TaskExecution(
        id="exec-002",
        execution_id="exec-002",
        task_id="task-002",
        session_id="session-alpha",
        user_id="user-456",
        task_input="Test task input 2",
        task_domain=TaskDomain.RESEARCH,
        memory_mode=MemoryMode.NAIVE,
        memory_enabled=True,
        status=ExecutionStatus.COMPLETED,
        outcome_score=0.75,
        latency_ms=80,
        tokens_used=90,
        created_at=datetime.now(timezone.utc),
    )

    await store.save_execution(exec1)
    await store.save_execution(exec2)

    # 1. Fetch by ID
    loaded = await store.get_execution("exec-001")
    assert loaded is not None
    assert loaded.id == "exec-001"
    assert loaded.user_id == "user-123"

    # 2. Filter by user_id
    total, items = await store.list_executions(user_id="user-123")
    assert total == 1
    assert items[0].id == "exec-001"

    # 3. Filter by domain
    total, items = await store.list_executions(domain="research")
    assert total == 1
    assert items[0].id == "exec-002"

    # 4. List sessions
    sessions = await store.list_sessions(user_id="user-123")
    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "session-alpha"

    # 5. Clear executions
    cleared_count = await store.clear_executions()
    assert cleared_count == 2
    total_after, _ = await store.list_executions()
    assert total_after == 0


@pytest.mark.asyncio
async def test_sqlite_session_aggregation_multi_turn(tmp_path):
    """Verify that multiple turns under the same session are grouped into 1 session item with turn count and first title."""
    db_file = str(tmp_path / "test_session_agg.db")
    store = SQLiteMemoryStore(db_path=db_file, auto_seed=False)

    # 3 turns in session-multi
    for i, prompt in enumerate(["First prompt: binary search", "Second prompt: write unit tests", "Third prompt: optimize memory"]):
        ex = TaskExecution(
            id=f"exec-agg-{i}",
            execution_id=f"exec-agg-{i}",
            task_id=f"task-agg-{i}",
            session_id="session-multi",
            user_id="user-dev",
            task_input=prompt,
            task_domain=TaskDomain.CODING,
            memory_mode=MemoryMode.ADAPTIVE,
            memory_enabled=True,
            status=ExecutionStatus.COMPLETED,
            outcome_score=0.9,
            latency_ms=100,
            tokens_used=120,
            created_at=datetime.now(timezone.utc),
        )
        await store.save_execution(ex)

    sessions = await store.list_sessions(user_id="user-dev")
    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "session-multi"
    assert sessions[0]["turnCount"] == 3
    assert "First prompt" in sessions[0]["title"]


@pytest.mark.asyncio
async def test_streaming_missing_api_key_raises():
    """Verify that generate_stream raises ProviderConfigurationError when unconfigured provider has no API key."""
    from ai_service.llm_client import ProviderConfigurationError
    from models.provider import ModelProvider

    client = UniversalLLMClient()
    config = ProviderConfig(provider=ModelProvider.OPENAI, model="gpt-4o", api_key="")

    with pytest.raises(ProviderConfigurationError):
        async for _ in client.generate_stream(
            messages=[{"role": "user", "content": "Hello"}],
            config=config,
        ):
            pass


@pytest.mark.asyncio
async def test_gemini_native_stream_live():
    """Verify that _generate_gemini_native_stream parses SSE lines and yields chunks."""
    from unittest.mock import patch, AsyncMock
    from models.provider import ModelProvider

    client = UniversalLLMClient()
    config = ProviderConfig(provider=ModelProvider.GEMINI, model="gemini-2.5-flash", api_key="dummy-gemini-key")

    sse_lines = [
        'data: {"candidates": [{"content": {"parts": [{"text": "Hello "}]}}]}',
        'data: {"candidates": [{"content": {"parts": [{"text": "world!"}]}}]}',
    ]

    class MockStreamResponse:
        status_code = 200

        async def aiter_lines(self):
            for line in sse_lines:
                yield line

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockHttpClient:
        def stream(self, *args, **kwargs):
            return MockStreamResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockHttpClient()):
        chunks = []
        async for chunk in client._generate_gemini_native_stream(
            messages=[{"role": "user", "content": "Hi"}],
            cfg=config,
        ):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world!"]


@pytest.mark.asyncio
async def test_store_failure_propagation_and_fallback():
    """Verify that execution persistence errors propagate and trigger SQLite fallback."""
    from unittest.mock import AsyncMock, patch
    from backend.routes.agent import _save_execution_to_store, shared_store

    test_exec = TaskExecution(
        id="exec-err-001",
        execution_id="exec-err-001",
        task_id="task-err-001",
        session_id="session-err",
        user_id="user-test",
        task_input="Testing fallback",
        task_domain=TaskDomain.CODING,
        memory_mode=MemoryMode.ADAPTIVE,
        memory_enabled=True,
        status=ExecutionStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )

    with patch.object(shared_store, "save_execution", new=AsyncMock(side_effect=RuntimeError("DB Connection Lost"))):
        with patch("backend.routes.agent._save_execution_to_db") as mock_db_fallback:
            await _save_execution_to_store(test_exec)
            mock_db_fallback.assert_called_once_with(test_exec)


@pytest.mark.asyncio
async def test_postgres_memory_store_execution_persistence():
    """Verify PostgresMemoryStore save, get, list, and clear execution methods with mock pool."""
    from unittest.mock import AsyncMock, MagicMock
    from ai_service.memory.store import PostgresMemoryStore

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    payload_data = {
        "id": "pg-exec-001",
        "execution_id": "pg-exec-001",
        "task_id": "pg-task-001",
        "session_id": "pg-session-1",
        "user_id": "pg-user",
        "task_input": "pg test input",
        "task_domain": "coding",
        "memory_mode": "adaptive",
        "memory_enabled": True,
        "status": "completed",
        "created_at": "2026-11-17T12:00:00Z",
    }

    mock_conn.fetchrow = AsyncMock(return_value={"payload_json": json.dumps(payload_data)})
    mock_conn.fetch = AsyncMock(return_value=[
        {"payload_json": json.dumps(payload_data)},
    ])

    class MockPoolContext:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockPoolContext()

    store = PostgresMemoryStore(database_url="postgresql://user:pass@localhost:5432/db", pool=mock_pool)
    store._initialized = True

    exec_obj = TaskExecution.model_validate(payload_data)

    # 1. save_execution
    await store.save_execution(exec_obj)
    assert mock_conn.execute.called

    # 2. get_execution
    fetched = await store.get_execution("pg-exec-001")
    assert fetched is not None
    assert fetched.id == "pg-exec-001"

    # 3. list_executions
    total, items = await store.list_executions(user_id="pg-user")
    assert total == 1
    assert len(items) == 1
    assert items[0].id == "pg-exec-001"

    # 4. list_sessions
    mock_conn.fetch = AsyncMock(return_value=[
        {"session_id": "pg-session-1", "title": "pg test input", "last_active": "2026-11-17T12:00:00Z", "turn_count": 2}
    ])
    sessions = await store.list_sessions(user_id="pg-user")
    assert len(sessions) == 1
    assert sessions[0]["sessionId"] == "pg-session-1"
    assert sessions[0]["turnCount"] == 2

    # 5. clear_executions
    cleared = await store.clear_executions()
    assert cleared == 1

