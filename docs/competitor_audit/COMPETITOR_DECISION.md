# COMPETITOR DECISION: ARCHITECTURAL ADOPTION BLUEPRINT

This document records our binding architectural decisions for every capability audited across the 9 competitor repositories.

---

### Category 1: BUILD NOW (P0 — High Value, Low Complexity, Zero Research Risk)

These improvements immediately strengthen our repository stability and product utility without altering experimental validity:

1. **Context Token Clamping (`Letta-Code: memory-constraints.ts`)**
   - **Action:** Enforce strict character and token limits on $\sigma$ ($\le 200$ tokens) and $\pi$ ($\le 100$ tokens) in `execute_node.py`.
   - **Why:** Prevents system prompt bloat and eliminates attention-degradation confounds across small foundation models.
2. **Benchmark State Machine & Checkpointing (`Zep: checkpoint.py`)**
   - **Action:** Add JSON state checkpointing to all benchmark evaluation runners.
   - **Why:** Guarantees trial resumability across long-running benchmark campaigns (Phase 9) without data loss from API rate limits.
3. **Multi-Tenant Scoping (`Mem0: Memory.add()`)**
   - **Action:** Add `tenant_id`, `agent_id`, and `session_id` columns to `models/experience.py` and the PostgreSQL schema (defaulting to `default` for research trials).
   - **Why:** Essential prerequisite for any multi-agent or multi-user production deployment.

---

### Category 2: BUILD LATER (P1 — High Product Utility, Moderate Complexity)

Planned for post-Phase 8 productization:

1. **Hybrid Lexical + Dense Retrieval (`Mem0: scoring.py`)**
   - **Action:** Implement a `HybridRetriever` abstraction blending BM25 with `pgvector` dense cosine similarity for the product REST API.
   - **Why:** Significantly improves developer experience on technical and coding queries where exact token matches are critical.
2. **Asynchronous Post-Turn Reflection (`Letta-Code: memory-worker.ts`)**
   - **Action:** In the FastAPI service, return the execution response $y$ immediately after `evaluate_node`, delegating `reflect_node` and `trust_node` to background workers.
   - **Why:** Cuts interactive user response latency by 4–8 seconds.
3. **Execution Plan Sealing (`Trajectory-IR: MASTER_SPECIFICATION.md`)**
   - **Action:** Record `sealed_plan` in `AgentState` before tool invocation to ensure at-most-once execution on crash resume.
   - **Why:** Prevents duplicate tool mutations during network disconnects.
4. **Offline Memory Bank Deduplication Sweep (`MemPalace: dedup.py`)**
   - **Action:** Provide a CLI utility `python -m ai_service.tools.dedup` to cluster near-identical experiences and prune redundant entries.
   - **Why:** Routine maintenance tool for keeping vector stores compact.

---

### Category 3: RESEARCH ABLATION (Phase 9 Experimental Conditions Only)

These represent compelling scientific hypotheses that must be evaluated as controlled ablations against the frozen A-EMA baseline:

1. **Ablation Condition A1: A-EMA + Hybrid Lexical Retrieval**
   - **Hypothesis:** Does blending BM25 lexical relevance with dense semantic similarity accelerate recovery from negative transfer, or does it increase false retrievals of superficial keyword matches?
2. **Ablation Condition A2: A-EMA + Active Contradiction Quarantine (`Graphiti`)**
   - **Hypothesis:** Does immediate contradiction-based quarantine ($S(t+1)=0.0$) outperform passive geometric decay ($t^*=3$) in dynamic environments with high factual churn?
3. **Ablation Condition A3: Multi-Trajectory Induction (`ExpeL`)**
   - **Hypothesis:** Does offline cross-trajectory clustering improve transfer generalizability compared to single-trajectory atomic 7-tuples?

---

### Category 4: DO NOT BUILD (Explicitly Rejected Non-Goals)

These ideas are formally rejected because they conflict with our core architecture, add unnecessary engineering bloat, or undermine our scientific contributions:

1. **In-Prompt Agent Self-Editing (`Letta / MemGPT`)**
   - **Reason:** Letta relies on the LLM to inspect and rewrite its own memory via tools. Research demonstrates that small edge models ($1.5\text{B}$–$7\text{B}$) suffer from meta-cognitive blindness and cannot reliably self-correct, directly inducing negative transfer loops. Our entire contribution is an **external, analytical, reliability-aware cognitive framework**.
2. **Full Temporal Knowledge Graph Engine (`Graphiti / Neo4j / Kuzu`)**
   - **Reason:** Our system is engineered for **procedural problem-solving strategies and pitfalls**, not general-purpose encyclopedic entity graphs. Adding a dual Neo4j/pgvector graph engine introduces massive operational overhead without addressing negative transfer in agent workflows.
3. **Full Distributed Durable Workflow Runtime (`Trajectory-IR / Temporal`)**
   - **Reason:** Operating a full Temporal cluster or DBOS server is excessive for our memory engine. Simple plan sealing within our LangGraph state delivers 90% of the crash-safety benefit with zero additional infrastructure.
4. **Unconstrained Additive Scoring (`Mem0: score_and_rank()`)**
   - **Reason:** Additive scoring without a hard safety cutoff ($\text{Score} = \text{Sim} + \text{BM25} + \text{Trust}$) is mathematically flawed: high semantic similarity ($\operatorname{Sim} \approx 0.95$) easily compensates for low empirical trust ($S \approx 0.20$), reviving harmful memories and causing negative transfer.
5. **Session-Bound Ephemeral Reflections (`Reflexion`)**
   - **Reason:** In-memory lists that reset on process termination defeat the primary objective of persistent cross-session experiential learning.
