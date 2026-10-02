"""
Offline policy replay.

WHAT REPLAY CAN DO (exactly, from observed evidence):
    observed outcomes -> policy state transitions -> admissibility decisions

Because `TrustPolicy.update` is pure and `PolicyState` is derived solely from the
observation sequence, replaying a log through the SAME policy must reproduce the live
run's state trajectory and decisions exactly. That equality is the fidelity test.

WHAT REPLAY CANNOT DO:
    It CANNOT reconstruct task outcomes that were never observed.

If a different policy would have suppressed a memory the live run injected, the task's
outcome under that policy is unobserved and unknowable from this log. Recovering it
would require an outcome matrix -- observed results for (task, memory) and (task, none)
-- which is NOT built here. Any function returning counterfactual *outcomes* without
that matrix would be fabricating data, so none is provided.

Replay therefore returns DECISION TRAJECTORIES only. Comparing two policies tells you
when each would admit or suppress each memory. It does not tell you what the agent
would have scored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ai_service.experiment.evidence import ExposureLog, ExposureRecord
from ai_service.trust.base import Decision, Observation, PolicyContext, PolicyState, TrustPolicy


@dataclass(frozen=True)
class ReplayStep:
    """One observation replayed through a policy."""
    task_index: int
    task_id: str
    memory_id: str
    observation_reward: float
    observation_binary: int
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    admissible_before: bool
    admissible_after: bool
    gate_reason_after: str


@dataclass
class ReplayResult:
    """
    Decision trajectory for one policy over one observation sequence.

    `counterfactual_outcomes` is intentionally absent. See the module docstring.
    """
    policy_name: str
    policy_params: Dict[str, Any]
    run_id: str
    steps: List[ReplayStep] = field(default_factory=list)
    final_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def suppressed_memories(self) -> List[str]:
        """Memories not admissible at the end of the sequence."""
        out = []
        for step in reversed(self.steps):
            if step.memory_id in out:
                continue
            if not step.admissible_after:
                out.append(step.memory_id)
        return sorted(set(out))

    def first_suppression_index(self, memory_id: str) -> Optional[int]:
        """1-based exposure count at which this memory first became inadmissible."""
        seen = 0
        for step in self.steps:
            if step.memory_id != memory_id:
                continue
            seen += 1
            if not step.admissible_after:
                return seen
        return None

    def decision_signature(self) -> List[tuple]:
        """Compact, comparable representation of the decision trajectory."""
        return [
            (s.task_index, s.memory_id, s.admissible_after, round(s.observation_reward, 6))
            for s in self.steps
        ]


def replay_observations(
    observations: Iterable[Observation],
    policy: TrustPolicy,
    run_id: str = "replay",
    initial_trust_by_memory: Optional[Dict[str, float]] = None,
) -> ReplayResult:
    """
    Replays an observation sequence through a policy.

    Pure: no I/O, no globals. Given the same inputs it always yields the same result.
    """
    seeds = initial_trust_by_memory or {}
    states: Dict[str, PolicyState] = {}
    result = ReplayResult(
        policy_name=policy.name, policy_params=dict(policy.params), run_id=run_id
    )

    for obs in observations:
        ctx = PolicyContext(run_id=run_id, domain=obs.domain)

        if obs.memory_id not in states:
            states[obs.memory_id] = policy.initial_state(
                obs.memory_id, trust_score=seeds.get(obs.memory_id)
            )

        before = states[obs.memory_id]
        decision_before: Decision = policy.admissible(before, ctx)

        after = policy.update(before, obs)
        states[obs.memory_id] = after
        decision_after: Decision = policy.admissible(after, ctx)

        result.steps.append(
            ReplayStep(
                task_index=obs.task_index,
                task_id=obs.task_id,
                memory_id=obs.memory_id,
                observation_reward=obs.reward,
                observation_binary=obs.binary_outcome,
                state_before=before.to_dict(),
                state_after=after.to_dict(),
                admissible_before=decision_before.admissible,
                admissible_after=decision_after.admissible,
                gate_reason_after=decision_after.reason,
            )
        )

    result.final_states = {mid: st.to_dict() for mid, st in sorted(states.items())}
    return result


def replay_log(
    log: ExposureLog,
    policy: TrustPolicy,
    initial_trust_by_memory: Optional[Dict[str, float]] = None,
) -> ReplayResult:
    """Replays an exposure log. Non-observation rows (memory_id=None) are skipped."""
    return replay_observations(
        observations=log.observations(),
        policy=policy,
        run_id=log.run_id,
        initial_trust_by_memory=initial_trust_by_memory,
    )


def compare_policies(
    log: ExposureLog,
    policies: Iterable[TrustPolicy],
    initial_trust_by_memory: Optional[Dict[str, float]] = None,
) -> Dict[str, ReplayResult]:
    """
    Runs several policies over the SAME observed evidence.

    Valid comparison: when each policy would admit/suppress each memory.
    NOT valid, and not returned: what the agent would have scored under each policy.
    """
    return {
        p.name: replay_log(log, p, initial_trust_by_memory=initial_trust_by_memory)
        for p in policies
    }
