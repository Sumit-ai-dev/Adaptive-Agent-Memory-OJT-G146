import React, { useState } from 'react'
import { X, Lock, Mail, User as UserIcon, ArrowRight, ShieldCheck, AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  initialMode?: 'signin' | 'signup'
}

export default function AuthModal({
  isOpen,
  onClose,
  onSuccess,
  initialMode = 'signin',
}: AuthModalProps) {
  const { signIn, signUp, signInWithGoogle, isConfigured } = useAuth()
  const [isSignUp, setIsSignUp] = useState(initialMode === 'signup')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  if (!isOpen) return null

  const handleGoogleSignIn = async () => {
    setError(null)
    setGoogleLoading(true)
    try {
      const { error } = await signInWithGoogle()
      if (error) {
        setError(error.message)
        setGoogleLoading(false)
      }
      // Browser will redirect to Google account selector
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Google OAuth initialization failed')
      setGoogleLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccessMsg(null)

    if (!email.trim() || !password.trim()) {
      setError('Please provide both email and password.')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      if (isSignUp) {
        const { error } = await signUp(email.trim(), password, name.trim())
        if (error) {
          setError(error.message)
        } else {
          setSuccessMsg(
            `Verification email sent to ${email}. Check your inbox to confirm your account, then sign in.`
          )
          setIsSignUp(false)
        }
      } else {
        const { error } = await signIn(email.trim(), password)
        if (error) {
          if (error.message.toLowerCase().includes('email not confirmed')) {
            setError('Email address is not yet confirmed. Please check your inbox.')
          } else {
            setError(error.message)
          }
        } else {
          setSuccessMsg('Authentication successful.')
          setTimeout(() => {
            onClose()
            onSuccess?.()
          }, 400)
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm anim-fade-in">
      <div
        className="w-full max-w-md rounded-2xl border p-7 shadow-2xl relative transition-all
          bg-[#FFFFFF] border-[#E6E6E1] text-[#18181B]
          dark:bg-[#131722] dark:border-[#252B3B] dark:text-[#F4F4F6]"
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
          aria-label="Close dialog"
        >
          <X size={18} />
        </button>

        {/* Modal Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 dark:bg-indigo-950/40 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <ShieldCheck size={18} />
            </div>
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
              AEMA Cloud Console
            </span>
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-[#18181B] dark:text-[#F4F4F6]">
            {isSignUp ? 'Create your workspace' : 'Sign in to your workspace'}
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Reliability-aware experiential memory engine for autonomous AI agents.
          </p>
        </div>

        {/* Supabase Status Check */}
        {!isConfigured && (
          <div className="mb-4 p-3 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>
              Supabase credentials not configured in environment. Authentication requires a live Supabase connection.
            </span>
          </div>
        )}

        {/* Mode Switch Tabs */}
        <div className="grid grid-cols-2 p-1 rounded-xl bg-zinc-100 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B] mb-5">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(false)
              setError(null)
            }}
            className={`py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer ${
              !isSignUp
                ? 'bg-white dark:bg-[#131722] text-[#18181B] dark:text-[#F4F4F6] shadow-sm'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsSignUp(true)
              setError(null)
            }}
            className={`py-1.5 text-xs font-medium rounded-lg transition-all cursor-pointer ${
              isSignUp
                ? 'bg-white dark:bg-[#131722] text-[#18181B] dark:text-[#F4F4F6] shadow-sm'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Google OAuth Button */}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={googleLoading}
          className="w-full flex items-center justify-center gap-3 py-2.5 px-4 rounded-xl border text-xs font-medium transition-all mb-4 cursor-pointer
            bg-white border-[#E6E6E1] text-[#18181B] hover:bg-[#F4F4F0]
            dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:hover:bg-[#252B3B]"
        >
          <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>{googleLoading ? 'Connecting to Google...' : 'Continue with Google'}</span>
        </button>

        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#E6E6E1] dark:border-[#252B3B]" />
          </div>
          <div className="relative flex justify-center text-[11px] uppercase tracking-wider font-mono">
            <span className="px-2 bg-white dark:bg-[#131722] text-zinc-400">or with email</span>
          </div>
        </div>

        {/* Feedback Banners */}
        {error && (
          <div className="mb-4 p-3 rounded-lg border border-rose-200 bg-rose-50 dark:border-rose-900/60 dark:bg-rose-950/30 text-rose-800 dark:text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="mb-4 p-3 rounded-lg border border-emerald-200 bg-emerald-50 dark:border-emerald-900/60 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 text-xs flex items-start gap-2">
            <ShieldCheck size={15} className="shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5">
          {isSignUp && (
            <div>
              <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Full Name
              </label>
              <div className="relative">
                <UserIcon size={14} className="absolute left-3 top-3 text-zinc-400" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Kasat Sakshi Dattaprasad"
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border transition-colors outline-none
                    bg-white border-[#E6E6E1] text-[#18181B] focus:border-indigo-600
                    dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:focus:border-indigo-400"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail size={14} className="absolute left-3 top-3 text-zinc-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@aema.ai"
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border transition-colors outline-none
                  bg-white border-[#E6E6E1] text-[#18181B] focus:border-indigo-600
                  dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:focus:border-indigo-400"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock size={14} className="absolute left-3 top-3 text-zinc-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border transition-colors outline-none
                  bg-white border-[#E6E6E1] text-[#18181B] focus:border-indigo-600
                  dark:bg-[#1A1F2C] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:focus:border-indigo-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-semibold text-white transition-all cursor-pointer
              bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 dark:bg-indigo-600 dark:hover:bg-indigo-500 shadow-sm"
          >
            <span>{loading ? 'Processing...' : isSignUp ? 'Create Workspace' : 'Sign In'}</span>
            <ArrowRight size={14} />
          </button>
        </form>

        <div className="mt-5 text-center">
          <span className="text-[11px] text-zinc-400">
            AEMA 0.1.0 · Reliability-Aware Experiential Memory
          </span>
        </div>
      </div>
    </div>
  )
}
