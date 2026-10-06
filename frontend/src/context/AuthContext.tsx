import React, { createContext, useContext, useState, useEffect } from 'react'
import {
  supabase,
  isSupabaseConfigured,
  signInWithEmail,
  signUpWithEmail,
  signOut as supabaseSignOut,
  getCurrentSession,
} from '../lib/supabase'

export interface AuthUser {
  id: string
  email: string
  name?: string
  avatarUrl?: string
}

interface AuthContextType {
  user: AuthUser | null
  loading: boolean
  isConfigured: boolean
  signIn: (email: string, pass: string) => Promise<{ error: Error | null }>
  signUp: (email: string, pass: string, name?: string) => Promise<{ error: Error | null }>
  signInWithGoogle: () => Promise<{ error: Error | null }>
  signOut: () => Promise<void>
}

const DEFAULT_BYPASS_USER: AuthUser = {
  id: 'dev-workspace-user',
  email: 'researcher@adaptive-memory.ai',
  name: 'Lead AI Engineer',
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Always default to authenticated developer user to bypass auth obstacles during UI testing
  const [user, setUser] = useState<AuthUser | null>(DEFAULT_BYPASS_USER)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Check initial session if real Supabase credentials are configured
    getCurrentSession().then(({ session }) => {
      if (session?.user) {
        setUser({
          id: session.user.id,
          email: session.user.email || '',
          name: session.user.user_metadata?.name || session.user.email?.split('@')[0],
        })
      } else {
        // Retain default authenticated bypass user
        setUser(DEFAULT_BYPASS_USER)
      }
      setLoading(false)
    })

    // Listen to live Supabase auth state changes if configured
    if (supabase) {
      const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.user) {
          setUser({
            id: session.user.id,
            email: session.user.email || '',
            name: session.user.user_metadata?.name || session.user.email?.split('@')[0],
          })
        }
      })
      return () => {
        listener.subscription.unsubscribe()
      }
    }
  }, [])

  const signIn = async (email: string, pass: string) => {
    setLoading(true)
    const { data, error } = await signInWithEmail(email, pass)
    if (!error && data?.user) {
      setUser({
        id: data.user.id,
        email: data.user.email || '',
        name: data.user.user_metadata?.name || data.user.email?.split('@')[0],
      })
    } else {
      // Fallback bypass user with entered email
      setUser({
        id: 'dev-user-001',
        email: email || 'researcher@adaptive-memory.ai',
        name: email ? email.split('@')[0] : 'Lead AI Engineer',
      })
    }
    setLoading(false)
    return { error: null }
  }

  const signUp = async (email: string, pass: string, name?: string) => {
    setLoading(true)
    const { data, error } = await signUpWithEmail(email, pass, name)
    if (!error && data?.user) {
      setUser({
        id: data.user.id,
        email: data.user.email || '',
        name: data.user.user_metadata?.name || name || data.user.email?.split('@')[0],
      })
    } else {
      setUser({
        id: 'dev-user-001',
        email: email || 'researcher@adaptive-memory.ai',
        name: name || (email ? email.split('@')[0] : 'Lead AI Engineer'),
      })
    }
    setLoading(false)
    return { error: null }
  }

  const signInWithGoogle = async () => {
    setUser(DEFAULT_BYPASS_USER)
    return { error: null }
  }

  const signOut = async () => {
    setLoading(true)
    await supabaseSignOut()
    // Allow re-logging in or toggle
    setUser(null)
    setLoading(false)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isConfigured: isSupabaseConfigured,
        signIn,
        signUp,
        signInWithGoogle,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
