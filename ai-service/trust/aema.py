"""
A-EMA ported behind the TrustPolicy interface.

Step 1 is an infrastructure change, not a mechanism change. This class therefore
DELEGATES to `ai_service.nodes.trust_node.compute_next_trust` rather than
reimplementing the recursion -- there is exactly one copy of the arithmetic in the
codebase, so the ported policy cannot silently drift from the reference.

Behaviour preserved exactly:
  success (R >= 0.80): S' = 0.85*S + 0.15
  failure (R <= 0.30): S' = 0.70*S
  neutral            : S' = 0.80*S + 0.20*R
  quarantine         : S < 0.35
  S_0 = 0.75

One thing is deliberately NOT inherited: the evidence counters. Those now follow the
evaluator's `binary_outcome` (F3) instead of the sign of the trust delta. A-EMA still
consumes the continuous reward for its own recursion, which is what preserves its
numeric behaviour.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ai_service.nodes.trust_node import (
    ALPHA_SUCCESS,
    BETA_FAILURE,
    GAMMA_NEUTRAL,
    QUARANTINE_THRESHOLD,
    compute_next_trust,
)
from ai_service.trust.base import (
    Decision,
    Observation,
    PolicyContext,
    PolicyState,
    TrustPolicy,
)

DEFAULT_INITIAL_TRUST: float = 0.75
TRUST_KEY = "trust_score"


class AEMAPolicy(TrustPolicy):
    """Asymmetric Exponential Moving Average -- the Step 0 reference mechanism."""

    name = "aema"

    def __init__(
        self,
        initial_trust: float = DEFAULT_INITIAL_TRUST,
        quarantine_threshold: float = QUARANTINE_THRESHOLD,
    ):
        self.initial_trust = float(initial_trust)
        self.quarantine_threshold = float(quarantine_threshold)

    @property
    def params(self) -> Dict[str, Any]:
        return {
            "alpha_success": ALPHA_SUCCESS,
            "beta_failure": BETA_FAILURE,
            "gamma_neutral": GAMMA_NEUTRAL,
            "quarantine_threshold": self.quarantine_threshold,
            "initial_trust": self.initial_trust,
        }

    def initial_state(self, memory_id: str, trust_score: Optional[float] = None, **kwargs: Any) -> PolicyState:
        """
        `trust_score` seeds from the memory bank's declared starting trust so a fixed
        bank can define heterogeneous initial values without mutating bank content.
        """
        seed = self.initial_trust if trust_score is None else float(trust_score)
        return PolicyState(memory_id=memory_id, extra={TRUST_KEY: seed})

    def update(self, state: PolicyState, observation: Observation) -> PolicyState:
        """PURE. Delegates the recursion to the single reference implementation."""
        old_trust = float(state.extra.get(TRUST_KEY, self.initial_trust))
        new_trust, reason = compute_next_trust(old_trust, observation.reward)
        return state.with_observation(
            observation,
            **{TRUST_KEY: new_trust, "last_reason": reason},
        )

    def admissible(self, state: PolicyState, ctx: PolicyContext) -> Decision:
        trust = float(state.extra.get(TRUST_KEY, self.initial_trust))
        if trust < self.quarantine_threshold:
            return Decision(
                admissible=False,
                reason=f"quarantined: trust {trust:.4f} < theta {self.quarantine_threshold}",
                score=trust,
                diagnostics={TRUST_KEY: trust},
            )
        return Decision(
            admissible=True,
            reason=f"admissible: trust {trust:.4f} >= theta {self.quarantine_threshold}",
            score=trust,
            diagnostics={TRUST_KEY: trust},
        )

    def score(self, state: PolicyState, ctx: PolicyContext) -> Optional[float]:
        """A-EMA's trust score is the trust term used by the legacy composite ranker."""
        return float(state.extra.get(TRUST_KEY, self.initial_trust))


class StaticTrustPolicy(TrustPolicy):
    """
    No-op policy: trust never changes and every memory stays admissible.

    Needed so that similarity-only retrieval can be expressed through the same
    interface. Introduces no new mechanism -- it is the absence of one.
    """

    name = "static"

    def __init__(self, initial_trust: float = DEFAULT_INITIAL_TRUST):
        self.initial_trust = float(initial_trust)

    @property
    def params(self) -> Dict[str, Any]:
        return {"initial_trust": self.initial_trust}

    def initial_state(self, memory_id: str, trust_score: Optional[float] = None, **kwargs: Any) -> PolicyState:
        seed = self.initial_trust if trust_score is None else float(trust_score)
        return PolicyState(memory_id=memory_id, extra={TRUST_KEY: seed})

    def update(self, state: PolicyState, observation: Observation) -> PolicyState:
        """Counters still advance -- evidence is recorded even when trust is frozen."""
        return state.with_observation(observation)

    def admissible(self, state: PolicyState, ctx: PolicyContext) -> Decision:
        return Decision(
            admissible=True,
            reason="static policy: always admissible",
            score=float(state.extra.get(TRUST_KEY, self.initial_trust)),
        )

    def score(self, state: PolicyState, ctx: PolicyContext) -> Optional[float]:
        return float(state.extra.get(TRUST_KEY, self.initial_trust))
