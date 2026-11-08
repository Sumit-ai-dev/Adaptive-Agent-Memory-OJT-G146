# Contributing to AEMA

Welcome to **AEMA (Adaptive Experiential Memory Architecture)**! We are excited to welcome contributors of all experience levels. Whether you are fixing a typo in documentation, improving test coverage, or implementing a new feature, your contributions make this project better for everyone.

This project participates in open-source programs like **Google Summer of Code (GSoC)** and follows standard open-source best practices. Please take a moment to review these guidelines before getting started.

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for everyone, regardless of background or level of experience. Please treat all contributors with respect, courtesy, and constructive feedback.

---

## How to Contribute

### 1. Reporting Bugs
- Search [existing issues](https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146/issues) to ensure the bug hasn't already been reported.
- If it hasn't, open a new issue with:
  - A clear and descriptive title
  - Step-by-step instructions to reproduce the problem
  - Expected vs. actual behavior
  - System environment details (OS, Python version, Node.js version)
  - Relevant error logs or stack traces

### 2. Suggesting Features & Enhancements
- Open a feature request issue before writing code to discuss the motivation, design, and scope.
- Discussing ideas early ensures alignment with project roadmap and avoids duplicate effort.

### 3. First-Time Contributors
- Look for issues tagged [`good first issue`](https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146/labels/good%20first%20issue) or [`help wanted`](https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146/labels/help%20wanted).
- **Claim an issue**: Leave a comment on the issue asking to be assigned before starting work so multiple people do not duplicate the same task.

---

## Getting Started & Environment Setup

### Prerequisites
- **Git**
- **Python 3.11+**
- **Node.js 18+** & **npm**

### 1. Fork and Clone
```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork locally
git clone https://github.com/<your-username>/Adaptive-Agent-Memory-OJT-G146.git
cd Adaptive-Agent-Memory-OJT-G146

# 3. Add the upstream remote
git remote add upstream https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146.git
git fetch upstream
```

### 2. Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

### 3. Set Up TypeScript SDK (Optional)
If you are working on the TypeScript SDK or Model Context Protocol (MCP) server:
```bash
cd packages/aema
npm install
npm run build
cd ../..
```

### 4. Install Pre-Commit Hooks
We use pre-commit hooks to prevent secrets and sensitive keys from entering git history:
```bash
./scripts/install_git_hooks.sh
# or
pre-commit install
```

---

## Development Workflow

### 1. Create a Topic Branch
Always branch off the latest `upstream/main`:
```bash
git checkout main
git pull upstream main
git checkout -b feat/your-feature-name  # or fix/issue-number-short-description
```

### 2. Coding Standards
- **Python**: Follow PEP 8 guidelines. Include type annotations (`typing`) and clear docstrings for public functions and classes.
- **TypeScript**: Use strict typing and follow ESLint formatting standards.
- **Security**: Never hardcode API keys, passwords, or personal credentials.
- **Tests**: Every new feature or bug fix must include corresponding tests.

### 3. Run Tests Locally
Make sure all test suites pass locally before submitting:

```bash
# Run Python test suite
pytest tests/ -v

# Run TypeScript SDK tests (if touching packages/aema)
cd packages/aema && npm test && cd ../..
```

### 4. Commit Guidelines
We use the [Conventional Commits](https://www.conventionalcommits.org/) convention:

| Type | When to use |
|---|---|
| `feat:` | Adding a new feature or functionality |
| `fix:` | Fixing a bug |
| `docs:` | Documentation changes only |
| `test:` | Adding or updating tests |
| `refactor:` | Code restructuring without behavior changes |
| `chore:` | Tooling, dependencies, or repository maintenance |

**Example:**
```bash
git commit -m "fix(retrieval): prevent empty array index out of bounds error"
```

### 5. Push and Open a Pull Request
```bash
git push origin feat/your-feature-name
```
Then navigate to GitHub and open a Pull Request targeting `main`.

---

## Pull Request Checklist

Before submitting your PR, please ensure:
- [ ] My PR targets the `main` branch.
- [ ] My changes are focused on a single issue or feature.
- [ ] I have tested my changes locally (`pytest tests/` and `npm test`).
- [ ] All new and existing tests pass.
- [ ] Relevant documentation or docstrings have been updated.
- [ ] My commit messages follow the Conventional Commits format.
- [ ] No temporary files, logs, or sensitive keys are included in git diff.

---

## Getting Help & Community

Have questions or need guidance?
- **GitHub Issues**: For bug reports, feature proposals, and task assignments.
- **GitHub Discussions**: For general questions, architectural ideas, and GSoC project discussions.
- Feel free to tag a maintainer on your issue or PR if you need help or review.

Thank you for contributing to AEMA!
