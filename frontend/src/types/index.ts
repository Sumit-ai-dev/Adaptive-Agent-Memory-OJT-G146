// ─── AEMA Operational Domain Types ──────────────────────────────────────────

export type TaskDomain = 'research' | 'coding' | 'analysis' | 'planning' | 'general'

export type ExperienceStatus = 'active' | 'candidate' | 'deprecated' | 'provisional' | 'quarantined'

export interface Experience {
  id: string
  taskDomain: TaskDomain
  triggerCondition: string
  strategyLesson: string
  pitfallWarning?: string
  trustScore: number // St in [0.0, 1.0]
  confidenceScore?: number // Bayesian beta uncertainty or posterior confidence
  usesCount: number
  successesCount: number
  failuresCount: number
  consecutiveFailures: number // k count for Theorem 1 quarantine
  status: ExperienceStatus
  trustTrajectory: number[] // historical values of St
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

export type ExecutionNode = 'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update'

export interface ExecutionStepTrace {
  id: string
  node: ExecutionNode
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
  status: 'pending' | 'running' | 'completed' | 'failed'
  retrievedExperiences: {
    experience: Experience
    similarityScore: number
    empiricalTrust: number
    combinedRankScore: number
  }[]
  finalOutput?: string
  reflectionLesson?: string
  trustUpdates: {
    experienceId: string
    oldScore: number
    newScore: number
    delta: number
    isQuarantined?: boolean
    formulaApplied: string
  }[]
  tokensUsed: number
  latencyMs: number
  outcomeQuality?: 'positive' | 'negative' | 'neutral'
  trajectory?: ExecutionStepTrace[]
  createdAt: string
}

export interface AgentMetricSummary {
  totalTasks: number
  activeMemories: number
  candidateMemories?: number
  quarantinedMemories: number
  meanTrustScore: number
  memoryHitRate: number // %
  negativeTransferReduction?: number // %
  timeSavedPct?: number
  tokensSavedPct?: number
  benchmarkNegativeTransferReduction?: number
  benchmarkSource?: string
}

export interface BenchmarkResult {
  suite: string
  baselineAccuracy: number
  naiveMemoryAccuracy: number
  aemaAccuracy: number
  recoveryTrial: number
  pValMcNemar: string
  datasetSize: number
  status: 'Completed' | 'Running' | 'Planned'
}

export type AvailabilityBadge = 'Available Now' | 'Demo' | 'Preview' | 'Planned'

export interface UserProfile {
  id: string
  email: string
  name?: string
  avatarUrl?: string
  createdAt: string
}
