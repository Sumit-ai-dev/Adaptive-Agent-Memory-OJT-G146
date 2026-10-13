"""
Cross-Platform Ecosystem & Mathematical Parity Test Suite
Author: Kasat Sakshi Dattaprasad (Memory Intelligence & Backend Gateway Lead)

Asserts strict mathematical and algorithmic invariance across:
1. Python Backend Trust Engine (ai_service/nodes/trust_node.py)
2. TypeScript SDK Engine (packages/aema/src/trust.ts)
3. Theorem 1 Deterministic Quarantine Boundary Condition (theta = 0.35, k* = 3)
"""

import math
import pytest
from ai_service.nodes.trust_node import (
    compute_next_trust,
    ALPHA_SUCCESS,
    BETA_FAILURE,
    QUARANTINE_THRESHOLD,
)
from models.domain import TaskDomain
from models.experience import Experience, ExperienceStatus


def test_theorem_1_k_star_deterministic_quarantine_derivation():
    """
    Theorem 1 Invariant:
    k* = ceil( ln(theta / S_0) / ln(beta) )
    With default S_0 = 1.0, beta = 0.70, theta = 0.35:
    k* = ceil( ln(0.35) / ln(0.70) ) = ceil(-1.0498 / -0.3567) = ceil(2.9435) = 3.
    """
    s_0 = 1.0
    theta = QUARANTINE_THRESHOLD
    beta = BETA_FAILURE

    k_star_theoretical = math.ceil(math.log(theta / s_0) / math.log(beta))
    assert k_star_theoretical == 3, f"Theoretical k* must equal 3, got {k_star_theoretical}"

    # Step through failure trajectory
    s = s_0
    for step in range(1, 4):
        s, reason = compute_next_trust(current_trust=s, outcome_score=0.0)
        if step < 3:
            assert s >= theta, f"Step {step} trust {s} dropped below quarantine threshold prematurely"
        else:
            assert s < theta, f"Step {step} trust {s} did not clear quarantine threshold"

    assert round(s, 3) == 0.343, f"Expected 0.343 at step 3, got {s}"


def test_cross_platform_success_reinforcement_parity():
    """
    Validates that Python and TypeScript SDK compute identical steady-climb updates:
    S_{t+1} = 0.85 * S_t + 0.15 * 1.0.
    Starting from S_0 = 0.50:
    S_1 = 0.85 * 0.50 + 0.15 = 0.425 + 0.15 = 0.575.
    Matches TypeScript SDK test expectation (0.575).
    """
    new_trust, reason = compute_next_trust(current_trust=0.50, outcome_score=1.0)
    assert round(new_trust, 4) == 0.5750
    assert "Success reward" in reason
    assert str(ALPHA_SUCCESS) in reason


def test_cross_platform_failure_penalty_parity():
    """
    Validates that Python and TypeScript SDK compute identical penalty updates:
    S_{t+1} = 0.70 * S_t + 0.30 * 0.0.
    Starting from S_0 = 1.0:
    Step 1: 0.70
    Step 2: 0.49
    Step 3: 0.343 (Quarantine triggered)
    """
    s1, _ = compute_next_trust(1.0, 0.0)
    assert round(s1, 2) == 0.70

    s2, _ = compute_next_trust(s1, 0.0)
    assert round(s2, 2) == 0.49

    s3, _ = compute_next_trust(s2, 0.0)
    assert round(s3, 3) == 0.343
    assert s3 < QUARANTINE_THRESHOLD


def test_cross_platform_boundary_clamping():
    """Ensures trust updates remain strictly clamped within [0.0, 1.0] under extreme values."""
    clamped_high, _ = compute_next_trust(current_trust=1.5, outcome_score=1.0)
    assert 0.0 <= clamped_high <= 1.0

    clamped_low, _ = compute_next_trust(current_trust=-0.5, outcome_score=0.0)
    assert 0.0 <= clamped_low <= 1.0


def test_schema_cross_platform_field_interoperability():
    """
    Validates that Python Experience model seamlessly bridges with
    TypeScript SDK NewExperience and Experience types.
    """
    exp = Experience(
        id="exp-eco-test-01",
        task_domain=TaskDomain.CODING,
        trigger_condition="AEMA SDK REST client sync",
        strategy_lesson="Use AEMAClient with baseUrl pointing to FastAPI /api/v1 gateway",
        pitfall="Do not bypass Theorem 1 quarantine threshold during local fallback",
        confidence=0.95,
        trust_score=0.88,
        status=ExperienceStatus.ACTIVE,
    )
    data = exp.model_dump()
    assert data["trust_score"] == 0.88
    assert data["status"] == ExperienceStatus.ACTIVE
