"""
Hatchling custom build hook for AEMA.
Namespaces `ai-service`, `models`, and `backend` under `aema._internal` inside
built wheels so `pip install aema` never collides with user `models/` or `backend/`
packages while keeping the repository root layout intact for local development.
"""

from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_FROM_RE = re.compile(
    r"^([ \t]*from[ \t]+)(ai_service|models|backend)\b",
    re.MULTILINE,
)
_IMPORT_RE = re.compile(
    r"^([ \t]*import[ \t]+)(ai_service|models|backend)\b",
    re.MULTILINE,
)
_IGNORE_PATTERNS = shutil.ignore_patterns(
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "tests",
    "*.pyc",
    "*.pyo",
    ".env",
    ".DS_Store",
)


def _rewrite_internal_imports(py_file: Path) -> None:
    content = py_file.read_text(encoding="utf-8")
    updated = _FROM_RE.sub(r"\1aema._internal.\2", content)
    updated = _IMPORT_RE.sub(r"\1aema._internal.\2", updated)
    updated = updated.replace('"backend.main:app"', '"aema._internal.backend.main:app"')
    if updated != content:
        py_file.write_text(updated, encoding="utf-8")


class CustomBuildHook(BuildHookInterface):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tmp_dir: str | None = None

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        if self.target_name != "wheel":
            return

        root = Path(self.root)
        self._tmp_dir = tempfile.mkdtemp(prefix="aema_wheel_")
        internal_root = Path(self._tmp_dir) / "aema" / "_internal"
        internal_root.mkdir(parents=True, exist_ok=True)
        (internal_root / "__init__.py").write_text(
            '"""Internal namespaced modules bundled with AEMA."""\n',
            encoding="utf-8",
        )

        package_map = {
            "ai-service": "ai_service",
            "models": "models",
            "backend": "backend",
        }
        for src_name, dst_name in package_map.items():
            src_dir = root / src_name
            dst_dir = internal_root / dst_name
            shutil.copytree(src_dir, dst_dir, ignore=_IGNORE_PATTERNS)
            for py_file in dst_dir.rglob("*.py"):
                _rewrite_internal_imports(py_file)

        build_data.setdefault("force_include", {})
        build_data["force_include"][str(internal_root)] = "aema/_internal"

    def finalize(self, version: str, build_data: Dict[str, Any], artifact_path: str) -> None:
        if self._tmp_dir:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir = None
