"""
Memory Retriever supporting the 4 Controlled Experimental Ablation Conditions:
  - Condition A: Memory OFF (Baseline / Vanilla ReAct)
  - Condition B: Naive Vector RAG (pure cosine, no reliability filtering)
  - Condition C: Symmetric Reflexion (symmetric trust scoring)
  - Condition D: Adaptive Agent Memory (composite 0.70*Sim + 0.30*Trust, theta=0.35 cutoff)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ai_service.config import settings
from ai_service.embedder import local_embedder
from ai_service.memory.store import BaseMemoryStore, memory_store
from ai_service.trust_math import beta_lcb, should_quarantine
from models.domain import ExperienceStatus, MemoryMode, TaskDomain
from models.experience import RetrievedMemory

logger = logging.getLogger("ai_service.memory.retriever")


class MemoryRetriever:
    """
    Retrieves and ranks relevant experiential memories under specific ablation modes.
    """

    def __init__(self, store: Optional[BaseMemoryStore] = None):
        self.store = store or memory_store

    async def retrieve_with_diagnostics(
        self,
        query: str,
        domain: TaskDomain = TaskDomain.GENERAL,
        mode: MemoryMode = MemoryMode.ADAPTIVE,
        top_k: int = 3,
    ) -> Tuple[List[RetrievedMemory], Dict[str, Any]]:
        """
        Executes constrained retrieval based on the operational memory mode and returns
        both the ranked memories and retrieval funnel diagnostics.
        """
        diagnostics: Dict[str, Any] = {
            "candidate_count": 0,
            "admissible_count": 0,
            "gate_reasons": {},
            "ranker": "lcb" if mode == MemoryMode.ADAPTIVE else f"retriever_{mode.value}",
            "policy": "aema" if mode == MemoryMode.ADAPTIVE else mode.value,
        }

        # Condition A: Memory OFF
        if mode == MemoryMode.OFF:
            return [], diagnostics

        # Embed query text
        query_vec = local_embedder.embed_text(query)

        # Retrieve top candidates by raw cosine similarity
        raw_matches = await self.store.search_similar(query_vec, domain=domain, top_k=top_k * 3)
        if not raw_matches:
            return [], diagnostics

        diagnostics["candidate_count"] = len(raw_matches)
        results: List[RetrievedMemory] = []
        gate_reasons: Dict[str, str] = {}

        for exp, raw_sim in raw_matches:
            trust = float(exp.trust_score)

            # P0-1: `ExperienceMatch.similarity` is declared `ge=0.0, le=1.0`, but
            # `BaseMemoryStore.search_similar` returns an unclamped cosine in [-1, 1].
            # Clamp to the unit interval using the same convention already applied by
            # `ai_service.nodes.retrieve_node.cosine_similarity`. No ranking semantics change.
            sim = max(0.0, min(1.0, float(raw_sim)))

            # Condition B: Naive Vector RAG (relevance only, no quarantine, no trust weighting)
            if mode == MemoryMode.NAIVE:
                # Naive RAG accepts any memory above similarity cutoff, ignoring trust score
                if sim >= (settings.SIMILARITY_THRESHOLD - 0.20):
                    results.append(
                        RetrievedMemory(
                            experience=exp,
                            similarity=sim,
                            composite_score=sim,
                        )
                    )
                else:
                    gate_reasons[exp.id] = f"similarity below naive cutoff ({sim:.3f})"

            # Condition C: Symmetric Reflexion
            elif mode == MemoryMode.SYMMETRIC:
                composite = (settings.WEIGHT_SIMILARITY * sim) + (settings.WEIGHT_TRUST * trust)
                results.append(
                    RetrievedMemory(
                        experience=exp,
                        similarity=sim,
                        composite_score=composite,
                    )
                )

            # Condition D: Adaptive Agent Memory (OURS: Bayesian LCB + Statistical Quarantine)
            elif mode == MemoryMode.ADAPTIVE:
                # 1. Statistical Quarantine filter (Theorem 1)
                is_quar = should_quarantine(
                    successes=exp.successes_count,
                    failures=exp.failures_count,
                    gamma=settings.QUARANTINE_GAMMA,
                    threshold=settings.RELIABILITY_THRESHOLD,
                    alpha_0=settings.PRIOR_ALPHA,
                    beta_0=settings.PRIOR_BETA,
                ) or (trust < settings.THETA_CUTOFF) or (exp.status == ExperienceStatus.DEPRECATED)

                if is_quar:
                    logger.debug(f"Quarantined memory {exp.id} (P(reliable) < {settings.QUARANTINE_GAMMA} or trust={trust:.2f})")
                    gate_reasons[exp.id] = f"quarantined (P(reliable) < {settings.QUARANTINE_GAMMA} or trust={trust:.2f})"
                    continue

                # 2. Status filter: Exclude deprecated / quarantined memories
                if exp.status == ExperienceStatus.DEPRECATED:
                    gate_reasons[exp.id] = "deprecated"
                    continue

                # 3. Relevance threshold
                if sim < settings.SIMILARITY_THRESHOLD:
                    gate_reasons[exp.id] = f"similarity below threshold ({sim:.3f} < {settings.SIMILARITY_THRESHOLD})"
                    continue

                # 4. Pessimistic Lower Confidence Bound (LCB) composite score
                lcb_val = beta_lcb(
                    successes=exp.successes_count,
                    failures=exp.failures_count,
                    lambda_risk=settings.LAMBDA_RISK,
                    alpha_0=settings.PRIOR_ALPHA,
                    beta_0=settings.PRIOR_BETA,
                )
                composite = round(sim * lcb_val, 4)
                results.append(
                    RetrievedMemory(
                        experience=exp,
                        similarity=sim,
                        composite_score=composite,
                    )
                )

        # Sort by composite score descending
        results.sort(key=lambda m: m.composite_score, reverse=True)
        diagnostics["admissible_count"] = len(results)
        diagnostics["gate_reasons"] = gate_reasons
        return results[:top_k], diagnostics

    async def retrieve(
        self,
        query: str,
        domain: TaskDomain = TaskDomain.GENERAL,
        mode: MemoryMode = MemoryMode.ADAPTIVE,
        top_k: int = 3,
    ) -> List[RetrievedMemory]:
        """
        Executes constrained retrieval based on the operational memory mode.
        Backwards-compatible wrapper returning List[RetrievedMemory].
        """
        results, _ = await self.retrieve_with_diagnostics(
            query=query, domain=domain, mode=mode, top_k=top_k
        )
        return results


# Global default retriever instance
memory_retriever = MemoryRetriever()
