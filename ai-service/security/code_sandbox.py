"""
Code Sandbox and AST Safety Verification Engine.
Provides pre-execution static analysis and process-level sandboxing to prevent
Host-Level Remote Code Execution (RCE), filesystem traversal, and network exfiltration.
"""

from __future__ import annotations

import ast
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ai_service.security.code_sandbox")

# Modules strictly prohibited in candidate solutions
PROHIBITED_MODULES: Set[str] = {
    # System and shell execution
    "os",
    "posix",
    "nt",
    "subprocess",
    "pty",
    "commands",
    "shutil",
    # Network sockets and HTTP clients
    "socket",
    "urllib",
    "requests",
    "http",
    "ftplib",
    "telnetlib",
    "aiohttp",
    "httpx",
    # Native bindings and raw memory access
    "ctypes",
    "cffi",
    # Arbitrary object deserialization
    "pickle",
    "shelve",
    # Runtime tampering / dynamic import hooks
    "importlib",
    "builtins",
    "_thread",
    "threading",
    "multiprocessing",
    "signal",
}

# Dangerous function calls
PROHIBITED_CALLS: Set[str] = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "breakpoint",
}

# Python sandbox escape gadget attributes
PROHIBITED_ATTRIBUTES: Set[str] = {
    "__subclasses__",
    "__globals__",
    "__code__",
    "__closure__",
    "__bases__",
    "__mro__",
}

# Dangerous target names passed to dynamic getattr/setattr
DANGEROUS_DYNAMIC_ATTRS: Set[str] = {
    "system",
    "popen",
    "spawn",
    "remove",
    "unlink",
    "rmdir",
    "rmtree",
    "connect",
    "eval",
    "exec",
}

# Sensitive path indicators in file operations
SENSITIVE_PATH_PATTERNS: Set[str] = {
    "/etc",
    "~",
    ".ssh",
    ".env",
    "id_rsa",
    "passwd",
    "shadow",
    "adaptive_memory.db",
}


class CodeSafetyVisitor(ast.NodeVisitor):
    """AST Visitor that validates Python code against dangerous execution patterns."""

    def __init__(self, is_test_code: bool = False):
        self.is_test_code = is_test_code
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_mod = alias.name.split(".")[0]
            if not self.is_test_code and root_mod in PROHIBITED_MODULES:
                self.violations.append(f"Prohibited module '{root_mod}' imported (line {node.lineno})")
            elif self.is_test_code and root_mod in {"socket", "requests", "urllib", "http", "pty"}:
                self.violations.append(f"Network module '{root_mod}' prohibited in test code (line {node.lineno})")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root_mod = node.module.split(".")[0]
            if not self.is_test_code and root_mod in PROHIBITED_MODULES:
                self.violations.append(f"Prohibited import from '{root_mod}' (line {node.lineno})")
            elif self.is_test_code and root_mod in {"socket", "requests", "urllib", "http", "pty"}:
                self.violations.append(f"Network import from '{root_mod}' prohibited in test code (line {node.lineno})")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct calls (e.g. eval(), exec())
        if isinstance(node.func, ast.Name):
            if node.func.id in PROHIBITED_CALLS:
                self.violations.append(f"Prohibited function call '{node.func.id}()' (line {node.lineno})")
            elif node.func.id == "getattr":
                # Check for getattr(x, "system") style evasion
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Constant) and str(arg.value).lower() in DANGEROUS_DYNAMIC_ATTRS:
                        self.violations.append(f"Prohibited dynamic getattr call on '{arg.value}' (line {node.lineno})")

        # Check open() on sensitive filesystem paths
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            if node.args and isinstance(node.args[0], ast.Constant):
                path_str = str(node.args[0].value)
                for sensitive in SENSITIVE_PATH_PATTERNS:
                    if sensitive in path_str:
                        self.violations.append(f"Prohibited access to sensitive path '{path_str}' in open() (line {node.lineno})")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in PROHIBITED_ATTRIBUTES:
            self.violations.append(f"Prohibited sandbox escape attribute '{node.attr}' accessed (line {node.lineno})")
        self.generic_visit(node)


def validate_code_safety(code: str, is_test_code: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Parses and checks Python source code for security violations.
    Returns (True, None) if safe, or (False, reason) if dangerous patterns exist.
    """
    if not code or not code.strip():
        return True, None

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        # Syntax errors are handled downstream by the test runner
        return True, None

    visitor = CodeSafetyVisitor(is_test_code=is_test_code)
    visitor.visit(tree)

    if visitor.violations:
        reason = "; ".join(visitor.violations)
        logger.warning(f"Security validation blocked untrusted code: {reason}")
        return False, reason

    return True, None


def get_sanitized_subprocess_env(workdir: str) -> Dict[str, str]:
    """
    Constructs an isolated, minimal environment dict for child execution processes.
    Strips all API keys, database credentials, and secret environment variables.
    """
    # Safe system path preservation
    clean_env: Dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        "HOME": workdir,
        "TMPDIR": workdir,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": workdir,
        "LANG": "en_US.UTF-8",
    }

    # Ensure no secrets leak even if child inspects os.environ
    for key, val in os.environ.items():
        k_upper = key.upper()
        if any(secret_term in k_upper for secret_term in ["KEY", "TOKEN", "SECRET", "PASS", "DATABASE", "SUPABASE"]):
            continue
        # Only allow minimal system variables
        if key in {"USER", "LOGNAME", "SHELL", "TERM", "VIRTUAL_ENV"}:
            clean_env[key] = val

    return clean_env


def apply_sandbox_resource_limits() -> None:
    """
    POSIX preexec_fn for subprocesses: clamps CPU time, virtual memory,
    and file size limits to prevent resource exhaustion and fork bombs.
    """
    if sys.platform == "win32":
        return

    try:
        import resource

        # Maximum CPU time: 10s soft, 15s hard
        resource.setrlimit(resource.RLIMIT_CPU, (10, 15))

        # Maximum file write size: 10 MB
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 15 * 1024 * 1024))

        # Virtual address space limit: 512 MB (if supported by OS)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 1024 * 1024 * 1024))
        except (ValueError, OSError):
            pass

        # Maximum child processes (fork bomb defense): 64
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 128))
        except (ValueError, OSError):
            pass

    except Exception as exc:
        logger.debug(f"Could not apply POSIX rlimits in child process: {exc}")

