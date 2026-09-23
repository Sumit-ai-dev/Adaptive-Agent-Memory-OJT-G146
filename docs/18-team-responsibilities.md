# Team Responsibilities

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Approved Team Governance (Month 2 Specification)  

---

## Student 1 — Kasat Sakshi Dattaprasad (Memory Intelligence + Trust Engine + Full-Stack Gateway)

- **Requirements & System Governance:**
  - Lead author of BRD, PRD, TRD, API Specification, and Database Design specifications.
  - Definition of research question, problem formulation, and evaluation criteria.
- **Memory Retrieval Engine (LangGraph Node 1 — `retrieve_node`):**
  - Implementation of `retrieve_node` in `ai-service/nodes/retrieve_node.py`.
  - Composite retrieval ranking formula: $\text{Score} = 0.70 \times \text{Similarity} + 0.30 \times \text{TrustScore}$.
  - Vector embedding pipeline using HuggingFace `all-MiniLM-L6-v2` (384 dimensions, zero cloud cost).
  - Supabase PostgreSQL 15 + `pgvector` HNSW vector index optimization and `match_experiences` stored procedure (RPC).
- **Trust Lifecycle Engine (LangGraph Node 5 — `trust_node`):**
  - Implementation of `trust_node` in `ai-service/nodes/trust_node.py`.
  - Asymmetric Exponential Moving Average (A-EMA) trust engine: $\alpha = 0.85$ (success climb), $\beta = 0.70$ (failure penalty).
  - Active memory quarantine cutoff ($\theta < 0.35$): automatically transitions degraded memories to `status = 'deprecated'` to neutralize negative transfer.
  - Vector deduplication checks ($\text{distance} < 0.10$) before inserting new candidate lessons into PostgreSQL.
  - Immutable audit ledger writes to `public.trust_history`.
- **Backend API Gateway & Contracts:**
  - FastAPI asynchronous architecture (`backend/app/`), `/api/v1` router, and CORS configuration.
  - Pydantic v2 data models: `models/experience.py` (memory schemas) and joint review on `models/task.py`.
  - Authentication dependencies, Supabase JWT verification, and Row-Level Security (RLS) policies.
- **Frontend Live Integration:**
  - Connecting the React 18 dashboard to live FastAPI streaming endpoints and task visualizer.
  - Real-time trust score telemetry updates and memory catalog exploration.

---

## Student 2 — Sumit Das (Agent Orchestration + Model Gateway + Benchmarks)

- **Month 1 Foundation Scaffolding:**
  - Initial Three.js 3D Neural Memory Core component (`ThreeMemoryCore.tsx`), Supabase OAuth integration, and baseline dashboard UI layout.
- **Cognitive Loop & Execution (LangGraph Node 2 — `execute_node`):**
  - Implementation of `execute_node` in `ai-service/nodes/execute_node.py`.
  - Bilateral prompt synthesis: augmenting system instructions with affirmative **Strategies** and negative constraints (**Pitfalls**).
  - Multi-turn tool execution loop with strict circuit breakers (`max_turns = 4`).
  - Tool execution wrappers: DuckDuckGo web search, Jina AI reader, and sandboxed Python code execution.
- **Evaluation & Reflection (LangGraph Nodes 3 & 4 — `evaluate_node` & `reflect_node`):**
  - Implementation of `evaluate_node` in `ai-service/nodes/evaluate_node.py`: deterministic outcome evaluation heuristics (tool exit codes, Python AST parsing, schema checks) emitting scalar reward $R_t \in [0.0, 1.0]$.
  - Implementation of `reflect_node` in `ai-service/nodes/reflect_node.py`: reflector prompt engineering to distill structured 3-tuples `{Trigger, Strategy, Pitfall}` from non-trivial trajectories ($\ge 2$ steps).
- **Universal BYOK Model Gateway:**
  - LiteLLM multi-provider adapter supporting Groq Cloud (`llama-3.3-70b-versatile`), Google Gemini 2.0 Flash, and local Ollama (`llama3.2:3b`) at $0.00 operational cost.
  - Session-based API key management (in-memory zero-storage policy).
- **Benchmark Suite & Empirical Research:**
  - Benchmark test harness (`benchmarks/`): HotpotQA distractor setting, ALFWorld text simulation, and ToolBench API trap suite.
  - Ablation matrix execution (A: ReAct vs. B: Naive RAG vs. C: Reflexion vs. D: Ours).
  - Telemetry logging and automated plot generation scripts (`plot_telemetry.py`).
  - Pydantic v2 models: `models/state.py` (`AgentState` TypedDict), `models/provider.py`, and joint review on `models/task.py`.

---

## Shared

- **System Architecture:** Joint authoring and review of HLD, LLD, and RFC-001.
- **Data Contracts:** Joint review and validation of `models/task.py` and `models/domain.py`.
- **Quality Assurance & CI/CD:** Writing automated test suites (`pytest`), GitHub Actions workflows, and security guardrails.
- **OJT Milestone Defenses & Viva:** Both team members understand the complete end-to-end architecture, mathematical equations, and code implementations, and are equally prepared to defend the capstone in technical viva examinations.

Both team members maintain a shared understanding of the entire system architecture, mathematical models, and implementation codebase.

