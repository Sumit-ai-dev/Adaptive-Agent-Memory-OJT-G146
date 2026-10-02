"""
Agent Execution API endpoints (/api/v1/agent).
Executes tasks through the 5-node LangGraph StateGraph cycle:
  retrieve_node -> execute_node -> evaluate_node -> reflect_node -> trust_node
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ai_service.graph import execute_task
from ai_service.memory.store import SQLiteMemoryStore
from models.domain import MemoryMode, TaskDomain
from models.task import TaskExecuteRequest, TaskExecution

logger = logging.getLogger("backend.app.api.v1.agent")

router = APIRouter(prefix="/agent", tags=["Agent Execution"])

# Global shared memory store for API server
shared_store = SQLiteMemoryStore(db_path="data/adaptive_memory.db")

# In-memory execution history cache
_execution_history: List[TaskExecution] = []


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
    try:
        logger.info(f"Received agent execution request: domain={request.task_domain}, mode={request.memory_mode}")
        execution_result = await execute_task(request, memory_store=shared_store)

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
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Lists historical task execution records with optional filtering and pagination."""
    filtered = _execution_history
    if domain and domain != "all":
        filtered = [e for e in filtered if e.task_domain.value == domain]
    if memory_mode and memory_mode != "all":
        filtered = [e for e in filtered if e.memory_mode.value == memory_mode]

    total = len(filtered)
    page_items = filtered[offset : offset + limit]

    return {
        "total": total,
        "items": [item.model_dump(by_alias=True) for item in page_items],
    }


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
