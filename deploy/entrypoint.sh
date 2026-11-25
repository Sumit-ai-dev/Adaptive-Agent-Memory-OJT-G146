#!/bin/bash
# ==============================================================================
# Dual-Process Entrypoint for AEMA Unified Single-Container Deployment
# Boots FastAPI Uvicorn on 127.0.0.1:8000, then starts Nginx on 0.0.0.0:80.
# Handles graceful shutdown on SIGTERM / SIGINT.
# ==============================================================================

set -e

echo "==> [AEMA] Starting Adaptive Agent Memory Engine in single-container mode..."

# Function to handle shutdown signals cleanly
cleanup() {
    echo "==> [AEMA] Stopping services..."
    if [ -n "$UVICORN_PID" ]; then
        kill -TERM "$UVICORN_PID" 2>/dev/null || true
    fi
    nginx -s quit 2>/dev/null || true
    wait
    exit 0
}

trap cleanup SIGTERM SIGINT

# Ensure persistent data directories exist
mkdir -p /data /app/data
chmod -R 755 /data /app/data 2>/dev/null || true

# 1. Start FastAPI backend server in background
echo "==> [AEMA] Launching FastAPI backend on 127.0.0.1:8000..."
python -m uvicorn backend.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers "${WORKERS:-2}" \
    --log-level info &
UVICORN_PID=$!

# 2. Wait for FastAPI health endpoint to respond
echo "==> [AEMA] Waiting for backend gateway health check..."
RETRIES=30
until curl -s -f http://127.0.0.1:8000/api/health > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
    echo "    Backend initializing... ($RETRIES attempts remaining)"
    RETRIES=$((RETRIES-1))
    sleep 1
done

if [ $RETRIES -eq 0 ]; then
    echo "❌ [AEMA] Backend failed to start in time. Check logs above."
    kill -TERM "$UVICORN_PID" 2>/dev/null || true
    exit 1
fi

echo "✅ [AEMA] Backend health verified: http://127.0.0.1:8000/api/health is UP"

# 3. Start Nginx in foreground
echo "==> [AEMA] Launching Nginx reverse proxy & static asset server on port 80..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Wait for any process to exit
wait -n "$UVICORN_PID" "$NGINX_PID"
cleanup
