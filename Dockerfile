# ==============================================================================
# Multi-stage Production Dockerfile for AEMA Backend Server (aema-server)
# Supports standalone SQLite mode or distributed PostgreSQL + pgvector mode
# ==============================================================================

# --- Stage 1: Build & Dependency Resolution ---
FROM python:3.11-slim AS builder

WORKDIR /app

ARG WITH_EMBEDDINGS=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY backend/requirements.txt ./backend/requirements.txt

# When WITH_EMBEDDINGS=true, install CPU PyTorch and sentence-transformers.
# By default (false), filter out sentence-transformers to yield a fast, lightweight image.
RUN if [ "$WITH_EMBEDDINGS" = "true" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
        pip install --no-cache-dir -r backend/requirements.txt; \
    else \
        grep -v "^sentence-transformers" backend/requirements.txt > /tmp/reqs-light.txt && \
        pip install --no-cache-dir -r /tmp/reqs-light.txt && \
        rm -f /tmp/reqs-light.txt; \
    fi

# --- Stage 2: Hardened Runtime ---
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    AEMA_DB_PATH=/data/adaptive_memory.db

# Copy installed Python packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create dedicated non-root user and group (UID/GID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Initialize persistent data directory
RUN mkdir -p /data /app && chown -R appuser:appgroup /data /app
VOLUME ["/data"]

# Copy project definition, build hook, and application sources
COPY README.md pyproject.toml hatch_build.py ./
COPY aema ./aema
COPY models ./models
COPY backend ./backend
COPY ai-service ./ai_service
RUN ln -s ai_service /app/ai-service

# Install project editable link without pulling unpinned transitive deps
RUN pip install --no-cache-dir -e . --no-deps

# Enforce non-root ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Lightweight healthcheck using standard library urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
