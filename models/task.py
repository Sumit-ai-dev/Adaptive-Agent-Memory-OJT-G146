"""
Task execution request and response models for Adaptive Agent Memory System.
Handles BYOK credentials, multi-mode memory execution, telemetry step traces, and outcome payloads.
"""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.domain import MemoryMode, TaskDomain
from models.experience import Experience, ExperienceMatch


def to_camel(string: str) -> str:
    """Converts snake_case field names to camelCase for API/JSON serialization."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionStatus(str, Enum):
    """Execution status lifecycle."""
    PENDING = "pending"
    RETRIEVING = "retrieving"
    REASONING = "reasoning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


class OutcomeQuality(str, Enum):
    """Evaluated task outcome category."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class EvaluatorName(str, Enum):
    """
    F2: Explicit, task-level evaluator selection.

    The evaluator is declared by the task. It is NEVER inferred from `task_domain` --
    `task_domain == "coding"` previously forced every programming task through the
    tool-call validator, which scored it on incidental JSON content rather than on
    whether the code was correct.
    """
    PYTEST_EXECUTION = "pytest_execution"   # run candidate code against a frozen test suite
    EXACT_MATCH_F1 = "exact_match_f1"       # QA: EM / token-F1 against a ground-truth string
    STRICT_KEY_ANSWER = "strict_key_answer" # Controlled Phase 3: deterministic structured key-answer semantics
    TOOLBENCH_TRAP = "toolbench_trap"       # tool-use: deprecated-param / trap detection
    HEURISTIC = "heuristic"                 # smoke-test only -- NOT valid for research conditions


#: Evaluators that may be used to produce research evidence. `HEURISTIC` is excluded
#: deliberately: it scores answer length and token overlap, not correctness.
RESEARCH_GRADE_EVALUATORS = frozenset({
    EvaluatorName.PYTEST_EXECUTION,
    EvaluatorName.EXACT_MATCH_F1,
    EvaluatorName.STRICT_KEY_ANSWER,
    EvaluatorName.TOOLBENCH_TRAP,
})

#: F3: default binarisation cut-point. Recorded explicitly on every outcome so that
#: `binary_outcome` is always recomputable from `reward` and is never implicit.
DEFAULT_OUTCOME_THRESHOLD: float = 0.80


class EvaluationOutcome(BaseModel):
    """
    F3 -- THE FROZEN OUTCOME CONTRACT.

    The evaluator is the single authority on whether a task succeeded. A trust policy
    CONSUMES this outcome; it must never re-derive success/failure from its own internal
    state (the previous `delta >= 0` rule made "success" mean "the reward exceeded the
    memory's own current trust score", which is self-referential and mechanism-coupled).

    Invariants:
      * `reward` is always retained, even when `binary_outcome` is the value consumed.
      * `binary_outcome == int(reward >= outcome_threshold)`, always recomputable.
      * Exactly one of these is produced per task-level memory exposure.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reward: float = Field(..., ge=0.0, le=1.0, description="Continuous reward R in [0,1]; never discarded")
    binary_outcome: int = Field(..., ge=0, le=1, description="1 = success, 0 = failure")
    outcome_threshold: float = Field(default=DEFAULT_OUTCOME_THRESHOLD, ge=0.0, le=1.0)
    evaluator_name: EvaluatorName = Field(...)
    evaluator_version: str = Field(default="1.0")
    reason: str = Field(default="")
    details: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_binarisation(self) -> "EvaluationOutcome":
        expected = 1 if self.reward >= self.outcome_threshold else 0
        if self.binary_outcome != expected:
            raise ValueError(
                f"binary_outcome={self.binary_outcome} contradicts "
                f"reward={self.reward} at threshold={self.outcome_threshold}"
            )
        return self

    @classmethod
    def from_reward(
        cls,
        reward: float,
        evaluator_name: "EvaluatorName",
        reason: str = "",
        outcome_threshold: float = DEFAULT_OUTCOME_THRESHOLD,
        evaluator_version: str = "1.0",
        details: Optional[Dict[str, Any]] = None,
    ) -> "EvaluationOutcome":
        """Single construction path -- guarantees the binarisation invariant holds."""
        bounded = max(0.0, min(1.0, float(reward)))
        return cls(
            reward=bounded,
            binary_outcome=1 if bounded >= outcome_threshold else 0,
            outcome_threshold=outcome_threshold,
            evaluator_name=evaluator_name,
            evaluator_version=evaluator_version,
            reason=reason,
            details=details or {},
        )


class AttemptRecord(BaseModel):
    """
    F1: one record per ATTEMPT (retry iteration) inside a single task.

    A retry is an attempt, not an independent learning observation. Attempts are kept
    for diagnostics (cost, convergence); only the TERMINAL attempt supplies the
    task-level outcome that reaches the memory's evidence counters.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    attempt_index: int = Field(..., ge=1, description="1-based position within the task")
    reward: float = Field(..., ge=0.0, le=1.0)
    binary_outcome: int = Field(..., ge=0, le=1)
    outcome_threshold: float = Field(default=DEFAULT_OUTCOME_THRESHOLD)
    evaluator_name: Optional[EvaluatorName] = Field(default=None)
    reason: str = Field(default="")
    tokens_used: int = Field(default=0)
    is_terminal: bool = Field(default=False, description="True for the attempt that defines the task outcome")


class TrustUpdate(BaseModel):
    """Summary of a trust score adjustment applied during task execution."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    experience_id: str = Field(..., alias="experienceId")
    old_score: float = Field(..., alias="oldScore")
    new_score: float = Field(..., alias="newScore")
    delta: float = Field(...)
    reason: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)


TrustUpdateSummary = TrustUpdate


class ExecutionStepTrace(BaseModel):
    """Granular trace event for the React stepper UI and observability."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(default_factory=lambda: f"step_{int(datetime.now().timestamp()*1000)}")
    type: str = Field(default="thought")  # "thought" | "retrieval" | "action" | "observation" | "reflection"
    node: Optional[str] = None
    title: str
    detail: str
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    tools_called: Optional[List[str]] = Field(default=None, alias="toolsCalled")
    metadata: Optional[Dict[str, Any]] = None


class TaskExecuteRequest(BaseModel):
    """Incoming request to execute an agent task."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    task_input: str = Field(..., min_length=1, description="The user prompt or task specification", alias="taskInput")
    task_domain: TaskDomain = Field(default=TaskDomain.GENERAL, alias="taskDomain")
    domain_alias: Optional[TaskDomain] = Field(default=None, alias="domain")
    memory_enabled: bool = Field(default=True, alias="memoryEnabled")
    memory_mode: MemoryMode = Field(default=MemoryMode.ADAPTIVE, alias="memoryMode")
    provider: Optional[str] = Field(default="groq", description="Model provider")
    model: Optional[str] = Field(default="llama-3.3-70b-versatile", description="Model identifier")
    api_key: Optional[str] = Field(default=None, description="Optional BYOK API key", alias="apiKey")
    # S8: sampling temperature actually handed to the provider. None => the provider's
    # own default applies (ProviderConfig.temperature). Recorded manifests must report
    # whatever value is effective here, never an independent second value.
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    # S9: rejected at execution time if the provider cannot honour it.
    seed: Optional[int] = Field(default=None)
    # S12: None => the provider default applies and is recorded as such.
    max_tokens: Optional[int] = Field(default=None, ge=64, le=16384)

    # F2: explicit, task-level evaluator selection. When None, the evaluator is inferred
    # from directives embedded in `task_input` (ground-truth tag / validation-criteria tag)
    # and otherwise falls back to HEURISTIC. `task_domain` plays no part in the decision.
    evaluator: Optional[EvaluatorName] = Field(default=None, alias="evaluator")
    evaluator_config: Dict[str, Any] = Field(
        default_factory=dict,
        alias="evaluatorConfig",
        description="Evaluator payload, e.g. {'test_code': ..., 'timeout_s': 10} for pytest_execution",
    )
    outcome_threshold: float = Field(
        default=DEFAULT_OUTCOME_THRESHOLD,
        ge=0.0,
        le=1.0,
        alias="outcomeThreshold",
        description="F3: explicit binarisation cut-point, recorded on every outcome",
    )

    @model_validator(mode="before")
    @classmethod
    def check_domain_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "domain" in data and "task_domain" not in data and "taskDomain" not in data:
                data["task_domain"] = data["domain"]
        return data

    @property
    def domain(self) -> TaskDomain:
        return self.task_domain


class ExecutionMetadata(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    latency_ms: int = 0
    steps_count: int = 0
    tool_calls_count: int = 0
    outcome_score: float = 0.0
    tokens_used: int = 0
    loop_count: int = 1


class TaskExecution(BaseModel):
    """Comprehensive Task Execution Record for persistence and frontend dashboard consumption."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:8]}")
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    user_id: Optional[str] = None
    task_input: str = Field(..., alias="taskInput")
    task_domain: TaskDomain = Field(default=TaskDomain.GENERAL, alias="taskDomain")
    memory_enabled: bool = Field(default=True, alias="memoryEnabled")
    memory_mode: MemoryMode = Field(default=MemoryMode.ADAPTIVE, alias="memoryMode")
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    final_output: Optional[str] = Field(default=None, alias="finalOutput")
    final_answer: Optional[str] = Field(default=None, alias="finalAnswer")
    reflection_lesson: Optional[str] = Field(default=None, alias="reflectionLesson")
    new_experience_created: bool = Field(default=False, alias="newExperienceCreated")
    new_experience: Optional[Experience] = None
    retrieved_experiences: List[ExperienceMatch] = Field(default_factory=list, alias="retrievedExperiences")
    retrieved_memories: List[Dict[str, Any]] = Field(default_factory=list)
    trust_updates: List[TrustUpdate] = Field(default_factory=list, alias="trustUpdates")
    trajectory: List[ExecutionStepTrace] = Field(default_factory=list)
    tokens_used: int = Field(default=0, alias="tokensUsed")
    latency_ms: int = Field(default=0, alias="latencyMs")
    outcome_quality: Optional[OutcomeQuality] = Field(default=OutcomeQuality.POSITIVE, alias="outcomeQuality")
    outcome_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, alias="outcomeScore")

    # --- F3: the frozen outcome contract, at TASK level ---
    # `outcome_score` is retained unchanged as the continuous reward; these carry the
    # binarisation alongside it so the continuous signal is never lost.
    binary_outcome: Optional[int] = Field(default=None, ge=0, le=1, alias="binaryOutcome")
    outcome_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, alias="outcomeThreshold")
    evaluator_name: Optional[EvaluatorName] = Field(default=None, alias="evaluatorName")
    evaluator_version: Optional[str] = Field(default=None, alias="evaluatorVersion")

    # --- F1: attempt-level diagnostics, kept separate from the task-level outcome ---
    attempts: List[AttemptRecord] = Field(default_factory=list)
    n_attempts: int = Field(default=0, alias="nAttempts")
    execution_metadata: Optional[ExecutionMetadata] = None
    created_at: Union[datetime, str] = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")

    def model_post_init(self, __context: Any) -> None:
        if not self.execution_id:
            self.execution_id = self.id
        if not self.task_id:
            self.task_id = f"task_{self.id[5:]}" if self.id.startswith("exec_") else self.id
        if not self.final_answer and self.final_output:
            self.final_answer = self.final_output
        if not self.final_output and self.final_answer:
            self.final_output = self.final_answer


TaskExecuteResponse = TaskExecution


class AgentMetricSummary(BaseModel):
    """High-level aggregate KPIs for the React dashboard."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total_tasks: int = 0
    active_memories: int = 0
    memory_hit_rate: float = 0.0
    sla_adherence: float = 99.9
    avg_time_saved_min: float = 4.2
    tokens_saved: str = "2.4M"
    memory_reuse_rate: float = 76.0
    ai_deflection_rate: float = 80.0
    mttr_min: float = 6.0
