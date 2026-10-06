import {
  Experience,
  TaskExecution,
  AgentMetricSummary,
  TaskDomain,
  AgentConfig,
  ProviderOption,
} from '../types'
import { getCurrentSession } from '../lib/supabase'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ─── Supported Provider Configurations (Verified in Backend Gateway) ────────
export const SUPPORTED_PROVIDERS: ProviderOption[] = [
  {
    id: 'mock',
    name: 'Local Test Engine (Mock)',
    models: ['mock-deterministic-v1'],
    defaultModel: 'mock-deterministic-v1',
    requiresKey: false,
    description: 'Deterministic 5-node LangGraph emulator. Runs without external API keys.',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    models: ['gpt-4o-mini', 'gpt-4o'],
    defaultModel: 'gpt-4o-mini',
    requiresKey: true,
    description: 'Requires an OpenAI API key (BYOK) or OPENAI_API_KEY in backend environment.',
  },
  {
    id: 'groq',
    name: 'Groq Cloud',
    models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant'],
    defaultModel: 'llama-3.3-70b-versatile',
    requiresKey: true,
    description: 'High-speed cloud inference. Requires Groq API key (BYOK) or GROQ_API_KEY in backend.',
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    models: ['qwen2.5:1.5b', 'llama3.2:3b', 'deepseek-r1:1.5b'],
    defaultModel: 'qwen2.5:1.5b',
    requiresKey: false,
    description: 'Connects to local Ollama daemon at http://localhost:11434/v1.',
  },
]

// ─── Real Agent Task Execution (POST /api/agent/execute) ────────────────────

export interface ExecuteAgentTaskParams {
  taskInput: string
  config: AgentConfig
}

export async function executeAgentTask({
  taskInput,
  config,
}: ExecuteAgentTaskParams): Promise<TaskExecution> {
  const session = await getCurrentSession()
  const token = session.session?.access_token

  const payload: Record<string, unknown> = {
    taskInput: taskInput.trim(),
    taskDomain: config.domain,
    domain: config.domain,
    memoryEnabled: config.memoryEnabled,
    memoryMode: config.memoryMode,
    provider: config.provider,
    model: config.model,
  }

  // Supply BYOK API key if user entered one
  if (config.apiKey && config.apiKey.trim().length > 0) {
    payload.apiKey = config.apiKey.trim()
  }

  const res = await fetch(`${API_BASE_URL}/api/agent/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let errorDetail = `Backend returned status ${res.status}`
    try {
      const errJson = await res.json()
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail)
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail)
  }

  const data: TaskExecution = await res.json()
  return data
}

// ─── Real Telemetry KPIs (GET /api/telemetry) ────────────────────────────────

export async function fetchTelemetryMetrics(): Promise<AgentMetricSummary> {
  const session = await getCurrentSession()
  const token = session.session?.access_token

  const res = await fetch(`${API_BASE_URL}/api/telemetry`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!res.ok) {
    throw new Error(`Failed to load telemetry (status ${res.status})`)
  }

  return res.json()
}

// ─── Real Memory Retrieval (GET /api/memories) ──────────────────────────────

export interface FetchMemoriesParams {
  domain?: TaskDomain | 'all'
  status?: string
  minTrust?: number
  search?: string
  limit?: number
  offset?: number
}

export async function fetchExperiences(params?: FetchMemoriesParams): Promise<Experience[]> {
  const session = await getCurrentSession()
  const token = session.session?.access_token

  const queryParams = new URLSearchParams()
  if (params?.domain && params.domain !== 'all') {
    queryParams.set('domain', params.domain)
  }
  if (params?.status && params.status !== 'all') {
    queryParams.set('status', params.status)
  }
  if (params?.minTrust !== undefined) {
    queryParams.set('min_trust', params.minTrust.toString())
  }
  if (params?.search && params.search.trim().length > 0) {
    queryParams.set('search', params.search.trim())
  }
  if (params?.limit) {
    queryParams.set('limit', params.limit.toString())
  }
  if (params?.offset) {
    queryParams.set('offset', params.offset.toString())
  }

  const url = `${API_BASE_URL}/api/memories${queryParams.toString() ? `?${queryParams.toString()}` : ''}`

  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!res.ok) {
    throw new Error(`Failed to load memories (status ${res.status})`)
  }

  const data = await res.json()
  return Array.isArray(data) ? data : []
}

// ─── Real Execution History (GET /api/agent/executions) ──────────────────────

export interface FetchExecutionsParams {
  domain?: string
  memoryMode?: string
  limit?: number
  offset?: number
}

export interface ExecutionListResponse {
  total: number
  items: TaskExecution[]
}

export async function fetchExecutions(params?: FetchExecutionsParams): Promise<ExecutionListResponse> {
  const session = await getCurrentSession()
  const token = session.session?.access_token

  const queryParams = new URLSearchParams()
  if (params?.domain && params.domain !== 'all') {
    queryParams.set('domain', params.domain)
  }
  if (params?.memoryMode && params.memoryMode !== 'all') {
    queryParams.set('memory_mode', params.memoryMode)
  }
  if (params?.limit) {
    queryParams.set('limit', params.limit.toString())
  }
  if (params?.offset) {
    queryParams.set('offset', params.offset.toString())
  }

  const url = `${API_BASE_URL}/api/agent/executions${queryParams.toString() ? `?${queryParams.toString()}` : ''}`

  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!res.ok) {
    throw new Error(`Failed to load executions (status ${res.status})`)
  }

  return res.json()
}

// ─── Single Execution Trace (GET /api/agent/executions/{id}) ────────────────

export async function fetchExecutionTrace(executionId: string): Promise<TaskExecution> {
  const session = await getCurrentSession()
  const token = session.session?.access_token

  const res = await fetch(`${API_BASE_URL}/api/agent/executions/${executionId}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!res.ok) {
    throw new Error(`Failed to fetch trace for execution ${executionId}`)
  }

  return res.json()
}
