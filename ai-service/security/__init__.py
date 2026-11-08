"""
Security subsystem for Adaptive Agent Memory Architecture (AEMA).
Provides code sandboxing, AST verification, prompt sanitization, rate limiting, and audit logging.
"""

from ai_service.security.audit import security_audit_logger
from ai_service.security.code_sandbox import (
    apply_sandbox_resource_limits,
    get_sanitized_subprocess_env,
    validate_code_safety,
)
from ai_service.security.rate_limiter import rate_limiter
from ai_service.security.sanitizer import (
    detect_prompt_injection_heuristic,
    format_bilateral_constraints,
    sanitize_memory_content,
)

__all__ = [
    "security_audit_logger",
    "apply_sandbox_resource_limits",
    "get_sanitized_subprocess_env",
    "validate_code_safety",
    "rate_limiter",
    "detect_prompt_injection_heuristic",
    "format_bilateral_constraints",
    "sanitize_memory_content",
]

