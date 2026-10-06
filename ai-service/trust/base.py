"""
TrustPolicy -- the pluggable decision boundary for memory reuse.

Step 1 introduces the abstraction only. It does NOT choose a mechanism. A-EMA is
ported behind this interface with its arithmetic unchanged and remains the reference
implementation.

Four invariants make this interface useful rather than decorative:

1. `update` is PURE: (state, observation) -> new state. No I/O, no globals, no clock,
   no RNG. This is the single property that makes offline replay provably equivalent
   to the live run.

2. `PolicyState` is immutable and fully serialisable, so a run's policy state can be
   reconstructed from its observation sequence alone.

3. Evidence counters come from the evaluator's `binary_outcome` (F3), never from the
   sign of a trust delta. A policy may additionally consume the continuous `reward`
   -- A-EMA does -- but it may not redefine what counted as a success.

4. `score` defaults to None, meaning "this policy expresses no ranking opinion". That
   is how similarity-only ranking is expressed without any weighting constant.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class Observation:
    """
    One TASK-LEVEL outcome for one memory exposure.

    Exactly one of these exists per (task, memory). Retry attempts inside a task do
    not produce additional observations -- see F1.
    """
    memory_id: str
    task_id: str
    run_id: str
    task_index: int
    reward: float                 # continuous R in [0,1], always preserved
    binary_outcome: int           # 0/1, produced by the evaluator (F3)
    outcome_threshold: float
    similarity: Optional[float] = None
    domain: Optional[str] = None
    evaluator_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.binary_outcome not in (0, 1):
            raise ValueError(f"binary_outcome must be 0 or 1, got {self.binary_outcome!r}")
        if not (0.0 <= self.reward <= 1.0):
            raise ValueError(f"reward must lie in [0,1], got {self.reward!r}")


@dataclass(frozen=True)
class PolicyState:
    """
    Immutable per-(run, memory) policy state.

    `uses`, `successes`, `failures` are the mechanism-independent evidence counters and
    always satisfy `successes + failures == uses`. `extra` holds policy-private scalars
    (A-EMA keeps its trust score there) and is kept read-only.
    """
    memory_id: str
    uses: int = 0
    successes: int = 0
    failures: int = 0
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))
        if self.successes + self.failures != self.uses:
            raise ValueError(
                f"counter invariant violated for {self.memory_id}: "
                f"{self.successes} + {self.failures} != {self.uses}"
            )

    def with_observation(self, observation: Observation, **extra: Any) -> "PolicyState":
        """Returns a new state with counters advanced by one observation."""
        return replace(
            self,
            uses=self.uses + 1,
            successes=self.successes + (1 if observation.binary_outcome == 1 else 0),
            failures=self.failures + (1 if observation.binary_outcome == 0 else 0),
            extra=MappingProxyType({**dict(self.extra), **extra}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "uses": self.uses,
            "successes": self.successes,
            "failures": self.failures,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PolicyState":
        return cls(
            memory_id=data["memory_id"],
            uses=int(data.get("uses", 0)),
            successes=int(data.get("successes", 0)),
            failures=int(data.get("failures", 0)),
            extra=MappingProxyType(dict(data.get("extra", {}))),
        )


@dataclass(frozen=True)
class PolicyContext:
    """
    Run-level context injected into admissibility decisions.

    Carried explicitly so policies never read module globals -- that coupling is what
    made the previous trust logic impossible to swap.
    """
    run_id: str
    domain: Optional[str] = None
    baseline_success_rate: Optional[float] = None   # measured p0, when available


@dataclass(frozen=True)
class Decision:
    """Outcome of an admissibility check. Carries a reason for diagnostics."""
    admissible: bool
    reason: str = ""
    score: Optional[float] = None       # ranking contribution; None = no opinion
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


class TrustPolicy(ABC):
    """Base class for memory-reuse policies."""

    #: Stable identifier recorded in the run manifest.
    name: str = "abstract"

    @property
    def params(self) -> Dict[str, Any]:
        """Frozen hyper-parameters, hashed into the run manifest."""
        return {}

    @abstractmethod
    def initial_state(self, memory_id: str, **kwargs: Any) -> PolicyState:
        """State for a memory that has not yet been observed in this run."""

    @abstractmethod
    def update(self, state: PolicyState, observation: Observation) -> PolicyState:
        """
        PURE. Must not perform I/O, read globals, consult a clock, or use randomness.
        Replay fidelity depends on this.
        """

    @abstractmethod
    def admissible(self, state: PolicyState, ctx: PolicyContext) -> Decision:
        """Whether this memory may be retrieved given its accumulated state."""

    def score(self, state: PolicyState, ctx: PolicyContext) -> Optional[float]:
        """Ranking contribution. None means the policy expresses no opinion."""
        return None

    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "params": dict(self.params)}
