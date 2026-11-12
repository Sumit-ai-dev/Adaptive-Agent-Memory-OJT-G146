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
  it('correctly calculates Theorem 1 deterministic quarantine failure count k*=3 and exact integer boundaries', () => {
    const kStar = computeQuarantineSteps(1.0, DEFAULT_QUARANTINE_THRESHOLD, DEFAULT_BETA);
    assert.equal(kStar, 3);
    assert.equal(computeQuarantineSteps(0.75, DEFAULT_QUARANTINE_THRESHOLD, DEFAULT_BETA), 3);
    // Exact integer boundary: ln(0.5 / 1.0) / ln(0.5) = 1.0, must require 2 steps for strict < 0.5
    assert.equal(computeQuarantineSteps(1.0, 0.5, 0.5), 2);
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

describe('Multi-LLM Adapters (Claude, Cursor, OpenAI, Grok, Gemini)', () => {
  it('dispatches OpenAI / Grok tool calls seamlessly', async () => {
    const { handleOpenAIToolCall, openAITools } = await import('./adapters.js');
    assert.equal(openAITools.length, 4);

    const storeRes = await handleOpenAIToolCall('aema_store', {
      task: 'Solve quadratic equation',
      solution: 'Use quadratic formula -b +- sqrt(b^2 - 4ac) / 2a',
      initialTrust: 1.0,
      domain: 'math',
    });
    const parsed = JSON.parse(storeRes);
    assert.equal(parsed.trustScore, 1.0);

    const auditRes = await handleOpenAIToolCall('aema_audit', {});
    const auditObj = JSON.parse(auditRes);
    assert.ok(auditObj.totalMemories >= 1);
  });

  it('dispatches Gemini tool calls seamlessly', async () => {
    const { handleGeminiToolCall, geminiTools } = await import('./adapters.js');
    assert.equal(geminiTools[0].functionDeclarations.length, 4);

    const res = await handleGeminiToolCall('aema_audit', {});
    assert.ok(res.totalMemories !== undefined);
  });
});

describe('AEMAClient Persistence & FastAPI Remote Mapping', () => {
  it('persists offline memories to disk across client restarts', async () => {
    const fs = await import('node:fs');
    const os = await import('node:os');
    const path = await import('node:path');
    const { AEMAClient } = await import('./client.js');

    const tmpStore = path.join(os.tmpdir(), `aema_persist_test_${Date.now()}.json`);
    try {
      const writer = new AEMAClient({ baseUrl: 'http://localhost:0', persistPath: tmpStore });
      const stored = await writer.store({
        task: 'Handle SQLite WAL checkpointing',
        solution: 'Run PRAGMA wal_checkpoint(TRUNCATE)',
        metadata: { domain: 'coding' },
      });

      const reader = new AEMAClient({ baseUrl: 'http://localhost:0', persistPath: tmpStore });
      const hits = await reader.retrieve('sqlite wal');
      assert.equal(hits.length, 1);
      assert.equal(hits[0].experience.id, stored.id);
      assert.equal(hits[0].experience.solution, 'Run PRAGMA wal_checkpoint(TRUNCATE)');
    } finally {
      if (fs.existsSync(tmpStore)) fs.unlinkSync(tmpStore);
    }
  });

  it('syncs remote memories into localStore for audit() and matches punctuation-normalized tokens', async () => {
    const { AEMAClient } = await import('./client.js');
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () =>
      new Response(
        JSON.stringify([
          {
            id: 'exp-sync-1',
            taskDomain: 'coding',
            triggerCondition: 'SQLite, WAL mode deadlock!',
            strategyLesson: 'Use busy_timeout=30000.',
            trustScore: 0.9,
            status: 'active',
          },
        ]),
        { status: 200 }
      )) as typeof fetch;

    try {
      const client = new AEMAClient({ baseUrl: 'http://mock-aema.local', persistPath: false });
      const synced = await client.syncFromRemote();
      assert.equal(synced, true);
      assert.equal(client.audit().totalMemories, 1);
    } finally {
      globalThis.fetch = originalFetch;
    }

    const offlineClient = new AEMAClient({ baseUrl: 'http://localhost:0', persistPath: false });
    await offlineClient.store({
      task: 'SQLite, WAL-mode deadlock!',
      solution: 'Enable WAL.',
    });
    const hits = await offlineClient.retrieve('sqlite wal');
    assert.equal(hits.length, 1);
  });

  it('maps store/retrieve/feedback cleanly with FastAPI /api/v1 ExperienceMatch schemas', async () => {
    const { AEMAClient } = await import('./client.js');
    const originalFetch = globalThis.fetch;
    let postedStoreBody: Record<string, any> = {};

    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/v1/memories')) {
        postedStoreBody = JSON.parse(String(init?.body || '{}'));
        return new Response(
          JSON.stringify({
            id: postedStoreBody.id,
            taskDomain: 'coding',
            triggerCondition: postedStoreBody.triggerCondition,
            strategyLesson: postedStoreBody.strategyLesson,
            trustScore: 0.5,
            status: 'candidate',
          }),
          { status: 201 }
        );
      }
      if (url.endsWith('/api/v1/memories/search')) {
        return new Response(
          JSON.stringify([
            {
              experience: {
                id: 'exp-remote-1',
                taskDomain: 'coding',
                triggerCondition: 'Async PG connection pool exhaustion',
                strategyLesson: 'Use max_overflow with pool_pre_ping=True',
                trustScore: 0.88,
                usesCount: 5,
                failuresCount: 0,
                status: 'active',
              },
              similarity: 0.92,
              compositeScore: 0.908,
            },
          ]),
          { status: 200 }
        );
      }
      if (url.includes('/feedback')) {
        return new Response(
          JSON.stringify({
            experience: {
              id: 'exp-remote-1',
              taskDomain: 'coding',
              triggerCondition: 'Async PG connection pool exhaustion',
              strategyLesson: 'Use max_overflow with pool_pre_ping=True',
              trustScore: 0.616,
              status: 'active',
            },
            trustUpdate: {
              oldScore: 0.88,
              newScore: 0.616,
              delta: -0.264,
            },
          }),
          { status: 200 }
        );
      }
      return new Response('{}', { status: 404 });
    }) as typeof fetch;

    try {
      const client = new AEMAClient({ baseUrl: 'http://mock-aema.local', persistPath: false });
      const created = await client.store({
        task: 'Async PG connection pool exhaustion',
        solution: 'Use max_overflow with pool_pre_ping=True',
        metadata: { domain: 'coding' },
      });
      assert.equal(postedStoreBody.triggerCondition, 'Async PG connection pool exhaustion');
      assert.equal(postedStoreBody.strategyLesson, 'Use max_overflow with pool_pre_ping=True');
      assert.equal(created.trustScore, 0.5);

      const hits = await client.retrieve({ query: 'connection pool', domain: 'coding' });
      assert.equal(hits.length, 1);
      assert.equal(hits[0].experience.task, 'Async PG connection pool exhaustion');
      assert.equal(hits[0].effectiveScore, 0.908);
      assert.equal(hits[0].isReliable, true);

      const fb = await client.recordFeedback('exp-remote-1', 'failure');
      assert.equal(fb.previousScore, 0.88);
      assert.equal(fb.newScore, 0.616);
      assert.equal(fb.isQuarantined, false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('isolates experiences by userId and supports forget() + recover() lifecycle', async () => {
    const fs = await import('node:fs');
    const os = await import('node:os');
    const path = await import('node:path');
    const { AEMAClient } = await import('./client.js');

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'aema-ts-life-'));
    const storeFile = path.join(tmpDir, 'mem.json');

    try {
      const client = new AEMAClient({ baseUrl: 'http://localhost:0', persistPath: storeFile });
      const aliceExp = await client.store({
        userId: 'alice',
        task: 'Voice TTS response format rule',
        solution: 'Strip markdown symbols before synthesis',
        metadata: { domain: 'general' },
      });
      await client.store({
        userId: 'bob',
        task: 'Voice TTS response format rule',
        solution: 'Keep bullet lists short',
        metadata: { domain: 'general' },
      });

      const aliceHits = await client.retrieve({ query: 'Voice TTS format', userId: 'alice' });
      const bobHits = await client.retrieve({ query: 'Voice TTS format', userId: 'bob' });
      assert.equal(aliceHits.length, 1);
      assert.equal(aliceHits[0].experience.userId, 'alice');
      assert.equal(bobHits.length, 1);
      assert.equal(bobHits[0].experience.userId, 'bob');

      // Soft quarantine via forget()
      const softRemoved = await client.forget(aliceExp.id, false);
      assert.equal(softRemoved, true);
      const afterForget = await client.retrieve({ query: 'Voice TTS format', userId: 'alice' });
      assert.equal(afterForget.length, 0);

      // Recover into candidate probation
      const recovered = await client.recover(aliceExp.id, 'Unit test verified recovery');
      assert.ok(recovered);
      assert.equal(recovered?.isQuarantined, false);
      assert.equal(recovered?.metadata?.backendStatus, 'candidate');

      // Permanent GDPR erasure
      const hardRemoved = await client.forget(aliceExp.id, true);
      assert.equal(hardRemoved, true);
      assert.equal(client.list({ userId: 'alice' }).length, 0);
      assert.equal(client.list({ userId: 'bob' }).length, 1);
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });
});
