"""
Tests for the plug-and-play `AdaptiveMemory` Python SDK, user_id scoping,
lifecycle management (forget/recover/export), unified path resolution, and pure-Python betainc.
"""

import json
import pytest
import scipy.special as sc

from aema import AdaptiveMemory
from aema._compat import resolve_db_path
from ai_service.trust_math import _betainc_pure


@pytest.mark.parametrize(
    "a,b,x",
    [
        (3.0, 1.0, 0.70),
        (3.0, 4.0, 0.70),
        (3.0, 5.0, 0.70),
        (10.0, 2.0, 0.85),
        (2.5, 6.5, 0.35),
        (1.0, 1.0, 0.50),
    ],
)
def test_pure_python_betainc_matches_scipy(a: float, b: float, x: float):
    assert abs(_betainc_pure(a, b, x) - float(sc.betainc(a, b, x))) < 1e-11


def test_adaptive_memory_sdk_lifecycle_and_quarantine(tmp_path):
    db_file = str(tmp_path / "voice_agent.db")
    mem = AdaptiveMemory(db_path=db_file)

    item = mem.remember(
        task="Voice TTS markdown formatting rule",
        strategy="Strip asterisks and backticks before sending text to TTS synthesizer.",
        pitfall="Do not speak raw markdown symbols aloud.",
        domain="general",
    )
    assert item["status"] == "active"
    assert item["trust"] == 0.75

    hits = mem.recall("Format reply for voice TTS model", min_similarity=0.05)
    assert len(hits) == 1
    assert hits[0]["id"] == item["id"]

    prompt_ctx = mem.format_for_prompt("Format reply for voice TTS model")
    assert "Strip asterisks" in prompt_ctx

    # 3 consecutive failures trigger Theorem 1 deterministic quarantine (0.75 -> 0.525 -> 0.3675 -> 0.2572 < 0.35)
    r1 = mem.feedback(item["id"], success=False)
    r2 = mem.feedback(item["id"], success=False)
    r3 = mem.feedback(item["id"], success=False)
    assert r1["quarantined"] is False
    assert r2["quarantined"] is False
    assert r3["quarantined"] is True
    assert r3["new_trust"] < 0.35
    assert r3["status"] == "deprecated"

    # Quarantined experience is automatically excluded from recall
    post_hits = mem.recall("Format reply for voice TTS model", min_similarity=0.05)
    assert post_hits == []

    # Recover into candidate probation per AEMA state-machine invariant
    rec = mem.recover(item["id"], reason="Verified updated TTS rule")
    assert rec["status"] == "candidate"
    assert mem.recall("Format reply for voice TTS model", min_similarity=0.05) == []

    # Soft forget / quarantine, then hard_delete permanently erases (GDPR/PII compliance)
    assert mem.forget(item["id"], hard_delete=False) is True
    assert mem.status()["quarantined"] == 1
    assert mem.forget(item["id"], hard_delete=True) is True
    assert mem.status()["total"] == 0


def test_adaptive_memory_multi_user_isolation_and_export(tmp_path):
    db_file = str(tmp_path / "multi_user.db")
    alice = AdaptiveMemory(db_path=db_file, user_id="user_alice")
    bob = AdaptiveMemory(db_path=db_file, user_id="user_bob")

    alice.remember(
        task="Alice banking PIN voice rule",
        strategy="Never read Alice account numbers aloud.",
        domain="general",
    )
    bob.remember(
        task="Bob preferred speed",
        strategy="Speak at 1.2x speed for Bob.",
        domain="general",
    )

    alice_hits = alice.recall("voice rule account speed", min_similarity=0.0)
    bob_hits = bob.recall("voice rule account speed", min_similarity=0.0)

    assert len(alice_hits) == 1
    assert alice_hits[0]["user_id"] == "user_alice"
    assert len(bob_hits) == 1
    assert bob_hits[0]["user_id"] == "user_bob"

    export_file = tmp_path / "alice_backup.json"
    count = alice.export_json(str(export_file))
    assert count == 1
    exported = json.loads(export_file.read_text(encoding="utf-8"))
    assert len(exported) == 1
    assert exported[0]["user_id"] == "user_alice"


def test_resolve_db_path_matches_cli_and_sdk(tmp_path, monkeypatch):
    monkeypatch.delenv("AEMA_DB_PATH", raising=False)
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    # Outside repo -> ~/.aema/memory.db
    default_path = resolve_db_path()
    assert default_path.endswith(".aema/memory.db") or default_path.endswith(".aema\\memory.db")

    # Explicit AEMA_DB_PATH wins
    custom = str(tmp_path / "custom.db")
    monkeypatch.setenv("AEMA_DB_PATH", custom)
    assert resolve_db_path() == custom


@pytest.mark.asyncio
async def test_adaptive_memory_sync_wrappers_safe_inside_running_event_loop(tmp_path):
    db_file = str(tmp_path / "async_voice.db")
    mem = AdaptiveMemory(db_path=db_file)

    created = mem.remember("Keep spoken turns concise", domain="general")
    assert created["id"]

    hits = mem.recall("spoken turns", min_similarity=0.05)
    assert len(hits) == 1


def test_backend_non_sqlite_store_and_create_memory_embedding(tmp_path, monkeypatch):
    """
    Verify FastAPI telemetry, agent routes, and memory creation/search do not crash
    when shared_store is a non-SQLite store (no .db_path attribute, e.g. Postgres).
    """
    from fastapi.testclient import TestClient
    import backend.main as backend_main
    import backend.routes.agent as agent_routes
    import backend.routes.memories as mem_routes
    import backend.routes.telemetry as telemetry_routes

    class _NoDbPathStore:
        def __init__(self):
            self.items = {}

        async def list_experiences(self, domain=None, status=None, min_trust=0.0, user_id=None):
            exps = list(self.items.values())
            if user_id is not None:
                exps = [e for e in exps if e.user_id == user_id]
            return [e for e in exps if e.trust_score >= min_trust]

        async def add_experience(self, exp):
            self.items[exp.id] = exp
            return exp

        async def get_experience(self, exp_id):
            return self.items.get(exp_id)

        async def search_similar(self, query_embedding, domain=None, top_k=5, user_id=None):
            return [(e, 0.8) for e in self.items.values() if user_id is None or e.user_id == user_id][:top_k]

    stub = _NoDbPathStore()
    monkeypatch.setattr(agent_routes, "shared_store", stub)
    monkeypatch.setattr(mem_routes, "shared_store", stub)
    monkeypatch.setattr(telemetry_routes, "shared_store", stub)

    with TestClient(backend_main.app) as client:
        assert client.get("/api/v1/telemetry").status_code == 200
        assert client.get("/api/v1/agent/executions").status_code == 200
        assert client.get("/api/v1/agent/sessions").status_code == 200

        created = client.post(
            "/api/v1/memories",
            json={
                "userId": "startup_tenant",
                "taskDomain": "coding",
                "triggerCondition": "Asyncpg connection pool exhausted",
                "strategyLesson": "Bound max_size and release connections in async with pool.acquire()",
            },
        )
        assert created.status_code == 201
        created_body = created.json()
        assert len(stub.items[created_body["id"]].embedding or []) == 384

        # Verify adaptive min_similarity on /search (omitted min_similarity still works)
        from models.domain import ExperienceStatus
        stub.items[created_body["id"]].status = ExperienceStatus.ACTIVE
        search_res = client.post(
            "/api/v1/memories/search",
            json={
                "query": "Asyncpg connection pool exhausted",
                "userId": "startup_tenant",
            },
        )
        assert search_res.status_code == 200
        assert len(search_res.json()) == 1
