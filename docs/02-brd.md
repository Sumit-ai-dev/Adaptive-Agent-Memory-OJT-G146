# Business Requirements Document (BRD)

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146  
**Track:** Generative AI / Agentic AI  

---

## 1. Executive Summary
Modern Large Language Models (LLMs) demonstrate remarkable capability in solving individual reasoning tasks, yet they remain fundamentally stateless. When deployed across recurring workflows, LLMs fail to retain operational lessons from previous executions, frequently repeating identical mistakes and requiring users to restate domain guidance. Conversely, existing agent memory approaches naively treat semantic relevance as equivalent to reliability, allowing obsolete, wrong, or context-inappropriate experiences to degrade future performance. 

This project delivers an **Adaptive AI Agent with Persistent Experience Memory**—an external intelligence layer wrapped around a frozen LLM. The system systematically extracts compact, reusable lessons (`{Trigger, Strategy, Pitfall}`), evaluates execution outcomes, dynamically tracks empirical trust scores, and applies reliability-aware retrieval ($0.70 \times \text{Similarity} + 0.30 \times \text{Trust}$) to ensure an agent measurably improves over time without modifying underlying model weights.

---

## 2. Problem Statement
Knowledge workers, software developers, and research evaluators using AI agents face two interconnected challenges:
1. **Experience Amnesia:** Useful problem-solving strategies, error recoveries, and operational lessons discovered during task execution are permanently lost once a session terminates.
2. **The "Relevant $\neq$ Reliable" Fallacy:** Storing unvetted conversational transcripts or purely semantic vector memories pollutes the agent's context. When an agent recalls past experiences solely based on cosine similarity, misleading, outdated, or harmful strategies are injected into future prompts, inducing compounding hallucinations and degraded task success.

Memory requires continuous evaluation, evidence-based trust scoring, and lifecycle management—not merely persistent vector storage.

---

## 3. Vision
To build an evidence-grounded, zero-cost adaptive agent memory architecture that turns task executions into a self-improving, auditable experience library, enabling frozen LLMs to improve task accuracy and filter harmful recollections across recurring domains.

---

## 4. Objectives
- **Eliminate Repetitive Operational Errors:** Automatically extract actionable strategies and pitfalls from completed tasks to prevent recurring failures.
- **Decouple Semantic Relevance from Reliability:** Implement a composite ranking mechanism that weights empirical usefulness alongside vector similarity.
- **Ensure Grounded Memory Hygiene:** Persist structured, token-efficient lessons rather than dumping unstructured conversational transcripts.
- **Autonomous Lifecycle Deprecation:** Dynamically penalize and deprecate unreliable experiences whose trust score falls below configurable thresholds ($< 0.35$).
- **Provide Observable Control:** Deliver an interactive web dashboard with transparent audit trails for task trajectories, trust evolutions, and memory curation.
- **Scientifically Quantify Memory Utility:** Rigorously validate performance gains across controlled experimental conditions: Condition A (Memory OFF), Condition B (Naive Memory), and Condition C (Adaptive Memory).

---

## 5. Personas

| Persona | Goals | Pain Points |
| :--- | :--- | :--- |
| **AI Application Developer** | Build reliable agentic workflows without the prohibitive expense or complexity of fine-tuning foundation models. | Agents repeat known library bugs or API misconfigurations across separate user sessions. |
| **Research & Benchmark Evaluator** | Experimentally verify whether persistent memory genuinely benefits task performance or causes negative transfer. | Lack of clean attribution frameworks to measure whether retrieved memories caused task success or failure. |
| **Knowledge Worker / Analyst** | Delegate multi-step research, coding, and analytical tasks to an assistant that learns working preferences and domain constraints. | Forced to manually re-prompt the agent with identical domain caveats and verification rules every day. |

---

## 6. Business Use Cases
- **Task Execution with Memory Augmentation:** User submits a task; the agent retrieves top-$k$ relevant and high-trust experiences to guide execution.
- **Post-Execution Lesson Extraction:** The system reflects on multi-step executions and distills reusable strategies and pitfalls.
- **Dynamic Trust Calibration:** The system observes task success/failure and updates the experience's trust score using an Exponential Moving Average.
- **Experience Library Curation:** Developer searches, filters, inspects, and manually modifies or deprecates experiences via the dashboard.
- **Trust History Auditing:** Evaluator inspects the step-by-step mathematical score updates and execution provenance of any stored memory.
- **Controlled Benchmark Execution:** Evaluator triggers automated offline batch test runs comparing Memory OFF vs. Naive Memory vs. Adaptive Memory.
- **System Health & Telemetry Inspection:** Operator monitors API latency, LiteLLM gateway status, and vector database connectivity.

---

## 7. Business Requirements

| ID | Requirement | Priority | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **BR-001** | User can execute agent tasks with memory controls | Must | User selects domain and memory mode (`off`, `naive`, `adaptive`); receives structured answer and execution metadata. |
| **BR-002** | System automatically extracts reusable experiences | Must | Multi-step runs trigger reflection node; generates structured `{Trigger, Strategy, Pitfall}` with initial confidence. |
| **BR-003** | System maintains hybrid relational and vector persistence | Must | Experiences, usage counters, trust logs, and vector embeddings are stored transactionally in PostgreSQL + `pgvector`. |
| **BR-004** | System retrieves experiences using composite ranking | Must | Retrieval ranks candidates via composite formula ($0.70 \times \text{Similarity} + 0.30 \times \text{Trust}$); filters deprecated items. |
| **BR-005** | System dynamically updates empirical trust scores | Must | Task outcome evaluates $R \in [0, 1]$; updates trust via EMA ($S_{t+1} = 0.8 S_t + 0.2 R$); records audit event. |
| **BR-006** | System enforces experience lifecycle state transitions | Must | Manages states (`CANDIDATE`, `ACTIVE`, `DEPRECATED`); experiences with trust $< 0.35$ are excluded from retrieval. |
| **BR-007** | User can inspect and curate experiences in dashboard | Must | Web dashboard allows browsing, searching by domain/status, editing lessons, and manual deprecation. |
| **BR-008** | System logs execution trajectories and trust history | Must | Every execution records node durations, tools invoked, memories retrieved, and token metrics with unique IDs. |
| **BR-009** | System runs controlled scientific benchmark comparisons | Must | Offline runner evaluates identical task suites across Condition A, Condition B, and Condition C, outputting comparative metrics. |
| **BR-010** | System operates within a zero-cost architecture | Must | Uses LiteLLM (Groq/Ollama), local HuggingFace embeddings, DuckDuckGo, Jina Reader, and Supabase free tier. |

---

## 8. Non-Functional Requirements
- **Security & Access Control:** Role-based dashboard access backed by Supabase Auth; all API calls validated via JWT Bearer tokens; API keys stored strictly in `.env`.
- **Performance & Latency:** Non-LLM operations (pgvector similarity search, composite ranking, trust updates, DB writes) target p95 latency < 200 ms.
- **Auditability & Traceability:** Every stored memory maintains full provenance linking to its generating task execution ID, with complete trust transition logs.
- **Token Efficiency:** Memory injection is restricted to top-$k$ relevant items (preventing context bloating and minimizing inference cost).
- **Modularity & Independence:** The memory architecture remains decoupled from any single proprietary LLM via the LiteLLM gateway boundary.
- **Research Reproducibility:** Fixed prompt baselines and deterministic evaluation harnesses ensure performance differences are attributable solely to memory behavior.

---

## 9. Success Metrics
- **Task Success Rate Delta:** Percentage increase in completed benchmark tasks under Adaptive Memory (Condition C) compared to Baseline (Condition A).
- **Net Memory Utility:** Measured improvement of Adaptive Memory over Naive Relevance-Only Memory (Condition C vs. Condition B):
  $$\text{Utility} = P(\text{Success} \mid \text{Adaptive Memory}) - P(\text{Success} \mid \text{Naive Memory})$$
- **Harmful Recollection Filtering:** Number of deprecated or low-trust memories correctly excluded from candidate injection.
- **Trust Convergence:** Speed at which empirical trust stabilizes around genuinely effective vs. ineffective strategies over successive runs.
- **Median Execution Latency:** End-to-end task turnaround time across all pipeline nodes.
- **Zero-Cost Adherence:** Operational spend maintained at $0 throughout the 12-week OJT lifecycle.

---

## 10. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| **Memory Poisoning / Bad Strategies** | Medium | High | Conservative initial trust ($0.60$), EMA score penalization on failure, and automatic deprecation threshold ($< 0.35$). |
| **Over-generalization / Semantic Drift** | Medium | Medium | Require structured trigger conditions and domain scoping (`research`, `coding`, `analysis`, `planning`). |
| **External LLM Provider Rate Limits** | Medium | Medium | LiteLLM abstraction layer allows seamless fallback between cloud Groq and local open-weight Ollama instances. |
| **Credit Assignment Ambiguity** | High | Medium | Isolate multi-factor evaluation; measure performance across repeated iterations rather than attributing success to memory from a single run. |
| **Vector DB Storage / Latency Bottlenecks** | Low | Medium | Utilize indexed `pgvector` HNSW/IVFFlat cosine similarity with relational pre-filtering on status and trust. |

---

## 11. MVP Scope

### In Scope (12-Week OJT Deliverables)
- **Frontend Client:** React + Vite web dashboard with Supabase authentication, task execution console, experience library explorer, and visual trust graphs.
- **Backend API:** FastAPI versioned RESTful service (`/api/v1`) with Pydantic v2 validation contracts.
- **Agent Orchestration:** LangGraph 5-node StateGraph (`retrieve` → `execute` → `evaluate` → `reflect` → `trust`).
- **Model & Embeddings Gateway:** LiteLLM gateway (Groq / Ollama) coupled with local HuggingFace embedding models (`bge-small-en-v1.5` / `all-MiniLM-L6-v2`).
- **Deterministic Tools:** DuckDuckGo Search, Jina AI Reader (`r.jina.ai/<url>`), and Python execution tool.
- **Persistence:** Supabase PostgreSQL + `pgvector` storing tasks, executions, structured experiences, and trust logs.
- **Evaluation Harness:** Benchmark test runner executing controlled comparisons across Condition A, Condition B, and Condition C.

### Out of Scope (Deliberate Non-Goals)
- Model fine-tuning, parameter retraining, or adapter training (LLM remains completely frozen).
- Raw conversational chat log dumping.
- Full multi-tenant enterprise billing or organizational hierarchy.
- Production multi-language SDK package during the 12-week timeframe.

---

## 12. Future Scope
- **Offline Memory Clustering & Deduplication:** Background batch workers using `pgvector` cosine distance ($< 0.10$) to consolidate duplicate strategies.
- **Chrome Extension Companion:** Manifest V3 browser extension consuming the centralized `/api/v1` backend.
- **Standalone Reusable Python Package:** Publishing the core memory engine as an open-source library (`pip install adaptive-memory`).
- **Domain-Specific Memory Namespaces:** Dynamically partitioning memory stores by organization, project, or domain for targeted multi-agent retrieval.
