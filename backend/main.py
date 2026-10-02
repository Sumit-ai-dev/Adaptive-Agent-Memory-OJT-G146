"""
FastAPI Backend Application Entrypoint for Adaptive Agent Memory System.
Harmonizes with Supabase Auth, React Dashboard, and the LangGraph AI Service.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.agent import router as agent_router, shared_store
from backend.routes.memories import router as memories_router
from backend.routes.telemetry import router as telemetry_router
from ai_service.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Adaptive Agent Memory Backend Engine...")
    logger.info(f"Database path: {shared_store.db_path}")
    logger.info(f"Model Provider Gateway: Llama-3.3-70B / BYOK active")
    yield
    logger.info("Shutting down Adaptive Agent Memory Backend.")


app = FastAPI(
    title="Adaptive Agent Memory API",
    description="Backend orchestration engine and experiential memory store for autonomous LLM agents.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes under /api (frontend convention) and /api/v1 (REST spec convention)
app.include_router(agent_router, prefix="/api")
app.include_router(agent_router, prefix="/api/v1")

app.include_router(memories_router, prefix="/api")
app.include_router(memories_router, prefix="/api/v1")

app.include_router(telemetry_router, prefix="/api")
app.include_router(telemetry_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "adaptive-agent-memory-backend",
        "memory_store": "sqlite_hybrid",
        "quarantine_cutoff": settings.THETA_CUTOFF,
        "asymmetric_alpha": settings.ALPHA_SUCCESS,
        "asymmetric_beta": settings.BETA_FAILURE,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
