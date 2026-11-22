"""
Base benchmark evaluation contract for independent, objective verification.

Enforces:
1. Evaluator has zero access to experimental condition names (e.g., adaptive vs vanilla).
2. Evaluator has zero access to trial counters (e.g., trial 2 cannot force success).
3. Evaluator never awards points for response length, tool invocation counts, or memory presence.
4. Continuous score and discrete binary pass/fail are both explicitly returned.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvaluationOutcome:
    """Immutable result of an independent benchmark evaluation."""
    score: float
    passed: bool
    evaluator_name: str
    evaluator_version: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "evaluator_name": self.evaluator_name,
            "evaluator_version": self.evaluator_version,
            "metrics": self.metrics,
            "failure_reason": self.failure_reason,
            "details": self.details,
        }


class BaseBenchmarkEvaluator(ABC):
    """Abstract interface that all research-grade benchmark evaluators must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the benchmark evaluator."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version of the evaluator."""
        pass

    @abstractmethod
    def evaluate(
        self,
        task: Dict[str, Any],
        agent_output: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        trajectory: Optional[List[Any]] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationOutcome:
        """
        Evaluate an agent's output against the benchmark task specifications.
        
        Note:
            Must NOT accept condition_name or trial parameters to prevent
            evaluation bias.
        """
        pass
