# Technical Requirements Document (TRD)

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146  
**Track:** Generative AI / Agentic AI  

---

## 1. Proposed Architecture

- **Client / Access Layer:**
  - **Central Dashboard:** React, TypeScript, Tailwind CSS
  - **Browser Extension:** TypeScript, Chrome Extension Manifest V3
- **Backend / API Layer:** Python, FastAPI, Pydantic
- **Agent / Intelligence Layer:** Python (custom lightweight agent orchestration; no heavy frameworks)
- **LLM & Embeddings:** OpenAI API (primary provider with abstract interface boundary), OpenAI Embeddings
- **Persistence & Vector Layer:** PostgreSQL + `pgvector`, SQLAlchemy (ORM), Alembic (database migrations)
- **Testing & Evaluation:** `pytest`, Python evaluation scripts, `matplotlib` (offline visualization)
- **Infrastructure & Tooling:** Docker, GitHub Actions (CI), Python structured application logging

```text
Dashboard (React + TS) ────────┐
                               │
                               ↓
                        FastAPI (Python)
                               ↓
                      Python Agent Engine
                               ↓
                    Retrieval + LLM + Tools
                               ↓
                    Reflection / Validation
                               ↓
                   Experience + Trust Update
                               ↓
                     PostgreSQL + pgvector
                               ↑
                               │
Browser Extension (Chrome MV3) ┘
```

---

## 2. Technology Rationale

### React, TypeScript & Tailwind CSS (Dashboard)
- **Role:** Web-based central interface for submitting tasks, inspecting agent traces, browsing accumulated experiences, and visualizing reliability trends over time.
- **Rationale:** React provides a responsive, component-driven UI; TypeScript ensures strict type safety across complex data objects (e.g., experiences, execution traces, evaluation metrics); Tailwind CSS enables a clean, modern dashboard design without UI bloat.

### Chrome Extension Manifest V3 (Browser Extension)
- **Role:** Optional lightweight web companion allowing users to invoke the agent and access persistent experience memory directly from browser workflows.
- **Rationale:** Manifest V3 complies with modern browser security and lifecycle standards while connecting to the same centralized FastAPI backend.

### Python & FastAPI (Backend / API Layer)
- **Role:** Application API layer exposing endpoints for task execution, experience retrieval, evaluation runs, and dashboard data.
- **Rationale:** Python is the standard language for GenAI and data workflows. FastAPI provides high performance, native async support, and automatic OpenAPI schema generation with Pydantic type validation.

### Custom Lightweight Agent Orchestration (Python)
- **Role:** Coordinates the core execution loop: retrieving past experiences, augmenting LLM prompts, invoking tools, evaluating outcomes, extracting lessons, and updating trust scores.
- **Rationale:** Heavy orchestration frameworks like LangChain or LangGraph introduce opaque abstractions. A clean, custom Python orchestration layer ensures that research logic (memory retrieval, reflection, trust updates) remains transparent, explicit, and easy to evaluate.

### OpenAI API (LLM & Embeddings)
- **Role:** Provides underlying language understanding, task execution, reflection, and semantic embedding generation.
- **Rationale:** Offers reliable reasoning capabilities and stable embedding generation. An abstract internal LLM interface is maintained to avoid rigid vendor lock-in without introducing the overhead of multi-provider adapter platforms during the MVP phase.

### PostgreSQL + pgvector (Persistence Layer)
- **Role:** Unified persistent storage for structured application entities (tasks, executions, evaluations) and vector embeddings for semantic experience retrieval.
- **Rationale:** The experience memory system is not merely a vector database. An experience contains rich structured metadata (lesson, context, provenance, confidence, usage counters, trust score, lifecycle state) alongside its vector embedding. PostgreSQL with `pgvector` enables combined relational filtering, transactional integrity, and vector similarity search within a single reliable engine.

### SQLAlchemy & Alembic (ORM & Migrations)
- **Role:** Database object-relational mapping and schema version control.
- **Rationale:** SQLAlchemy provides type-annotated domain model mapping in Python, while Alembic guarantees reproducible, version-controlled schema migrations across development and evaluation environments.

### Pytest, Evaluation Scripts & Matplotlib (Testing & Evaluation)
- **Role:** Unit testing, component integration verification, offline batch evaluation experiments, and benchmark plotting.
- **Rationale:** `pytest` verifies system correctness; dedicated Python scripts run controlled test suites comparing Memory OFF vs. Memory ON conditions; `matplotlib` generates comparative performance charts.

### Docker & GitHub Actions (Infrastructure & CI)
- **Role:** Containerization of services and automated testing/linting pipelines.
- **Rationale:** Docker ensures identical execution environments across local development and evaluation setups; GitHub Actions automates test execution and code quality checks on every push.

---

## 3. Technical Requirements

| ID | Requirement | Description | Maps to |
| :--- | :--- | :--- | :--- |
| **TR-001** | Versioned RESTful API | FastAPI endpoints for task execution, experience querying, lifecycle updates, and evaluation runs. | US-001, US-008 |
| **TR-002** | Dual Client Support | Central React web dashboard and Chrome MV3 extension consuming the same backend API. | US-001, US-009 |
| **TR-003** | Abstract LLM Boundary | Internal provider abstraction for prompt execution and embedding generation, keeping the underlying model fixed during experiments. | US-001, US-003 |
| **TR-004** | Explicit Agent Orchestration | Deterministic execution pipeline managing retrieval, prompt construction, tool execution, and response synthesis. | US-001, US-002 |
| **TR-005** | Hybrid Memory Persistence | PostgreSQL schema storing structured experience metadata, provenance, usage history, and `pgvector` embeddings. | US-002, US-006 |
| **TR-006** | Relevance & Reliability Retrieval | Query engine combining vector similarity with reliability/trust scoring to rank candidate experiences. | US-002, US-005 |
| **TR-007** | Post-Execution Reflection | Reflection module distilling concise, reusable strategies and operational lessons from completed task runs. | US-003 |
| **TR-008** | Outcome Evaluation Module | Automated evaluation component assessing task success, quality scores, and attributing outcomes to reused experiences. | US-004 |
| **TR-009** | Trust & Reliability Tracker | Dynamic score adjustment algorithm updating experience trust values based on observed positive/negative reuse. | US-005 |
| **TR-010** | Experience Lifecycle Controller | State machine managing experience status (`CREATED`, `ACTIVE`, `DEPRECATED`) and filtering obsolete records from retrieval. | US-006 |
| **TR-011** | Controlled Evaluation Harness | Automated offline test runner executing identical task suites across Memory OFF vs. Memory ON conditions. | US-007 |
| **TR-012** | Structured Execution Tracing | Application-level logging capturing execution steps, retrieved experiences, evaluation outputs, and state transitions. | US-001, US-008 |

---

## 4. Non-Functional Requirements (NFR Targets)

- **Research Control & Reproducibility:** The underlying LLM model and prompt baselines must remain fixed across benchmark evaluations to ensure valid attribution of performance gains to the memory subsystem.
- **API Latency:** Non-LLM backend operations (retrieval ranking, trust score updates, database reads/writes) target p95 < 200 ms.
- **Deterministic Evaluation:** Batch evaluation runs must produce consistent, reproducible scoring logs and exportable result sets.
- **Modularity & Maintainability:** Strict layer separation between API routing, agent orchestration, memory lifecycle logic, and database persistence.
- **Security & Secret Hygiene:** API keys and environment configurations managed strictly through environment variables (`.env`), never committed to source control.
- **Experience Sanitization:** Memory extraction pipelines must filter sensitive or transient operational tokens, persisting only reusable conceptual lessons.
- **Cost & Token Efficiency:** Experience retrieval must limit injected context size (top-$k$ relevant items) to minimize token consumption and prevent context saturation.

---

## 5. Scope Constraints & Deliberate Non-Goals

- **No LLM Fine-Tuning / Retraining:** Model parameters remain completely unmodified; all adaptation is external and driven by persistent memory.
- **No Raw Chat History Dumps:** The experience store retains structured lessons and operational strategies, not unstructured conversational transcripts.
- **No Heavy Framework Lock-In:** Core agent, reflection, and trust logic implemented in clean Python without LangChain or LangGraph dependencies.
- **No Multi-LLM Platform Complexity:** Single fixed provider (OpenAI API) for initial research; multi-provider routing is out of scope for the MVP.
- **No Multi-Tenant SaaS Overhead:** System focused on single-user/evaluator research workflows; multi-tenant enterprise isolation is out of scope.

---

## 6. Future Technical Extensions

- **Modular Secondary LLM Adapters:** Support for alternative reasoning providers (e.g., Anthropic Claude, Google Gemini, or local open-weight models) via the abstract boundary.
- **Experience Clustering & Consolidation:** Periodic offline background jobs to merge duplicate experiences and prune redundant memory clusters.
- **Domain-Specific Memory Namespaces:** Partitioning experience stores by domain (e.g., research, coding, writing) for targeted retrieval optimization.
