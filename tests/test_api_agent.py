"""
Integration tests for Agent Execution API endpoint (/api/v1/agent/execute).
Verifies full end-to-end execution of the 5-node LangGraph StateGraph via HTTP.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_agent_execute_endpoint_mock_provider():
    """Verify that POST /api/v1/agent/execute executes the 5-node graph and returns trajectory."""
    payload = {
        "taskInput": "Which planet is closest to the Sun?",
        "domain": "research",
        "memoryEnabled": True,
        "memoryMode": "adaptive",
        "provider": "mock",
    }

    response = client.post("/api/v1/agent/execute", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "id" in data
    assert data["status"] == "completed"
    assert "trajectory" in data
    assert len(data["trajectory"]) >= 5

    # Verify nodes in trajectory
    executed_nodes = [t["node"] for t in data["trajectory"] if "node" in t]
    for expected in ["retrieve_node", "execute_node", "evaluate_node", "reflect_node", "trust_node"]:
        assert expected in executed_nodes, f"Missing node {expected} in {executed_nodes}"

    assert data["finalAnswer"] is not None
    assert len(data["finalAnswer"]) > 0


def test_agent_executions_list_and_detail():
    """Verify listing and fetching specific execution record."""
    # 1. Run a task
    payload = {
        "taskInput": "Calculate fibonacci sequence iteratively",
        "domain": "coding",
        "memoryEnabled": True,
        "memoryMode": "adaptive",
        "provider": "mock",
    }
    exec_res = client.post("/api/v1/agent/execute", json=payload)
    assert exec_res.status_code == 200
    exec_id = exec_res.json()["id"]

    # 2. List executions
    list_res = client.get("/api/v1/agent/executions")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1

    # 3. Get single execution
    detail_res = client.get(f"/api/v1/agent/executions/{exec_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == exec_id
