"""
Domain and Status Enums for Adaptive Agent Memory System.
Strictly aligned with infrastructure/supabase/schema.sql and frontend/src/types/index.ts.
"""

from enum import Enum
from typing import List


class TaskDomain(str, Enum):
    """Supported task domains matching infrastructure/supabase/schema.sql."""
    RESEARCH = "research"
    CODING = "coding"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    GENERAL = "general"

    @classmethod
    def list(cls) -> List[str]:
        return [c.value for c in cls]


class ExperienceStatus(str, Enum):
    """Lifecycle status of a memory experience."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    CANDIDATE = "candidate"


class MemoryMode(str, Enum):
    """Memory operational modes for benchmark ablation."""
    OFF = "off"              # Condition A: Baseline / Vanilla ReAct (no memory)
    NAIVE = "naive"          # Condition B: Naive Vector RAG (pure cosine, no trust)
    SYMMETRIC = "symmetric"  # Condition C: Symmetric Reflexion (alpha = beta = 0.80)
    ADAPTIVE = "adaptive"    # Condition D: Asymmetric EMA + Quarantine Cutoff (OURS)


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
