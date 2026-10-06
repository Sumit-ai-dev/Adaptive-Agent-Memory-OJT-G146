"""
Run identity, isolation, and reproducibility metadata.

A `RunContext` owns everything mutable for one run:
  * run-scoped policy state  (TrustStateStore)
  * the run's append-only exposure log
  * the memory-write gate

It holds the memory bank by reference and never mutates it. Two RunContexts over the
same bank cannot observe each other's state -- that is the property the previous
architecture lacked, because trust lived inside the shared `experiences` table.

There are no module-level singletons in this module. A run must be constructed
explicitly, which is what prevents the global-store contamination present in
`memory_store` / `memory_retriever` / `shared_store`.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai_service.experiment.evidence import ExposureLog
from ai_service.experiment.memory_bank import MemoryBank
from ai_service.trust.base import Observation, PolicyContext, PolicyState, TrustPolicy
from models.provider import ModelProvider, ProviderConfig, provider_supports_seed, validate_seed
from models.task import DEFAULT_OUTCOME_THRESHOLD


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _git_sha() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


def _git_dirty() -> Optional[bool]:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5,
        )
        return bool(out.stdout.strip()) if out.returncode == 0 else None
    except Exception:
        return None


def params_hash(params: Dict[str, Any]) -> str:
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class RunManifest:
    """
    Everything needed to reproduce a run. Written BEFORE execution -- a manifest
    produced afterwards can be retrofitted to its own result.
    """
    run_id: str
    condition_id: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # mechanism
    policy_name: str = ""
    policy_params: Dict[str, Any] = field(default_factory=dict)
    policy_params_hash: str = ""

    # materials
    bank_id: str = ""
    bank_hash: str = ""
    bank_size: int = 0

    # retrieval configuration (recorded, never tuned here)
    memory_mode: str = "adaptive"
    ranker_name: str = ""
    similarity_threshold: Optional[float] = None
    top_k: int = 2

    # pairing
    pair_id: Optional[str] = None
    task_id: Optional[str] = None
    task_hash: Optional[str] = None

    # model / determinism
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    seed: Optional[int] = None
    seed_supported: Optional[bool] = None   # S9: None = provider not declared

    # evaluation
    evaluator_name: Optional[str] = None
    evaluator_version: Optional[str] = None
    outcome_threshold: Optional[float] = None          # S11: EFFECTIVE value
    requested_outcome_threshold: Optional[float] = None # what the task asked for
    max_tokens: Optional[int] = None                    # S12: effective budget
    max_tokens_source: Optional[str] = None             # explicit | provider_default

    # write gate
    memory_write_enabled: bool = False

    # environment
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=platform.platform)
    code_git_sha: Optional[str] = field(default_factory=_git_sha)
    code_dirty: Optional[bool] = field(default_factory=_git_dirty)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2, default=str)

    def digest(self) -> str:
        """Content digest, so post-hoc tampering with a manifest is detectable."""
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    def persist(self, directory: str) -> str:
        """
        Writes the manifest to disk. Called BEFORE execution -- a manifest written
        afterwards can be retrofitted to its own result.

        Refuses to overwrite an existing manifest for the same run_id.
        """
        import os

        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"manifest_{self.run_id}.json")
        if os.path.exists(path):
            raise FileExistsError(f"manifest already exists for run {self.run_id}: {path}")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())
        return path

    @classmethod
    def load(cls, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)


class TrustStateStore:
    """
    Run-scoped policy state: memory_id -> PolicyState.

    Lazily seeded from the bank's `initial_trust` on first access, so a fresh run
    always starts from the bank's declared starting point regardless of what any other
    run did.
    """

    def __init__(self, policy: TrustPolicy, bank: MemoryBank, run_id: str):
        self._policy = policy
        self._bank = bank
        self._run_id = run_id
        self._states: Dict[str, PolicyState] = {}

    @property
    def run_id(self) -> str:
        return self._run_id

    def get(self, memory_id: str) -> PolicyState:
        if memory_id not in self._states:
            rec = self._bank.get(memory_id)
            seed = rec.initial_trust if rec is not None else None
            self._states[memory_id] = self._policy.initial_state(memory_id, trust_score=seed)
        return self._states[memory_id]

    def set(self, state: PolicyState) -> None:
        self._states[state.memory_id] = state

    def apply(self, observation: Observation) -> tuple[PolicyState, PolicyState]:
        """Applies one task-level observation. Returns (before, after)."""
        before = self.get(observation.memory_id)
        after = self._policy.update(before, observation)
        self._states[observation.memory_id] = after
        return before, after

    def reset(self) -> None:
        """Drops all accumulated state, returning the run to its initial condition."""
        self._states.clear()

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {mid: st.to_dict() for mid, st in sorted(self._states.items())}

    def observed_ids(self) -> List[str]:
        return sorted(self._states)


class RunContext:
    """Owns all mutable state for exactly one run."""

    def __init__(
        self,
        bank: MemoryBank,
        policy: TrustPolicy,
        run_id: Optional[str] = None,
        condition_id: str = "default",
        memory_write_enabled: bool = False,
        manifest_overrides: Optional[Dict[str, Any]] = None,
        ranker: Optional[Any] = None,
        top_k: int = 2,
        temperature: Optional[float] = None,
        seed: Optional[int] = None,
        provider: Optional[str] = None,
        evaluator_name: Optional[str] = None,
        outcome_threshold: float = DEFAULT_OUTCOME_THRESHOLD,
        max_tokens: Optional[int] = None,
    ):
        self.run_id = run_id or new_run_id()
        self.condition_id = condition_id
        self.bank = bank
        self.policy = policy
        # S6: top_k is an executable run parameter, not manifest-only decoration.
        # execute_task reads it from here, so the manifest always describes what ran.
        self.top_k = int(top_k)
        # S8: same rule for temperature. execute_task reads this attribute and the
        # manifest is populated from it, so there is exactly one source of truth.
        # None means "unspecified -> provider default"; the manifest then records
        # None rather than asserting a number that was not used.
        self.temperature = None if temperature is None else float(temperature)
        # S9: a seed is only accepted when the declared provider honours it. The
        # manifest therefore never records a seed that execution did not apply.
        self.provider = provider
        self.seed = None if seed is None else int(seed)
        if self.seed is not None:
            if provider is None:
                raise ValueError(
                    "a seed requires an explicit provider so its support can be verified"
                )
            validate_seed(ModelProvider(provider), self.seed)
        self.seed_supported = (
            provider_supports_seed(ModelProvider(provider)) if provider else None
        )

        # S11: the manifest must describe the EFFECTIVE binarisation cut-point, which
        # some evaluators fix themselves (pytest_execution pins 1.0). Both this and the
        # execution path resolve it through `effective_outcome_threshold`.
        from ai_service.tools.evaluator import effective_outcome_threshold

        self.evaluator_name = evaluator_name
        self.requested_outcome_threshold = float(outcome_threshold)
        self.outcome_threshold = effective_outcome_threshold(
            evaluator_name, self.requested_outcome_threshold
        )

        # S12: effective token budget. None means "provider default"; resolved here so
        # the manifest states the number actually sent rather than leaving it invisible.
        if max_tokens is not None:
            self.max_tokens = int(max_tokens)
            self.max_tokens_source = "explicit"
        elif provider is not None:
            self.max_tokens = ProviderConfig.default_for(ModelProvider(provider)).max_tokens
            self.max_tokens_source = "provider_default"
        else:
            self.max_tokens = None
            self.max_tokens_source = "provider_not_declared"
        # What the model actually receives: None here means the provider default,
        # which is exactly the number recorded above.
        self._max_tokens_for_execution = max_tokens
        # Fixed-bank experiments MUST NOT mutate the bank. Default is off.
        self.memory_write_enabled = bool(memory_write_enabled)

        # R3: the ranker is an EXPLICIT part of the run, never derived from
        # `memory_mode`. The default is SimilarityOnlyRanker, which applies no trust
        # logic of its own -- so the injected TrustPolicy is the single trust decision
        # boundary. LegacyModeRanker (which additionally consults the pre-existing
        # Beta/quarantine filter) must now be opted into by name.
        if ranker is None:
            from ai_service.experiment.retrieval import SimilarityOnlyRanker

            ranker = SimilarityOnlyRanker()
        self.ranker = ranker

        # Baseline outcome for this run, populated ONLY by an actual E0 execution.
        # Never estimated, inferred, or synthesised.
        self.baseline_reward: Optional[float] = None
        self.baseline_binary: Optional[int] = None

        self.trust_state = TrustStateStore(policy, bank, self.run_id)
        self.exposures = ExposureLog(self.run_id)
        self._task_index = 0

        self.manifest = RunManifest(
            run_id=self.run_id,
            condition_id=condition_id,
            policy_name=policy.name,
            policy_params=dict(policy.params),
            policy_params_hash=params_hash(dict(policy.params)),
            bank_id=bank.bank_id,
            bank_hash=bank.bank_hash,
            bank_size=len(bank),
            memory_write_enabled=self.memory_write_enabled,
            ranker_name=getattr(self.ranker, "name", str(self.ranker)),
            # S6 / S8: recorded from the SAME attributes the executor reads, so the
            # manifest cannot disagree with execution. Caller-supplied overrides for
            # these keys are deliberately discarded.
            **{
                k: v for k, v in (manifest_overrides or {}).items()
                if k not in (
                    "top_k", "temperature", "seed", "seed_supported", "provider",
                    "outcome_threshold", "requested_outcome_threshold",
                    "evaluator_name", "max_tokens", "max_tokens_source",
                )
            },
            top_k=self.top_k,
            temperature=self.temperature,
            seed=self.seed,
            seed_supported=self.seed_supported,
            provider=self.provider,
            evaluator_name=self.evaluator_name,
            outcome_threshold=self.outcome_threshold,
            requested_outcome_threshold=self.requested_outcome_threshold,
            max_tokens=self.max_tokens,
            max_tokens_source=self.max_tokens_source,
        )
        # Captured at construction so bank tampering mid-run is detectable.
        self._bank_hash_at_start = bank.bank_hash

    def set_baseline(self, reward: float, binary_outcome: int) -> None:
        """
        Records an OBSERVED stateless baseline for this run.

        Must only ever be called with the result of an actual E0 execution of the same
        task. There is deliberately no estimator, no default, and no inference path.
        """
        if binary_outcome not in (0, 1):
            raise ValueError(f"binary_outcome must be 0 or 1, got {binary_outcome!r}")
        if not (0.0 <= float(reward) <= 1.0):
            raise ValueError(f"reward must lie in [0,1], got {reward!r}")
        self.baseline_reward = float(reward)
        self.baseline_binary = int(binary_outcome)

    def next_task_index(self) -> int:
        self._task_index += 1
        return self._task_index

    def policy_context(self, domain: Optional[str] = None) -> PolicyContext:
        return PolicyContext(run_id=self.run_id, domain=domain)

    def verify_bank_unchanged(self) -> bool:
        """Fixed-bank guarantee: content hash must be identical to run start."""
        return self.bank.bank_hash == self._bank_hash_at_start

    def reset(self) -> None:
        """Full reset: policy state, evidence, and task counter."""
        self.trust_state.reset()
        self.exposures = ExposureLog(self.run_id)
        self._task_index = 0

    def summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "condition_id": self.condition_id,
            "policy": self.policy.describe(),
            "bank_hash": self.bank.bank_hash,
            "bank_unchanged": self.verify_bank_unchanged(),
            "memory_write_enabled": self.memory_write_enabled,
            "n_exposures": len(self.exposures),
            "n_tasks": self._task_index,
            "trust_state": self.trust_state.snapshot(),
        }
