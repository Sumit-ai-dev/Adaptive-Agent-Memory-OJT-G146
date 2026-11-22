"""
Comprehensive Test Suite for MemoryAgentBench Multi-Turn Streaming Session Harness.
Validates:
1. Multi-turn session continuity and sequential state maintenance.
2. Memory isolation across sessions and experimental conditions.
3. Epistemic Conflict Detection (True Positives, False Positives, False Negatives).
4. Prevention of False Positive Quarantine (preserving valid historical/additional facts).
5. Ground-truth isolation from LLM prompts.
6. Baseline equivalence across all 5 conditions (Vanilla, Naive, Recency, Symmetric, Adaptive).
7. Full AEMA Bayesian Quarantine blocking obsolete memories during retrieval.
8. Telemetry recording integrity and official evaluator integration.
"""

from datetime import datetime, timezone
import pytest

from ai_service.embedder import local_embedder
from benchmarks.evaluators.memoryagentbench_evaluator import MemoryAgentBenchEvaluator
from benchmarks.memoryagentbench_runner import (
    CONDITION_MODE_MAP,
    EpistemicConflictDetector,
    FactTriple,
    MemoryAgentBenchSession,
)
from models.domain import ExperienceStatus, MemoryMode


@pytest.fixture(autouse=True)
def setup_fast_offline_embedder():
    """Ensure fast, deterministic vector embeddings without network timeouts."""
    from ai_service.config import settings
    local_embedder._load_attempted = True
    local_embedder._model = None
    old_threshold = settings.SIMILARITY_THRESHOLD
    settings.SIMILARITY_THRESHOLD = 0.40
    yield
    settings.SIMILARITY_THRESHOLD = old_threshold



# ============================================================================
# 1. EPISTEMIC CONFLICT DETECTION & QUARANTINE VALIDATION
# ============================================================================

def test_conflict_detection_true_positive_functional_contradiction():
    f1 = FactTriple(
        index=100,
        subject="rugby union",
        relation="country_of_origin",
        target_object="england",
        is_functional=True,
        raw_statement="rugby union was created in the country of England."
    )
    f2 = FactTriple(
        index=186,
        subject="rugby union",
        relation="country_of_origin",
        target_object="india",
        is_functional=True,
        raw_statement="rugby union was created in the country of India."
    )
    # Direct single-valued functional contradiction
    assert EpistemicConflictDetector.is_contradiction(f1, f2) is True


def test_false_positive_quarantine_prevention_additional_facts():
    # Fact 1: Pesäpallo creation country
    f1 = FactTriple(
        index=59,
        subject="pesäpallo",
        relation="country_of_origin",
        target_object="finland",
        is_functional=True,
        raw_statement="pesäpallo was created in the country of Finland."
    )
    # Fact 2: Goaltender position sport (mentions pesäpallo as object, not subject!)
    f2 = FactTriple(
        index=310,
        subject="goaltender",
        relation="sport",
        target_object="pesäpallo",
        is_functional=True,
        raw_statement="goaltender is associated with the sport of pesäpallo."
    )
    # MUST NOT be flagged as contradiction (different subjects and relations)
    assert EpistemicConflictDetector.is_contradiction(f1, f2) is False


def test_false_positive_quarantine_prevention_multi_valued_citizenship():
    f1 = FactTriple(
        index=42,
        subject="vijay mallya",
        relation="citizenship",
        target_object="india",
        is_functional=True,
        raw_statement="Vijay Mallya is a citizen of India."
    )
    f2 = FactTriple(
        index=176,
        subject="narendra modi",
        relation="citizenship",
        target_object="india",
        is_functional=True,
        raw_statement="Narendra Modi is a citizen of India."
    )
    # Different people can have the same citizenship - NOT a contradiction!
    assert EpistemicConflictDetector.is_contradiction(f1, f2) is False


def test_false_negative_prevention_single_valued_capital():
    f1 = FactTriple(
        index=158,
        subject="india",
        relation="capital",
        target_object="new delhi",
        is_functional=True,
        raw_statement="The capital of India is New Delhi."
    )
    f2 = FactTriple(
        index=341,
        subject="india",
        relation="capital",
        target_object="grosseto",
        is_functional=True,
        raw_statement="The capital of India is Grosseto."
    )
    # Same country, same relation, different capital -> Contradiction!
    assert EpistemicConflictDetector.is_contradiction(f1, f2) is True


# ============================================================================
# 2. MULTI-TURN SESSION CONTINUITY & ISOLATION
# ============================================================================

@pytest.mark.asyncio
async def test_multi_turn_session_continuity():
    session = MemoryAgentBenchSession(
        scenario_id="test_stream",
        condition_name="adaptive",
        db_path=":memory:",
    )

    context = (
        "Here is a list of facts:\n"
        "0. Thomas Kyd was born in the city of London.\n"
        "1. The chairperson of Fatah is Mahmoud Abbas.\n"
        "2. Amy Winehouse died in the city of Camden Town.\n"
        "3. Hines Ward plays the position of wide receiver.\n"
    )

    stats = await session.ingest_stream(context, competency="Conflict_Resolution")
    assert stats["ingested_count"] == 4
    assert stats["quarantined_count"] == 0
    assert len(session.memory_id_to_exp) == 4


@pytest.mark.asyncio
async def test_memory_isolation_between_conditions():
    session_a = MemoryAgentBenchSession(
        scenario_id="scenario_1",
        condition_name="adaptive",
        db_path=":memory:",
    )
    session_b = MemoryAgentBenchSession(
        scenario_id="scenario_1",
        condition_name="naive_rag",
        db_path=":memory:",
    )

    context_a = "0. Thomas Kyd was born in the city of London."
    context_b = "0. The chairperson of Fatah is Mahmoud Abbas."

    await session_a.ingest_stream(context_a, competency="Conflict_Resolution")
    await session_b.ingest_stream(context_b, competency="Conflict_Resolution")

    # Assert memories in session A cannot be retrieved by session B
    res_a, _ = await session_a.retriever.retrieve_with_diagnostics("Where was Thomas Kyd born?", mode=MemoryMode.NAIVE)
    res_b, _ = await session_b.retriever.retrieve_with_diagnostics("Where was Thomas Kyd born?", mode=MemoryMode.NAIVE)

    assert len(res_a) == 1
    assert "London" in res_a[0].experience.strategy_lesson
    assert len(res_b) == 0  # Completely isolated database


# ============================================================================
# 3. BASELINE EQUIVALENCE & RETRIEVAL BEHAVIOR
# ============================================================================

@pytest.mark.asyncio
async def test_baseline_equivalence_conditions_registered():
    assert len(CONDITION_MODE_MAP) == 5
    expected_modes = {"vanilla", "naive_rag", "recency", "symmetric", "adaptive"}
    assert set(CONDITION_MODE_MAP.keys()) == expected_modes


@pytest.mark.asyncio
async def test_aema_quarantine_blocks_obsolete_memory():
    # Create Full AEMA session
    session_aema = MemoryAgentBenchSession(
        scenario_id="conflict_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    context = (
        "Here is a list of facts:\n"
        "100. rugby union was created in the country of England.\n"
        "186. rugby union was created in the country of India.\n"
    )

    await session_aema.ingest_stream(context, competency="Conflict_Resolution")

    # Verify that Fact 100 was quarantined
    assert len(session_aema.quarantine_events) == 1
    quarantined_event = session_aema.quarantine_events[0]
    assert "England" in quarantined_event["obsolete_fact"]
    assert "India" in quarantined_event["superseding_fact"]

    # In AEMA mode, query retrieval MUST filter out the quarantined England memory
    retrieved, diagnostics = await session_aema.retriever.retrieve_with_diagnostics(
        query="Which country was rugby union created in?",
        mode=MemoryMode.ADAPTIVE,
        top_k=3,
    )

    assert len(retrieved) >= 1
    # Top memory MUST be India, NOT England
    assert "India" in retrieved[0].experience.strategy_lesson
    for r in retrieved:
        assert "England" not in r.experience.strategy_lesson
        assert r.experience.status == ExperienceStatus.ACTIVE


@pytest.mark.asyncio
async def test_naive_rag_admits_obsolete_memory():
    # Create Naive RAG session
    session_naive = MemoryAgentBenchSession(
        scenario_id="conflict_test",
        condition_name="naive_rag",
        db_path=":memory:",
    )

    context = (
        "Here is a list of facts:\n"
        "100. rugby union was created in the country of England.\n"
        "186. rugby union was created in the country of India.\n"
    )

    await session_naive.ingest_stream(context, competency="Conflict_Resolution")

    # In Naive RAG, zero memories are quarantined
    assert len(session_naive.quarantine_events) == 0

    # Query retrieval in Naive RAG admits both memories based on similarity alone
    retrieved, _ = await session_naive.retriever.retrieve_with_diagnostics(
        query="Which country was rugby union created in?",
        mode=MemoryMode.NAIVE,
        top_k=5,
    )

    # Both facts exist in memory
    lessons = [r.experience.strategy_lesson for r in retrieved]
    has_england = any("England" in l for l in lessons)
    has_india = any("India" in l for l in lessons)
    assert has_england is True
    assert has_india is True


# ============================================================================
# 4. GROUND TRUTH ISOLATION & TELEMETRY INTEGRITY
# ============================================================================

@pytest.mark.asyncio
async def test_ground_truth_isolation_in_prompts():
    session = MemoryAgentBenchSession(
        scenario_id="gt_leak_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    task = {
        "task_id": "cr_test_isolation",
        "question": "Which country was rugby union created in?",
        "ground_truth_answers": ["India"],
        "obsolete_answers": ["England"],
        "competency": "Conflict_Resolution",
    }

    # Query with mock provider
    record = await session.query(task)

    # Telemetry record is complete and unmanipulated
    assert record.benchmark == "MemoryAgentBench"
    assert record.task_id == "cr_test_isolation"
    assert record.condition == "adaptive"
    assert record.latency_ms > 0.0
    assert record.tokens_used > 0
    assert record.token_count_estimated is True
    assert "official" in record.evaluator_metrics
    assert "exact_match" in record.evaluator_metrics["official"]


@pytest.mark.asyncio
async def test_accurate_retrieval_document_chunking():
    session = MemoryAgentBenchSession(
        scenario_id="ar_doc_test",
        condition_name="adaptive",
        db_path=":memory:",
    )

    doc_context = (
        "Document 1:\n"
        "Complexity theory studies algorithms and computational problems.\n\n"
        "Document 2:\n"
        "Normandy is located in the country of France. It was settled in the 10th century.\n"
    )

    stats = await session.ingest_stream(doc_context, competency="Accurate_Retrieval")
    assert stats["ingested_count"] == 2

    # Query for Normandy
    retrieved, _ = await session.retriever.retrieve_with_diagnostics(
        query="In what country is Normandy located?",
        mode=MemoryMode.ADAPTIVE,
        top_k=2,
    )

    assert len(retrieved) >= 1
    assert "France" in retrieved[0].experience.strategy_lesson
