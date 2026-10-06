"""
LangGraph Node 1: Memory Retrieval Engine (retrieve_node.py)
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)

Implements composite memory ranking:
    CompositeScore = 0.70 * Similarity + 0.30 * TrustScore
Filters out unreliable experiences (Trust < 0.35 or Sim < 0.70) to mitigate negative transfer.
"""

import logging
import math
from typing import Any, Optional, Sequence

from models.domain import TaskDomain
from models.experience import Experience, ExperienceMatch, ExperienceStatus

logger = logging.getLogger("ai_service.nodes.retrieve_node")


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


async def async_retrieve_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Asynchronous StateGraph node function connected to active memory store.
    """
    import time
    start_ts = time.time()
    task_input = state.get("task_input", "")
    domain_str = state.get("task_domain", "general")
    try:
        domain = TaskDomain(domain_str)
    except ValueError:
        domain = TaskDomain.GENERAL

    mode_str = state.get("memory_mode", "adaptive")
    retrieved = []
    positive_strategy = None
    negative_pitfall = None

    memory_enabled = state.get("memory_enabled", True)
    retrieval_diagnostics: dict[str, Any] = {}

    # Step 1: when a run-scoped, policy-backed retriever is injected, use it. Trust
    # state then comes from the RunContext rather than from the memory bank, and
    # admissibility comes from the injected TrustPolicy rather than hardcoded logic.
    policy_retriever = state.get("policy_retriever")
    if memory_enabled and mode_str != "off" and policy_retriever is not None:
        candidates, retrieval_diagnostics = policy_retriever.retrieve(
            query=task_input, domain=domain, top_k=state.get("top_k", 2),
        )
        for cand in candidates:
            exp_view = cand.record.to_experience(
                trust_score=cand.decision.score,
                uses=cand.state.uses,
                successes=cand.state.successes,
                failures=cand.state.failures,
            )
            retrieved.append({
                "experience": exp_view.model_dump(by_alias=True),
                "similarityScore": round(cand.similarity, 3),
                "trustScore": round(float(cand.decision.score or 0.0), 3),
                "compositeScore": round(cand.composite_score, 3),
                "gateReason": cand.decision.reason,
            })

    elif memory_enabled and mode_str != "off":
        try:
            from ai_service.memory.retriever import MemoryRetriever, memory_retriever
            from models.domain import MemoryMode
            mode = MemoryMode(mode_str)
            custom_store = state.get("memory_store")
            active_retriever = MemoryRetriever(store=custom_store) if custom_store else memory_retriever
            retrieved_models = await active_retriever.retrieve(
                query=task_input,
                domain=domain,
                mode=mode,
                top_k=2,
            )
            for m in retrieved_models:
                exp_dict = m.experience.model_dump(by_alias=True)
                retrieved.append({
                    "experience": exp_dict,
                    "similarityScore": round(m.similarity, 3),
                    "trustScore": round(m.experience.trust_score, 3),
                    "compositeScore": round(m.composite_score, 3),
                })
        except Exception:
            # P0-2: Never silently degrade a store-backed retrieval failure into
            # "zero memories retrieved" -- that is indistinguishable from MemoryMode.OFF
            # and silently invalidates every memory-enabled condition.
            # Always log with traceback. Only fall back to the in-memory candidate path
            # when the caller actually supplied candidates; otherwise re-raise.
            candidates = state.get("memory_candidates") or []
            logger.error(
                "Store-backed retrieval failed (mode=%s, domain=%s, candidates_available=%d).",
                mode_str,
                domain.value,
                len(candidates),
                exc_info=True,
            )
            if not candidates:
                raise

            # Discard any partial results accumulated before the failure.
            retrieved = []
            matches = retrieve_experiences(
                query_embedding=state.get("query_embedding"),
                candidates=candidates,
                filter_domain=domain,
                min_similarity=0.70,
                min_trust=0.35 if mode_str == "adaptive" else 0.0,
                top_k=2,
            )
            for m in matches:
                retrieved.append({
                    "experience": m.experience.model_dump(by_alias=True),
                    "similarityScore": round(m.similarity, 3),
                    "trustScore": round(m.experience.trust_score, 3),
                    "compositeScore": round(m.composite_score, 3),
                })

    # Applies to BOTH the policy-backed and legacy retrieval branches.
    if retrieved:
        top_exp = retrieved[0]["experience"]
        positive_strategy = top_exp.get("strategyLesson") or top_exp.get("strategy_lesson")
        negative_pitfall = top_exp.get("pitfall")

    duration_ms = int((time.time() - start_ts) * 1000)

    trace = {
        "id": f"step_retrieval_{int(start_ts)}",
        "type": "retrieval",
        "node": "retrieve_node",
        "title": "Experiential Memory Retrieval",
        "detail": (
            f"Retrieved {len(retrieved)} memories under mode '{mode_str}'. "
            f"Quarantine threshold (theta >= 0.35) enforced."
            if retrieved
            else f"Zero prior experiences passed trust and similarity thresholds under mode '{mode_str}'."
        ),
        "durationMs": duration_ms,
        "metadata": {
            "retrievedCount": len(retrieved),
            "memoryMode": mode_str,
            "hasPositiveStrategy": positive_strategy is not None,
            "hasNegativePitfall": negative_pitfall is not None,
            "candidateCount": retrieval_diagnostics.get("candidate_count", 0),
            "admissibleCount": retrieval_diagnostics.get("admissible_count", 0),
            "gateReasons": retrieval_diagnostics.get("gate_reasons", {}),
            "ranker": retrieval_diagnostics.get("ranker"),
            "policy": retrieval_diagnostics.get("policy"),
            "fallbackOccurred": len(retrieved) == 0,
        },
    }

    trajectory = list(state.get("trajectory", []))
    trajectory.append(trace)

    return {
        "retrieved_memories": retrieved,
        "retrieved_experiences": retrieved,
        "positive_strategy": positive_strategy,
        "negative_pitfall": negative_pitfall,
        "trajectory": trajectory,
        "status": "executing",
    }
