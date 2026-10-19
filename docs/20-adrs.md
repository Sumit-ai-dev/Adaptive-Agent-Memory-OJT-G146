# Architecture Decision Records (ADRs)

**Project:** Adaptive AI Agent with Persistent Experience Memory (AEMA)  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Approved Engineering Decisions  

---

## ADR-001: LangGraph Cyclical StateGraph for Cognitive Control Loop

- **Status:** Accepted & Implemented
- **Context:** An autonomous experiential agent requires a multi-step feedback loop: retrieve experiences, execute tools, evaluate outcomes, distill lessons, and update trust scores. Linear chains (such as standard LangChain `SequentialChain`) cannot naturally support cyclical feedback loops, conditional branches, or stateful checkpoints.
- **Decision:** Use LangGraph to define a 5-node cyclical `StateGraph` with explicit typed state (`AgentState`).
- **Rationale:** LangGraph provides first-class support for cyclical agent state transitions, human-in-the-loop inspection, state serialization, and clean separation of concerns across graph nodes (`retrieve`, `execute`, `evaluate`, `reflect`, `trust`).
- **Trade-offs:** Requires strict state schema management and careful handling of conditional loop termination to prevent infinite cycles.

---

## ADR-002: React 18 + TypeScript + Vite + Three.js for Frontend Dashboard

- **Status:** Accepted & Implemented
- **Context:** Evaluators and researchers need an intuitive interface to submit tasks, inspect live execution traces, explore semantic memory clusters in 3D space, and manage persistent conversation histories.
- **Decision:** Build a modern Single Page Application (SPA) using React 18, TypeScript, Tailwind CSS, Vite, and Three.js.
- **Rationale:** React 18 provides high responsiveness with concurrent features; TypeScript guarantees end-to-end type safety against backend API schemas; Three.js delivers a 3D visual experience (`ThreeMemoryCore.tsx`) rendering real-time memory nodes clustered by domain and colored by trust.
- **Trade-offs:** Introduces client-side JavaScript compilation and WebGL rendering requirements on the browser.

---

## ADR-003: Deterministic Evaluator Architecture vs. LLM-as-a-Judge

- **Status:** Accepted & Implemented
- **Context:** Measuring whether an agent successfully accomplished a task is required to compute reward $R_t \in [0.0, 1.0]$. Relying on an auxiliary LLM ("LLM-as-a-judge") introduces substantial latency (2-4 seconds), non-deterministic scoring variances, token costs ($0.02 - $0.05 per task), and susceptibility to prompt injection.
- **Decision:** Implement a deterministic outcome evaluator (`evaluate_node`) utilizing Python AST parsing, subprocess exit codes, schema validation, and programmatic assertion checks.
- **Rationale:** Deterministic evaluation executes in under 5 milliseconds on CPU, costs zero LLM tokens, and provides 100% reproducible ground-truth verification.
- **Trade-offs:** Requires domain-specific assertion heuristics or unit test fixtures for novel task domains.

---

## ADR-004: Asymmetric Exponential Moving Average (A-EMA) Trust Dynamic

- **Status:** Accepted & Implemented
- **Context:** An experience memory must update its trust score based on observed usefulness over repeated tasks. A standard symmetric moving average treats success and failure identically, allowing harmful or outdated advice to linger dangerously in the retrieval pool.
- **Decision:** Adopt an Asymmetric Exponential Moving Average (A-EMA) formula:
  - Success ($R_t \ge 0.5$): $S_{t+1} = \alpha S_t + (1 - \alpha) R_t$, with $\alpha = 0.85$ (conservative trust accumulation).
  - Failure ($R_t < 0.5$): $S_{t+1} = \beta S_t + (1 - \beta) R_t$, with $\beta = 0.70$ (aggressive penalty).
- **Rationale:** Asymmetry ensures that trust is difficult to gain but easy to lose. Flawed lessons are rapidly penalized before they cause cascading negative transfer in related tasks.
- **Trade-offs:** Requires careful tuning of $\alpha$ and $\beta$ to avoid over-penalizing experiences due to transient external tool errors.

---

## ADR-005: Theorem 1 Deterministic Quarantine Bound

- **Status:** Accepted & Implemented
- **Context:** In adversarial or noisy environments, a previously trusted memory can become obsolete or poisoned. The system must guarantee that a persistently failing memory is deactivated before causing widespread failure.
- **Decision:** Formalize and enforce Theorem 1: Any experience with initial trust $S_0 < 0.95$ drops below the active threshold $\theta = 0.35$ in at most $k^* = 3$ consecutive failures ($R_t = 0.0$), triggering automatic transition to `status = 'quarantined'`.
- **Rationale:** Provides mathematical certainty and bounded risk. In empirical tests, Theorem 1 completely eliminated negative transfer across consecutive failure trajectories.
- **Trade-offs:** Quarantined memories require an explicit recovery mechanism or human-in-the-loop review to re-enter the active pool.

---

## ADR-006: Local Sentence-Transformers with Deterministic Hash Fallback

- **Status:** Accepted & Implemented
- **Context:** The system requires vector embeddings to power semantic retrieval. Relying exclusively on OpenAI/Cohere embedding APIs introduces external network dependencies, privacy concerns, latency, and cost. Furthermore, heavy PyTorch dependencies can slow down continuous integration runners.
- **Decision:** Use HuggingFace `sentence-transformers/all-MiniLM-L6-v2` locally (384 dimensions) with an automated fallback to a deterministic hash embedder when PyTorch is not installed.
- **Rationale:** Local embeddings run in $<15\text{ ms}$ on CPU with zero dollar cost. The fallback embedder guarantees that the CI/CD pipeline and lightweight development environments run 100% of test suites with zero external model downloads.
- **Trade-offs:** MiniLM has a 256 token input context limit, which is sufficient for compact lessons but unsuitable for long document passages.

---

## ADR-007: Bring-Your-Own-Key (BYOK) Multi-Provider Gateway with Zero-Retention

- **Status:** Accepted & Implemented
- **Context:** Users and evaluators may have varying access to LLM providers (Groq, Google Gemini, OpenAI, or local Ollama). Storing user credentials on a shared database introduces serious security and compliance risks.
- **Decision:** Build an ephemeral BYOK gateway using LiteLLM where API keys are passed via session headers, held strictly in-memory during task execution, and never written to logs or persistent storage.
- **Rationale:** Maximum flexibility for end-users, zero credential leakage risk, and compliance with data privacy standards.
- **Trade-offs:** Users must provide an API key or configure local Ollama for real LLM reasoning.
