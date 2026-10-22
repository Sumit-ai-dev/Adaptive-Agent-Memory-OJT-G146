# 🐳 Docker Deployment & Orchestration Guide

Complete guide for containerizing and running the **Adaptive Agent Memory (AEMA)** platform using Docker and Docker Compose.

---

## 🏛 Architecture Overview

The multi-container topology is orchestrated via `docker-compose.yml`:

```
                    ┌─────────────────────────┐
                    │      Client Browser     │
                    │   http://localhost:3000 │
                    └────────────┬────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │     aema-frontend     │
                     │ (Nginx 1.27 + Vite SPA│
                     └───────────┬───────────┘
                                 │ Reverse Proxy (/api/*)
                                 ▼
                     ┌───────────────────────┐         ┌───────────────────────┐
                     │     aema-backend      │◄────────┤       aema-mcp        │
                     │  (FastAPI + LangGraph)│         │ (Node.js MCP Server)  │
                     │  http://backend:8000  │         │ (Claude / Cursor MCP) │
                     └───────────┬───────────┘         └───────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   aema_data (Volume)  │
                     │ SQLite Persistent DB  │
                     └───────────────────────┘
```

---

## 🚀 Quick Start (Single Command)

To build and start all services in detached mode:

```bash
docker compose up --build -d
```

### Check Service Health & Status
```bash
docker compose ps
```

### View Realtime Logs
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend only
docker compose logs -f frontend
```

---

## 🔍 Service Endpoints & Verification

| Service | Port | Endpoint | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | `3000` | `http://localhost:3000` | Interactive React Dashboard |
| **Frontend Health** | `3000` | `http://localhost:3000/healthz` | Nginx Health Probe |
| **Backend API** | `8000` | `http://localhost:8000/api/health` | FastAPI System Health |
| **API Docs (Swagger)** | `8000` | `http://localhost:8000/api/docs` | OpenAPI Specification |
| **MCP Server** | Stdio | `docker run -i aema/mcp:0.1.0` | Claude / Cursor Integration |

---

## 🔒 Security & Optimization Highlights

1. **Multi-Stage Builds**:
   - `frontend`: 22.7 MB final image using `nginx:alpine` runtime.
   - `backend`: CPU-optimized wheels, removing compile-time dependencies.
   - `mcp`: 79.5 MB lightweight Alpine runner.
2. **Non-Root Execution**:
   - `appuser` (UID 10001) in Backend.
   - `node` (UID 1000) in MCP.
   - Hardened Nginx unprivileged capabilities in Frontend.
3. **Automated Healthchecks**:
   - Backend relies on Python standard library (`urllib.request`) probes.
   - Frontend uses Nginx lightweight `wget -qO- /healthz`.
   - Dependent services utilize `depends_on: condition: service_healthy` to guarantee zero-downtime ordered startup.

---

## 🛑 Stopping & Teardown

```bash
# Stop containers without removing persistent data
docker compose down

# Stop containers and purge volumes (fresh start)
docker compose down -v
```
