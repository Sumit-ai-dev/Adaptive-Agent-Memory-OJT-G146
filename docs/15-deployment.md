# Deployment Architecture & Operational Guide

**Project:** Adaptive AI Agent with Persistent Experience Memory (AEMA)  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Implemented & Operational  

---

## 1. Environment Topology

The AEMA platform supports an agile deployment continuum spanning local workstations to cloud-hosted environments:

```text
+-----------------------+     +------------------------+     +------------------------+
|   Local Development   | --> |  Continuous Integration | --> | Staging / Evaluation   |
| (Vite:5173, Uvi:8000) |     |  (GitHub Actions CI)   |     | (Demo & Viva Defense)  |
+-----------------------+     +------------------------+     +------------------------+
```

### Environment Breakdown

| Environment | Host / Runtime | Ports | Primary Purpose |
|---|---|---|---|
| **Local Development** | macOS / Linux / WSL2 Workstations | Frontend: 5173<br>Backend: 8000 | Feature iteration, interactive visual testing, live debugging. |
| **CI / Automated Test** | GitHub Actions Ubuntu Runner | N/A (headless) | Strict pull-request gates, type checking, unit and regression tests. |
| **Staging / Evaluation** | Unified Local Runner or Cloud VM | Frontend: 5173<br>Backend: 8000 | Capstone demonstration, benchmark evaluations, viva review. |

---

## 2. Deployed System Architecture

```text
[ Browser / Client ] 
        |
        | HTTP (JSON / SSE)
        v
+--------------------------------------------------------------+
| Frontend Layer (Port 5173)                                   |
| - React 18 + TypeScript + Vite Single Page Application      |
| - Tailwind CSS & Three.js 3D Neural Memory Visualizer        |
| - Mock Fallback Provider for zero-dependency offline mode   |
+--------------------------------------------------------------+
        |
        | HTTP REST / Bearer JWT (CORS enabled)
        v
+--------------------------------------------------------------+
| Backend Gateway Layer (Port 8000)                            |
| - FastAPI High-Performance Asynchronous Web Server (Uvicorn) |
| - Endpoints: /api/v1/agent, /api/v1/memories, /api/health    |
| - Session-Scoped BYOK Header Forwarding                     |
+--------------------------------------------------------------+
        |
        | In-Process Async Invocation
        v
+--------------------------------------------------------------+
| AI Cognitive Engine (ai-service/)                            |
| - LangGraph 5-Node Cyclical StateGraph                       |
|   (Retrieve -> Execute -> Evaluate -> Reflect -> Trust)      |
| - LiteLLM Multi-Provider Gateway (Groq, Gemini, Ollama)      |
| - Local Embedding Engine (all-MiniLM-L6-v2 / Hash Fallback)  |
+--------------------------------------------------------------+
        |
        | SQL / Vector RPC
        v
+--------------------------------------------------------------+
| Persistence Layer                                            |
| - Primary: Supabase PostgreSQL 15 + pgvector (HNSW Index)    |
| - Local Fallback: SQLite3 + In-Memory Cosine Similarity Engine|
| - Tables: experiences, task_executions, trust_history, msgs   |
+--------------------------------------------------------------+
```

---

## 3. Unified Demo Launcher (`./run_demo.sh`)

A single production-grade bash script automates full-stack startup with industrial safety guarantees:

```bash
# Make executable and launch:
chmod +x run_demo.sh
./run_demo.sh
```

### Automation & Safety Capabilities
1. **Repository Auto-Resolution:** Automatically detects repository root path regardless of where the command is invoked.
2. **Virtual Environment Validation:** Verifies existence of `backend/venv/bin/uvicorn` and instructs developer on setup if missing.
3. **Frontend Dependency Resolution:** Auto-runs `npm install` if `node_modules` is absent.
4. **Non-Destructive Port Cleanup:**
   - Inspects TCP ports `8000` and `5173`.
   - Specifically checks command line process names. Only stops prior AEMA processes (`backend.main:app`, `vite`).
   - Aborts with an informative error if an unrelated third-party process occupies the port, protecting developer workloads.
5. **FastAPI Readiness Health Polling:** Actively polls `http://localhost:8000/api/health` with a 20-second timeout before starting the frontend.
6. **Graceful Process Lifecycle Cleanup:** Traps `SIGINT`, `SIGTERM`, and `EXIT` signals to terminate child processes cleanly without orphaned daemons.

---

## 4. Zero-GPU Constraint Strategy

Because dedicated GPU infrastructure is an explicit capstone constraint, AEMA is architected from the ground up for CPU-native and hosted API efficiency:

1. **No LLM Fine-Tuning or Weight Training:** All agent adaptability is externalized into the persistent experiential memory substrate.
2. **CPU-Optimized Embeddings:** Local embedding uses HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). Typical CPU inference takes under 15ms per query without requiring CUDA or Metal acceleration.
3. **Deterministic Fallback Embedder:** When `sentence-transformers` is unavailable, AEMA switches to a lightweight hash embedder with zero PyTorch dependencies.
4. **Hosted BYOK Model Execution:** High-parameter model reasoning is delegated to zero-cost or pay-per-token hosted inference providers (Groq LPUs for Llama-3.3-70B, Google Gemini 2.0 Flash) or quantized local models via Ollama CPU.
5. **Provider-Agnostic Abstraction:** LiteLLM abstraction layer allows hot-swapping model backends through environment variables without rewriting agent code.

---

## 5. Environment Configuration

### Backend Environment Configuration (`backend/.env` or root `.env`)
```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO

# Persistence Configuration
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
# Fallback to local SQLite when DATABASE_URL is omitted:
# DATABASE_URL=sqlite:///./adaptive_agent.db

# Vector Index Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384
SIMILARITY_THRESHOLD=0.65

# Model Provider Keys (Optional: Can also be supplied via frontend BYOK header)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...

# Observability (Optional)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=lsv2_...
```

### Frontend Environment Configuration (`frontend/.env`)
```bash
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://[PROJECT_REF].supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_ENABLE_MOCK_FALLBACK=true
```

---

## 6. Rollback & Fault Tolerance

1. **Reversible Migrations:** Database migrations in `migrations/` follow forward-compatible declarative schemas.
2. **Immutable Audit Trails:** Trust score mutations write appending rows to `trust_history`. State transitions can be replayed or rolled back mathematically.
3. **Graceful Persistence Fallback:** If PostgreSQL becomes unreachable, the agent automatically falls back to in-memory local caching, logging a warning while preserving task execution.
4. **Memory Quarantine Isolation:** Flawed or corrupted memories are isolated within 3 task failures via Theorem 1 deterministic quarantine, preventing systemic failure propagation without requiring manual rollback.
