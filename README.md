# Adaptive AI Agent with Persistent Experience Memory

**GenAI OJT Project — Group G146**

## Project Overview

Adaptive AI Agent with Persistent Experience Memory is a GenAI/Agentic AI project exploring how an AI agent can retain reusable experience from previous tasks and use it in future tasks.

Current LLMs can solve individual tasks very well, but repeated task execution raises an important question: How can an agent remember useful experience from previous tasks, and how can it avoid relying on misleading or outdated experience?

Our project focuses on an external experience-memory system built around an LLM rather than training or fine-tuning a new LLM. Memory here does not simply mean conversation history; an experience is intended to be a reusable lesson or strategy extracted from a previous task.

## Research Question

> **Under what conditions does persistent experience memory improve future task performance, and can reliability-aware memory selection reduce the harm caused by misleading or outdated experiences?**

The project investigates:
- Experience retrieval
- Evaluation of task outcomes
- Reflection and experience extraction
- Experience validation
- Trust and reliability scoring
- Future experience reuse

## Core Idea

The proposed system loop for learning from task execution:

```text
Task
  ↓
Retrieve relevant experience
  ↓
Execute task
  ↓
Evaluate outcome
  ↓
Reflect / extract reusable lesson
  ↓
Validate experience
  ↓
Update trust / reliability
  ↓
Persist experience
  ↓
Reuse in future tasks
```

The system is intended to learn from task experience without changing the underlying LLM. In this proposed loop, experiences should not only be retrieved based on relevance; their reliability should also be considered and updated based on observed usefulness over time.

## Why This Project

We selected GenAI for our 12-week OJT track, but aimed to look beyond building another standard LLM application.

The project direction came from analyzing what happens when AI systems are used across repeated tasks:
- Useful experience may be lost once execution ends.
- Relevant memories may not always be reliable.
- Old or misleading experience can affect future decisions.
- Therefore, memory needs continuous evaluation, not just storage.

## Existing Work We Studied

We studied existing agent-learning and memory approaches to understand what has already been explored and to narrow our own research focus:
- Reflexion
- Voyager
- Generative Agents
- MemoryBank
- Mem0
- Zep
- Letta
- LangMem

Our focus is specifically on experience-level reliability: whether a past experience was actually useful for a later task, and how that should affect future reuse.

## Design & Scope Exploration

### Model Choice
We considered whether the system should be tightly coupled to one LLM or keep the memory layer independent of a particular model.

*Current direction:* Keep the memory layer as generic as reasonably possible while initially using one LLM provider for implementation.

### SDK Direction
We explored whether the memory system could eventually be packaged as a reusable SDK for integration into different AI applications, including narrower ideas such as coding-agent use cases.

*Decision:* For the OJT, the priority is validating and implementing the experience-memory system rather than building a complete production SDK and multiple integrations. The SDK remains a possible future productization direction.

### Browser Extension
The browser extension is being considered as a client through which the same memory system can eventually be accessed.

*Note:* The SDK is not yet built, and the browser extension is not yet fully integrated with the memory backend.

## System Architecture

```text
Dashboard + Browser Extension
            ↓
          FastAPI
            ↓
     Agent / Orchestration
            ↓
       LLM + Tools
            ↓
   Experience Intelligence
   ┌──────────────────────┐
   │ Retrieve             │
   │ Reflect              │
   │ Validate             │
   │ Trust / Reliability  │
   └──────────────────────┘
            ↓
   PostgreSQL + pgvector
```

Evaluation and observability are intended to operate across the execution pipeline so that task outcomes and memory usefulness can be measured.

## Current Status — Month 1

- [x] Initial problem definition
- [x] Research direction and research question
- [x] Existing approaches reviewed
- [x] Initial system architecture
- [x] Repository structure
- [x] Frontend/dashboard foundation
- [x] Authentication foundation
- [x] Initial backend/database direction
- [ ] Experience extraction loop
- [ ] Persistent experience-memory backend
- [ ] Retrieval pipeline
- [ ] Validation and reliability updates
- [ ] Controlled evaluation

## Technology Stack

### Frontend
- React
- TypeScript
- Tailwind CSS

### Browser Extension
- TypeScript
- Chrome Manifest V3

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic

### AI / Agent
- Python
- LLM provider integration
- Embeddings
- Custom/lightweight orchestration initially

### Memory / Database
- PostgreSQL
- pgvector

### Authentication
- Supabase Auth

### Testing / Evaluation
- pytest
- Python evaluation scripts
- matplotlib

### Infrastructure / Development
- Docker
- GitHub Actions

## Repository Structure

```text
docs/           # Project documentation
frontend/       # Dashboard/client interface
backend/        # API and backend services
ai-service/     # Agent, memory, retrieval and AI-related logic
data/           # Task, experience and evaluation data
models/         # Project data models
tests/          # Unit, integration and evaluation tests
infrastructure/ # Deployment/infrastructure configuration
scripts/        # Setup, seed and evaluation utilities
```

## Development Direction

```text
Baseline Agent
  → Experience Extraction
  → Persistent Storage
  → Retrieval
  → Reflection + Validation
  → Trust / Reliability
  → Controlled Evaluation
```

The next major phase is moving from the current research/client foundation into the actual adaptive-memory backend and measurement loop.

## Team

- Sakshi Kasat
- Sumit Das

---

**Status Note:**  
Current stage: Month 1 / foundation and research phase.

The dashboard currently contains some mock/hardcoded interface data while the actual backend and memory pipeline are being developed. These values should not be interpreted as measured system results.
