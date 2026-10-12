/**
 * AEMA Client: Connects to local or remote AEMA Memory Gateway.
 * Supports both standalone in-memory mode and remote API mode.
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
   * Store a new experiential memory.
   */
  async store(newExp: NewExperience): Promise<Experience> {
    const initialTrust = newExp.initialTrust ?? 1.0;
    const now = new Date().toISOString();

    const experience: Experience = {
      id: `exp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      task: newExp.task,
      solution: newExp.solution,
      outcome: newExp.outcome ?? 'success',
      trustScore: initialTrust,
      totalTrials: 1,
      consecutiveFailures: newExp.outcome === 'failure' ? 1 : 0,
      isQuarantined: isQuarantined(initialTrust),
      metadata: newExp.metadata,
      createdAt: now,
      updatedAt: now,
    };

    // If API is available, attempt remote sync; otherwise save locally
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
          }),
        });
        if (res.ok) {
          return (await res.json()) as RetrievalResult[];
        }
      }
    } catch {
      // Fallback to local ranking
    }

    // Local semantic mock matching via keyword overlap
    const queryTokens = new Set(options.query.toLowerCase().split(/\s+/).filter(Boolean));
    const candidates = Array.from(this.localStore.values()).map((exp) => {
      const taskTokens = exp.task.toLowerCase().split(/\s+/);
      const overlap = taskTokens.filter((t) => queryTokens.has(t)).length;
      const semanticRelevance = queryTokens.size > 0 ? Math.min(1.0, overlap / queryTokens.size + 0.2) : 0.5;
      return { experience: exp, semanticRelevance };
    });

    return rankByReliability(candidates, { minTrust, topK });
  }

  /**
   * Record outcome feedback and update trust using A-EMA.
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
