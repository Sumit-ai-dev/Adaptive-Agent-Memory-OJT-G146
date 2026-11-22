import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()
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
          setError(error.message)
        } else {
          onSuccess?.()
          onClose()
          navigate('/dashboard')
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGuestAccess = () => {
    onClose()
    navigate('/dashboard?demo=true')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl rounded-xl border border-[#EAE8E3] bg-[#FAFAF7] shadow-2xl overflow-hidden flex flex-col md:flex-row">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 p-1.5 rounded-full text-[#7E7D77] hover:text-[#141413] hover:bg-[#EAE8E3] transition-colors"
          aria-label="Close"
        >
          <X size={18} />
        </button>

        {/* LEFT COLUMN: Clean Form */}
        <div className="w-full md:w-1/2 p-8 sm:p-10 flex flex-col justify-between bg-[#FAFAF7]">
          <div>
            {/* Brand Header */}
            <div className="flex items-center gap-2 mb-6">
              <span className="font-mono font-bold text-sm text-[#141413]">AEMA</span>
              <span className="text-xs text-[#7E7D77]">/</span>
              <span className="text-xs text-[#6B6A65] font-medium">
                {isSignUp ? 'Create Account' : 'Sign In'}
              </span>
            </div>

            <h2 className="font-serif-headline text-3xl font-normal text-[#141413]">
              {isSignUp ? 'Start building reliable agents' : 'Welcome back'}
            </h2>
            <p className="mt-2 text-xs text-[#6B6A65] leading-relaxed">
              {isSignUp
                ? 'Join engineering teams evaluating runs and preventing negative transfer.'
                : 'Sign in to access your persistent memory banks and cognitive sessions.'}
            </p>

            {/* Error Message */}
            {error && (
              <div className="mt-4 p-3 rounded border border-[#FECACA] bg-[#FEF2F2] text-[#DC2626] text-xs flex items-start gap-2">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Success Message */}
            {successMsg && (
              <div className="mt-4 p-3 rounded border border-[#A7F3D0] bg-[#ECFDF5] text-[#059669] text-xs flex items-start gap-2">
                <ShieldCheck size={14} className="shrink-0 mt-0.5" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              {isSignUp && (
                <div>
                  <label className="block text-[11px] font-mono text-[#6B6A65] uppercase tracking-wider mb-1">
                    Full Name
                  </label>
                  <div className="relative">
                    <UserIcon size={14} className="absolute left-3 top-3 text-[#A3A29D]" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Sakshi Kasat"
                      className="w-full pl-9 pr-3 py-2 rounded border border-[#EAE8E3] bg-white text-xs text-[#141413] placeholder-[#A3A29D] focus:outline-none focus:border-[#141413] transition-colors"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-[11px] font-mono text-[#6B6A65] uppercase tracking-wider mb-1">
                  Developer / Work Email
                </label>
                <div className="relative">
                  <Mail size={14} className="absolute left-3 top-3 text-[#A3A29D]" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="dev@company.com"
                    className="w-full pl-9 pr-3 py-2 rounded border border-[#EAE8E3] bg-white text-xs text-[#141413] placeholder-[#A3A29D] focus:outline-none focus:border-[#141413] transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#6B6A65] uppercase tracking-wider mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock size={14} className="absolute left-3 top-3 text-[#A3A29D]" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2 rounded border border-[#EAE8E3] bg-white text-xs text-[#141413] placeholder-[#A3A29D] focus:outline-none focus:border-[#141413] transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded bg-[#141413] text-[#FAFAF7] text-xs font-medium hover:bg-[#2B2B28] transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <span>{loading ? 'Authenticating...' : isSignUp ? 'Create Account' : 'Sign In'}</span>
                <ArrowRight size={13} />
              </button>
            </form>

            {/* Google OAuth (if configured) */}
            {isConfigured && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  disabled={googleLoading}
                  className="w-full py-2 rounded border border-[#EAE8E3] bg-white text-[#141413] text-xs font-medium hover:bg-[#F7F6F2] transition-colors flex items-center justify-center gap-2 cursor-pointer"
                >
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
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
                  <span>Continue with Google</span>
                </button>
              </div>
            )}

            {/* Quick Guest Access */}
            <div className="mt-4 pt-4 border-t border-[#EAE8E3] text-center">
              <button
                type="button"
                onClick={handleGuestAccess}
                className="text-xs text-[#6B6A65] hover:text-[#141413] transition-colors underline cursor-pointer"
              >
                Or continue as guest (instant local sandbox) &rarr;
              </button>
            </div>
          </div>

          {/* Toggle Sign In / Sign Up */}
          <div className="mt-6 pt-4 text-center text-xs text-[#7E7D77]">
            {isSignUp ? (
              <span>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => setIsSignUp(false)}
                  className="font-medium text-[#141413] hover:underline cursor-pointer"
                >
                  Sign In
                </button>
              </span>
            ) : (
              <span>
                New developer?{' '}
                <button
                  type="button"
                  onClick={() => setIsSignUp(true)}
                  className="font-medium text-[#141413] hover:underline cursor-pointer"
                >
                  Create an account
                </button>
              </span>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Obsidian Statement Panel */}
        <div className="w-full md:w-1/2 p-8 sm:p-10 bg-[#141412] text-[#EDECE8] flex flex-col justify-between border-t md:border-t-0 md:border-l border-[#242422]">
          <div className="space-y-6">
            <div className="font-mono text-[10px] uppercase tracking-widest text-[#7E7D77]">
              Architectural Mission
            </div>

            <blockquote className="font-serif-headline text-lg sm:text-xl text-[#EDECE8] leading-relaxed font-normal">
              &ldquo;Current AI agents are amnesiac. Every session starts from zero, repeating past bugs, dead-end tool calls, and bad assumptions.
              <br /><br />
              AEMA gives agents experiential memory: not just storing text, but tracking whether an action actually succeeded, and mathematically quarantining failing strategies before they ruin production workflows.&rdquo;
            </blockquote>

            <div className="pt-2">
              <div className="text-xs font-semibold text-[#EDECE8]">Sakshi Kasat & Sumit Das</div>
              <div className="text-[11px] text-[#7E7D77] font-mono">Co-Founders & Systems Architects, AEMA</div>
            </div>
          </div>

          {/* Calibration Lifecycle Pipeline */}
          <div className="mt-8 pt-6 border-t border-[#242422]">
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-[10px] uppercase tracking-widest text-[#7E7D77]">
                Calibration Lifecycle
              </span>
              <span className="font-mono text-[10px] text-[#4EAA79] font-medium">
                Theorem 1 Bound: k* &le; 3
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-left">
              {/* Step 1: Fault Encounter */}
              <div className="p-2.5 rounded-lg bg-[#181816] border border-[#262624] flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] text-[#7E7D77]">01</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#D9534F]" />
                </div>
                <div className="text-[11px] font-semibold text-[#EDECE8] leading-tight">
                  Trap Detected
                </div>
                <div className="text-[10px] font-mono text-[#9E9D96] mt-1 leading-tight">
                  Penalty: &minus;&beta;S<sub>t</sub>
                </div>
              </div>

              {/* Step 2: Theorem 1 Isolation */}
              <div className="p-2.5 rounded-lg bg-[#181816] border border-[#262624] flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] text-[#7E7D77]">02</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#E67E22]" />
                </div>
                <div className="text-[11px] font-semibold text-[#EDECE8] leading-tight">
                  Quarantine Lock
                </div>
                <div className="text-[10px] font-mono text-[#9E9D96] mt-1 leading-tight">
                  S<sub>t</sub> &le; &theta; (k* &le; 3)
                </div>
              </div>

              {/* Step 3: Verified Recovery */}
              <div className="p-2.5 rounded-lg bg-[#181816] border border-[#262624] flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] text-[#7E7D77]">03</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#4EAA79]" />
                </div>
                <div className="text-[11px] font-semibold text-[#EDECE8] leading-tight">
                  Verified Recovery
                </div>
                <div className="text-[10px] font-mono text-[#9E9D96] mt-1 leading-tight">
                  100% Pass@1 Run
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
