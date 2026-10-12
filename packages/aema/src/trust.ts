/**
 * AEMA Mathematical Trust Engine
 * Implements Asymmetric Exponential Moving Average (A-EMA) and Theorem 1 Quarantine Bounds.
 */

import type { OutcomeType, TrustUpdateOptions, TrustUpdateResult, Experience, RetrievalResult } from './types.js';

export const DEFAULT_ALPHA = 0.85; // Success smoothing factor
export const DEFAULT_BETA = 0.70;  // Failure decay penalty factor
export const DEFAULT_QUARANTINE_THRESHOLD = 0.35; // Theorem 1 isolation cutoff

/**
 * Update trust score using Asymmetric Exponential Moving Average (A-EMA).
 * - On success: S_{t+1} = alpha * S_t + (1 - alpha)
 * - On failure: S_{t+1} = beta * S_t
 */
export function calculateAsymmetricEMA(
  currentScore: number,
  outcome: OutcomeType,
  options: TrustUpdateOptions = {}
): TrustUpdateResult {
  const alpha = options.alpha ?? DEFAULT_ALPHA;
  const beta = options.beta ?? DEFAULT_BETA;
  const threshold = options.quarantineThreshold ?? DEFAULT_QUARANTINE_THRESHOLD;

  // Clamp current score to [0.0, 1.0]
  const clampedCurrent = Math.max(0.0, Math.min(1.0, currentScore));

  let newScore: number;
  if (outcome === 'success') {
    newScore = alpha * clampedCurrent + (1.0 - alpha);
  } else {
    newScore = beta * clampedCurrent;
  }

  // Ensure bounded in [0.0, 1.0]
  newScore = Math.max(0.0, Math.min(1.0, newScore));
  const isQuarantined = newScore < threshold;

  return {
    previousScore: clampedCurrent,
    newScore,
    outcome,
    isQuarantined,
    decayDelta: newScore - clampedCurrent,
  };
}

/**
 * Check if a trust score violates Theorem 1 quarantine threshold.
 */
export function isQuarantined(score: number, threshold = DEFAULT_QUARANTINE_THRESHOLD): boolean {
  return score < threshold;
}

/**
 * Compute Theorem 1 deterministic quarantine failure count:
 * k* = ceil( ln(theta / S_0) / ln(beta) )
 */
export function computeQuarantineSteps(
  initialScore = 1.0,
  threshold = DEFAULT_QUARANTINE_THRESHOLD,
  beta = DEFAULT_BETA
): number {
  if (initialScore <= threshold) return 0;
  if (beta <= 0 || beta >= 1.0) throw new Error('Beta must be strictly between 0 and 1');
  return Math.ceil(Math.log(threshold / initialScore) / Math.log(beta));
}

/**
 * Compute Wilson Score 95% Lower Confidence Bound.
 */
export function calculateWilsonLCB(successes: number, total: number, z = 1.96): number {
  if (total <= 0) return 0.0;
  const p = successes / total;
  const denominator = 1.0 + (z * z) / total;
  const center = p + (z * z) / (2 * total);
  const spread = z * Math.sqrt((p * (1.0 - p) + (z * z) / (4 * total)) / total);
  return Math.max(0.0, (center - spread) / denominator);
}

/**
 * Filter and rank experiences by reliability-weighted relevance.
 */
export function rankByReliability(
  candidates: Array<{ experience: Experience; semanticRelevance: number }>,
  options: {
    minTrust?: number;
    threshold?: number;
    topK?: number;
  } = {}
): RetrievalResult[] {
  const threshold = options.threshold ?? DEFAULT_QUARANTINE_THRESHOLD;
  const minTrust = options.minTrust ?? threshold;
  const topK = options.topK ?? 5;

  const scored: RetrievalResult[] = candidates.map(({ experience, semanticRelevance }) => {
    const trust = experience.trustScore;
    const reliable = trust >= threshold && !experience.isQuarantined;
    // Effective score penalizes unverified or low-trust memories
    const effectiveScore = reliable ? semanticRelevance * Math.sqrt(trust) : semanticRelevance * 0.05;

    return {
      experience,
      relevanceScore: semanticRelevance,
      effectiveScore,
      isReliable: reliable && trust >= minTrust,
    };
  });

  return scored
    .filter((item) => item.isReliable)
    .sort((a, b) => b.effectiveScore - a.effectiveScore)
    .slice(0, topK);
}
