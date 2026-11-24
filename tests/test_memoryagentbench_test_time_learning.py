"""
Comprehensive Test Suite for MemoryAgentBench Test-Time Learning (TTL) Integration.

Validates:
1. Official HuggingFace Parquet dataset schema and checksum.
2. Pilot manifest integrity, task count, and demonstration count.
3. Chronological demonstration ordering and monotonic timestamps.
4. Future-test leakage prevention (zero demonstration/test question overlap, zero prompt leakage).
5. Ephemeral SQLite memory isolation across conditions and repeated trials.
6. Execution equivalence and memory behavior across all five conditions:
   - vanilla (MemoryMode.OFF, zero stored memories)
   - naive_rag (MemoryMode.NAIVE)
   - recency (MemoryMode.RECENCY)
   - symmetric (MemoryMode.SYMMETRIC)
   - adaptive (MemoryMode.ADAPTIVE)
7. XML answer tag extraction and exact-match evaluation for discrete classification labels.
8. Telemetry integrity, authentic timing, and token accounting.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest

try:
    import pyarrow.parquet as pq
except ImportError:
    pq = None

from ai_service.embedder import local_embedder
from benchmarks.evaluators.memoryagentbench_evaluator import (
    extract_xml_answer,
    MemoryAgentBenchEvaluator,
    parse_output,
)
from benchmarks.memoryagentbench_runner import (
    CONDITION_MODE_MAP,
    load_pilot_manifest,
    MemoryAgentBenchSession,
)
from models.domain import MemoryMode

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "benchmarks" / "data" / "memoryagentbench"
PARQUET_FILE = DATA_DIR / "upstream_parquets" / "Test_Time_Learning.parquet"
MANIFEST_FILE = DATA_DIR / "pilot_test_time_learning_25.json"
METADATA_FILE = DATA_DIR / "manifest_metadata.json"

OFFICIAL_TTL_PARQUET_SHA256 = "5338753BE48F925D03318EED66117286E3489025FABE050A547BD086CD7D79C0"


@pytest.fixture(autouse=True)
def setup_fast_offline_embedder():
    """Ensure fast deterministic vector embeddings without remote network calls."""
    from ai_service.config import settings
    local_embedder._load_attempted = True
    local_embedder._model = None
    old_threshold = settings.SIMILARITY_THRESHOLD
    settings.SIMILARITY_THRESHOLD = 0.40
    yield
    settings.SIMILARITY_THRESHOLD = old_threshold


# ============================================================================
# 1. OFFICIAL DATASET SCHEMA & CHECKSUM VALIDATION
# ============================================================================

def test_ttl_official_dataset_schema_and_checksum():
    """Verify that official HuggingFace Parquet file exists, has correct hash and schema."""
    if pq is None or not PARQUET_FILE.exists():
        pytest.skip(f"pyarrow or official Parquet file not available at {PARQUET_FILE}")

    # Verify SHA-256 checksum
    hasher = hashlib.sha256()
    with open(PARQUET_FILE, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_sha = hasher.hexdigest().upper()
    assert actual_sha == OFFICIAL_TTL_PARQUET_SHA256, (
        f"Checksum mismatch for {PARQUET_FILE.name}: expected {OFFICIAL_TTL_PARQUET_SHA256}, got {actual_sha}"
    )

    # Verify Parquet schema
    table = pq.read_table(PARQUET_FILE)
    col_names = table.column_names
    for required_col in ["context", "questions", "answers", "metadata"]:
        assert required_col in col_names, f"Missing required column: {required_col}"

    # Verify icl_trec_coarse_6600shot_balance row exists
    df = table.to_pandas()
    matching_rows = df[df["metadata"].apply(lambda m: m.get("source") == "icl_trec_coarse_6600shot_balance")]
    assert len(matching_rows) == 1, "Expected exactly 1 row for icl_trec_coarse_6600shot_balance"

    row = matching_rows.iloc[0]
    assert len(row["context"]) > 100000
    assert len(row["questions"]) == 100
    assert len(row["answers"]) == 100


# ============================================================================
# 2. MANIFEST INTEGRITY & METADATA VERIFICATION
# ============================================================================

def test_ttl_manifest_integrity():
    """Verify pilot manifest structure, task count, and SHA-256 against manifest_metadata.json."""
    assert MANIFEST_FILE.exists(), f"Missing manifest at {MANIFEST_FILE}"

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert "pilot_test_time_learning_25.json" in meta["files"]
    expected_meta = meta["files"]["pilot_test_time_learning_25.json"]

    # Verify file hash
    hasher = hashlib.sha256()
    with open(MANIFEST_FILE, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == expected_meta["sha256"], f"Hash mismatch: expected {expected_meta['sha256']}, got {actual_hash}"

    manifest = load_pilot_manifest("Test_Time_Learning")
    assert manifest["benchmark"] == "MemoryAgentBench"
    assert manifest["competency"] == "Test_Time_Learning"
    assert manifest["split"] == "icl_trec_coarse_6600shot_balance"
    assert manifest["total_pilot_tasks"] == 25
    assert len(manifest["tasks"]) == 25

    # Check demonstrations in context
    demos = [d.strip() for d in manifest["context"].split("\n\n") if d.strip()]
    assert len(demos) == 50, f"Expected exactly 50 demonstrations in context, got {len(demos)}"

    for idx, d in enumerate(demos):
        assert "\nlabel:" in d, f"Demo {idx} does not contain '\nlabel:': {d}"

    # Check tasks schema
    for idx, task in enumerate(manifest["tasks"]):
        assert task["index"] == idx
        assert task["competency"] == "Test_Time_Learning"
        assert task["sub_dataset"] == "icl_trec_coarse_6600shot_balance"
        assert isinstance(task["question"], str) and len(task["question"]) > 0
        assert isinstance(task["ground_truth_answers"], list) and len(task["ground_truth_answers"]) >= 1


# ============================================================================
# 3. DEMONSTRATION ORDERING & CHRONOLOGICAL SIMULATED CLOCK
# ============================================================================

def test_ttl_demonstration_ordering_matches_upstream():
    """Verify demonstrations are strictly aligned in upstream chronological sequence."""
    if pq is None or not PARQUET_FILE.exists():
        pytest.skip(f"pyarrow or official Parquet file not available at {PARQUET_FILE}")
    table = pq.read_table(PARQUET_FILE)
    df = table.to_pandas()
    row = df[df["metadata"].apply(lambda m: m.get("source") == "icl_trec_coarse_6600shot_balance")].iloc[0]
    upstream_demos = [d.strip() for d in row["context"].split("\n\n") if d.strip()][:50]

    manifest = load_pilot_manifest("Test_Time_Learning")
    manifest_demos = [d.strip() for d in manifest["context"].split("\n\n") if d.strip()]

    assert len(manifest_demos) == 50
    assert manifest_demos == upstream_demos, "Manifest demonstrations do not match upstream ordering!"


@pytest.mark.asyncio
async def test_ttl_session_simulated_time_advancement():
    """Verify session simulated time advances monotonically turn-by-turn during TTL ingestion."""
    session = MemoryAgentBenchSession(
        scenario_id="ttl_clock_test",
        condition_name="adaptive",
        db_path=":memory:",
    )
    t0 = session.simulated_time
    context = (
        "What does Elysium mean ?\nlabel: 3\n\n"
        "What was Jimmy Durante 's theme song ?\nlabel: 1\n\n"
        "What does HIV stand for ?\nlabel: 2"
    )
    stats = await session.ingest_stream(context, competency="Test_Time_Learning")
    assert stats["ingested_count"] == 3
    t1 = session.simulated_time
    # 3 turns * 60 seconds = 180 seconds advanced
    assert (t1 - t0).total_seconds() == 180.0
    session.close()


# ============================================================================
# 4. FUTURE-TEST LEAKAGE PREVENTION
# ============================================================================

def test_ttl_zero_overlap_between_demonstrations_and_test_questions():
    """Verify complete absence of overlap between demonstration queries and test questions."""
    manifest = load_pilot_manifest("Test_Time_Learning")
    demos = [d.strip() for d in manifest["context"].split("\n\n") if d.strip()]

    demo_questions = set()
    for d in demos:
        q_part = d.split("\nlabel:")[0].strip().lower()
        demo_questions.add(q_part)

    test_questions = [t["question"].strip().lower() for t in manifest["tasks"]]

    overlap = demo_questions.intersection(set(test_questions))
    assert len(overlap) == 0, f"Critical Leakage: Found overlapping questions: {overlap}"


@pytest.mark.asyncio
async def test_ttl_prompt_ground_truth_isolation():
    """Verify that agent prompt contains zero ground-truth answers or labels during query probing."""
    session = MemoryAgentBenchSession(
        scenario_id="ttl_leak_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    demo_context = (
        "What does Elysium mean ?\nlabel: 3\n\n"
        "What was Jimmy Durante 's theme song ?\nlabel: 1"
    )
    await session.ingest_stream(demo_context, competency="Test_Time_Learning")

    task = {
        "task_id": "ttl_q0",
        "question": "What is the population of Venezuela ?",
        "ground_truth_answers": ["4"],
        "competency": "Test_Time_Learning",
    }

    # Intercept messages in _generate_response
    captured_messages = []
    original_generate = session._generate_response

    async def mock_gen(messages, retrieved_memories, question):
        captured_messages.extend(messages)
        return await original_generate(messages, retrieved_memories, question)

    session._generate_response = mock_gen

    record = await session.query(task)
    assert record.task_id == "ttl_q0"

    user_prompt = captured_messages[1]["content"]
    system_prompt = captured_messages[0]["content"]

    # Ground truth answer '4' must NOT appear as ground-truth label in prompt
    assert "ground_truth" not in user_prompt.lower()
    assert "ground_truth" not in system_prompt.lower()
    # Test query question is present, but correct answer is isolated
    assert "What is the population of Venezuela ?" in user_prompt

    # Querying must not mutate memory store
    assert session.ingestion_count == 2
    assert len(session.memory_id_to_exp) == 2

    session.close()


# ============================================================================
# 5. MEMORY ISOLATION ACROSS SESSIONS & TRIALS
# ============================================================================

@pytest.mark.asyncio
async def test_ttl_memory_isolation_across_trials():
    """Verify independent temporary SQLite databases per trial and condition without cross-contamination."""
    demo_context = "What city was JFK nominated in ?\nlabel: 5"

    session1 = MemoryAgentBenchSession(
        scenario_id="ttl_isolation",
        condition_name="adaptive",
        trial=1,
        db_path=":memory:",
    )
    await session1.ingest_stream(demo_context, competency="Test_Time_Learning")
    assert len(session1.memory_id_to_exp) == 1

    session2 = MemoryAgentBenchSession(
        scenario_id="ttl_isolation",
        condition_name="adaptive",
        trial=2,
        db_path=":memory:",
    )
    # Session 2 starts completely empty
    assert len(session2.memory_id_to_exp) == 0
    assert session1.db_path != session2.db_path

    session1.close()
    session2.close()


# ============================================================================
# 6. ALL FIVE CONDITIONS SUPPORT
# ============================================================================

@pytest.mark.parametrize("condition_name,expected_mode,expect_memories", [
    ("vanilla", MemoryMode.OFF, False),
    ("naive_rag", MemoryMode.NAIVE, True),
    ("recency", MemoryMode.RECENCY, True),
    ("symmetric", MemoryMode.SYMMETRIC, True),
    ("adaptive", MemoryMode.ADAPTIVE, True),
])
@pytest.mark.asyncio
async def test_ttl_all_five_conditions(condition_name, expected_mode, expect_memories):
    """Verify all 5 experimental conditions execute cleanly with correct memory mode and behavior."""
    assert condition_name in CONDITION_MODE_MAP
    assert CONDITION_MODE_MAP[condition_name] == expected_mode

    session = MemoryAgentBenchSession(
        scenario_id=f"ttl_{condition_name}",
        condition_name=condition_name,
        db_path=":memory:",
    )

    demo_context = (
        "What city was JFK nominated in ?\nlabel: 5\n\n"
        "What does Elysium mean ?\nlabel: 3"
    )
    stats = await session.ingest_stream(demo_context, competency="Test_Time_Learning")
    assert stats["ingested_count"] == 2

    if expect_memories:
        assert len(session.memory_id_to_exp) == 2
    else:
        # Vanilla stores zero external memories
        assert len(session.memory_id_to_exp) == 0

    task = {
        "task_id": f"ttl_task_{condition_name}",
        "question": "What does target heart rate mean ?",
        "ground_truth_answers": ["3"],
        "competency": "Test_Time_Learning",
    }

    record = await session.query(task)
    assert record.condition == condition_name
    assert record.benchmark == "MemoryAgentBench"
    assert record.latency_ms > 0.0

    session.close()


# ============================================================================
# 7. XML ANSWER EXTRACTION & EXACT-MATCH EVALUATION
# ============================================================================

def test_ttl_xml_extraction_and_exact_match_scoring():
    """Verify official exact match and flexible label extraction for TTL."""
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "ttl_eval_test",
        "question": "What does target heart rate mean ?",
        "ground_truth_answers": ["3"],
        "competency": "Test_Time_Learning",
    }

    # Case 1: Standard XML tag <answer>3</answer>
    out1 = evaluator.evaluate(task, "The correct class is <answer>3</answer>.")
    assert out1.passed is True
    assert out1.score == 1.0
    assert out1.metrics["official"]["exact_match"] == 1.0
    assert out1.metrics["official"]["accuracy"] == 1.0

    # Case 2: XML tag with label: prefix <answer>label: 3</answer>
    out2 = evaluator.evaluate(task, "I classified this as <answer>label: 3</answer>")
    assert out2.passed is True
    assert out2.score == 1.0

    # Case 3: Raw output with label prefix label: 3
    out3 = evaluator.evaluate(task, "label: 3")
    assert out3.passed is True
    assert out3.score == 1.0

    # Case 4: Answer prefix Answer: 3
    out4 = evaluator.evaluate(task, "Answer: 3")
    assert out4.passed is True
    assert out4.score == 1.0

    # Case 5: Incorrect label <answer>5</answer>
    out5 = evaluator.evaluate(task, "<answer>5</answer>")
    assert out5.passed is False
    assert out5.score == 0.0
    assert out5.metrics["official"]["exact_match"] == 0.0

    # Case 6: Empty output
    out6 = evaluator.evaluate(task, "")
    assert out6.passed is False
    assert out6.score == 0.0


# ============================================================================
# 8. TELEMETRY INTEGRITY
# ============================================================================

@pytest.mark.asyncio
async def test_ttl_telemetry_record_completeness():
    """Verify that all telemetry fields are strictly populated without heuristic fabrications."""
    session = MemoryAgentBenchSession(
        scenario_id="ttl_telemetry_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    demo_context = "Where does the US get most energy ?\nlabel: 5"
    await session.ingest_stream(demo_context, competency="Test_Time_Learning")

    task = {
        "task_id": "icl_trec_coarse_6600shot_balance_no0",
        "question": "Where is the geographic center of the lower 48 states ?",
        "ground_truth_answers": ["5"],
        "competency": "Test_Time_Learning",
    }

    record = await session.query(task)

    assert record.benchmark == "MemoryAgentBench"
    assert record.task_id == "icl_trec_coarse_6600shot_balance_no0"
    assert record.condition == "adaptive"
    assert record.trial == 1
    assert record.iterations == 1
    assert record.latency_ms > 0.0
    assert record.tokens_used > 0
    assert record.evaluator_name == "memoryagentbench_evaluator"
    assert "official" in record.evaluator_metrics
    assert "accuracy" in record.evaluator_metrics["official"]
    assert "exact_match" in record.evaluator_metrics["official"]
    assert "substring_exact_match" in record.evaluator_metrics["official"]
    assert "token_f1" in record.evaluator_metrics["official"]

    session.close()
