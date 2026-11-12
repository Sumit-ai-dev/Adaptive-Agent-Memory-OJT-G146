"""
Internal package resolver and path helpers for AEMA.
Uses the namespaced `aema._internal.*` bundle when installed from a PyPI wheel
(avoiding top-level `models` / `backend` / `ai_service` collisions in user projects),
and seamlessly resolves repository-root modules in local / editable installs.
"""

import importlib
import importlib.util
import os
from pathlib import Path
import sys
from typing import Any


def has_internal_bundle() -> bool:
    """Return True when internal modules are bundled under `aema._internal`."""
    return importlib.util.find_spec("aema._internal") is not None


def import_pkg(module_path: str) -> Any:
    """Import an AEMA internal module regardless of wheel vs. repo layout."""
    if has_internal_bundle():
        return importlib.import_module(f"aema._internal.{module_path}")

    repo_root = Path(__file__).resolve().parent.parent
    if (repo_root / "models").is_dir() and str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return importlib.import_module(module_path)


def resolve_db_path() -> str:
    """
    Resolve the default SQLite path consistently across CLI and `AdaptiveMemory`:
    1. Explicit `AEMA_DB_PATH` or `SQLITE_DB_PATH` environment variable.
    2. Local `./data/adaptive_memory.db` if running inside a repository that already has it.
    3. User-level `~/.aema/memory.db` otherwise.
    """
    env_path = os.environ.get("AEMA_DB_PATH") or os.environ.get("SQLITE_DB_PATH")
    if env_path:
        return env_path

    repo_db = Path.cwd() / "data" / "adaptive_memory.db"
    if repo_db.is_file():
        return str(repo_db)

    return str(Path.home() / ".aema" / "memory.db")
