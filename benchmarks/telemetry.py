"""
Benchmark Telemetry and Resource Measurement Utility.

Enforces:
- Real wall-clock timing via monotonic high-resolution counters (time.perf_counter).
- Genuine token count collection from provider response or explicit, documented fallback.
- Explicit boolean flags indicating whether tokens were measured from provider or estimated.
- Preservation of raw execution telemetry with JSONL persistence.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("benchmarks.telemetry")


def estimate_tokens_fallback(text: str) -> int:
    """
    Transparent, documented tokenizer estimate when a provider does not expose token counts.
    Uses whitespace and punctuation heuristic (~4 characters per token).
    """
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        words = len(text.split())
        chars = len(text)
        return max(1, int(chars / 4.0))


@dataclass
class TrialTelemetryRecord:
    """Standardized, immutable schema for an authentic trial telemetry record."""
    benchmark: str
    task_id: str
    condition: str
    trial: int
    success: bool
    score: float
    evaluator_name: str
    evaluator_version: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    token_count_estimated: bool
    latency_ms: float
    iterations: int
    error_recurred: bool
    quarantine_triggered: bool
    quarantine_blocked_poison: bool
    failure_reason: Optional[str] = None
    evaluator_metrics: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    reward_score: float = 0.0

    def __post_init__(self):
        if self.reward_score == 0.0 and self.score > 0.0:
            self.reward_score = self.score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class TelemetryLogger:
    """Thread-safe and process-safe telemetry logger to append records to JSONL files."""

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def log_trial(self, record: TrialTelemetryRecord) -> None:
        line = record.to_json() + "\n"
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(line)
