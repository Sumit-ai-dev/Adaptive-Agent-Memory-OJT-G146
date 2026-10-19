"""
Agent Execution API endpoints (/api/v1/agent).
Executes tasks through the 5-node LangGraph StateGraph cycle:
  retrieve_node -> execute_node -> evaluate_node -> reflect_node -> trust_node
"""

import logging
import secrets
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, status

from ai_service.config import settings

from ai_service.graph import execute_task
from ai_service.memory.store import BaseMemoryStore, SQLiteMemoryStore, get_memory_store
from models.domain import MemoryMode, TaskDomain
from models.task import TaskExecuteRequest, TaskExecution

logger = logging.getLogger("backend.app.api.v1.agent")

import sqlite3

router = APIRouter(prefix="/agent", tags=["Agent Execution"])

# Re-use canonical shared_store and persistence helpers from backend.routes.agent
try:
    from backend.routes.agent import (
        shared_store,
        _save_execution_to_db,
        _load_executions_from_db,
    )
except ImportError:
    from routes.agent import (
        shared_store,
        _save_execution_to_db,
        _load_executions_from_db,
    )

# In-memory execution history cache and unbounded lifetime execution counter
_execution_history: List[TaskExecution] = []
_total_task_executions: int = 0


def get_task_execution_count() -> int:
    """Returns the cumulative lifetime agent task execution count."""
    return _total_task_executions


@router.post(
    "/execute",
    response_model=TaskExecution,
    status_code=status.HTTP_200_OK,
    summary="Execute Agent Task through 5-Node Cyclical Loop",
)
async def run_agent_task(request: TaskExecuteRequest) -> TaskExecution:
    """
    Executes a task through the 5-node LangGraph orchestration loop:
    `retrieve_node` -> `execute_node` -> `evaluate_node` -> `reflect_node` -> `trust_node`.
    Handles multi-model dispatch, tool verification, and experiential memory calibration.
    """
    global _total_task_executions
    try:
        logger.info(f"Received agent execution request: domain={request.task_domain}, mode={request.memory_mode}")
        execution_result = await execute_task(request, memory_store=shared_store)
        _total_task_executions += 1

        # Durable execution persistence in SQLite (survives restarts)
        _save_execution_to_db(execution_result)

        # Store in historical cache (keep latest 100)
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


@router.get(
    "/executions",
    response_model=Dict[str, Any],
    summary="List Historical Task Executions",
)
async def list_executions(
    domain: Optional[str] = Query(None, description="Filter by task domain"),
    memory_mode: Optional[str] = Query(None, description="Filter by memory mode"),
    session_id: Optional[str] = Query(None, alias="sessionId", description="Filter by session ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Lists historical task execution records with optional filtering and pagination."""
    try:
        total, items = _load_executions_from_db(
            domain=domain,
            memory_mode=memory_mode,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        if total > 0 or not _execution_history:
            return {
                "total": total,
                "items": [item.model_dump(by_alias=True) for item in items],
            }
    except Exception as exc:
        logger.warning(f"Failed to query SQLite execution store: {exc}")

    filtered = _execution_history
    if domain and domain != "all":
        filtered = [e for e in filtered if e.task_domain.value == domain]
    if memory_mode and memory_mode != "all":
        filtered = [e for e in filtered if e.memory_mode.value == memory_mode]
    if session_id:
        filtered = [e for e in filtered if getattr(e, "session_id", None) == session_id]

    total = len(filtered)
    page_items = filtered[offset : offset + limit]

    return {
        "total": total,
        "items": [item.model_dump(by_alias=True) for item in page_items],
    }


@router.get(
    "/sessions",
    response_model=List[Dict[str, Any]],
    summary="List Recent Conversational Sessions",
)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Lists unique recent conversation sessions persisted in SQLite."""
    try:
        conn = sqlite3.connect(shared_store.db_path)
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

        if rows:
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

    seen: Dict[str, Dict[str, Any]] = {}
    for item in _execution_history:
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


@router.get(
    "/executions/{execution_id}",
    response_model=TaskExecution,
    summary="Get Granular Execution Trace",
)
async def get_execution_trace(execution_id: str) -> TaskExecution:
    """Returns fine-grained step traces, trajectory, and memory updates for a specific run."""
    for item in _execution_history:
        if item.id == execution_id or item.execution_id == execution_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Execution ID '{execution_id}' not found.",
    )


@router.delete(
    "/executions",
    status_code=status.HTTP_200_OK,
    summary="Clear Execution Trace History",
)
async def clear_executions(
    authorization: Optional[str] = Header(None, description="Admin authorization header"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token", description="Admin authorization token"),
) -> Dict[str, Any]:
    """Clears task execution history from in-memory cache."""
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
    return {"status": "success", "message": "All execution runs cleared."}

