"""
Rigorous Bayesian Trust Mathematics & Statistical Inference Engine.
Replaces arbitrary heuristic constants with conjugate Beta-Bernoulli posterior updates,
uncertainty quantification, Lower Confidence Bound (LCB) retrieval, and incomplete
beta integral hypothesis testing for quarantine.
"""

import math
from typing import Tuple
import numpy as np
import scipy.special as sc


def beta_trust_mean(
    successes: int,
    failures: int,
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
) -> float:
    """
    Computes the posterior expectation of experience reliability:
    E[theta | n_s, n_f] = (alpha_0 + n_s) / (alpha_0 + beta_0 + n_s + n_f)

    With default weakly-informative prior Beta(3, 1), the initial trust at n_s=0, n_f=0
    is exactly 3 / (3 + 1) = 0.75 (aligning with S_0 = 0.75).
    """
    if successes < 0 or failures < 0:
        raise ValueError("Successes and failures must be non-negative integers.")
    if alpha_0 <= 0 or beta_0 <= 0:
        raise ValueError("Prior parameters alpha_0 and beta_0 must be strictly positive.")

    alpha_post = alpha_0 + float(successes)
    beta_post = beta_0 + float(failures)
    return float(alpha_post / (alpha_post + beta_post))


def beta_trust_var(
    successes: int,
    failures: int,
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
) -> float:
    """
    Computes the posterior variance of experience reliability:
    Var[theta | n_s, n_f] = (alpha * beta) / ((alpha + beta)^2 * (alpha + beta + 1))

    Quantifies epistemic uncertainty. Monotonically decays towards 0 as n_s + n_f -> inf.
    """
    if successes < 0 or failures < 0:
        raise ValueError("Successes and failures must be non-negative integers.")
    if alpha_0 <= 0 or beta_0 <= 0:
        raise ValueError("Prior parameters alpha_0 and beta_0 must be strictly positive.")

    alpha_post = alpha_0 + float(successes)
    beta_post = beta_0 + float(failures)
    total = alpha_post + beta_post
    return float((alpha_post * beta_post) / ((total ** 2) * (total + 1.0)))


def beta_trust_std(
    successes: int,
    failures: int,
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
) -> float:
    """Computes posterior standard deviation sigma = sqrt(Var)."""
    return float(math.sqrt(beta_trust_var(successes, failures, alpha_0, beta_0)))


def beta_lcb(
    successes: int,
    failures: int,
    lambda_risk: float = 1.0,
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
) -> float:
    """
    Computes the Lower Confidence Bound (LCB) of reliability:
    LCB_lambda = max(0.0, mu - lambda * sigma)

    Penalizes untested or uncertain memories.
    - lambda = 0.0: Risk-neutral (uses posterior mean).
    - lambda = 1.0: Moderate risk-aversion (1-sigma, ~84% one-sided confidence).
    - lambda = 2.0: Conservative (2-sigma, ~97.5% one-sided confidence).
    """
    if lambda_risk < 0.0:
        raise ValueError("Risk aversion parameter lambda_risk must be non-negative.")

    mu = beta_trust_mean(successes, failures, alpha_0, beta_0)
    sigma = beta_trust_std(successes, failures, alpha_0, beta_0)
    score = mu - (lambda_risk * sigma)
    return float(max(0.0, min(1.0, score)))


def posterior_probability_reliable(
    successes: int,
    failures: int,
    threshold: float = 0.70,
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
) -> float:
    """
    Calculates P(theta > threshold | n_s, n_f) using the Regularized Incomplete Beta function:
    P(theta > threshold) = 1.0 - I_{threshold}(alpha_post, beta_post)

    By default, threshold = 0.70 represents the operational admissibility standard for
    active memories in the agent store.
    """
    if not (0.0 < threshold < 1.0):
        raise ValueError("Reliability threshold must be strictly between 0 and 1.")

    alpha_post = alpha_0 + float(successes)
    beta_post = beta_0 + float(failures)
    cdf_at_thresh = float(sc.betainc(alpha_post, beta_post, threshold))
    return float(max(0.0, min(1.0, 1.0 - cdf_at_thresh)))


def should_quarantine(
    successes: int,
    failures: int,
    gamma: float = 0.05,
    threshold: float = 0.70,
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
) -> bool:
    """
    Theorem 1 Statistical Quarantine Criterion:
    Quarantines an experience if the posterior probability that its true reliability
    exceeds the operational admissibility standard (threshold = 0.70) falls below
    significance level gamma (default 0.05):
    P(theta > 0.70 | n_s, n_f) < gamma  <=>  I_{0.70}(alpha_post, beta_post) > 1.0 - gamma.
    """
    prob_reliable = posterior_probability_reliable(
        successes=successes,
        failures=failures,
        threshold=threshold,
        alpha_0=alpha_0,
        beta_0=beta_0,
    )
    return prob_reliable < gamma


def quarantine_bound_t_star(
    alpha_0: float = 3.0,
    beta_0: float = 1.0,
    gamma: float = 0.05,
    threshold: float = 0.70,
    max_trials: int = 20,
) -> int:
    """
    Finds the minimum consecutive failure count t* that triggers quarantine:
    t* = min { t in N : P(theta > threshold | 0, t) < gamma }

    For prior Beta(3, 1), threshold 0.70, gamma 0.05:
      t=1: P(theta > 0.70) = 0.3483  (Active)
      t=2: P(theta > 0.70) = 0.1631  (Active)
      t=3: P(theta > 0.70) = 0.0705  (Active)
      t=4: P(theta > 0.70) = 0.0288  (< 0.05 -> QUARANTINED!)
    Yielding exactly t* = 4 trials.
    """
    for t in range(1, max_trials + 1):
        if should_quarantine(0, t, gamma=gamma, threshold=threshold, alpha_0=alpha_0, beta_0=beta_0):
            return t
    return max_trials


# --- Legacy / Baseline Comparators for Empirical Ablations (Conditions A, B, C) ---

def asymmetric_ema_update(
    old_trust: float,
    outcome_score: float,
    alpha_success: float = 0.85,
    beta_failure: float = 0.70,
    success_threshold: float = 0.80,
) -> float:
    """Piecewise Asymmetric Exponential Moving Average (Ablation Condition D-legacy)."""
    if outcome_score >= success_threshold:
        updated = (alpha_success * old_trust) + ((1.0 - alpha_success) * 1.0)
    else:
        updated = beta_failure * old_trust
    return float(max(0.0, min(1.0, round(updated, 4))))


def symmetric_ema_update(
    old_trust: float,
    outcome_score: float,
    alpha_symmetric: float = 0.80,
) -> float:
    """Symmetric Exponential Moving Average (Ablation Condition C: Reflexion baseline)."""
    updated = (alpha_symmetric * old_trust) + ((1.0 - alpha_symmetric) * outcome_score)
    return float(max(0.0, min(1.0, round(updated, 4))))
