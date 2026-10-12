# Final Pre-Implementation Audit: Internal System Reality & Competitor Gap Analysis

**Date:** October 8, 2026  
**Project:** Adaptive Agent Memory with Asymmetric Exponential Moving Average (`Adaptive-Agent-Memory-OJT-G146`)  
**Scope:** Exhaustive internal source code audit across 10 competitor-inspired features, memory security, lifecycle, provenance, failure modes, and research firewall boundaries.  
**Operating Constraint:** Audit and verification ONLY. No source code modifications, dependency installations, database migrations, or benchmark mutations permitted.

---

## 1. Current Architecture Reality

A rigorous, evidence-based code inspection was performed across the entire repository to uncover the true operational state of the product, ai-service, and benchmark runners.

| Subsystem Component | Documented Intent vs. Actual Source Code Reality | Exact File & Lines |
| :--- | :--- | :--- |
| **Active Product Database** | Documentation mentions Supabase/PostgreSQL with pgvector. **Reality:** The active runtime is strictly **local SQLite** (`SQLiteMemoryStore`). `SupabaseMemoryStore` is completely absent from the codebase despite being mentioned in docstrings. | [`ai-service/memory/store.py:L74-L128`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py#L74-L128)<br>[`backend/app/api/v1/agent.py:L21`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/api/v1/agent.py#L21) |
| **REST API vs Agent Store Discrepancy** | **Critical Architectural Inconsistency:** The Agent execution router (`/api/v1/agent/execute`) persists to SQLite (`data/adaptive_memory.db`). In contrast, the Memories REST router (`/api/v1/memories`) queries an in-memory dictionary (`MemoryDatabase`) seeded with 5 mock experiences! Web client list queries do not reflect agent-executed SQLite writes. | [`backend/app/api/v1/memories.py:L21-L24, L53`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/api/v1/memories.py#L21-L24)<br>[`backend/app/database.py:L11-L90`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/database.py#L11-L90) |
| **Execution State & Trace Persistence** | `TaskExecution` objects from live API calls are stored strictly in an in-memory Python list `_execution_history: List[TaskExecution] = []` capped at 100 items. Server restarts permanently wipe execution history. | [`backend/app/api/v1/agent.py:L24, L44-L46`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/api/v1/agent.py#L24) |
| **Current Memory Schema** | 7-Tuple representation: `(task_domain, trigger_condition, strategy_lesson, pitfall, confidence, trust_score, embedding)`. Stored in SQLite table `experiences` with `trust_history` audit ledger. Embeddings stored as raw JSON-serialized text strings. | [`models/experience.py:L28-L51`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/experience.py#L28-L51)<br>[`ai-service/memory/store.py:L93-L128`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py#L93-L128) |
| **Current Retrieval Implementation** | Dual-track retrieval: <br>1. **Benchmark Track:** `PolicyBackedRetriever` with `LegacyModeRanker` using clamped numpy cosine similarity over fixed `MemoryBank`.<br>2. **Product Track:** `MemoryRetriever` calling `SQLiteMemoryStore.search_similar()`, computing vectorized cosine similarity over all stored embeddings in numpy, applying $0.70 \times \text{Sim} + 0.30 \times \text{Trust}$, and filtering out $\text{Trust} < 0.35$ or $\text{Sim} < 0.70$. | [`ai-service/experiment/retrieval.py:L35-L105`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/experiment/retrieval.py#L35-L105)<br>[`ai-service/memory/retriever.py:L40-L129`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/retriever.py#L40-L129)<br>[`ai-service/nodes/retrieve_node.py:L37-L92`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/retrieve_node.py#L37-L92) |
| **Current Reflection Implementation** | Single-trajectory reflection node: takes prompt, output (first 400 chars), and scalar outcome $R \in [0.0, 1.0]$. Prompt LLM via JSON mode to extract `{trigger_condition, strategy_lesson, pitfall, confidence}`. Saves candidate experience with status `CANDIDATE`. | [`ai-service/nodes/reflect_node.py:L18-L74`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/reflect_node.py#L18-L74) |
| **Current Trust Persistence** | A-EMA parameters: $\alpha = 0.85$ (success $R \ge 0.80$), $\beta = 0.70$ (failure $R \le 0.30$), $\gamma = 0.80$ (neutral). Cutoff $\theta = 0.35$. F3 contract strictly guarantees 1 task-level update per exposed memory based on terminal attempt reward. Logged to `trust_history` table in SQLite. | [`ai-service/nodes/trust_node.py:L26-L59`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/trust_node.py#L26-L59)<br>[`ai-service/graph.py:L335-L359`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/graph.py#L335-L359) |
| **Current Tool Execution** | Exactly one active tool: `duckduckgo_search` (`SearchTool` in `tools/search.py`). Injected purely on keyword triggers (`"who"`, `"which"`, `"research"`) in `execute_node.py`. No general tool-use registry or plan-sealing harness. | [`ai-service/tools/search.py:L15-L78`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/tools/search.py#L15-L78)<br>[`ai-service/nodes/execute_node.py:L58-L72`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/execute_node.py#L58-L72) |
| **API Request Flow** | FastAPI router routes `/api/v1/agent/execute` $\to$ `execute_task()` $\to$ LangGraph 5-node StateGraph (`retrieve` $\to$ `execute` $\to$ `evaluate` $\to$ `reflect` $\to$ `trust` $\to$ `should_loop_or_finish`). Synchronous execution loop blocks until completion. | [`backend/app/main.py:L34-L37`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/main.py#L34-L37)<br>[`ai-service/graph.py:L53-L84, L204-L433`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/graph.py#L53-L84) |
| **Authentication & Authorization** | **Zero Authentication:** No JWT, Bearer tokens, or API key middleware exist on FastAPI endpoints. CORS is configured for localhost. Any caller can execute tasks or query memory. | [`backend/app/main.py:L21-L32`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/main.py#L21-L32) |
| **Provider / BYOK Handling** | BYOK passes via `TaskExecuteRequest.api_key`, mapped to `AgentState["api_key"]`, then into `ProviderConfig`. Resolved in `UniversalLLMClient` with LiteLLM or AsyncOpenAI fallback. If no BYOK key is provided, falls back to ambient environment variable (e.g. `GROQ_API_KEY`). | [`ai-service/llm_client.py:L49-L96, L125`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/llm_client.py#L49-L96)<br>[`models/task.py:L204`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/task.py#L204) |

---

## 2. Feature Gap Verification

Detailed inspection of the 10 competitor-inspired capabilities against our verified codebase.

---

### Feature 1: Context / Token Budgeting
1. **Current Implementation:** Partial token ceiling parameters exist on request (`max_tokens: Optional[int]` in `TaskExecuteRequest`) and are passed to LiteLLM.
2. **Exact File(s):** [`models/task.py:L212`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/task.py#L212), [`models/state.py:L27`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/state.py#L27), [`ai-service/nodes/execute_node.py:L35-76`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/execute_node.py#L35-76), [`ai-service/llm_client.py:L182, L199`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/llm_client.py#L182).
3. **Existing Behavior:** Memory injection into prompt concatenates positive strategy and negative pitfall strings directly into the system prompt. In addition, `search_res.get('output', '')` is appended to user input without length checks.
4. **Actual Gap:** No token budgeting exists for memory injection or retrieved memories. If retrieved lessons or tool outputs are large, they can consume the entire context window, starving the agent of reasoning space and causing context window overflow errors.
5. **Proposed Improvement:** Implement a prompt token budget allocator that caps memory injection (e.g., maximum 500 tokens for $\sigma$ and $\pi$) and truncates search results to a deterministic token limit.
6. **Expected Benefit:** Eliminates context overflow crashes; guarantees predictable LLM latency and prompt costs.
7. **New Failure Modes:** Lessons truncated mid-sentence could omit crucial negative constraints or invert logic (e.g., "Do not use sys.setrecursionlimit..." truncated to "Use sys.setrecursionlimit...").
8. **Security Implications:** None.
9. **Research Impact:** **RESEARCH-SAFE INFRASTRUCTURE.** As long as budget $\ge$ existing benchmark memory size (existing memories are $<120$ tokens), benchmark behavior is unchanged.
10. **Migration Complexity:** Low (simple token counting helper before prompt formatting in `execute_node.py`).
11. **Required Tests:** Test truncation when positive strategy exceeds token limit; test negative constraint preservation under budget.
12. **Final Decision:** **ACCEPTED (P0 - Product and Harness Safety).**

---

### Feature 2: Benchmark Checkpointing & Resumption
1. **Current Implementation:** Benchmark runners loop across tasks and append trial results to JSONL files.
2. **Exact File(s):** [`benchmarks/run_all.py:L105-133`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/benchmarks/run_all.py#L105-133), [`benchmarks/hotpotqa_runner.py:L108-141`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/benchmarks/hotpotqa_runner.py#L108-141), [`benchmarks/toolbench_runner.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/benchmarks/toolbench_runner.py).
3. **Existing Behavior:** In `hotpotqa_runner.py:L109-113`, `os.remove(store_path)` deletes the SQLite DB at the beginning of each condition. If an execution fails at task 49 of 50, re-running begins from task 0.
4. **Actual Gap:** Zero checkpoint state or resumption capability. Any transient network failure or rate limit during long multi-seed runs wastes compute and forces complete restart.
5. **Proposed Improvement:** Checkpoint completed `(benchmark, condition, task_id, trial)` tuples to a manifest JSON/sqlite ledger and resume uncompleted tasks.
6. **Expected Benefit:** Resilient multi-hour benchmark evaluations; zero lost compute.
7. **New Failure Modes:** Resuming with corrupted or partial database state if an interrupted trial committed partial writes.
8. **Security Implications:** None.
9. **Research Impact:** **RESEARCH-SAFE INFRASTRUCTURE.** Does not alter the evaluation metric or memory algorithm; purely harness orchestration.
10. **Migration Complexity:** Low (wrap task loop with checkpoint lookup in benchmark runners).
11. **Required Tests:** Interruption simulation test verifying that resumed execution yields identical completed records.
12. **Final Decision:** **ACCEPTED (P0 - Benchmark Harness Resilience).**

---

### Feature 3: Tenant / Agent / Session Scoping
1. **Current Implementation:** `user_id` exists in schema and table definition, but is completely ignored in queries.
2. **Exact File(s):** [`models/experience.py:L36`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/experience.py#L36), [`models/state.py:L15`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/state.py#L15), [`ai-service/memory/store.py:L96, L257-279, L282-307`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py#L257-279).
3. **Existing Behavior:** `SQLiteMemoryStore.list_experiences()` filters strictly by `task_domain`, `status`, and `min_trust`. It has no `user_id`, `tenant_id`, or `agent_id` parameter.
4. **Actual Gap:** Critical multi-tenant isolation failure. Every user and agent retrieves memories created by any other user or agent across the entire system.
5. **Proposed Improvement:** Add `tenant_id`, `agent_id`, and `session_id` to `Experience` model and filter them in `list_experiences()` and `search_similar()`.
6. **Expected Benefit:** Strict tenant isolation; prevents cross-user memory leakage in multi-user deployments.
7. **New Failure Modes:** Misconfigured tenant IDs (e.g. `None` or `"default"`) causing unintended cross-tenant leakage or total recall failure (empty memory store).
8. **Security Implications:** **CRITICAL SECURITY RISK.** Multi-tenant SaaS without this is subject to cross-tenant data leakage.
9. **Research Impact:** **PRODUCT ONLY.** In research benchmarks, runs already use isolated databases (`data/test_hotpotqa_{cond}.db`). The benchmark runner does not need tenant keys.
10. **Migration Complexity:** Moderate (schema update, adding `tenant_id` to index, passing `tenant_id` in API headers).
11. **Required Tests:** Unit test verifying tenant A cannot retrieve tenant B's memories under identical prompt and domain.
12. **Final Decision:** **ACCEPTED (P1 - Product Architecture).**

---

### Feature 4: Hybrid Retrieval (Dense + BM25)
1. **Current Implementation:** Pure dense cosine similarity search over vector embeddings computed via `local_embedder` (`all-MiniLM-L6-v2`, 384-d).
2. **Exact File(s):** [`ai-service/memory/store.py:L282-307`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py#L282-307), [`ai-service/nodes/retrieve_node.py:L69-76`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/retrieve_node.py#L69-76), [`ai-service/experiment/retrieval.py:L35-44`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/experiment/retrieval.py#L35-44).
3. **Existing Behavior:** Query text is embedded into 384 floats; dot product with stored memory embeddings computes similarity.
4. **Actual Gap:** Dense retrieval fails on exact token matches: specific error codes (`RecursionError`, `ECONNREFUSED`), precise function names, or exact parameter strings.
5. **Proposed Improvement:** Add SQLite FTS5 (full-text search) or BM25 index over `trigger_condition` and `strategy_lesson`, combining lexical score with cosine similarity via Reciprocal Rank Fusion (RRF).
6. **Expected Benefit:** Enhanced retrieval precision on code errors, technical APIs, and named entities.
7. **New Failure Modes:** Lexical matching retrieves irrelevant memories that share common generic stopwords or code boilerplate; altered candidate ranking.
8. **Security Implications:** None.
9. **Research Impact:** **FUTURE ABLATION / PRODUCT ONLY.** **CRITICAL FIREWALL RULE:** Phase 8 retrieval scoring is frozen (`LegacyModeRanker`). Hybrid retrieval must NOT be enabled in the frozen Phase 8 benchmark suite because it alters the retrieval set and invalidates baseline comparisons.
10. **Migration Complexity:** Moderate (requires SQLite FTS5 table creation and hybrid ranking fusion logic).
11. **Required Tests:** Comparison tests proving exact keyword recall increases without degrading semantic recall.
12. **Final Decision:** **ACCEPTED FOR PRODUCT / FUTURE ABLATION ONLY (P2). STRICTLY FIREWALLED FROM PHASE 8 RUNNERS.**

---

### Feature 5: Async Reflection
1. **Current Implementation:** Synchronous in-graph reflection node (`reflect_node`).
2. **Exact File(s):** [`ai-service/graph.py:L63, L71, L277`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/graph.py#L63), [`ai-service/nodes/reflect_node.py:L18-103`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/reflect_node.py#L18-103), [`backend/app/api/v1/agent.py:L41`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/api/v1/agent.py#L41).
3. **Existing Behavior:** The LangGraph execution flow is completely serial: `retrieve` $\to$ `execute` $\to$ `evaluate` $\to$ `reflect` $\to$ `trust`. The client waits until reflection LLM generation (1-3s) finishes before receiving the final answer.
4. **Actual Gap:** User-facing latency is inflated by post-task reflection and trust calculation.
5. **Proposed Improvement:** Return `final_answer` to the user immediately after evaluation; dispatch `reflect_node` and `trust_node` to a background worker (e.g. `asyncio.create_task` or Celery/Redis).
6. **Expected Benefit:** Reduces user-perceived API response latency by 1,000–3,000 ms.
7. **New Failure Modes:** **Race condition / Stale Read:** If the user or agent issues Task $T_2$ immediately after Task $T_1$, $T_2$ will retrieve memories before $T_1$'s reflection is distilled or its trust is updated. In benchmark evaluation, async reflection breaks sequential Markovian trust calibration completely!
8. **Security Implications:** None.
9. **Research Impact:** **DO NOT BUILD FOR BENCHMARK.** In benchmarks, synchronous reflection is mandatory to guarantee deterministic sequential evaluation. Acceptable only as an optional flag for consumer REST API.
10. **Migration Complexity:** High (requires background worker task management, handling disconnects, and eventual consistency).
11. **Required Tests:** Concurrency tests ensuring trust updates are serialized per experience ID even if reflection runs in background.
12. **Final Decision:** **DEFERRED (Product-Only Future Optimization).**

---

### Feature 6: Execution Plan Sealing (Deterministic Action Replay)
1. **Current Implementation:** Every task execution invokes LLM generation from scratch in `execute_node.py`.
2. **Exact File(s):** [`ai-service/nodes/execute_node.py:L58-86`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/execute_node.py#L58-86), [`models/task.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/task.py).
3. **Existing Behavior:** Bilateral constraints ($+\sigma, -\pi$) guide LLM generation, but the LLM plans and generates the response dynamically.
4. **Actual Gap:** High-confidence recurring tasks consume full LLM generation tokens even when the solution path is completely identical to prior successful runs.
5. **Proposed Improvement:** Seal verified tool execution plans and replay tool sequences deterministically without LLM generation.
6. **Expected Benefit:** Zero token cost and sub-100ms execution for deterministic repetitive tasks.
7. **New Failure Modes:** **Catastrophic Non-Idempotent Side-Effects:** Replaying tool actions on mutating operations (e.g., file writes, API POST requests, database deletes) when external environment state has changed can cause severe corruption.
8. **Security Implications:** High risk of unauthorized command replay.
9. **Research Impact:** **DO NOT BUILD.** The core research hypothesis of this paper is adaptive experiential cognitive constraints ($+\sigma, -\pi$) guiding LLM reasoning, not hardcoded workflow replay.
10. **Migration Complexity:** Very High.
11. **Required Tests:** N/A.
12. **Final Decision:** **REJECTED (DO NOT BUILD).**

---

### Feature 7: Memory Deduplication
1. **Current Implementation:** Every task execution that generates a candidate creates a new random UUID4.
2. **Exact File(s):** [`models/experience.py:L35`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/experience.py#L35), [`ai-service/nodes/reflect_node.py:L57-64`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/reflect_node.py#L57-64), [`ai-service/memory/store.py:L145`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py#L145), [`ai-service/graph.py:L360-367`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/graph.py#L360-367).
3. **Existing Behavior:** If 50 similar tasks succeed, 50 near-identical experience rows are stored in SQLite with distinct IDs.
4. **Actual Gap:** Database bloats with duplicate memories; evidence counters (`uses_count`, `successes_count`) are fragmented across dozens of copies instead of accumulating on a single canonical experience; top-k retrieval is saturated by duplicate advice.
5. **Proposed Improvement:** Semantic deduplication gate: before saving a candidate experience, compute cosine similarity against existing experiences in that domain. If $\text{Sim} \ge 0.92$, merge/reinforce the existing memory instead of inserting a duplicate row.
6. **Expected Benefit:** Prevents memory pool pollution, concentrates evidence counts, and keeps retrieval diversity high.
7. **New Failure Modes:** Context-specific distinctions lost if threshold is too low (e.g., merging "Iterative traversal for binary trees" with "Iterative traversal for directed graphs").
8. **Security Implications:** None.
9. **Research Impact:** **RESEARCH-SAFE INFRASTRUCTURE.** In Phase 8 benchmarks, `MemoryBank` is immutable (`bank.bank_hash` check enforced in `harness.py:L447-451`), so deduplication applies purely to candidate creation during live learning.
10. **Migration Complexity:** Low to Moderate (lookup before insert in `store.add_experience`).
11. **Required Tests:** Unit tests verifying that semantically identical experiences ($\ge 0.92$) increment counters on the existing record, while distinct experiences ($< 0.92$) create new rows.
12. **Final Decision:** **ACCEPTED (P1 - System Health).**

---

### Feature 8: Temporal Metadata & Recency
1. **Current Implementation:** `created_at` and `updated_at` ISO timestamps are stored in SQLite and Pydantic models.
2. **Exact File(s):** [`models/experience.py:L49-50`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/experience.py#L49-50), [`ai-service/memory/store.py:L109-110, L274`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py#L109-110).
3. **Existing Behavior:** Timestamps are recorded but completely ignored during retrieval and trust scoring. `store.py:L274` only uses `updated_at DESC` as a secondary sort tie-breaker.
4. **Actual Gap:** Outdated operational strategies (e.g. deprecated software API syntax from months ago) compete equally with current strategies.
5. **Proposed Improvement:** Add `last_accessed_at` and a configurable half-life decay parameter to memory ranking.
6. **Expected Benefit:** Naturally phases out obsolete advice in long-lived agents.
7. **New Failure Modes:** Older but universally true mathematical/algorithmic principles (e.g. "Iterative stack traversal prevents recursion overflow") could decay and be forgotten in favor of newer but trivial tips.
8. **Security Implications:** None.
9. **Research Impact:** **FUTURE ABLATION.** Must not alter the frozen Phase 8 A-EMA formula or retrieval ranking in benchmark runs.
10. **Migration Complexity:** Moderate (modifying retrieval score formula with decay term).
11. **Required Tests:** Simulation verifying that decayed memory falls below retrieval threshold over simulated time steps while refreshed memory stays active.
12. **Final Decision:** **DEFERRED TO FUTURE ABLATION (P2).**

---

### Feature 9: Contradiction Detection
1. **Current Implementation:** Zero contradiction detection exists.
2. **Exact File(s):** [`ai-service/nodes/reflect_node.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/reflect_node.py), [`ai-service/memory/store.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py).
3. **Existing Behavior:** Two memories with diametrically opposed advice can coexist in the database with high trust scores and both be injected into the prompt.
4. **Actual Gap:** Injected prompt constraints can conflict (e.g., "Use SQLite WAL mode for concurrency" vs "Never use SQLite for concurrent multi-process writes"), degrading agent performance.
5. **Proposed Improvement:** Run an NLI (Natural Language Inference) or LLM contradiction check when saving or retrieving memories; quarantine the lower-trust conflicting memory.
6. **Expected Benefit:** Eliminates cognitive dissonance in agent prompts.
7. **New Failure Modes:** Nuanced context-dependent exceptions incorrectly flagged as contradictions and quarantined.
8. **Security Implications:** None.
9. **Research Impact:** **DO NOT BUILD FOR CORE LOOP.** High computational overhead (extra LLM call per write/read) and potential to disrupt benchmark consistency.
10. **Migration Complexity:** High.
11. **Required Tests:** NLI verification suite on known contradictory rule pairs.
12. **Final Decision:** **REJECTED (DO NOT BUILD).**

---

### Feature 10: Multi-Trajectory Consolidation (Offline Synthesis)
1. **Current Implementation:** Reflection operates strictly on a single trajectory (one prompt, one output, one score).
2. **Exact File(s):** [`ai-service/nodes/reflect_node.py:L25-37`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/reflect_node.py#L25-37).
3. **Existing Behavior:** Each run independently distills a lesson. There is no background consolidation across runs.
4. **Actual Gap:** Procedural lessons remain hyper-specific to individual prompt phrasings; no synthesis into generalized domain heuristics across 20+ runs.
5. **Proposed Improvement:** Offline background consolidation job that clusters similar experiences in a domain and prompts an LLM to synthesize high-level meta-rules with higher confidence.
6. **Expected Benefit:** Produces clean, compact, generalized heuristics similar to human expert rule consolidation.
7. **New Failure Modes:** Over-generalization: synthesis might erase critical edge-case warnings present in individual trajectories.
8. **Security Implications:** None.
9. **Research Impact:** **FUTURE ABLATION.** Out of scope for current single-agent benchmarking; valuable for long-term product roadmap.
10. **Migration Complexity:** High (requires offline batch clustering and synthesis pipeline).
11. **Required Tests:** Verification that synthesized rules preserve critical pitfalls from source experiences.
12. **Final Decision:** **DEFERRED TO FUTURE ABLATION (P2).**

---

## 3. Memory Security Audit

### 3.1 Vulnerability Matrix: Secrets & Sensitive Data Leakage
The source code was audited for accidental storage, exposure, and transmission of sensitive credentials:

| Credential / Secret Category | Risk in Current System | Exact Code Pathway / Mechanism | Current Mitigation |
| :--- | :--- | :--- | :--- |
| **BYOK API Keys** (`OPENAI_API_KEY`, `GROQ_API_KEY`, etc.) | **CRITICAL** | `api_key` is passed in `TaskExecuteRequest.api_key`, saved in `AgentState["api_key"]` ([`models/state.py:L24`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/state.py#L24)), and passed into execution traces. If reflection analyzes messages containing keys, it distills them into `experiences.strategy_lesson`. | None. No regex or masking boundary exists. |
| **Access Tokens & Passwords** | **HIGH** | If `task_input` contains DB credentials (e.g. `postgresql://user:pass@host/db`) or auth tokens, `reflect_node` extracts text from `task_input` and `final_answer[:400]`, storing it permanently in SQLite `experiences` and embedding it into the vector index. | None. |
| **.env Values & Config Secrets** | **MODERATE** | Ambient credentials loaded in `ai-service/config.py` can be leaked if an error traceback is caught and serialized into `trajectory.detail` or `evaluator_reason`. | Partial (error messages sanitized in some places, but raw exceptions logged in `agent.py:L50`). |
| **Private URLs & Internal Endpoints** | **HIGH** | Web search results (`SearchTool`) or agent outputs containing private intranet URLs or staging endpoints are stored permanently in `experiences.trigger_condition`. | None. |
| **Secrets inside Code Artifacts** | **HIGH** | In coding tasks, code snippets containing hardcoded tokens are evaluated by `pytest_execution` and reflected into lessons. | None. |

### 3.2 Security Audit Findings
1. **Are secrets stored in experience memory?**
   **YES.** Any credential present in the user prompt, tool output, or agent trajectory can be extracted by `reflect_node.py:L30` and written to the `experiences` SQLite table as part of `strategy_lesson` or `trigger_condition`.
2. **Do secrets appear in logs?**
   **YES.** `logger.error("Error during agent task execution: %s", e)` and the in-memory execution trace (`ExecutionStepTrace.detail`) preserve the full text of prompts and tool outputs without redaction.
3. **Do retrieved memories expose secrets?**
   **YES.** If an experience row contains a secret, `execute_node.py:L43` formats it directly into the LLM system prompt (`[VERIFIED OPERATIONAL STRATEGY (+sigma)]:\n{positive_strategy}`) and returns it in the API response payload `retrieved_memories` to any client.
4. **Do deleted memories remain in vector indexes?**
   In the current `SQLiteMemoryStore`, deleting a row deletes its embedding JSON from the table. However, there is no explicit soft-delete tombstone, and vector embeddings cannot be selectively revoked without full row deletion.
5. **Is memory access properly scoped?**
   **NO.** Memory access is completely unscoped across tenants and users. Any user can retrieve any memory from any other user in the same domain.

### 3.3 Recommended Minimal Secret-Redaction Boundary (Do NOT Implement Yet)
A lightweight, zero-dependency `SecretRedactor` boundary should be established at three strategic ingress/egress chokepoints:
1. **Reflection Ingestion Chokepoint:** Scrub candidate experience fields (`trigger_condition`, `strategy_lesson`, `pitfall`) before calling `store.add_experience()`.
2. **Prompt Injection Chokepoint:** Scrub retrieved memory contents before assembling the system prompt in `execute_node.py`.
3. **Trace / Log Serialization Chokepoint:** Scrub `AgentState` before writing to `trajectory` and returning HTTP responses.

**Boundary Pattern:**
- Match and replace high-entropy patterns: Bearer tokens (`Bearer [a-zA-Z0-9_\-\.]{20,}`), API keys (`(?:sk-|gsk_|ai-|key-)[a-zA-Z0-9]{20,}`), Database connection URIs (`(?:postgres|mysql|mongodb|redis):\/\/[^:]+:[^@]+@[^\s]+`), and private IP ranges (`10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+`).

---

## 4. Memory Lifecycle Audit

### 4.1 Lifecycle State Transition Map
The lifecycle transitions in our current system were mapped against the theoretical model:

```mermaid
stateDiagram-v2
    [*] --> CREATE: reflect_node distills candidate
    CREATE --> CANDIDATE: store.add_experience(status='candidate')
    CANDIDATE --> ACTIVE: trust_node verifies R >= 0.80
    ACTIVE --> RETRIEVED: retrieve_node matches query
    RETRIEVED --> REUSED: execute_node injects (+sigma, -pi)
    REUSED --> TRUST_UPDATED: trust_node applies A-EMA
    TRUST_UPDATED --> ACTIVE: S_new >= theta (0.35)
    TRUST_UPDATED --> QUARANTINED: S_new < theta (0.35)
    QUARANTINED --> DEPRECATED: status = 'deprecated'
    DEPRECATED --> [*]: Inactive in SQLite
```

### 4.2 State Verification Table

| Lifecycle State | Present in Code? | Enum / Status Value | Implementation Mechanism |
| :--- | :---: | :--- | :--- |
| **CREATE** | **YES** | Implicit in Node | Extracted in `reflect_node.py:L57` as dictionary. |
| **CANDIDATE** | **YES** | `ExperienceStatus.CANDIDATE` | Set in `reflect_node.py:L63`; requires empirical success to promote. |
| **ACTIVE** | **YES** | `ExperienceStatus.ACTIVE` | Promoted in `trust_node.py:L81` on verified success ($R \ge 0.80$). |
| **RETRIEVED** | **YES** | In State / Trajectory | Formatted as `ExperienceMatch` in `retrieve_node.py:L82`. |
| **REUSED** | **YES** | In System Prompt | Injected into system prompt in `execute_node.py:L43`. |
| **TRUST UPDATED** | **YES** | In SQLite Ledger | A-EMA computed in `trust_node.py`; logged to `trust_history`. |
| **OUTDATED / CONFLICTED** | **MISSING** | None | **Gap:** No state exists to represent stale or contradicted memories. |
| **QUARANTINED** | **CONFLATED** | `ExperienceStatus.DEPRECATED` | **Gap:** Quarantined memories are immediately marked `deprecated`. There is no separate `quarantined` state allowing diagnostic audit or probation. |
| **ARCHIVED / DELETED** | **MISSING** | None | **Gap:** No soft-delete tombstone or archive state exists. |

---

## 5. Memory Provenance Audit

### 5.1 Provenance Capability Checklist

| Provenance Question | Can System Answer Today? | Current Mechanism & Limitation |
| :--- | :---: | :--- |
| **Where did this memory originate?** | **PARTIALLY** | `experiences.task_domain` and `experiences.user_id` exist. But origin source (repo, benchmark suite, external user, model version) is missing. |
| **Which task created it?** | **YES** | `experiences.source_task_id` records the `task_id` that distilled the memory. |
| **Which execution created it?** | **NO** | `execution_id` is generated in `execute_task()` but is NOT stored on the `experiences` table (only on `trust_history`). |
| **When was it created?** | **YES** | `experiences.created_at` records the UTC ISO timestamp. |
| **Which runs reused it?** | **PARTIALLY** | `trust_history.execution_id` records tasks that changed its trust score. But if a memory was retrieved and had a neutral run with zero delta, or if memory updates were suppressed, reuse is not recorded. |
| **Which outcomes supported its current trust?** | **NO** | `experiences.successes_count` stores an aggregate integer. The actual tasks, prompts, or evaluation outcomes that rewarded the memory are not linked. |
| **Which failures reduced its trust?** | **NO** | `experiences.failures_count` stores an aggregate integer. Specific error traces or failing task inputs are not recorded. |

### 5.2 Smallest Schema Addition Needed (Do NOT Implement Yet)
To achieve complete provenance without breaking SQLite compatibility or the 7-tuple model:

1. **Add to `experiences` table:**
   - `created_by_execution_id TEXT` (links to creator task execution trace)
   - `model_version TEXT` (model that distilled the lesson)
2. **Add to `trust_history` table:**
   - `task_id TEXT` (direct foreign key to task)
   - `task_reward REAL` (exact continuous reward $R_t$ from evaluator)
   - `binary_outcome INTEGER` (0 or 1)
   - `evaluator_name TEXT` (evaluator that certified the outcome)

---

## 6. Failure-Mode Analysis

Detailed failure modes across all 10 candidate features:

```
+-----------------------------------+---------------------------------------------------------------------------------+
| Proposed Feature                  | Critical Failure Mode                                                           |
+-----------------------------------+---------------------------------------------------------------------------------+
| 1. Context / Token Budgeting      | Truncation amputates negative constraint (-pi), turning a warning into advice.  |
| 2. Benchmark Checkpointing        | Resuming from corrupt partial database state causes inconsistent seed results.  |
| 3. Tenant / Agent Scoping         | Misconfigured tenant ID ('None' or 'default') causes cross-tenant memory leak.  |
| 4. Hybrid Retrieval (BM25)        | Lexical matching retrieves irrelevant memory with high word overlap; alters     |
|                                   | frozen Phase 8 candidate set and invalidates baseline comparisons.              |
| 5. Async Reflection               | Race condition: Task 2 runs before Task 1 reflection updates trust, causing     |
|                                   | stale retrieval and broken sequential calibration.                              |
| 6. Execution Plan Sealing         | Replaying non-idempotent tool actions (file deletes, API posts) on mutated     |
|                                   | external environment causes severe state corruption.                           |
| 7. Memory Deduplication           | Over-aggressive similarity threshold merges context-distinct lessons, erasing  |
|                                   | edge-case distinctions.                                                         |
| 8. Temporal Metadata / Decay      | Time-decay penalizes fundamental unchanging algorithmic truths over recent      |
|                                   | trivial tips.                                                                   |
| 9. Contradiction Detection        | False positive: subtle context-specific exceptions mistaken for contradictions. |
| 10. Multi-Trajectory Synthesis    | Over-generalization: synthesis erases vital operational negative constraints.   |
+-----------------------------------+---------------------------------------------------------------------------------+
```

---

## 7. Research Firewall Classifications

To protect the empirical claims, mathematical theorems (Theorem 1), and frozen evaluation baselines of the paper, every proposed feature is strictly classified:

```
========================================================================================
                               RESEARCH FIREWALL MATRIX
========================================================================================

[RESEARCH-SAFE INFRASTRUCTURE]  (Can be added to harness without altering paper claims)
  ├── 1. Context / Token Budgeting (safeguards LLM context; transparent to existing tests)
  └── 2. Benchmark Checkpointing (pure harness resilience; zero effect on agent decisions)

[PRODUCT ONLY]  (Crucial for production deployment; omitted from benchmark runners)
  ├── 3. Tenant / Agent / Session Scoping (required for multi-user SaaS security)
  └── 4. Secret Redaction Boundary (required to prevent credential leakage in experiences)

[FUTURE ABLATION]  (Valuable research concepts, but strictly deferred to future work)
  ├── 5. Hybrid Retrieval (Dense + BM25) (must not alter frozen Phase 8 ranker)
  ├── 6. Memory Deduplication (needs controlled empirical threshold tuning)
  ├── 7. Temporal Metadata / Recency Decay (requires formal mathematical formulation)
  └── 8. Multi-Trajectory Offline Consolidation (batch meta-learning study)

[DO NOT BUILD]  (Rejected; conflicts with core research principles or introduces high risk)
  ├── 9. Execution Plan Sealing (rigid macro replay conflicts with adaptive reasoning)
  ├── 10. Async Reflection in Benchmarks (destroys causal trial-by-trial trust updates)
  └── 11. Contradiction Detection via NLI (high latency, high false-positive risk)
========================================================================================
```

### Absolute Constraints
1. **Phase 8 is FROZEN.** Do not modify `ai-service/experiment/harness.py`, `ai-service/experiment/run_context.py`, or `ai-service/experiment/evidence.py`.
2. **Do NOT alter A-EMA formulas.** The parameters $\alpha=0.85$, $\beta=0.70$, $\gamma=0.80$, $\theta=0.35$ are mathematically anchored to Theorem 1.
3. **Do NOT alter the frozen evaluator.** The F3 outcome contract (`ai-service/tools/evaluator.py`, `models/task.py`) is the single authority for task reward.
4. **Do NOT alter frozen benchmark retrieval behavior.** `LegacyModeRanker` in `ai-service/experiment/retrieval.py` must remain bit-compatible.

---

## 8. Recommended Implementation Order

When implementation is explicitly authorized by the user, changes must proceed in strictly guarded phases:

### Phase 1: Zero-Risk Harness Resilience & Security (P0)
- **Feature 2:** Benchmark Checkpointing & Resumption in `benchmarks/run_all.py` and benchmark runners.
- **Security:** Secret Redaction Filter at reflection ingestion and prompt injection boundaries.
- **Feature 1:** Context/Token Budgeting in `ai-service/nodes/execute_node.py`.

### Phase 2: Product Integrity & Multi-Tenancy (P1)
- **Fix Discrepancy:** Unify `backend/app/api/v1/memories.py` to use `SQLiteMemoryStore` instead of the mock in-memory `MemoryDatabase`.
- **Feature 3:** Tenant and Agent Scoping in `models/experience.py` and `SQLiteMemoryStore`.
- **Feature 7:** Semantic Memory Deduplication gate in `SQLiteMemoryStore.add_experience()`.

### Phase 3: Future Research Ablations (P2 - Post-Paper Submission)
- **Feature 4:** Hybrid Retrieval (behind an explicit feature flag, never enabled on Phase 8 benchmarks).
- **Feature 8 & 10:** Temporal Decay and Offline Multi-Trajectory Consolidation.

---

## 9. Explicit Non-Goals

1. **NO Replacement of SQLite with PostgreSQL / Supabase:** The product and offline benchmark runners are optimized for local SQLite with numpy cosine search. Adding mandatory Postgres/Supabase infrastructure is a non-goal.
2. **NO Execution Plan Macro Replay:** We are building an adaptive reasoning agent, not a deterministic RPA macro recorder.
3. **NO Async Reflection in Benchmark Harness:** Benchmarks require synchronous, sequential trust updates to preserve mathematical validity.
4. **NO Rewriting of Evaluators:** The deterministic evaluators (`pytest_execution`, `toolbench_trap`, `exact_match_f1`) are frozen.

---

## 10. Exact Files Likely to Change (When Authorized)

The following files are identified as the exact edit targets for upcoming work:

| Target File | Intended Change (Post-Authorization Only) | Safety Classification |
| :--- | :--- | :--- |
| [`benchmarks/run_all.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/benchmarks/run_all.py) | Add run checkpointing ledger and resume capability | Research-Safe Infrastructure |
| [`benchmarks/hotpotqa_runner.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/benchmarks/hotpotqa_runner.py) | Checkpoint completed tasks before deleting DB | Research-Safe Infrastructure |
| [`ai-service/nodes/execute_node.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/execute_node.py) | Add token budgeting for $\sigma, \pi$ and search context | Research-Safe Infrastructure |
| [`ai-service/nodes/reflect_node.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/nodes/reflect_node.py) | Add secret redaction boundary on extracted lessons | Product Security |
| [`backend/app/api/v1/memories.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/backend/app/api/v1/memories.py) | Replace in-memory `db` with active `SQLiteMemoryStore` | Product Only |
| [`ai-service/memory/store.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/ai-service/memory/store.py) | Add tenant filtering and semantic deduplication gate | Product Only |
| [`models/experience.py`](file:///Users/sumitdas/Desktop/OJT/Adaptive-Agent-Memory-OJT-G146/models/experience.py) | Add `tenant_id` and provenance execution fields | Product Only |

---
**AUDIT COMPLETED. ALL IMPLEMENTATION ACTIVITIES ARE STOPPED PENDING USER INSTRUCTION.**
