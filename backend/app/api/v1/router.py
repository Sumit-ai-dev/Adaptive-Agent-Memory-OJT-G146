from fastapi import APIRouter

try:
    from app.api.v1.health import router as health_router
    from app.api.v1.memories import router as memories_router
    from app.api.v1.telemetry import router as telemetry_router
except ModuleNotFoundError:
    from backend.app.api.v1.health import router as health_router
    from backend.app.api.v1.memories import router as memories_router
    from backend.app.api.v1.telemetry import router as telemetry_router


api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(memories_router)
api_v1_router.include_router(telemetry_router)
