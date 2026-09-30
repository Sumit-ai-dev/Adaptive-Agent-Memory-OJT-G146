"""
Unit tests for Memory Intelligence Models and LangGraph Nodes.
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Trust Lead)
Verifies:
1. Pydantic v2 data models and serialization.
2. Composite retrieval scoring (0.70 Sim + 0.30 Trust) and cutoff invariants.
3. Asymmetric EMA trust dynamics, candidate promotion, and quarantine deprecation.
"""

import pytest
from models.domain import TaskDomain
from models.experience import (
    Experience,
    ExperienceMatch,
    ExperienceStatus,
    TrustHistoryRecord,
)
from models.task import (
    ExecutionStatus,
    MemoryMode,
    OutcomeQuality,
    TaskExecuteRequest,
    TaskExecuteResponse,
)
from ai_service.nodes.retrieve_node import (
    cosine_similarity,
    retrieve_experiences,
    retrieve_node,
)
from ai_service.nodes.trust_node import (
    ALPHA_SUCCESS,
    BETA_FAILURE,
    QUARANTINE_THRESHOLD,
    compute_next_trust,
    trust_node,
    update_experience_trust,
)


# ==============================================================================
# 1. Pydantic v2 Models Validation
# ==============================================================================

def test_experience_model_instantiation():
    """Verifies standard 7-tuple experience schema creation and field defaults."""
    exp = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="Write recursive Fibonacci in Python",
        strategy_lesson="Use functools.lru_cache to avoid exponential blowup",
        pitfall="Do not use unmemoized recursion on n > 35",
        confidence=0.90,
        trust_score=0.80,
    )
    assert exp.id is not None
    assert exp.task_domain == TaskDomain.CODING
    assert exp.status == ExperienceStatus.ACTIVE
    assert exp.trust_score == 0.80
    assert exp.uses_count == 0


def test_task_execute_request_byok_serialization():
    """Verifies TaskExecuteRequest validates BYOK keys and camelCase aliases."""
    payload = {
        "taskInput": "Optimize SQL query for sales data",
        "domain": "analysis",
        "memoryMode": "adaptive",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "apiKey": "gsk_test12345",
    }
    req = TaskExecuteRequest.model_validate(payload)
    assert req.task_input == "Optimize SQL query for sales data"
    assert req.domain == TaskDomain.ANALYSIS
    assert req.memory_mode == MemoryMode.ADAPTIVE
    assert req.api_key == "gsk_test12345"


# ==============================================================================
# 2. Vector Cosine Similarity
# ==============================================================================

def test_cosine_similarity_identical_vectors():
    v1 = [1.0, 2.0, 3.0]
    v2 = [1.0, 2.0, 3.0]
    sim = cosine_similarity(v1, v2)
    assert pytest.approx(sim, 0.0001) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    sim = cosine_similarity(v1, v2)
    assert pytest.approx(sim, 0.0001) == 0.0


def test_cosine_similarity_mismatched_dimensions():
    v1 = [1.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 0.0


# ==============================================================================
# 3. Composite Memory Retrieval (retrieve_node)
# ==============================================================================

def test_composite_retrieval_formula_and_ranking():
    """
    Verifies: CompositeScore = 0.70 * Sim + 0.30 * Trust.
    Candidate A: Sim = 0.90, Trust = 0.50 -> Score = 0.70*0.90 + 0.30*0.50 = 0.63 + 0.15 = 0.78
    Candidate B: Sim = 0.80, Trust = 0.90 -> Score = 0.70*0.80 + 0.30*0.90 = 0.56 + 0.27 = 0.83
    Candidate B should rank higher than Candidate A!
    """
    query_vector = [1.0, 0.0]

    # Candidate A: high similarity, moderate trust
    exp_a = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="A",
        strategy_lesson="A",
        trust_score=0.50,
        embedding=[0.90, 0.43588989],  # norm ~ 1.0, sim = 0.90
    )

    # Candidate B: moderate similarity, very high trust
    exp_b = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="B",
        strategy_lesson="B",
        trust_score=0.90,
        embedding=[0.80, 0.60],  # norm = 1.0, sim = 0.80
    )

    matches = retrieve_experiences(
        query_embedding=query_vector,
        candidates=[exp_a, exp_b],
        min_similarity=0.70,
        min_trust=0.35,
    )

    assert len(matches) == 2
    # Verify B is ranked first due to trust weighting
    assert matches[0].experience.trigger_condition == "B"
    assert pytest.approx(matches[0].composite_score, 0.01) == 0.83
    assert matches[1].experience.trigger_condition == "A"
    assert pytest.approx(matches[1].composite_score, 0.01) == 0.78


def test_retrieval_quarantine_cutoff():
    """Experiences with Trust < 0.35 must be filtered out to prevent negative transfer."""
    query_vector = [1.0, 0.0]

    toxic_exp = Experience(
        task_domain=TaskDomain.CODING,
        trigger_condition="Toxic advice",
        strategy_lesson="Delete production database",
        trust_score=0.20,  # Below theta=0.35
        embedding=[1.0, 0.0],  # Perfect similarity 1.0!
    )

    matches = retrieve_experiences(
        query_embedding=query_vector,
        candidates=[toxic_exp],
        min_similarity=0.70,
        min_trust=0.35,
    )
    # Must be completely rejected despite perfect semantic similarity
    assert len(matches) == 0


def test_retrieval_node_ablation_mode_off():
    """In ablation mode ('off'), retrieve_node returns zero experiences."""
    state = {
        "task_input": "Test query",
        "memory_mode": "off",
        "memory_candidates": [
            Experience(
                trigger_condition="X",
                strategy_lesson="Y",
                trust_score=0.90,
            )
        ],
    }
    result = retrieve_node(state)
    assert result["retrieved_experiences"] == []


# ==============================================================================
# 4. Asymmetric EMA Trust Engine (trust_node)
# ==============================================================================

def test_asymmetric_ema_success_climb():
    """On success (R >= 0.8), trust climbs steadily: S_{t+1} = 0.85 * S_t + 0.15 * 1.0."""
    initial_trust = 0.60
    new_trust, reason = compute_next_trust(current_trust=initial_trust, outcome_score=0.95)
    expected = (ALPHA_SUCCESS * initial_trust) + ((1.0 - ALPHA_SUCCESS) * 1.0)
    assert pytest.approx(new_trust, 0.001) == round(expected, 4)
    assert "Success reward" in reason


def test_asymmetric_ema_failure_penalty():
    """On failure (R <= 0.3), trust drops aggressively: S_{t+1} = 0.70 * S_t."""
    initial_trust = 0.60
    new_trust, reason = compute_next_trust(current_trust=initial_trust, outcome_score=0.10)
    expected = (BETA_FAILURE * initial_trust) + ((1.0 - BETA_FAILURE) * 0.0)
    assert pytest.approx(new_trust, 0.001) == round(expected, 4)
    assert "Failure penalty" in reason


def test_automatic_quarantine_deprecation_on_failure():
    """When a failure drops trust score below 0.35, memory status transitions to deprecated."""
    exp = Experience(
        trigger_condition="Fragile Regex parsing",
        strategy_lesson="Use regex for HTML parsing",
        trust_score=0.40,
        status=ExperienceStatus.ACTIVE,
    )

    # Catastrophic failure: R = 0.0
    updated_exp, record, update = update_experience_trust(
        experience=exp,
        outcome_score=0.0,
        execution_id="exec-test-123",
    )

    # 0.70 * 0.40 = 0.28 < 0.35 -> Must be quarantined!
    assert updated_exp.trust_score == 0.28
    assert updated_exp.status == ExperienceStatus.DEPRECATED
    assert "Quarantined" in record.reason
    assert record.old_trust == 0.40
    assert record.new_trust == 0.28
    assert record.delta == -0.12


def test_candidate_promotion_on_verified_success():
    """A new lesson in 'candidate' quarantine gets promoted to 'active' on success."""
    candidate_exp = Experience(
        trigger_condition="Novel API workaround",
        strategy_lesson="Use exponential backoff with jitter",
        trust_score=0.50,
        status=ExperienceStatus.CANDIDATE,
    )

    updated_exp, record, update = update_experience_trust(
        experience=candidate_exp,
        outcome_score=0.90,
    )

    assert updated_exp.status == ExperienceStatus.ACTIVE
    assert "Promoted from candidate to active" in record.reason


def test_trust_node_batch_execution():
    """Verifies trust_node runs over all retrieved experiences and outputs audit records."""
    exp1 = Experience(trigger_condition="A", strategy_lesson="A", trust_score=0.70)
    exp2 = Experience(trigger_condition="B", strategy_lesson="B", trust_score=0.50)

    state = {
        "task_id": "batch-exec-001",
        "outcome_score": 0.90,
        "retrieved_experiences": [exp1, exp2],
    }

    output = trust_node(state)
    assert len(output["updated_experiences"]) == 2
    assert len(output["trust_history_records"]) == 2
    assert len(output["trust_updates"]) == 2
    assert all(r.execution_id == "batch-exec-001" for r in output["trust_history_records"])
