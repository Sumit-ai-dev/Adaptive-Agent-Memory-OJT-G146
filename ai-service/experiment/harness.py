"""
Paired experimental harness (Step 1.5).

Executes the SAME task under two conditions that differ only in the memory condition:

    E0 -- stateless: memory disabled, nothing injected, no trust state touched
    E1 -- memory:    fixed bank, similarity retrieval, exactly ONE injected TrustPolicy

Everything else -- task text, evaluator, evaluator config, outcome threshold, model,
provider, temperature -- is held fixed and recorded.

This module is a MEASUREMENT INSTRUMENT. It defines no benchmark, no memory bank
contents, no trust mechanism, and no research metric. The paired difference between
conditions is recorded as an OBSERVED quantity under a deliberately neutral name; it
is not called a causal effect, treatment effect, lift, or benefit, because the
assumptions required to license that language have not been reviewed.

Execution order within a pair is E0 first, so that E1's exposure records can carry an
OBSERVED stateless baseline at write time. If E1 runs first the baseline fields stay
None -- they are never estimated, inferred, or synthesised.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ai_service.experiment.evidence import ExposureRecord
from ai_service.experiment.memory_bank import MemoryBank
from ai_service.experiment.retrieval import SimilarityOnlyRanker
from ai_service.experiment.run_context import RunContext, new_run_id, params_hash
from ai_service.trust.base import TrustPolicy
from models.domain import MemoryMode, TaskDomain
from models.task import DEFAULT_OUTCOME_THRESHOLD, EvaluatorName, TaskExecuteRequest

E0_CONDITION_ID = "E0"
E1_CONDITION_ID = "E1"


def new_pair_id() -> str:
    import uuid

    return f"pair_{uuid.uuid4().hex[:12]}"


# ======================================================================
# Frozen specifications
# ======================================================================

@dataclass(frozen=True)
class TaskSpec:
    """
    A frozen task. `task_hash` covers everything that defines the task, so two
    conditions can be proved to have executed the identical specification.
    """
    task_id: str
    prompt: str
    domain: TaskDomain = TaskDomain.GENERAL
    evaluator: EvaluatorName = EvaluatorName.HEURISTIC
    evaluator_config: Mapping[str, Any] = field(default_factory=dict)
    outcome_threshold: float = DEFAULT_OUTCOME_THRESHOLD

    @property
    def task_hash(self) -> str:
        payload = json.dumps(
            {
                "task_id": self.task_id,
                "prompt": self.prompt,
                "domain": self.domain.value if hasattr(self.domain, "value") else str(self.domain),
                "evaluator": self.evaluator.value,
                "evaluator_config": dict(self.evaluator_config),
                "outcome_threshold": self.outcome_threshold,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelSpec:
    """Model configuration held fixed across both conditions."""
    provider: str = "mock"
    model: str = "mock-deterministic-v1"
    model_version: str = "mock-1"
    temperature: float = 0.0
    seed: Optional[int] = None
    # S12: None keeps the existing provider default (2048); the run records
    # the effective number either way.
    max_tokens: Optional[int] = None

    def __post_init__(self) -> None:
        # S9: fail at configuration time, not silently at record time.
        from models.provider import ModelProvider, validate_seed

        if self.seed is not None:
            validate_seed(ModelProvider(self.provider), self.seed)

    @property
    def seed_supported(self) -> bool:
        from models.provider import ModelProvider, provider_supports_seed

        return provider_supports_seed(ModelProvider(self.provider))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConditionSpec:
    """
    Declares one experimental condition.

    Every component that can influence admission is named here. Nothing is inferred
    from `memory_mode`, which is what allowed the legacy Beta/quarantine filter to be
    applied silently alongside the injected policy (R3).
    """
    condition_id: str
    memory_enabled: bool
    policy: Optional[TrustPolicy] = None
    ranker: Optional[Any] = None
    top_k: int = 2
    memory_write_enabled: bool = False

    def __post_init__(self) -> None:
        if self.memory_enabled:
            if self.policy is None:
                raise ValueError(f"condition {self.condition_id}: memory_enabled requires a policy")
            if self.ranker is None:
                self.ranker = SimilarityOnlyRanker()
        if self.memory_write_enabled:
            raise ValueError(
                f"condition {self.condition_id}: memory_write_enabled must be False "
                "for fixed-bank experiments"
            )

    def describe(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "memory_enabled": self.memory_enabled,
            "policy_name": self.policy.name if self.policy else None,
            "policy_params": dict(self.policy.params) if self.policy else {},
            "policy_params_hash": params_hash(dict(self.policy.params)) if self.policy else "",
            "ranker_name": getattr(self.ranker, "name", None),
            "top_k": self.top_k,
            "memory_write_enabled": self.memory_write_enabled,
        }


def make_e0(condition_id: str = E0_CONDITION_ID) -> ConditionSpec:
    """Stateless condition. No policy, no ranker, no memory."""
    return ConditionSpec(condition_id=condition_id, memory_enabled=False)


def make_e1(
    policy: TrustPolicy,
    ranker: Optional[Any] = None,
    top_k: int = 2,
    condition_id: str = E1_CONDITION_ID,
) -> ConditionSpec:
    """
    Memory condition. Defaults to SimilarityOnlyRanker so that the injected policy is
    the ONLY trust decision boundary (R3).
    """
    return ConditionSpec(
        condition_id=condition_id,
        memory_enabled=True,
        policy=policy,
        ranker=ranker or SimilarityOnlyRanker(),
        top_k=top_k,
    )


# ======================================================================
# Results
# ======================================================================

@dataclass
class ConditionResult:
    """Immutable-by-convention record of one task executed under one condition."""
    pair_id: str
    condition_id: str
    run_id: str
    task_id: str
    task_hash: str

    terminal_reward: float
    binary_outcome: int
    outcome_threshold: float
    evaluator_name: Optional[str]
    evaluator_version: Optional[str]

    model: str
    model_version: str
    provider: str
    temperature: float

    memory_enabled: bool
    memory_ids_exposed: List[str] = field(default_factory=list)

    n_attempts: int = 0
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    policy_name: Optional[str] = None
    policy_params_hash: Optional[str] = None
    ranker_name: Optional[str] = None

    bank_hash_before: Optional[str] = None
    bank_hash_after: Optional[str] = None
    code_git_sha: Optional[str] = None

    manifest_path: Optional[str] = None
    manifest_digest_before: Optional[str] = None
    manifest_digest_after: Optional[str] = None

    exposures: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def bank_unchanged(self) -> bool:
        return self.bank_hash_before == self.bank_hash_after

    @property
    def manifest_unchanged(self) -> bool:
        return self.manifest_digest_before == self.manifest_digest_after

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["bank_unchanged"] = self.bank_unchanged
        d["manifest_unchanged"] = self.manifest_unchanged
        return d


@dataclass
class PairedObservation:
    """
    Two condition results linked by `pair_id` over an identical task specification.

    NOTE ON ANALYSIS: E0 and E1 here are repeated measures on the SAME task. They are
    NOT independent observations. Any later analysis must respect the pairing.
    """
    pair_id: str
    task_id: str
    task_hash: str
    e0: Optional[ConditionResult] = None
    e1: Optional[ConditionResult] = None

    @property
    def complete(self) -> bool:
        return self.e0 is not None and self.e1 is not None

    @property
    def task_specification_identical(self) -> bool:
        if not self.complete:
            return False
        return self.e0.task_hash == self.e1.task_hash == self.task_hash

    def observed_paired_difference(self) -> Optional[Dict[str, float]]:
        """
        The raw arithmetic difference between the two observed outcomes.

        Deliberately NOT named a causal effect, treatment effect, lift, or benefit.
        It is a recorded observation on one task under two conditions. Whether it
        licenses any causal reading depends on assumptions that have not yet been
        reviewed, so no such claim is encoded here.

        Returns None unless both conditions actually executed -- there is no
        imputation path.
        """
        if not self.complete:
            return None
        return {
            "reward_difference": self.e1.terminal_reward - self.e0.terminal_reward,
            "binary_difference": float(self.e1.binary_outcome - self.e0.binary_outcome),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "task_id": self.task_id,
            "task_hash": self.task_hash,
            "complete": self.complete,
            "task_specification_identical": self.task_specification_identical,
            "e0": self.e0.to_dict() if self.e0 else None,
            "e1": self.e1.to_dict() if self.e1 else None,
            "observed_paired_difference": self.observed_paired_difference(),
        }


# ======================================================================
# Harness
# ======================================================================

class ExperimentHarness:
    """
    Orchestrates: create manifest -> persist manifest -> execute -> append evidence.

    Each condition gets a brand-new RunContext, so no trust state, exposure record,
    retrieved memory, or attempt can cross between conditions or tasks.
    """

    def __init__(
        self,
        bank: MemoryBank,
        model_spec: Optional[ModelSpec] = None,
        output_dir: Optional[str] = None,
    ):
        self.bank = bank
        self.model_spec = model_spec or ModelSpec()
        self.output_dir = output_dir
        self._results: List[PairedObservation] = []

    # -- internals ----------------------------------------------------

    def _build_request(self, task: TaskSpec, condition: ConditionSpec) -> TaskExecuteRequest:
        """Identical for both conditions except the memory flags."""
        return TaskExecuteRequest(
            task_input=task.prompt,
            task_domain=task.domain,
            memory_enabled=condition.memory_enabled,
            memory_mode=MemoryMode.ADAPTIVE if condition.memory_enabled else MemoryMode.OFF,
            provider=self.model_spec.provider,
            model=self.model_spec.model,
            evaluator=task.evaluator,
            evaluator_config=dict(task.evaluator_config),
            outcome_threshold=task.outcome_threshold,
            temperature=self.model_spec.temperature,
            seed=self.model_spec.seed,
            max_tokens=self.model_spec.max_tokens,
        )

    def _build_run(
        self, task: TaskSpec, condition: ConditionSpec, pair_id: str,
    ) -> RunContext:
        from ai_service.trust.aema import StaticTrustPolicy

        # E0 still needs a policy object to construct a RunContext, but with
        # memory_enabled=False retrieval never runs, so it is never consulted.
        policy = condition.policy or StaticTrustPolicy()
        return RunContext(
            bank=self.bank,
            policy=policy,
            condition_id=condition.condition_id,
            memory_write_enabled=False,
            ranker=condition.ranker,
            # S6 / S8: handed to the run as EXECUTABLE values, not manifest decoration.
            top_k=condition.top_k,
            temperature=self.model_spec.temperature,
            seed=self.model_spec.seed,
            provider=self.model_spec.provider,
            # S11 / S12: executable values, not manifest decoration.
            evaluator_name=task.evaluator.value,
            outcome_threshold=task.outcome_threshold,
            max_tokens=self.model_spec.max_tokens,
            manifest_overrides={
                "pair_id": pair_id,
                "task_id": task.task_id,
                "task_hash": task.task_hash,
                "memory_mode": "adaptive" if condition.memory_enabled else "off",
                "model": self.model_spec.model,
                "similarity_threshold": getattr(condition.ranker, "similarity_threshold", None),
            },
        )

    # -- public API ---------------------------------------------------

    async def run_condition(
        self,
        task: TaskSpec,
        condition: ConditionSpec,
        pair_id: Optional[str] = None,
        baseline: Optional[ConditionResult] = None,
    ) -> ConditionResult:
        """
        Executes one task under one condition.

        `baseline`, when supplied, must be an ACTUAL E0 result for the same task. It is
        written into the exposure records at creation time; nothing is back-filled.
        """
        from ai_service.graph import execute_task

        pair_id = pair_id or new_pair_id()
        run = self._build_run(task, condition, pair_id)

        if baseline is not None:
            if baseline.task_hash != task.task_hash:
                raise ValueError(
                    "baseline task_hash does not match the task being executed; "
                    "a baseline may only come from an E0 run of the SAME task"
                )
            run.set_baseline(baseline.terminal_reward, baseline.binary_outcome)

        # 1. manifest BEFORE execution
        manifest_path = None
        if self.output_dir:
            manifest_path = run.manifest.persist(self.output_dir)
        digest_before = run.manifest.digest()

        bank_hash_before = self.bank.bank_hash

        # 2. execute
        execution = await execute_task(self._build_request(task, condition), run_context=run)

        # 3. collect
        bank_hash_after = self.bank.bank_hash
        exposures: List[ExposureRecord] = run.exposures.records
        memory_ids = sorted({r.memory_id for r in exposures if r.memory_id})

        result = ConditionResult(
            pair_id=pair_id,
            condition_id=condition.condition_id,
            run_id=run.run_id,
            task_id=task.task_id,
            task_hash=task.task_hash,
            terminal_reward=float(execution.outcome_score or 0.0),
            binary_outcome=int(execution.binary_outcome or 0),
            outcome_threshold=float(execution.outcome_threshold or task.outcome_threshold),
            evaluator_name=execution.evaluator_name.value if execution.evaluator_name else None,
            evaluator_version=execution.evaluator_version,
            model=self.model_spec.model,
            model_version=self.model_spec.model_version,
            provider=self.model_spec.provider,
            temperature=self.model_spec.temperature,
            memory_enabled=condition.memory_enabled,
            memory_ids_exposed=memory_ids,
            n_attempts=execution.n_attempts,
            attempts=[a.model_dump() for a in execution.attempts],
            policy_name=condition.policy.name if condition.policy else None,
            policy_params_hash=(
                params_hash(dict(condition.policy.params)) if condition.policy else None
            ),
            ranker_name=getattr(condition.ranker, "name", None),
            bank_hash_before=bank_hash_before,
            bank_hash_after=bank_hash_after,
            code_git_sha=run.manifest.code_git_sha,
            manifest_path=manifest_path,
            manifest_digest_before=digest_before,
            manifest_digest_after=run.manifest.digest(),
            exposures=[r.to_dict() for r in exposures],
        )

        if not result.bank_unchanged:
            raise RuntimeError(
                f"fixed-bank integrity violated during run {run.run_id}: "
                f"{bank_hash_before} -> {bank_hash_after}"
            )
        return result

    async def run_pair(
        self,
        task: TaskSpec,
        e1_policy: TrustPolicy,
        e1_ranker: Optional[Any] = None,
        top_k: int = 2,
        pair_id: Optional[str] = None,
    ) -> PairedObservation:
        """
        Runs the same task under E0 then E1, linked by `pair_id`.

        E0 runs first so that E1's records can carry the OBSERVED stateless baseline.
        """
        pair_id = pair_id or new_pair_id()

        e0_result = await self.run_condition(task, make_e0(), pair_id=pair_id)
        e1_result = await self.run_condition(
            task,
            make_e1(policy=e1_policy, ranker=e1_ranker, top_k=top_k),
            pair_id=pair_id,
            baseline=e0_result,
        )

        obs = PairedObservation(
            pair_id=pair_id, task_id=task.task_id, task_hash=task.task_hash,
            e0=e0_result, e1=e1_result,
        )
        self._results.append(obs)
        return obs

    @property
    def results(self) -> List[PairedObservation]:
        return list(self._results)

    def write_results(self, path: str) -> None:
        """Append-only JSONL dump of paired observations."""
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for obs in self._results:
                fh.write(json.dumps(obs.to_dict(), sort_keys=True, default=str) + "\n")
