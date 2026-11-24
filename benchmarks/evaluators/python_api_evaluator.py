"""
Python API Evolution Benchmark Independent Evaluator.

Executes candidate Python code against frozen pytest test suites inside isolated temporary directories.
- Real subprocess invocation of sys.executable -m pytest.
- Strict exit code verification: returncode == 0 for pass, returncode != 0 for fail.
- Captures stdout, stderr, and detects specific API deprecation/attribute exceptions.
- Zero length scoring, zero condition favoritism, zero trial-index awareness.
"""

import logging
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

from benchmarks.evaluators.base import BaseBenchmarkEvaluator, EvaluationOutcome

logger = logging.getLogger("benchmarks.evaluators.python_api")


def extract_python_code(text: str) -> str:
    """Extract Python source code from markdown code blocks or return clean text."""
    if not text:
        return ""

    # Search for ```python ... ``` code blocks
    matches = re.findall(r"```(?:python)?\s*([\s\S]*?)\s*```", text)
    if matches:
        # Return the largest code block
        return max(matches, key=len).strip()

    return text.strip()


class PythonAPIEvolutionEvaluator(BaseBenchmarkEvaluator):
    """
    Independent execution evaluator for Python API Evolution tasks.
    Runs candidate code with pytest in a dedicated subprocess.
    """

    def __init__(self, timeout_sec: float = 10.0):
        self.timeout_sec = timeout_sec

    @property
    def name(self) -> str:
        return "PythonAPIEvolutionEvaluator"

    @property
    def version(self) -> str:
        return "1.0.0"

    def evaluate(
        self,
        task: Dict[str, Any],
        agent_output: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        trajectory: Optional[List[Any]] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationOutcome:
        task_id = str(task.get("id", "api_task"))
        test_suite_code = task.get("test_suite", "")
        if not test_suite_code:
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason="missing_test_suite_in_task",
            )

        code = extract_python_code(agent_output)
        if not code:
            return EvaluationOutcome(
                score=0.0,
                passed=False,
                evaluator_name=self.name,
                evaluator_version=self.version,
                failure_reason="no_python_code_extracted_from_output",
            )

        # Isolated directory for execution
        with tempfile.TemporaryDirectory(prefix=f"api_eval_{task_id}_") as tmpdir:
            tmppath = Path(tmpdir)
            solution_file = tmppath / "solution.py"
            test_file = tmppath / "test_suite.py"

            solution_file.write_text(code, encoding="utf-8")
            test_file.write_text(test_suite_code, encoding="utf-8")

            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", "--tb=short", str(test_file)],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                )
                exec_time_ms = (time.perf_counter() - t0) * 1000.0
                stdout = proc.stdout
                stderr = proc.stderr
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                exec_time_ms = self.timeout_sec * 1000.0
                return EvaluationOutcome(
                    score=0.0,
                    passed=False,
                    evaluator_name=self.name,
                    evaluator_version=self.version,
                    failure_reason=f"pytest_execution_timeout_after_{self.timeout_sec}s",
                    metrics={"returncode": -1, "exec_time_ms": exec_time_ms},
                )
            except Exception as e:
                return EvaluationOutcome(
                    score=0.0,
                    passed=False,
                    evaluator_name=self.name,
                    evaluator_version=self.version,
                    failure_reason=f"subprocess_invocation_error: {str(e)}",
                )

        passed = (returncode == 0)
        score = 1.0 if passed else 0.0

        # Detect specific runtime error pattern in stdout/stderr
        detected_exception = None
        expected_runtime_exc = task.get("runtime_exception")
        full_output = f"{stdout}\n{stderr}"
        if "AttributeError" in full_output:
            detected_exception = "AttributeError"
        elif "PydanticUserError" in full_output or "ValidationError" in full_output:
            detected_exception = "PydanticError"
        elif "SyntaxError" in full_output:
            detected_exception = "SyntaxError"

        failure_reason = None
        if not passed:
            lines = [l for l in full_output.splitlines() if l.strip()]
            summary_line = lines[-1] if lines else "pytest returned non-zero exit status"
            failure_reason = f"pytest_failed: {summary_line}"

        metrics = {
            "returncode": returncode,
            "exec_time_ms": round(exec_time_ms, 2),
            "detected_exception": detected_exception,
            "matched_expected_deprecated_exception": bool(
                expected_runtime_exc and expected_runtime_exc in full_output
            ),
        }

        return EvaluationOutcome(
            score=score,
            passed=passed,
            evaluator_name=self.name,
            evaluator_version=self.version,
            metrics=metrics,
            failure_reason=failure_reason,
            details={
                "task_id": task_id,
                "stdout": stdout[:2000],
                "stderr": stderr[:2000],
            },
        )
