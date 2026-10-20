# Contributing Guidelines

Thank you for contributing to the **Adaptive AI Agent with Persistent Experience Memory** project.

## Development Principles

- **Focused Changes**: Keep pull requests and changes scoped to specific tasks, user stories, or fixes.
- **Security & Hygiene**: Never commit secrets, API keys, credentials, or `.env` files to the repository.
- **Architectural Documentation**: Document all meaningful architectural and technical decisions in Architecture Decision Records (`docs/20-adrs.md`).
- **Testing**: Add tests (unit, integration, or evaluation) alongside any new functionality or modules.
- **Clear Commit Messages**: Use standard conventional commit formats (e.g., `feat:`, `fix:`, `docs:`, `chore:`).
- **Documentation Synchronization**: Keep project documentation (`docs/`) synchronized whenever specifications, interfaces, or designs evolve.

## Secret Scanning & Gitleaks

We enforce automated secret detection to prevent API keys, private tokens, and credentials from entering git history.

- **Automated CI**: Every pull request and push to `main` is scanned via `.github/workflows/gitleaks.yml`.
- **Local Pre-Commit Hook**: You can install the pre-commit hook by running:
  ```bash
  ./scripts/install_git_hooks.sh
  ```
  Or via `pre-commit`:
  ```bash
  pre-commit install
  ```
- **Manual Scan**: Run `gitleaks detect --verbose` at any time to scan git history locally.

