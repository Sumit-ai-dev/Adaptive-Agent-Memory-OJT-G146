"""
Security package for AEMA Backend Application.
Provides unified identity, JWT verification, and machine authorization.
"""

from backend.security.auth import (
    AuthContext,
    create_access_token,
    decode_jwt_token,
    get_auth_context,
    get_optional_auth_context,
    require_admin_auth,
)

__all__ = [
    "AuthContext",
    "create_access_token",
    "decode_jwt_token",
    "get_auth_context",
    "get_optional_auth_context",
    "require_admin_auth",
]
