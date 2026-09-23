"""FastAPI Application entry point for Adaptive AI Agent with Persistent Experience Memory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from app.api.v1.router import api_v1_router
    from app.api.v1.health import router as health_router
except ModuleNotFoundError:
    from backend.app.api.v1.router import api_v1_router
    from backend.app.api.v1.health import router as health_router


app = FastAPI(
    title="Adaptive AI Agent with Persistent Experience Memory",
    description="Backend API service for experience retrieval, execution, evaluation, reflection, and trust updates.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for local development and frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router under /api/v1
app.include_router(api_v1_router, prefix="/api/v1")

# Convenience root health route
app.include_router(health_router, prefix="")


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "adaptive-agent-backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
