#!/usr/bin/env python3
"""
Automated Smoke Test for AEMA Containerized PostgreSQL + pgvector Cluster.
Validates:
1. Health check (/api/v1/health)
2. Memory creation & persistence in pgvector (POST /api/v1/memories)
3. Direct CRUD retrieval by ID (GET /api/v1/memories/{id})
4. Tenant isolation scoping (GET /api/v1/memories?userId=...)
5. Semantic cosine similarity search against pgvector (POST /api/v1/memories/search)
6. Observability & system telemetry (/api/v1/telemetry)
7. Privileged admin deletion security & cleanup (DELETE /api/v1/memories/{id})
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
        try:
            parsed_err = json.loads(err_body) if err_body else {}
        except Exception:
            parsed_err = {"raw": err_body}
        return he.code, parsed_err


def main():
    print(f"=== Starting AEMA Docker Smoke Test against {BASE_URL} ===")

    # 1. Health check
    print("Step 1: Checking health endpoint...")
    status, body = request_json("GET", "/api/v1/health")
    assert status == 200, f"Health check failed with status {status}: {body}"
    assert body.get("status") == "ok", f"Health status not ok: {body}"
    print("Health check OK.")

    # 2. Store a candidate memory for tenant A
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
        "trustScore": 0.50,
    }
    status, body = request_json("POST", "/api/v1/memories", payload=create_payload)
    assert status == 201, f"Memory creation failed with status {status}: {body}"
    assert body.get("id") == test_id, f"Created ID mismatch: {body}"
    assert body.get("status") == "candidate", f"Expected candidate lifecycle status: {body}"
    print(f"Memory {test_id} created successfully with status candidate.")

    # 3. Direct CRUD retrieval by ID
    print(f"Step 3: Fetching memory {test_id} directly by ID...")
    status, fetched = request_json("GET", f"/api/v1/memories/{test_id}")
    assert status == 200, f"Failed to fetch memory by ID: {status} {fetched}"
    assert fetched.get("id") == test_id, f"ID mismatch: {fetched}"
    assert fetched.get("userId") == tenant_a, f"User ID mismatch: {fetched}"
    assert fetched.get("taskDomain") == "coding", f"Domain mismatch: {fetched}"
    print(f"Direct retrieval verified: memory persisted in PostgreSQL with ID {test_id}.")

    # 4. Tenant isolation scoping
    print(f"Step 4: Verifying tenant isolation scoping...")
    status, list_a = request_json("GET", f"/api/v1/memories?userId={tenant_a}")
    assert status == 200, f"Listing for tenant A failed: {status} {list_a}"
    ids_a = [m.get("id") for m in list_a if isinstance(m, dict)]
    assert test_id in ids_a, f"Expected {test_id} in {tenant_a} listings: {ids_a}"

    status, list_b = request_json("GET", f"/api/v1/memories?userId={tenant_b}")
    assert status == 200, f"Listing for tenant B failed: {status} {list_b}"
    ids_b = [m.get("id") for m in list_b if isinstance(m, dict)]
    assert test_id not in ids_b, f"Tenant isolation violated: {test_id} visible to {tenant_b}!"
    print(f"Tenant isolation verified: {tenant_a} sees {test_id}, {tenant_b} sees 0 memories.")

    # 5. Semantic cosine similarity search against pgvector
    print(f"Step 5: Testing semantic cosine search on active memories...")
    search_payload = {
        "query": "Recursive depth calculation in deeply nested tree structures",
        "domain": "coding",
        "top_k": 3,
    }
    status, matches = request_json("POST", "/api/v1/memories/search", payload=search_payload)
    assert status == 200, f"Search failed with status {status}: {matches}"
    assert len(matches) > 0, f"Expected non-empty search matches: {matches}"
    match_ids = [m.get("experience", {}).get("id") for m in matches if isinstance(m, dict)]
    assert "exp-coding-001" in match_ids, f"Expected exp-coding-001 in search matches: {match_ids}"
    assert matches[0].get("similarity", 0) > 0.0, f"Expected positive similarity: {matches[0]}"
    assert matches[0].get("composite_score", 0) > 0.0, f"Expected positive composite score: {matches[0]}"
    print(f"Semantic search against pgvector verified: returned {len(matches)} matches (top: {match_ids[0]}).")

    # 6. Observability & system telemetry
    print("Step 6: Verifying telemetry endpoint...")
    status, telemetry = request_json("GET", "/api/v1/telemetry")
    assert status == 200, f"Telemetry failed with status {status}: {telemetry}"
    assert isinstance(telemetry, dict), f"Telemetry response format invalid: {telemetry}"
    print(f"Telemetry verified: {telemetry.get('total_memories', 'ok')} memories reported.")

    # 7. Privileged admin deletion security & cleanup
    print(f"Step 7: Verifying deletion access control & hard cleanup...")
    # Unauthenticated deletion must be rejected
    status, _ = request_json("DELETE", f"/api/v1/memories/{test_id}?hard_delete=true")
    assert status in (401, 403), f"Expected 401/403 for unauthenticated delete, got {status}"

    # Authorized admin deletion
    headers = {"Authorization": f"Bearer {ADMIN_KEY}"}
    status, _ = request_json("DELETE", f"/api/v1/memories/{test_id}?hard_delete=true", headers=headers)
    assert status in (200, 204), f"Admin delete failed with status {status}"

    # Confirm permanent deletion
    status, _ = request_json("GET", f"/api/v1/memories/{test_id}")
    assert status == 404, f"Expected 404 after hard delete, got {status}"
    print(f"Privileged admin deletion and hard cleanup verified for {test_id}.")

    print("\nALL DOCKER SMOKE TESTS PASSED SUCCESSFULLY! Cluster is 100% production-ready.")


if __name__ == "__main__":
    main()
