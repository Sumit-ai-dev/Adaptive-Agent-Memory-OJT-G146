# Requirements Traceability Matrix (RTM)

**Project:** Adaptive AI Agent with Persistent Experience Memory (AEMA)  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Approved & Verified across Implementation & Test Suites  

---

## 1. Traceability Matrix

The following matrix provides complete forward and backward traceability linking Business Requirements (BRD), Product Features (PRD), Technical Architecture (TRD), API Endpoints, Database Schemas, and Automated Test Suites:

| Business Req | Product Feature | Technical Req | API / Component | Database / Persistence | Automated Verification Tests |
|---|---|---|---|---|---|
| **BR-001** (Task Submission) | PR-001 (Interactive Execution Studio) | TR-001 (FastAPI Async Gateway) | `POST /api/v1/agent/run` | `task_executions` | `tests/test_api_agent.py` |
| **BR-002** (Experience Retrieval) | PR-002 (Ranked Memory Recall) | TR-002 (Composite Vector Ranking) | `retrieve_node.py` | `experiences` (pgvector HNSW RPC) | `tests/test_experiential_memory_pipeline.py`, `tests/test_memory_nodes.py` |
| **BR-003** (Memory Prompt Injection) | PR-003 (Bilateral Prompt Guidance) | TR-003 (Strategy + Pitfall Augmentation) | `execute_node.py` | In-memory `AgentState` | `tests/test_agent_graph.py`, `tests/test_execution_and_gateway.py` |
| **BR-004** (Outcome Evaluation) | PR-004 (Deterministic Grading) | TR-004 (AST Heuristic Reward Engine) | `evaluate_node.py` | `task_executions.evaluation_score` | `tests/test_evaluator.py`, `tests/test_evaluator_adversarial.py` |
| **BR-005** (Post-Run Reflection) | PR-005 (Structured Lesson Extraction) | TR-005 (Reflector 3-Tuple Distiller) | `reflect_node.py` | `experiences` (candidate records) | `tests/test_experiential_lifecycle_verification.py` |
| **BR-006** (Trust Lifecycle) | PR-006 (Empirical Trust Scoring) | TR-006 (A-EMA Mathematical Dynamic) | `trust_node.py` | `trust_history` (audit ledger) | `tests/test_trust_dynamics.py`, `tests/test_math_properties.py` |
| **BR-007** (Poisoning Protection) | PR-007 (Deterministic Quarantine) | TR-007 (Theorem 1 Quarantine Bound) | `trust_node.py` | `experiences.status = 'quarantined'` | `tests/test_failure_handling_and_quarantine.py`, `tests/test_quarantine_lifecycle_e2e.py` |
| **BR-008** (Thread Persistence) | PR-008 (Conversation History Drawer) | TR-008 (Session History Management) | `GET /api/v1/agent/sessions`, `POST /api/v1/agent/execute` | `task_executions`, SQLite session store | `tests/test_conversations.py` |
| **BR-009** (Memory Visualization) | PR-009 (3D Neural Memory Core) | TR-009 (WebGL Spatial Visualizer) | `ThreeMemoryCore.tsx` | `GET /api/v1/memories` | Frontend TypeScript Build (`tsc -b`), `tests/test_api_memories.py` |
| **BR-010** (Zero-GPU Infrastructure) | PR-010 (System Diagnostics & BYOK) | TR-010 (LiteLLM Adapter & Health API) | `GET /api/v1/health` | Diagnostic Telemetry | `tests/test_health.py`, `tests/test_step1_infrastructure.py` |

---

## 2. Verification Mapping by Component

### A. Memory Intelligence & Trust Subsystem
- **Core Files:** `ai-service/nodes/retrieve_node.py`, `ai-service/nodes/trust_node.py`, `ai-service/memory/embedder.py`, `ai-service/memory/postgres_store.py`
- **Associated Requirements:** BR-002, BR-006, BR-007, TR-002, TR-006, TR-007
- **Verification Suites:**
  - `tests/test_math_properties.py`: Verifies A-EMA monotonic trust convergence and bounds ($S \in [0.0, 1.0]$).
  - `tests/test_failure_handling_and_quarantine.py`: Formally validates Theorem 1 quarantine cutoff within 3 steps.
  - `tests/test_postgres_store.py`: Asserts correct vector serialization, cosine matching, and RPC execution.

### B. Agent Execution & Orchestration Subsystem
- **Core Files:** `ai-service/graph.py`, `ai-service/nodes/execute_node.py`, `ai-service/nodes/evaluate_node.py`, `ai-service/nodes/reflect_node.py`
- **Associated Requirements:** BR-001, BR-003, BR-004, BR-005, TR-001, TR-003, TR-004, TR-005
- **Verification Suites:**
  - `tests/test_agent_graph.py`: Validates complete 5-node StateGraph cyclicity.
  - `tests/test_evaluator.py`: Tests deterministic AST Python validation, tool code return parsing, and reward emission.
  - `tests/test_experiential_lifecycle_verification.py`: Confirms lesson extraction from non-trivial execution traces.

### C. Backend API Gateway & History Management Subsystem
- **Core Files:** `backend/app/main.py`, `backend/app/api/v1/agent.py`
- **Associated Requirements:** BR-001, BR-008, BR-010, TR-001, TR-008, TR-010
- **Verification Suites:**
  - `tests/test_api_agent.py`: Exercises `/api/v1/agent/run` with mock and real execution modes.
  - `tests/test_conversations.py`: Exercises thread creation, message appending, search filtering, and deletion.
  - `tests/test_health.py`: Validates `/api/v1/health` and root health endpoints.

### D. Frontend User Interface & 3D Spatial Core
- **Core Files:** `frontend/src/components/ThreeMemoryCore.tsx`, `frontend/src/components/ConversationDrawer.tsx`, `frontend/src/pages/Dashboard.tsx`
- **Associated Requirements:** BR-008, BR-009, PR-008, PR-009, TR-009
- **Verification Commands:**
  - `npx tsc -b` (Strict TypeScript verification)
  - `npm run build` (Vite production asset compilation)
