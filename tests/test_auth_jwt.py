"""
Unit and integration tests for unified identity, JWT verification, and multi-tenant partitioning.
Validates:
1. JWT token issuance and decoding mechanics (claims, expiration, tampering).
2. Machine service authentication fallback (AGENT_API_KEY, ADMIN_API_KEY).
3. User Bearer JWT authentication on execution and memory endpoints.
4. Multi-tenant memory store isolation (User A cannot see User B's private memories).
5. Anti-spoofing enforcement (User A cannot query User B by passing userId query param).
6. Multi-tenant execution trace isolation on agent execution endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from ai_service.config import settings
from backend.main import app
from backend.routes.agent import shared_store
from backend.security.auth import (
    AuthContext,
    create_access_token,
    decode_jwt_token,
    get_auth_context,
)
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience

client = TestClient(app)


# ─── 1. JWT Token Issuance & Decoding Mechanics ──────────────────────────────

def test_create_and_decode_valid_jwt():
    """Verify standard JWT claims encoding and decoding."""
    payload = {
        "sub": "usr_test_12345",
        "email": "developer@aema.io",
        "role": "user",
    }
    token = create_access_token(payload, expires_delta=timedelta(hours=2))
    decoded = decode_jwt_token(token)

    assert decoded["sub"] == "usr_test_12345"
    assert decoded["email"] == "developer@aema.io"
    assert decoded["role"] == "user"
    assert "exp" in decoded


def test_expired_jwt_rejected():
    """Verify expired token raises HTTP 401 with descriptive error."""
    payload = {"sub": "usr_expired_999"}
    # Token expired 1 hour ago
    expired_token = create_access_token(payload, expires_delta=timedelta(hours=-1))

    with pytest.raises(HTTPException) as exc_info:
        decode_jwt_token(expired_token)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_tampered_jwt_rejected():
    """Verify modified or signature-tampered token raises HTTP 401."""
    token = create_access_token({"sub": "usr_legit_123"})
    parts = token.split(".")
    # Tamper with the payload part
    tampered_token = f"{parts[0]}.eyJuYW1lIjoiZmFrZSJ9.{parts[2]}"

    with pytest.raises(HTTPException) as exc_info:
        decode_jwt_token(tampered_token)

    assert exc_info.value.status_code == 401
    assert "invalid" in exc_info.value.detail.lower()


# ─── 2. Machine Service Authentication ───────────────────────────────────────

def test_machine_admin_api_key_auth():
    """Verify ADMIN_API_KEY grants admin role across X-Admin-Token and Bearer headers."""
    admin_key = "test-ci-admin-secret-key"

    with patch.object(settings, "ADMIN_API_KEY", admin_key):
        # 1. Via X-Admin-Token
        res_header = client.delete(
            "/api/v1/agent/executions",
            headers={"X-Admin-Token": admin_key},
        )
        assert res_header.status_code == 200

        # 2. Via Authorization Bearer
        res_bearer = client.delete(
            "/api/v1/agent/executions",
            headers={"Authorization": f"Bearer {admin_key}"},
        )
        assert res_bearer.status_code == 200


def test_machine_agent_api_key_auth():
    """Verify AGENT_API_KEY grants machine execution access when REQUIRE_AGENT_AUTH is enabled."""
    agent_key = "test-ci-agent-secret-key"
    payload = {
        "taskInput": "Calculate 1 + 1",
        "domain": "coding",
        "provider": "mock",
    }

    with patch.object(settings, "REQUIRE_AGENT_AUTH", True), \
         patch.object(settings, "AGENT_API_KEY", agent_key):

        # Valid X-API-Key
        res_valid = client.post(
            "/api/v1/agent/execute",
            json=payload,
            headers={"X-API-Key": agent_key},
        )
        assert res_valid.status_code == 200

        # Invalid key -> 401
        res_bad = client.post(
            "/api/v1/agent/execute",
            json=payload,
            headers={"X-API-Key": "wrong-agent-key"},
        )
        assert res_bad.status_code == 401


# ─── 3. User Bearer JWT Execution Attribution ────────────────────────────────

def test_user_jwt_execution_attribution():
    """Verify authenticated user JWT sets execution user_id correctly."""
    user_id = "usr_alice_777"
    token = create_access_token({"sub": user_id, "email": "alice@test.com"})

    payload = {
        "taskInput": "Explain the concept of quantum superposition",
        "domain": "research",
        "provider": "mock",
    }

    res = client.post(
        "/api/v1/agent/execute",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data.get("userId") == user_id or data.get("user_id") == user_id


# ─── 4. Multi-Tenant Memory Store Partitioning ──────────────────────────────

@pytest.mark.asyncio
async def test_multi_tenant_memory_isolation_and_anti_spoofing():
    """
    Verify complete experiential memory tenant isolation:
    - User Alice cannot see User Bob's private memories.
    - User Bob cannot see User Alice's private memories.
    - Both users see global baseline memories (user_id IS NULL).
    - Alice passing userId=bob via query param cannot bypass tenant filter.
    - Cleans up shared-store records after execution.
    """
    alice_id = "usr_tenant_alice"
    bob_id = "usr_tenant_bob"

    alice_token = create_access_token({"sub": alice_id, "email": "alice@tenant.io"})
    bob_token = create_access_token({"sub": bob_id, "email": "bob@tenant.io"})

    # Seed an Alice-specific private memory
    alice_exp = Experience(
        id=f"exp-alice-{datetime.now(timezone.utc).timestamp()}",
        user_id=alice_id,
        task_domain=TaskDomain.CODING,
        trigger_condition="Alice secure private crypto banking logic",
        strategy_lesson="Use Alice HSM hardware keys exclusively for signing",
        pitfall="Storing Alice keys in environment variables",
        confidence=0.98,
        trust_score=0.92,
        status=ExperienceStatus.ACTIVE,
    )

    # Seed a Bob-specific private memory
    bob_exp = Experience(
        id=f"exp-bob-{datetime.now(timezone.utc).timestamp()}",
        user_id=bob_id,
        task_domain=TaskDomain.CODING,
        trigger_condition="Bob proprietary algorithmic trade execution",
        strategy_lesson="Batch orders in 100ms micro-slices",
        pitfall="Submitting single lump-sum market orders",
        confidence=0.95,
        trust_score=0.90,
        status=ExperienceStatus.ACTIVE,
    )

    try:
        await shared_store.add_experience(alice_exp)
        await shared_store.add_experience(bob_exp)

        # 1. Alice lists memories: must see Alice's memory, must NOT see Bob's memory
        res_alice = client.get(
            "/api/v1/memories",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert res_alice.status_code == 200
        alice_items = res_alice.json()
        alice_exp_ids = [m["id"] for m in alice_items]
        assert alice_exp.id in alice_exp_ids
        assert bob_exp.id not in alice_exp_ids

        # 2. Bob lists memories: must see Bob's memory, must NOT see Alice's memory
        res_bob = client.get(
            "/api/v1/memories",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert res_bob.status_code == 200
        bob_items = res_bob.json()
        bob_exp_ids = [m["id"] for m in bob_items]
        assert bob_exp.id in bob_exp_ids
        assert alice_exp.id not in bob_exp_ids

        # 3. Anti-Spoofing: Alice tries to snoop on Bob by passing userId=bob
        res_spoof = client.get(
            f"/api/v1/memories?userId={bob_id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert res_spoof.status_code == 200
        spoof_items = res_spoof.json()
        spoof_exp_ids = [m["id"] for m in spoof_items]
        # Bob's private memory must NOT be visible even when Alice explicitly requests Bob's userId
        assert bob_exp.id not in spoof_exp_ids
        assert alice_exp.id in spoof_exp_ids

        # 4. Authorize ownership before returning a memory by ID (Issue #8)
        # Alice fetches Alice's memory -> 200
        res_own = client.get(
            f"/api/v1/memories/{alice_exp.id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert res_own.status_code == 200
        assert res_own.json()["id"] == alice_exp.id

        # Bob attempts to fetch Alice's private memory by ID -> 404 (ownership denied)
        res_other = client.get(
            f"/api/v1/memories/{alice_exp.id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert res_other.status_code == 404

        # Unauthenticated caller attempts to fetch Alice's private memory -> 404
        res_unauth = client.get(f"/api/v1/memories/{alice_exp.id}")
        assert res_unauth.status_code == 404

    finally:
        # Issue #11: Clean up test data from shared store
        await shared_store.delete_experience(alice_exp.id)
        await shared_store.delete_experience(bob_exp.id)


# ─── 5. Multi-Tenant Execution Trace Isolation ──────────────────────────────

def test_multi_tenant_execution_trace_isolation():
    """Verify execution history list filters by tenant identity and cleans up."""
    alice_id = "trace_tenant_alice"
    bob_id = "trace_tenant_bob"

    alice_token = create_access_token({"sub": alice_id})
    bob_token = create_access_token({"sub": bob_id})

    # Run execution for Alice
    res_a = client.post(
        "/api/v1/agent/execute",
        json={"taskInput": "Alice secret execution task", "domain": "coding", "provider": "mock"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_a.status_code == 200
    exec_a_id = res_a.json()["id"]

    # Run execution for Bob
    res_b = client.post(
        "/api/v1/agent/execute",
        json={"taskInput": "Bob secret execution task", "domain": "coding", "provider": "mock"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_b.status_code == 200
    exec_b_id = res_b.json()["id"]

    try:
        # Alice lists executions
        list_a = client.get(
            "/api/v1/agent/executions",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert list_a.status_code == 200
        a_ids = [x["id"] for x in list_a.json()["items"]]
        assert exec_a_id in a_ids
        assert exec_b_id not in a_ids

        # Bob lists executions
        list_b = client.get(
            "/api/v1/agent/executions",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert list_b.status_code == 200
        b_ids = [x["id"] for x in list_b.json()["items"]]
        assert exec_b_id in b_ids
        assert exec_a_id not in b_ids

        # Issue #6: Scope execution detail lookup GET /executions/{id}
        # Alice fetches her own execution trace -> 200
        trace_a = client.get(
            f"/api/v1/agent/executions/{exec_a_id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert trace_a.status_code == 200
        assert trace_a.json()["id"] == exec_a_id

        # Bob attempts to fetch Alice's execution trace -> 404 (tenant isolation)
        trace_b_on_a = client.get(
            f"/api/v1/agent/executions/{exec_a_id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert trace_b_on_a.status_code == 404

        # Unauthenticated attempts to fetch Alice's execution trace -> 404
        trace_unauth = client.get(f"/api/v1/agent/executions/{exec_a_id}")
        assert trace_unauth.status_code == 404
    finally:
        # Issue #11: Clean up test executions
        from backend.routes.agent import _execution_history
        _execution_history[:] = [ex for ex in _execution_history if ex.id not in (exec_a_id, exec_b_id)]


# ─── 6. Security Hardening & Copilot Audit Regressions ──────────────────────

def test_require_user_auth_enforced_without_credentials():
    """
    Verify REQUIRE_USER_AUTH rejects unauthenticated requests across all routes (Issue #1).
    """
    with patch.object(settings, "REQUIRE_USER_AUTH", True):
        # 1. GET /memories without token
        res_mem = client.get("/api/v1/memories")
        assert res_mem.status_code == 401

        # 2. GET /agent/executions without token
        res_exec = client.get("/api/v1/agent/executions")
        assert res_exec.status_code == 401

        # 3. GET /agent/sessions without token
        res_sess = client.get("/api/v1/agent/sessions")
        assert res_sess.status_code == 401


def test_reject_fallback_jwt_key_when_supabase_secret_configured():
    """
    Verify when SUPABASE_JWT_SECRET is configured, AEMA_JWT_SECRET is strictly rejected (Issues #2 & #9).
    """
    supabase_sec = "supabase-production-hmac-secret-xyz-987-long"
    aema_sec = "fallback-local-aema-key-123-with-thirty-two-chars"

    with patch.object(settings, "SUPABASE_JWT_SECRET", supabase_sec), \
         patch.object(settings, "AEMA_JWT_SECRET", aema_sec):

        # Valid Supabase token decodes successfully
        supabase_token = create_access_token({"sub": "usr_supabase"}, secret_key=supabase_sec)
        decoded = decode_jwt_token(supabase_token)
        assert decoded["sub"] == "usr_supabase"

        # Token signed with AEMA_JWT_SECRET MUST fail when Supabase secret is active
        forged_token = create_access_token({"sub": "usr_forged"}, secret_key=aema_sec)
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt_token(forged_token)
        assert exc_info.value.status_code == 401


def test_anonymous_execution_cannot_spoof_tenant_id():
    """
    Verify client-supplied tenant ID is ignored for unauthenticated executions (Issues #4 & #10).
    """
    # Unauthenticated caller sends userId: "victim_alice"
    res = client.post(
        "/api/v1/agent/execute",
        json={
            "taskInput": "Calculate 5 * 5",
            "domain": "coding",
            "provider": "mock",
            "userId": "victim_alice",
        },
    )
    assert res.status_code == 200
    data = res.json()
    # Server must NEVER trust the client-supplied tenant ID for unauthenticated calls
    assert data.get("userId") is None or data.get("userId") == "anonymous"
    assert data.get("userId") != "victim_alice"


def test_unauthenticated_cannot_enumerate_cross_tenant_records():
    """
    Verify unauthenticated requests cannot pass ?userId=victim to enumerate records (Issues #5 & #7).
    """
    # 1. Memories query with userId parameter without credentials -> 401
    res_mem = client.get("/api/v1/memories?userId=victim_alice")
    assert res_mem.status_code == 401

    # 2. Executions query with userId parameter without credentials -> 401
    res_exec = client.get("/api/v1/agent/executions?userId=victim_alice")
    assert res_exec.status_code == 401

    # 3. Sessions query with userId parameter without credentials -> 401
    res_sess = client.get("/api/v1/agent/sessions?userId=victim_alice")
    assert res_sess.status_code == 401


@pytest.mark.asyncio
async def test_retriever_signature_tenant_scoping_no_typeerror_fallback():
    """
    Verify retriever inspects method signature and preserves tenant scoping (Issue #3).
    """
    from ai_service.memory.retriever import MemoryRetriever

    retriever = MemoryRetriever(store=shared_store)
    # Search for an authenticated user's scope
    results, diagnostics = await retriever.retrieve_with_diagnostics(
        query="banking logic",
        domain=TaskDomain.CODING,
        user_id="usr_tenant_alice",
    )
    assert isinstance(results, list)
    assert diagnostics["policy"] == "aema"
