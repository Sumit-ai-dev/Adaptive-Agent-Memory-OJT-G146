# Security Design

**Project:** Adaptive AI Agent with Persistent Experience Memory  
**Group:** G146 (GenAI / Agentic AI OJT Capstone)  
**Status:** Approved Security Specification (Month 2 Specification)  

---

## Authentication

- **Provider:** Managed Supabase Auth (GoTrue engine) handles user registration, password hashing (bcrypt), email verification, and session lifecycle.
- **Token Mechanism:** Authentication is stateless via cryptographically signed JSON Web Tokens (JWT).
- **Session Verification:** Protected FastAPI endpoints decode the JWT using Supabase public JWT secrets via `fastapi.security.HTTPBearer`, extracting the caller's UUID (`auth.uid()`).
- **Token Expiry & Refresh:** Access tokens expire after 1 hour; the React frontend automatically manages token rotation using refresh tokens.

---

## Authorization

- **Row-Level Security (RLS):** All Supabase PostgreSQL tables (`experiences`, `task_executions`, `trust_history`, `execution_experiences`) enforce RLS at the database engine level.
- **Tenant Isolation:**
  - `task_executions`: Users can strictly read and write only rows where `user_id = auth.uid()`.
  - `experiences`: Users can inspect public active experiences or their own private experiences (`status = 'active' OR user_id = auth.uid()`). Modification is restricted to the owning user.
  - `trust_history`: Append-only audit table; modifications are restricted to the backend service role key.
- **Role Hierarchy:** Supports standard `ANALYST` (run tasks, view memories) and `ADMIN` (manage global benchmarks, purge quarantined records).

---

## Data Protection

- **Transport Security:** All client-to-backend and backend-to-database communications are encrypted in transit using TLS 1.3 / HTTPS.
- **Zero-Storage BYOK (Bring Your Own Key):**
  - Third-party LLM API keys (Groq, Google Gemini) supplied by users are never written to the PostgreSQL database or persistent disk.
  - Keys are passed via session headers or held temporarily in volatile memory for the duration of the execution context.
- **Secret Management:** Backend system credentials (Supabase Service Role Key, Database connection strings, LangSmith API Keys) reside strictly in `.env` environment variables and are excluded from version control via `.gitignore`.
- **Synthetic Demonstration Data:** For research benchmarks and public demonstrations, exclusively open-domain datasets (ALFWorld, HotpotQA) or synthetic tasks are used; no proprietary or personal PII is processed.

---

## Tool Security

- **Restricted Web Retrieval:** The web search (DuckDuckGo) and web reader (Jina AI) tools are constrained to read-only HTTP GET operations.
- **Sandboxed Code Execution:** The Python REPL tool runs in an isolated sub-process with restricted standard libraries, execution timeout limits (5 seconds max), and disabled filesystem write access.
- **Network Boundaries:** External tool calls cannot access internal network services, private IP ranges (RFC 1918), or cloud metadata endpoints (`169.254.169.254`).

---

## API Security

- **CORS Restrictions:** FastAPI applies strict Cross-Origin Resource Sharing (CORS) middleware, permitting requests solely from approved frontend origins (`http://localhost:5173` and deployed Vercel domains).
- **Payload Validation:** Pydantic v2 validates all incoming request bodies, sanitizing strings, checking boundary constraints, and preventing buffer or injection payloads.
- **Rate Limiting:** Gateway rate limiting throttles abusive task execution loops (e.g., maximum 30 task runs per minute per user).
- **Secure Headers:** Backend responses include standard OWASP defensive headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`).

---

## AI Security

- **Prompt Injection Defense:** User-supplied task queries and retrieved memory strategies are treated strictly as untrusted data. They are enclosed within explicit XML delimiters (`<task>`, `<retrieved_experiences>`) and preceded by strong system instructions forbidding context overrides.
- **Negative Constraints (Pitfall Enforcement):** Retrieved pitfalls explicitly restrict the agent from executing harmful anti-patterns learned from past failures.
- **Quarantine Isolation:** Experiences with degraded trust scores ($S < 0.35$) are instantly quarantined (`status = 'deprecated'`). They are completely excluded from retrieval queries, preventing malicious or hallucinated memories from propagating negative transfer.
- **Audit Immutability:** Every prompt, tool call, output, and trust transition is permanently logged in PostgreSQL, enabling full post-incident forensic inspection.

---

## Important Product Rule

The Adaptive AI Agent is an **autonomous research and decision-support agent**. In high-stakes production environments, any destructive tool action (e.g., file deletion, external communication, financial transaction) must require explicit **Human-in-the-Loop (HITL)** approval before execution.
