"""
Unit Tests for Mathematical Trust Dynamics (Theorem 1).
Verifies:
  1. Theorem 1 Analytical Bound: t* <= 3 consecutive failures to trigger quarantine under (beta=0.70, theta=0.35).
  2. Asymmetric vs Symmetric decay trajectories.
  3. Positive momentum recovery under alpha=0.85.
"""

import math
import pytest
from ai_service.config import settings


def compute_decay_steps(s0: float, beta: float, theta: float) -> int:
    """Exact analytical formula from Theorem 1 in Section IV-A."""
    return math.ceil(math.log(theta / s0) / math.log(beta))


def test_theorem_1_analytical_bound():
    """
    Theorem 1 states: For S_0 = 0.75, beta = 0.70, theta = 0.35:
    t* = ceil( ln(0.35 / 0.75) / ln(0.70) ) = ceil( 2.135 ) = 3.
    """
    s0 = settings.INITIAL_TRUST      # 0.75
    beta = settings.BETA_FAILURE     # 0.70
    theta = settings.THETA_CUTOFF    # 0.35

    t_star = compute_decay_steps(s0, beta, theta)
    assert t_star == 3, f"Expected t* to be 3, got {t_star}"

    # Step-by-step numerical simulation:
    s = s0
    # Step 1:
    s = s * beta
    assert round(s, 4) == 0.5250
    assert s >= theta, "After 1 failure, memory must NOT be quarantined"

    # Step 2:
    s = s * beta
    assert round(s, 4) == 0.3675
    assert s >= theta, "After 2 failures, memory must NOT yet be quarantined"

    # Step 3:
    s = s * beta
    assert round(s, 5) == 0.25725
    assert s < theta, "After 3 failures, memory MUST be quarantined (< 0.35)"


def test_symmetric_reflexion_decay_lag():
    """
    Symmetric baseline (beta = 0.80) decays slower:
    t* = ceil( ln(0.35 / 0.75) / ln(0.80) ) = ceil( 3.41 ) = 4.
    Poisoned memory persists an extra trial, causing negative transfer.
    """
    s0 = 0.75
    beta_sym = 0.80
    theta = 0.35

    t_sym = compute_decay_steps(s0, beta_sym, theta)
    assert t_sym == 4, f"Expected symmetric decay to take 4 steps, got {t_sym}"


def test_positive_momentum_update():
    """
    Positive outcome update: S_{t+1} = alpha * S_t + (1 - alpha) * 1.0
    For alpha = 0.85, starting at S_0 = 0.75:
    S_1 = 0.85 * 0.75 + 0.15 * 1.0 = 0.6375 + 0.15 = 0.7875
    """
    alpha = settings.ALPHA_SUCCESS   # 0.85
    s0 = 0.75

    s1 = alpha * s0 + (1.0 - alpha) * 1.0
    assert round(s1, 4) == 0.7875
    assert s1 > s0, "Successful execution must increase trust score"


# --- Novel Bayesian Posterior Trust Tests ---

from ai_service.trust_math import (
    beta_lcb,
    beta_trust_mean,
    beta_trust_var,
    quarantine_bound_t_star,
    should_quarantine,
)


def test_bayesian_cold_start_prior_alignment():
    """Prior Beta(3, 1) starts at exactly initial trust S_0 = 0.75."""
    mu_0 = beta_trust_mean(0, 0, alpha_0=settings.PRIOR_ALPHA, beta_0=settings.PRIOR_BETA)
    assert mu_0 == 0.75
    assert mu_0 == settings.INITIAL_TRUST


def test_bayesian_quarantine_bound_theorem_1():
    """Theorem 1: 4 consecutive failures trigger quarantine under Beta(3, 1), gamma=0.05, threshold=0.70."""
    t_star = quarantine_bound_t_star(
        alpha_0=settings.PRIOR_ALPHA,
        beta_0=settings.PRIOR_BETA,
        gamma=settings.QUARANTINE_GAMMA,
        threshold=settings.RELIABILITY_THRESHOLD,
    )
    assert t_star == 4

    assert not should_quarantine(0, 1, gamma=0.05, threshold=0.70)
    assert not should_quarantine(0, 2, gamma=0.05, threshold=0.70)
    assert not should_quarantine(0, 3, gamma=0.05, threshold=0.70)
    assert should_quarantine(0, 4, gamma=0.05, threshold=0.70)


def test_bayesian_epistemic_uncertainty_distinction():
    """
    Demonstrates the key mathematical advantage over EMA:
    A memory with 1 success and 0 failures vs 10 successes and 0 failures.
    EMA gives static numbers without variance.
    Bayesian model explicitly quantifies epistemic confidence:
    Var(10, 0) << Var(1, 0).
    """
    var_prior = beta_trust_var(0, 0, alpha_0=3.0, beta_0=1.0)  # 0.0375
    var_1 = beta_trust_var(1, 0, alpha_0=3.0, beta_0=1.0)      # 0.0267
    var_10 = beta_trust_var(10, 0, alpha_0=3.0, beta_0=1.0)    # 0.00442

    assert var_10 < var_1 < var_prior
    # Epistemic uncertainty shrunk by >8x compared to cold-start prior
    assert (var_prior / var_10) > 8.0
    # Epistemic uncertainty shrunk by >6x from 1 to 10 trials
    assert (var_1 / var_10) > 6.0

    # LCB score rewards well-proven memories
    lcb_1 = beta_lcb(1, 0, lambda_risk=1.0)
    lcb_10 = beta_lcb(10, 0, lambda_risk=1.0)
    assert lcb_10 > lcb_1

