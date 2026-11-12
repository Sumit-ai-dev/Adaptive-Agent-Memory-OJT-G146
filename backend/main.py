"""
FastAPI Backend Application Entrypoint for Adaptive Agent Memory System.
Harmonizes with Supabase Auth, React Dashboard, and the LangGraph AI Service.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

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
    db_path = getattr(shared_store, "db_path", None)
    if db_path:
        logger.info(f"Database path: {db_path}")
    else:
        logger.info(f"Memory backend: {type(shared_store).__name__}")
    logger.info(f"Groq Provider Key: {'CONFIGURED' if settings.GROQ_API_KEY else 'NOT SET (falls back to mock if empty)'}")
    logger.info(f"Gemini Provider Key: {'CONFIGURED' if settings.GEMINI_API_KEY else 'NOT SET (falls back to mock if empty)'}")
    logger.info(f"OpenAI Provider Key: {'CONFIGURED' if settings.OPENAI_API_KEY else 'NOT SET'}")
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
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Injects defensive HTTP headers on all API responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Mount Routes under /api (frontend convention) and /api/v1 (REST spec convention)
app.include_router(agent_router, prefix="/api")
app.include_router(agent_router, prefix="/api/v1")

app.include_router(memories_router, prefix="/api")
app.include_router(memories_router, prefix="/api/v1")

app.include_router(telemetry_router, prefix="/api")
app.include_router(telemetry_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "adaptive-agent-backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health", tags=["Health"])
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "adaptive-agent-backend",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
