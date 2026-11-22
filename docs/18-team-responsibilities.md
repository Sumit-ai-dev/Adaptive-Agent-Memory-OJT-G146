# Team Responsibilities

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Completed & Approved Team Governance (12-Week Capstone Defense)  

---

## Student 1: Sakshi Kasat (Memory Intelligence + Trust Engine + Full-Stack Gateway)

- **Requirements & System Governance:**
  - Lead author of BRD, PRD, TRD, API Specification, Database Design, and ADR architecture specifications.
  - Formulation of primary research questions, negative transfer problem definition, and quantitative evaluation criteria.
- **Memory Retrieval Engine (LangGraph Node 1: `retrieve_node`):**
  - Implementation of `retrieve_node` in `ai-service/nodes/retrieve_node.py`.
  - Composite retrieval ranking formula: $\text{Score} = 0.70 \times \text{Similarity} + 0.30 \times \text{TrustScore}$.
  - Vector embedding pipeline using HuggingFace `all-MiniLM-L6-v2` (384 dimensions, zero cloud cost) and fallback hash embedder.
  - Supabase PostgreSQL 15 + `pgvector` HNSW vector index optimization and `match_experiences` stored procedure (RPC), alongside local SQLite WAL store.
- **Trust Lifecycle Engine (LangGraph Node 5: `trust_node`):**
  - Implementation of `trust_node` in `ai-service/nodes/trust_node.py`.
  - Asymmetric Exponential Moving Average (A-EMA) trust engine: $\alpha = 0.85$ (success climb), $\beta = 0.70$ (failure penalty).
  - Formal proof and algorithmic implementation of Theorem 1: guarantees any poisoned memory with initial trust $S_0 < 0.95$ drops below quarantine threshold $\theta = 0.35$ in strictly $k^* = 3$ consecutive failures.
  - Active memory quarantine cutoff ($\theta < 0.35$): automatically transitions degraded memories to `status = 'quarantined'` to neutralize negative transfer.
  - Vector deduplication checks ($\text{distance} < 0.10$) before inserting new candidate lessons into PostgreSQL.
  - Immutable audit ledger writes to `public.trust_history`.
- **Backend API Gateway & Security:**
  - FastAPI asynchronous architecture (`backend/app/`, `backend/routes/`), `/api/v1` router aggregator, and CORS configuration.
  - Implementation of core endpoints: `POST /api/v1/agent/execute`, `POST /api/v1/agent/execute/stream`, `GET /api/v1/memories`, `GET /api/v1/conversations`, and `GET /api/v1/telemetry/stats`.
  - Pydantic v2 data models: `models/experience.py` (memory schemas) and joint review on `models/task.py`.
  - Authentication dependencies, Supabase JWT verification, and Row-Level Security (RLS) policies.
- **Production MCP Server (Model Context Protocol):**
  - Implementation of dual-transport MCP server supporting both Stdio and HTTP Server-Sent Events (SSE on Port 3001) in `scripts/mcp_server.py`.
  - Exposure of 5 standard MCP tools: `query_experience`, `record_experience`, `update_trust`, `get_system_status`, and `simulate_execution`.
  - Cross-platform process lifecycle and JSON-RPC protocol compliance.
- **Manifest V3 Chrome Extension:**
  - Engineering companion browser extension (`extension/`) adhering to Chrome Manifest V3 standards.
  - Background service worker, context menu text clipper for quick experience capture, and obsidian cognitive studio popup.
- **Documentation Architecture & Compliance:**
  - Maintenance of the 22-document technical documentation suite, repository index, and zero em-dash compliance enforcement.

---

## Student 2: Sumit Das (Agent Orchestration + Model Gateway + Benchmarks)

- **Month 1 Foundation Scaffolding:**
  - Initial Three.js 3D Neural Memory Core component (`ThreeMemoryCore.tsx`), Supabase OAuth integration, and baseline dashboard UI layout.
- **Cognitive Loop & Execution (LangGraph Node 2: `execute_node`):**
  - Implementation of `execute_node` in `ai-service/nodes/execute_node.py`.
  - Bilateral prompt synthesis: augmenting system instructions with affirmative **Strategies** and negative constraints (**Pitfalls**).
  - Multi-turn tool execution loop with strict circuit breakers (`max_turns = 4`).
  - Tool execution wrappers: DuckDuckGo web search, Jina AI reader, and sandboxed Python code execution.
- **Evaluation & Reflection (LangGraph Nodes 3 & 4: `evaluate_node` & `reflect_node`):**
  - Implementation of `evaluate_node` in `ai-service/nodes/evaluate_node.py`: deterministic outcome evaluation heuristics (tool exit codes, Python AST parsing, schema checks) emitting scalar reward $R_t \in [0.0, 1.0]$.
  - Implementation of `reflect_node` in `ai-service/nodes/reflect_node.py`: reflector prompt engineering to distill structured 3-tuples `{Trigger, Strategy, Pitfall}` from non-trivial trajectories ($\ge 2$ steps).
- **Universal BYOK Model Gateway:**
  - LiteLLM multi-provider adapter supporting Groq Cloud (`llama-3.3-70b-versatile`), Google Gemini 2.0 Flash, and local Ollama (`llama3.2:3b`) at $0.00 operational cost.
  - Session-based API key management (in-memory zero-storage policy).
- **Full-Stack Frontend & UI Engineering:**
  - Modern Obsidian design system, React 18 + Vite dashboard, and interactive Tailwind CSS styling.
  - Three.js 3D Neural Memory Core (`ThreeMemoryCore.tsx`) rendering spatial memory nodes clustered by domain and color-coded by trust score.
  - Conversational Execution Studio with multi-chat sidebar drawer, session persistence, thread rename, and deletion capabilities.
  - Live 5-node cognitive stepper console displaying real-time execution telemetry.
- **Dual SDK Streaming Parity:**
  - Full-parity real-time Server-Sent Events (SSE) streaming SDKs for TypeScript (`packages/aema`, `@sumitaidev/aema`) and Python (`aema`).
  - Asynchronous and synchronous iterator generators for token and node event streaming.
- **Benchmark Suite & Empirical Research:**
  - Benchmark test harness (`benchmarks/`): HotpotQA distractor setting, ALFWorld text simulation, and ToolBench API trap suite.
  - Ablation matrix execution (A: ReAct vs. B: Naive RAG vs. C: Reflexion vs. D: Ours), demonstrating a 91.0% pass rate under AEMA.
  - Telemetry logging, statistical verification of Theorem 1 bounds, and automated plot generation scripts (`plot_telemetry.py`).
  - Pydantic v2 models: `models/state.py` (`AgentState` TypedDict), `models/provider.py`, and joint review on `models/task.py`.

---

## Shared

- **System Architecture:** Joint authoring and review of HLD, LLD, and system architecture RFCs.
- **Data Contracts:** Joint review and validation of `models/task.py`, `models/experience.py`, and `models/domain.py`.
- **Quality Assurance & CI/CD:** Writing automated test suites (33 test modules across `pytest`, `vitest`, and TypeScript compiler checks), GitHub Actions workflows, and security guardrails.
- **Unified Industrial Runner:** Authoring and maintaining `./run_demo.sh` with process inspection, port conflict resolution, readiness polling, and landing page browser launch.
- **OJT Milestone Defenses & Viva:** Both team members understand the complete end-to-end architecture, mathematical equations, and code implementations, and are equally prepared to defend the capstone in technical viva examinations.

Both team members maintain a shared understanding of the entire system architecture, mathematical models, and implementation codebase.

