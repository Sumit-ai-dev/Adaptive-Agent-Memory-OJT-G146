# Adaptive AI Agent with Persistent Experience Memory — Project Overview

## Project Identity
- **Track:** Generative AI / Agentic AI
- **Domain:** General-Purpose Agentic AI / AI Memory Systems
- **Duration:** 12 weeks
- **Team:** 2 students (Kasat Sakshi Dattaprasad, Sumit Das — Group G146)
- **Skill level:** Intermediate
- **Primary users:** Knowledge workers, researchers, AI developers, and evaluators
- **Constraint:** Fixed/unmodified LLM (no model fine-tuning or retraining; adaptation driven solely by external memory)

## Executive Summary
The Adaptive AI Agent with Persistent Experience Memory is an end-to-end task-oriented AI agent application that learns reusable lessons from previous task executions and selectively reuses them in future related tasks.

The system is intentionally designed so that **the underlying LLM is not trained, fine-tuned, or modified**. Instead, adaptation occurs externally through a persistent experience-memory architecture that handles experience retrieval, execution augmentation, outcome evaluation, reflection/extraction, reliability tracking, and memory lifecycle management.

## Core Product Flow
User task submission → experience retrieval & ranking → memory-augmented agent execution → outcome evaluation → post-execution reflection & strategy extraction → experience reliability update → persistence to experience store → future task reuse.

## MVP
1. Free-text task submission via central dashboard.
2. Experience retrieval ranked by semantic relevance and reliability.
3. Memory-augmented agent task execution.
4. Execution logging and unique task run tracing.
5. Task outcome evaluation and quality assessment.
6. Post-execution reflection and concise reusable lesson extraction.
7. Experience reliability/trust tracking based on repeated outcomes.
8. Experience lifecycle management (activation and deprecation of unreliable lessons).
9. Controlled evaluation framework (comparing Memory OFF baseline vs. Memory ON adaptive runs).
10. Central agent dashboard for task execution, experience inspection, and trust visualization.

## Out of Scope for MVP
- Fine-tuning, retraining, or modifying the underlying LLM.
- Storing uncurated raw conversation history or chat transcripts as memory.
- Multi-LLM provider support.
- Generalized external SDK / distribution package.
- Complex multi-agent swarms or unnecessary multi-agent architectures.
- Multi-user production SaaS infrastructure.
- Broad autonomous browser automation.
- Specialized coding-agent fine-tuning.
