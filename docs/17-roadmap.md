# 12-Week Project Roadmap & Delivery Log

**Project:** Adaptive AI Agent with Persistent Experience Memory (AEMA)  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Completed & Validated across 12-Week Milestones  

---

## 1. 12-Week Milestone Schedule

The project roadmap was structured across six distinct 2-week engineering phases:

| Phase | Weeks | Phase Name | Planned Deliverables | Status |
|---|---:|---|---|---|
| **Phase 1** | Weeks 1-2 | Problem Formulation & Literature Review | Problem validation, study of prior memory systems (Reflexion, ExpeL, Voyager), BRD, PRD, UX mockups. | Completed |
| **Phase 2** | Weeks 3-4 | Architecture & Mathematical Foundations | TRD, HLD, Database schema, formalization of Asymmetric EMA trust mathematics and Theorem 1 deterministic quarantine proof. | Completed |
| **Phase 3** | Weeks 5-6 | Core AI Service & Memory Subsystem | LangGraph 5-node StateGraph engine, local `all-MiniLM-L6-v2` embeddings, Supabase PostgreSQL pgvector HNSW index, SQLite fallback. | Completed |
| **Phase 4** | Weeks 7-8 | Cognitive Loop, Evaluation & BYOK Gateway | Deterministic evaluation heuristics (`evaluate_node`), structured reflection distillation (`reflect_node`), LiteLLM BYOK gateway (Groq, Gemini, Ollama). | Completed |
| **Phase 5** | Weeks 9-10 | Full-Stack Integration & Interactive Dashboard | React 18 + Vite frontend, Three.js 3D Neural Memory Core, Execution Studio with conversation history drawer, live telemetry streaming. | Completed |
| **Phase 6** | Weeks 11-12 | Verification, Benchmarks, CI/CD & Viva Readiness | 33 automated test suites, GitHub Actions CI pipeline, empirical benchmark evaluation (HotpotQA, HumanEval), unified demo runner (`run_demo.sh`), final viva preparation. | Completed |

---

## 2. Definition of Done (DoD)

A feature or milestone is defined as complete only when it satisfies all of the following seven criteria:

1. **Implementation:** Fully coded and adhering to clean architectural boundaries between the API gateway, LangGraph state machine, and storage layers.
2. **Automated Testing:** Accompanied by automated unit and regression tests passing with 100% success rate across pytest and vitest.
3. **Algorithmic Invariants:** Mathematical properties (e.g., trust bounds in $[0.0, 1.0]$, quarantine transition within 3 failures) formally asserted in test suites.
4. **Clean Compilation:** Strict TypeScript checking (`tsc -b`) and asset bundling (`vite build`) complete with zero errors.
5. **Documentation & Traceability:** Requirements traceable in `docs/21-traceability.md`, architecture documented in ADRs, and zero em-dash compliance verified.
6. **Security & Guardrails:** Zero exposed credentials or secrets; session-scoped BYOK keys cleared from memory immediately following task execution.
7. **Demonstrable:** Verifiable end-to-end within the live application via the unified demo runner script (`./run_demo.sh`).

---

## 3. Phase-by-Phase Deliverable Log

### Month 1: Foundation, Mathematics & Core Engine (Weeks 1-6)
- **Literature Review & Gap Identification:** Identified critical vulnerability in existing agents (negative transfer from unverified memories).
- **Mathematical Formalization:** Defined Asymmetric Exponential Moving Average (A-EMA) trust dynamic with conservative climb ($\alpha = 0.85$) and aggressive penalty ($\beta = 0.70$).
- **Theorem 1 Proof:** Mathematically proved that any poisoned memory with initial trust $S_0 < 0.95$ drops below quarantine threshold $\theta = 0.35$ in strictly $k^* = 3$ consecutive failures.
- **StateGraph Scaffolding:** Built 5-node LangGraph cyclic workflow in `ai-service/` with typed `AgentState`.
- **Vector Persistence:** Engineered Supabase PostgreSQL schema with `pgvector` HNSW indexing and `match_experiences` cosine similarity RPC.

### Month 2: Full-Stack Integration, Execution Studio & Hardening (Weeks 7-12)
- **Deterministic Outcome Evaluator:** Replaced slow LLM judges with deterministic code execution checks, syntax validation, and heuristic rewards.
- **Execution Studio & Conversation History:** Implemented persistent conversation threads, sidebar drawer, and session resume capabilities.
- **Interactive 3D Visualizer:** Three.js spatial graph rendering memory nodes color-coded by trust score ($S \ge 0.70$ emerald, $0.35 \le S < 0.70$ amber, $S < 0.35$ crimson).
- **Industrial Runner Script:** Created `./run_demo.sh` with process inspection, port conflict resolution, readiness polling, and graceful signal handling.
- **Continuous Integration Pipeline:** Configured GitHub Actions `.github/workflows/ci.yml` supporting offline caching, model fallbacks, and multi-job parallel checks.

---

## 4. Technical Pivot & Risk Mitigation Log

| Risk / Challenge | Potential Impact | Engineering Resolution |
|---|---|---|
| **HuggingFace Dependency Bloat in CI** | 2 GB PyTorch download causing CI timeouts (>15 mins). | Implemented intelligent cache layer and developed a deterministic hash embedder fallback that allows 100% test passage in zero-PyTorch environments. |
| **Flawed Memory Poisoning (Negative Transfer)** | Agent degrades in performance after encountering wrong advice. | Implemented Theorem 1 deterministic quarantine ($k^* = 3$) and composite ranking ($0.70 \times \text{Similarity} + 0.30 \times \text{Trust}$), guaranteeing poisoned memories are isolated immediately. |
| **Third-Party LLM Downtime & Quotas** | Broken agent during viva evaluation if an API key expires. | Built LiteLLM multi-provider gateway supporting Groq Llama 3.3, Google Gemini Flash, and local Ollama, coupled with an offline mock mode. |
| **Port Conflicts during Local Startup** | Startup failure if port 8000 or 5173 is already bound. | Added non-destructive process inspection in `run_demo.sh` that terminates stale AEMA processes while protecting unrelated user applications. |
