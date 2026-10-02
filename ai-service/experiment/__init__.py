"""
Experiment infrastructure: immutable memory content, run-scoped evidence and trust
state, and legitimate offline replay.

No module-level singletons. Every run must be constructed explicitly.
"""

from ai_service.experiment.evidence import AttemptEvidence, ExposureLog, ExposureRecord
from ai_service.experiment.harness import (
    E0_CONDITION_ID,
    E1_CONDITION_ID,
    ConditionResult,
    ConditionSpec,
    ExperimentHarness,
    ModelSpec,
    PairedObservation,
    TaskSpec,
    make_e0,
    make_e1,
    new_pair_id,
)
from ai_service.experiment.memory_bank import MemoryBank, MemoryRecord
from ai_service.experiment.replay import (
    ReplayResult,
    ReplayStep,
    compare_policies,
    replay_log,
    replay_observations,
)
from ai_service.experiment.retrieval import (
    LegacyModeRanker,
    PolicyBackedRetriever,
    SimilarityOnlyRanker,
)
from ai_service.experiment.run_context import (
    RunContext,
    RunManifest,
    TrustStateStore,
    new_run_id,
    params_hash,
)

__all__ = [
    "MemoryRecord", "MemoryBank",
    "ExposureRecord", "ExposureLog", "AttemptEvidence",
    "RunContext", "RunManifest", "TrustStateStore", "new_run_id", "params_hash",
    "PolicyBackedRetriever", "LegacyModeRanker", "SimilarityOnlyRanker",
    "replay_log", "replay_observations", "compare_policies", "ReplayResult", "ReplayStep",
    "ExperimentHarness", "TaskSpec", "ConditionSpec", "ModelSpec",
    "ConditionResult", "PairedObservation",
    "make_e0", "make_e1", "new_pair_id", "E0_CONDITION_ID", "E1_CONDITION_ID",
]
