"""
Property-based Mathematical Invariant Tests using Hypothesis.
Adversarially tests mathematical guarantees, boundaries, monotonicity, and stability of:
  - Beta-Bernoulli conjugate posterior updates
  - Uncertainty variance shrinkage
  - Pessimistic Lower Confidence Bound (LCB)
  - Regularized incomplete beta integral quarantine criterion (Theorem 1)
"""

import math
import pytest

try:
    from hypothesis import given, settings as hyp_settings, strategies as st
except ImportError as e:
    pytest.skip(f"hypothesis not installed: {e}", allow_module_level=True)


from ai_service.trust_math import (
    beta_lcb,
    beta_trust_mean,
    beta_trust_std,
    beta_trust_var,
    posterior_probability_reliable,
    quarantine_bound_t_star,
    should_quarantine,
)


# --- 1. Boundary & Validity Invariants ---

@given(st.integers(min_value=0, max_value=1_000_000), st.integers(min_value=0, max_value=1_000_000))
def test_posterior_mean_strictly_bounded(ns: int, nf: int):
    """Invariant: Posterior expectation must remain strictly within (0.0, 1.0)."""
    mu = beta_trust_mean(ns, nf)
    assert 0.0 < mu < 1.0
    assert not math.isnan(mu)
    assert not math.isinf(mu)


def test_cold_start_prior_exactness():
    """Invariant: Unobserved experiences must strictly evaluate to prior mean 0.75."""
    mu = beta_trust_mean(0, 0, alpha_0=3.0, beta_0=1.0)
    assert mu == 0.75
    sigma = beta_trust_std(0, 0, alpha_0=3.0, beta_0=1.0)
    expected_var = (3.0 * 1.0) / (16.0 * 5.0)  # 3 / 80 = 0.0375
    assert math.isclose(sigma ** 2, expected_var, rel_tol=1e-6)


# --- 2. Monotonicity Guarantees ---

@given(st.integers(min_value=0, max_value=500_000), st.integers(min_value=0, max_value=500_000))
def test_monotonicity_in_successes(ns: int, nf: int):
    """Invariant: An additional success must strictly increase trust score."""
    mu_before = beta_trust_mean(ns, nf)
    mu_after = beta_trust_mean(ns + 1, nf)
    assert mu_after > mu_before


@given(st.integers(min_value=0, max_value=500_000), st.integers(min_value=0, max_value=500_000))
def test_monotonicity_in_failures(ns: int, nf: int):
    """Invariant: An additional failure must strictly decrease trust score."""
    mu_before = beta_trust_mean(ns, nf)
    mu_after = beta_trust_mean(ns, nf + 1)
    assert mu_after < mu_before


# --- 3. Uncertainty Quantification & Variance Properties ---

@given(st.integers(min_value=0, max_value=1_000_000), st.integers(min_value=0, max_value=1_000_000))
def test_variance_non_negativity_and_bounds(ns: int, nf: int):
    """Invariant: Variance must be non-negative and bounded above by 0.25 (maximum Bernoulli variance)."""
    var = beta_trust_var(ns, nf)
    assert 0.0 <= var <= 0.25
    std = beta_trust_std(ns, nf)
    assert math.isclose(std, math.sqrt(var), rel_tol=1e-6)


@given(st.integers(min_value=1, max_value=10_000))
def test_variance_shrinks_with_evidence(n: int):
    """Invariant: As sample size increases along balanced observations, epistemic uncertainty strictly decays."""
    var_small = beta_trust_var(n, n)
    var_large = beta_trust_var(n * 10, n * 10)
    assert var_large < var_small


# --- 4. Lower Confidence Bound (LCB) Retrieval Properties ---

@given(
    st.integers(min_value=0, max_value=100_000),
    st.integers(min_value=0, max_value=100_000),
    st.floats(min_value=0.0, max_value=5.0),
)
def test_lcb_is_less_than_or_equal_to_mean(ns: int, nf: int, lmbda: float):
    """Invariant: LCB_lambda <= Mean for all non-negative risk aversion parameters lambda."""
    mu = beta_trust_mean(ns, nf)
    lcb = beta_lcb(ns, nf, lambda_risk=lmbda)
    assert lcb <= mu + 1e-9
    assert 0.0 <= lcb <= 1.0


@given(
    st.integers(min_value=0, max_value=10_000),
    st.integers(min_value=0, max_value=10_000),
    st.floats(min_value=0.0, max_value=2.0),
    st.floats(min_value=2.01, max_value=5.0),
)
def test_lcb_risk_aversion_monotonicity(ns: int, nf: int, l1: float, l2: float):
    """Invariant: Higher risk aversion lambda strictly penalizes retrieval score (or saturates at 0)."""
    lcb1 = beta_lcb(ns, nf, lambda_risk=l1)
    lcb2 = beta_lcb(ns, nf, lambda_risk=l2)
    assert lcb1 >= lcb2


# --- 5. Regularized Incomplete Beta & Theorem 1 Quarantine Proof ---

def test_theorem_1_exact_discrete_bound():
    """
    Formally verifies Theorem 1:
    Case A: Prior Beta(3, 1), significance gamma = 0.05, admissibility threshold = 0.70:
      t=1: P(theta > 0.70 | 0, 1) = 0.3483  (Active, > 0.05)
      t=2: P(theta > 0.70 | 0, 2) = 0.1631  (Active, > 0.05)
      t=3: P(theta > 0.70 | 0, 3) = 0.0705  (Active, > 0.05)
      t=4: P(theta > 0.70 | 0, 4) = 0.0288  (QUARANTINED! < 0.05)
      t* = 4 trials.

    Case B: Uninformative prior Beta(1, 1), significance gamma = 0.05, baseline threshold = 0.50:
      Closed form: P(theta > 0.50 | 0, t) = (0.50)^(1 + t)
      t=1: 0.25 > 0.05
      t=2: 0.125 > 0.05
      t=3: 0.0625 > 0.05
      t=4: 0.03125 < 0.05 -> QUARANTINED!
      t* = ceil( ln(0.05) / ln(0.50) ) - 1 = ceil(4.3219) - 1 = 5 - 1 = 4 trials.
    """
    # Case A: Operational Admissibility Standard (threshold = 0.70, prior Beta(3, 1))
    p1 = posterior_probability_reliable(0, 1, threshold=0.70, alpha_0=3.0, beta_0=1.0)
    p2 = posterior_probability_reliable(0, 2, threshold=0.70, alpha_0=3.0, beta_0=1.0)
    p3 = posterior_probability_reliable(0, 3, threshold=0.70, alpha_0=3.0, beta_0=1.0)
    p4 = posterior_probability_reliable(0, 4, threshold=0.70, alpha_0=3.0, beta_0=1.0)

    assert math.isclose(p1, 0.3483, abs_tol=1e-3)
    assert math.isclose(p2, 0.1631, abs_tol=1e-3)
    assert math.isclose(p3, 0.0705, abs_tol=1e-3)
    assert math.isclose(p4, 0.0288, abs_tol=1e-3)

    assert should_quarantine(0, 1, gamma=0.05, threshold=0.70) is False
    assert should_quarantine(0, 2, gamma=0.05, threshold=0.70) is False
    assert should_quarantine(0, 3, gamma=0.05, threshold=0.70) is False
    assert should_quarantine(0, 4, gamma=0.05, threshold=0.70) is True

    t_star_a = quarantine_bound_t_star(alpha_0=3.0, beta_0=1.0, gamma=0.05, threshold=0.70)
    assert t_star_a == 4, f"Case A bound must be exactly 4, got {t_star_a}"

    # Case B: Laplace Prior (threshold = 0.50, prior Beta(1, 1))
    t_star_b = quarantine_bound_t_star(alpha_0=1.0, beta_0=1.0, gamma=0.05, threshold=0.50)
    assert t_star_b == 4, f"Case B bound must be exactly 4, got {t_star_b}"


# --- 6. Numerical Stability Under Extreme Asymptotics ---

def test_numerical_stability_under_extreme_counts():
    """Ensures no floating point overflow, underflow, or NaN under massive usage counts."""
    huge_s = 10_000_000
    huge_f = 10_000_000

    mu = beta_trust_mean(huge_s, huge_f)
    assert math.isclose(mu, 0.5, abs_tol=1e-4)

    var = beta_trust_var(huge_s, huge_f)
    assert 0.0 <= var < 1e-6

    lcb = beta_lcb(huge_s, huge_f, lambda_risk=2.0)
    assert math.isclose(lcb, 0.5, abs_tol=1e-3)
