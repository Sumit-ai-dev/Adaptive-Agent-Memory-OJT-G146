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
from typing import Any, Dict, List, Optional

logger = logging.getLogger("benchmarks.alfworld")


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
