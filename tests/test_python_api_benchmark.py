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

from ai_service.nodes.reflect_node import (
    normalize_reflection_confidence,
    normalize_reflection_payload,
    normalize_reflection_text,
)
from benchmarks.evaluators.python_api_evaluator import (
    extract_python_code,
    PythonAPIEvolutionEvaluator,
)
from benchmarks.python_api_runner import (
    CONDITION_MODE_MAP,
    load_api_evolution_tasks,
    MANIFEST_PATH,
    PythonAPIEvolutionSession,
    seed_outdated_api_memory,
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


class TestPythonAPIEvolutionSQLiteIsolation:
    """Regression tests for Issue 1: SQLite database isolation across conditions and trials."""

    @pytest.mark.asyncio
    async def test_sqlite_isolation_across_repeated_trials(self):
        """Repeated trials on the same task ID obtain independently isolated databases."""
        import os
        from models.domain import ExperienceStatus, TaskDomain
        from models.experience import Experience

        task = {"id": "pandas_append_01", "library": "pandas"}

        # Trial 1 session
        session1 = PythonAPIEvolutionSession(
            condition_name="adaptive",
            task_id="pandas_append_01",
            trial=1,
        )
        temp_dir1 = session1._temp_dir.name
        db_path1 = session1.db_path
        assert os.path.exists(temp_dir1)
        assert os.path.exists(db_path1)

        # Seed memory into session 1
        await seed_outdated_api_memory(session1.store, task)
        memories1 = await session1.store.list_experiences(domain=TaskDomain.CODING)
        assert len(memories1) == 1
        assert "legacy_pandas_append_01" in memories1[0].id

        # Trial 2 session: must be completely independent
        session2 = PythonAPIEvolutionSession(
            condition_name="adaptive",
            task_id="pandas_append_01",
            trial=2,
        )
        temp_dir2 = session2._temp_dir.name
        db_path2 = session2.db_path

        assert temp_dir1 != temp_dir2
        assert db_path1 != db_path2

        # Session 2 must be clean and not have session 1's seeded memory
        memories2 = await session2.store.list_experiences(domain=TaskDomain.CODING)
        assert len(memories2) == 0

        # Close session 1: WAL truncation and safe removal of temp dir
        session1.close()
        assert session1._temp_dir is None
        assert not os.path.exists(temp_dir1), f"Temp dir {temp_dir1} should have been unlinked"

        # Session 2 must remain functional and accessible
        await seed_outdated_api_memory(session2.store, task)
        memories2_after = await session2.store.list_experiences(domain=TaskDomain.CODING)
        assert len(memories2_after) == 1

        session2.close()
        assert not os.path.exists(temp_dir2)

    def test_context_manager_cleanup(self):
        """Using PythonAPIEvolutionSession as a context manager safely cleans up."""
        import os

        with PythonAPIEvolutionSession(condition_name="vanilla", task_id="cm_test", trial=1) as s:
            temp_path = s._temp_dir.name
            db_path = s.db_path
            assert os.path.exists(temp_path)
            assert os.path.exists(db_path)

        assert not os.path.exists(temp_path)

    def test_cleanup_failure_not_silently_ignored(self, monkeypatch):
        """If directory cleanup fails with an unresolvable error, it raises RuntimeError rather than silently passing."""
        import shutil

        session = PythonAPIEvolutionSession(condition_name="adaptive", task_id="fail_test", trial=1)
        temp_dir_obj = session._temp_dir

        def mock_cleanup_fail():
            raise PermissionError("Access denied on Windows")

        def mock_rmtree_fail(path, ignore_errors=False):
            raise OSError("Critical file lock")

        monkeypatch.setattr(temp_dir_obj, "cleanup", mock_cleanup_fail)
        monkeypatch.setattr(shutil, "rmtree", mock_rmtree_fail)

        with pytest.raises(RuntimeError, match="Failed to clean up isolated benchmark database"):
            session.close()


class TestReflectionPipelineTypeSafety:
    """Regression tests for Issue 2: Reflection pipeline type safety and nested dictionary normalization."""

    def test_reflection_string_type(self):
        """Plain string fields remain clean and unchanged."""
        parsed = {
            "trigger_condition": "Tasks involving pandas dataframe operations",
            "strategy_lesson": "Use pd.concat([df1, df2]) instead of df.append()",
            "pitfall": "Do not call DataFrame.append in pandas >= 2.0",
            "confidence": 0.90,
        }
        res = normalize_reflection_payload(parsed, task_input="Combine dataframes", domain="coding")
        assert res["trigger_condition"] == "Tasks involving pandas dataframe operations"
        assert res["strategy_lesson"] == "Use pd.concat([df1, df2]) instead of df.append()"
        assert res["pitfall"] == "Do not call DataFrame.append in pandas >= 2.0"
        assert res["confidence"] == 0.90

        # Slicing operates cleanly without error
        assert res["strategy_lesson"][:70] == "Use pd.concat([df1, df2]) instead of df.append()"

    def test_reflection_dictionary_type(self):
        """Single-level dictionaries are normalized into human-readable strings without raw dict syntax."""
        parsed = {
            "trigger_condition": {"operation": "concatenation", "library": "pandas"},
            "strategy_lesson": {"action": "Use pd.concat", "reason": "append was deprecated"},
            "pitfall": {"avoid": "DataFrame.append", "consequence": "AttributeError in 2.0"},
            "confidence": 0.85,
        }
        res = normalize_reflection_payload(parsed, task_input="Combine dfs", domain="coding")
        assert isinstance(res["strategy_lesson"], str)
        assert isinstance(res["trigger_condition"], str)
        assert isinstance(res["pitfall"], str)

        assert "Action: Use pd.concat" in res["strategy_lesson"]
        assert "Reason: append was deprecated" in res["strategy_lesson"]
        assert "{" not in res["strategy_lesson"]
        assert "}" not in res["strategy_lesson"]

        # Slicing works without KeyError: slice(None, 70, None)
        assert len(res["strategy_lesson"][:70]) <= 70

    def test_reflection_nested_dictionary_type(self):
        """Deeply nested dictionaries are safely flattened and formatted."""
        parsed = {
            "trigger_condition": {
                "scope": {"module": "pandas", "class": "DataFrame"},
                "trigger": "Appending rows",
            },
            "strategy_lesson": {
                "recommendation": {"action": "Use pd.concat", "method": "concat"},
                "rationale": "DataFrame.append removed in pandas 2.0",
            },
            "pitfall": {
                "error_details": {"name": "AttributeError", "msg": "DataFrame has no attribute append"},
            },
            "confidence": 0.95,
        }
        res = normalize_reflection_payload(parsed, task_input="Combine dfs", domain="coding")
        assert isinstance(res["strategy_lesson"], str)
        assert isinstance(res["trigger_condition"], str)
        assert isinstance(res["pitfall"], str)

        assert "Action: Use pd.concat" in res["strategy_lesson"]
        assert "Rationale: DataFrame.append removed in pandas 2.0" in res["strategy_lesson"]
        assert "{" not in res["strategy_lesson"]

    def test_reflection_actual_llama3_output(self):
        """Actual Llama 3.1 8B output with nested structures and string confidence parses safely."""
        llama3_json = {
            "trigger_condition": {
                "context": "Python data manipulation",
                "trigger": "Appending rows to a DataFrame",
            },
            "strategy_lesson": {
                "action": "Use pandas.concat([df1, df2]) to combine DataFrames along rows or columns.",
                "rationale": "DataFrame.append was deprecated in version 1.4.0 and removed in pandas 2.0.",
            },
            "pitfall": {
                "error": "AttributeError: 'DataFrame' object has no attribute 'append'",
                "warning": "Do not attempt to call append on DataFrame instances",
            },
            "confidence": "high",
        }
        res = normalize_reflection_payload(llama3_json, task_input="Append to df", domain="coding")

        # Crucial slice test that previously crashed with KeyError: slice(None, 70, None)
        strat_slice = res["strategy_lesson"][:70]
        pit_slice = res["pitfall"][:70]
        assert len(strat_slice) <= 70
        assert len(pit_slice) <= 70

        # Verify confidence string normalized to valid float
        assert isinstance(res["confidence"], float)
        assert res["confidence"] == 0.85

        # Verify compatibility with domain Experience model
        from models.domain import TaskDomain
        from models.experience import Experience, ExperienceStatus

        exp = Experience(
            task_domain=TaskDomain.CODING,
            trigger_condition=res["trigger_condition"],
            strategy_lesson=res["strategy_lesson"],
            pitfall=res["pitfall"],
            confidence=res["confidence"],
            status=ExperienceStatus.CANDIDATE,
        )
        assert exp.strategy_lesson == res["strategy_lesson"]
        assert exp.confidence == 0.85

    def test_reflection_null_and_missing_values(self):
        """Null, empty, and missing values fall back to safe defaults without raising exceptions."""
        parsed_nulls = {
            "trigger_condition": None,
            "strategy_lesson": None,
            "pitfall": None,
            "confidence": None,
        }
        res = normalize_reflection_payload(parsed_nulls, task_input="Some task input", domain="coding")
        assert isinstance(res["strategy_lesson"], str)
        assert len(res["strategy_lesson"]) > 0
        assert isinstance(res["trigger_condition"], str)
        assert len(res["trigger_condition"]) > 0
        assert isinstance(res["pitfall"], str)
        assert len(res["pitfall"]) > 0
        assert isinstance(res["confidence"], float)
        assert res["confidence"] == 0.85

        # Empty dict
        res_empty = normalize_reflection_payload({}, task_input="", domain="general")
        assert isinstance(res_empty["strategy_lesson"], str)
        assert res_empty["confidence"] == 0.85

    def test_reflection_root_wrapper_unwrapping(self):
        """JSON output wrapped in root objects (e.g. {'reflection': ...}) is automatically unwrapped."""
        wrapped = {
            "reflection": {
                "trigger_condition": "SQLAlchemy execute queries",
                "strategy_lesson": "Use conn.execute(text('SELECT 1'))",
                "pitfall": "Do not pass bare string SQL to connection.execute() in SQLAlchemy 2.0",
                "confidence": 0.92,
            }
        }
        res = normalize_reflection_payload(wrapped, task_input="SQLAlchemy query", domain="coding")
        assert res["trigger_condition"] == "SQLAlchemy execute queries"
        assert res["strategy_lesson"] == "Use conn.execute(text('SELECT 1'))"
        assert res["confidence"] == 0.92
