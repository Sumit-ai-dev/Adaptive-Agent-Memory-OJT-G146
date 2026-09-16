# Technical Requirements Document (TRD)

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146  
**Track:** Generative AI / Agentic AI  

---

## 1. Proposed Architecture

- **Client / Access Layer:**
  - **Central Dashboard:** React, Vite, TypeScript, Tailwind CSS, Three.js
  - **Browser Extension:** TypeScript, Chrome Extension Manifest V3 (planned client companion)
- **Backend / API Layer:** Python, FastAPI, Pydantic v2, Uvicorn
- **Agent Orchestration Layer:** LangGraph StateGraph (5-node execution loop: `retrieve_node` → `execute_node` → `evaluate_node` → `reflect_node` → `trust_node`)
- **Model Gateway & Providers:** LiteLLM gateway abstraction (Groq, local Ollama)
- **Vector Embeddings:** Local HuggingFace embedding models (`bge-small-en-v1.5` or `all-MiniLM-L6-v2`)
- **Agent Tools:** DuckDuckGo Search, Jina AI Reader (`r.jina.ai/<url>`), Python execution, document reader
- **Persistence & Vector Layer:** Supabase PostgreSQL + `pgvector`, SQLAlchemy (ORM), Alembic (migrations)
- **Authentication:** Supabase Auth (GoTrue) with JWT Bearer verification
- **Observability & Tracing:** LangSmith (LangGraph node-level tracing, latency and run inspection)
- **Testing & Scientific Evaluation:** `pytest`, NumPy, Scikit-learn, `matplotlib` (controlled evaluation: Condition A vs. B vs. C)
- **Infrastructure & Tooling:** Docker, GitHub Actions (CI)

```text
Dashboard (React + Vite) ────────┐
                                 │
                                 ↓ HTTP / Bearer JWT
                         FastAPI (/api/v1)
                                 │
                                 ↓
                    LangGraph Agent (StateGraph)
              ┌──────────────────────────────────────┐
              │ 1. retrieve_node (pgvector + trust)   │
              │ 2. execute_node (LiteLLM + Tools)    │
              │ 3. evaluate_node (Outcome Score R)   │
              │ 4. reflect_node (Lesson Extraction)  │
              │ 5. trust_node (EMA Score Update)     │
              └──────────────────┬───────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ↓                    ↓                    ↓
  LiteLLM Gateway      Supabase PostgreSQL      LangSmith
  (Groq / Ollama)          + pgvector           (Observability)
            ↑                    ↑
            │                    │
  HuggingFace Embeds    Browser Extension (MV3)
  (bge-small/MiniLM)    (Planned Client)
```

---

## 2. Technology Rationale

### React, Vite, TypeScript & Tailwind CSS (Dashboard)
- **Role:** Web-based central interface for submitting tasks, inspecting agent trajectories, browsing persistent experiences, and visualizing reliability trends over time.
- **Rationale:** Vite provides fast development builds; React offers component-driven UI modularity; TypeScript guarantees strict data contract safety across complex experience and trace objects; Tailwind CSS ensures a clean, responsive layout; Three.js powers the interactive 3D memory core visualization.

### Chrome Extension Manifest V3 (Browser Extension)
- **Role:** Planned client companion allowing users to invoke the agent and access the shared persistent experience store directly within browser workflows.
- **Rationale:** Manifest V3 complies with modern browser security standards while consuming the exact same centralized FastAPI `/api/v1` endpoints as the dashboard.

### Python & FastAPI (Backend / API Layer)
- **Role:** Application API layer exposing versioned RESTful endpoints for task execution, experience retrieval, trust auditing, evaluation runs, and health checks.
- **Rationale:** FastAPI offers native asynchronous execution, high performance, automatic OpenAPI documentation, and strict schema validation powered by Pydantic v2.

### LangGraph StateGraph (Agent Orchestration Layer)
- **Role:** Orchestrates the cyclical 5-node agent execution workflow: retrieving past experiences, executing tasks with tools, evaluating outcomes, reflecting on operational lessons, and updating trust scores.
- **Rationale:** Rather than relying on opaque, black-box agent chains, LangGraph provides an explicit, deterministic state graph with typed state channels (`task`, `retrieved_memories`, `trajectory`, `outcome_score`, `new_experience`). This ensures full control over research logic and clean step-level tracing.

### LiteLLM Gateway & Open Model Providers (Groq / Ollama)
- **Role:** Unified model gateway providing reasoning capabilities for task execution and reflection.
- **Rationale:** LiteLLM abstracts underlying model providers behind a standardized interface, preventing vendor lock-in. Supporting Groq (cloud) and Ollama (local open-weight models) keeps the project zero-cost for the 12-week OJT while ensuring high inference throughput.

### Local HuggingFace Embeddings (Vector Generation)
- **Role:** Generates dense semantic vector embeddings for tasks and experiences locally.
- **Rationale:** Deploying models such as `bge-small-en-v1.5` or `all-MiniLM-L6-v2` locally eliminates external embedding API costs and rate limits while maintaining high retrieval accuracy.

### Deterministic Tools (DuckDuckGo Search, Jina AI Reader, Python Execution)
- **Role:** Provides grounded external information retrieval and computational execution for agent tasks.
- **Rationale:** DuckDuckGo provides zero-cost web search; Jina AI Reader (`r.jina.ai/<url>`) extracts clean, Markdown-formatted web content without web-scraping overhead; Python execution enables deterministic problem solving.

### PostgreSQL + pgvector via Supabase (Persistence Layer)
- **Role:** Unified persistent storage for relational entities (tasks, executions, trust logs) and high-dimensional vector embeddings for semantic experience search.
- **Rationale:** Experiences require both rich relational metadata (lesson, trigger, pitfall, confidence, trust score, status, usage counters) and vector embeddings. PostgreSQL with `pgvector` enables combined relational filtering (e.g., `status = 'active' AND trust_score >= 0.35`) and cosine similarity search within a single ACID-compliant database.

### Supabase Auth (Authentication)
- **Role:** User identity management, session handling, and endpoint route protection.
- **Rationale:** Built-in GoTrue authentication provides reliable email/password auth and JWT tokens verified by FastAPI middleware, securing backend APIs without custom authentication debt.

### LangSmith (Observability & Tracing)
- **Role:** Execution monitoring, node-level latency tracking, token usage inspection, and trajectory debugging across LangGraph runs.
- **Rationale:** Seamless integration with LangGraph allows fine-grained observability of each discrete node transition, providing transparent evidence for research analysis.

### Pytest, NumPy, Scikit-learn & Matplotlib (Testing & Evaluation)
- **Role:** Unit testing, component integration verification, offline batch evaluation, and scientific plotting.
- **Rationale:** `pytest` enforces software correctness; evaluation scripts systematically benchmark Condition A (Memory OFF), Condition B (Naive Memory), and Condition C (Adaptive Memory); `matplotlib` plots comparative performance and trust evolution curves.

### Docker & GitHub Actions (Infrastructure & CI)
- **Role:** Containerization of backend and frontend services, alongside automated testing and linting pipelines.
- **Rationale:** Docker ensures identical execution environments across local development and evaluation setups; GitHub Actions runs automated CI checks on every commit.

---

## 3. Technical Requirements

| ID | Requirement | Description | Maps to |
| :--- | :--- | :--- | :--- |
| **TR-001** | Versioned RESTful API | FastAPI `/api/v1` endpoints for task execution, experience querying, trust audit logs, and benchmark runs. | US-001, US-008 |
| **TR-002** | Dual Client Support | Central React dashboard and planned Chrome MV3 extension consuming the same backend API contracts. | US-001, US-009 |
| **TR-003** | Model Gateway Abstraction | LiteLLM gateway supporting Groq and Ollama, keeping the underlying model fixed during comparative evaluations. | US-001, US-003 |
| **TR-004** | Explicit LangGraph Orchestration | Deterministic 5-node StateGraph managing retrieval, execution, evaluation, reflection, and trust scoring. | US-001, US-002 |
| **TR-005** | Hybrid Memory Persistence | PostgreSQL schema storing structured experience metadata, provenance, usage history, and `pgvector` embeddings. | US-002, US-006 |
| **TR-006** | Relevance & Reliability Retrieval | Query engine combining vector similarity with reliability scoring ($0.70 \times \text{Sim} + 0.30 \times \text{Trust}$) to rank candidates. | US-002, US-005 |
| **TR-007** | Post-Execution Reflection | Reflection node distilling structured operational lessons (`{Trigger, Strategy, Pitfall}`) from multi-step runs. | US-003 |
| **TR-008** | Outcome Evaluation Module | Heuristic evaluation component assessing task success ($R \in [0, 1]$) and attributing outcomes to reused experiences. | US-004 |
| **TR-009** | Trust & Reliability Tracker | Dynamic score adjustment algorithm updating experience trust via Exponential Moving Average ($S_{t+1} = 0.8 S_t + 0.2 R$). | US-005 |
| **TR-010** | Experience Lifecycle Controller | State machine managing status (`CANDIDATE` → `ACTIVE` → `DEPRECATED`) and filtering records below trust threshold ($< 0.35$). | US-006 |
| **TR-011** | Controlled Evaluation Harness | Automated offline test runner executing identical task suites across Condition A, Condition B, and Condition C. | US-007 |
| **TR-012** | Node-Level Tracing & Observability | LangSmith tracing and structured logging capturing node transitions, latencies, and state payloads. | US-001, US-008 |

---

## 4. Non-Functional Requirements (NFR Targets)

- **Research Control & Reproducibility:** The underlying LLM and prompt baselines must remain fixed across benchmark evaluations to ensure valid attribution of performance gains to the memory subsystem.
- **Zero-Cost Development Architecture:** System services prioritized around zero-cost or open-source tiers (LiteLLM with Groq/Ollama, local HuggingFace embeddings, DuckDuckGo search, Jina Reader, Supabase free tier).
- **API Latency:** Non-LLM backend operations (pgvector similarity search, composite ranking, trust updates, DB writes) target p95 < 200 ms.
- **Deterministic Evaluation:** Batch evaluation runs must produce consistent, reproducible scoring logs and exportable JSON result sets.
- **Modularity & Maintainability:** Strict layer separation between API routing (`app/api/v1`), agent orchestration (`ai-service/agent`), memory lifecycle (`ai-service/memory`), and database models (`app/database`).
- **Security & Secret Hygiene:** API keys and environment configurations managed strictly via `.env` files; Supabase JWT bearer tokens required on protected routes.
- **Experience Sanitization:** Memory reflection pipelines must extract generalized conceptual strategies, filtering transient operational noise or sensitive tokens.
- **Token & Context Efficiency:** Retrieval must inject only top-$k$ relevant and reliable experiences to minimize token consumption and prevent context distraction.

---

## 5. Scope Constraints & Deliberate Non-Goals

- **No LLM Fine-Tuning / Retraining:** Model weights remain completely unmodified; all adaptation is external and driven by persistent memory.
- **No Raw Chat History Dumps:** The experience store retains structured lessons and operational strategies, not unstructured conversational transcripts.
- **No Heavy Production SDK During OJT:** An external Python SDK is explored as a potential productization direction, but the primary OJT deliverable is the core experience-memory system.
- **No Multi-Tenant Enterprise Isolation:** System focuses on single-evaluator and research team workflows; complex enterprise multi-tenancy is out of scope.
- **No Multi-Provider Routing Complexity:** Initial implementation focuses on one primary provider via LiteLLM (Groq / Ollama) rather than dynamic multi-LLM broker routing.

---

## 6. Future Technical Extensions

- **Experience Clustering & Consolidation:** Periodic offline background jobs using `pgvector` distance thresholds (e.g., cosine distance $< 0.10$) to merge duplicate memories and prune redundant clusters.
- **Domain-Specific Memory Namespaces:** Partitioning experience stores by domain (`research`, `coding`, `analysis`, `planning`) for targeted retrieval optimization.
- **Standalone Reusable Client SDK:** Packaging the memory layer into an installable Python package (`pip install adaptive-memory`) for external agent integrations.
