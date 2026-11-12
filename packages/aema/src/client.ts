/**
 * AEMA Client: Connects to local or remote AEMA Memory Gateway.
 * Supports persistent local JSON fallback store, remote FastAPI /api/v1 sync,
 * WAL audit trails, and deduplication.
 */

import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
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

const VALID_BACKEND_DOMAINS = new Set(['research', 'coding', 'analysis', 'planning', 'general']);

function tokenizeNormalized(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 0);
}

function normalizeBackendDomain(domain?: unknown): string | undefined {
  if (typeof domain !== 'string' || !domain.trim()) return undefined;
  const d = domain.trim().toLowerCase();
  return VALID_BACKEND_DOMAINS.has(d) ? d : 'general';
}

function mapBackendExperience(raw: Record<string, any>, fallback?: Partial<Experience>): Experience {
  const trustScore =
    typeof raw.trustScore === 'number'
      ? raw.trustScore
      : typeof raw.trust_score === 'number'
        ? raw.trust_score
        : (fallback?.trustScore ?? 0.75);
  const status = String(raw.status ?? 'active').toLowerCase();
  const consecutiveFailures =
    raw.consecutiveFailures ?? raw.consecutive_failures ?? fallback?.consecutiveFailures ?? 0;
  const failuresCount = raw.failuresCount ?? raw.failures_count ?? fallback?.consecutiveFailures ?? 0;
  const usesCount = raw.usesCount ?? raw.uses_count ?? fallback?.totalTrials ?? 1;

  return {
    id: String(raw.id ?? fallback?.id ?? `exp_${Date.now()}`),
    task: String(raw.task ?? raw.triggerCondition ?? raw.trigger_condition ?? fallback?.task ?? ''),
    solution: String(
      raw.solution ?? raw.strategyLesson ?? raw.strategy_lesson ?? fallback?.solution ?? ''
    ),
    outcome:
      raw.outcome ??
      (failuresCount > 0 && status === 'deprecated' ? 'failure' : (fallback?.outcome ?? 'success')),
    trustScore,
    totalTrials: Number(raw.totalTrials ?? usesCount),
    consecutiveFailures: Number(consecutiveFailures),
    isQuarantined:
      typeof raw.isQuarantined === 'boolean'
        ? raw.isQuarantined
        : status === 'deprecated' || isQuarantined(trustScore),
    metadata: {
      ...(fallback?.metadata ?? {}),
      domain: raw.taskDomain ?? raw.task_domain ?? fallback?.metadata?.domain,
      pitfall: raw.pitfall ?? raw.pitfallWarning ?? fallback?.metadata?.pitfall,
      backendStatus: status,
    },
    createdAt: String(raw.createdAt ?? raw.created_at ?? fallback?.createdAt ?? new Date().toISOString()),
    updatedAt: String(raw.updatedAt ?? raw.updated_at ?? fallback?.updatedAt ?? new Date().toISOString()),
  };
}

function mapBackendMatch(item: Record<string, any>): RetrievalResult {
  const rawExp = (item.experience ?? item) as Record<string, any>;
  const experience = mapBackendExperience(rawExp);
  const relevanceScore = Number(
    item.relevanceScore ?? item.similarity ?? item.similarityScore ?? 0.8
  );
  const effectiveScore = Number(
    item.effectiveScore ??
      item.compositeScore ??
      item.composite_score ??
      0.7 * relevanceScore + 0.3 * experience.trustScore
  );
  const isReliable =
    typeof item.isReliable === 'boolean'
      ? item.isReliable
      : !experience.isQuarantined && experience.trustScore >= DEFAULT_QUARANTINE_THRESHOLD;

  return {
    experience,
    relevanceScore,
    effectiveScore,
    isReliable,
  };
}

export class AEMAClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeoutMs: number;
  private storeFile: string | null;
  private localStore: Map<string, Experience> = new Map();

  constructor(config: AEMAClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? (process.env.AEMA_API_URL || 'http://localhost:8000');
    this.apiKey = config.apiKey ?? process.env.AEMA_API_KEY;
    this.timeoutMs = config.timeoutMs ?? 10000;

    if (config.persistPath === false) {
      this.storeFile = null;
    } else if (typeof config.persistPath === 'string') {
      this.storeFile = config.persistPath;
    } else if (process.env.AEMA_STORE_PATH) {
      this.storeFile = process.env.AEMA_STORE_PATH;
    } else {
      this.storeFile = path.join(os.homedir(), '.aema', 'memories.json');
    }

    this.loadLocalStore();
  }

  private loadLocalStore(): void {
    if (!this.storeFile) return;
    try {
      if (!fs.existsSync(this.storeFile)) return;
      const raw = fs.readFileSync(this.storeFile, 'utf-8');
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        for (const item of parsed) {
          if (item && typeof item.id === 'string') {
            this.localStore.set(item.id, item as Experience);
          }
        }
      }
    } catch {
      // Side-effect-free fallback if local cache is unreadable
    }
  }

  private saveLocalStore(): void {
    if (!this.storeFile) return;
    try {
      const dir = path.dirname(this.storeFile);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
      }
      const data = JSON.stringify(Array.from(this.localStore.values()), null, 2);
      const tmpFile = `${this.storeFile}.${process.pid}.${Math.random().toString(36).slice(2, 8)}.tmp`;
      fs.writeFileSync(tmpFile, data, { encoding: 'utf-8', mode: 0o600 });
      fs.renameSync(tmpFile, this.storeFile);
    } catch {
      // Never crash execution if filesystem persistence fails
    }
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

    // Sync with FastAPI /api/v1/memories using backend Experience schema
    try {
      if (this.baseUrl && !this.baseUrl.includes('localhost:0')) {
        const res = await this.fetchWithTimeout(`${this.baseUrl}/api/v1/memories`, {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({
            id: experience.id,
            taskDomain: normalizeBackendDomain(newExp.metadata?.domain) ?? 'general',
            triggerCondition: newExp.task,
            strategyLesson: newExp.solution,
            pitfall: typeof newExp.metadata?.pitfall === 'string' ? newExp.metadata.pitfall : null,
            confidence: initialTrust,
            trustScore: initialTrust,
          }),
        });
        if (res.ok) {
          const remoteRaw = (await res.json()) as Record<string, any>;
          const remoteExp = mapBackendExperience(remoteRaw, experience);
          this.localStore.set(remoteExp.id, remoteExp);
          this.saveLocalStore();
          return remoteExp;
        }
      }
    } catch {
      // Remote unavailable; fall back to local persistent store
    }

    this.localStore.set(experience.id, experience);
    this.saveLocalStore();
    return experience;
  }

  /**
   * Retrieve reliable, non-quarantined memories matching a query.
   */
  async retrieve(query: RetrievalQuery | string): Promise<RetrievalResult[]> {
    const options: RetrievalQuery = typeof query === 'string' ? { query } : query;
    const topK = options.topK ?? 5;
    const minTrust = options.minTrustScore ?? DEFAULT_QUARANTINE_THRESHOLD;
    const backendDomain =
      options.domain && VALID_BACKEND_DOMAINS.has(options.domain.toLowerCase())
        ? options.domain.toLowerCase()
        : undefined;

    try {
      if (this.baseUrl && !this.baseUrl.includes('localhost:0')) {
        const res = await this.fetchWithTimeout(`${this.baseUrl}/api/v1/memories/search`, {
          method: 'POST',
          headers: this.getHeaders(),
          body: JSON.stringify({
            query: options.query,
            top_k: topK,
            min_trust: minTrust,
            ...(backendDomain ? { domain: backendDomain } : {}),
          }),
        });
        if (res.ok) {
          const rawList = (await res.json()) as Record<string, any>[];
          if (Array.isArray(rawList)) {
            return rawList.map(mapBackendMatch);
          }
        }
      }
    } catch {
      // Fallback to local ranking
    }

    // Local semantic matching via keyword overlap & domain filtering
    let candidatesList = Array.from(this.localStore.values());
    if (options.domain) {
      candidatesList = candidatesList.filter((e) => e.metadata?.domain === options.domain);
    }

    const queryTokens = new Set(tokenizeNormalized(options.query));
    const candidates = candidatesList.map((exp) => {
      const taskTokens = new Set(tokenizeNormalized(`${exp.task} ${exp.solution}`));
      let overlap = 0;
      for (const token of queryTokens) {
        if (taskTokens.has(token)) overlap += 1;
      }
      const semanticRelevance = queryTokens.size > 0 ? Math.min(1.0, overlap / queryTokens.size + 0.2) : 0.5;
      return { experience: exp, semanticRelevance };
    });

    return rankByReliability(candidates, { minTrust, topK });
  }

  /**
   * Synchronize local cache with remote FastAPI /api/v1/memories store when reachable.
   * Ensures audit(), status, and dedup() reflect remote database state.
   */
  async syncFromRemote(limit = 200): Promise<boolean> {
    try {
      if (!this.baseUrl || this.baseUrl.includes('localhost:0')) {
        return false;
      }
      const res = await this.fetchWithTimeout(`${this.baseUrl}/api/v1/memories?limit=${limit}`, {
        method: 'GET',
        headers: this.getHeaders(),
      });
      if (!res.ok) return false;
      const items = (await res.json()) as Record<string, any>[];
      if (!Array.isArray(items)) return false;

      for (const raw of items) {
        const mapped = mapBackendExperience(raw);
        this.localStore.set(mapped.id, mapped);
      }
      this.saveLocalStore();
      return true;
    } catch {
      return false;
    }
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
    let result = calculateAsymmetricEMA(currentScore, outcome, options);
    let syncedFromRemote = false;

    try {
      if (this.baseUrl && !this.baseUrl.includes('localhost:0')) {
        const res = await this.fetchWithTimeout(
          `${this.baseUrl}/api/v1/memories/${experienceId}/feedback`,
          {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ outcome }),
          }
        );
        if (res.ok) {
          const payload = (await res.json()) as Record<string, any>;
          const remoteExpRaw = payload.experience as Record<string, any> | undefined;
          const tu = (payload.trustUpdate ?? payload.trust_update) as Record<string, any> | undefined;

          if (tu) {
            const previousScore = Number(tu.oldScore ?? tu.old_score ?? currentScore);
            const newScore = Number(tu.newScore ?? tu.new_score ?? result.newScore);
            const threshold = options?.quarantineThreshold ?? DEFAULT_QUARANTINE_THRESHOLD;
            result = {
              previousScore,
              newScore,
              outcome,
              isQuarantined: newScore < threshold,
              decayDelta: Number((tu.delta ?? newScore - previousScore).toFixed(4)),
            };
          }

          if (remoteExpRaw) {
            const mapped = mapBackendExperience(remoteExpRaw, exp);
            this.localStore.set(experienceId, mapped);
            this.saveLocalStore();
            syncedFromRemote = true;
          }
        }
      }
    } catch {
      // Remote unavailable; rely on local A-EMA computation below
    }

    if (!syncedFromRemote && exp) {
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
      this.saveLocalStore();
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
      this.saveLocalStore();
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
