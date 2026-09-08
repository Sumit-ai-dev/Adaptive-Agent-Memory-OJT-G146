# Adaptive AI Agent with Persistent Experience Memory

**GenAI OJT Project — G146**

## Overview

We are building a general-purpose AI agent that learns reusable experiences from previous task executions and selectively reuses them in future related tasks.

The underlying LLM is not trained or fine-tuned.

Instead, the system maintains a persistent experience memory and uses retrieval, reflection, validation, and reliability-aware memory management to adapt future task execution.

## Core Idea

```text
User Task
    ↓
Retrieve Relevant Experiences
    ↓
Agent Execution
    ↓
Evaluate Outcome
    ↓
Reflect / Extract Experience
    ↓
Update Reliability
    ↓
Persist Experience
    ↓
Future Tasks
```

## Research Question

Does persistent, validated experience memory improve future task performance compared with the same agent operating without memory?

## Core Components

- **Agent**: Coordinates execution workflows and utilizes retrieved memory to handle tasks.
- **Experience Store**: Persists structured experiences, lessons, and reliability scores.
- **Retriever**: Performs similarity and reliability ranking to fetch relevant past experiences.
- **Reflector**: Analyzes completed executions to extract concise, reusable strategies.
- **Validator / Reliability Tracker**: Updates trust scores based on observed execution outcomes.
- **Experience Lifecycle Manager**: Deprecates unreliable experiences and activates vetted lessons.
- **Evaluation System**: Runs controlled comparisons (Memory OFF vs. Memory ON) across standard tasks.
- **Central Dashboard**: Provides visibility into task runs, experience store state, and trust history.

## What Is an Experience?

The system does not simply save raw chat history.

It attempts to extract reusable lessons or strategies from previous task executions.

**Example:**
> *"For research tasks involving conflicting claims, verify important claims against multiple independent sources before finalizing."*

## Evaluation

The system will eventually compare:

$$\text{Memory OFF} \quad \text{vs.} \quad \text{Memory ON}$$

and investigate whether persistent experience memory improves performance on related future tasks.

Evaluation will record both positive and negative effects of memory.

## Project Scope

The project focuses on persistent experience memory, relevant retrieval, reflection, validation, reliability tracking, and experience lifecycle management.

The browser extension is an optional access point and is not the core of the system.

## Team

- **Kasat Sakshi Dattaprasad**
- **Sumit Das**
- **Group:** G146

## Repository Structure

```text
Adaptive-Agent-Memory-OJT-G146/
├── docs/             # Project, product, technical, and evaluation documentation
├── frontend/         # Central dashboard for interaction, memory, and evaluation
├── backend/          # Application and API layer connecting frontend to agent services
├── ai-service/       # Core GenAI system (agent, retrieval, reflection, validation)
├── data/             # Evaluation datasets, test tasks, and experiment outputs
├── models/           # Application and domain models (Task, Experience, Trust, etc.)
├── tests/            # Unit, integration, system, and evaluation tests
├── infrastructure/   # Docker, environment, and deployment configurations
├── scripts/          # Setup, seeding, experiment, and utility scripts
├── .github/          # GitHub Actions CI/CD workflows
├── CONTRIBUTING.md   # Guidelines for contributing to the repository
├── LICENSE           # Project license (MIT)
└── README.md         # Project overview and index
```

## Development Status

**Current phase:** Repository Initialization / Documentation

The technical architecture and technology stack will be finalized after research and architecture evaluation.
