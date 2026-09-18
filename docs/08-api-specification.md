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

### GET /agent/executions/{id}
*Path alias: `GET /agent/executions/:id`*  
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

### GET /memories/{id}
*Path alias: `GET /memories/:id`*  
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

### PATCH /memories/{id}
*Path alias: `PATCH /memories/:id`*  
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

### GET /memories/{id}/trust-history
*Path alias: `GET /memories/:id/trust-history`*  
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

### POST /memories/{id}/deprecate
*Path alias: `POST /memories/:id/deprecate`*  
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

---

## External APIs & Third-Party Integration Points

The backend integrates with four categories of external systems. To satisfy the project's zero-cost development mandate and ensure model-agnostic flexibility, all external integrations feature 100% free tiers or local execution alternatives.

### 1. LLM Model Gateways (Reasoning, Execution & Reflection)

The agent uses **LiteLLM** as an abstraction gateway. The agent logic never calls raw provider SDKs directly; it calls LiteLLM with a unified interface (`litellm.completion(...)`), allowing seamless switching across models.

| Provider / Service | Endpoint / Protocol | Auth Header | Model Identifiers | Pricing / Limits | Role in Architecture |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Groq Cloud API** | `https://api.groq.com/openai/v1/chat/completions` (HTTP REST) | `Authorization: Bearer $GROQ_API_KEY` | `groq/llama-3.3-70b-versatile`, `groq/mixtral-8x7b-32768` | Free Tier (30 req/min, 6k tokens/min, 14.4k req/day) | Primary ultra-fast inference for `execute_node` and `reflect_node` |
| **Local Ollama** | `http://localhost:11434/v1/chat/completions` (HTTP REST) | *None (Localhost)* | `ollama/llama3.2:3b`, `ollama/mistral`, `ollama/qwen2.5:7b` | 100% Free, offline, zero data leaves machine | Zero-cost development & air-gapped benchmark testing |
| **Google Gemini API** | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` (HTTP REST) | `Authorization: Bearer $GEMINI_API_KEY` | `gemini/gemini-1.5-flash`, `gemini/gemini-1.5-pro` | Free Tier (15 RPM, 1M TPM, 1,500 req/day) | Free high-context cloud fallback |
| **OpenAI API** *(Optional)* | `https://api.openai.com/v1/chat/completions` (HTTP REST) | `Authorization: Bearer $OPENAI_API_KEY` | `openai/gpt-4o-mini`, `openai/gpt-4o` | Pay-as-you-go | Gold standard baseline comparison in benchmarks |
| **Anthropic API** *(Optional)* | `https://api.anthropic.com/v1/messages` (HTTP REST) | `x-api-key: $ANTHROPIC_API_KEY` | `claude-3-5-sonnet-20241022` | Pay-as-you-go | Secondary baseline comparison |

### 2. External Retrieval & Research Tools

When solving tasks, the agent invokes external research tools during `execute_node`.

| Service / Tool | Endpoint / Protocol | Auth | Free Tier / Policy | Input Parameters | Output Format |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DuckDuckGo Search** | Python package `duckduckgo-search` / HTML REST (`html.duckduckgo.com`) | *None required* | 100% Free, zero registration, rate-limited reasonably | `query` *(string)*, `max_results` *(int, default: 5)* | List of `{title, href, body}` |
| **Jina AI Reader** | `https://r.jina.ai/<TARGET_URL>` (HTTP GET) | *None required* (or optional free API key) | Free tier: 20 req/min without key, 200 req/min with free key | Target URL prepended to endpoint | Clean LLM-ready Markdown of full webpage without ads/navbars |
| **Tavily Search** *(Optional)* | `https://api.tavily.com/search` (POST JSON) | `api_key: $TAVILY_API_KEY` | Free tier: 1,000 queries/month | `{"query": "...", "search_depth": "basic"}` | Structured search results with extracted answers |

### 3. Database, Vector Search & Identity (Supabase)

| Service | Endpoint / Protocol | Connection Details | Auth | Role |
| :--- | :--- | :--- | :--- | :--- |
| **Supabase PostgreSQL 16** | `aws-0-ap-south-1.pooler.supabase.com:6543/postgres` (TCP / Session Pooler) | `postgresql://postgres.[ref]:[pw]@...:6543/postgres` | DB Credentials | ACID storage for `experiences`, `task_executions`, `trust_history` |
| **pgvector Extension** | Embedded inside PostgreSQL | `vector(1536)` (or `vector(384)`) with HNSW cosine index | DB connection | Sub-millisecond similarity search (`1 - (embedding <=> query)`) |
| **Supabase Auth (GoTrue)** | `https://fuwtdoxzfmghdxgferyf.supabase.co/auth/v1` (HTTPS REST) | Public API gateway | `apikey: $SUPABASE_ANON_KEY`, Bearer JWT | Validates incoming client tokens, extracts `user_id` |

### 4. Telemetry & Observability (LangSmith)

| Service | Endpoint / Protocol | Auth Header | Free Tier / Policy | Role |
| :--- | :--- | :--- | :--- | :--- |
| **LangSmith Tracing** | `https://api.smith.langchain.com` (HTTPS / Async Background) | `x-api-key: $LANGCHAIN_API_KEY` | Free Developer Tier (5,000 traces/month) | Full execution tracing: latency per LangGraph node, tokens used, prompts, and tool calls |

---

## End-to-End Architecture Flow (Internal ↔ External)

```
[Client: React Dashboard / Extension]
                 │  (1) POST /api/v1/agent/execute (Internal API)
                 ▼
     [FastAPI Application]
                 │  (2) Verify JWT with Supabase Auth (External API)
                 ▼
   [LangGraph 5-Node State Machine]
    ┌────────────────────────────────────────────────────────┐
    │ 1. retrieve_node:                                      │
    │    └── Embed query -> Query Supabase pgvector          │
    │        (Internal DB / External PostgreSQL)             │
    │                                                        │
    │ 2. execute_node:                                       │
    │    ├── LiteLLM -> Groq / Ollama / Gemini (External LLM)│
    │    └── Tool Calls -> DuckDuckGo / Jina (External Tools)│
    │                                                        │
    │ 3. evaluate_node:                                      │
    │    └── Heuristic rule evaluator (Deterministic Python) │
    │                                                        │
    │ 4. reflect_node:                                       │
    │    └── LiteLLM -> Groq / Ollama (External LLM)         │
    │        Extracts {Trigger, Strategy, Pitfall}           │
    │                                                        │
    │ 5. trust_node:                                         │
    │    └── EMA trust update -> Save to PostgreSQL          │
    │        (Internal DB / External PostgreSQL)             │
    └────────────────────────────────────────────────────────┘
                 │
                 ├── (Background) Send traces to LangSmith (External API)
                 ▼
[Response 200 OK with Trajectory & Lesson to Client]
```

