import React, { createContext, useContext, useState, useEffect } from 'react'
import {
  supabase,
  isSupabaseConfigured,
  signInWithEmail,
  signUpWithEmail,
  signInWithGoogle as supabaseSignInWithGoogle,
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

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check initial active Supabase session
    getCurrentSession().then(({ data }) => {
      const session = data?.session
      if (session?.user) {
        setUser({
          id: session.user.id,
          email: session.user.email || '',
          name: session.user.user_metadata?.name || session.user.email?.split('@')[0],
          avatarUrl: session.user.user_metadata?.avatar_url,
        })
      } else {
        setUser(null)
      }
      setLoading(false)
    }).catch(() => {
      setUser(null)
      setLoading(false)
    })

    // Listen to real Supabase auth state changes
    if (supabase) {
      const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.user) {
          setUser({
            id: session.user.id,
            email: session.user.email || '',
            name: session.user.user_metadata?.name || session.user.email?.split('@')[0],
            avatarUrl: session.user.user_metadata?.avatar_url,
          })
        } else {
          setUser(null)
        }
      })
      return () => {
        listener.subscription.unsubscribe()
      }
    }
  }, [])

  const signIn = async (email: string, pass: string) => {
    setLoading(true)
    try {
      const { data, error } = await signInWithEmail(email, pass)
      if (error) {
        setLoading(false)
        return { error: new Error(error.message) }
      }
      if (data?.user) {
        setUser({
          id: data.user.id,
          email: data.user.email || '',
          name: data.user.user_metadata?.name || data.user.email?.split('@')[0],
          avatarUrl: data.user.user_metadata?.avatar_url,
        })
      }
      setLoading(false)
      return { error: null }
    } catch (err: unknown) {
      setLoading(false)
      return { error: err instanceof Error ? err : new Error('Sign in failed') }
    }
  }

  const signUp = async (email: string, pass: string, name?: string) => {
    setLoading(true)
    try {
      const { data, error } = await signUpWithEmail(email, pass, name)
      if (error) {
        setLoading(false)
        return { error: new Error(error.message) }
      }
      if (data?.user) {
        setUser({
          id: data.user.id,
          email: data.user.email || '',
          name: data.user.user_metadata?.name || name || data.user.email?.split('@')[0],
        })
      }
      setLoading(false)
      return { error: null }
    } catch (err: unknown) {
      setLoading(false)
      return { error: err instanceof Error ? err : new Error('Sign up failed') }
    }
  }

  const signInWithGoogle = async () => {
    try {
      const { error } = await supabaseSignInWithGoogle()
      return { error: error ? new Error(error.message) : null }
    } catch (err: unknown) {
      return { error: err instanceof Error ? err : new Error('Google sign in failed') }
    }
  }

  const signOut = async () => {
    setLoading(true)
    try {
      await supabaseSignOut()
      setUser(null)
    } finally {
      setLoading(false)
    }
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
