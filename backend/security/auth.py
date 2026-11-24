"""
Unified Identity and Authentication Gateway for AEMA.
Harmonizes machine authorization (AGENT_API_KEY, ADMIN_API_KEY) with
user identity tokens (Supabase GoTrue JWTs, local development JWTs).
Enforces multi-tenant user boundaries across agent execution and memory management.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException, Request, status
import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from ai_service.config import settings
from ai_service.security import security_audit_logger

logger = logging.getLogger("backend.security.auth")


@dataclass
class AuthContext:
    """Authenticated identity context representing a user or machine actor."""
    user_id: str
    email: Optional[str] = None
    role: str = "user"  # "admin", "service", "user", "anonymous"
    is_machine: bool = False
    raw_token: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_authenticated(self) -> bool:
        return self.role != "anonymous"


DEFAULT_INSECURE_SECRETS = {
    "dev-insecure-jwt-secret-do-not-use-in-prod-12345",
    "secret",
    "jwt_secret",
}


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> str:
    """
    Generate a signed JWT token for user authentication (used for testing and local auth).
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=24)
    to_encode.update({"exp": expire, "iat": now})
    secret = secret_key or settings.SUPABASE_JWT_SECRET or settings.AEMA_JWT_SECRET
    alg = algorithm or settings.JWT_ALGORITHM
    return jwt.encode(to_encode, secret, algorithm=alg)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Supports symmetric HMAC (HS256) with SUPABASE_JWT_SECRET.
    Only falls back to AEMA_JWT_SECRET if SUPABASE_JWT_SECRET is unset.
    Strictly isolates secrets: does NOT accept AEMA_JWT_SECRET alongside SUPABASE_JWT_SECRET.
    Rejects known default insecure secret in production environments.
    """
    import os
    env_name = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
    is_production = env_name in ("production", "prod")

    secrets_to_try: List[str] = []
    if settings.SUPABASE_JWT_SECRET:
        # Crucial security rule: When SUPABASE_JWT_SECRET is configured,
        # never accept or fall back to any other JWT secret.
        secrets_to_try.append(settings.SUPABASE_JWT_SECRET.strip())
    elif settings.AEMA_JWT_SECRET:
        sec = settings.AEMA_JWT_SECRET.strip()
        if sec in DEFAULT_INSECURE_SECRETS and is_production:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default insecure JWT secret cannot be used in production.",
            )
        secrets_to_try.append(sec)

    if not secrets_to_try:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret is not configured on the server.",
        )

    last_error: Optional[Exception] = None
    for sec in secrets_to_try:
        try:
            payload = jwt.decode(
                token,
                sec,
                algorithms=["HS256", "HS384", "HS512"],
                options={"verify_exp": True, "verify_signature": True},
            )
            return payload
        except ExpiredSignatureError as exp_err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token has expired\""},
            ) from exp_err
        except PyJWTError as err:
            last_error = err
            continue

    # Development-only fallback: if SUPABASE_JWT_SECRET is unconfigured in local development,
    # decode the authentic Supabase token payload so local developers aren't blocked by 401s.
    if not is_production and not settings.SUPABASE_JWT_SECRET:
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            if "supabase" in unverified.get("iss", "") or unverified.get("role") in ("authenticated", "anon"):
                logger.info(
                    f"Decoded Supabase JWT without signature check in development for tenant: {unverified.get('sub')}"
                )
                return unverified
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token.",
        headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
    )


def _extract_tokens_from_headers(
    authorization: Any = None,
    x_api_key: Any = None,
    x_admin_token: Any = None,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Normalizes bearer token, API key, and admin token from HTTP headers."""
    # Defensively handle default FastAPI Header params if called as a regular function
    raw_auth = authorization if isinstance(authorization, str) else None
    raw_api_key = x_api_key if isinstance(x_api_key, str) else None
    raw_admin = x_admin_token if isinstance(x_admin_token, str) else None

    bearer_token = None
    if raw_auth:
        auth_clean = raw_auth.strip()
        if auth_clean.lower().startswith("bearer "):
            bearer_token = auth_clean[7:].strip()
        else:
            bearer_token = auth_clean

    api_key = (raw_api_key or "").strip() or None
    admin_token = (raw_admin or "").strip() or None
    return bearer_token, api_key, admin_token


def get_auth_context(
    request: Request,
    authorization: Optional[str] = Header(None, description="Bearer JWT or API Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Agent API Key"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token", description="Admin API Key"),
) -> AuthContext:
    """
    Unified identity authentication gateway dependency for FastAPI.
    Validates machine keys (ADMIN_API_KEY, AGENT_API_KEY) and user Bearer JWTs.
    Fails closed with 401 when credentials are invalid or missing under enforced auth.
    Allows anonymous context in open/dev mode when no keys are configured and auth is disabled.
    """
    client_ip = request.client.host if (request and request.client) else "127.0.0.1"
    bearer_token, api_key, admin_token = _extract_tokens_from_headers(authorization, x_api_key, x_admin_token)

    admin_secret = (getattr(settings, "ADMIN_API_KEY", None) or "").strip()
    agent_secret = (getattr(settings, "AGENT_API_KEY", None) or "").strip()
    require_agent_auth = getattr(settings, "REQUIRE_AGENT_AUTH", False)
    require_user_auth = getattr(settings, "REQUIRE_USER_AUTH", False)

    # 1. Machine Admin Authentication
    if admin_secret:
        if admin_token and secrets.compare_digest(admin_token, admin_secret):
            return AuthContext(user_id="system:admin", email="admin@aema.internal", role="admin", is_machine=True)
        if bearer_token and secrets.compare_digest(bearer_token, admin_secret):
            return AuthContext(user_id="system:admin", email="admin@aema.internal", role="admin", is_machine=True)

    # 2. Machine Service Authentication (AGENT_API_KEY)
    if agent_secret:
        if api_key and secrets.compare_digest(api_key, agent_secret):
            return AuthContext(user_id="system:agent", email="agent@aema.internal", role="service", is_machine=True)
        if bearer_token and secrets.compare_digest(bearer_token, agent_secret):
            return AuthContext(user_id="system:agent", email="agent@aema.internal", role="service", is_machine=True)

    # 3. User Bearer JWT Authentication
    if bearer_token:
        # Check if the bearer token has JWT structure (header.payload.signature)
        if bearer_token.count(".") == 2:
            payload = decode_jwt_token(bearer_token)
            user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing valid subject (sub) claim.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            email = payload.get("email") or payload.get("user_metadata", {}).get("email")
            role = payload.get("role") or payload.get("app_metadata", {}).get("role") or "user"
            return AuthContext(
                user_id=str(user_id),
                email=email,
                role=role,
                is_machine=False,
                raw_token=bearer_token,
            )

    # 4. Explicit credential supplied but invalid -> 401
    has_any_token = bool(bearer_token or api_key or admin_token)
    if has_any_token:
        security_audit_logger.record_event(
            event_type="AUTHENTICATION_FAILURE",
            severity="HIGH",
            details={"endpoint": request.url.path, "reason": "invalid_credentials"},
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Missing credentials when authentication is enforced -> 401
    path = request.url.path if request else ""
    is_execute_endpoint = path.endswith("/execute") or path.endswith("/execute/stream")
    if require_agent_auth or require_user_auth or (agent_secret and is_execute_endpoint):
        security_audit_logger.record_event(
            event_type="AUTHENTICATION_FAILURE",
            severity="HIGH",
            details={"endpoint": path, "reason": "missing_credentials"},
            client_ip=client_ip,
        )
        detail_msg = (
            "Valid Agent or Admin API Key required for execution."
            if is_execute_endpoint
            else "Authentication required."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 6. Open / dev mode (e.g. unauthenticated unit tests or local development without keys)
    return AuthContext(
        user_id="anonymous",
        email=None,
        role="anonymous",
        is_machine=False,
    )


def get_optional_auth_context(
    request: Request,
    authorization: Optional[str] = Header(None, description="Bearer JWT or API Key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> Optional[AuthContext]:
    """
    Returns AuthContext if credentials are provided and valid.
    If REQUIRE_USER_AUTH is True, strictly requires credentials and raises 401 if missing.
    Returns None if no credentials are provided and REQUIRE_USER_AUTH is False.
    Raises 401 if invalid credentials were explicitly supplied.
    """
    bearer_token, api_key, admin_token = _extract_tokens_from_headers(authorization, x_api_key, x_admin_token)
    if not (bearer_token or api_key or admin_token):
        if getattr(settings, "REQUIRE_USER_AUTH", False):
            client_ip = request.client.host if (request and request.client) else "127.0.0.1"
            path = request.url.path if request else ""
            security_audit_logger.record_event(
                event_type="AUTHENTICATION_FAILURE",
                severity="HIGH",
                details={"endpoint": path, "reason": "missing_required_user_credentials"},
                client_ip=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None
    return get_auth_context(request, authorization, x_api_key, x_admin_token)


def require_admin_auth(
    request: Request,
    authorization: Optional[str] = Header(None, description="Admin authorization header"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token", description="Admin authorization token"),
) -> AuthContext:
    """
    Validates administrative credentials for destructive operations and quarantine recovery.
    Fails closed with HTTP 503 if ADMIN_API_KEY is not configured on the server and no admin credentials exist.
    Raises HTTP 401 if credentials are missing or invalid.
    """
    configured_key = (getattr(settings, "ADMIN_API_KEY", None) or "").strip()
    client_ip = request.client.host if (request and request.client) else "127.0.0.1"

    bearer_token, _, admin_token = _extract_tokens_from_headers(authorization, None, x_admin_token)
    token = admin_token or bearer_token

    # Backward compatibility: if ADMIN_API_KEY is unset on the server, fail closed with 503
    if not configured_key and not (token and token.count(".") == 2):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured on the server. Administrative actions are disabled.",
        )

    if not token:
        security_audit_logger.record_event(
            event_type="AUTHENTICATION_FAILURE",
            severity="HIGH",
            details={"endpoint": request.url.path, "reason": "missing_admin_token"},
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authorization required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check static key
    if configured_key and secrets.compare_digest(token, configured_key):
        return AuthContext(user_id="system:admin", email="admin@aema.internal", role="admin", is_machine=True)

    # Check JWT admin role
    if token.count(".") == 2:
        try:
            payload = decode_jwt_token(token)
            role = payload.get("role") or payload.get("app_metadata", {}).get("role")
            if role == "admin":
                user_id = payload.get("sub") or payload.get("id") or "admin"
                email = payload.get("email")
                return AuthContext(user_id=str(user_id), email=email, role="admin", is_machine=False, raw_token=token)
        except Exception:
            pass

    security_audit_logger.record_event(
        event_type="AUTHENTICATION_FAILURE",
        severity="HIGH",
        details={"endpoint": request.url.path, "reason": "invalid_admin_token"},
        client_ip=client_ip,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin authorization required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
