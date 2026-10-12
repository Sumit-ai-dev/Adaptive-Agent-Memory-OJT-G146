/**
 * AEMA Client: Connects to local or remote AEMA Memory Gateway.
 * Supports standalone in-memory mode, remote API mode, WAL audit trails, and dedup.
 */

import type {
  AEMAClientConfig,
  Experience,
  NewExperience,
  OutcomeType,
  RetrievalQuery,
  RetrievalResult,
  TrustUpdateOptions,
  TrustUpdateResult,
} from './types.js';
import {
  calculateAsymmetricEMA,
  isQuarantined,
  DEFAULT_QUARANTINE_THRESHOLD,
  rankByReliability,
} from './trust.js';
import { globalWAL, type WALEntry } from './wal.js';
import { deduplicateExperiences, type DedupResult } from './dedup.js';
import { auditMemoryBank, type AuditReport } from './audit.js';

export class AEMAClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeoutMs: number;
  private localStore: Map<string, Experience> = new Map();

  constructor(config: AEMAClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? (process.env.AEMA_API_URL || 'http://localhost:8000');
    this.apiKey = config.apiKey ?? process.env.AEMA_API_KEY;
    this.timeoutMs = config.timeoutMs ?? 10000;
  }

  /**
   * Store a new experiential memory and record WAL entry.
   */
  async store(newExp: NewExperience): Promise<Experience> {
    const initialTrust = newExp.initialTrust ?? 1.0;
    const now = new Date().toISOString();
    const isQuar = isQuarantined(initialTrust);

    const experience: Experience = {
      id: `exp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      task: newExp.task,
      solution: newExp.solution,
      outcome: newExp.outcome ?? 'success',
      trustScore: initialTrust,
      totalTrials: 1,
      consecutiveFailures: newExp.outcome === 'failure' ? 1 : 0,
      isQuarantined: isQuar,
      metadata: newExp.metadata,
      createdAt: now,
      updatedAt: now,
    };

    // Log to Write-Ahead Log
    globalWAL.log({
      eventType: 'STORE',
      experienceId: experience.id,
      domain: newExp.metadata?.domain as string | undefined,
      newTrust: initialTrust,
      quarantined: isQuar,
      metadata: { taskLength: newExp.task.length },
    });

    // If remote API is available, attempt remote sync; otherwise save locally
    try {
      if (this.baseUrl && !this.baseUrl.includes('localhost:0')) {
        const res = await this.fetchWithTimeout(`${this.baseUrl}/api/v1/memories`, {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify(experience),
        });
        if (res.ok) {
          const remoteExp = (await res.json()) as Experience;
          this.localStore.set(remoteExp.id, remoteExp);
          return remoteExp;
        }
      }
    } catch {
      // Remote unavailable; fall back to local store
    }

    this.localStore.set(experience.id, experience);
    return experience;
  }

  /**
   * Retrieve reliable, non-quarantined memories matching a query.
   */
  async retrieve(query: RetrievalQuery | string): Promise<RetrievalResult[]> {
    const options: RetrievalQuery = typeof query === 'string' ? { query } : query;
    const topK = options.topK ?? 5;
    const minTrust = options.minTrustScore ?? DEFAULT_QUARANTINE_THRESHOLD;

    try {
      if (this.baseUrl && !this.baseUrl.includes('localhost:0')) {
        const res = await this.fetchWithTimeout(`${this.baseUrl}/api/v1/memories/search`, {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({
            query: options.query,
            top_k: topK,
            min_trust: minTrust,
            domain: options.domain,
          }),
        });
        if (res.ok) {
          return (await res.json()) as RetrievalResult[];
        }
      }
    } catch {
      // Fallback to local ranking
    }

    // Local semantic mock matching via keyword overlap & domain filtering
    let candidatesList = Array.from(this.localStore.values());
    if (options.domain) {
      candidatesList = candidatesList.filter((e) => e.metadata?.domain === options.domain);
    }

    const queryTokens = new Set(options.query.toLowerCase().split(/\s+/).filter(Boolean));
    const candidates = candidatesList.map((exp) => {
      const taskTokens = exp.task.toLowerCase().split(/\s+/);
      const overlap = taskTokens.filter((t) => queryTokens.has(t)).length;
      const semanticRelevance = queryTokens.size > 0 ? Math.min(1.0, overlap / queryTokens.size + 0.2) : 0.5;
      return { experience: exp, semanticRelevance };
    });

    return rankByReliability(candidates, { minTrust, topK });
  }

  /**
   * Record outcome feedback, update trust via A-EMA, and log to WAL.
   */
  async recordFeedback(
    experienceId: string,
    outcome: OutcomeType,
    options?: TrustUpdateOptions
  ): Promise<TrustUpdateResult> {
    const exp = this.localStore.get(experienceId);
    const currentScore = exp ? exp.trustScore : 1.0;

    const result = calculateAsymmetricEMA(currentScore, outcome, options);

    if (exp) {
      exp.trustScore = result.newScore;
      exp.totalTrials += 1;
      exp.outcome = outcome;
      if (outcome === 'failure') {
        exp.consecutiveFailures += 1;
      } else {
        exp.consecutiveFailures = 0;
      }
      exp.isQuarantined = result.isQuarantined;
      exp.updatedAt = new Date().toISOString();
      this.localStore.set(experienceId, exp);
    }

    // Write-Ahead Log audit
    globalWAL.log({
      eventType: result.isQuarantined ? 'QUARANTINE' : 'FEEDBACK',
      experienceId,
      domain: exp?.metadata?.domain as string | undefined,
      outcome,
      previousTrust: result.previousScore,
      newTrust: result.newScore,
      quarantined: result.isQuarantined,
    });

    try {
      if (this.baseUrl && !this.baseUrl.includes('localhost:0')) {
        await this.fetchWithTimeout(`${this.baseUrl}/api/v1/memories/${experienceId}/feedback`, {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({ outcome, new_score: result.newScore }),
        });
      }
    } catch {
      // Ignore remote errors
    }

    return result;
  }

  /**
   * Offline deduplication sweep across stored experiences.
   */
  dedup(options?: { threshold?: number; dryRun?: boolean; domain?: string }): DedupResult {
    const all = Array.from(this.localStore.values());
    const { cleaned, report } = deduplicateExperiences(all, {
      similarityThreshold: options?.threshold,
      dryRun: options?.dryRun,
      domain: options?.domain,
    });

    if (!options?.dryRun) {
      this.localStore.clear();
      for (const item of cleaned) {
        this.localStore.set(item.id, item);
      }
    }

    return report;
  }

  /**
   * Memory bank health audit report.
   */
  audit(): AuditReport {
    return auditMemoryBank(Array.from(this.localStore.values()));
  }

  /**
   * Get recent WAL audit records.
   */
  getWAL(limit = 20): WALEntry[] {
    return globalWAL.getRecent(limit);
  }

  /**
   * Return all stored experiences.
   */
  getAll(): Experience[] {
    return Array.from(this.localStore.values());
  }

  /**
   * List all quarantined experiences.
   */
  getQuarantined(): Experience[] {
    return Array.from(this.localStore.values()).filter((e) => e.isQuarantined);
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  private async fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }
  }
}
