import React, { useState } from 'react'
import { X, Sparkles, Lock, Mail, User as UserIcon, ArrowRight, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  initialMode?: 'signin' | 'signup'
}

export default function AuthModal({ isOpen, onClose, onSuccess, initialMode = 'signin' }: AuthModalProps) {
  const { signIn, signUp, isConfigured } = useAuth()
  const [isSignUp, setIsSignUp] = useState(initialMode === 'signup')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (isSignUp) {
        const { error } = await signUp(email, password, name)
        if (error) {
          setError(error.message)
        } else {
          setSuccessMsg('Account created successfully! Redirecting...')
          setTimeout(() => {
            onClose()
            onSuccess?.()
          }, 800)
        }
      } else {
        const { error } = await signIn(email, password)
        if (error) {
          setError(error.message)
        } else {
          setSuccessMsg('Signed in successfully!')
          setTimeout(() => {
            onClose()
            onSuccess?.()
          }, 600)
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md anim-float-up">
      <div
        className="w-full max-w-md p-7 rounded-3xl relative overflow-hidden text-white"
        style={{
          background: 'rgba(18, 10, 32, 0.95)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          boxShadow: '0 25px 80px rgba(0, 0, 0, 0.8), 0 0 50px rgba(168, 85, 247, 0.15)',
        }}
      >
        {/* Background glow */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-purple-600/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-600/15 rounded-full blur-3xl pointer-events-none" />

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-white/40 hover:text-white transition-colors p-1.5 rounded-full hover:bg-white/10"
        >
          <X size={18} />
        </button>

        {/* Modal Header */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-3 bg-purple-500/15 border border-purple-500/30">
            <Sparkles size={13} className="text-purple-300" />
            <span className="text-purple-300 text-xs font-mono font-bold tracking-wider uppercase">
              {isConfigured ? '🟢 Live Supabase Auth' : '🟣 Local Dev Auth Mode'}
            </span>
          </div>
          <h3 className="text-2xl font-display font-bold text-white tracking-tight">
            {isSignUp ? 'Create your account' : 'Welcome back to MemoryAgent'}
          </h3>
          <p className="text-white/50 text-xs font-sans mt-1">
            Access your persistent experience store, live task runner, and telemetry.
          </p>
        </div>

        {/* Status banner */}
        {!isConfigured && (
          <div className="mb-4 p-2.5 rounded-xl bg-purple-950/40 border border-purple-800/40 text-[11px] font-mono text-purple-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Dev mode: Instant sign in active. Paste Supabase keys into .env to connect live project.</span>
          </div>
        )}

        {/* Error / Success Feedback */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/40 border border-red-800/50 text-xs text-red-300">
            {error}
          </div>
        )}
        {successMsg && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/50 text-xs text-emerald-300 flex items-center gap-2">
            <CheckCircle2 size={14} />
            {successMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignUp && (
            <div>
              <label className="block text-white/50 text-xs font-mono mb-1.5 uppercase tracking-wider">
                Full Name
              </label>
              <div className="relative">
                <UserIcon size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Sumit Das"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:border-purple-400 transition-colors"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-white/50 text-xs font-mono mb-1.5 uppercase tracking-wider">
              Email Address
            </label>
            <div className="relative">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@enterprise.ai"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:border-purple-400 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-white/50 text-xs font-mono mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/30 text-sm focus:outline-none focus:border-purple-400 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl font-display font-bold text-sm text-white anim-gradient-bg shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 cursor-pointer mt-2 disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <span>{isSignUp ? 'Create Free Account' : 'Sign In'}</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Mode switcher toggle */}
        <div className="mt-6 pt-4 border-t border-white/10 text-center">
          <p className="text-white/40 text-xs font-sans">
            {isSignUp ? 'Already have an account?' : "Don't have an account yet?"}{' '}
            <button
              onClick={() => {
                setIsSignUp(!isSignUp)
                setError(null)
                setSuccessMsg(null)
              }}
              className="text-purple-300 font-semibold hover:text-white transition-colors cursor-pointer ml-1"
            >
              {isSignUp ? 'Sign in instead' : 'Create an account'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
