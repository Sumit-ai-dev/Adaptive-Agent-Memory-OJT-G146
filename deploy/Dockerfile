# ==============================================================================
# Unified Production Dockerfile for AEMA (Adaptive Agent Memory)
# Builds both the React Vite frontend and FastAPI LangGraph backend into
# a single self-contained, high-performance container with Nginx reverse proxy.
# ==============================================================================

# --- Stage 1: Build Frontend Static Assets ---
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/tsconfig*.json frontend/vite.config.ts frontend/postcss.config.js frontend/tailwind.config.js frontend/index.html ./
COPY frontend/public ./public
COPY frontend/src ./src

RUN npm run build

# --- Stage 2: Install Python Backend Dependencies ---
FROM python:3.11-slim AS backend-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip==24.3.1 setuptools==75.8.0 wheel==0.45.1

COPY backend/requirements.txt ./backend/requirements.txt

# Install lightweight dependencies (sentence-transformers hash fallback for CPU efficiency)
RUN grep -v "^sentence-transformers" backend/requirements.txt > /tmp/reqs-light.txt && \
    pip install --no-cache-dir -r /tmp/reqs-light.txt && \
    rm -f /tmp/reqs-light.txt

# --- Stage 3: Unified Production Runtime ---
FROM python:3.11-slim AS runner

WORKDIR /app

# Install Nginx and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    AEMA_DB_PATH=/data/adaptive_memory.db

# Copy Python dependencies from backend-builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy compiled Frontend assets from frontend-builder into Nginx root
RUN rm -rf /usr/share/nginx/html/*
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# Configure Nginx
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# Copy backend application source code
COPY README.md pyproject.toml hatch_build.py ./
COPY aema ./aema
COPY models ./models
COPY backend ./backend
COPY ai-service ./ai_service
RUN ln -s ai_service /app/ai-service

# Install editable link for aema package
RUN pip install --no-cache-dir -e . --no-deps

# Create persistent storage directories
RUN mkdir -p /data /app/data
VOLUME ["/data"]

# Copy process supervisor entrypoint script
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose HTTP port 80 (serves frontend + proxies API) and internal 8000
EXPOSE 80 8000

# Health check verifies both Nginx and FastAPI
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost/healthz && curl -f http://127.0.0.1:8000/api/health || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
