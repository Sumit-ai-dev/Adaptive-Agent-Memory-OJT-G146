"""
AEMA — Adaptive Experience Memory Agent.
Reliability-aware experiential memory for autonomous AI agents.
"""

__version__ = "0.1.1"


def get_memory_store(*args, **kwargs):
    """Convenience factory to obtain the active AEMA memory store (SQLite or Postgres)."""
    from ai_service.memory.store import get_memory_store as _gms
    return _gms(*args, **kwargs)


async def execute_task(*args, **kwargs):
    """Convenience async entrypoint to execute a task through AEMA's 5-node LangGraph."""
    from ai_service.graph import execute_task as _et
    return await _et(*args, **kwargs)


def __getattr__(name: str):
    """Lazy-load core Pydantic schemas so `import aema` stays lightweight."""
    if name in ("Experience", "ExperienceMatch", "TrustHistoryRecord"):
        import models.experience as _exp
        return getattr(_exp, name)
    if name in ("TaskDomain", "ExperienceStatus", "MemoryMode"):
        import models.domain as _dom
        return getattr(_dom, name)
    if name in ("TaskExecuteRequest", "TaskExecution"):
        import models.task as _task
        return getattr(_task, name)
    raise AttributeError(f"module 'aema' has no attribute {name!r}")


__all__ = [
    "__version__",
    "get_memory_store",
    "execute_task",
    "Experience",
    "ExperienceMatch",
    "TrustHistoryRecord",
    "TaskDomain",
    "ExperienceStatus",
    "MemoryMode",
    "TaskExecuteRequest",
    "TaskExecution",
]
