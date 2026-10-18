"""
Experiential Memory Management API endpoints.
Provides CRUD and semantic retrieval operations over stored agent experiences.
"""

import logging
import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from ai_service.config import settings
from ai_service.embedder import LocalEmbedder
from ai_service.memory.probation import execute_probationary_probe
from backend.routes.agent import shared_store
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience

logger = logging.getLogger("backend.routes.memories")

router = APIRouter(prefix="/memories", tags=["Experiential Memories"])
embedder = LocalEmbedder()


class RecoveryRequest(BaseModel):
    reason: str = Field(..., min_length=15, description="Meaningful audit justification for recovery (>= 15 chars)")
    client_ref: Optional[str] = Field(None, description="Client reference identifier (logged without storing secrets)")


class ProbationValidationRequest(BaseModel):
    task_input: str = Field(..., min_length=1, description="Deterministic task prompt")
    test_code: str = Field(..., min_length=1, description="Deterministic pytest executable assertions")
    client_ref: Optional[str] = Field(None, description="Client reference identifier")


def verify_admin_auth(
    authorization: Optional[str] = Header(None, description="Admin authorization header"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token", description="Admin authorization token"),
) -> str:
    configured_key = (getattr(settings, "ADMIN_API_KEY", None) or "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured on the server. Administrative actions are disabled.",
        )

    token = (x_admin_token or "").strip()
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    if not token or not secrets.compare_digest(token, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authorization required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "system:admin_api_key"


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    summary="List Experiential Memories",
)
async def list_memories(
    domain: Optional[str] = Query(None, description="Filter by task domain"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, candidate, deprecated)"),
    min_trust: float = Query(0.0, ge=0.0, le=1.0, description="Minimum trust threshold"),
    search: Optional[str] = Query(None, description="Semantic or keyword search query"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """
    Lists persistent agent experiences from memory store.
    Supports domain filtering, trust thresholds, and semantic similarity search.
    """
    try:
        if search:
            # P0-6: `LocalEmbedder` exposes `embed_text` / `embed_batch`; there is no
            # `embed`. The AttributeError was absorbed by the handler below and surfaced
            # as an opaque 500 on every semantic-search request.
            query_emb = embedder.embed_text(search)
            results = await shared_store.search_similar(
                query_embedding=query_emb,
                domain=TaskDomain(domain) if domain and domain != "all" else None,
                top_k=limit,
            )
            out = []
            for exp, sim in results:
                if exp.trust_score >= min_trust:
                    d = exp.model_dump(by_alias=True)
                    d["similarityScore"] = round(sim, 3)
                    d["compositeScore"] = round(0.70 * sim + 0.30 * exp.trust_score, 3)
                    out.append(d)
            return out

        # Non-semantic listing
        all_exps = await shared_store.list_experiences(
            domain=TaskDomain(domain) if domain and domain != "all" else None,
            status=ExperienceStatus(status_filter) if status_filter and status_filter != "all" else None,
            min_trust=min_trust,
        )

        paged = all_exps[offset : offset + limit]
        return [e.model_dump(by_alias=True) for e in paged]
    except Exception as e:
        logger.error(f"Error listing memories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query experiences: {str(e)}",
        )


@router.post(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create New Experience Manually",
)
async def create_memory(experience: Experience) -> Dict[str, Any]:
    """Manually insert an experience into the memory store."""
    try:
        # Enforce server-side lifecycle policy: manually submitted memories
        # start as CANDIDATE with capped initial trust to prevent injection
        experience.status = ExperienceStatus.CANDIDATE
        experience.trust_score = min(experience.trust_score, 0.50)
        await shared_store.add_experience(experience)
        return experience.model_dump(by_alias=True)
    except Exception as e:
        logger.error(f"Error creating memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create experience: {str(e)}",
        )


@router.get(
    "/{memory_id}",
    response_model=Dict[str, Any],
    summary="Get Single Experience by ID",
)
async def get_memory(memory_id: str) -> Dict[str, Any]:
    """Retrieves an experience record by ID."""
    exp = await shared_store.get_experience(memory_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience '{memory_id}' not found.",
        )
    return exp.model_dump(by_alias=True)


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete or Quarantine Experience",
)
async def delete_memory(memory_id: str):
    """Removes an experience record from the store."""
    exp = await shared_store.get_experience(memory_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience '{memory_id}' not found.",
        )
    await shared_store.update_trust(
        experience_id=memory_id,
        new_trust=0.0,
        reason="manual_deletion",
    )
    return None


@router.post(
    "/{memory_id}/recover",
    response_model=Dict[str, Any],
    summary="Safely Recover Quarantined Memory to CANDIDATE Probation",
)
async def recover_memory(
    memory_id: str,
    request: RecoveryRequest,
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    actor = verify_admin_auth(authorization, x_admin_token)

    exp = await shared_store.get_experience(memory_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience '{memory_id}' not found.",
        )

    if exp.status in (ExperienceStatus.CANDIDATE, ExperienceStatus.ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experience '{memory_id}' is already in status '{exp.status.value}'. Duplicate recovery rejected.",
        )

    try:
        updated = await shared_store.admin_recover_to_probation(
            experience_id=memory_id,
            reason=request.reason,
            actor_id=actor,
            client_ref=request.client_ref,
        )
        return updated.model_dump(by_alias=True)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error recovering memory: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/{memory_id}/validate",
    response_model=Dict[str, Any],
    summary="Execute Isolated Probationary Validation Probe",
)
async def validate_memory_probe(
    memory_id: str,
    request: ProbationValidationRequest,
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    actor = verify_admin_auth(authorization, x_admin_token)

    exp = await shared_store.get_experience(memory_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience '{memory_id}' not found.",
        )

    if exp.status != ExperienceStatus.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experience '{memory_id}' is in status '{exp.status.value}'. Only CANDIDATE memories can undergo probationary validation.",
        )

    try:
        updated_exp, outcome, record = await execute_probationary_probe(
            experience_id=memory_id,
            task_input=request.task_input,
            test_code=request.test_code,
            store=shared_store,
            actor_id=actor,
            client_ref=request.client_ref,
        )
        return {
            "experience": updated_exp.model_dump(by_alias=True),
            "outcome": outcome.model_dump(),
            "trustRecord": record.model_dump() if hasattr(record, "model_dump") else record.__dict__,
        }
    except ValueError as ve:
        err_msg = str(ve)
        if "Duplicate" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        logger.error(f"Error during validation probe: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
