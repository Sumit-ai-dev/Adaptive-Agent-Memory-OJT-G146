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
    OFF = "off"                           # Condition 1: Baseline / Vanilla ReAct (no memory)
    NAIVE = "naive"                       # Condition 2: Naive Vector RAG (pure cosine, no trust)
    RECENCY = "recency"                   # Condition 3: Recency-Based Retrieval (time decay heuristic)
    TRUST_NO_QUARANTINE = "trust_no_quarantine" # Condition 4: Trust Scoring without Quarantine Cutoff
    SYMMETRIC = "symmetric"               # Legacy alias for Condition 4
    ADAPTIVE = "adaptive"                 # Condition 5: Full AEMA (Bayesian LCB + Theorem 1 Quarantine)


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
