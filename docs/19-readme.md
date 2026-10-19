# Documentation Guide & Repository Map

**Project:** Adaptive AI Agent with Persistent Experience Memory (AEMA)  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Canonical Documentation Index  

---

## 1. Documentation Index

The `docs/` directory contains complete, production-grade technical and architectural artifacts covering the entire 12-week capstone lifecycle:

| Document | Title | Description |
|---|---|---|
| [01-project-overview.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/01-project-overview.md) | Project Overview | Problem formulation, core product flow, MVP scope, and non-goals. |
| [02-brd.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/02-brd.md) | Business Requirements Document | Business value, target personas, ROI calculations, and market gap analysis. |
| [03-prd.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/03-prd.md) | Product Requirements Document | User stories, acceptance criteria, functional requirements, and metrics. |
| [04-ux-requirements.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/04-ux-requirements.md) | UX Requirements | Screen flows, wireframes, 3D visualizer interaction, and design tokens. |
| [05-trd.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/05-trd.md) | Technical Requirements Document | System non-functionals, latency budgets, scalability, and stack selection. |
| [06-hld.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/06-hld.md) | High-Level Design | End-to-end component architecture, LangGraph control loop, and network flow. |
| [07-database-design.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/07-database-design.md) | Database Design | Relational schemas, pgvector HNSW indexing, stored procedures, and audit ledgers. |
| [08-api-specification.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/08-api-specification.md) | API Specification | OpenAPI/Swagger specs, request/response contracts, and error structures. |
| [09-lld.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/09-lld.md) | Low-Level Design | Class diagrams, StateGraph node signatures, AST parsers, and type models. |
| [10-genai-architecture.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/10-genai-architecture.md) | GenAI Architecture | Prompt engineering, bilateral injection, reflector distillation, and BYOK. |
| [11-security.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/11-security.md) | Security & Guardrails | Key isolation, zero-retention policies, RLS multi-tenancy, and sandbox limits. |
| [12-testing.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/12-testing.md) | Testing Strategy | Pytest test taxonomy, invariant testing, adversarial fixtures, and mock modes. |
| [13-cicd.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/13-cicd.md) | CI/CD Pipeline | GitHub Actions workflow, quality gates, and automated test automation. |
| [14-observability.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/14-observability.md) | Observability & Telemetry | Structured JSON logging, LangSmith tracing, and operational metrics. |
| [15-deployment.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/15-deployment.md) | Deployment Architecture | Multi-environment topology, unified runner script, and zero-GPU strategy. |
| [16-cost-analysis.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/16-cost-analysis.md) | Cost & Resource Analysis | Node token consumption, economic ROI (61.4% savings), and storage sizing. |
| [17-roadmap.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/17-roadmap.md) | 12-Week Roadmap | Milestone delivery logs, Definition of Done, and risk mitigations. |
| [18-team-responsibilities.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/18-team-responsibilities.md) | Team Responsibilities | Clear governance between Kasat Sakshi Dattaprasad and Sumit Das. |
| [19-readme.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/19-readme.md) | Documentation Guide | Master catalog and codebase structural roadmap (this document). |
| [20-adrs.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/20-adrs.md) | Architecture Decision Records | Formal ADRs detailing choices, alternatives, rationales, and trade-offs. |
| [21-traceability.md](file:///Users/sakshidattaprasadkasat/Adaptive-Agent-Memory-OJT-G146/docs/21-traceability.md) | Traceability Matrix | End-to-end mapping from business requirements to code, APIs, and test suites. |

---

## 2. Codebase Directory Map

```text
Adaptive-Agent-Memory-OJT-G146/
├── ai-service/                    # Core Cognitive Engine & LangGraph StateGraph
│   ├── graph.py                   # 5-node cyclical workflow wiring
│   ├── state.py                   # TypedDict state contracts
│   ├── config.py                  # AI service configurations & thresholds
│   ├── nodes/                     # Discrete functional graph nodes
│   │   ├── retrieve_node.py       # Vector retrieval & composite ranking
│   │   ├── execute_node.py        # Bilateral prompt augmentation & execution
│   │   ├── evaluate_node.py       # Deterministic Python AST outcome evaluator
│   │   ├── reflect_node.py        # Structured 3-tuple lesson distillation
│   │   └── trust_node.py          # A-EMA update & Theorem 1 quarantine
│   ├── memory/                    # Persistent vector memory & embeddings
│   │   ├── embedder.py            # Local MiniLM-L6-v2 + Hash Fallback
│   │   └── postgres_store.py      # Supabase pgvector HNSW client
│   └── tools/                     # Agent execution tools (DuckDuckGo, Arxiv)
│
├── backend/                       # High-Performance FastAPI Gateway
│   ├── app/
│   │   ├── main.py                # FastAPI application initialization & CORS
│   │   ├── api/v1/                # Versioned REST endpoints (/agent, /memories)
│   │   └── core/                  # Security, auth, and database dependencies
│   ├── requirements.txt           # Production Python backend dependencies
│   └── venv/                      # Local Python virtual environment
│
├── frontend/                      # React 18 + TypeScript Web Application
│   ├── src/
│   │   ├── components/            # Visual components & Three.js 3D Canvas
│   │   │   ├── ThreeMemoryCore.tsx # Interactive 3D particle graph
│   │   │   └── ConversationDrawer.tsx # Chat history sidebar
│   │   ├── pages/                 # Route views (Dashboard, Studio, Settings)
│   │   └── services/              # API clients and Supabase auth bindings
│   ├── package.json               # Node dependencies & Vite build scripts
│   └── vite.config.ts             # Vite bundler configuration
│
├── packages/aema/                 # Portable AEMA TypeScript SDK
│   ├── src/                       # Client library implementation
│   └── package.json               # Standalone npm package definitions
│
├── tests/                         # Full Pytest Automated Verification Suite
│   ├── test_agent_graph.py        # End-to-end cognitive loop validation
│   ├── test_math_properties.py    # Formal A-EMA mathematical bounds
│   ├── test_failure_handling_and_quarantine.py # Theorem 1 quarantine proofs
│   ├── test_api_agent.py          # FastAPI endpoint integration tests
│   └── test_conversations.py      # Conversation management tests
│
├── benchmarks/                    # Empirical evaluation datasets & scripts
├── docs/                          # Comprehensive technical documentation (01-22)
├── run_demo.sh                    # Unified one-command demo launcher script
├── pyproject.toml                 # Root Python project configuration
└── README.md                      # Primary repository landing page
```

---

## 3. Developer Quick Reference

### Launching the Full Stack
```bash
./run_demo.sh
```

### Running Backend Tests
```bash
pytest tests/ -v --tb=short
```

### Compiling Frontend Bundle
```bash
cd frontend && npm run build && cd ..
```
