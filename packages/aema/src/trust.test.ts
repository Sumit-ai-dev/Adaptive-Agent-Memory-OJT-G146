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
} from './trust.js';
import { deduplicateExperiences } from './dedup.js';
import { auditMemoryBank } from './audit.js';
import { WriteAheadLog } from './wal.js';
import type { Experience } from './types.js';

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
    assert.equal(res.newScore.toFixed(3), '0.575');
    assert.equal(res.isQuarantined, false);
  });

  it('computes valid Wilson LCB interval', () => {
    const lcb = calculateWilsonLCB(24, 24);
    assert.ok(lcb > 0.85, 'Wilson lower bound for 24/24 should exceed 85%');
  });
});

describe('MemPalace-Inspired Robustness (WAL, Dedup, Audit)', () => {
  it('deduplicates near-identical experiences and retains the higher-trust version', () => {
    const experiences: Experience[] = [
      {
        id: 'exp_1',
        task: 'Fix React hydration error in SSR',
        solution: 'Use useEffect or dynamic import with ssr false',
        outcome: 'success',
        trustScore: 0.95,
        totalTrials: 5,
        consecutiveFailures: 0,
        isQuarantined: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: 'exp_2',
        task: 'Fix React hydration error in SSR',
        solution: 'Use useEffect or dynamic import with ssr false',
        outcome: 'failure',
        trustScore: 0.40,
        totalTrials: 2,
        consecutiveFailures: 1,
        isQuarantined: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    const { cleaned, report } = deduplicateExperiences(experiences, { similarityThreshold: 0.85 });
    assert.equal(cleaned.length, 1);
    assert.equal(report.duplicatesFound, 1);
    assert.equal(cleaned[0].id, 'exp_1'); // Kept exp_1 because trust is 0.95 > 0.40
  });

  it('audits memory bank health and flags negative transfer risk accurately', () => {
    const experiences: Experience[] = [
      {
        id: 'exp_1',
        task: 'Task A',
        solution: 'Sol A',
        outcome: 'success',
        trustScore: 0.95,
        totalTrials: 3,
        consecutiveFailures: 0,
        isQuarantined: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: 'exp_2',
        task: 'Task B',
        solution: 'Sol B',
        outcome: 'failure',
        trustScore: 0.25,
        totalTrials: 3,
        consecutiveFailures: 3,
        isQuarantined: true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    const audit = auditMemoryBank(experiences);
    assert.equal(audit.totalMemories, 2);
    assert.equal(audit.quarantinedCount, 1);
    assert.equal(audit.quarantineRatio, 0.5);
    assert.equal(audit.healthStatus, 'CRITICAL');
  });

  it('logs immutable records to write-ahead log', () => {
    const wal = new WriteAheadLog('/tmp/aema_test_wal');
    wal.clear();
    wal.log({
      eventType: 'STORE',
      experienceId: 'test_exp',
      newTrust: 1.0,
      quarantined: false,
    });

    const entries = wal.getRecent(10);
    assert.equal(entries.length, 1);
    assert.equal(entries[0].experienceId, 'test_exp');
    wal.clear();
  });
});
