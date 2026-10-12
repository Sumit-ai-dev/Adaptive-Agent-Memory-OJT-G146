import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateAsymmetricEMA,
  computeQuarantineSteps,
  isQuarantined,
  calculateWilsonLCB,
  DEFAULT_ALPHA,
  DEFAULT_BETA,
  DEFAULT_QUARANTINE_THRESHOLD,
} from './trust.ts';

describe('AEMA Mathematical Guarantees (Theorem 1)', () => {
  it('correctly calculates Theorem 1 deterministic quarantine failure count k*=3', () => {
    const kStar = computeQuarantineSteps(1.0, DEFAULT_QUARANTINE_THRESHOLD, DEFAULT_BETA);
    assert.equal(kStar, 3);
  });

  it('quarantines experience after exactly 3 consecutive failures from S0=1.0', () => {
    let score = 1.0;
    
    // Failure 1
    const t1 = calculateAsymmetricEMA(score, 'failure');
    assert.equal(t1.newScore.toFixed(2), '0.70');
    assert.equal(t1.isQuarantined, false);
    score = t1.newScore;

    // Failure 2
    const t2 = calculateAsymmetricEMA(score, 'failure');
    assert.equal(t2.newScore.toFixed(2), '0.49');
    assert.equal(t2.isQuarantined, false);
    score = t2.newScore;

    // Failure 3 -> Drops to 0.343 < 0.35 -> Quarantine!
    const t3 = calculateAsymmetricEMA(score, 'failure');
    assert.equal(t3.newScore.toFixed(3), '0.343');
    assert.equal(t3.isQuarantined, true);
    assert.equal(isQuarantined(t3.newScore), true);
  });

  it('smoothly reinforces trust on verified success', () => {
    const res = calculateAsymmetricEMA(0.5, 'success', { alpha: 0.85 });
    // S_1 = 0.85 * 0.5 + 0.15 = 0.425 + 0.15 = 0.575
    assert.equal(res.newScore.toFixed(3), '0.575');
    assert.equal(res.isQuarantined, false);
  });

  it('computes valid Wilson LCB interval', () => {
    const lcb = calculateWilsonLCB(24, 24); // 100% win rate out of 24
    assert.ok(lcb > 0.85, 'Wilson lower bound for 24/24 should exceed 85%');
  });
});
