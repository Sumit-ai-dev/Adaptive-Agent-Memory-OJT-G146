# Adaptive AI Agent with Persistent Experience Memory

**GenAI OJT Capstone Project — Group G146**

---

## Project Overview

**Adaptive AI Agent with Persistent Experience Memory** is an Agentic AI project exploring how an AI agent can retain, evaluate, and reuse operational problem-solving experience across repeated task executions.

While foundational Large Language Models (LLMs) solve individual tasks with high proficiency, multi-step agentic workflows reveal two critical vulnerabilities:
1. **Experience Amnesia:** A frozen model starts completely stateless in every new session, unable to recall prior problem-solving discoveries or avoid repeating past mistakes.
2. **Negative Transfer:** Naive retrieval of past conversational history often retrieves irrelevant context, flawed logic, or anti-patterns that degrade downstream task performance.

Our architecture solves this externally **without fine-tuning or modifying base LLM weights**. We introduce an external experience-memory intelligence layer that distills generalizable lessons (`{Trigger, Strategy, Pitfall}`), verifies empirical reliability using an evidence-based **Trust Score** ($S \in [0.0, 1.0]$), and dynamically augments prompts with verified strategies and negative constraints.

---

## Research Question

> **Under what conditions does persistent experience memory improve future task performance, and can reliability-aware memory selection reduce the harm caused by misleading or outdated experiences?**

---

## Core Idea

The agent operates across a closed-loop cognitive lifecycle:

```text
Task Input
    ↓
Retrieve Relevant Experiences (Composite Ranking: 0.70*Similarity + 0.30*Trust)
    ↓
Execute Task (Prompt augmented with positive Strategy + negative Pitfall)
    ↓
Evaluate Outcome (Deterministic scalar reward R ∈ [0.0, 1.0])
    ↓
Reflect & Extract Lesson (Structured 3-tuple: {Trigger, Strategy, Pitfall})
    ↓
Update Trust Score (Exponential Moving Average & Quarantine if S < 0.35)
    ↓
Persist to Vector Store (Supabase PostgreSQL + pgvector HNSW index)
    ↓
Reuse in Future Tasks
```

The system learns continuously from task execution without altering the underlying LLM. In this cognitive loop, experiences are not only retrieved based on semantic relevance; their empirical reliability is continuously scored and updated based on observed usefulness over time.

---

## Why This Project

Standard RAG architectures retrieve static document passages for factual question answering. However, autonomous agents require **Experience-RAG**: remembering *how* to solve problems, *which* tools to invoke, and *what mistakes to avoid*.

Key design principles:
- **Preserving Discoveries:** Useful problem-solving strategies must persist beyond an individual session boundary.
- **Relevance ≠ Reliability:** Just because a memory is semantically similar does not mean it was historically successful.
- **Active Quarantine:** Unreliable or outdated memories must decay and be isolated ($S < 0.35$) before they trigger negative transfer.

---

## Existing Work We Studied

We analyzed prior agent memory architectures to ground our research methodology:
- **Reflexion (Shinn et al., 2023):** Linguistic self-reflection within a single task episode, but lacked cross-session vector persistence and reliability decay.
- **Voyager (Wang et al., 2023):** Open-ended skill libraries in Minecraft, but assumed non-decaying deterministic code skills without negative constraint learning.
- **Generative Agents (Park et al., 2023) & MemoryBank:** Memory importance and recency decay for conversational personas, but did not focus on empirical task success reliability.
- **Mem0 / Zep / Letta:** Commercial memory stores focused on entity extraction and conversational key-value facts rather than structured strategy-pitfall pairs.
- **ExpeL (Zhao et al., 2024):** Highlighted the critical risk of negative transfer when agents blindly retrieve unverified past experiences.

Our architecture directly addresses the limitation identified in ExpeL by establishing an evidence-grounded **Trust Score ($S$)** and bilateral prompt augmentation (**positive strategies + negative pitfalls**).

---

## Key Implemented Features

### 1. Interactive 3D Neural Memory Core
- **Three.js Spatial Visualizer:** An interactive 3D particle graph (`ThreeMemoryCore.tsx`) rendering memory nodes clustered by domain and color-coded by trust score ($S \ge 0.70$ emerald, $0.35 \le S < 0.70$ amber, $S < 0.35$ crimson).
- **Domain Filtering:** Real-time exploration across `research`, `coding`, `reasoning`, and `general` domains.

### 2. Live Supabase Authentication & Session Management
- **GoTrue Engine:** Secure user registration, password hashing (bcrypt), and JWT session persistence.
- **Row-Level Security (RLS):** Database-level multi-tenant isolation ensuring users only access their own task runs and memories.

### 3. Central Agent Dashboard (`/dashboard`)
- **Telemetry Overview:** Real-time telemetry monitoring active memories, average trust scores, success rates, and execution latencies.
- **Task Runner:** Multi-line prompt input with domain selection and memory retrieval inspection.

### 4. FastAPI Backend Gateway & Deterministic Health Check
- High-performance asynchronous API gateway running on Uvicorn.
- Native `/api/v1/health` and `/health` endpoints with automated pytest verification.

---

## System Architecture

```text
React 18 Dashboard ──(HTTP / Bearer JWT)──► FastAPI Gateway (/api/v1)
                                                    │
                                                    ▼
                                           LangGraph StateGraph
                                       ┌────────────┴────────────┐
                                       ▼                         ▼
                            LiteLLM Gateway              Experience Engine
                     (Groq / Gemini / Ollama)       (PostgreSQL 15 + pgvector)
                                       │                         │
                                       ▼                         ▼
                                 External Tools            HNSW Vector Index
                             (DuckDuckGo / Reader)      (Composite Retrieval RPC)
```

Evaluation and observability operate across the execution pipeline via **LangSmith** and immutable PostgreSQL audit ledgers (`trust_history`).

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend / Client** | React 18, Vite, TypeScript, Tailwind CSS, Three.js, Lucide Icons |
| **Authentication** | Supabase Auth (GoTrue), JWT, Session Persistence |
| **Backend API Gateway** | Python 3.9+, FastAPI, Uvicorn, Pydantic v2 |
| **Agent Orchestration** | LangGraph, LangChain Core (5-Node StateGraph Engine) |
| **Model Gateway (BYOK)**| LiteLLM (Groq Llama-3.3, Google Gemini Flash, Local Ollama) |
| **Database & Vector Store**| PostgreSQL 15 (Supabase), pgvector (HNSW Indexing) |
| **Telemetry & Observability**| LangSmith Distributed Tracing, PostgreSQL Audit Tables, Loguru |
| **Testing & CI/CD** | pytest, pytest-asyncio, HTTPX, GitHub Actions |

---

## Quick Start & Local Setup

### Prerequisites
- **Node.js** 18.0 or later
- **Python** 3.9 or later
- **npm** 9.0 or later
- **Git**

---

### 1. Clone the Repository
```bash
git clone https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146.git
cd Adaptive-Agent-Memory-OJT-G146
```

---

### 2. Frontend Setup & Execution
1. Navigate to the frontend directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your Supabase credentials (or use the built-in mock fallback for instant offline preview):
   ```env
   VITE_SUPABASE_URL=https://your-project-ref.supabase.co
   VITE_SUPABASE_ANON_KEY=your-supabase-publishable-key
   VITE_API_URL=http://localhost:8000
   VITE_ENABLE_MOCK_FALLBACK=true
   ```

3. Launch the development server:
   ```bash
   npm run dev
   ```
   Open **`http://localhost:5173`** in your browser.

4. Verify type-checking and production build:
   ```bash
   npx tsc --noEmit
   npm run build
   ```

---

### 3. Backend Setup & Execution
1. In a separate terminal, navigate to the backend directory:
   ```bash
   cd backend
   ```

2. (Recommended) Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Interactive API documentation (Swagger UI) is available at **`http://localhost:8000/docs`**.

---

### 4. Running Automated Tests

From the repository root (return to root if currently in `backend/`):
```bash
# Return to the repository root if you are in the backend directory
cd ..

# Run the automated pytest suite:
python3 -m pytest tests/test_health.py -v
```


Expected output:
```text
tests/test_health.py::test_health_check_api_v1 PASSED
tests/test_health.py::test_health_check_root_alias PASSED
tests/test_health.py::test_root_endpoint PASSED
============================== 3 passed in 0.22s ===============================
```

---

## Team & Attribution

- **Kasat Sakshi Dattaprasad** ([@SakshiKasat18](https://github.com/SakshiKasat18))
- **Sumit Das** ([@Sumit-ai-dev](https://github.com/Sumit-ai-dev))

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
