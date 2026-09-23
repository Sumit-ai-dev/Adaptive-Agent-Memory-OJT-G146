from fastapi import APIRouter
try:
    from app.api.v1.health import router as health_router
except ModuleNotFoundError:
    from backend.app.api.v1.health import router as health_router


api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
