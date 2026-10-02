"""
Append-only exposure evidence.

One `ExposureRecord` per (run, task, memory-or-None). `memory_id=None` denotes a task
executed with no memory injected, so fallback and memory-off conditions are recorded
explicitly rather than inferred from absence. k>1 retrieval extends naturally to
several rows sharing a task_id.

The log is the record of truth. Policy state is a derived cache that can always be
rebuilt by replaying this log -- which is what makes replay fidelity testable.

Raw outcome preservation: every record keeps the continuous `reward`, the
`binary_outcome`, the `outcome_threshold` used, and the full per-attempt sequence.
Nothing is reduced to a single trust number.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional

from ai_service.trust.base import Observation


@dataclass(frozen=True)
class AttemptEvidence:
    """Per-attempt diagnostic detail (F1). Never an independent observation."""
    attempt_index: int
    reward: float
    binary_outcome: int
    outcome_threshold: float
    evaluator_name: Optional[str] = None
    tokens_used: int = 0
    is_terminal: bool = False


@dataclass(frozen=True)
class ExposureRecord:
    """A single task-level memory exposure."""

    # identity
    run_id: str
    task_id: str
    task_index: int
    memory_id: Optional[str]
    exposure_id: str

    # provenance / reproducibility
    condition_id: str = "default"
    policy_name: str = ""
    policy_params_hash: str = ""
    memory_content_hash: Optional[str] = None
    bank_hash: Optional[str] = None

    # retrieval
    domain: Optional[str] = None
    similarity: Optional[float] = None
    composite_score: Optional[float] = None
    candidate_count: int = 0
    admissible_count: int = 0
    passed_trust_gate: bool = False
    gate_reason: str = ""
    fallback_occurred: bool = False
    injected: bool = False

    # task-level outcome (raw signal preserved)
    reward: float = 0.0
    binary_outcome: int = 0
    outcome_threshold: float = 0.80
    evaluator_name: Optional[str] = None

    # attempt-level diagnostics
    n_attempts: int = 0
    attempts: List[AttemptEvidence] = field(default_factory=list)

    # policy state transition captured at the moment of update
    policy_state_before: Optional[Dict[str, Any]] = None
    policy_state_after: Optional[Dict[str, Any]] = None

    # baseline / cost
    stateless_reward: Optional[float] = None
    stateless_binary: Optional[int] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0

    def to_observation(self) -> Observation:
        """Rebuilds the policy input. Used by replay -- no re-derivation of outcomes."""
        if self.memory_id is None:
            raise ValueError("exposure has no memory_id; it is not an observation")
        return Observation(
            memory_id=self.memory_id,
            task_id=self.task_id,
            run_id=self.run_id,
            task_index=self.task_index,
            reward=self.reward,
            binary_outcome=self.binary_outcome,
            outcome_threshold=self.outcome_threshold,
            similarity=self.similarity,
            domain=self.domain,
            evaluator_name=self.evaluator_name,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class ExposureLog:
    """Append-only, ordered. No update, no delete."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._records: List[ExposureRecord] = []

    def append(self, record: ExposureRecord) -> None:
        if record.run_id != self.run_id:
            raise ValueError(
                f"run isolation violated: record run_id={record.run_id!r} "
                f"appended to log for run_id={self.run_id!r}"
            )
        self._records.append(record)

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[ExposureRecord]:
        return iter(self._records)

    @property
    def records(self) -> List[ExposureRecord]:
        return list(self._records)

    def observations(self) -> List[Observation]:
        """Task-level observations, in order. Attempts are not observations."""
        return [r.to_observation() for r in self._records if r.memory_id is not None]

    def for_memory(self, memory_id: str) -> List[ExposureRecord]:
        return [r for r in self._records if r.memory_id == memory_id]

    def to_jsonl(self) -> str:
        return "\n".join(r.to_json() for r in self._records)

    def write_jsonl(self, path: str) -> None:
        import os

        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for rec in self._records:
                fh.write(rec.to_json() + "\n")

    @classmethod
    def from_records(cls, run_id: str, records: Iterable[ExposureRecord]) -> "ExposureLog":
        log = cls(run_id)
        for rec in records:
            log.append(rec)
        return log
