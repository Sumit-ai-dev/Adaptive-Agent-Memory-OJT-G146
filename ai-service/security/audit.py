"""
Security Event Audit Logger and Telemetry Tracking.
Records security-relevant events, blocked execution attempts, and policy violations
to maintain security observability across agent workflows.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai_service.security.audit")


class SecurityAuditLogger:
    """Thread-safe in-memory security audit log with metric counters."""

    def __init__(self, max_records: int = 500):
        self._max_records = max_records
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "total_security_events": 0,
            "blocked_code_executions": 0,
            "unauthorized_access_attempts": 0,
            "rate_limit_exceeded_count": 0,
            "prompt_injection_flags": 0,
        }

    def record_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> None:
        """Appends a new security event and increments associated metrics."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "client_ip": client_ip or "unknown",
            "details": details,
        }

        with self._lock:
            self._counters["total_security_events"] += 1
            if event_type == "BLOCKED_CODE_EXECUTION":
                self._counters["blocked_code_executions"] += 1
            elif event_type in ("UNAUTHORIZED_ACCESS", "AUTHENTICATION_FAILURE"):
                self._counters["unauthorized_access_attempts"] += 1
            elif event_type == "RATE_LIMIT_EXCEEDED":
                self._counters["rate_limit_exceeded_count"] += 1
            elif event_type == "PROMPT_INJECTION_DETECTED":
                self._counters["prompt_injection_flags"] += 1

            self._events.insert(0, record)
            if len(self._events) > self._max_records:
                self._events.pop()

        logger.warning(
            f"[SECURITY EVENT] type={event_type} severity={severity} ip={client_ip} details={details}"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Returns aggregate security metrics and recent event count."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "recentEventCount": len(self._events),
                "lastEventTimestamp": self._events[0]["timestamp"] if self._events else None,
            }

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent security events, up to limit."""
        with self._lock:
            return list(self._events[:limit])


# Global singleton audit instance
security_audit_logger = SecurityAuditLogger()

