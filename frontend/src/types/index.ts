// ─── Domain Models matching PRD (docs/03-prd.md) ───────────────────────────

export type TaskDomain = 'research' | 'coding' | 'analysis' | 'planning' | 'general'

export type ExperienceStatus = 'active' | 'deprecated' | 'candidate'

export type ModelProvider = 'mock' | 'openai' | 'groq' | 'ollama'

export interface ProviderOption {
  id: ModelProvider
  name: string
  models: string[]
  defaultModel: string
  requiresKey: boolean
  description: string
}

export interface AgentConfig {
  domain: TaskDomain
  memoryEnabled: boolean
  memoryMode: 'adaptive' | 'naive' | 'off'
  provider: ModelProvider
  model: string
  apiKey?: string
}

export interface Experience {
  id: string
  taskDomain: TaskDomain
  triggerCondition: string
  strategyLesson: string
  pitfall?: string
  confidence?: number
  trustScore: number // 0.0 to 1.0 (e.g. 0.94)
  usesCount: number
  successesCount: number
  failuresCount: number
  status: ExperienceStatus
  embedding?: number[]
  sourceTaskId?: string
  createdAt: string
  updatedAt: string
}

export interface RetrievedMemoryItem {
  experience: Experience
  similarityScore?: number
  trustScore?: number
  compositeScore?: number
  gateReason?: string
}

export interface TrustUpdateItem {
  experienceId: string
  oldScore: number
  newScore: number
  delta: number
  reason?: string
  status?: string
}

export interface TrustHistoryRecord {
  id: string
  experienceId: string
  executionId: string
  oldTrust: number
  newTrust: number
  delta: number
  reason: string
  createdAt: string
}

export interface ExecutionStepTrace {
  id: string
  type: string
  node?: string
  title: string
  detail: string
  durationMs?: number
  toolsCalled?: string[]
  metadata?: Record<string, unknown>
}

export interface TaskExecution {
  id: string
  executionId?: string
  taskId?: string
  userId?: string
  taskInput: string
  taskDomain: TaskDomain
  memoryEnabled: boolean
  memoryMode?: string
  status: 'pending' | 'retrieving' | 'reasoning' | 'executing' | 'reflecting' | 'completed' | 'failed'
  finalOutput?: string
  finalAnswer?: string
  reflectionLesson?: string
  newExperienceCreated?: boolean
  newExperience?: Experience
  retrievedMemories?: RetrievedMemoryItem[]
  trustUpdates?: TrustUpdateItem[]
  trajectory?: ExecutionStepTrace[]
  tokensUsed?: number
  latencyMs?: number
  outcomeQuality?: 'positive' | 'neutral' | 'negative'
  outcomeScore?: number
  binaryOutcome?: number
  outcomeThreshold?: number
  evaluatorName?: string
  createdAt?: string
}

export interface AgentMetricSummary {
  totalTasks: number
  activeMemories: number
  quarantinedMemories?: number
  totalMemories?: number
  memoryHitRate: number // percentage, e.g. 87%
  slaAdherence: number // percentage, e.g. 99.9%
  avgTimeSavedMin: number
  tokensSaved: string // e.g. '2.4M'
  memoryReuseRate: number // percentage, e.g. 76%
  aiDeflectionRate: number // percentage, e.g. 80%
  mttrMin: number // e.g. 6 min
  latestBenchmarks?: Record<string, unknown>
}

export interface EvaluationComparison {
  domain: TaskDomain
  memoryOffAccuracy: number
  memoryOnAccuracy: number
  latencyReductionPct: number
  tokenReductionPct: number
  sampleCount: number
}

// ─── Supabase / Auth Types ───────────────────────────────────────────────────

export interface UserProfile {
  id: string
  email: string
  name?: string
  avatarUrl?: string
  createdAt: string
}
