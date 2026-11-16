# Security Policy

## Supported Versions

We actively maintain and provide security updates for the following versions of the **Adaptive Experiential Memory Architecture (AEMA)**:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| `0.1.x` (SDK / MCP) | :white_check_mark: | Active support (current release) |
| `main` branch       | :white_check_mark: | Active development & mainline security patches |
| `< 0.1.0`           | :x:                | Unsupported |

---

## Reporting a Vulnerability

The AEMA project team takes security vulnerabilities seriously. If you discover a security vulnerability, we appreciate your help in disclosing it to us responsibly.

### 1. Preferred Method: GitHub Private Vulnerability Reporting
Please report security issues confidentially using GitHub's Private Vulnerability Reporting feature:
- Navigate to the [Security Advisories](https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146/security/advisories) tab.
- Click **"Report a vulnerability"** to open a private draft advisory.

### 2. Alternative Method: Security Contact Email
If you cannot use GitHub Security Advisories, send an encrypted or direct email to the core maintainers:
- **Primary Contact**: Sumit Das (`sumitds2005@gmail.com`)
- **Secondary Contact**: Kasat Sakshi Dattaprasad (`sakshisamu18@gmail.com`)
- **Subject Line**: `[SECURITY VULNERABILITY] AEMA - <Brief Description>`

> [!IMPORTANT]
> **Please DO NOT file public GitHub issues, pull requests, or discuss vulnerabilities publicly** until the issue has been triaged, patched, and a coordinated disclosure date has been agreed upon.

---

## Disclosure Response Timeline & SLAs

When a vulnerability report is submitted, the maintainers adhere to the following service level agreements:

- **Initial Acknowledgment**: Within **48 hours** of report receipt.
- **Triage & Impact Assessment**: Within **5 business days**, confirming whether the vulnerability is valid, reproducing the exploit, and assigning a preliminary CVSS score.
- **Remediation & Patch**: Security fixes are developed in private branches and tested against automated security test suites (`tests/test_security_hardening.py`).
- **Coordinated Disclosure**: Fixes are released in a patch release, accompanied by a public GitHub Security Advisory and CVE identifier. Public disclosure follows a standard **90-day responsible disclosure timeline**, or sooner if mutually agreed.

---

## Security Architecture & In-Scope Areas

We actively monitor and secure the following domains:

1. **Agent Sandboxing & Execution Isolation**:
   - Prevention of remote code execution (RCE) via agent code tools (`ai-service/tools/evaluator.py`).
   - Abstract Syntax Tree (AST) validation (`ai-service/security/code_sandbox.py`) enforcing restricted builtins and blocked system modules (`os`, `subprocess`, `socket`, `ctypes`, etc.).
   - POSIX process resource limits (`rlimit`) for memory, CPU time, file size, and fork bombs.
2. **Memory Poisoning & Prompt Injection**:
   - Delimiter boundary escaping and XML encapsulation (`<experiential_strategy>`, `<prohibited_pitfall>`) in memory retrieval prompts (`ai-service/security/sanitizer.py`).
   - Rejection of prompt injection vectors and synthetic adversarial feedback aimed at corrupting Bayesian trust scores ($p_i, q_i$).
3. **API Access Control & Rate Limiting**:
   - Authentication tokens on sensitive execution endpoints (`/agent/execute`) and destructive memory mutations (`DELETE /api/v1/memories/{memory_id}`).
   - Sliding-window IP rate limiting (`ai-service/security/rate_limiter.py`) preventing denial-of-service (DoS) against vector similarity searches.
4. **Credential & Secret Protection**:
   - Automated secret scanning on every push/PR via Gitleaks (`.github/workflows/gitleaks.yml`).
   - Automated environment sanitization in subprocess runners to prevent leaking host environment variables.

---

## Out-of-Scope Vulnerabilities

The following scenarios are considered out-of-scope for security rewards/bounties:
- Vulnerabilities requiring root/physical access to the host machine running the agent.
- Theoretical vulnerabilities without a viable proof-of-concept (PoC) demonstrating practical exploitability.
- Denial of Service attacks caused solely by flooding network infrastructure beyond standard rate-limit thresholds.
- Issues related to third-party dependencies where no patch or advisory is yet available upstream (though mitigations are welcome).

