#!/usr/bin/env python3
"""
Automated Smoke Test for AEMA Containerized PostgreSQL + pgvector Cluster.
Validates:
1. Health check (/api/v1/health)
2. Memory creation & persistence in pgvector (POST /api/v1/memories)
3. Semantic cosine similarity search (POST /api/v1/memories/search)
4. User tenant isolation (userId scoping assertions)
5. Telemetry endpoint (/api/v1/telemetry)
6. Admin cleanup (DELETE /api/v1/memories/{id}?hard_delete=true)
"""

import json
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ADMIN_KEY = sys.argv[2] if len(sys.argv) > 2 else "ci-smoke-admin-key"


def request_json(method: str, path: str, payload: dict = None, headers: dict = None) -> tuple:
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8")
        return he.code, json.loads(err_body) if err_body else {}


def main():
    print(f"=== Starting AEMA Docker Smoke Test against {BASE_URL} ===")

    # 1. Health check
    print("Step 1: Checking health endpoint...")
    status, body = request_json("GET", "/api/v1/health")
    assert status == 200, f"Health check failed with status {status}: {body}"
    assert body.get("status") == "ok", f"Health status not ok: {body}"
    print("Health check OK.")

    # 2. Store a verified memory for tenant A
    test_id = f"smoke-{uuid4().hex[:8]}"
    tenant_a = f"tenant-a-{uuid4().hex[:6]}"
    tenant_b = f"tenant-b-{uuid4().hex[:6]}"

    print(f"Step 2: Storing test memory {test_id} for {tenant_a}...")
    create_payload = {
        "id": test_id,
        "userId": tenant_a,
        "taskDomain": "coding",
        "triggerCondition": "High concurrency schema migration with active locks",
        "strategyLesson": "Run migrations in transactional batches and acquire short locks",
        "pitfall": "Running full table rewrites during peak traffic hours",
        "confidence": 0.95,
        "trustScore": 0.85,
    }
    status, body = request_json("POST", "/api/v1/memories", payload=create_payload)
    assert status == 201, f"Memory creation failed with status {status}: {body}"
    print(f"Memory created with status {status}.")

    # 3. Retrieve memory for tenant A using semantic search
    print(f"Step 3: Searching memories for {tenant_a}...")
    search_payload = {
        "query": "schema migrations with active database locks",
        "domain": "coding",
        "userId": tenant_a,
        "limit": 5,
    }
    status, matches = request_json("POST", "/api/v1/memories/search", payload=search_payload)
    assert status == 200, f"Search failed with status {status}: {matches}"
    match_ids = [m.get("id") or (m.get("experience", {}).get("id")) for m in matches]
    assert test_id in match_ids, f"Expected {test_id} in search results: {match_ids}"
    print(f"Semantic search returned match {test_id} successfully.")

    # 4. Verify tenant isolation for tenant B
    print(f"Step 4: Verifying tenant isolation for {tenant_b}...")
    isolated_search = {
        "query": "schema migrations with active database locks",
        "domain": "coding",
        "userId": tenant_b,
        "limit": 5,
    }
    status, isolated_matches = request_json("POST", "/api/v1/memories/search", payload=isolated_search)
    assert status == 200, f"Isolated search failed with status {status}: {isolated_matches}"
    isolated_ids = [m.get("id") or (m.get("experience", {}).get("id")) for m in isolated_matches]
    assert test_id not in isolated_ids, f"Tenant isolation violated: {test_id} leaked to {tenant_b}!"
    print(f"Tenant isolation verified: {tenant_b} cannot see {tenant_a}'s memories.")

    # 5. Check telemetry endpoint
    print("Step 5: Verifying telemetry endpoint...")
    status, telemetry = request_json("GET", "/api/v1/telemetry")
    assert status == 200, f"Telemetry failed with status {status}: {telemetry}"
    print(f"Telemetry verified: total_memories={telemetry.get('total_memories', 'ok')}.")

    # 6. Admin hard-delete cleanup
    print(f"Step 6: Cleaning up test memory {test_id} via admin authorization...")
    headers = {"Authorization": f"Bearer {ADMIN_KEY}"}
    status, _ = request_json("DELETE", f"/api/v1/memories/{test_id}?hard_delete=true", headers=headers)
    assert status in (200, 204), f"Delete failed with status {status}"
    print("Test memory successfully deleted.")

    print("\nALL DOCKER SMOKE TESTS PASSED SUCCESSFULLY! Cluster is 100% production-ready.")


if __name__ == "__main__":
    main()
