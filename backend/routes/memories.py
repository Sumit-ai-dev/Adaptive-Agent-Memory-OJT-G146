"""
Experiential Memory Management API endpoints.
Provides CRUD and semantic retrieval operations over stored agent experiences.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ai_service.embedder import LocalEmbedder
from backend.routes.agent import shared_store
from models.domain import ExperienceStatus, TaskDomain
from models.experience import Experience

logger = logging.getLogger("backend.routes.memories")

router = APIRouter(prefix="/memories", tags=["Experiential Memories"])
embedder = LocalEmbedder()


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
