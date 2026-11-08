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
    """Sliding-window rate limiter per client IP with bounded memory eviction."""

    def __init__(self, max_tracked_ips: int = 5000):
        """Initializes the thread-safe rate limiter and eviction parameters."""
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self.max_tracked_ips = max_tracked_ips

    def check(
        self, client_ip: str, max_requests: int = 60, window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Determines whether client_ip is permitted to execute a request.
        Safely handles non-positive limits and purges expired client state.
        Returns (allowed, retry_after_seconds).
        """
        if max_requests <= 0:
            return False, max(1, window_seconds)

        client_ip = (client_ip or "unknown").strip()
        now = time.time()
        with self._lock:
            # Active bounded eviction when tracking pool reaches or exceeds capacity
            if len(self._requests) >= self.max_tracked_ips and client_ip not in self._requests:
                cutoff_global = now - window_seconds
                stale_ips = [
                    ip for ip, reqs in self._requests.items()
                    if not reqs or reqs[-1] <= cutoff_global
                ]
                for ip in stale_ips:
                    del self._requests[ip]

                # If all tracked IPs are active and capacity is still saturated,
                # evict the oldest entries to strictly enforce the hard memory bound.
                if len(self._requests) >= self.max_tracked_ips:
                    target_size = max(1, int(self.max_tracked_ips * 0.8))
                    num_to_remove = len(self._requests) - target_size + 1
                    oldest_ips = sorted(
                        self._requests.keys(),
                        key=lambda k: self._requests[k][-1] if self._requests[k] else 0.0,
                    )[:num_to_remove]
                    for ip in oldest_ips:
                        self._requests.pop(ip, None)

            timestamps = self._requests.get(client_ip, [])
            cutoff = now - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0] if valid_timestamps else now
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
