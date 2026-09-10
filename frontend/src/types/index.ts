// ─── Domain Models matching PRD (docs/03-prd.md) ───────────────────────────

export type TaskDomain = 'research' | 'coding' | 'analysis' | 'planning' | 'general'

export type ExperienceStatus = 'active' | 'deprecated' | 'candidate'

export interface Experience {
  id: string
  taskDomain: TaskDomain
  triggerCondition: string
  strategyLesson: string
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

export type ExecutionStatus = 'pending' | 'retrieving' | 'reasoning' | 'executing' | 'reflecting' | 'completed' | 'failed'

export interface ExecutionStepTrace {
  id: string
  type: 'retrieval' | 'thought' | 'action' | 'reflection' | 'trust_update'
  timestamp: string
  title: string
  detail: string
  metadata?: Record<string, unknown>
}

export interface TaskExecution {
  id: string
  userId?: string
  taskInput: string
  taskDomain: TaskDomain
  memoryEnabled: boolean
  status: ExecutionStatus
  retrievedExperiences: {
    experience: Experience
    relevanceScore: number
  }[]
  finalOutput?: string
  reflectionLesson?: string
  newExperienceCreated?: boolean
  trustUpdates: {
    experienceId: string
    oldScore: number
    newScore: number
  }[]
  tokensUsed: number
  latencyMs: number
  outcomeQuality?: 'positive' | 'neutral' | 'negative'
  createdAt: string
}

export interface AgentMetricSummary {
  totalTasks: number
  activeMemories: number
  memoryHitRate: number // percentage, e.g. 87%
  slaAdherence: number // percentage, e.g. 99.9%
  avgTimeSavedMin: number
  tokensSaved: string // e.g. '2.4M'
  memoryReuseRate: number // percentage, e.g. 76%
  aiDeflectionRate: number // percentage, e.g. 80%
  mttrMin: number // e.g. 6 min
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
