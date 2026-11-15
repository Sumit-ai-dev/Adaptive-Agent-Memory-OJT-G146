"""
AEMA — Adaptive Experience Memory Agent.
Reliability-aware experiential memory for autonomous AI agents.
"""

from aema._compat import import_pkg
from aema.memory import AdaptiveMemory

__version__ = "0.1.1"


def get_memory_store(*args, **kwargs):
    """Convenience factory to obtain the active AEMA memory store (SQLite or Postgres)."""
    store_mod = import_pkg("ai_service.memory.store")
    return store_mod.get_memory_store(*args, **kwargs)


async def execute_task(*args, **kwargs):
    """Convenience async entrypoint to execute a task through AEMA's 5-node LangGraph."""
    graph_mod = import_pkg("ai_service.graph")
    return await graph_mod.execute_task(*args, **kwargs)


def __getattr__(name: str):
    """Lazy-load core Pydantic schemas so `import aema` stays lightweight."""
    if name in ("Experience", "ExperienceMatch", "TrustHistoryRecord"):
        exp_mod = import_pkg("models.experience")
        return getattr(exp_mod, name)
    if name in ("TaskDomain", "ExperienceStatus", "MemoryMode"):
        dom_mod = import_pkg("models.domain")
        return getattr(dom_mod, name)
    if name in ("TaskExecuteRequest", "TaskExecution"):
        task_mod = import_pkg("models.task")
        return getattr(task_mod, name)
    raise AttributeError(f"module 'aema' has no attribute {name!r}")


__all__ = [
    "__version__",
    "AdaptiveMemory",
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
