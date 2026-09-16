# API Specification

Base URL: `/api/v1`

## Overview & Authentication

The API provides RESTful endpoints connecting clients (React Dashboard, Chrome Extension companion) to the FastAPI backend, LangGraph agent orchestration engine, and PostgreSQL + `pgvector` persistence layer.

### Authentication
All protected endpoints require an HTTP Bearer JWT token issued by Supabase Auth:
```http
Authorization: Bearer <supabase_jwt_access_token>
```
Endpoints return `401 Unauthorized` if the header is missing or expired, and `403 Forbidden` if the caller lacks permission.

---

## Agent Execution

### POST /agent/execute
Executes a task through the 5-node LangGraph orchestration loop (`retrieve_node` → `execute_node` → `evaluate_node` → `reflect_node` → `trust_node`). Handles experience retrieval, task execution with LiteLLM and tools, outcome evaluation, reflection, and trust scoring.

**Request Body:**
```json
{
  "task_input": "Research conflicting claims on carbon capture efficiency rates.",
  "task_domain": "research",
  "memory_enabled": true,
  "memory_mode": "adaptive"
}
```

* `task_input` *(string, required)*: The natural language prompt or problem statement.
* `task_domain` *(string, required)*: One of `research`, `coding`, `analysis`, `planning`.
* `memory_enabled` *(boolean, required)*: Whether to enable the memory subsystem.
* `memory_mode` *(string, optional, default: `"adaptive"`)*: Execution condition:
  * `"off"`: Condition A (Baseline agent, no experience retrieval).
  * `"naive"`: Condition B (Standard semantic retrieval, no reliability filtering).
  * `"adaptive"`: Condition C (Retrieval with composite similarity + trust scoring and reliability updates).

**Response (200 OK):**
```json
{
  "execution_id": "exec_8f12a9c4",
  "task_id": "task_3d78e2b1",
  "final_answer": "Synthesis of empirical literature shows direct air capture requires 1,200–2,000 kWh/tCO2 depending on thermal regeneration efficiency...",
  "status": "success",
  "execution_metadata": {
    "latency_ms": 3420,
    "steps_count": 3,
    "tool_calls_count": 2,
    "outcome_score": 0.88
  },
  "trajectory": [
    {
      "node": "retrieve_node",
      "status": "completed",
      "duration_ms": 115,
      "details": "Retrieved 1 candidate experience exceeding trust threshold (>=0.35)."
    },
    {
      "node": "execute_node",
      "status": "completed",
      "tools_called": ["duckduckgo_search"],
      "duration_ms": 2100
    },
    {
      "node": "evaluate_node",
      "status": "completed",
      "outcome_score": 0.88,
      "evaluator": "heuristic_outcome_evaluator"
    },
    {
      "node": "reflect_node",
      "status": "completed",
      "extracted": true
    },
    {
      "node": "trust_node",
      "status": "completed",
      "updated_experiences_count": 1
    }
  ],
  "retrieved_memories": [
    {
      "experience_id": "exp_10a8c2f1",
      "strategy": "Verify disputed technical claims across at least 2 independent primary literature citations before finalizing output.",
      "similarity_score": 0.89,
      "trust_score": 0.94,
      "composite_score": 0.905
    }
  ],
  "new_experience": {
    "experience_id": "exp_91b7d3e0",
    "trigger": "Technical queries involving thermodynamic efficiency benchmarks",
    "strategy": "State explicit temperature and pressure boundary conditions when comparing heat pump and thermal regeneration efficiencies.",
    "pitfall": "Do not compare industrial pilot plant claims with theoretical Carnot limits directly.",
    "confidence": 0.85,
    "initial_trust": 0.60,
    "status": "candidate"
  }
}
```

### GET /agent/executions
Lists historical task execution records with filtering and pagination.

**Query Parameters:**
* `domain` *(string, optional)*: Filter by task domain (`research`, `coding`, `analysis`, `planning`).
* `memory_mode` *(string, optional)*: Filter by condition (`off`, `naive`, `adaptive`).
* `limit` *(integer, optional, default: 20, max: 100)*: Items per page.
* `offset` *(integer, optional, default: 0)*: Pagination offset.

**Response (200 OK):**
```json
{
  "total": 128,
  "items": [
    {
      "execution_id": "exec_8f12a9c4",
      "task_id": "task_3d78e2b1",
      "task_input": "Research conflicting claims on carbon capture efficiency rates.",
      "task_domain": "research",
      "memory_mode": "adaptive",
      "status": "success",
      "outcome_score": 0.88,
      "latency_ms": 3420,
      "created_at": "2026-09-15T14:22:10Z"
    }
  ]
}
```

### GET /agent/executions/:id
Returns granular execution details for a specific run, including complete node trajectory, tools invoked, prompt token usage, retrieved memories, and outcome evaluation.

**Response (200 OK):**
```json
{
  "execution_id": "exec_8f12a9c4",
  "task_id": "task_3d78e2b1",
  "task_input": "Research conflicting claims on carbon capture efficiency rates.",
  "task_domain": "research",
  "memory_mode": "adaptive",
  "status": "success",
  "outcome_score": 0.88,
  "final_answer": "Synthesis of empirical literature shows...",
  "trajectory": [
    { "step": 1, "node": "retrieve_node", "latency_ms": 115 },
    { "step": 2, "node": "execute_node", "latency_ms": 2100 },
    { "step": 3, "node": "evaluate_node", "latency_ms": 450 },
    { "step": 4, "node": "reflect_node", "latency_ms": 620 },
    { "step": 5, "node": "trust_node", "latency_ms": 135 }
  ],
  "retrieved_memories": [
    {
      "experience_id": "exp_10a8c2f1",
      "strategy": "Verify disputed technical claims across at least 2 independent primary literature citations before finalizing output.",
      "trust_score": 0.94,
      "similarity_score": 0.89
    }
  ],
  "created_at": "2026-09-15T14:22:10Z"
}
```

---

## Experiences

### GET /memories
Lists persistent experiences stored in PostgreSQL + `pgvector` with relevance and metadata filters.

**Query Parameters:**
* `domain` *(string, optional)*: Filter by task domain (`research`, `coding`, `analysis`, `planning`, `all`).
* `status` *(string, optional)*: Filter by lifecycle state (`candidate`, `active`, `deprecated`).
* `min_trust` *(float, optional, default: 0.0)*: Minimum trust score filter (e.g. `0.35`).
* `search` *(string, optional)*: Semantic search query against experience embeddings via `pgvector`.
* `limit` *(integer, optional, default: 20, max: 100)*: Items per page.
* `offset` *(integer, optional, default: 0)*: Pagination offset.

**Response (200 OK):**
```json
{
  "total": 45,
  "items": [
    {
      "id": "exp_10a8c2f1",
      "domain": "research",
      "trigger": "Conflicting or multi-source factual claims in research queries",
      "strategy": "Verify disputed claims across at least 2 independent primary literature citations before synthesizing conclusions.",
      "pitfall": "Do not rely on a single secondary summary when domain estimates diverge.",
      "trust_score": 0.94,
      "confidence": 0.90,
      "uses_count": 412,
      "success_count": 388,
      "failure_count": 24,
      "status": "active",
      "created_at": "2026-08-15T10:00:00Z",
      "updated_at": "2026-09-15T14:22:12Z",
      "last_used_at": "2026-09-15T14:22:10Z"
    }
  ]
}
```

### GET /memories/:id
Returns detailed metadata for an individual experience, including its source execution provenance.

**Response (200 OK):**
```json
{
  "id": "exp_10a8c2f1",
  "domain": "research",
  "trigger": "Conflicting or multi-source factual claims in research queries",
  "strategy": "Verify disputed claims across at least 2 independent primary literature citations before synthesizing conclusions.",
  "pitfall": "Do not rely on a single secondary summary when domain estimates diverge.",
  "context": "Scientific literature analysis with diverging quantitative estimates",
  "trust_score": 0.94,
  "confidence": 0.90,
  "uses_count": 412,
  "success_count": 388,
  "failure_count": 24,
  "status": "active",
  "source_execution_id": "exec_01e74f88",
  "created_at": "2026-08-15T10:00:00Z",
  "updated_at": "2026-09-15T14:22:12Z",
  "last_used_at": "2026-09-15T14:22:10Z"
}
```

### PATCH /memories/:id
Updates editable metadata or lifecycle status of an existing experience record.

**Request Body:**
```json
{
  "status": "deprecated",
  "strategy": "Updated strategy statement based on manual supervisor review."
}
```

* `status` *(string, optional)*: New lifecycle status (`candidate`, `active`, `deprecated`).
* `strategy` *(string, optional)*: Refined strategy text.
* `pitfall` *(string, optional)*: Refined pitfall text.

**Response (200 OK):**
```json
{
  "id": "exp_10a8c2f1",
  "status": "deprecated",
  "updated_at": "2026-09-16T10:15:00Z",
  "message": "Experience updated successfully."
}
```

---

## Trust & Lifecycle

### GET /memories/:id/trust-history
Returns the complete audit log of trust adjustments for an experience, recording each execution outcome and formula transition.

**Response (200 OK):**
```json
{
  "experience_id": "exp_10a8c2f1",
  "current_trust": 0.94,
  "history": [
    {
      "timestamp": "2026-09-15T14:22:12Z",
      "execution_id": "exec_8f12a9c4",
      "old_trust": 0.925,
      "outcome_score": 1.0,
      "new_trust": 0.94,
      "formula": "EMA(S_next = 0.8 * S_prev + 0.2 * R)"
    },
    {
      "timestamp": "2026-09-14T09:18:30Z",
      "execution_id": "exec_77b3d11a",
      "old_trust": 0.906,
      "outcome_score": 1.0,
      "new_trust": 0.925,
      "formula": "EMA(S_next = 0.8 * S_prev + 0.2 * R)"
    }
  ]
}
```

### POST /memories/:id/deprecate
Explicitly marks an experience as `deprecated`, immediately removing it from candidate pools in future retrieval cycles.

**Request Body:**
```json
{
  "reason": "Superseded by updated library documentation in v2.0 release."
}
```

**Response (200 OK):**
```json
{
  "id": "exp_10a8c2f1",
  "status": "deprecated",
  "trust_score": 0.94,
  "deprecated_at": "2026-09-16T10:30:00Z",
  "reason": "Superseded by updated library documentation in v2.0 release."
}
```

---

## Evaluation & Benchmarks

### POST /evaluation/run-benchmark
Initiates an offline comparative benchmark job evaluating the agent across standard test datasets under controlled experimental conditions.

**Request Body:**
```json
{
  "benchmark_suite": "standard_reasoning_v1",
  "conditions": ["memory_off", "naive_memory", "adaptive_memory"],
  "tasks_count": 50,
  "iterations_per_task": 3
}
```

* `benchmark_suite` *(string, required)*: Identifier for dataset in `data/`.
* `conditions` *(array of strings, required)*: Subsets of `memory_off`, `naive_memory`, `adaptive_memory`.
* `tasks_count` *(integer, optional, default: 50)*: Number of benchmark tasks to run.
* `iterations_per_task` *(integer, optional, default: 1)*: Repetitions per task for variance measurement.

**Response (202 Accepted):**
```json
{
  "job_id": "eval_job_7a29e4",
  "status": "queued",
  "benchmark_suite": "standard_reasoning_v1",
  "conditions": ["memory_off", "naive_memory", "adaptive_memory"],
  "created_at": "2026-09-16T11:00:00Z",
  "message": "Benchmark job successfully queued."
}
```

### GET /evaluation/results
Returns aggregated evaluation metrics across completed benchmark runs, contrasting Condition A (Memory OFF), Condition B (Naive Memory), and Condition C (Adaptive Memory).

**Query Parameters:**
* `benchmark_suite` *(string, optional)*: Filter by test suite identifier.
* `job_id` *(string, optional)*: Filter by specific evaluation run.

**Response (200 OK):**
```json
{
  "benchmark_suite": "standard_reasoning_v1",
  "total_tasks_evaluated": 50,
  "comparisons": [
    {
      "condition": "memory_off",
      "label": "Condition A (Baseline)",
      "success_rate": 0.68,
      "avg_outcome_score": 0.65,
      "avg_latency_ms": 2840,
      "total_runs": 150
    },
    {
      "condition": "naive_memory",
      "label": "Condition B (Relevance-Only Memory)",
      "success_rate": 0.74,
      "avg_outcome_score": 0.71,
      "avg_latency_ms": 3120,
      "total_runs": 150
    },
    {
      "condition": "adaptive_memory",
      "label": "Condition C (Reliability-Aware Memory)",
      "success_rate": 0.82,
      "avg_outcome_score": 0.79,
      "avg_latency_ms": 3310,
      "total_runs": 150
    }
  ],
  "memory_utility": {
    "harmful_recollections_filtered": 18,
    "net_improvement_over_naive": 0.08
  }
}
```

---

## System Health

### GET /health
Returns operational status of the API server, database connectivity, and LiteLLM model provider gateway.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "pgvector": "available",
    "litellm_gateway": "ready"
  },
  "timestamp": "2026-09-16T12:00:00Z"
}
```

---

## Standard Errors

All non-2xx responses adhere to a consistent error schema:

```json
{
  "error": {
    "code": "EXPERIENCE_NOT_FOUND",
    "message": "The requested experience record does not exist or has been permanently purged.",
    "requestId": "req_6b82f0a1"
  }
}
```

### HTTP Status Code Conventions
* `400 Bad Request`: Malformed syntax or request query validation failures.
* `401 Unauthorized`: Missing, invalid, or expired Supabase Bearer token.
* `403 Forbidden`: Authenticated user lacks permission for the requested action.
* `404 Not Found`: Target resource (e.g., `execution_id` or `experience_id`) does not exist.
* `409 Conflict`: Conflict with current state (e.g., attempting duplicate experience persistence without merging).
* `422 Unprocessable Entity`: Pydantic schema validation failures (e.g., missing required fields, invalid domain enum).
* `500 Internal Server Error`: Unhandled server exceptions during execution or reflection.
* `503 Service Unavailable`: External dependency unreachable (e.g., LiteLLM model provider gateway or Supabase database downtime).
