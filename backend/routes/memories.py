"""
Experiential Memory Management API endpoints.
Provides CRUD and semantic retrieval operations over stored agent experiences.
"""

import logging
import secrets
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from ai_service.config import settings
from ai_service.embedder import LocalEmbedder, local_embedder
from ai_service.memory.probation import execute_probationary_probe
from ai_service.nodes.retrieve_node import retrieve_experiences
from ai_service.nodes.trust_node import update_experience_trust
from backend.routes.agent import shared_store
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience, ExperienceMatch

logger = logging.getLogger("backend.routes.memories")

router = APIRouter(prefix="/memories", tags=["Experiential Memories"])
embedder = local_embedder


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
    """
    Validates administrative credentials for destructive memory mutations and quarantine recoveries.
    Fails closed with HTTP 503 if ADMIN_API_KEY is not configured.
    Requires constant-time token comparison via X-Admin-Token or Authorization: Bearer.
    """
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
    user_id: Annotated[Optional[str], Query(alias="userId", description="Optional user/tenant namespace filter")] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """
    Lists persistent agent experiences from memory store.
    Supports domain filtering, trust thresholds, and semantic similarity search.
    """
    try:
        resolved_status: Optional[ExperienceStatus] = None
        if status_filter and status_filter.lower() != "all":
            sf = status_filter.lower().strip()
            if sf in ("candidate", "provisional"):
                resolved_status = ExperienceStatus.CANDIDATE
            elif sf in ("deprecated", "quarantined"):
                resolved_status = ExperienceStatus.DEPRECATED
            elif sf == "active":
                resolved_status = ExperienceStatus.ACTIVE
            else:
                try:
                    resolved_status = ExperienceStatus(sf)
                except ValueError:
                    return []

        if search:
            # P0-6: `LocalEmbedder` exposes `embed_text` / `embed_batch`; there is no
            # `embed`. The AttributeError was absorbed by the handler below and surfaced
            # as an opaque 500 on every semantic-search request.
            query_emb = embedder.embed_text(search)
            results = await shared_store.search_similar(
                query_embedding=query_emb,
                domain=TaskDomain(domain) if domain and domain != "all" else None,
                top_k=limit,
                user_id=user_id,
            )
            out = []
            for exp, sim in results:
                if resolved_status is not None and exp.status != resolved_status:
                    continue
                if exp.trust_score >= min_trust:
                    d = exp.model_dump(by_alias=True)
                    d["similarityScore"] = round(sim, 3)
                    d["compositeScore"] = round(0.70 * sim + 0.30 * exp.trust_score, 3)
                    out.append(d)
            return out

        # Non-semantic listing
        all_exps = await shared_store.list_experiences(
            domain=TaskDomain(domain) if domain and domain != "all" else None,
            status=resolved_status,
            min_trust=min_trust,
            user_id=user_id,
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
        if not experience.embedding:
            experience.embedding = embedder.embed_text(
                f"{experience.trigger_condition} {experience.strategy_lesson}"
            )
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
async def delete_memory(
    memory_id: str,
    hard_delete: Annotated[bool, Query(description="When true, permanently delete from storage instead of soft quarantine")] = False,
    authorization: Optional[str] = Header(None, description="Admin authorization header"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token", description="Admin authorization token"),
):
    """Removes or quarantines an experience record from the store. Requires admin authorization."""
    verify_admin_auth(authorization, x_admin_token)
    exp = await shared_store.get_experience(memory_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience '{memory_id}' not found.",
        )
    if hard_delete:
        await shared_store.delete_experience(memory_id)
    else:
        await shared_store.update_trust(
            experience_id=memory_id,
            new_trust=0.0,
            reason="manual_deletion",
            status="deprecated",
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
    except NotImplementedError as nie:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(nie))
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
    except NotImplementedError as nie:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(nie))
    except ValueError as ve:
        err_msg = str(ve)
        if "Duplicate" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        logger.error(f"Error during validation probe: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class MemoryRetrieveRequest(BaseModel):
    """Payload for live composite memory retrieval (supports both API and SDK schemas)."""
    task_input: Optional[str] = Field(default=None, description="Task prompt or query to match against memory index")
    query: Optional[str] = Field(default=None, description="SDK/MCP alias for task_input")
    domain: Optional[TaskDomain] = Field(default=None, description="Optional task domain filter")
    user_id: Optional[str] = Field(default=None, alias="userId", description="Optional user/tenant namespace filter")
    min_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity cutoff (defaults to 0.60 with neural embeddings or 0.15 with hash fallback)",
    )
    min_trust: float = Field(default=0.35, ge=0.0, le=1.0, description="Minimum trust score cutoff (Theorem 1 boundary)")
    top_k: int = Field(default=3, ge=1, le=10, description="Maximum number of memories to return")

    @property
    def effective_input(self) -> str:
        return self.task_input or self.query or ""


class TrustUpdateRequest(BaseModel):
    """Payload for updating an experience trust score via Asymmetric EMA."""
    experience_id: str = Field(..., description="ID of the experience to update")
    outcome_score: float = Field(..., ge=0.0, le=1.0, description="Evaluated outcome reward (0.0=failure, 1.0=success)")
    execution_id: Optional[str] = Field(default=None, description="Optional audit execution ID")


class MemoryFeedbackRequest(BaseModel):
    """Feedback payload used by AEMA TypeScript SDK and MCP clients."""
    outcome: Optional[str] = Field(default="success", description="Outcome label: 'success' or 'failure'")
    outcome_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    new_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


@router.post("/retrieve", response_model=List[ExperienceMatch], summary="Execute composite memory retrieval")
async def retrieve_memories_endpoint(payload: MemoryRetrieveRequest):
    """
    Executes live memory retrieval using composite scoring:
        CompositeScore = 0.70 * Similarity + 0.30 * TrustScore
    Applies Theorem 1 dual-threshold cutoffs (Sim >= 0.70, Trust >= 0.35).
    """
    query_emb = None
    query_text = payload.effective_input
    if query_text:
        try:
            query_emb = local_embedder.embed_text(query_text)
        except Exception:
            query_emb = None

    effective_min_similarity = (
        payload.min_similarity
        if payload.min_similarity is not None
        else (0.60 if local_embedder._model is not None else 0.15)
    )
    all_candidates = await shared_store.list_experiences(user_id=payload.user_id)
    matches = retrieve_experiences(
        query_embedding=query_emb,
        candidates=all_candidates,
        filter_domain=payload.domain,
        min_similarity=effective_min_similarity,
        min_trust=payload.min_trust,
        top_k=payload.top_k,
    )
    return matches


@router.post("/search", response_model=List[ExperienceMatch], summary="SDK/MCP alias for composite memory retrieval")
async def search_memories_endpoint(payload: MemoryRetrieveRequest):
    """Alias for /retrieve matching AEMA TypeScript SDK and MCP specification."""
    return await retrieve_memories_endpoint(payload)


@router.post("/trust-update", summary="Execute Asymmetric EMA trust update")
async def trust_update_endpoint(payload: TrustUpdateRequest):
    """
    Updates experience trust score via Asymmetric EMA:
    - Success (R >= 0.80): S_{t+1} = 0.85 * S_t + 0.15 (Steady climb)
    - Failure (R <= 0.30): S_{t+1} = 0.70 * S_t (Aggressive penalty)
    - Automatically deprecates memory if trust drops below theta = 0.35.
    """
    exp = await shared_store.get_experience(payload.experience_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experience '{payload.experience_id}' not found.",
        )

    updated_exp, audit_record, trust_update = update_experience_trust(
        experience=exp,
        outcome_score=payload.outcome_score,
        execution_id=payload.execution_id,
    )

    status_val = updated_exp.status.value if hasattr(updated_exp.status, "value") else str(updated_exp.status)
    bin_outcome = 1 if payload.outcome_score >= 0.80 else (0 if payload.outcome_score <= 0.30 else None)
    await shared_store.update_trust(
        experience_id=payload.experience_id,
        new_trust=updated_exp.trust_score,
        reason=audit_record.reason,
        execution_id=payload.execution_id,
        status=status_val,
        binary_outcome=bin_outcome,
    )

    return {
        "experience": updated_exp,
        "auditRecord": audit_record,
        "trustUpdate": trust_update,
    }


@router.post("/{experience_id}/feedback", summary="Record feedback from AEMA SDK/MCP clients")
async def record_feedback_endpoint(experience_id: str, payload: MemoryFeedbackRequest):
    """
    Direct feedback bridge for AEMAClient and MCP server.
    Maps outcome ('success'/'failure') to Asymmetric EMA update.
    """
    score = payload.outcome_score
    if score is None:
        score = 1.0 if payload.outcome == "success" else 0.0

    trust_req = TrustUpdateRequest(
        experience_id=experience_id,
        outcome_score=score,
        execution_id=None,
    )
    return await trust_update_endpoint(trust_req)

