"""
AI Service Package Root for Adaptive Agent Memory.
"""

from ai_service.config import settings
from ai_service.embedder import local_embedder
from ai_service.llm_client import llm_gateway

__all__ = ["settings", "llm_gateway", "local_embedder"]
