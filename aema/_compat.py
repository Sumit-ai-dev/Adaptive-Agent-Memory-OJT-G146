"""
Internal package resolver for AEMA.
Uses the namespaced `aema._internal.*` bundle when installed from a PyPI wheel
(avoiding top-level `models` / `backend` / `ai_service` collisions in user projects),
and seamlessly resolves repository-root modules in local / editable installs.
"""

import importlib
import importlib.util
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
