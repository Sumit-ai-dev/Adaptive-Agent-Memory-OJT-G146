"""
Task execution request and response models for Adaptive Agent Memory System.
Handles BYOK credentials, multi-mode memory execution, and outcome payloads.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from models.domain import TaskDomain
from models.experience import ExperienceMatch


class MemoryMode(str, Enum):
    """Memory operational modes for benchmark ablation."""
    OFF = "off"
    NAIVE = "naive"
    ADAPTIVE = "adaptive"


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


class TrustUpdate(BaseModel):
    """Summary of a trust score adjustment applied during task execution."""
    model_config = ConfigDict(populate_by_name=True)

    experience_id: str = Field(..., alias="experienceId")
    old_score: float = Field(..., alias="oldScore")
    new_score: float = Field(..., alias="newScore")
    delta: float = Field(...)
    reason: Optional[str] = Field(default=None)


class TaskExecuteRequest(BaseModel):
    """Incoming request to execute an agent task."""
    model_config = ConfigDict(populate_by_name=True)

    task_input: str = Field(..., min_length=1, description="The user prompt or task specification", alias="taskInput")
    domain: TaskDomain = Field(default=TaskDomain.GENERAL, description="Problem domain")
    memory_enabled: bool = Field(default=True, alias="memoryEnabled")
    memory_mode: MemoryMode = Field(default=MemoryMode.ADAPTIVE, alias="memoryMode")
    provider: str = Field(default="groq", description="Model provider (groq, gemini, ollama, openai, anthropic)")
    model: str = Field(default="llama-3.3-70b-versatile", description="Model identifier")
    api_key: Optional[str] = Field(default=None, description="Optional BYOK API key for this execution", alias="apiKey")


class TaskExecuteResponse(BaseModel):
    """Execution result and telemetry payload."""
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(default_factory=lambda: str(uuid4()), alias="taskId")
    status: ExecutionStatus = Field(default=ExecutionStatus.COMPLETED)
    task_input: str = Field(..., alias="taskInput")
    task_domain: TaskDomain = Field(default=TaskDomain.GENERAL, alias="taskDomain")
    final_output: Optional[str] = Field(default=None, alias="finalOutput")
    retrieved_experiences: list[ExperienceMatch] = Field(default_factory=list, alias="retrievedExperiences")
    reflection_lesson: Optional[str] = Field(default=None, alias="reflectionLesson")
    new_experience_created: bool = Field(default=False, alias="newExperienceCreated")
    trust_updates: list[TrustUpdate] = Field(default_factory=list, alias="trustUpdates")
    tokens_used: int = Field(default=0, alias="tokensUsed")
    latency_ms: int = Field(default=0, alias="latencyMs")
    outcome_quality: Optional[OutcomeQuality] = Field(default=None, alias="outcomeQuality")
    outcome_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, alias="outcomeScore")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
