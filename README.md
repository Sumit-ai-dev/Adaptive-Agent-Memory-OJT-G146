# Adaptive AI Agent with Persistent Experience Memory

[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Three.js](https://img.shields.io/badge/Three.js-WebGL-black?logo=three.js&logoColor=white)](https://threejs.org/)
[![Supabase](https://img.shields.io/badge/Supabase-GoTrue_Auth-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**GenAI OJT Capstone Project — Group G146**

---

## 📌 Project Overview

**Adaptive AI Agent with Persistent Experience Memory** is a GenAI / Agentic AI capstone project exploring how an AI agent can retain reusable experiences from previous task executions and selectively reuse them in future related tasks.

Current LLMs can solve individual isolated tasks very well. However, when deployed across repeated workflows, a fundamental question emerges: **How can an agent remember useful strategies from previous executions, and how can it avoid relying on misleading, deprecated, or outdated experience?**

Our system is intentionally designed so that **the underlying LLM is never trained, fine-tuned, or modified**. Instead, adaptation occurs entirely through an external cognitive architecture managing:
- Structured experience retrieval with reliability-weighted ranking
- Reflection loops that extract concise, reusable strategies from completed runs
- Dynamic trust and reliability scoring calibrated via execution outcomes
- Experience lifecycle management that deprecates low-confidence memories

---

## 🎯 Research Question

> **Under what conditions does persistent experience memory improve future task performance, and can reliability-aware memory selection reduce the harm caused by misleading or outdated experiences?**

$$\text{Baseline: Memory OFF} \quad \longleftrightarrow \quad \text{Adaptive: Memory ON}$$

The evaluation framework records both positive transfer (improved accuracy, reduced latency, reuse of verified shortcuts) and potential negative transfer (overfitting to prior strategies or cascading failures).

---

## 🔄 Cognitive Architecture & Core Loop

```text
               ┌───────────────────────────────┐
               │          User Task            │
               └──────────────┬────────────────┘
                              │
                              ▼
               ┌───────────────────────────────┐
               │    Semantic Retrieval &       │◄────────┐
               │    Reliability-Aware Ranking   │         │
               └──────────────┬────────────────┘         │
                              │                          │
                              ▼                          │
               ┌───────────────────────────────┐         │
               │   Memory-Augmented Execution   │         │
               └──────────────┬────────────────┘         │
                              │                          │
                              ▼                          │
               ┌───────────────────────────────┐         │ (Experience
               │    Task Outcome Evaluation     │         │  Reuse)
               └──────────────┬────────────────┘         │
                              │                          │
                              ▼                          │
               ┌───────────────────────────────┐         │
               │  Post-Execution Reflection     │         │
               │  & Lesson Extraction           │         │
               └──────────────┬────────────────┘         │
                              │                          │
                              ▼                          │
               ┌───────────────────────────────┐         │
               │   Update Trust / Reliability   │         │
               └──────────────┬────────────────┘         │
                              │                          │
                              ▼                          │
               ┌───────────────────────────────┐         │
               │  Persist to Experience Store  │─────────┘
               └───────────────────────────────┘
```

---

## 💡 Why This Project

We selected GenAI for our 12-week OJT track, aiming to look beyond building another standard conversational wrapper:
- **Experience Loss**: Useful execution lessons are typically lost once an agent context window closes.
- **Uncurated Memory Harm**: Relevant memories are not always reliable. Recalling a broken strategy degrades task completion.
- **Continuous Calibration**: Memory requires systematic evaluation and reliability scoring, not passive storage.

---

## 🔬 Existing Work Studied

We analyzed foundational agent-learning and memory systems to ground our architecture:
- **Reflexion (Shinn et al., 2023)**: Self-reflection loops and verbal reinforcement learning.
- **Voyager (Wang et al., 2023)**: Continually evolving skill libraries for programmatic reuse.
- **Generative Agents (Park et al., 2023)**: Memory stream synthesis and associative reflection.
- **MemoryBank, Mem0, Zep, Letta, LangMem**: Contemporary persistent memory architectures and agent stores.

**Our distinct focus**: Explicit **experience-level reliability tracking** — measuring whether a retrieved lesson was genuinely beneficial for downstream task execution and adjusting future ranking weights accordingly.

---

## 🚀 Key Features Implemented

### 1. Interactive Web Experience & Cybernetic Landing Page
- **3D Neural Core (`ThreeMemoryCore.tsx`)**: Real-time WebGL particle system with gyroscopic orbital rings, dynamic mouse parallax, and cybernetic data streams.
- **Atomicwork-Style Performance Section**:
  - Audience switchers: *For Employees*, *For IT Teams*, *For Business Leaders*.
  - 4-layer stacked non-linear regression model showing agent performance curves over repeated trials.
  - Interactive scrub cursor, floating glass regression tooltip, and 95% Confidence Interval corridors.
- **Simulated Agent Reflection Stream**: Interactive terminal demonstrating real-time experience retrieval, memory matching (Voyager / Reflexion paradigms), and trust updates.
- **Provider Integrations Showcase**: Dynamic switcher for model providers (OpenAI, Anthropic Claude, Google Gemini, Grok, Ollama, Meta Llama).

### 2. Live Supabase Authentication & Google OAuth
- **Supabase GoTrue Integration**: Full session persistence, token refresh listeners, and user state management.
- **Google OAuth Support**: One-click **"Continue with Google"** with forced account selection (`prompt: 'select_account'`) and live Supabase callback redirection.
- **Local Dev Mock Fallback**: Smooth offline development mode when backend or cloud services are disconnected.

### 3. Central Agent Dashboard (`/dashboard`)
- **Real-Time Telemetry Cards**:
  - Total Experiences tracked (with weekly deltas)
  - Mean Trust Score (regression-calibrated)
  - Retrieval Latency (cosine similarity + metadata filtering)
  - Active Regression Model status (confidence R² calibration)
- **Identity & Session Management**: Live user badge with pulse indicator, direct "Back to Landing" navigation, and accessible **Sign Out** controls.
- **Recent Experience Stream**: Chronological feed of extracted lessons, trust scores, and reflection tags.

---

## 🛠️ Technology Stack

| Layer | Technologies | Notes |
|---|---|---|
| **Frontend Framework** | React 18, Vite 5, TypeScript | Responsive single-page application |
| **Styling & Design** | TailwindCSS 3.4, Vanilla CSS, Lucide Icons | Cybernetic glassmorphic design system |
| **3D & Graphics** | Three.js (WebGL Particle Core) | Interactive particle neural visualization |
| **Authentication & Store** | Supabase (GoTrue Auth, PostgreSQL + `pgvector`) | User auth & vector embeddings store |
| **Backend & Agent Service** | FastAPI, Python 3.11, SQLAlchemy, Alembic | Async execution pipeline *(in progress)* |
| **Orchestration & AI** | LangChain / LangGraph, LiteLLM | Agent reasoning & reflection loops |
| **Evaluation & Analysis** | Scikit-learn, Matplotlib, Pytest | Trust calibration models & A/B benchmarks |
| **Browser Extension** | TypeScript, Chrome Manifest V3 | Client access point *(planned)* |

---

## 📊 Current Status — Month 1

- [x] Initial problem definition and research question
- [x] Literature review of agent memory systems (Reflexion, Voyager, Mem0)
- [x] Initial system architecture & cognitive loop design
- [x] Full repository structure and engineering standards
- [x] Interactive frontend landing page with 3D neural core
- [x] Performance regression model & confidence corridor visualization
- [x] Supabase GoTrue authentication & Google OAuth integration
- [x] Central agent dashboard foundation (`/dashboard`)
- [ ] Automated experience extraction loop
- [ ] Persistent experience-memory backend service (FastAPI)
- [ ] Vector retrieval & reliability ranking pipeline
- [ ] Experience validation & trust score decay engine
- [ ] Controlled evaluation suite (Memory OFF vs. Memory ON)

---

## 📂 Repository Structure

```text
Adaptive-Agent-Memory-OJT-G146/
├── docs/                     # Comprehensive engineering & product documentation
│   ├── 01-project-overview.md
│   ├── 02-brd.md             # Business Requirements Document
│   ├── 03-prd.md             # Product Requirements Document
│   ├── 05-trd.md             # Technical Requirements Document
│   ├── 06-hld.md             # High-Level Architecture Design
│   ├── 07-database-design.md # PostgreSQL + pgvector schema
│   ├── 08-api-specification.md # REST API contracts
│   ├── 09-lld.md             # Low-Level Component Design
│   ├── 10-genai-architecture.md # Reflection & retrieval patterns
│   └── ...                   # Security, CI/CD, Roadmap, ADRs
├── frontend/                 # Interactive web app & central dashboard
│   ├── src/
│   │   ├── components/       # UI components (ThreeMemoryCore, AuthModal, etc.)
│   │   ├── context/          # React Contexts (AuthContext)
│   │   ├── lib/              # Supabase client & storage helpers
│   │   ├── pages/            # LandingPage, DashboardPage
│   │   ├── services/         # API client hooks for agent execution
│   │   ├── types/            # Domain TypeScript models
│   │   ├── App.tsx           # Route definitions (/ and /dashboard)
│   │   └── main.tsx          # Application entrypoint
│   ├── .env.example          # Environment variables template
│   ├── tailwind.config.js    # Design tokens & color palettes
│   └── package.json          # Dependencies & scripts
├── backend/                  # Application API layer (FastAPI / schema.sql)
├── ai-service/               # Core GenAI system (agent, retrieval, reflection)
├── infrastructure/           # Docker, Supabase, and cloud deployment configs
├── models/                   # Domain schemas (TaskExecution, Experience, Trust)
├── data/                     # Evaluation benchmarks and test datasets
└── README.md                 # Project documentation & setup index
```

---

## ⚡ Quick Start & Local Setup

### Prerequisites
- **Node.js** 18.0 or later
- **npm** 9.0 or later
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146.git
cd Adaptive-Agent-Memory-OJT-G146
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

### 3. Configure Environment Variables
Create a local `.env` file from the example:
```bash
cp .env.example .env
```

Configure your credentials:
```env
# Supabase Configuration
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-publishable-key

# Backend AI Service API
VITE_API_URL=http://localhost:8000

# Dev fallback (allows instant offline preview without cloud keys)
VITE_ENABLE_MOCK_FALLBACK=true
```

### 4. Run Locally
```bash
npm run dev
```

Open your browser at **`http://localhost:5173`**.

### 5. Type Checking & Production Build
```bash
# Type check without emitting files
npx tsc --noEmit

# Build production bundle
npm run build
```

---

## 👥 Team & Attribution

- **Kasat Sakshi Dattaprasad**
- **Sumit Das** ([@Sumit-ai-dev](https://github.com/Sumit-ai-dev))
- **Cohort Group:** G146

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
