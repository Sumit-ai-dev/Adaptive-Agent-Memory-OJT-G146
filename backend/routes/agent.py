"""
Agent Execution API endpoints.
Provides POST /agent/execute to trigger LangGraph 5-node cyclical workflow,
and GET /agent/executions to list execution traces.

Executions are persisted to SQLite (task_executions table) so history survives
server restarts.
"""

import json
import logging
import secrets
import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from aema._compat import resolve_db_path
from ai_service.config import settings
from ai_service.graph import execute_task, execute_task_stream
from ai_service.memory.store import BaseMemoryStore, SQLiteMemoryStore, get_memory_store
from ai_service.security import rate_limiter, security_audit_logger
from backend.security.auth import (
    AuthContext,
    decode_jwt_token,
    get_auth_context,
    get_optional_auth_context,
)
from models.domain import MemoryMode, TaskDomain
from models.task import TaskExecuteRequest, TaskExecution

logger = logging.getLogger("backend.routes.agent")

router = APIRouter(prefix="/agent", tags=["Agent Execution"])

# Global shared memory store for API server
shared_store: BaseMemoryStore = get_memory_store(db_path=resolve_db_path(), auto_seed=True)

# In-memory session cache: populated from SQLite on startup, kept in sync after that
_execution_history: List[TaskExecution] = []


def _sqlite_db_path() -> Optional[str]:
    """Return the SQLite file path when SQLiteMemoryStore is active, else None."""
    return getattr(shared_store, "db_path", None)


def _filter_in_memory_executions(
    domain: Optional[str] = None,
    memory_mode: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[TaskExecution]:
    """Filter cached executions when using a non-SQLite store (Postgres/Supabase)."""
    items: List[TaskExecution] = []
    for ex in _execution_history:
        ex_domain = ex.task_domain.value if hasattr(ex.task_domain, "value") else str(ex.task_domain)
        ex_mode = ex.memory_mode.value if hasattr(ex.memory_mode, "value") else str(ex.memory_mode)
        if domain and domain != "all" and ex_domain != domain:
            continue
        if memory_mode and memory_mode != "all" and ex_mode != memory_mode:
            continue
        if session_id and ex.session_id != session_id:
            continue
        if user_id and ex.user_id != user_id:
            continue
        items.append(ex)
    return items


# ─── SQLite Execution Persistence ────────────────────────────────────────────

def _ensure_executions_table() -> None:
    """Create task_executions table in the shared SQLite DB if running on SQLite."""
    db_path = _sqlite_db_path()
    if not db_path:
        return
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_executions (
            id                     TEXT PRIMARY KEY,
            session_id             TEXT,
            user_id                TEXT,
            task_input             TEXT NOT NULL,
            task_domain            TEXT NOT NULL,
            memory_mode            TEXT NOT NULL,
            memory_enabled         INTEGER NOT NULL DEFAULT 1,
            status                 TEXT NOT NULL DEFAULT 'completed',
            outcome_score          REAL,
            latency_ms             INTEGER DEFAULT 0,
            tokens_used            INTEGER DEFAULT 0,
            new_experience_created INTEGER DEFAULT 0,
            payload_json           TEXT NOT NULL,
            created_at             TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    # Backward compatibility: verify session_id and user_id columns exist
    cursor = conn.execute("PRAGMA table_info(task_executions)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "session_id" not in existing_cols:
        try:
            conn.execute("ALTER TABLE task_executions ADD COLUMN session_id TEXT")
            conn.commit()
        except Exception as exc:
            logger.warning(f"Could not add session_id column to task_executions: {exc}")
    if "user_id" not in existing_cols:
        try:
            conn.execute("ALTER TABLE task_executions ADD COLUMN user_id TEXT")
            conn.commit()
        except Exception as exc:
            logger.warning(f"Could not add user_id column to task_executions: {exc}")
    conn.commit()
    conn.close()


def _save_execution_to_db(execution: TaskExecution) -> None:
    """Persist a TaskExecution to SQLite as a full JSON blob when SQLite is active."""
    db_path = _sqlite_db_path()
    if not db_path:
        return
    try:
        payload = execution.model_dump_json(by_alias=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO task_executions
                (id, session_id, user_id, task_input, task_domain, memory_mode, memory_enabled,
                 status, outcome_score, latency_ms, tokens_used,
                 new_experience_created, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution.id,
                execution.session_id,
                execution.user_id,
                (execution.task_input or "")[:500],
                execution.task_domain.value,
                execution.memory_mode.value,
                int(execution.memory_enabled),
                execution.status.value,
                execution.outcome_score,
                execution.latency_ms,
                execution.tokens_used,
                int(execution.new_experience_created),
                payload,
                str(execution.created_at),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"Could not persist execution {execution.id} to SQLite: {exc}")


def _load_executions_from_db(
    domain: Optional[str] = None,
    memory_mode: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    unauthenticated_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> "tuple[int, List[TaskExecution]]":
    """
    Load paginated executions from SQLite (or in-memory cache when using Postgres/Supabase).
    Returns (total_count, page_of_TaskExecution_objects).
    """
    db_path = _sqlite_db_path()
    if not db_path:
        filtered = _filter_in_memory_executions(
            domain=domain,
            memory_mode=memory_mode,
            session_id=session_id,
            user_id=user_id,
        )
        if unauthenticated_only:
            filtered = [ex for ex in filtered if ex.user_id is None or ex.user_id == "anonymous"]
        return len(filtered), filtered[offset : offset + limit]

    try:
        conn = sqlite3.connect(db_path)
        where_clauses: List[str] = []
        params: List[Any] = []
        if domain and domain != "all":
            where_clauses.append("task_domain = ?")
            params.append(domain)
        if memory_mode and memory_mode != "all":
            where_clauses.append("memory_mode = ?")
            params.append(memory_mode)
        if session_id:
            where_clauses.append("session_id = ?")
            params.append(session_id)
        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)
        elif unauthenticated_only:
            where_clauses.append("(user_id IS NULL OR user_id = 'anonymous')")

        # Build parameterized queries with static structure
        base_count_sql = "SELECT COUNT(*) FROM task_executions"
        base_select_sql = "SELECT payload_json FROM task_executions"
        if where_clauses:
            filter_expression = " WHERE " + " AND ".join(where_clauses)
            count_sql = base_count_sql + filter_expression  # nosec B608
            select_sql = base_select_sql + filter_expression + " ORDER BY created_at DESC LIMIT ? OFFSET ?"  # nosec B608
        else:
            count_sql = base_count_sql
            select_sql = base_select_sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?"

        total: int = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(select_sql, params + [limit, offset]).fetchall()
        conn.close()

        items: List[TaskExecution] = []
        for (payload_json,) in rows:
            try:
                items.append(TaskExecution.model_validate_json(payload_json))
            except Exception as exc:
                logger.warning(f"Could not deserialise execution row: {exc}")
        return total, items
    except Exception as exc:
        logger.warning(f"Could not load executions from SQLite: {exc}")
        return 0, []


def _get_execution_from_db(execution_id: str) -> Optional[TaskExecution]:
    """Look up a single execution by ID from SQLite (or session cache)."""
    db_path = _sqlite_db_path()
    if not db_path:
        return next((ex for ex in _execution_history if ex.id == execution_id), None)

    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT payload_json FROM task_executions WHERE id = ?", (execution_id,)
        ).fetchone()
        conn.close()
        if row:
            return TaskExecution.model_validate_json(row[0])
    except Exception as exc:
        logger.warning(f"SQLite lookup failed for execution {execution_id}: {exc}")
    return None


# Initialise table on module load and warm in-memory cache from persisted records
_ensure_executions_table()
try:
    _, _persisted = _load_executions_from_db(limit=100)
    _execution_history.extend(_persisted)
    if _persisted:
        logger.info(
            f"Loaded {len(_persisted)} persisted execution(s) from SQLite into session cache."
        )
except Exception as _warm_exc:
    logger.warning(f"Could not pre-load execution history from SQLite: {_warm_exc}")


def verify_agent_execution_auth(
    authorization: Optional[str] = None,
    x_api_key: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Optional[str]:
    """
    Validates API key or JWT for agent execution when REQUIRE_AGENT_AUTH is enabled.
    Accepts AGENT_API_KEY, ADMIN_API_KEY, or valid user Bearer JWT. Logs authentication failures with client IP.
    """
    configured_key = (getattr(settings, "AGENT_API_KEY", None) or "").strip()
    admin_key = (getattr(settings, "ADMIN_API_KEY", None) or "").strip()
    require_auth = getattr(settings, "REQUIRE_AGENT_AUTH", False)

    # In open/dev/demo mode, allow without credentials
    if not require_auth and not configured_key:
        return None

    target_keys = [k for k in [configured_key, admin_key] if k]
    token = (x_api_key or "").strip()
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    # 1. Check if token is a valid User Bearer JWT
    if token and token.count(".") == 2:
        try:
            payload = decode_jwt_token(token)
            uid = payload.get("sub") or payload.get("user_id") or payload.get("id")
            if uid:
                return f"user:{uid}"
        except Exception:
            pass

    if not target_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGENT_API_KEY or ADMIN_API_KEY must be configured on the server when authentication is enforced.",
        )

    if not token or not any(secrets.compare_digest(token, k) for k in target_keys):
        security_audit_logger.record_event(
            event_type="AUTHENTICATION_FAILURE",
            severity="HIGH",
            details={"endpoint": "/agent/execute", "reason": "invalid_or_missing_token"},
            client_ip=client_ip or "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid Agent or Admin API Key required for execution.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return "authorized_client"


def resolve_execution_tenant(
    requested_user_id: Optional[str],
    auth: Optional[AuthContext],
) -> Optional[str]:
    """
    Derives execution tenant ID exclusively from authenticated context.
    - Authenticated user: ALWAYS returns auth.user_id (ignoring any client-supplied user_id).
    - Machine/Admin: may specify a target tenant via requested_user_id, or defaults to None.
    - Anonymous/Unauthenticated: NEVER trusts client-supplied tenant ID; returns None.
    """
    if isinstance(auth, AuthContext) and auth.is_authenticated:
        if auth.is_machine or auth.is_admin:
            return requested_user_id
        return auth.user_id
    return None


# ─── API Routes ───────────────────────────────────────────────────────────────

@router.post(
    "/execute",
    response_model=TaskExecution,
    status_code=status.HTTP_200_OK,
    summary="Execute Agent Task through 5-Node Cyclical Loop",
)
async def run_agent_task(
    request: TaskExecuteRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None, description="Admin or Agent authorization header"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Agent API Key header"),
) -> TaskExecution:
    """
    Executes a task through the 5-node LangGraph orchestration loop:
    `retrieve_node` -> `execute_node` -> `evaluate_node` -> `reflect_node` -> `trust_node`.
    Handles multi-model dispatch, tool verification, and experiential memory calibration.
    Each execution is persisted to SQLite and survives server restarts.
    """
    client_ip = http_request.client.host if (http_request and http_request.client) else "127.0.0.1"

    # Rate limiting protection
    allowed, retry_after = rate_limiter.check(
        client_ip=client_ip,
        max_requests=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
    )
    if not allowed:
        security_audit_logger.record_event(
            event_type="RATE_LIMIT_EXCEEDED",
            severity="WARNING",
            details={"endpoint": "/agent/execute", "retry_after": retry_after},
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # API Authentication verification
    auth_ctx = get_auth_context(http_request, authorization, x_api_key)
    request.user_id = resolve_execution_tenant(request.user_id, auth_ctx)

    try:
        logger.info(
            f"Received agent execution request: domain={request.task_domain}, mode={request.memory_mode} from IP={client_ip}"
        )
        execution_result = await execute_task(request, memory_store=shared_store)

        # Persist to SQLite (durable across restarts)
        _save_execution_to_db(execution_result)

        # Keep in session cache (fast reads within current session, keep latest 100)
        _execution_history.insert(0, execution_result)
        if len(_execution_history) > 100:
            _execution_history.pop()

        return execution_result
    except Exception as e:
        logger.error(f"Error during agent task execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution pipeline error: {str(e)}",
        )


@router.post(
    "/execute/stream",
    summary="Execute Agent Task with Real-Time Event & Token Streaming (SSE)",
)
async def run_agent_task_stream(
    request: TaskExecuteRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None, description="Admin or Agent authorization header"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="Agent API Key header"),
):
    """
    Executes a task through the 5-node LangGraph orchestration loop with real-time SSE streaming.
    Streams node lifecycle events (node_complete), code generation tokens, and final TaskExecution.
    """
    client_ip = http_request.client.host if (http_request and http_request.client) else "127.0.0.1"
    auth_ctx = get_auth_context(http_request, authorization, x_api_key)
    request.user_id = resolve_execution_tenant(request.user_id, auth_ctx)

    async def event_generator():
        try:
            async for sse_chunk in execute_task_stream(request, memory_store=shared_store):
                if sse_chunk.startswith("event: done"):
                    try:
                        lines = sse_chunk.strip().split("\n")
                        for line in lines:
                            if line.startswith("data: "):
                                payload_data = json.loads(line[6:])
                                res_obj = payload_data.get("result")
                                if res_obj:
                                    exec_obj = TaskExecution.model_validate(res_obj)
                                    _save_execution_to_db(exec_obj)
                                    _execution_history.insert(0, exec_obj)
                                    if len(_execution_history) > 100:
                                        _execution_history.pop()
                    except Exception as cache_exc:
                        logger.warning(f"Could not cache streaming execution in db: {cache_exc}")

                yield sse_chunk
        except Exception as exc:
            logger.error(f"Error during streaming execution: {exc}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/executions",
    response_model=Dict[str, Any],
    summary="List Historical Task Executions",
)
async def list_executions(
    domain: Optional[str] = Query(None, description="Filter by task domain"),
    memory_mode: Optional[str] = Query(None, description="Filter by memory mode"),
    session_id: Optional[str] = Query(None, alias="sessionId", description="Filter by session ID"),
    user_id: Optional[str] = Query(None, alias="userId", description="Filter by user ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> Dict[str, Any]:
    """
    Lists historical task execution records with optional domain/memory-mode/session_id filtering
    and pagination. Reads from SQLite: persisted across server restarts.
    Enforces strict tenant scoping.
    """
    unauthenticated_only = False
    if isinstance(auth, AuthContext) and auth.is_authenticated:
        if auth.is_admin or auth.is_machine:
            effective_user = user_id
        else:
            effective_user = auth.user_id
    else:
        if getattr(settings, "REQUIRE_USER_AUTH", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to filter executions by user ID.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        effective_user = None
        unauthenticated_only = True

    total, items = _load_executions_from_db(
        domain=domain,
        memory_mode=memory_mode,
        session_id=session_id,
        user_id=effective_user,
        unauthenticated_only=unauthenticated_only,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "items": [item.model_dump(by_alias=True) for item in items],
    }


@router.get(
    "/sessions",
    response_model=List[Dict[str, Any]],
    summary="List Recent Conversational Sessions",
)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[str] = Query(None, alias="userId", description="Filter by user ID"),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> List[Dict[str, Any]]:
    """
    Returns unique recent conversation sessions with session ID, title, turn count,
    and last activity timestamp from persisted execution history.
    Enforces multi-tenant scoping.
    """
    unauthenticated_only = False
    if isinstance(auth, AuthContext) and auth.is_authenticated:
        if auth.is_admin or auth.is_machine:
            effective_user = user_id
        else:
            effective_user = auth.user_id
    else:
        if getattr(settings, "REQUIRE_USER_AUTH", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to filter sessions by user ID.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        effective_user = None
        unauthenticated_only = True

    db_path = _sqlite_db_path()
    if not db_path:
        seen: Dict[str, Dict[str, Any]] = {}
        for item in _execution_history:
            if effective_user and item.user_id != effective_user:
                continue
            if unauthenticated_only and (item.user_id is not None and item.user_id != "anonymous"):
                continue
            sid = getattr(item, "session_id", None)
            if sid and sid not in seen:
                seen[sid] = {
                    "sessionId": sid,
                    "title": (item.task_input or "New Conversation")[:60],
                    "lastActive": str(item.created_at),
                    "turnCount": 1,
                }
            elif sid:
                seen[sid]["turnCount"] += 1
        return list(seen.values())[:limit]

    try:
        conn = sqlite3.connect(db_path)
        if effective_user:
            rows = conn.execute(
                """
                SELECT session_id, task_input, MAX(created_at) as last_active, COUNT(*) as turn_count
                FROM task_executions
                WHERE session_id IS NOT NULL AND session_id != '' AND user_id = ?
                GROUP BY session_id
                ORDER BY last_active DESC
                LIMIT ?
                """,
                (effective_user, limit),
            ).fetchall()
        elif unauthenticated_only:
            rows = conn.execute(
                """
                SELECT session_id, task_input, MAX(created_at) as last_active, COUNT(*) as turn_count
                FROM task_executions
                WHERE session_id IS NOT NULL AND session_id != '' AND (user_id IS NULL OR user_id = 'anonymous')
                GROUP BY session_id
                ORDER BY last_active DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT session_id, task_input, MAX(created_at) as last_active, COUNT(*) as turn_count
                FROM task_executions
                WHERE session_id IS NOT NULL AND session_id != ''
                GROUP BY session_id
                ORDER BY last_active DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        conn.close()

        sessions = []
        for row in rows:
            sessions.append({
                "sessionId": row[0],
                "title": (row[1] or "New Conversation")[:60],
                "lastActive": row[2],
                "turnCount": row[3],
            })
        return sessions
    except Exception as exc:
        logger.warning(f"Could not load sessions from SQLite: {exc}")
        return []


@router.get(
    "/executions/{execution_id}",
    response_model=TaskExecution,
    summary="Get Granular Execution Trace",
)
async def get_execution_trace(
    execution_id: str,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> TaskExecution:
    """
    Returns the full execution trace (trajectory, memory context, trust updates)
    for a specific execution ID. Checks the in-memory session cache first,
    then falls back to SQLite for executions from previous sessions.
    Enforces tenant authorization: users can only view their own executions;
    admins and machine services can view any execution.
    """
    # Fast path: session cache
    found = None
    for item in _execution_history:
        if item.id == execution_id or getattr(item, "execution_id", None) == execution_id:
            found = item
            break

    # Durable fallback: SQLite
    if not found:
        found = _get_execution_from_db(execution_id)

    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution ID '{execution_id}' not found.",
        )

    # Authorize tenant ownership
    exec_user = getattr(found, "user_id", None)
    if exec_user and exec_user != "anonymous":
        if isinstance(auth, AuthContext) and auth.is_authenticated:
            if not auth.is_admin and not auth.is_machine and auth.user_id != exec_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Execution ID '{execution_id}' not found.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution ID '{execution_id}' not found.",
            )
    elif getattr(settings, "REQUIRE_USER_AUTH", False):
        if not (isinstance(auth, AuthContext) and auth.is_authenticated):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return found


@router.delete(
    "/executions",
    status_code=status.HTTP_200_OK,
    summary="Clear Execution Trace History",
)
async def clear_executions(
    authorization: Optional[str] = Header(None, description="Admin authorization header"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token", description="Admin authorization token"),
) -> Dict[str, Any]:
    """
    Clears task execution history from SQLite and in-memory cache.
    Requires admin authorization token/header to prevent unauthorized trace destruction.
    """
    configured_key = (getattr(settings, "ADMIN_API_KEY", None) or "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured on the server. Destructive history deletion is disabled.",
        )

    token = (x_admin_token or "").strip()
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    if not token or not secrets.compare_digest(token, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authorization required to clear execution history.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    global _execution_history
    _execution_history.clear()
    db_path = _sqlite_db_path()
    if not db_path:
        return {"status": "success", "message": "All execution runs cleared."}

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM task_executions")
        conn.commit()
        conn.close()
        return {"status": "success", "message": "All execution runs cleared."}
    except Exception as e:
        logger.error(f"Error clearing executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear executions: {str(e)}",
        )

