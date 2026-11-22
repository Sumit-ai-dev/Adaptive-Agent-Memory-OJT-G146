/**
 * Core Types for Adaptive Experience Memory Agent (AEMA)
 * Reliability-Aware Experiential Memory for AI Agents
 */

export type OutcomeType = 'success' | 'failure';

export interface ExperienceMetadata {
  domain?: string;
  userId?: string;
  source?: string;
  author?: string;
  tags?: string[];
  executionTimeMs?: number;
  [key: string]: unknown;
}

export interface Experience {
  id: string;
  userId?: string;
  task: string;
  solution: string;
  outcome: OutcomeType;
  trustScore: number;
  totalTrials: number;
  consecutiveFailures: number;
  isQuarantined: boolean;
  metadata?: ExperienceMetadata;
  createdAt: string;
  updatedAt: string;
}

export interface NewExperience {
  task: string;
  solution: string;
  outcome?: OutcomeType;
  initialTrust?: number;
  userId?: string;
  metadata?: ExperienceMetadata;
}

export interface TrustUpdateOptions {
  alpha?: number; // Learning rate on success (default: 0.85)
  beta?: number;  // Decay rate on failure (default: 0.70)
  quarantineThreshold?: number; // Theorem 1 quarantine cutoff (default: 0.35)
}

export interface TrustUpdateResult {
  previousScore: number;
  newScore: number;
  outcome: OutcomeType;
  isQuarantined: boolean;
  decayDelta: number;
}

export interface RetrievalQuery {
  query: string;
  topK?: number;
  minTrustScore?: number;
  includeQuarantined?: boolean;
  domain?: string;
  userId?: string;
}

export interface RetrievalResult {
  experience: Experience;
  relevanceScore: number;
  effectiveScore: number; // Combined relevance * trust
  isReliable: boolean;
}

export interface TaskStreamOptions {
  task: string;
  domain?: string;
  userId?: string;
  sessionId?: string;
  memoryEnabled?: boolean;
  provider?: string;
  apiKey?: string;
  simulateFailure?: boolean;
}

export interface TaskStreamChunk {
  stage?: 'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update' | 'idle' | 'complete' | 'error';
  content?: string;
  node?: string;
  delta?: string;
  isComplete?: boolean;
  finalAnswer?: string;
  executionId?: string;
  latencyMs?: number;
  raw?: Record<string, unknown>;
}

export interface AEMAClientConfig {
  baseUrl?: string;
  apiKey?: string;
  userId?: string;
  timeoutMs?: number;
  persistPath?: string | false;
}
