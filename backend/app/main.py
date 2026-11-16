"""
FastAPI Application entry point for Adaptive AI Agent with Persistent Experience Memory.
Unified with backend.main to ensure all security middleware, rate limiting,
authentication helpers, and defensive headers are applied unconditionally across all entrypoints.
"""

from backend.main import app

__all__ = ["app"]
