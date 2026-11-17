# Multi-stage production Dockerfile for AEMA FastAPI Backend
FROM python:3.11-slim as builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into a virtual environment or user site
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Final runner stage
FROM python:3.11-slim as runner

WORKDIR /app

# Copy installed python site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy backend, ai-service, models, and data skeletons
COPY backend/ /app/backend/
COPY ai-service/ /app/ai-service/
COPY models/ /app/models/
COPY data/ /app/data/

# Symlink ai_service to ai-service for python import parity
RUN ln -s /app/ai-service /app/ai_service

# Ensure data directory exists for SQLite storage
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    ENVIRONMENT=production

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
