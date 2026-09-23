# UX Requirements

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Approved Specification Baseline (Month 2 Specification)  

---

## Information Architecture

1. **Authentication:** Sign In / Sign Up via Supabase Auth (GoTrue) with session persistence.
2. **Main Agent Dashboard:** Overview of agent performance, recent task executions, memory statistics, and rapid task dispatch.
3. **3D Memory Core Visualizer:** Interactive Three.js spatial graph displaying memory nodes clustered by domain and colored by trust score ($S \in [0.0, 1.0]$).
4. **Task Execution Workspace:** Prompt input, domain selection, model selector (Groq, Gemini, Ollama), live LangGraph node streaming, tool output inspection, and final answer display.
5. **Experience Memory Explorer:** Searchable, filterable catalog of all distilled memories with domain tags, trust score badges, trigger conditions, strategies, and negative constraints (pitfalls).
6. **Trust Evolution & Audit Timeline:** Chronological timeline showing memory lifecycle transitions, reward scores, and EMA trust score drift over time.
7. **BYOK & Model Settings:** Secure client-side configuration for model API keys (Groq, Gemini), local endpoint configuration (Ollama), and retrieval thresholds.

---

## Primary User Flow

```text
Login ──> Dashboard ──> Submit Task Prompt ──> Watch LangGraph Execution Stream 
        ──> Inspect Retrieved Memories & Pitfalls ──> View Tool Execution & Final Output 
        ──> Review Deterministic Reward & Reflection ──> Verify Trust Score Update in 3D Core / Audit Log
```

1. **Authentication:** User logs in securely; JWT token is stored in memory and attached to all API requests.
2. **Task Creation:** User selects a domain (`research`, `coding`, `reasoning`), chooses an LLM provider, and inputs the task prompt.
3. **Execution Streaming:** User observes the 5-node LangGraph lifecycle as it updates live (`retrieve` → `execute` → `evaluate` → `reflect` → `trust`).
4. **Context Inspection:** User inspects the top-$k$ retrieved memories and explicitly sees the active strategies and pitfalls injected into the prompt.
5. **Outcome Review:** User views the final response, tools called, token usage, latency, and the deterministic reward score ($R_t \in [0.0, 1.0]$).
6. **Memory Lifecycle Verification:** If a new operational lesson is distilled, user inspects the extracted `{Trigger, Strategy, Pitfall}` and sees its initial `candidate` status and trust score in the memory catalog.

---

## Key Screen Requirements

### 1. Agent Dashboard
- Summary cards: Total Memories, Active Memories, Quarantined Count, Average Trust Score, Total Task Runs.
- Quick Task Runner: Multi-line prompt input with domain selector and "Run Agent" CTA.
- Recent Executions Table: Status indicators (`success`, `failed`, `running`), latency, and reward score.

### 2. 3D Memory Core Visualizer
- Interactive Three.js canvas with orbit controls (pan, zoom, rotate).
- Node coloring by trust level:
  - Green / Emerald: High Trust ($S \ge 0.70$)
  - Amber / Yellow: Moderate Trust ($0.35 \le S < 0.70$)
  - Red / Crimson: Quarantined / Deprecated ($S < 0.35$)
- Node clustering by domain using force-directed layout.
- Click-to-inspect: Clicking a memory node opens a drawer with its complete 7-tuple attributes.

### 3. Task Execution View
- Node stepper showing current LangGraph active node (`retrieve` → `execute` → `evaluate` → `reflect` → `trust`).
- Retrieved Memories Accordion: Displays the exact Trigger, Strategy, and Pitfall injected into the model context.
- Tool Call Terminal: Monospace collapsible log of search queries, scraped content, and exit codes.
- Final Output Panel: Formatted Markdown response with copy button and latency/token badges.

### 4. Experience Memory Explorer
- Search bar querying triggers, strategies, and pitfalls.
- Domain filter pills (`all`, `research`, `coding`, `reasoning`, `finance`).
- Status tabs: `active`, `candidate`, `deprecated` (quarantined).
- Detail Modal: Shows confidence, success count, failure count, embedding dimensions, and historical audit trail.

### 5. Settings & BYOK (Bring Your Own Key) Panel
- Form inputs for Groq API Key, Google Gemini API Key, and Ollama Base URL (`http://localhost:11434`).
- Secure storage indicator (explaining that keys are kept in session memory and never persisted in database plaintext).
- Retrieval parameter sliders: Similarity Threshold ($\theta_{\text{sim}} \in [0.5, 0.9]$), Top-$k$ ($1 \le k \le 10$), and Trust Weight ($w_{\text{trust}} \in [0.0, 0.5]$).

---

## States

Every asynchronous screen and component must explicitly define 5 fundamental states:
1. **Loading State:** Skeleton loaders for tables, spinning orbital ring for the 3D core, and pulsating node badges during LangGraph execution.
2. **Empty State:** Clean illustrative cards with helpful onboarding actions (e.g., *"No memories found in this domain. Run a task to generate your first experience lesson."*).
3. **Success State:** Clear visual confirmation, green badges, and crisp data rendering upon task completion.
4. **Degraded / Fallback State:** Notice banner when primary LLM fails over to secondary or local Ollama, or when zero memories matched the retrieval threshold (running zero-shot baseline).
5. **Error State:** Human-readable error alerts displaying error code, correlation ID, and actionable guidance without leaking internal stack traces.

---

## Accessibility

- **Keyboard Navigation:** Full tab-order navigation across all forms, buttons, modals, and data tables.
- **Semantic HTML:** Appropriate usage of `<main>`, `<nav>`, `<section>`, `<article>`, `<header>`, and ARIA roles.
- **Color Contrast:** Strict WCAG 2.1 AA compliance ($> 4.5:1$ contrast ratio) across both light and dark themes.
- **Multi-Modal Trust Indicators:** Trust scores are never conveyed by color alone; every badge includes a numerical score and text label (e.g., `High Trust (0.88)` vs green dot alone).
- **Reduced Motion:** Honor `prefers-reduced-motion` media queries by disabling camera rotations and particle animations in the Three.js 3D visualizer.
