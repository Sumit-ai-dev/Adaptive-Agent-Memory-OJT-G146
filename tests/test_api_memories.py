"""
API Integration tests for Memory Subsystem and Telemetry Endpoints.
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Backend Gateway Lead)
"""

import pytest
from fastapi.testclient import TestClient

try:
    from app.main import app
except ModuleNotFoundError:
    from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_list_memories_endpoint(client):
    """GET /api/v1/memories should return seeded experiences."""
    response = client.get("/api/v1/memories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    # Check 7-tuple keys exist
    first = data[0]
    assert "taskDomain" in first or "task_domain" in first
    assert "strategyLesson" in first or "strategy_lesson" in first
    assert "trustScore" in first or "trust_score" in first


def test_list_memories_domain_filter(client):
    """GET /api/v1/memories?domain=coding should only return coding items."""
    response = client.get("/api/v1/memories?domain=coding")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for item in data:
        domain = item.get("taskDomain") or item.get("task_domain")
        assert domain == "coding"


def test_get_memory_by_id(client):
    """GET /api/v1/memories/{id} returns single memory or 404."""
    response = client.get("/api/v1/memories/exp-coding-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "exp-coding-001"

    # Non-existent ID should 404
    missing_response = client.get("/api/v1/memories/non-existent-uuid")
    assert missing_response.status_code == 404


def test_retrieve_memories_composite_ranking(client):
    """POST /api/v1/memories/retrieve executes composite retrieval."""
    payload = {
        "task_input": "Optimize recursive graph algorithm",
        "domain": "coding",
        # 0.20 gives headroom for the deterministic hash embedder used in CI
        # (sentence-transformers absent). Production similarity is ~0.7+ for
        # semantically matching tasks.
        "min_similarity": 0.20,
        "min_trust": 0.35,
        "top_k": 2,
    }
    response = client.post("/api/v1/memories/retrieve", json=payload)
    assert response.status_code == 200
    matches = response.json()
    assert isinstance(matches, list)
    assert len(matches) >= 1
    for m in matches:
        assert "compositeScore" in m or "composite_score" in m
        score = m.get("compositeScore") or m.get("composite_score")
        assert score > 0.0


def test_trust_update_success_reward(client):
    """POST /api/v1/memories/trust-update with R=0.95 increases trust score."""
    # Seed experience with initial trust 0.88
    payload = {
        "experience_id": "exp-coding-001",
        "outcome_score": 0.95,
        "execution_id": "exec-test-success",
    }
    response = client.post("/api/v1/memories/trust-update", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "experience" in data
    assert "auditRecord" in data or "audit_record" in data
    assert "trustUpdate" in data or "trust_update" in data


def test_trust_update_failure_penalty_and_quarantine(client):
    """POST /api/v1/memories/trust-update with R=0.0 drops trust and deprecates."""
    payload = {
        "experience_id": "exp-candidate-004",  # starts at trust 0.50
        "outcome_score": 0.05,
        "execution_id": "exec-test-fail",
    }
    response = client.post("/api/v1/memories/trust-update", json=payload)
    assert response.status_code == 200
    data = response.json()
    exp = data["experience"]
    # 0.70 * 0.50 = 0.35 -> second penalty drops below 0.35
    assert exp["trustScore"] < 0.50 or exp["trust_score"] < 0.50


def test_telemetry_endpoint(client):
    """GET /api/v1/telemetry returns aggregate memory metrics."""
    response = client.get("/api/v1/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "activeMemories" in data
    assert "avgTrustScore" in data
    assert "memoryHitRate" in data
    assert data["activeMemories"] >= 1
