"""
Domain definitions for Adaptive Agent Memory System.
Defines task domains recognized by the agent and database schema.
"""

from enum import Enum


class TaskDomain(str, Enum):
    """Supported task domains matching infrastructure/supabase/schema.sql."""
    RESEARCH = "research"
    CODING = "coding"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    GENERAL = "general"

    @classmethod
    def list(cls) -> list[str]:
        return [c.value for c in cls]
