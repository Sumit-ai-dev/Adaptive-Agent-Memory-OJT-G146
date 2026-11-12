"""
AI Service Package Root for Adaptive Agent Memory.
"""

__all__ = ["settings", "llm_gateway", "local_embedder"]


def __getattr__(name: str):
    if name == "settings":
        from ai_service.config import settings
        return settings
    if name == "local_embedder":
        from ai_service.embedder import local_embedder
        return local_embedder
    if name == "llm_gateway":
        from ai_service.llm_client import llm_gateway
        return llm_gateway
    raise AttributeError(f"module 'ai_service' has no attribute {name!r}")
