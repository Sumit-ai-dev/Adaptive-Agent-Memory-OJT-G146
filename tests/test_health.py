import pytest
from fastapi.testclient import TestClient

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app


client = TestClient(app)


def test_health_check_api_v1():
    """Verify that GET /api/v1/health returns status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "adaptive-agent-backend"
    }


def test_health_check_root_alias():
    """Verify that GET /health alias responds with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "adaptive-agent-backend"
    }


def test_root_endpoint():
    """Verify that GET / returns service information."""
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "adaptive-agent-backend"
    assert payload["health"] == "/api/v1/health"
