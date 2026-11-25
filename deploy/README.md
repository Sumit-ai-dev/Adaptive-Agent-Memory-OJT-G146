# Deploying AEMA to Vultr Cloud

This directory provides production deployment configs for running the AEMA full-stack application (React Frontend + FastAPI Backend + Experiential Memory Engine) on Vultr or any standard cloud VPS.

---

## Deployment Options

### Option 1: Standalone Single-Container Deployment (Simplest & Fast)
Runs both the compiled React frontend (served by Nginx on port 80) and the FastAPI backend (on port 8000) inside **one single container**. Uses persistent SQLite storage.

```bash
# 1. Clone the repository on your Vultr server
git clone -b feat/multi-provider-byok-models https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146.git aema
cd aema

# 2. Build the unified Docker image
docker build -f Dockerfile.standalone -t aema:latest .

# 3. Run the container on port 80
docker run -d \
  --name aema-app \
  --restart unless-stopped \
  -p 80:80 \
  -v aema_data:/data \
  aema:latest

# 4. Open http://<YOUR_VULTR_IP> in your browser!
```

---

### Option 2: Multi-Container Deployment with PostgreSQL + pgvector
Runs 3 isolated services using Docker Compose:
- `db`: PostgreSQL 16 with pgvector extension
- `backend`: FastAPI server connected to Postgres
- `frontend`: Vite React Dashboard served by Nginx

```bash
# 1. Copy the environment file
cp deploy/.env.vultr.example .env

# 2. Start all services
docker compose up -d --build

# 3. View logs
docker compose logs -f
```

---

## How to Update After Deployment (Zero URL Change)
Whenever you push new code to GitHub, update the running server in seconds:

```bash
cd aema
git pull origin feat/multi-provider-byok-models
docker compose up -d --build
# OR for single-container:
# docker build -f Dockerfile.standalone -t aema:latest . && docker restart aema-app
```
Your Vultr IP / domain and database memories remain completely preserved!
