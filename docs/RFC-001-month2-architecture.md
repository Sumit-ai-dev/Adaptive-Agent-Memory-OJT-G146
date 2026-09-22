# RFC-001: Month 2 Architecture & Implementation Proposal

* **Document ID:** RFC-001  
* **Title:** 5-Node Cyclical LangGraph Engine & Universal BYOK Multi-Model Gateway  
* **Author:** Sumit Das (`sumitds2005@gmail.com`)  
* **Reviewer / Co-Maintainer:** Kasat Sakshi Dattaprasad (`sakshisamu1809@gmail.com`)  
* **Created:** September 22, 2026  
* **Status:** **PROPOSED / READY FOR REVIEW**  
* **Target Sprint:** Month 2 (GenAI OJT Capstone — Group G146)  

---

## 1. Context & Motivation

In **Month 1**, we successfully built and verified:
1. The **React 18 + Vite Frontend Dashboard** with domain filtering, execution tracing, and telemetry analytics.
2. The **Supabase PostgreSQL 16 Schema** (`infrastructure/supabase/schema.sql`) with `pgvector` HNSW cosine indexing.
3. The baseline project structure, authentication flow, and initial state interfaces.

In **Month 2**, our goal is to build the **real Python AI backend and agent orchestration engine** that replaces the mock client simulator and wires the frontend directly into live LangGraph intelligence.

---

## 2. Core Architectural Pillars

### Pillar 1: Bring-Your-Own-Key (BYOK) Universal Multi-Provider Gateway
To ensure our project costs **$0.00** to run while giving complete flexibility to users:
* **Default Free Cloud:** **Groq Cloud** running `llama-3.3-70b-versatile` at 280 tokens/sec. Free API keys from `console.groq.com`.
* **Free Alternative:** **Google Gemini 2.0 Flash** via free keys from `aistudio.google.com`.
* **Free Offline Local:** **Local Ollama** (`http://localhost:11434`) running `llama3.2:3b` or `qwen2.5:3b` on Mac M1/M2/M3 without internet.
* **Commercial Models:** Users can provide their own **Claude 3.5 Sonnet** or **OpenAI GPT-4o** key in the UI. Keys are stored only in client `localStorage` and passed per-request.

### Pillar 2: 5-Node Cyclical LangGraph State Machine
Rather than an unstructured chain, the agent executes as a formal 5-node StateGraph:
```
  [retrieve_node] ──► [execute_node] ──► [evaluate_node]
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          │ steps >= 2                                │ steps == 1
                          ▼                                           ▼
                   [reflect_node]                              [trust_node]
                          │                                           │
                          └───────────────────► [trust_node] ────────► [END]
```

1. **`retrieve_node`:** Calculates composite score ($0.70 \times \text{Sim} + 0.30 \times \text{Trust}$). Filters candidates with $\text{Sim} \ge 0.70$ and $\text{Trust} \ge 0.35$.
2. **`execute_node`:** Injects the verified positive strategy plus the **Critical Negative Constraint (Pitfall)** into the system prompt. Dispatches LLM + DuckDuckGo search tool (max 4 turns).
3. **`evaluate_node`:** Deterministically inspects tool exit codes, Python AST parsing, and schema invariants to compute scalar reward $R_t \in [0.0, 1.0]$.
4. **`reflect_node`:** Distills reusable $\{\text{Trigger}, \text{Strategy}, \text{Pitfall}\}$ tuple when trajectory length $\ge 2$ steps. Enters quarantine as `status = 'candidate'`.
5. **`trust_node`:** Updates reliability score via Asymmetric EMA:
   * Success ($R \ge 0.8$): $S_{t+1} = 0.85 S_t + 0.15 \times 1.0$ (Steady climb)
   * Failure ($R \le 0.3$): $S_{t+1} = 0.70 S_t + 0.30 \times 0.0$ (Aggressive drop)
   * Prunes memory to `deprecated` if $S < 0.35$.
   * Promotes `candidate` to `active` if task evaluated positive.

---

## 3. Directory Layout & Planned Files

```
├── models/
│   ├── domain.py          # TaskDomain enum (research, coding, analysis, planning, general)
│   ├── provider.py        # ModelProvider enum & default configurations
│   ├── experience.py      # Experience 7-tuple schemas, match models, trust history
│   ├── task.py            # TaskExecuteRequest (with BYOK dynamic key), TaskExecuteResponse
│   └── state.py           # LangGraph AgentState TypedDict
│
├── ai-service/
│   ├── config.py          # Environment settings with fallback defaults
│   ├── llm_client.py      # Universal OpenAI-compatible + Anthropic async adapter
│   ├── tools/
│   │   ├── search.py      # DuckDuckGo search + Jina Reader free empirical research tool
│   │   └── evaluator.py   # Deterministic invariant evaluator (Reward R in [0, 1])
│   ├── nodes/
│   │   ├── retrieve_node.py # Composite retrieval & theta=0.35 cutoff
│   │   ├── execute_node.py  # System prompt strategy/pitfall injection & execution loop
│   │   ├── evaluate_node.py # Deterministic output invariant verification
│   │   ├── reflect_node.py  # Distills structured {Trigger, Strategy, Pitfall} tuples
│   │   └── trust_node.py    # Asymmetric EMA trust update & deprecation logging
│   └── graph.py           # 5-node cyclical LangGraph StateGraph builder
│
├── backend/
│   ├── database.py        # PostgreSQL pgvector repository + offline in-memory fallback
│   ├── main.py            # FastAPI entry point, CORS, lifespan, health checks
│   ├── requirements.txt   # Pinned backend dependencies
│   └── routes/
│       ├── agent.py       # POST /api/agent/execute (BYOK key parsing & LangGraph dispatch)
│       ├── memories.py    # GET /api/memories & POST /api/memories
│       └── telemetry.py   # GET /api/telemetry (Serves live React dashboard metrics)
│
└── tests/
    ├── test_agent_graph.py # Pytest for LangGraph 5-node cycle, EMA decay, Theorem 1 pruning
    └── test_api.py         # Pytest for FastAPI endpoints & BYOK header/body handling
```

---

## 4. Month 2 Milestone Schedule

| Milestone | Deliverable Description | Target Completion |
| :--- | :--- | :--- |
| **Milestone 2.1** | Pydantic v2 Models (`domain.py`, `experience.py`, `task.py`, `state.py`, `provider.py`) | Day 1–2 |
| **Milestone 2.2** | Universal Multi-Model Client (`llm_client.py`) & Search Tools (`search.py`, `evaluator.py`) | Day 3–4 |
| **Milestone 2.3** | 5 LangGraph Nodes & StateGraph Assembler (`nodes/` & `graph.py`) | Day 5–7 |
| **Milestone 2.4** | FastAPI Endpoints & Supabase Connector (`main.py`, `routes/`, `database.py`) | Day 8–10 |
| **Milestone 2.5** | Automated Tests (`pytest tests/`) & Live Frontend UI Integration | Day 11–12 |

---

## 5. Reviewer Sign-Off Checklist (For Sakshi)

Please review this proposal and check the boxes below or leave feedback in the review thread:

- [ ] **Data Model Alignment:** The Pydantic v2 schemas match `infrastructure/supabase/schema.sql` and the React frontend types in `frontend/src/types/index.ts`.
- [ ] **Multi-Model Strategy:** The BYOK approach (Groq / Gemini / Ollama / Claude) is sound, zero-cost, and developer-friendly.
- [ ] **LangGraph 5-Node Loop:** The cyclical structure (`retrieve` $\to$ `execute` $\to$ `evaluate` $\to$ `reflect` $\to$ `trust`) accurately represents the project lifecycle.
- [ ] **Trust & Pruning Dynamics:** The Asymmetric EMA formula and $0.35$ cutoff appropriately address negative transfer mitigation.
- [ ] **Ready for Implementation:** Approved to proceed with Milestone 2.1 coding.

---
*Questions or feedback? Reach out directly or open a review thread on this document.*
