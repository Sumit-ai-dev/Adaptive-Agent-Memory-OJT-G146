"""
Agent Execution API endpoints.
Provides POST /agent/execute to trigger LangGraph 5-node cyclical workflow,
and GET /agent/executions to list execution traces.

Executions are persisted to SQLite (task_executions table) so history survives
server restarts.
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from models.domain import MemoryMode, TaskDomain
from models.task import TaskExecuteRequest, TaskExecution

logger = logging.getLogger("backend.routes.agent")

router = APIRouter(prefix="/agent", tags=["Agent Execution"])

# Global shared memory store for API server
shared_store = SQLiteMemoryStore(db_path="data/adaptive_memory.db")

# In-memory session cache — populated from SQLite on startup, kept in sync after that
_execution_history: List[TaskExecution] = []


# ─── SQLite Execution Persistence ────────────────────────────────────────────

def _ensure_executions_table() -> None:
    """Create task_executions table in the shared SQLite DB if it does not exist."""
    conn = sqlite3.connect(shared_store.db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_executions (
            id                     TEXT PRIMARY KEY,
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
    conn.commit()
    conn.close()


def _save_execution_to_db(execution: TaskExecution) -> None:
    """Persist a TaskExecution to SQLite as a full JSON blob."""
    try:
        payload = execution.model_dump_json(by_alias=True)
        conn = sqlite3.connect(shared_store.db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO task_executions
                (id, task_input, task_domain, memory_mode, memory_enabled,
                 status, outcome_score, latency_ms, tokens_used,
                 new_experience_created, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution.id,
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
    limit: int = 20,
    offset: int = 0,
) -> "tuple[int, List[TaskExecution]]":
    """
    Load paginated executions from SQLite.
    Returns (total_count, page_of_TaskExecution_objects).
    """
    try:
        conn = sqlite3.connect(shared_store.db_path)
        where_clauses: List[str] = []
        params: List[Any] = []
        if domain and domain != "all":
            where_clauses.append("task_domain = ?")
            params.append(domain)
        if memory_mode and memory_mode != "all":
            where_clauses.append("memory_mode = ?")
            params.append(memory_mode)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        total: int = conn.execute(
            f"SELECT COUNT(*) FROM task_executions {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT payload_json FROM task_executions {where_sql} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
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
    """Look up a single execution by ID from SQLite."""
    try:
        conn = sqlite3.connect(shared_store.db_path)
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


# ─── API Routes ───────────────────────────────────────────────────────────────

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
    Each execution is persisted to SQLite and survives server restarts.
    """
    try:
        logger.info(
            f"Received agent execution request: domain={request.task_domain}, mode={request.memory_mode}"
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


@router.get(
    "/executions",
    response_model=Dict[str, Any],
    summary="List Historical Task Executions",
)
async def list_executions(
    domain: Optional[str] = Query(None, description="Filter by task domain"),
    memory_mode: Optional[str] = Query(None, description="Filter by memory mode"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Lists historical task execution records with optional domain/memory-mode filtering
    and pagination. Reads from SQLite — persisted across server restarts.
    """
    total, items = _load_executions_from_db(
        domain=domain, memory_mode=memory_mode, limit=limit, offset=offset
    )
    return {
        "total": total,
        "items": [item.model_dump(by_alias=True) for item in items],
    }


@router.get(
    "/executions/{execution_id}",
    response_model=TaskExecution,
    summary="Get Granular Execution Trace",
)
async def get_execution_trace(execution_id: str) -> TaskExecution:
    """
    Returns the full execution trace (trajectory, memory context, trust updates)
    for a specific execution ID. Checks the in-memory session cache first,
    then falls back to SQLite for executions from previous sessions.
    """
    # Fast path: session cache
    for item in _execution_history:
        if item.id == execution_id or item.execution_id == execution_id:
            return item

    # Durable fallback: SQLite
    found = _get_execution_from_db(execution_id)
    if found:
        return found

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Execution ID '{execution_id}' not found.",
    )
