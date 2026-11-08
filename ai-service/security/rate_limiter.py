"""
In-Memory Sliding-Window Rate Limiter.
Defends against endpoint flooding, token exhaustion attacks, and DoS.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Tuple

logger = logging.getLogger("ai_service.security.rate_limiter")


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter per client IP."""

    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(
        self, client_ip: str, max_requests: int = 60, window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Determines whether client_ip is permitted to execute a request.
        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        with self._lock:
            timestamps = self._requests.get(client_ip, [])
            cutoff = now - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(earliest + window_seconds - now) + 1)
                return False, retry_after

            valid_timestamps.append(now)
            self._requests[client_ip] = valid_timestamps
            return True, 0

    def reset(self) -> None:
        """Clears all tracking windows."""
        with self._lock:
            self._requests.clear()


# Global singleton rate limiter instance
rate_limiter = SlidingWindowRateLimiter()

