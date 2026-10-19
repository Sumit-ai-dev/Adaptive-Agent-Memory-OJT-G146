"""
Unit and Integration Tests for Multi-Turn Conversational Execution Studio.
Verifies:
- ChatMessage and TaskExecuteRequest Pydantic validation (roles, bounds, context limit clipping)
- execute_node message assembly (system prompt, history preservation, deduplication)
- End-to-end multi-turn execution via FastAPI (/api/v1/agent/execute)
- Session isolation and session-scoped execution history filtering
- Backward compatibility with legacy single-turn requests
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import app
from models.task import ChatMessage, TaskExecuteRequest, TaskExecution
from ai_service.nodes.execute_node import execute_node

client = TestClient(app)


def test_chat_message_role_validation():
    """Verify ChatMessage accepts valid roles and rejects invalid roles."""
    msg_user = ChatMessage(role="user", content="Hello agent")
    assert msg_user.role == "user"

    msg_asst = ChatMessage(role="ASSISTANT", content="Hello user")
    assert msg_asst.role == "assistant"

    msg_sys = ChatMessage(role="system", content="System instruction")
    assert msg_sys.role == "system"

    with pytest.raises(ValidationError):
        ChatMessage(role="invalid_role", content="test")

    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="")


def test_task_execute_request_session_and_messages_validation():
    """Verify session_id and messages validation on TaskExecuteRequest."""
    # Valid session ID
    req = TaskExecuteRequest(
        taskInput="Explain photosynthesis",
        sessionId="session_abc-123.test",
        messages=[
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello! How can I help?"),
        ],
    )
    assert req.session_id == "session_abc-123.test"
    assert len(req.messages) == 2

    # Context clipping: passing > 50 messages clips to the latest 50
    overflow_messages = [ChatMessage(role="user", content=f"msg {i}") for i in range(65)]
    req_clipped = TaskExecuteRequest(
        taskInput="Latest question",
        messages=overflow_messages,
    )
    assert len(req_clipped.messages) == 50
    assert req_clipped.messages[-1].content == "msg 64"

    # Invalid session ID with disallowed characters
    with pytest.raises(ValidationError):
        TaskExecuteRequest(
            taskInput="Test",
            sessionId="invalid session with spaces!",
        )


@pytest.mark.asyncio
async def test_execute_node_conversation_history_assembly():
    """Verify execute_node preserves conversation history order and avoids duplicate user turn."""
    state = {
        "task_input": "What is its main advantage?",
        "task_domain": "general",
        "provider": "mock",
        "positive_strategy": "Be concise.",
        "negative_pitfall": "Do not hallucinate.",
        "messages": [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level programming language."},
        ],
        "loop_count": 0,
        "tokens_used": 0,
    }

    result = await execute_node(state)

    assert "final_answer" in result
    assert "messages" in result
    msgs = result["messages"]

    # 1. System prompt at index 0 with bilateral constraints
    assert msgs[0]["role"] == "system"
    assert "Be concise" in msgs[0]["content"]

    # 2. Historical messages in order
    assert msgs[1] == {"role": "user", "content": "What is Python?"}
    assert msgs[2] == {"role": "assistant", "content": "Python is a high-level programming language."}

    # 3. Current user turn
    assert msgs[3] == {"role": "user", "content": "What is its main advantage?"}

    # 4. Final assistant answer
    assert msgs[4]["role"] == "assistant"
    assert msgs[4]["content"] == result["final_answer"]


@pytest.mark.asyncio
async def test_execute_node_avoids_duplicate_current_user_turn():
    """Verify execute_node does not duplicate user message if client already included it in history."""
    state = {
        "task_input": "Show me a code snippet",
        "task_domain": "coding",
        "provider": "mock",
        "messages": [
            {"role": "user", "content": "Explain async await"},
            {"role": "assistant", "content": "Async await allows non-blocking concurrency."},
            {"role": "user", "content": "Show me a code snippet"},  # Pre-populated
        ],
        "loop_count": 0,
        "tokens_used": 0,
    }

    result = await execute_node(state)
    msgs = result["messages"]

    user_messages = [m for m in msgs if m["role"] == "user"]
    assert len(user_messages) == 2
    assert user_messages[0]["content"] == "Explain async await"
    assert user_messages[1]["content"] == "Show me a code snippet"


def test_api_multiturn_continuity_and_session_persistence():
    """Verify end-to-end multi-turn execution and session filtering via REST API."""
    session_id = "test_sess_conv_999"

    # Turn 1
    t1_payload = {
        "sessionId": session_id,
        "taskInput": "What is the capital of France?",
        "provider": "mock",
    }
    res1 = client.post("/api/v1/agent/execute", json=t1_payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["sessionId"] == session_id
    ans1 = data1["finalAnswer"]
    assert len(ans1) > 0

    # Turn 2: send turn 1 history
    t2_payload = {
        "sessionId": session_id,
        "taskInput": "What is its primary landmark?",
        "provider": "mock",
        "messages": [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": ans1},
        ],
    }
    res2 = client.post("/api/v1/agent/execute", json=t2_payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["sessionId"] == session_id

    # Query executions filtered by session_id
    list_res = client.get(f"/api/v1/agent/executions?sessionId={session_id}")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 2
    for item in list_data["items"]:
        assert item.get("sessionId") == session_id


def test_api_session_isolation():
    """Verify sessions do not leak executions across each other."""
    sess_a = "test_sess_isolated_A"
    sess_b = "test_sess_isolated_B"

    client.post("/api/v1/agent/execute", json={"sessionId": sess_a, "taskInput": "Task in A", "provider": "mock"})
    client.post("/api/v1/agent/execute", json={"sessionId": sess_b, "taskInput": "Task in B", "provider": "mock"})

    res_a = client.get(f"/api/v1/agent/executions?sessionId={sess_a}").json()
    res_b = client.get(f"/api/v1/agent/executions?sessionId={sess_b}").json()

    # All items in query for A must have sessionId == sess_a
    for item in res_a["items"]:
        assert item["sessionId"] == sess_a

    # All items in query for B must have sessionId == sess_b
    for item in res_b["items"]:
        assert item["sessionId"] == sess_b


def test_singleturn_backward_compatibility():
    """Verify legacy single-turn requests without sessionId or messages continue to work seamlessly."""
    legacy_payload = {
        "taskInput": "Compute 2 + 2",
        "domain": "general",
        "provider": "mock",
    }
    res = client.post("/api/v1/agent/execute", json=legacy_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data.get("sessionId") is None
    assert len(data["trajectory"]) >= 5


def test_api_list_sessions_endpoint():
    """Verify GET /api/agent/sessions returns distinct recent sessions."""
    sess_id = "test_sess_listing_xyz"
    client.post("/api/v1/agent/execute", json={"sessionId": sess_id, "taskInput": "Initial topic question", "provider": "mock"})
    client.post("/api/v1/agent/execute", json={"sessionId": sess_id, "taskInput": "Follow-up topic question", "provider": "mock"})

    sessions_res = client.get("/api/v1/agent/sessions")
    assert sessions_res.status_code == 200
    sessions = sessions_res.json()
    assert isinstance(sessions, list)
    matching = [s for s in sessions if s["sessionId"] == sess_id]
    assert len(matching) == 1
    assert matching[0]["turnCount"] >= 2
    assert "Initial" in matching[0]["title"] or "Follow-up" in matching[0]["title"]

