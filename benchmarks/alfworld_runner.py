"""
ALFWorld Embodied Decision-Making Benchmark Runner.

AUDIT NOTICE (November 22, 2026):
Historical versions of this runner used trial-index success overrides and synthetic token multipliers
without running inside a live ALFWorld / TextWorld interactive environment.

In compliance with the Scientific Integrity Mandate:
- All synthetic trial-index success logic has been completely removed.
- Execution requires a genuine interactive ALFWorld environment.
- When the 'alfworld' or 'textworld' package is not installed, this runner is explicitly disabled.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("benchmarks.alfworld")

ALFWORLD_DATA_DIR = Path(__file__).parent / "data" / "alfworld" / "json_2.1.1" / "valid_seen"


def load_alfworld_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    """Loads offline trajectory metadata for ALFWorld tasks if available."""
    if not ALFWORLD_DATA_DIR.exists():
        alt_path = Path(__file__).parent / "data" / "alfworld"
        paths = list(alt_path.rglob("traj_data.json")) if alt_path.exists() else []
    else:
        paths = list(ALFWORLD_DATA_DIR.rglob("traj_data.json"))

    tasks: List[Dict[str, Any]] = []
    for p in paths[:limit]:
        try:
            import json
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            desc = d.get("turk_annotations", {}).get("anns", [{}])[0].get("task_desc", "")
            if not desc and "pddl_params" in d:
                desc = f"{d.get('task_type')}: {d.get('pddl_params', {}).get('object_target', '')}"
            tasks.append({
                "id": d.get("task_id", p.parent.name),
                "task_type": d.get("task_type", "general"),
                "goal": desc,
                "plan": [step.get("discrete_action", {}).get("action", "") for step in d.get("plan", {}).get("high_pddl", [])],
            })
        except Exception as e:
            logger.warning(f"Failed to load ALFWorld task at {p}: {e}")
    return tasks


def is_alfworld_available() -> bool:
    """Check if the real ALFWorld simulation environment is installed."""
    try:
        import alfworld  # type: ignore # noqa: F401
        return True
    except ImportError:
        return False


async def run_alfworld_trial(*args, **kwargs) -> Dict[str, Any]:
    if not is_alfworld_available():
        raise NotImplementedError(
            "ALFWorld runner is disabled: The genuine ALFWorld / TextWorld simulation environment "
            "is not installed in the local environment. Per scientific audit mandate, synthetic simulation "
            "without an interactive environment is strictly forbidden."
        )
    raise NotImplementedError("Live interactive ALFWorld harness integration in progress.")


async def run_alfworld_benchmark(
    tasks_limit: int = 5,
    conditions: Optional[List[str]] = None,
    max_trials: int = 3,
    telemetry_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not is_alfworld_available():
        logger.error(
            "ALFWorld benchmark skipped: Genuine 'alfworld' package is not installed. "
            "To prevent fabricated results, the runner will not simulate execution."
        )
        print(
            "\n[ALFWorld] SKIPPED: Genuine 'alfworld' simulation environment is not installed. "
            "Simulated / hardcoded runs are strictly disabled per scientific integrity policy."
        )
        return []
    raise NotImplementedError("Live interactive ALFWorld harness integration in progress.")
