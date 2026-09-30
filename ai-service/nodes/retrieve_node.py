"""
LangGraph Node 1: Memory Retrieval Engine (retrieve_node.py)
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)

Implements composite memory ranking:
    CompositeScore = 0.70 * Similarity + 0.30 * TrustScore
Filters out unreliable experiences (Trust < 0.35 or Sim < 0.70) to mitigate negative transfer.
"""

import math
from typing import Any, Optional, Sequence

from models.domain import TaskDomain
from models.experience import Experience, ExperienceMatch, ExperienceStatus


def cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Computes cosine similarity between two numeric vectors in [-1.0, 1.0]."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    sim = dot_product / (norm1 * norm2)
    # Clip to valid unit interval for distance-derived similarities
    return max(0.0, min(1.0, float(sim)))


def retrieve_experiences(
    query_embedding: Optional[Sequence[float]],
    candidates: Sequence[Experience],
    filter_domain: Optional[TaskDomain] = None,
    min_similarity: float = 0.70,
    min_trust: float = 0.35,
    top_k: int = 3,
    weight_similarity: float = 0.70,
    weight_trust: float = 0.30,
) -> list[ExperienceMatch]:
    """
    Ranks candidates by composite score:
        CompositeScore = (weight_sim * Similarity) + (weight_trust * TrustScore)
    Applies strict dual-threshold cutoffs to eliminate low-relevance or toxic advice.
    """
    matches: list[ExperienceMatch] = []

    for exp in candidates:
        # 1. Filter by active status
        if exp.status != ExperienceStatus.ACTIVE:
            continue

        # 2. Filter by domain (allow domain match or general)
        if filter_domain and exp.task_domain not in (filter_domain, TaskDomain.GENERAL):
            continue

        # 3. Filter by trust score cutoff (Theorem 1: negative transfer boundary)
        if exp.trust_score < min_trust:
            continue

        # 4. Compute similarity
        if query_embedding is not None and exp.embedding is not None:
            sim = cosine_similarity(query_embedding, exp.embedding)
        else:
            # Fallback when embeddings are not supplied: neutral similarity estimate
            sim = 0.75

        # 5. Filter by minimum similarity
        if sim < min_similarity:
            continue

        # 6. Compute composite score
        composite = (weight_similarity * sim) + (weight_trust * exp.trust_score)

        matches.append(
            ExperienceMatch(
                experience=exp,
                similarity=round(sim, 4),
                composite_score=round(composite, 4),
            )
        )

    # Sort descending by composite score, then by trust score
    matches.sort(key=lambda m: (m.composite_score, m.experience.trust_score), reverse=True)
    return matches[:top_k]


def retrieve_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph StateGraph node function for memory retrieval.
    Takes agent state dictionary and updates `retrieved_experiences`.
    """
    query_embedding = state.get("query_embedding")
    candidates = state.get("memory_candidates", [])
    filter_domain = state.get("task_domain")
    memory_mode = state.get("memory_mode", "adaptive")

    # If memory is turned off for ablation study, return empty list
    if memory_mode == "off" or state.get("memory_enabled") is False:
        return {"retrieved_experiences": []}

    matches = retrieve_experiences(
        query_embedding=query_embedding,
        candidates=candidates,
        filter_domain=filter_domain,
        min_similarity=0.70,
        min_trust=0.35 if memory_mode == "adaptive" else 0.0,  # naive RAG ignores trust cutoff
        top_k=3,
    )

    return {"retrieved_experiences": matches}
