#!/usr/bin/env bash
# ==============================================================================
# AEMA: Autonomous Experiential Memory Agent - Unified Demo Launcher
# Starts both Backend (FastAPI on :8000) and Frontend (Vite on :5173) in one command
# ==============================================================================

set -e

# Resolve repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Ensure common binary paths are available on macOS / Linux
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Load root .env if present
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env" 2>/dev/null || true
    set +a
fi

# Color formatting
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD}${CYAN}   AEMA: Reliability-Aware Agent Memory Engine        ${NC}"
echo -e "${BOLD}${CYAN}   Starting Unified Demo (Backend + Frontend)         ${NC}"
echo -e "${BOLD}${CYAN}======================================================${NC}"

# 1. Check Python Virtual Environment
VENV_UVICORN="$REPO_ROOT/backend/venv/bin/uvicorn"

if [ ! -f "$VENV_UVICORN" ]; then
    echo -e "${RED}[ERROR] Backend virtualenv not found at backend/venv!${NC}"
    echo -e "Please create it: python3 -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.txt"
    exit 1
fi

# 2. Check Frontend Node Modules
if [ ! -d "$REPO_ROOT/frontend/node_modules" ]; then
    echo -e "${YELLOW}[INFO] Installing frontend dependencies...${NC}"
    (cd "$REPO_ROOT/frontend" && npm install)
fi

# 3. Clean up any stale processes on ports 8000 and 5173
cleanup_port() {
    local port=$1
    local pids=$(lsof -ti tcp:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}[CLEANUP] Releasing occupied port :$port (PID: $pids)...${NC}"
        kill -9 $pids 2>/dev/null || true
        sleep 0.5
    fi
}

cleanup_port 8000

# Trap SIGINT, SIGTERM, and EXIT to kill child processes cleanly
BACKEND_PID=""
FRONTEND_PID=""

shutdown() {
    trap - SIGINT SIGTERM EXIT
    echo -e "\n${YELLOW}[SHUTDOWN] Stopping AEMA Demo services...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    cleanup_port 8000
    cleanup_port 5173
    echo -e "${GREEN}[SHUTDOWN] All services stopped cleanly.${NC}"
    exit 0
}

trap shutdown SIGINT SIGTERM EXIT

# 4. Launch Backend
echo -e "\n${BOLD}${GREEN}[1/2] Starting FastAPI Backend on http://localhost:8000...${NC}"
"$VENV_UVICORN" backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend health check
echo -n "Waiting for backend to initialize..."
for i in {1..40}; do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        echo -e " ${GREEN}READY!${NC}"
        break
    fi
    echo -n "."
    sleep 0.5
done

# 5. Launch Frontend
echo -e "\n${BOLD}${GREEN}[2/2] Starting Vite Frontend on http://localhost:5173...${NC}"
cd "$REPO_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo -e "\n${BOLD}${CYAN}======================================================${NC}"
echo -e "${BOLD}${GREEN}   AEMA Demo is running!                              ${NC}"
echo -e "   - Frontend Dashboard: ${CYAN}http://localhost:5173/dashboard?demo=true${NC}"
echo -e "   - Backend Health:     ${CYAN}http://localhost:8000/api/health${NC}"
echo -e "   - Interactive Docs:   ${CYAN}http://localhost:8000/docs${NC}"
echo -e "   - Press ${YELLOW}Ctrl+C${NC} anytime to stop all services"
echo -e "${BOLD}${CYAN}======================================================${NC}\n"

# Wait for background processes to keep script running
wait
