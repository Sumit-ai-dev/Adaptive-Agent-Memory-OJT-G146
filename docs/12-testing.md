# Testing Strategy

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Approved Testing Specification (Month 2 Specification)  

---

## Test Levels

The testing strategy validates the entire stack from low-level mathematical formulas to end-to-end multi-agent execution:

1. **Unit Testing:**
   * Validates standalone modules in isolation using `pytest`.
   * Verifies Pydantic v2 data schemas, EMA trust formula updates, vector cosine math, and API response serializers.
2. **Integration Testing:**
   * Tests interactions with Supabase PostgreSQL and `pgvector`.
   * Verifies database migrations, Row-Level Security policies, and the `match_experiences` stored procedure.
3. **Agent Workflow Testing:**
   * Uses mocked LLM responses to test deterministic state transitions across the 5 LangGraph nodes (`retrieve` → `execute` → `evaluate` → `reflect` → `trust`).
   * Validates edge transitions: max-iteration loop breakers, error branches, and zero-shot cold starts.
4. **API Contract & End-to-End Testing:**
   * Uses `httpx.AsyncClient` to test live endpoints (`GET /api/v1/health`, `POST /api/v1/tasks/run`).
   * Validates authentication header parsing, status codes, and JSON response envelopes.
5. **Memory & Retrieval Evaluation:**
   * Evaluates top-$k$ recall, semantic ranking precision, and deduplication clustering accuracy.
6. **GenAI & Agentic Evaluation:**
   * Benchmarks task success rate and negative transfer mitigation across benchmark task distributions.

---

## Sample Test Cases

| Test ID | Category | Scenario / Input | Expected Result | Priority |
|---|---|---|---|---|
| **TEST-001** | API | `GET /api/v1/health` | Returns HTTP 200 `{"status": "ok", "service": "adaptive-agent-backend"}` | High |
| **TEST-002** | Retrieval | Query with active matching experiences ($\text{Sim} \ge 0.70$) | Returns Top-$k$ experiences sorted by $0.70\text{Sim} + 0.30\text{Trust}$ | High |
| **TEST-003** | Cold Start | Query with zero semantic matches ($\text{Sim} < 0.70$) | Returns empty memory list; executes zero-shot baseline cleanly | High |
| **TEST-004** | Agent Exec | Model triggers valid tool call (DuckDuckGo search) | Agent executes tool, parses text, and completes task successfully | High |
| **TEST-005** | Circuit Breaker| Model loops without reaching terminal answer | LangGraph terminates at `max_turns = 4`; assigns $R_t = 0.0$ | High |
| **TEST-006** | Reflection | Trajectory completes with non-trivial tool steps | Reflector emits valid `{Trigger, Strategy, Pitfall}` JSON matching schema | High |
| **TEST-007** | Trust Update | Reused experience on successful task run ($R_t = 1.0$) | Trust score increases via EMA: $S_{t+1} = 0.15(1.0) + 0.85(S_t)$ | High |
| **TEST-008** | Quarantine | Reused experience drops below threshold ($S < 0.35$) | Experience status updates to `deprecated`; excluded from future retrieval | High |
| **TEST-009** | Deduplication | New reflection has cosine distance $< 0.10$ from existing | System merges evidence rather than creating duplicate row | Medium |
| **TEST-010** | Security/BYOK | Invalid or expired JWT token | Request rejected with HTTP 401 Unauthorized | High |

---

## Memory & Retrieval Evaluation

To ensure the external memory store enhances rather than degrades agent capability, retrieval is evaluated against:
1. **Recall@k:** Measures whether the empirically optimal strategy for a task domain appears in the retrieved Top-$k$ candidates.
2. **Ranking Consistency:** Verifies that a high-trust memory ($S = 0.90$) outranks an identical-similarity memory with low trust ($S = 0.40$), confirming the composite formula $0.70\text{Sim} + 0.30\text{Trust}$.
3. **Retrieval Latency:** Benchmarks pgvector query resolution time under simulated load, verifying $p95 < 25\text{ ms}$ on 10,000+ vector rows.

---

## GenAI Evaluation

GenAI evaluation does not rely on subjective human rating alone; it implements continuous automated scoring:

1. **Deterministic Scalar Reward ($R_t \in [0.0, 1.0]$):**
   * Output verified against ground-truth regex markers, schema validators, and tool exit codes.
   * Produces reproducible numerical metrics across repetitive experimental runs.
2. **Reflection Quality Assessment:**
   * Schema compliance: 100% adherence to `{Trigger, Strategy, Pitfall}` format.
   * Conciseness: Strategies and pitfalls bounded to $\le 100$ tokens to minimize prompt overhead.
3. **Negative Transfer Reduction Metric:**
   * When identical failure scenarios are re-submitted, the agent must leverage the stored Pitfall to avoid repeating the previous mistake, measured by the reduction in recurring failure rate ($\Delta \text{Error} \ge 60\%$).
