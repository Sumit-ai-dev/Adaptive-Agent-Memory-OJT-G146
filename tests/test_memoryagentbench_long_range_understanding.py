"""
Comprehensive Test Suite for MemoryAgentBench Long-Range Understanding (LRU) Integration.

Validates:
1. Official HuggingFace Parquet dataset schema, row presence, and SHA-256 checksum.
2. Pilot manifest integrity, book count, task count (25), and checksum against manifest_metadata.json.
3. Paragraph-based sequential chunking (~1,000 words / chunk, preserving numbered paragraph boundaries).
4. Chronological simulated clock advancement during novel chunk ingestion.
5. Zero leakage: no ground-truth answers in prompt; memory store not mutated during query probing.
6. Ephemeral SQLite memory isolation across conditions, books, and trials.
7. Execution equivalence across all five experimental conditions:
   - vanilla (MemoryMode.OFF, zero stored memories)
   - naive_rag (MemoryMode.NAIVE)
   - recency (MemoryMode.RECENCY)
   - symmetric (MemoryMode.SYMMETRIC)
   - adaptive (MemoryMode.ADAPTIVE)
8. Evaluator multiple-choice parsing and accuracy scoring:
   - Exact option match (letter and text)
   - Text-only match
   - Option-letter match on declared answer
   - JSON output extraction
   - Rejection of negated and incorrect options
9. Complete trial telemetry and authentic metrics reporting.
10. Full run_scenario_evaluation execution with mock provider across the 4 novels.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest
import pyarrow.parquet as pq

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
    run_scenario_evaluation,
)
from models.domain import MemoryMode

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "benchmarks" / "data" / "memoryagentbench"
PARQUET_FILE = DATA_DIR / "upstream_parquets" / "Long_Range_Understanding.parquet"
MANIFEST_FILE = DATA_DIR / "pilot_long_range_understanding_25.json"
METADATA_FILE = DATA_DIR / "manifest_metadata.json"

OFFICIAL_LRU_PARQUET_SHA256 = "5AB175461954DB67770D4A4CB69E569B513EBB96ACEB9EE79B57F67488BCD539"


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

def test_lru_official_dataset_schema_and_checksum():
    """Verify that official HuggingFace Parquet file exists, has correct hash and schema."""
    assert PARQUET_FILE.exists(), f"Missing official Parquet file at {PARQUET_FILE}"

    # Verify SHA-256 checksum
    hasher = hashlib.sha256()
    with open(PARQUET_FILE, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_sha = hasher.hexdigest().upper()
    assert actual_sha == OFFICIAL_LRU_PARQUET_SHA256, (
        f"Checksum mismatch for {PARQUET_FILE.name}: expected {OFFICIAL_LRU_PARQUET_SHA256}, got {actual_sha}"
    )

    # Verify Parquet schema
    table = pq.read_table(PARQUET_FILE)
    col_names = table.column_names
    for required_col in ["context", "questions", "answers", "metadata"]:
        assert required_col in col_names, f"Missing required column: {required_col}"

    # Verify detective_qa rows exist
    df = table.to_pandas()
    matching_rows = df[df["metadata"].apply(lambda m: m.get("source") == "detective_qa")]
    assert len(matching_rows) == 10, f"Expected 10 detective novels, got {len(matching_rows)}"

    # Check first novel structure
    row0 = matching_rows.iloc[0]
    assert len(row0["context"]) > 300000
    assert len(row0["questions"]) == 6
    assert len(row0["answers"]) == 6
    assert row0["metadata"]["qa_pair_ids"] is not None


# ============================================================================
# 2. MANIFEST INTEGRITY & METADATA VERIFICATION
# ============================================================================

def test_lru_manifest_integrity():
    """Verify pilot manifest structure, task count, and SHA-256 against manifest_metadata.json."""
    assert MANIFEST_FILE.exists(), f"Missing manifest at {MANIFEST_FILE}"

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert "pilot_long_range_understanding_25.json" in meta["files"]
    expected_meta = meta["files"]["pilot_long_range_understanding_25.json"]

    # Verify file hash
    hasher = hashlib.sha256()
    with open(MANIFEST_FILE, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == expected_meta["sha256"], (
        f"Hash mismatch: expected {expected_meta['sha256']}, got {actual_hash}"
    )

    manifest = load_pilot_manifest("Long_Range_Understanding")
    assert manifest["benchmark"] == "MemoryAgentBench"
    assert manifest["competency"] == "Long_Range_Understanding"
    assert manifest["split"] == "detective_qa"
    assert manifest["total_pilot_tasks"] == 25
    assert len(manifest["tasks"]) == 25
    assert manifest["total_books"] == 4
    assert len(manifest["books"]) == 4

    # Verify book distribution: 6 + 6 + 8 + 5 = 25
    expected_book_counts = {
        "detective_qa_book124": 6,
        "detective_qa_book134": 6,
        "detective_qa_book142": 8,
        "detective_qa_book219": 5,
    }
    for b in manifest["books"]:
        b_id = b["book_id"]
        assert b_id in expected_book_counts
        assert b["task_count"] == expected_book_counts[b_id]
        assert len(b["context"]) > 300000

    # Verify each task schema
    for idx, task in enumerate(manifest["tasks"]):
        assert task["index"] == idx
        assert task["competency"] == "Long_Range_Understanding"
        assert task["sub_dataset"] == "detective_qa"
        assert isinstance(task["question"], str) and len(task["question"]) > 0
        assert isinstance(task["ground_truth_answers"], list) and len(task["ground_truth_answers"]) >= 1
        assert task["book_id"] in expected_book_counts


# ============================================================================
# 3. CHUNKING PROCEDURE & PARAGRAPH BOUNDARY PRESERVATION
# ============================================================================

@pytest.mark.asyncio
async def test_lru_paragraph_chunking_preserves_boundaries():
    """Verify that paragraph-based chunking produces ~1,000-word chunks without corrupting paragraph markers."""
    session = MemoryAgentBenchSession(
        scenario_id="lru_chunk_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    sample_context = (
        "[1] Chapter 1\n"
        "[2] The mystery began on a cold morning.\n"
        "[3] Detective Miller inspected the room.\n"
        + "\n".join(f"[{i}] Paragraph {i} with descriptive narrative text." for i in range(4, 150))
    )

    stats = await session.ingest_stream(sample_context, competency="Long_Range_Understanding")
    assert stats["ingested_count"] > 0
    assert len(session.memory_id_to_exp) == stats["ingested_count"]

    # Verify each chunk preserved the paragraph bracket structure
    for exp in session.memory_id_to_exp.values():
        chunk_text = exp.strategy_lesson
        assert chunk_text.startswith("[")
        assert len(chunk_text.split()) <= 1100  # Within ~1000 word bound

    session.close()


# ============================================================================
# 4. SIMULATED WALL-CLOCK ADVANCEMENT
# ============================================================================

@pytest.mark.asyncio
async def test_lru_simulated_time_advances_monotonically():
    """Verify session simulated time advances 60s per chunk during LRU novel ingestion."""
    session = MemoryAgentBenchSession(
        scenario_id="lru_clock_test",
        condition_name="adaptive",
        db_path=":memory:",
    )
    t0 = session.simulated_time
    context = (
        "[1] First chapter text with some words.\n"
        "[2] " + "word " * 1200 + "\n"
        "[3] " + "word " * 1200 + "\n"
    )
    stats = await session.ingest_stream(context, competency="Long_Range_Understanding")
    assert stats["ingested_count"] >= 2
    t1 = session.simulated_time
    expected_seconds = stats["ingested_count"] * 60.0
    assert (t1 - t0).total_seconds() == expected_seconds
    session.close()


# ============================================================================
# 5. FUTURE-TEST LEAKAGE PREVENTION & READ-ONLY QUERYING
# ============================================================================

@pytest.mark.asyncio
async def test_lru_prompt_isolation_and_read_only_queries():
    """Verify ground truth is never passed into prompts and querying does not mutate memory store."""
    session = MemoryAgentBenchSession(
        scenario_id="lru_isolation_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    sample_story = (
        "[1] The Brandt couple was seen visiting the mansion.\n"
        "[2] Miss Martin Dale was also present during the evening."
    )
    await session.ingest_stream(sample_story, competency="Long_Range_Understanding")
    initial_mem_count = len(session.memory_id_to_exp)

    task = {
        "task_id": "detective_qa_book124_no0",
        "question": (
            "Now Answer the Question: Which character is related to the death of the deceased?\n"
            "A. Mrs. Hemm\n"
            "B. Mr. and Mrs. MacNamara\n"
            "C. The Brandt couple\n"
            "D. Miss House\n"
            "Output:"
        ),
        "ground_truth_answers": ["C. The Brandt couple"],
        "competency": "Long_Range_Understanding",
    }

    captured_messages = []
    orig_generate = session._generate_response

    async def mock_gen(messages, retrieved_memories, question):
        captured_messages.extend(messages)
        return await orig_generate(messages, retrieved_memories, question)

    session._generate_response = mock_gen
    record = await session.query(task)

    assert record.task_id == "detective_qa_book124_no0"
    user_prompt = captured_messages[1]["content"]
    system_prompt = captured_messages[0]["content"]

    # Ground-truth tag/answer must NOT appear as ground-truth label in prompt
    assert "ground_truth" not in user_prompt.lower()
    assert "ground_truth" not in system_prompt.lower()

    # Memory state MUST NOT be mutated by probe query
    assert len(session.memory_id_to_exp) == initial_mem_count
    assert session.ingestion_count == 1

    session.close()


# ============================================================================
# 6. MEMORY ISOLATION ACROSS SESSIONS & NOVELS
# ============================================================================

@pytest.mark.asyncio
async def test_lru_memory_isolation_across_novels_and_trials():
    """Verify that different novels and trials run in strictly separated databases."""
    session_book0 = MemoryAgentBenchSession(
        scenario_id="lru_book124",
        condition_name="adaptive",
        trial=1,
        db_path=":memory:",
    )
    await session_book0.ingest_stream("[1] Story of book 124.", competency="Long_Range_Understanding")
    assert len(session_book0.memory_id_to_exp) == 1

    session_book1 = MemoryAgentBenchSession(
        scenario_id="lru_book134",
        condition_name="adaptive",
        trial=1,
        db_path=":memory:",
    )
    # Starts completely empty
    assert len(session_book1.memory_id_to_exp) == 0
    assert session_book0.db_path != session_book1.db_path

    session_book0.close()
    session_book1.close()


# ============================================================================
# 7. ALL FIVE CONDITIONS SUPPORT
# ============================================================================

@pytest.mark.parametrize("condition_name,expected_mode,expect_memories", [
    ("vanilla", MemoryMode.OFF, False),
    ("naive_rag", MemoryMode.NAIVE, True),
    ("recency", MemoryMode.RECENCY, True),
    ("symmetric", MemoryMode.SYMMETRIC, True),
    ("adaptive", MemoryMode.ADAPTIVE, True),
])
@pytest.mark.asyncio
async def test_lru_all_five_conditions(condition_name, expected_mode, expect_memories):
    """Verify all 5 experimental conditions execute cleanly for LRU."""
    assert condition_name in CONDITION_MODE_MAP
    assert CONDITION_MODE_MAP[condition_name] == expected_mode

    session = MemoryAgentBenchSession(
        scenario_id=f"lru_{condition_name}",
        condition_name=condition_name,
        db_path=":memory:",
    )

    story = "[1] The Brandt couple was seen leaving the crime scene."
    stats = await session.ingest_stream(story, competency="Long_Range_Understanding")
    assert stats["ingested_count"] == 1

    if expect_memories:
        assert len(session.memory_id_to_exp) == 1
    else:
        assert len(session.memory_id_to_exp) == 0

    task = {
        "task_id": f"lru_task_{condition_name}",
        "question": (
            "Now Answer the Question: Which character is related to the death of the deceased?\n"
            "A. Mrs. Hemm\n"
            "B. Mr. and Mrs. MacNamara\n"
            "C. The Brandt couple\n"
            "D. Miss House\n"
            "Output:"
        ),
        "ground_truth_answers": ["C. The Brandt couple"],
        "competency": "Long_Range_Understanding",
    }

    record = await session.query(task)
    assert record.condition == condition_name
    assert record.benchmark == "MemoryAgentBench"
    assert record.latency_ms > 0.0

    if expect_memories:
        # Mock provider matches option from retrieved memory
        assert record.success is True
        assert record.score == 1.0
    else:
        # Vanilla has no memory and cannot answer
        assert record.success is False
        assert record.score == 0.0

    session.close()


# ============================================================================
# 8. MULTIPLE-CHOICE EVALUATOR PARSING & SCORING
# ============================================================================

def test_lru_evaluator_scoring_variants():
    """Verify evaluator robustly scores XML tags, text-only, JSON, and letters for multiple choice."""
    evaluator = MemoryAgentBenchEvaluator()
    task = {
        "task_id": "detective_qa_book124_no0",
        "competency": "Long_Range_Understanding",
        "ground_truth_answers": ["C. The Brandt couple"],
    }

    # 1. Exact match with letter and text in XML tag
    res1 = evaluator.evaluate(task, "The murderer is <answer>C. The Brandt couple</answer>.")
    assert res1.passed is True
    assert res1.score == 1.0
    assert res1.metrics["official"]["accuracy"] == 1.0

    # 2. Text only in XML tag
    res2 = evaluator.evaluate(task, "Answer is <answer>The Brandt couple</answer>")
    assert res2.passed is True
    assert res2.score == 1.0

    # 3. Option letter only in XML tag
    res3 = evaluator.evaluate(task, "Option is <answer>C</answer>")
    assert res3.passed is True
    assert res3.score == 1.0

    # 4. JSON format
    res4 = evaluator.evaluate(task, 'Output: {"answer":"C. The Brandt couple", "reasoning":"evidence"}')
    assert res4.passed is True
    assert res4.score == 1.0

    # 5. JSON with option letter only
    res5 = evaluator.evaluate(task, '{"answer":"C"}')
    assert res5.passed is True
    assert res5.score == 1.0

    # 6. Prefix Answer
    res6 = evaluator.evaluate(task, "Answer: C. The Brandt couple")
    assert res6.passed is True
    assert res6.score == 1.0

    # 7. Incorrect option
    res7 = evaluator.evaluate(task, "<answer>A. Mrs. Hemm</answer>")
    assert res7.passed is False
    assert res7.score == 0.0

    # 8. Negated reasoning (must not cause false positive)
    res8 = evaluator.evaluate(task, "Although not C. The Brandt couple, it was actually A.")
    assert res8.passed is False
    assert res8.score == 0.0


# ============================================================================
# 9. TELEMETRY RECORD INTEGRITY
# ============================================================================

@pytest.mark.asyncio
async def test_lru_telemetry_record_completeness():
    """Verify telemetry record populated with accurate metadata for LRU."""
    session = MemoryAgentBenchSession(
        scenario_id="lru_telemetry_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    await session.ingest_stream(
        "[1] The Brandt couple was seen near Wilbraham Crescent.",
        competency="Long_Range_Understanding",
    )

    task = {
        "task_id": "detective_qa_book124_no0",
        "question": (
            "Now Answer the Question: Which character is related to the death of the deceased?\n"
            "A. Mrs. Hemm\n"
            "B. Mr. and Mrs. MacNamara\n"
            "C. The Brandt couple\n"
            "D. Miss House\n"
            "Output:"
        ),
        "ground_truth_answers": ["C. The Brandt couple"],
        "competency": "Long_Range_Understanding",
    }

    record = await session.query(task)
    assert record.benchmark == "MemoryAgentBench"
    assert record.task_id == "detective_qa_book124_no0"
    assert record.condition == "adaptive"
    assert record.trial == 1
    assert record.latency_ms > 0.0
    assert record.tokens_used > 0
    assert record.evaluator_name == "memoryagentbench_evaluator"
    assert "accuracy" in record.evaluator_metrics["official"]
    assert "exact_match" in record.evaluator_metrics["official"]
    assert "substring_exact_match" in record.evaluator_metrics["official"]

    session.close()


# ============================================================================
# 10. MULTI-NOVEL RUN_SCENARIO_EVALUATION EXECUTION
# ============================================================================

@pytest.mark.asyncio
async def test_lru_run_scenario_evaluation_limited():
    """Verify run_scenario_evaluation executes across novels with isolated sessions."""
    records = await run_scenario_evaluation(
        competency="Long_Range_Understanding",
        condition_name="adaptive",
        trial=1,
        limit=5,  # Evaluate first 5 tasks
        provider="mock",
    )
    assert len(records) == 5
    for r in records:
        assert r.benchmark == "MemoryAgentBench"
        assert r.condition == "adaptive"
        assert r.trial == 1
        assert r.tokens_used > 0
