# CI/CD Pipeline & Quality Assurance

**Project:** Adaptive AI Agent with Persistent Experience Memory (AEMA)  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Implemented & Verified in Production CI  

---

## 1. Pipeline Architecture

The Continuous Integration and Continuous Deployment (CI/CD) pipeline automates code quality enforcement, static analysis, unit testing, algorithmic invariant validation, and artifact compilation across every push and pull request.

```text
Developer Working Directory
         |
         v
Feature Branch (`feat/*`)
         |
         v
Pull Request to `main`
         |
         +---> GitHub Actions Automated Workflow (.github/workflows/ci.yml)
         |        |
         |        +---> Job 1: Backend & Algorithmic Invariants (Python 3.11)
         |        |        |
         |        |        +-- Code Checkout & Python Environment Setup
         |        |        +-- HuggingFace Cache Layer (`all-MiniLM-L6-v2`)
         |        |        +-- Core Dependency Installation (FastAPI, LangGraph, Pydantic)
         |        |        +-- Fallback Embedding Engine Verification (Deterministic Hash Embedder)
         |        |        +-- Full Pytest Test Suite Execution (33 Test Modules)
         |        |        +-- Mathematical Invariant Verification (A-EMA & Theorem 1 Quarantine)
         |        |
         |        +---> Job 2: Frontend & TypeScript Verification (Node.js 20)
         |                 |
         |                 +-- Code Checkout & Node.js 20 Setup
         |                 +-- Dependency Tree Resolution (`npm install`)
         |                 +-- TypeScript Strict Type Checking (`tsc -b`)
         |                 +-- Production Asset Bundle Compilation (`vite build`)
         |                 +-- AEMA TypeScript SDK Test Suite Execution
         |
         v
Branch Protection & Quality Gates (Zero Failures Required)
         |
         v
Automated PR Review & Copilot Recommendations
         |
         v
Squash Merge to `main` (Origin Stable)
         |
         v
Local / Staging Deployment via Unified Runner (`./run_demo.sh`)
```

---

## 2. Branching Strategy

Our development workflow enforces trunk-based stability with short-lived feature branches:

| Branch Name | Access / Protection | Purpose |
|---|---|---|
| `main` | Protected, PR required, CI passing required | Production-grade, always demonstrable release branch. |
| `feat/*` | Student feature branches | Ephemeral branches for focused capabilities (e.g., `feat/execution-studio-conversations`, `feat/quarantine-lifecycle`). |
| `fix/*` | Student bugfix branches | Targeted regression and hotfix patches. |

### Branching Rules
1. Never push directly to `main`.
2. All feature branches branch off latest `main`.
3. Branches are kept short-lived (1-3 days) to minimize merge friction.
4. Squash merging is preferred on PR merge to maintain a linear, bisectable commit history.

---

## 3. Pull Request Standards

Every Pull Request submitted to the repository must fulfill the structured engineering template:

1. **Problem Statement:** Clear articulation of the defect, architectural gap, or requested feature.
2. **Solution Overview:** Detailed description of technical changes, module additions, or schema adjustments.
3. **Traceability Mapping:** Explicit citation of related Business Requirements (`BR-*`) or Technical Requirements (`TR-*`).
4. **Verification Evidence:** Terminal transcripts of test execution (`pytest`, `npm run build`), including passing counts and execution times.
5. **Security & Secret Audit:** Explicit verification that no API keys, tokens, or confidential variables are staged.
6. **Zero Em-Dash Compliance:** Strict repository hygiene ban on em-dash characters in documentation and code comments.

---

## 4. Automated Quality Gates

Pull Requests are blocked from merging if any of the following gates fail:

| Quality Gate | Tool / Mechanism | Pass Criterion |
|---|---|---|
| **Python Backend Unit Tests** | `pytest` 8.x | 100% pass across all 33 test modules in `tests/`. |
| **Algorithmic Invariant Tests** | `test_math_properties.py`, `test_failure_handling_and_quarantine.py` | Strict adherence to A-EMA bounds ($S \in [0.0, 1.0]$) and Theorem 1 ($k^* = 3$). |
| **TypeScript Type Safety** | `tsc -b` | Zero compiler errors under strict TypeScript configuration. |
| **Vite Production Bundling** | `vite build` | Clean asset generation with zero unresolved chunks or missing imports. |
| **Secret Scanning** | Local pre-commit check & CI environment scan | Zero plaintext secrets (`GROQ_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`). |
| **Offline Embedder Resiliency** | Local hash embedder fallback | Test harness operates deterministically without external model downloads. |

---

## 5. GitHub Actions Workflow Configuration

The primary CI pipeline is defined in `.github/workflows/ci.yml`.

### Key Features of the CI Pipeline
- **Smart Model Caching:** HuggingFace cache layer prevents multi-gigabyte re-downloads across runs, keeping test execution under 3 minutes.
- **Graceful Embedder Degradation:** The pipeline installs core requirements without heavyweight PyTorch by default, leveraging AEMA's built-in deterministic hash embedder with adjusted cosine gates (`SIMILARITY_THRESHOLD=0.10`). Best-effort installation of `sentence-transformers` is attempted without failing the build.
- **Matrix Parallelism:** Backend Python validation and frontend TypeScript bundle validation run concurrently to shorten feedback loops.

---

## 6. Local Pre-Commit & Verification Commands

Developers must run the following suite locally before pushing any branch:

```bash
# 1. Backend test suite verification
pytest tests/ -v --tb=short

# 2. Targeted invariant and regression validation
pytest tests/test_math_properties.py tests/test_failure_handling_and_quarantine.py -v

# 3. Frontend compilation and typecheck
cd frontend
npm run build
cd ..
```
