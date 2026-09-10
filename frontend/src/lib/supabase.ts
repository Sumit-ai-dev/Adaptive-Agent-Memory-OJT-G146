import { createClient, SupabaseClient } from '@supabase/supabase-js'
import type { Experience, TaskExecution, TrustHistoryRecord } from '../types'

// Retrieve environment variables with fallback
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

export const isSupabaseConfigured = Boolean(
  supabaseUrl && 
  supabaseAnonKey && 
  !supabaseUrl.includes('your-project-ref') && 
  !supabaseAnonKey.includes('your-anon-key')
)

if (!isSupabaseConfigured) {
  console.info(
    '%c[Supabase]%c Credentials not detected in .env. Running with local development storage & demo mode. To connect Supabase, fill VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.',
    'color: #a855f7; font-weight: bold;',
    'color: inherit;'
  )
}

// Initialize real Supabase client or null
export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null

// ─── Authentication Helpers ──────────────────────────────────────────────────

export async function signUpWithEmail(email: string, password: string, name?: string) {
  if (!supabase) {
    // Local mock auth fallback
    const mockUser = { id: 'mock-user-1', email, user_metadata: { name: name || email.split('@')[0] } }
    localStorage.setItem('memoryagent_user', JSON.stringify(mockUser))
    return { data: { user: mockUser, session: { access_token: 'mock-token' } }, error: null }
  }
  return supabase.auth.signUp({
    email,
    password,
    options: {
      data: { name },
    },
  })
}

export async function signInWithEmail(email: string, password: string) {
  if (!supabase) {
    const mockUser = { id: 'mock-user-1', email, user_metadata: { name: email.split('@')[0] } }
    localStorage.setItem('memoryagent_user', JSON.stringify(mockUser))
    return { data: { user: mockUser, session: { access_token: 'mock-token' } }, error: null }
  }
  return supabase.auth.signInWithPassword({ email, password })
}

export async function signOut() {
  if (!supabase) {
    localStorage.removeItem('memoryagent_user')
    return { error: null }
  }
  return supabase.auth.signOut()
}

export async function getCurrentSession() {
  if (!supabase) {
    const saved = localStorage.getItem('memoryagent_user')
    if (saved) {
      const user = JSON.parse(saved)
      return { session: { user, access_token: 'mock-token' } }
    }
    return { session: null }
  }
  const { data } = await supabase.auth.getSession()
  return data
}

// ─── Experience Memory Database Helpers ──────────────────────────────────────

export async function dbFetchExperiences(domain?: string): Promise<Experience[]> {
  if (!supabase) return []
  let query = supabase.from('experiences').select('*').order('trust_score', { ascending: false })
  if (domain && domain !== 'all') {
    query = query.eq('task_domain', domain)
  }
  const { data, error } = await query
  if (error || !data) return []

  return data.map((row) => ({
    id: row.id,
    taskDomain: row.task_domain,
    triggerCondition: row.trigger_condition,
    strategyLesson: row.strategy_lesson,
    trustScore: row.trust_score,
    usesCount: row.uses_count,
    successesCount: row.successes_count,
    failuresCount: row.failures_count,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }))
}

export async function dbSaveExperience(exp: Partial<Experience>) {
  if (!supabase) return null
  const { data, error } = await supabase
    .from('experiences')
    .insert([
      {
        task_domain: exp.taskDomain,
        trigger_condition: exp.triggerCondition,
        strategy_lesson: exp.strategyLesson,
        trust_score: exp.trustScore || 0.75,
        uses_count: exp.usesCount || 0,
        successes_count: exp.successesCount || 0,
        failures_count: exp.failuresCount || 0,
        status: exp.status || 'active',
      },
    ])
    .select()
    .single()

  if (error) {
    console.error('Error saving experience to Supabase:', error)
    return null
  }
  return data
}

export async function dbRecordTaskExecution(exec: Partial<TaskExecution>) {
  if (!supabase) return null
  const { data, error } = await supabase
    .from('task_executions')
    .insert([
      {
        task_input: exec.taskInput,
        task_domain: exec.taskDomain,
        memory_enabled: exec.memoryEnabled,
        status: exec.status,
        final_output: exec.finalOutput,
        reflection_lesson: exec.reflectionLesson,
        tokens_used: exec.tokensUsed,
        latency_ms: exec.latencyMs,
        outcome_quality: exec.outcomeQuality,
      },
    ])
    .select()
    .single()

  if (error) console.error('Error logging execution to Supabase:', error)
  return data
}

export async function dbRecordTrustUpdate(record: Omit<TrustHistoryRecord, 'id' | 'createdAt'>) {
  if (!supabase) return null
  const { data, error } = await supabase
    .from('trust_history')
    .insert([
      {
        experience_id: record.experienceId,
        execution_id: record.executionId,
        old_trust: record.oldTrust,
        new_trust: record.newTrust,
        delta: record.delta,
        reason: record.reason,
      },
    ])
    .select()
    .single()

  if (error) console.error('Error logging trust update to Supabase:', error)
  return data
}
