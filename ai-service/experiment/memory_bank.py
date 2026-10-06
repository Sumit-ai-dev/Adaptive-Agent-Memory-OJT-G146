"""
Immutable memory content, separated from mutable trust state.

Previously `Experience` carried content AND evidence AND trust in one row, so any run
that updated trust permanently altered the bank for every later run. `MemoryRecord`
carries content only. Accumulated evidence lives in run-scoped policy state
(`ai_service.experiment.run_context.TrustStateStore`).

A `MemoryBank` is frozen on construction and exposes a content hash, so a run manifest
can prove which bank produced its evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence

from models.domain import TaskDomain
from models.experience import Experience, ExperienceStatus


@dataclass(frozen=True)
class MemoryRecord:
    """
    Immutable memory content.

    Deliberately carries NO trust_score, uses_count, successes_count, failures_count
    or status. Those are per-run evidence, not properties of the content.

    `strategy` / `pitfall` are retained as separate fields so the existing bilateral
    prompt construction keeps working unchanged. Whether that split is the right
    representation is a separate research question and is not decided here.
    """
    memory_id: str
    domain: TaskDomain
    trigger: str
    strategy: str
    pitfall: Optional[str] = None
    provenance: str = "authored"
    embedding: Optional[Sequence[float]] = None
    initial_trust: float = 0.75          # seed for policy state; bank content, not live trust
    labels: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.labels, MappingProxyType):
            object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))
        if self.embedding is not None and not isinstance(self.embedding, tuple):
            object.__setattr__(self, "embedding", tuple(float(v) for v in self.embedding))

    @property
    def content_hash(self) -> str:
        """SHA-256 over content only. Embedding and labels are excluded."""
        payload = json.dumps(
            {
                "memory_id": self.memory_id,
                "domain": self.domain.value if hasattr(self.domain, "value") else str(self.domain),
                "trigger": self.trigger,
                "strategy": self.strategy,
                "pitfall": self.pitfall,
                "provenance": self.provenance,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # --- interop with the legacy Experience model -------------------------------

    @classmethod
    def from_experience(cls, exp: Experience) -> "MemoryRecord":
        return cls(
            memory_id=exp.id,
            domain=exp.task_domain,
            trigger=exp.trigger_condition,
            strategy=exp.strategy_lesson,
            pitfall=exp.pitfall,
            provenance="legacy_experience",
            embedding=tuple(exp.embedding) if exp.embedding else None,
            initial_trust=float(exp.trust_score),
        )

    def to_experience(
        self,
        trust_score: Optional[float] = None,
        uses: int = 0,
        successes: int = 0,
        failures: int = 0,
        status: ExperienceStatus = ExperienceStatus.ACTIVE,
    ) -> Experience:
        """
        Projects content + supplied run-scoped evidence into the legacy model.

        Used only at the boundary where downstream code still expects an `Experience`.
        The returned object is a throwaway view; mutating it cannot affect the bank.
        """
        return Experience(
            id=self.memory_id,
            task_domain=self.domain,
            trigger_condition=self.trigger,
            strategy_lesson=self.strategy,
            pitfall=self.pitfall,
            trust_score=self.initial_trust if trust_score is None else float(trust_score),
            uses_count=uses,
            successes_count=successes,
            failures_count=failures,
            status=status,
            embedding=list(self.embedding) if self.embedding else None,
        )


class MemoryBank:
    """
    A frozen collection of MemoryRecords.

    There is no `add` and no `update`. A bank is constructed once and is read-only for
    the lifetime of every run that uses it.
    """

    def __init__(self, records: Iterable[MemoryRecord], bank_id: str = "bank"):
        items: Dict[str, MemoryRecord] = {}
        for rec in records:
            if rec.memory_id in items:
                raise ValueError(f"duplicate memory_id in bank: {rec.memory_id}")
            items[rec.memory_id] = rec
        self._records: Mapping[str, MemoryRecord] = MappingProxyType(items)
        self.bank_id = bank_id

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[MemoryRecord]:
        return iter(self._records.values())

    def __contains__(self, memory_id: object) -> bool:
        return memory_id in self._records

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        return self._records.get(memory_id)

    def ids(self) -> List[str]:
        return sorted(self._records)

    def by_domain(self, domain: Optional[TaskDomain]) -> List[MemoryRecord]:
        if domain is None:
            return list(self._records.values())
        return [r for r in self._records.values() if r.domain == domain]

    @property
    def bank_hash(self) -> str:
        """Order-independent hash over every record's content hash."""
        digest = hashlib.sha256()
        for mid in sorted(self._records):
            digest.update(self._records[mid].content_hash.encode("utf-8"))
        return digest.hexdigest()

    def ensure_embeddings(self) -> "MemoryBank":
        """
        Returns a bank in which every record has an embedding, computing any that are
        missing from `trigger`. Returns a NEW bank -- the original is untouched.
        """
        from ai_service.embedder import local_embedder

        out: List[MemoryRecord] = []
        for rec in self._records.values():
            if rec.embedding is None:
                vec = tuple(local_embedder.embed_text(rec.trigger or ""))
                out.append(
                    MemoryRecord(
                        memory_id=rec.memory_id, domain=rec.domain, trigger=rec.trigger,
                        strategy=rec.strategy, pitfall=rec.pitfall, provenance=rec.provenance,
                        embedding=vec, initial_trust=rec.initial_trust, labels=rec.labels,
                    )
                )
            else:
                out.append(rec)
        return MemoryBank(out, bank_id=self.bank_id)

    @classmethod
    def from_experiences(cls, experiences: Iterable[Experience], bank_id: str = "bank") -> "MemoryBank":
        return cls((MemoryRecord.from_experience(e) for e in experiences), bank_id=bank_id)
