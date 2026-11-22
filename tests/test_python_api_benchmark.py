"""
Unit and Integration Tests for AEMA Python API Evolution Benchmark.

Verifies:
1. Manifest integrity (valid tasks, version constraints, test suites).
2. Real pytest execution via PythonAPIEvolutionEvaluator.
3. Modern API implementation passes pytest (score = 1.0).
4. Outdated API implementation fails pytest with real Python runtime exceptions (score = 0.0).
5. All 5 memory baseline modes are supported.
"""

import importlib.util
import json
import pytest

from benchmarks.evaluators.python_api_evaluator import (
    extract_python_code,
    PythonAPIEvolutionEvaluator,
)
from benchmarks.python_api_runner import (
    CONDITION_MODE_MAP,
    load_api_evolution_tasks,
    MANIFEST_PATH,
)
from models.domain import MemoryMode


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


has_pandas = pytest.mark.skipif(
    not _has_module("pandas"),
    reason="pandas is not installed in the test execution environment",
)
has_sqlalchemy = pytest.mark.skipif(
    not _has_module("sqlalchemy"),
    reason="sqlalchemy is not installed in the test execution environment",
)


class TestPythonAPIEvolutionManifest:
    def test_manifest_loads(self):
        """Manifest file exists and loads valid tasks."""
        tasks = load_api_evolution_tasks(limit=10)
        assert len(tasks) >= 5, "Expected at least 5 curated API evolution tasks."

        required_keys = [
            "id",
            "category",
            "library",
            "old_version",
            "new_version",
            "breaking_change",
            "test_suite",
            "problem_description",
            "reference_modern_code",
            "outdated_code",
        ]
        for t in tasks:
            for k in required_keys:
                assert k in t, f"Task {t.get('id')} missing required key '{k}'"

    def test_condition_mode_map(self):
        """All 5 memory conditions are mapped correctly."""
        assert CONDITION_MODE_MAP["vanilla"] == MemoryMode.OFF
        assert CONDITION_MODE_MAP["naive_rag"] == MemoryMode.NAIVE
        assert CONDITION_MODE_MAP["recency"] == MemoryMode.RECENCY
        assert CONDITION_MODE_MAP["symmetric"] == MemoryMode.SYMMETRIC
        assert CONDITION_MODE_MAP["adaptive"] == MemoryMode.ADAPTIVE


class TestPythonAPIEvaluator:
    @pytest.fixture
    def pandas_append_task(self):
        tasks = load_api_evolution_tasks(limit=10)
        return next(t for t in tasks if t["id"] == "api_pandas_01_append_concat")

    @pytest.fixture
    def pandas_iteritems_task(self):
        tasks = load_api_evolution_tasks(limit=10)
        return next(t for t in tasks if t["id"] == "api_pandas_02_series_iteritems")

    @pytest.fixture
    def sqlalchemy_task(self):
        tasks = load_api_evolution_tasks(limit=10)
        return next(t for t in tasks if t["id"] == "api_sqlalchemy_01_engine_execute")

    def test_extract_python_code(self):
        """Code block extraction handles markdown and raw code."""
        md = "Here is the solution:\n```python\ndef foo(): return 42\n```\nDone."
        assert extract_python_code(md) == "def foo(): return 42"

        raw = "def bar(): return 100"
        assert extract_python_code(raw) == "def bar(): return 100"

    @has_pandas
    def test_pandas_append_modern_passes(self, pandas_append_task):
        """Modern pd.concat implementation passes real pytest test suite."""
        evaluator = PythonAPIEvolutionEvaluator()
        code = pandas_append_task["reference_modern_code"]

        outcome = evaluator.evaluate(pandas_append_task, f"```python\n{code}\n```")
        assert outcome.passed is True
        assert outcome.score == 1.0
        assert outcome.metrics["returncode"] == 0

    @has_pandas
    def test_pandas_append_outdated_fails_with_attribute_error(self, pandas_append_task):
        """Outdated df.append implementation fails real pytest with AttributeError."""
        evaluator = PythonAPIEvolutionEvaluator()
        code = pandas_append_task["outdated_code"]

        outcome = evaluator.evaluate(pandas_append_task, f"```python\n{code}\n```")
        assert outcome.passed is False
        assert outcome.score == 0.0
        assert outcome.metrics["returncode"] != 0
        assert outcome.metrics["detected_exception"] == "AttributeError"
        assert "has no attribute 'append'" in outcome.details["stdout"]

    @has_pandas
    def test_pandas_iteritems_outdated_fails(self, pandas_iteritems_task):
        """Outdated Series.iteritems implementation fails on Pandas 2.x."""
        evaluator = PythonAPIEvolutionEvaluator()
        code = pandas_iteritems_task["outdated_code"]

        outcome = evaluator.evaluate(pandas_iteritems_task, code)
        assert outcome.passed is False
        assert outcome.score == 0.0
        assert outcome.metrics["detected_exception"] == "AttributeError"
        assert "has no attribute 'iteritems'" in outcome.details["stdout"]

    @has_sqlalchemy
    def test_sqlalchemy_modern_passes(self, sqlalchemy_task):
        """Modern SQLAlchemy 2.0 connection execution passes."""
        evaluator = PythonAPIEvolutionEvaluator()
        code = sqlalchemy_task["reference_modern_code"]

        outcome = evaluator.evaluate(sqlalchemy_task, code)
        assert outcome.passed is True
        assert outcome.score == 1.0

    @has_sqlalchemy
    def test_sqlalchemy_outdated_fails(self, sqlalchemy_task):
        """Legacy Engine.execute fails on SQLAlchemy 2.0 with AttributeError."""
        evaluator = PythonAPIEvolutionEvaluator()
        code = sqlalchemy_task["outdated_code"]

        outcome = evaluator.evaluate(sqlalchemy_task, code)
        assert outcome.passed is False
        assert outcome.score == 0.0
        assert outcome.metrics["detected_exception"] == "AttributeError"
        assert "has no attribute 'execute'" in outcome.details["stdout"]

    def test_syntax_error_fails_cleanly(self):
        """Syntax errors fail cleanly without unhandled crashes."""
        evaluator = PythonAPIEvolutionEvaluator()
        task = {
            "id": "test_pure_python_syntax",
            "test_suite": "import solution\ndef test_noop(): assert solution.broken_fn()\n",
        }
        broken_code = "def broken_fn(): return 1 +++ syntax error"

        outcome = evaluator.evaluate(task, broken_code)
        assert outcome.passed is False
        assert outcome.score == 0.0
        assert outcome.metrics["detected_exception"] == "SyntaxError"
