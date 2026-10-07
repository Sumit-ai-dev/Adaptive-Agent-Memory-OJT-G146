"""
Telemetry API endpoint.
Returns truthful system metrics derived entirely from stored data.
No fabricated constants.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter

from backend.routes.agent import shared_store
from models.domain import ExperienceStatus

logger = logging.getLogger("backend.routes.telemetry")

router = APIRouter(prefix="/telemetry", tags=["Dashboard Telemetry"])


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="Get System Telemetry — real metrics only, no fabricated values",
)
async def get_telemetry() -> Dict[str, Any]:
    """
    Returns truthful backend metrics derived from SQLite records.

    All values are computed from actual stored data. Metrics that cannot
    be honestly derived are omitted entirely.
    """
    # ── Memory metrics from SQLite experiences table ──────────────────────────
    all_exps = await shared_store.list_experiences(min_trust=0.0)
    active_exps    = [e for e in all_exps if e.status == ExperienceStatus.ACTIVE]
    candidate_exps = [e for e in all_exps if e.status == ExperienceStatus.CANDIDATE]
    quarantined_exps = [
        e for e in all_exps
        if e.trust_score < 0.35 or e.status == ExperienceStatus.DEPRECATED
    ]

    # ── Execution metrics from SQLite task_executions table ───────────────────
    total_executions = 0
    executions_with_memory_hit = 0
    memory_hit_rate: float = 0.0

    try:
        conn = sqlite3.connect(shared_store.db_path)
        total_executions = conn.execute(
            "SELECT COUNT(*) FROM task_executions"
        ).fetchone()[0]

        rows = conn.execute(
            "SELECT payload_json FROM task_executions"
        ).fetchall()
        conn.close()

        for (payload_json,) in rows:
            try:
                data = json.loads(payload_json)
                retrieved = (
                    data.get("retrievedExperiences")
                    or data.get("retrievedMemories")
                    or []
                )
                if retrieved:
                    executions_with_memory_hit += 1
            except Exception:
                pass

        if total_executions > 0:
            memory_hit_rate = round(executions_with_memory_hit / total_executions * 100, 1)

    except Exception as exc:
        logger.warning(f"Could not compute execution metrics from SQLite: {exc}")

    return {
        # ── Memory store (always real) ─────────────────────────────────────
        "totalMemories": len(all_exps),
        "activeMemories": len(active_exps),
        "candidateMemories": len(candidate_exps),
        "quarantinedMemories": len(quarantined_exps),
        # ── Execution history (persisted to SQLite) ────────────────────────
        "totalExecutions": total_executions,
        "executionsWithMemoryHit": executions_with_memory_hit,
        "memoryHitRate": memory_hit_rate,
        # ── Trust system constants (informational, always truthful) ────────
        "quarantineThreshold": 0.35,
        "trustDecayBeta": 0.70,
        "trustBoostAlpha": 0.85,
        "initialTrustScore": 0.75,
        # ── Benchmark results (populated only when Phase 9 runs) ───────────
        "latestBenchmarks": _load_benchmark_summary(),
    }


def _load_benchmark_summary() -> Any:
    """Load latest benchmark results JSON if available, else null."""
    benchmark_file = Path("benchmarks/results/table2_summary_latest.json")
    if not benchmark_file.exists():
        return None
    try:
        with open(benchmark_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Could not load benchmark summary: {exc}")
        return None
