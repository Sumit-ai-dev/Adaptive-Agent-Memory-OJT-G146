from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health Check")
async def health_check():
    """Verify backend API liveness and readiness."""
    return {
        "status": "ok",
        "service": "adaptive-agent-backend"
    }
