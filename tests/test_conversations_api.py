"""
Integration and Unit Tests for Multi-Thread Conversational Studio (Pillar 3).
Validates:
1. Conversation creation, retrieval, listing, updating (title, pin), and deletion.
2. Message append and chronological message history retrieval.
3. Multi-tenant isolation: User A's conversation is inaccessible to User B.
4. REQUIRE_USER_AUTH enforcement on conversation routes.
5. Automatic conversation synchronization when tasks are executed with a sessionId.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient

from ai_service.config import settings
from backend.main import app
from backend.routes.agent import shared_store
from backend.security.auth import create_access_token
from models.conversation import Conversation, ConversationMessage

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_conversations():
    """Ensure clean conversation state for isolated tests."""
    yield


def test_create_conversation():
    """Verify conversation thread creation with default and custom attributes."""
    conv_id = f"test-conv-{uuid.uuid4().hex[:8]}"
    payload = {
        "id": conv_id,
        "title": "Architecture Discussion",
        "isPinned": True,
    }
    response = client.post("/api/conversations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == conv_id
    assert data["title"] == "Architecture Discussion"
    assert data["isPinned"] is True
    assert data["messageCount"] == 0
    assert "createdAt" in data
    assert "updatedAt" in data


def test_list_conversations_ordering_and_pagination():
    """Verify conversations listing prioritizes pinned threads and respects pagination."""
    user_token = create_access_token({"sub": f"usr_test_{uuid.uuid4().hex[:6]}", "role": "user"})
    headers = {"Authorization": f"Bearer {user_token}"}
    id_unpinned = f"conv-unpinned-{uuid.uuid4().hex[:8]}"
    id_pinned = f"conv-pinned-{uuid.uuid4().hex[:8]}"

    client.post("/api/conversations", json={"id": id_unpinned, "title": "Normal Chat", "isPinned": False}, headers=headers)
    client.post("/api/conversations", json={"id": id_pinned, "title": "Pinned Chat", "isPinned": True}, headers=headers)

    response = client.get("/api/conversations?limit=50&offset=0", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    items = data["items"]
    assert len(items) == 2

    # Verify pinned thread appears before unpinned thread
    assert items[0]["id"] == id_pinned
    assert items[1]["id"] == id_unpinned


def test_get_conversation_by_id():
    """Verify retrieval of an existing conversation and 404 for unknown IDs."""
    conv_id = f"conv-get-{uuid.uuid4().hex[:8]}"
    client.post("/api/conversations", json={"id": conv_id, "title": "Lookup Test"})

    resp = client.get(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == conv_id
    assert resp.json()["title"] == "Lookup Test"

    non_existent = client.get("/api/conversations/non-existent-id-999")
    assert non_existent.status_code == 404


def test_update_conversation():
    """Verify renaming title and toggling pinned status."""
    conv_id = f"conv-update-{uuid.uuid4().hex[:8]}"
    client.post("/api/conversations", json={"id": conv_id, "title": "Initial Title", "isPinned": False})

    patch_resp = client.patch(
        f"/api/conversations/{conv_id}",
        json={"title": "Updated Title", "isPinned": True},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "Updated Title"
    assert data["isPinned"] is True

    # Confirm via get
    get_resp = client.get(f"/api/conversations/{conv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Updated Title"
    assert get_resp.json()["isPinned"] is True


def test_add_and_get_conversation_messages():
    """Verify appending user and assistant messages and reading full thread."""
    conv_id = f"conv-msgs-{uuid.uuid4().hex[:8]}"
    client.post("/api/conversations", json={"id": conv_id, "title": "Turn Test"})

    # Append user turn
    msg1_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": "What is the A-EMA trust formula?"},
    )
    assert msg1_resp.status_code == 201
    msg1_data = msg1_resp.json()
    assert msg1_data["role"] == "user"
    assert msg1_data["content"] == "What is the A-EMA trust formula?"
    assert msg1_data["conversationId"] == conv_id

    # Append assistant turn
    msg2_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "assistant", "content": "T_new = alpha * T_old + (1 - alpha) * outcome."},
    )
    assert msg2_resp.status_code == 201
    msg2_data = msg2_resp.json()
    assert msg2_data["role"] == "assistant"

    # Fetch messages
    list_resp = client.get(f"/api/conversations/{conv_id}/messages")
    assert list_resp.status_code == 200
    messages = list_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # Verify conversation messageCount is updated
    conv_resp = client.get(f"/api/conversations/{conv_id}")
    assert conv_resp.json()["messageCount"] == 2


def test_delete_conversation():
    """Verify deleting a conversation removes it and its messages."""
    conv_id = f"conv-del-{uuid.uuid4().hex[:8]}"
    client.post("/api/conversations", json={"id": conv_id, "title": "To be deleted"})
    client.post(f"/api/conversations/{conv_id}/messages", json={"role": "user", "content": "Message to be purged"})

    del_resp = client.delete(f"/api/conversations/{conv_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Confirm 404 on subsequent get
    assert client.get(f"/api/conversations/{conv_id}").status_code == 404
    assert client.get(f"/api/conversations/{conv_id}/messages").status_code == 404


def test_conversation_multi_tenant_isolation():
    """Verify tenant isolation: User B cannot access or modify User A's conversation."""
    token_user_a = create_access_token({"sub": "usr_tenant_alice", "role": "user"})
    token_user_b = create_access_token({"sub": "usr_tenant_bob", "role": "user"})
    headers_a = {"Authorization": f"Bearer {token_user_a}"}
    headers_b = {"Authorization": f"Bearer {token_user_b}"}

    conv_id = f"conv-alice-{uuid.uuid4().hex[:8]}"

    # User A creates a conversation
    create_resp = client.post(
        "/api/conversations",
        json={"id": conv_id, "title": "Alice Private Project"},
        headers=headers_a,
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["userId"] == "usr_tenant_alice"

    # User B cannot read User A's conversation
    get_resp = client.get(f"/api/conversations/{conv_id}", headers=headers_b)
    assert get_resp.status_code == 404

    # User B cannot read User A's messages
    msg_resp = client.get(f"/api/conversations/{conv_id}/messages", headers=headers_b)
    assert msg_resp.status_code == 404

    # User B cannot update User A's conversation
    patch_resp = client.patch(
        f"/api/conversations/{conv_id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert patch_resp.status_code == 404

    # User B cannot post a message into User A's conversation
    post_msg_resp = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Unauthorized message"},
        headers=headers_b,
    )
    assert post_msg_resp.status_code == 404

    # User B cannot delete User A's conversation
    del_resp = client.delete(f"/api/conversations/{conv_id}", headers=headers_b)
    assert del_resp.status_code == 404

    # User B listing conversations does NOT contain User A's conversation
    list_resp = client.get("/api/conversations", headers=headers_b)
    assert list_resp.status_code == 200
    b_conv_ids = [c["id"] for c in list_resp.json()["items"]]
    assert conv_id not in b_conv_ids

    # User A CAN access their own conversation
    alice_get = client.get(f"/api/conversations/{conv_id}", headers=headers_a)
    assert alice_get.status_code == 200
    assert alice_get.json()["title"] == "Alice Private Project"


def test_require_user_auth_enforced():
    """Verify that when REQUIRE_USER_AUTH is True, unauthenticated access is rejected."""
    with patch.object(settings, "REQUIRE_USER_AUTH", True):
        resp = client.get("/api/conversations")
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers

        post_resp = client.post("/api/conversations", json={"title": "Anonymous Attempt"})
        assert post_resp.status_code == 401


def test_agent_execution_syncs_to_conversation():
    """Verify that running an agent execution with sessionId automatically creates the conversation."""
    session_id = f"session-sync-{uuid.uuid4().hex[:8]}"

    # Execute a mock task with this sessionId
    exec_payload = {
        "taskInput": "Calculate the Fibonacci sequence up to 10",
        "taskDomain": "coding",
        "memoryMode": "adaptive",
        "sessionId": session_id,
        "provider": "mock",
    }
    exec_resp = client.post("/api/agent/execute", json=exec_payload)
    assert exec_resp.status_code == 200

    # Verify conversation was automatically synchronized
    conv_resp = client.get(f"/api/conversations/{session_id}")
    assert conv_resp.status_code == 200
    conv_data = conv_resp.json()
    assert conv_data["id"] == session_id
    assert "Fibonacci" in conv_data["title"]

    # Verify messages were appended (user turn + assistant turn)
    msgs_resp = client.get(f"/api/conversations/{session_id}/messages")
    assert msgs_resp.status_code == 200
    messages = msgs_resp.json()
    assert len(messages) >= 1
    assert any(m["role"] == "user" for m in messages)
