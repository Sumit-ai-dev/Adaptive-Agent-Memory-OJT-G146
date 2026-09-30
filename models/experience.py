"""
Experience and Trust Memory Models for Adaptive Agent Memory System.
Corresponds to public.experiences and public.trust_history in Supabase.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from models.domain import TaskDomain


class ExperienceStatus(str, Enum):
    """Lifecycle status of a memory experience."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    CANDIDATE = "candidate"


class Experience(BaseModel):
    """
    7-tuple Experience Memory representation:
    {Domain, Trigger, Strategy, Pitfall, TrajectoryLength, TrustScore, Embedding}
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = Field(default=None, alias="userId")
    task_domain: TaskDomain = Field(default=TaskDomain.GENERAL, alias="taskDomain")
    trigger_condition: str = Field(..., description="Condition/prompt pattern that activates this lesson", alias="triggerCondition")
    strategy_lesson: str = Field(..., description="Affirmative actionable strategy that succeeded", alias="strategyLesson")
    pitfall: Optional[str] = Field(default=None, description="Critical negative constraint to avoid")
    confidence: float = Field(default=0.850, ge=0.0, le=1.0)
    trust_score: float = Field(default=0.750, ge=0.0, le=1.0, alias="trustScore")
    uses_count: int = Field(default=0, ge=0, alias="usesCount")
    successes_count: int = Field(default=0, ge=0, alias="successesCount")
    failures_count: int = Field(default=0, ge=0, alias="failuresCount")
    status: ExperienceStatus = Field(default=ExperienceStatus.ACTIVE)
    embedding: Optional[list[float]] = Field(default=None, description="384-dimensional vector embedding")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt")


class ExperienceMatch(BaseModel):
    """Result of composite memory retrieval."""
    model_config = ConfigDict(populate_by_name=True)

    experience: Experience
    similarity: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score")
    composite_score: float = Field(..., ge=0.0, le=1.0, description="0.70 * Sim + 0.30 * Trust", alias="compositeScore")


class TrustHistoryRecord(BaseModel):
    """Immutable audit trail entry for a trust score update."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    experience_id: str = Field(..., alias="experienceId")
    execution_id: Optional[str] = Field(default=None, alias="executionId")
    old_trust: float = Field(..., ge=0.0, le=1.0, alias="oldTrust")
    new_trust: float = Field(..., ge=0.0, le=1.0, alias="newTrust")
    delta: float = Field(...)
    reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
