"""
Memory Subsystem API Endpoints (/api/v1/memories)
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Backend Gateway Lead)

Provides:
- GET  /api/v1/memories               : List memories with domain, status, and trust filtering.
- GET  /api/v1/memories/{id}          : Fetch single memory details.
- POST /api/v1/memories/retrieve      : Run composite retrieval algorithm (0.70 Sim + 0.30 Trust).
- POST /api/v1/memories/trust-update  : Run Asymmetric EMA trust update & quarantine demo.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from models.domain import TaskDomain
from models.experience import Experience, ExperienceMatch, ExperienceStatus
from ai_service.nodes.retrieve_node import retrieve_experiences
from ai_service.nodes.trust_node import update_experience_trust

try:
    from app.database import db
except ModuleNotFoundError:
    from backend.app.database import db


router = APIRouter(prefix="/memories", tags=["Memories"])


class MemoryRetrieveRequest(BaseModel):
    """Payload for testing live composite memory retrieval."""
    task_input: str = Field(..., min_length=1, description="Task prompt or query to match against memory index")
    domain: Optional[TaskDomain] = Field(default=None, description="Optional task domain filter")
    min_similarity: float = Field(default=0.70, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff")
    min_trust: float = Field(default=0.35, ge=0.0, le=1.0, description="Minimum trust score cutoff (Theorem 1 boundary)")
    top_k: int = Field(default=3, ge=1, le=10, description="Maximum number of memories to return")


class TrustUpdateRequest(BaseModel):
    """Payload for updating an experience trust score via Asymmetric EMA."""
    experience_id: str = Field(..., description="ID of the experience to update")
    outcome_score: float = Field(..., ge=0.0, le=1.0, description="Evaluated outcome reward (0.0=failure, 1.0=success)")
    execution_id: Optional[str] = Field(default=None, description="Optional audit execution ID")


@router.get("", response_model=list[Experience], summary="List stored memories")
async def list_memories(
    domain: Optional[TaskDomain] = Query(default=None, description="Filter by domain"),
    status: Optional[ExperienceStatus] = Query(default=None, description="Filter by status (active, candidate, deprecated)"),
    min_trust: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum trust score"),
):
    """Returns persistent experiences stored in the database matching optional query filters."""
    return db.list_experiences(domain=domain, status=status, min_trust=min_trust)


@router.get("/{experience_id}", response_model=Experience, summary="Get single memory by ID")
async def get_memory(experience_id: str):
    """Fetches full 7-tuple details for a specific memory experience."""
    exp = db.get_experience(experience_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experience '{experience_id}' not found.")
    return exp


@router.post("/retrieve", response_model=list[ExperienceMatch], summary="Execute composite memory retrieval")
async def retrieve_memories_endpoint(payload: MemoryRetrieveRequest):
    """
    Executes live memory retrieval using composite scoring:
        CompositeScore = 0.70 * Similarity + 0.30 * TrustScore
    Applies Theorem 1 dual-threshold cutoffs (Sim >= 0.70, Trust >= 0.35).
    """
    all_candidates = db.list_experiences()
    matches = retrieve_experiences(
        query_embedding=None,  # Uses neutral baseline similarity for prompt demonstration
        candidates=all_candidates,
        filter_domain=payload.domain,
        min_similarity=payload.min_similarity,
        min_trust=payload.min_trust,
        top_k=payload.top_k,
    )
    return matches


@router.post("/trust-update", summary="Execute Asymmetric EMA trust update")
async def trust_update_endpoint(payload: TrustUpdateRequest):
    """
    Updates experience trust score via Asymmetric EMA:
    - Success (R >= 0.80): S_{t+1} = 0.85 * S_t + 0.15 (Steady climb)
    - Failure (R <= 0.30): S_{t+1} = 0.70 * S_t (Aggressive penalty)
    - Automatically deprecates memory if trust drops below theta = 0.35.
    """
    exp = db.get_experience(payload.experience_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experience '{payload.experience_id}' not found.")

    updated_exp, audit_record, trust_update = update_experience_trust(
        experience=exp,
        outcome_score=payload.outcome_score,
        execution_id=payload.execution_id,
    )

    db.upsert_experience(updated_exp)
    db.record_trust_history(audit_record)

    return {
        "experience": updated_exp,
        "auditRecord": audit_record,
        "trustUpdate": trust_update,
    }
