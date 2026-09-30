"""
Telemetry Subsystem API Endpoints (/api/v1/telemetry)
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Backend Gateway Lead)

Provides:
- GET /api/v1/telemetry : Real-time metrics summary for dashboard visualization.
"""

from fastapi import APIRouter

try:
    from app.database import db
except ModuleNotFoundError:
    from backend.app.database import db


router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("", summary="Get live agent memory telemetry")
async def get_telemetry():
    """
    Returns aggregated telemetry statistics:
    - activeMemories, deprecatedMemories, candidateMemories
    - avgTrustScore across active memory pool
    - memoryHitRate and totalTaskExecutions
    """
    return db.get_telemetry_metrics()
