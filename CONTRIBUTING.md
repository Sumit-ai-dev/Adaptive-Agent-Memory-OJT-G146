# Contributing to AEMA

Thank you for your interest in contributing to **AEMA (Adaptive Experiential Memory Architecture)**! We welcome contributions ranging from bug fixes, security hardening, and algorithmic improvements to documentation enhancements and client SDK integrations.

---

## 1. Development Principles

- **Focused, Atomic Changes**: Scope each pull request to a single feature, bug fix, or architectural objective. Avoid giant, multi-concern PRs.
- **Defense-in-Depth Security**: Adhere strictly to the OpenSSF Scorecard principles, AST code execution sandboxing, input sanitization, and credential protection guidelines.
- **Architectural Traceability**: Document significant design and technical decisions in Architecture Decision Records ([`docs/20-adrs.md`](docs/20-adrs.md)).
- **Zero Hallucination Testing**: Back every code change with automated regression and integration tests verifying both positive and adversarial execution paths.
- **Conventional Commits**: Structure all commit messages according to the [Conventional Commits](https://www.conventionalcommits.org/) specification (e.g. `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- **Documentation Parity**: Keep `README.md`, package documentation, and API specifications synchronized whenever contracts, routes, or behaviors evolve.

---

## 2. Monorepo Structure

| Directory | Scope & Purpose | Primary Languages / Frameworks |
|---|---|---|
| [`/backend`](backend/) | FastAPI orchestration service, memory CRUD, trust updates, SQLite & Postgres hybrid stores | Python 3.11+, FastAPI, Pydantic |
| [`/ai-service`](ai-service/) | 5-node LangGraph execution cycle, AST safety validator, subprocess sandbox, prompt sanitizer | Python 3.11+, LangGraph, AST, NumPy |
| [`/packages/aema`](packages/aema/) | Official AEMA TypeScript SDK and Model Context Protocol (MCP) server | TypeScript 5.5+, Node.js, MCP SDK |
| [`/frontend`](frontend/) | Real-time experiential memory dashboard and 3D force-directed memory topology graph | React 18, Vite, TailwindCSS, Three.js |
| [`/tests`](tests/) | Comprehensive test suite covering lifecycle, trust dynamics, security sandbox, and API routes | Pytest, Hypothesis, TestClient |
| [`/docs`](docs/) | Master revision guides, mathematical derivations, architecture specifications, and ADRs | Markdown, LaTeX |

---

## 3. Local Development Setup

### Prerequisites
- **Python**: 3.11 or later
- **Node.js**: 18.0 or later (Node 20+ recommended)
- **Package Managers**: `pip` and `npm`
- **Git**

### A. Python Environment Setup
```bash
# Clone the repository
git clone https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146.git
cd Adaptive-Agent-Memory-OJT-G146

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install core and development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

### B. TypeScript SDK Setup
```bash
cd packages/aema
npm install
npm run build
```

### C. Frontend Dashboard Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

---

## 4. Git Hooks & Secret Scanning

We enforce automated secret detection to prevent API tokens, credentials, and private keys from entering git history.

- **Automated CI**: Every pull request and push is scanned by Gitleaks via [`.github/workflows/gitleaks.yml`](.github/workflows/gitleaks.yml).
- **Local Pre-Commit Hook**: Install pre-commit protection by running:
  ```bash
  ./scripts/install_git_hooks.sh
  ```
  Or via `pre-commit`:
  ```bash
  pre-commit install
  ```
- **Manual Verification**: Run `gitleaks detect --verbose` at any time to inspect your working tree and git history.

---

## 5. Testing & Quality Assurance

All PRs must pass the automated test suites before merging.

### Running Python Tests
```bash
# Run full Pytest suite (370+ unit and integration tests)
PYTHONPATH=. pytest tests/ -v

# Run targeted security and sandboxing suite
pytest tests/test_security_hardening.py -v

# Run experiential memory lifecycle and trust dynamics tests
pytest tests/test_experiential_lifecycle_verification.py tests/test_trust_dynamics.py -v
```

### Running TypeScript SDK Tests
```bash
cd packages/aema
# Run mathematical invariant & MCP tool adapter tests
npm test

# Type-check TypeScript codebase
npm run build
```

---

## 6. Security & Sandboxing Guidelines

When adding or modifying agent execution code, adhere to these mandatory security patterns:

1. **AST Code Sandboxing**:
   - Untrusted code (both candidate solutions and request-controlled test suites) must pass through [`validate_code_safety`](ai-service/security/code_sandbox.py) before execution.
   - Prohibited modules include `os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `pathlib`, and dynamic introspection hooks (`__subclasses__`, `__globals__`, `globals()`, `__builtins__`).
2. **Subprocess Sanitization**:
   - Subprocess environments must purge secrets via `get_sanitized_subprocess_env()` and enforce POSIX `rlimit` process resource bounds (CPU, memory, file writes).
3. **Prompt Injection Defense**:
   - External inputs must pass heuristic injection checks (`detect_prompt_injection_heuristic`).
   - Memory lessons placed into prompts must be sanitized via `sanitize_memory_content()` to escape delimiter breakout tags (`<experiential_strategy>`, `<prohibited_pitfall>`).
4. **Administrative Authentication**:
   - Destructive endpoints (`DELETE /api/v1/memories/{id}`, `/executions`) require `ADMIN_API_KEY` verification using constant-time `secrets.compare_digest`.
   - When `ADMIN_API_KEY` is unconfigured, endpoints must **fail closed** with HTTP 503.
5. **Rate Limiting**:
   - Public agent execution endpoints must be gated through [`SlidingWindowRateLimiter`](ai-service/security/rate_limiter.py) with bounded LRU eviction to prevent denial-of-service and state leaks.

---

## 7. Package Registries & Distribution

AEMA is published to both Python and JavaScript ecosystems:

- **PyPI (Python)**: [`aema`](https://pypi.org/project/aema/)
  ```bash
  pip install aema
  ```
- **npm (TypeScript / Node.js)**: [`@sumitaidev/aema`](https://www.npmjs.com/package/@sumitaidev/aema)
  ```bash
  npm install @sumitaidev/aema
  ```

When contributing to packaging:
- Ensure `packages/aema/package.json` retains `"name": "@sumitaidev/aema"`.
- Ensure version increments follow [Semantic Versioning](https://semver.org/).
- Build and test artifacts locally (`npm run build`, `python -m build`) before drafting release PRs.

---

## 8. Pull Request & Review Process

1. **Create a Topic Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```
2. **Make Changes and Test Locally**:
   - Ensure all Python and TypeScript tests pass.
   - Run `git status` to verify no secrets, logs, or untracked cache files are staged.
3. **Commit with Conventional Messages**:
   ```bash
   git commit -m "feat(retrieval): implement Wilson LCB scoring for low-sample memories"
   ```
4. **Push and Open a Pull Request**:
   - Provide a clear, detailed PR description outlining the motivation, changes, and verification evidence.
   - Link any associated issues or tracking items.
   - Verify that all CI workflows (Automated Tests, Gitleaks, CodeQL) complete successfully with green status.
5. **Code Review & Feedback**:
   - Address peer review and automated analysis comments promptly.
   - Rebase on latest `main` if merge conflicts arise.
