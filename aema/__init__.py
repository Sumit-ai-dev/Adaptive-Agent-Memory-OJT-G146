"""
AEMA — Adaptive Experience Memory Agent.
Reliability-aware experiential memory for autonomous AI agents.
"""

__version__ = "0.1.0"


def get_memory_store(*args, **kwargs):
    """Convenience factory to obtain the active AEMA memory store (SQLite or Postgres)."""
    from ai_service.memory.store import get_memory_store as _gms
    return _gms(*args, **kwargs)


async def execute_task(*args, **kwargs):
    """Convenience async entrypoint to execute a task through AEMA's 5-node LangGraph."""
    from ai_service.graph import execute_task as _et
    return await _et(*args, **kwargs)


__all__ = ["__version__", "get_memory_store", "execute_task"]
