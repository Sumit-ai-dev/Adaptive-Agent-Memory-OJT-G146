import { createClient, SupabaseClient } from '@supabase/supabase-js'
import type { Experience, TaskExecution, TrustHistoryRecord } from '../types'

const supabaseUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_SUPABASE_URL) || ''
const supabaseAnonKey = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_SUPABASE_ANON_KEY) || ''

export const isSupabaseConfigured = Boolean(
  supabaseUrl && 
  supabaseAnonKey && 
  !supabaseUrl.includes('your-project-ref') && 
  !supabaseAnonKey.includes('your-anon-key')
)

// Initialize real Supabase client
export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null

// ─── Pure Authentication Methods (No Local/Mock Fallbacks) ───────────────────

export async function signUpWithEmail(email: string, password: string, name?: string) {
  if (!supabase) {
    throw new Error('Supabase client is not configured. Real authentication requires VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.')
  }
  return supabase.auth.signUp({
    email,
    password,
    options: {
      data: { name: name || email.split('@')[0] },
    },
  })
}

export async function signInWithEmail(email: string, password: string) {
  if (!supabase) {
    throw new Error('Supabase client is not configured. Real authentication requires VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.')
  }
  return supabase.auth.signInWithPassword({ email, password })
}

export async function signInWithGoogle() {
  if (!supabase) {
    throw new Error('Google OAuth requires Supabase authentication credentials.')
  }
  return supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/dashboard`,
      queryParams: {
        prompt: 'select_account',
      },
    },
  })
}

export async function signOut() {
  if (!supabase) {
    return { error: null }
  }
  return supabase.auth.signOut()
}

export async function getCurrentSession() {
  if (!supabase) {
    return { data: { session: null }, error: null }
  }
  return supabase.auth.getSession()
}

// --- Direct Database Helpers (Supabase PostgreSQL / pgvector) ----------------

export async function dbFetchExperiences(domain?: string, status?: string): Promise<Experience[]> {
  if (!supabase) return []
  try {
    let query = supabase.from('experiences').select('*').order('trust_score', { ascending: false })
    if (domain && domain !== 'all') {
      query = query.eq('task_domain', domain)
    }
    if (status && status !== 'all') {
      const s = status.toLowerCase().trim()
      if (s === 'candidate' || s === 'provisional') {
        query = query.in('status', ['candidate', 'provisional'])
      } else if (s === 'deprecated' || s === 'quarantined') {
        query = query.in('status', ['deprecated', 'quarantined'])
      } else {
        query = query.eq('status', s)
      }
    }
    const { data, error } = await query
    if (error || !data) return []

    return data.map((row) => ({
      id: row.id,
      taskDomain: row.task_domain,
      triggerCondition: row.trigger_condition,
      strategyLesson: row.strategy_lesson,
      pitfallWarning: row.pitfall_warning,
      trustScore: row.trust_score,
      confidenceScore: row.confidence_score ?? 0.88,
      usesCount: row.uses_count,
      successesCount: row.successes_count,
      failuresCount: row.failures_count,
      consecutiveFailures: row.consecutive_failures ?? 0,
      status: row.status,
      trustTrajectory: Array.isArray(row.trust_trajectory) ? row.trust_trajectory : [row.trust_score],
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    }))
  } catch {
    return []
  }
}

export async function dbSaveExperience(exp: Partial<Experience>) {
  if (!supabase) return null
  try {
    const { data, error } = await supabase
      .from('experiences')
      .insert([
        {
          task_domain: exp.taskDomain,
          trigger_condition: exp.triggerCondition,
          strategy_lesson: exp.strategyLesson,
          pitfall_warning: exp.pitfallWarning,
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
  } catch (err) {
    console.error('Exception saving experience to Supabase:', err)
    return null
  }
}

export async function dbRecordTaskExecution(exec: Partial<TaskExecution>) {
  if (!supabase) return null
  try {
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
  } catch (err) {
    console.error('Exception logging execution to Supabase:', err)
    return null
  }
}

export async function dbRecordTrustUpdate(record: Omit<TrustHistoryRecord, 'id' | 'createdAt'>) {
  if (!supabase) return null
  try {
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
  } catch (err) {
    console.error('Exception logging trust update to Supabase:', err)
    return null
  }
}
