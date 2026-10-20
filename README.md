# Adaptive AI Agent with Persistent Experience Memory (AEMA)

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178c6.svg)](https://www.typescriptlang.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/Vector_DB-pgvector_HNSW-336791.svg)](https://github.com/pgvector/pgvector)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen.svg)](.github/workflows/ci.yml)

<img width="2172" height="724" alt="aema logo" src="https://github.com/user-attachments/assets/b6a01f8f-ed7c-4af4-a6b5-47e116e40d2c" />


**GenAI OJT Capstone Project: Group G146**  
**Authors:** Kasat Sakshi Dattaprasad & Sumit Das  

---

## 1. Executive Summary

Autonomous AI agents powered by Large Language Models (LLMs) solve complex multi-step tasks with high proficiency. However, production deployments expose two critical architectural vulnerabilities:

1. **Experience Amnesia:** Foundational LLMs remain fundamentally stateless. Every new user session starts from scratch, unable to retain problem-solving discoveries, error recoveries, or operational lessons discovered in earlier runs.
2. **Negative Transfer (The "Relevant != Reliable" Fallacy):** Naive vector memory systems retrieve past context based solely on semantic cosine similarity. When an agent recalls flawed, outdated, or context-inappropriate advice, performance degrades severely, often compounding hallucinations and leading to catastrophic task failure.

**AEMA (Adaptive Experiential Memory Architecture)** solves this challenge externally **without fine-tuning, retraining, or modifying underlying LLM weights**. AEMA introduces a closed-loop experiential intelligence layer that:
- Distills operational problem-solving lessons into structured 3-tuples: `{"trigger", "strategy", "pitfall"}`.
- Tracks empirical reliability using an evidence-grounded **Asymmetric Exponential Moving Average (A-EMA)** trust score ($S \in [0.0, 1.0]$).
- Synthesizes bilateral prompt injections (positive strategies + negative constraints).
- Implements **Theorem 1 Deterministic Quarantine**, mathematically guaranteeing that corrupted or obsolete memories are permanently isolated within strictly 3 consecutive task failures.

---

## 2. Research Problem & Core Question

> **Under what conditions does persistent experience memory improve future task performance, and can reliability-aware memory selection reduce the harm caused by misleading or outdated experiences?**

### Key Research Contributions
- **Formalized A-EMA Trust Dynamic:** Mathematical framework modeling experiential trust where confidence is hard to earn but fast to lose.
- **Deterministic Quarantine Bound (Theorem 1):** Rigorous proof bounding poisoned memory isolation to at most $k^* = 3$ consecutive failures.
- **Bilateral Prompt Augmentation:** Explicit injection of negative behavioral boundaries (`Pitfall`) alongside affirmative guidance (`Strategy`), preventing recurring anti-patterns.
- **Deterministic Outcome Evaluation:** High-speed AST syntax and programmatic assertions replacing slow, non-deterministic LLM-as-a-judge evaluators at $0.00 token cost.

---

## 3. Mathematical Foundations & Formulations

### A. Asymmetric Exponential Moving Average (A-EMA) Trust Scoring
Trust $S_t \in [0.0, 1.0]$ tracks an experience's empirical reliability over repeated task executions with scalar reward $R_t \in [0.0, 1.0]$:

$$S_{t+1} = \begin{cases} \alpha S_t + (1 - \alpha) R_t & \text{if } R_t \ge 0.5 \quad (\text{Success climb with } \alpha = 0.85) \\ \beta S_t + (1 - \beta) R_t & \text{if } R_t < 0.5 \quad (\text{Aggressive failure penalty with } \beta = 0.70) \end{cases}$$

### B. Theorem 1: Deterministic Quarantine Bound
Let an active memory have initial trust $S_0 < 0.95$ and experience consecutive failures ($R_t = 0.0$). The trust score after $k$ steps is:

$$S_k = S_0 \cdot \beta^k$$

Setting the quarantine threshold to $\theta = 0.35$ with penalty factor $\beta = 0.70$:

$$k^* = \left\lceil \frac{\ln(\theta) - \ln(S_0)}{\ln(\beta)} \right\rceil \le \left\lceil \frac{\ln(0.35) - \ln(0.95)}{\ln(0.70)} \right\rceil = \lceil 2.798 \rceil = 3$$

> **Theorem 1 Guarantee:** Any memory experiencing consecutive zero-reward outcomes drops below the active threshold $\theta = 0.35$ in **strictly 3 steps**, automatically transitioning to `quarantined` status and eliminating negative transfer.

### C. Composite Retrieval Ranking
Candidate experiences are retrieved from PostgreSQL `pgvector` HNSW index and ranked by combining semantic relevance and historical trust:

$$\text{Score}_{\text{composite}} = 0.70 \times \text{CosineSimilarity} + 0.30 \times \text{TrustScore}$$

Experiences with $S < 0.35$ are excluded from active retrieval.

---

## 4. System Architecture

AEMA decouples the user-facing interface, backend API gateway, cognitive orchestration engine, and persistence layers into clean, modular tiers:

```mermaid
graph TD
    UI[React 18 + Tailwind Dashboard & 3D Core] -->|REST / JWT / SSE| GW[FastAPI Backend Gateway :8000]
    GW --> LG[LangGraph 5-Node StateGraph Engine]
    
    subgraph Cognitive Loop
        LG --> N1[1. retrieve_node: pgvector HNSW Query]
        N1 --> N2[2. execute_node: Bilateral Injection + Tools]
        N2 --> N3[3. evaluate_node: Deterministic AST Parser]
        N3 --> N4[4. reflect_node: 3-Tuple Distiller]
        N4 --> N5[5. trust_node: A-EMA Math & Theorem 1 Quarantine]
    end
    
    N2 --> LLM[Universal BYOK Gateway: Groq / Gemini / Ollama]
    N2 --> Tools[Tools: DuckDuckGo / Arxiv / Code Sandbox]
    N5 --> DB[(Supabase PostgreSQL 15 + pgvector / SQLite Fallback)]
```

### Cognitive Control Cycle

```text
User Task Input
     |
     v
[1. retrieve_node] -----> Top-k experiences retrieved (Composite: 0.70*Sim + 0.30*Trust)
     |
     v
[2. execute_node] ------> Multi-turn tool execution with Strategy + Pitfall constraints
     |
     v
[3. evaluate_node] -----> Deterministic outcome grading: emits scalar reward R in [0.0, 1.0]
     |
     v
[4. reflect_node] ------> Distills reusable 3-tuple: {Trigger, Strategy, Pitfall}
     |
     v
[5. trust_node] --------> A-EMA trust update; Theorem 1 quarantine if S < 0.35
     |
     v
Persistence Layer ------> Saves to pgvector HNSW index & appends to trust_history ledger
```

---

## 5. Key Implemented Features

### 1. Interactive 3D Neural Memory Core (`ThreeMemoryCore.tsx`)
- WebGL particle cluster visualizer built with Three.js.
- Real-time node coloring by trust state: **Emerald** ($S \ge 0.70$), **Amber** ($0.35 \le S < 0.70$), **Crimson** ($S < 0.35$).
- Interactive force layout clustering memories by domain (`research`, `coding`, `reasoning`, `general`).

### 2. Multi-Turn Execution Studio & Conversation Drawer
- Context-aware conversation threads with instant session resume.
- Collapsible sidebar drawer listing past sessions with turn counts and relative timestamps.
- Zero-leakage session isolation verified by automated integration tests.

### 3. Universal BYOK Model Gateway
- Ephemeral session-scoped key forwarding via LiteLLM.
- Multi-provider support: Groq Cloud (Llama-3.3-70B), Google Gemini 2.0 Flash, and local Ollama CPU models.
- Zero-retention security policy: credentials are never logged or persisted to database tables.

### 4. Zero-GPU Local Embedding Engine
- Local HuggingFace `sentence-transformers/all-MiniLM-L6-v2` generating 384-dimensional embeddings on CPU in $<15\text{ ms}$.
- Deterministic hash embedder fallback ensuring 100% test passage in lightweight or PyTorch-free environments.

### 5. Dual Persistence Engine
- Production: Supabase PostgreSQL 15 with `pgvector` HNSW cosine indexing and RPC stored procedures.
- Local / Test: SQLite3 with in-memory vector cosine similarity engine.

---

## 6. Empirical Benchmark Results

Evaluated across 100 complex multi-step reasoning, coding, and web research tasks:

| Performance Dimension | Baseline Agent (Memory OFF) | Naive Vector RAG (No Trust) | AEMA (Our Method) | Net Impact |
|---|---|---|---|---|
| **Task Success Rate** | 62.0% | 68.0% | **88.0%** | **+26.0% accuracy** |
| **Negative Transfer Rate** | N/A | 31.0% (Poisoned advice reused) | **0.0% (Quarantine enforced)** | **Zero negative transfer** |
| **Average Turns per Task** | 3.8 turns | 3.2 turns | **1.4 turns** | **-63.2% turn reduction** |
| **Average Tokens per Task** | 2,460 tokens | 2,150 tokens | **950 tokens** | **-61.4% token savings** |
| **Average Task Latency** | 4.85 seconds | 4.10 seconds | **1.92 seconds** | **-60.4% faster execution** |

---

## 7. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend Application** | React 18, Vite, TypeScript 5.5, Tailwind CSS, Three.js, Lucide Icons |
| **Backend API Gateway** | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, HTTPX |
| **Agent Orchestration** | LangGraph, LangChain Core (5-Node Cyclical StateGraph) |
| **Model Gateway (BYOK)** | LiteLLM (Groq Llama 3.3, Google Gemini 2.0 Flash, Local Ollama) |
| **Vector Storage & DB** | PostgreSQL 15 (Supabase), `pgvector` (HNSW indexing), SQLite3 |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` (384-dim) + Deterministic Hash Fallback |
| **Observability** | Structured JSON Logging (Loguru), LangSmith Tracing, Audit Ledgers |
| **Testing & CI/CD** | Pytest 8.x, Pytest-Asyncio, GitHub Actions, Vite Bundler |

---

## 8. Quick Start & Local Execution

### Prerequisites
- **Node.js** 18.0 or later
- **Python** 3.11 or later
- **Git**

---

### Method A: One-Command Unified Launcher (Recommended)

A single production launcher script manages dependencies, port safety, background processes, health readiness polling, and graceful termination:

```bash
# Clone the repository
git clone https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146.git
cd Adaptive-Agent-Memory-OJT-G146

# Launch full stack (FastAPI on :8000 + Vite on :5173)
chmod +x run_demo.sh
./run_demo.sh
```

Once running:
- **Frontend Dashboard:** [http://localhost:5173/dashboard?demo=true](http://localhost:5173/dashboard?demo=true)
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Shutdown:** Press `Ctrl+C` to terminate both services cleanly.

---

### Method B: Manual Step-by-Step Setup

#### 1. Backend Setup
```bash
# From repository root
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
pip install -r ../requirements-dev.txt

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
In a new terminal:
```bash
# From repository root
cd frontend

# Install Node modules
npm install

# Configure environment variables (or use default mock mode)
cp .env.example .env

# Launch Vite development server
npm run dev
```

---

## 9. Automated Testing & Verification Commands

AEMA includes a comprehensive test suite with 33 test modules covering mathematical invariants, cognitive loops, API contracts, and multi-turn session continuity.

### Run All Pytest Tests
```bash
# From repository root (with virtual environment active)
pytest tests/ -v --tb=short
```

### Targeted Test Suites

#### 1. Mathematical Invariant & Quarantine Tests (Theorem 1)
```bash
pytest tests/test_math_properties.py tests/test_failure_handling_and_quarantine.py -v
```

#### 2. Multi-Turn Conversation & Session Isolation Tests
```bash
pytest tests/test_conversations.py tests/test_api_agent.py -v
```

#### 3. Full Cognitive Loop & Lifecycle Verification
```bash
pytest tests/test_agent_graph.py tests/test_experiential_lifecycle_verification.py -v
```

#### 4. Deterministic Outcome Evaluator Tests
```bash
pytest tests/test_evaluator.py tests/test_evaluator_adversarial.py -v
```

#### 5. Health & Infrastructure Diagnostics
```bash
pytest tests/test_health.py tests/test_step1_infrastructure.py -v
```

---

### Frontend Verification & TypeScript Build
```bash
cd frontend

# Strict TypeScript typechecking
npx tsc -b

# Production asset compilation
npm run build
```

### Standalone TypeScript SDK Validation
```bash
cd packages/aema
npm install
npm test
```

---

## 10. Repository Documentation Index

Complete production-grade architectural and engineering documentation is maintained in the `docs/` directory:

| Document | Title | Focus Area |
|---|---|---|
| [01-project-overview.md](docs/01-project-overview.md) | Project Overview | Problem statement, core product flow, MVP scope, and non-goals. |
| [02-brd.md](docs/02-brd.md) | Business Requirements | Market gap, economic rationale, and target user personas. |
| [03-prd.md](docs/03-prd.md) | Product Requirements | Functional user stories, acceptance criteria, and priority matrix. |
| [04-ux-requirements.md](docs/04-ux-requirements.md) | UX Requirements | Screen flows, 3D visualizer interaction, and Conversation Drawer. |
| [05-trd.md](docs/05-trd.md) | Technical Requirements | Non-functional latency budgets, throughput, and stack selection. |
| [06-hld.md](docs/06-hld.md) | High-Level Design | End-to-end component topology, control loop, and network diagrams. |
| [07-database-design.md](docs/07-database-design.md) | Database Design | PostgreSQL pgvector schemas, HNSW parameters, and audit tables. |
| [08-api-specification.md](docs/08-api-specification.md) | API Specification | Complete RESTful endpoints, schemas, and session parameters. |
| [09-lld.md](docs/09-lld.md) | Low-Level Design | Node function signatures, AST parsers, and data models. |
| [10-genai-architecture.md](docs/10-genai-architecture.md) | GenAI Architecture | Prompt engineering, bilateral injection, and reflector distillation. |
| [11-security.md](docs/11-security.md) | Security & Guardrails | Key isolation, zero-retention policies, and sandbox safeguards. |
| [12-testing.md](docs/12-testing.md) | Testing Strategy | Pytest taxonomy, invariant testing, and adversarial test harness. |
| [13-cicd.md](docs/13-cicd.md) | CI/CD Pipeline | GitHub Actions workflow, quality gates, and automated test runs. |
| [14-observability.md](docs/14-observability.md) | Observability & Telemetry | Structured JSON logging, LangSmith tracing, and metrics. |
| [15-deployment.md](docs/15-deployment.md) | Deployment Architecture | Multi-environment topology, runner script, and zero-GPU strategy. |
| [16-cost-analysis.md](docs/16-cost-analysis.md) | Cost Analysis | Node token consumption, economic ROI (61.4% savings), and storage. |
| [17-roadmap.md](docs/17-roadmap.md) | 12-Week Roadmap | Milestone delivery logs, Definition of Done, and risk mitigations. |
| [18-team-responsibilities.md](docs/18-team-responsibilities.md) | Team Responsibilities | Engineering division between Kasat Sakshi Dattaprasad and Sumit Das. |
| [19-readme.md](docs/19-readme.md) | Documentation Guide | Master catalog and codebase structural roadmap. |
| [20-adrs.md](docs/20-adrs.md) | Architecture Decision Records | Formal ADRs detailing choices, alternatives, and trade-offs. |
| [21-traceability.md](docs/21-traceability.md) | Traceability Matrix | End-to-end mapping from business requirements to test cases. |

---

## 11. Team & Attribution

**GenAI / Agentic AI OJT Capstone: Group G146**

- **Kasat Sakshi Dattaprasad** ([@SakshiKasat18](https://github.com/SakshiKasat18)): Memory Intelligence, Asymmetric EMA Trust Engine, Vector Persistence Layer, Full-Stack Gateway Integration, System Governance & Documentation.
- **Sumit Das** ([@Sumit-ai-dev](https://github.com/Sumit-ai-dev)): Agent Orchestration, Cognitive Loop Execution, Universal BYOK Model Gateway, Deterministic Outcome Evaluator, Benchmark Suite.

---

## 12. License

This project is licensed under the MIT License: see the [LICENSE](LICENSE) file for details.
