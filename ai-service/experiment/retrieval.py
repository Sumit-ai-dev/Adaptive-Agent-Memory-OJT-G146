"""
Policy-backed retrieval.

Retrieval no longer contains hardcoded trust logic. Admissibility comes from an
injected `TrustPolicy`; ranking comes from an injected `Ranker`.

IMPORTANT -- Step 1 does not change retrieval scoring. `LegacyModeRanker` reproduces
the formulas in `ai_service.memory.retriever` exactly:

    NAIVE      composite = sim                              , admit if sim >= (tau - 0.20)
    SYMMETRIC  composite = w_sim*sim + w_trust*trust         , no extra filter
    ADAPTIVE   composite = round(sim * beta_lcb(s, f), 4)    , admit if not quarantined
                                                               and sim >= tau

The Beta/LCB calls in the ADAPTIVE path are PRE-EXISTING code
(`ai_service.trust_math`, used by the legacy retriever today). They are preserved
here to keep behaviour identical. They are NOT a new trust mechanism and are not
reachable from `TrustPolicy`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from ai_service.config import settings
from ai_service.experiment.memory_bank import MemoryBank, MemoryRecord
from ai_service.experiment.run_context import RunContext
from ai_service.trust.base import Decision, PolicyContext, PolicyState, TrustPolicy
from ai_service.trust_math import beta_lcb, should_quarantine
from models.domain import MemoryMode, TaskDomain


def cosine(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Clamped cosine, matching `ai_service.nodes.retrieve_node.cosine_similarity`."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (n1 * n2)))


@dataclass(frozen=True)
class RetrievalCandidate:
    record: MemoryRecord
    similarity: float
    state: PolicyState
    decision: Decision
    composite_score: float


class Ranker(Protocol):
    """Injected scoring strategy."""

    name: str

    def admit(self, record: MemoryRecord, similarity: float, state: PolicyState) -> Tuple[bool, str]:
        ...

    def composite(self, record: MemoryRecord, similarity: float, state: PolicyState,
                  policy_score: Optional[float]) -> float:
        ...


class LegacyModeRanker:
    """
    Bit-compatible reproduction of the existing per-mode retrieval scoring.

    Preserved verbatim so Step 1 cannot alter A-EMA/retrieval behaviour. Any future
    change to scoring is a separate, explicit decision.
    """

    def __init__(self, mode: MemoryMode):
        self.mode = mode
        self.name = f"legacy_{mode.value}"

    def admit(self, record: MemoryRecord, similarity: float, state: PolicyState) -> Tuple[bool, str]:
        if self.mode == MemoryMode.NAIVE:
            thr = settings.SIMILARITY_THRESHOLD - 0.20
            if similarity < thr:
                return False, f"naive: sim {similarity:.4f} < {thr:.4f}"
            return True, "naive: similarity cutoff cleared"

        if self.mode == MemoryMode.SYMMETRIC:
            return True, "symmetric: no additional filter"

        # ADAPTIVE -- legacy statistical quarantine, unchanged.
        quarantined = should_quarantine(
            successes=state.successes,
            failures=state.failures,
            gamma=settings.QUARANTINE_GAMMA,
            threshold=settings.RELIABILITY_THRESHOLD,
            alpha_0=settings.PRIOR_ALPHA,
            beta_0=settings.PRIOR_BETA,
        )
        if quarantined:
            return False, "adaptive: statistical quarantine (legacy)"
        if similarity < settings.SIMILARITY_THRESHOLD:
            return False, f"adaptive: sim {similarity:.4f} < {settings.SIMILARITY_THRESHOLD}"
        return True, "adaptive: admissible"

    def composite(self, record: MemoryRecord, similarity: float, state: PolicyState,
                  policy_score: Optional[float]) -> float:
        trust = policy_score if policy_score is not None else record.initial_trust

        if self.mode == MemoryMode.NAIVE:
            return similarity
        if self.mode == MemoryMode.SYMMETRIC:
            return (settings.WEIGHT_SIMILARITY * similarity) + (settings.WEIGHT_TRUST * trust)

        lcb = beta_lcb(
            successes=state.successes,
            failures=state.failures,
            lambda_risk=settings.LAMBDA_RISK,
            alpha_0=settings.PRIOR_ALPHA,
            beta_0=settings.PRIOR_BETA,
        )
        return round(similarity * lcb, 4)


class SimilarityOnlyRanker:
    """Ranks by similarity alone. No trust term, no weighting constants."""

    name = "similarity_only"

    def __init__(self, similarity_threshold: Optional[float] = None):
        self.similarity_threshold = (
            settings.SIMILARITY_THRESHOLD if similarity_threshold is None else similarity_threshold
        )

    def admit(self, record: MemoryRecord, similarity: float, state: PolicyState) -> Tuple[bool, str]:
        if similarity < self.similarity_threshold:
            return False, f"sim {similarity:.4f} < {self.similarity_threshold}"
        return True, "similarity cutoff cleared"

    def composite(self, record: MemoryRecord, similarity: float, state: PolicyState,
                  policy_score: Optional[float]) -> float:
        return similarity


class PolicyBackedRetriever:
    """
    Retrieval driven by an injected policy (gate) and ranker (score).

    Trust state is read from the RunContext, never from the memory bank.
    """

    def __init__(self, run: RunContext, ranker: Ranker, embedder: Any = None):
        self.run = run
        self.ranker = ranker
        self._embedder = embedder

    @property
    def embedder(self) -> Any:
        if self._embedder is None:
            from ai_service.embedder import local_embedder

            self._embedder = local_embedder
        return self._embedder

    def retrieve(
        self,
        query: str,
        domain: Optional[TaskDomain] = None,
        top_k: int = 2,
    ) -> Tuple[List[RetrievalCandidate], Dict[str, Any]]:
        """Returns (selected candidates, diagnostics)."""
        bank: MemoryBank = self.run.bank
        policy: TrustPolicy = self.run.policy
        ctx: PolicyContext = self.run.policy_context(
            domain.value if isinstance(domain, TaskDomain) else domain
        )

        pool = bank.by_domain(domain)
        diagnostics: Dict[str, Any] = {
            "candidate_count": len(pool),
            "admissible_count": 0,
            "gate_reasons": {},
            "ranker": self.ranker.name,
            "policy": policy.name,
        }
        if not pool:
            return [], diagnostics

        qvec = self.embedder.embed_text(query)
        admitted: List[RetrievalCandidate] = []

        for rec in pool:
            sim = cosine(qvec, rec.embedding) if rec.embedding else 0.0
            state = self.run.trust_state.get(rec.memory_id)

            # 1. Policy gate (injected -- no hardcoded trust logic here).
            decision = policy.admissible(state, ctx)
            if not decision.admissible:
                diagnostics["gate_reasons"][rec.memory_id] = f"policy: {decision.reason}"
                continue

            # 2. Ranker-specific admission (legacy per-mode filters).
            ok, reason = self.ranker.admit(rec, sim, state)
            if not ok:
                diagnostics["gate_reasons"][rec.memory_id] = f"ranker: {reason}"
                continue

            composite = self.ranker.composite(rec, sim, state, policy.score(state, ctx))
            admitted.append(
                RetrievalCandidate(
                    record=rec, similarity=sim, state=state,
                    decision=decision, composite_score=composite,
                )
            )

        admitted.sort(key=lambda c: c.composite_score, reverse=True)
        diagnostics["admissible_count"] = len(admitted)
        return admitted[:top_k], diagnostics
