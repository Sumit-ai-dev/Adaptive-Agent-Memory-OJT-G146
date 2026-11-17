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
