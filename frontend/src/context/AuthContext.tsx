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
    // Check initial session
    getCurrentSession().then(({ session }) => {
      if (session?.user) {
        setUser({
          id: session.user.id,
          email: session.user.email || '',
          name: session.user.user_metadata?.name || session.user.email?.split('@')[0],
        })
      }
      setLoading(false)
    })

    // Listen to live Supabase auth state changes
    if (supabase) {
      const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.user) {
          setUser({
            id: session.user.id,
            email: session.user.email || '',
            name: session.user.user_metadata?.name || session.user.email?.split('@')[0],
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
    const { data, error } = await signInWithEmail(email, pass)
    if (!error && data?.user) {
      setUser({
        id: data.user.id,
        email: data.user.email || '',
        name: data.user.user_metadata?.name || data.user.email?.split('@')[0],
      })
    }
    setLoading(false)
    return { error: error ? new Error(error.message) : null }
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
    }
    setLoading(false)
    return { error: error ? new Error(error.message) : null }
  }

  const signInWithGoogle = async () => {
    setLoading(true)
    const { data, error } = await supabaseSignInWithGoogle()
    if (!error && data && 'user' in data && data.user) {
      const u = data.user as { id: string; email?: string; user_metadata?: { name?: string } }
      setUser({
        id: u.id,
        email: u.email || '',
        name: u.user_metadata?.name || u.email?.split('@')[0],
      })
    }
    setLoading(false)
    return { error: error ? new Error(error.message) : null }
  }

  const signOut = async () => {
    setLoading(true)
    await supabaseSignOut()
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
