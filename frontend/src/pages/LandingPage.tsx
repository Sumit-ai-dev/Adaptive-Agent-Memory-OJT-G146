import { useState, useEffect, useRef } from 'react'
import {
  Brain, CheckCircle2, ArrowRight,
  Zap, Database, Menu, X,
  Sparkles, User, MessageSquare, Star, BookOpen
} from 'lucide-react'
import ThreeMemoryCore from '../components/ThreeMemoryCore'
import AuthModal from '../components/AuthModal'
import { useAuth } from '../context/AuthContext'

// ─── Demo Simulation Data ─────────────────────────────────────────────────────
const DEMO_STEPS = [
  { type: 'user',   text: 'Summarize key AI memory research papers',   delay: 0 },
  { type: 'system', text: '🔍 Retrieving 3 relevant experiences...',    delay: 1400 },
  { type: 'memory', text: 'Reflexion (2023): Use self-reflection loops', delay: 2400, tag: '94% trust' },
  { type: 'memory', text: 'Voyager (2023): Skill library for reuse',    delay: 3100, tag: '88% trust' },
  { type: 'agent',  text: 'Using 2 memories. Generating response...',   delay: 4000 },
  { type: 'answer', text: 'Based on validated experiences: Reflexion improves task success by 22% via iterative self-critique. Voyager maintains a skill library that grows over time — exactly what MemoryAgent does.', delay: 5200 },
  { type: 'store',  text: '✨ New experience stored to memory',          delay: 7000 },
]

function LiveDemoPanel() {
  const [visibleSteps, setVisibleSteps] = useState<number[]>([])
  const [typing, setTyping] = useState(false)

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []

    const reset = () => {
      setVisibleSteps([])
      setTyping(false)
      DEMO_STEPS.forEach((step, i) => {
        const t1 = setTimeout(() => {
          if (step.type === 'user') setTyping(true)
        }, step.delay)
        const t2 = setTimeout(() => {
          setTyping(false)
          setVisibleSteps(prev => [...prev, i])
        }, step.delay + 600)
        timers.push(t1, t2)
      })
      // Restart after full cycle
      const restart = setTimeout(reset, 10500)
      timers.push(restart)
    }

    reset()
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div
      className="relative w-full max-w-lg"
      style={{ perspective: '1000px' }}
    >
      {/* 3D tilted panel */}
      <div
        className="rounded-3xl overflow-hidden shadow-2xl"
        style={{
          transform: 'rotateY(-8deg) rotateX(4deg)',
          transformStyle: 'preserve-3d',
          background: 'rgba(10,0,30,0.75)',
          backdropFilter: 'blur(24px)',
          border: '1px solid rgba(168,85,247,0.3)',
          boxShadow: '0 30px 80px rgba(100,0,200,0.4), 0 0 0 1px rgba(168,85,247,0.15), inset 0 1px 0 rgba(255,255,255,0.08)',
        }}
      >
        {/* Window chrome */}
        <div
          className="flex items-center gap-2 px-5 py-3.5 border-b"
          style={{ borderColor: 'rgba(168,85,247,0.2)', background: 'rgba(168,85,247,0.08)' }}
        >
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/70" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
            <div className="w-3 h-3 rounded-full bg-green-500/70" />
          </div>
          <div className="flex-1 flex items-center justify-center gap-2">
            <Brain size={13} className="text-fuchsia-400" />
            <span className="text-white/50 text-xs font-mono">MemoryAgent · Live Session</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-green-400 text-xs">Active</span>
          </div>
        </div>

        {/* Messages area */}
        <div className="p-5 space-y-3 min-h-[340px]">
          {DEMO_STEPS.map((step, i) => {
            if (!visibleSteps.includes(i)) return null
            return (
              <div
                key={i}
                className="anim-float-up"
                style={{ animationDuration: '0.4s' }}
              >
                {step.type === 'user' && (
                  <div className="flex items-start gap-2.5 justify-end">
                    <div
                      className="rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%]"
                      style={{ background: 'linear-gradient(135deg,#7c3aed,#a855f7)' }}
                    >
                      <p className="text-white text-sm font-medium">{step.text}</p>
                    </div>
                    <div className="w-7 h-7 rounded-xl bg-fuchsia-500/30 flex items-center justify-center flex-shrink-0">
                      <User size={13} className="text-fuchsia-300" />
                    </div>
                  </div>
                )}

                {step.type === 'system' && (
                  <div className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-purple-400" />
                    <p className="text-purple-300 text-xs font-mono">{step.text}</p>
                  </div>
                )}

                {step.type === 'memory' && (
                  <div
                    className="flex items-start gap-2.5 ml-3"
                    style={{ animationDuration: '0.3s' }}
                  >
                    <BookOpen size={13} className="text-cyan-400 mt-0.5 flex-shrink-0" />
                    <div
                      className="rounded-xl px-3 py-2 flex-1 flex items-center justify-between gap-3"
                      style={{
                        background: 'rgba(34,211,238,0.08)',
                        border: '1px solid rgba(34,211,238,0.2)',
                      }}
                    >
                      <p className="text-cyan-200 text-xs">{step.text}</p>
                      <span
                        className="text-xs font-bold px-2 py-0.5 rounded-full whitespace-nowrap"
                        style={{ background: 'rgba(34,211,238,0.15)', color: '#22d3ee' }}
                      >
                        {step.tag}
                      </span>
                    </div>
                  </div>
                )}

                {step.type === 'agent' && (
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: 'linear-gradient(135deg,#a855f7,#ec4899)' }}
                    >
                      <Brain size={13} className="text-white" />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-bounce" />
                      <div className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-bounce delay-100" />
                      <div className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-bounce delay-200" />
                      <span className="text-white/40 text-xs ml-1">{step.text}</span>
                    </div>
                  </div>
                )}

                {step.type === 'answer' && (
                  <div className="flex items-start gap-2.5">
                    <div
                      className="w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: 'linear-gradient(135deg,#a855f7,#ec4899)' }}
                    >
                      <Brain size={13} className="text-white" />
                    </div>
                    <div
                      className="rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%]"
                      style={{
                        background: 'rgba(168,85,247,0.12)',
                        border: '1px solid rgba(168,85,247,0.25)',
                      }}
                    >
                      <p className="text-white/85 text-sm leading-relaxed">{step.text}</p>
                    </div>
                  </div>
                )}

                {step.type === 'store' && (
                  <div
                    className="flex items-center gap-2.5 rounded-xl px-4 py-2.5"
                    style={{
                      background: 'linear-gradient(135deg, rgba(34,197,94,0.12), rgba(168,85,247,0.12))',
                      border: '1px solid rgba(34,197,94,0.3)',
                    }}
                  >
                    <Star size={13} className="text-green-400 flex-shrink-0" />
                    <p className="text-green-300 text-xs font-semibold">{step.text}</p>
                    <div
                      className="ml-auto text-xs px-2 py-0.5 rounded-full font-bold"
                      style={{ background: 'rgba(34,197,94,0.2)', color: '#4ade80' }}
                    >
                      +1 memory
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {/* Typing indicator */}
          {typing && (
            <div className="flex items-start gap-2.5 justify-end anim-float-up">
              <div
                className="rounded-2xl rounded-tr-sm px-4 py-3"
                style={{ background: 'rgba(168,85,247,0.3)' }}
              >
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce" />
                  <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce delay-100" />
                  <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce delay-200" />
                </div>
              </div>
              <div className="w-7 h-7 rounded-xl bg-fuchsia-500/30 flex items-center justify-center flex-shrink-0">
                <User size={13} className="text-fuchsia-300" />
              </div>
            </div>
          )}
        </div>

        {/* Input bar */}
        <div
          className="px-4 py-3 border-t flex items-center gap-3"
          style={{ borderColor: 'rgba(168,85,247,0.15)', background: 'rgba(0,0,0,0.3)' }}
        >
          <MessageSquare size={15} className="text-white/30" />
          <span className="text-white/25 text-sm flex-1 font-mono">Ask the agent anything...</span>
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg,#7c3aed,#ec4899)' }}
          >
            <ArrowRight size={13} className="text-white" />
          </div>
        </div>
      </div>

      {/* Glow under the panel */}
      <div
        className="absolute -bottom-8 left-1/2 -translate-x-1/2 w-3/4 h-16 blur-2xl rounded-full pointer-events-none"
        style={{ background: 'linear-gradient(90deg,#7c3aed,#ec4899,#22d3ee)' }}
      />
    </div>
  )
}

// ─── Mini Stat Cards (floating beside the demo) ───────────────────────────────
function StatBadge({ icon: Icon, val, label, color }: { icon: React.ElementType; val: string; label: string; color: string }) {
  return (
    <div
      className="rounded-2xl px-4 py-3 flex items-center gap-3 anim-float"
      style={{
        background: 'rgba(10,0,30,0.7)',
        backdropFilter: 'blur(16px)',
        border: `1px solid ${color}30`,
        boxShadow: `0 0 24px ${color}20`,
      }}
    >
      <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${color}20` }}>
        <Icon size={15} style={{ color }} />
      </div>
      <div>
        <p className="text-white font-bold text-sm font-display">{val}</p>
        <p className="text-white/40 text-xs">{label}</p>
      </div>
    </div>
  )
}

// ─── Animated Memory Node Graph (CSS only) ────────────────────────────────────
function MemoryNodes() {
  return (
    <div className="absolute right-0 top-0 bottom-0 w-72 hidden xl:block pointer-events-none overflow-hidden">
      <svg width="288" height="100%" viewBox="0 0 288 600" className="opacity-30">
        <defs>
          <radialGradient id="node-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#a855f7" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* Lines */}
        {[[144,100,80,200],[144,100,200,220],[80,200,60,340],[80,200,160,360],[200,220,220,380],[60,340,100,500],[160,360,180,480],[220,380,150,520]].map(([x1,y1,x2,y2],i) => (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="url(#node-glow)" strokeWidth="1" strokeDasharray="4 4">
            <animate attributeName="stroke-dashoffset" values="0;-100" dur={`${3+i*0.4}s`} repeatCount="indefinite" />
          </line>
        ))}
        {/* Nodes */}
        {[[144,100,8,'#a855f7'],[80,200,6,'#22d3ee'],[200,220,6,'#ec4899'],[60,340,5,'#fb923c'],[160,360,5,'#a855f7'],[220,380,5,'#22d3ee'],[100,500,4,'#ec4899'],[180,480,4,'#a855f7'],[150,520,4,'#22d3ee']].map(([cx,cy,r,color],i) => (
          <circle key={i} cx={cx} cy={cy} r={r} fill={color as string} opacity="0.8">
            <animate attributeName="r" values={`${r};${Number(r)+3};${r}`} dur={`${2+i*0.3}s`} repeatCount="indefinite" />
          </circle>
        ))}
      </svg>
    </div>
  )
}

// ─── Navbar ───────────────────────────────────────────────────────────────────
function Navbar({ scrolled }: { scrolled: boolean }) {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin')

  return (
    <>
      <nav className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${scrolled ? 'glass shadow-lg' : ''}`}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center anim-gradient-bg">
              <Brain size={18} className="text-white" />
            </div>
            <span className="text-white font-bold text-lg font-display tracking-tight">MemoryAgent</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            {['Features', 'How it works', 'Docs'].map(item => (
              <a key={item} href="#" className="text-white/60 hover:text-white text-sm font-medium transition-colors duration-150">{item}</a>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-200 text-xs font-mono">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>{user.name || user.email.split('@')[0]}</span>
                </div>
                <a
                  href="/dashboard"
                  className="text-sm font-bold px-4 py-2 rounded-xl text-white cursor-pointer anim-gradient-bg hover:opacity-90 transition-opacity"
                >
                  Dashboard
                </a>
                <button
                  onClick={() => signOut()}
                  className="text-white/50 hover:text-white text-xs font-mono transition-colors cursor-pointer bg-transparent border-0"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={() => {
                    setAuthMode('signin')
                    setShowAuth(true)
                  }}
                  className="text-white/70 hover:text-white text-sm font-medium transition-colors cursor-pointer bg-transparent border-0"
                >
                  Sign in
                </button>
                <button
                  onClick={() => {
                    setAuthMode('signup')
                    setShowAuth(true)
                  }}
                  id="nav-cta"
                  className="text-sm font-bold px-5 py-2.5 rounded-xl text-white cursor-pointer anim-gradient-bg hover:opacity-90 transition-opacity border-0"
                >
                  Get started →
                </button>
              </>
            )}
          </div>

          <button className="md:hidden text-white" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {open && (
          <div className="md:hidden glass px-6 pb-5 space-y-4 border-t border-white/10">
            {['Features', 'How it works', 'Docs'].map(item => (
              <a key={item} href="#" className="block text-white/80 text-sm font-medium py-1">{item}</a>
            ))}
            {user ? (
              <div className="space-y-2 pt-2 border-t border-white/10">
                <p className="text-white/60 text-xs font-mono">{user.email}</p>
                <a href="/dashboard" className="block text-center text-sm font-bold py-2.5 rounded-xl text-white anim-gradient-bg">
                  Go to Dashboard
                </a>
                <button
                  onClick={() => signOut()}
                  className="w-full text-center text-white/50 text-xs py-1"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  setAuthMode('signup')
                  setShowAuth(true)
                  setOpen(false)
                }}
                className="w-full text-center text-sm font-bold py-2.5 rounded-xl text-white anim-gradient-bg cursor-pointer border-0"
              >
                Get started →
              </button>
            )}
          </div>
        )}
      </nav>

      {/* Supabase Auth Modal */}
      <AuthModal
        isOpen={showAuth}
        initialMode={authMode}
        onClose={() => setShowAuth(false)}
        onSuccess={() => {
          window.location.href = '/dashboard'
        }}
      />
    </>
  )
}

// ─── LLM Provider Data with Interactive Scenarios ────────────────────────────
interface ProviderConfig {
  name: string
  modelTag: string
  color: string
  glowColor: string
  taskType: string
  query: string
  memoryId: string
  memoryMatch: string
  confidence: string
  codeLines: { num: string; text: string; color: string }[]
  latency: string
  timeSaved: string
  tokensSaved: string
  svg: React.ReactNode
}

const LLM_PROVIDERS: ProviderConfig[] = [
  {
    name: 'OpenAI',
    modelTag: 'GPT-4o Enterprise',
    color: '#10a37f',
    glowColor: '#10b981',
    taskType: 'INCIDENT AUTO-HEAL',
    query: 'Auto-heal failing payment webhook queue and alert on recurring anomalies',
    memoryId: 'MEM-520',
    memoryMatch: 'Run #520: Stripe idempotent replay queue with DLQ exponential backoff',
    confidence: '98.4%',
    codeLines: [
      { num: '01', text: '// Recalled memory pattern #520 from past resolution', color: '#6b7280' },
      { num: '02', text: 'const dlqStrategy = await memoryAgent.inject("stripe_webhook_dlq");', color: '#38bdf8' },
      { num: '03', text: 'const healed = await openAI.executeTool(dlqStrategy.retryPattern);', color: '#c084fc' },
      { num: '04', text: '// Status: 148 stalled webhooks reprocessed · 0 packet loss', color: '#4ade80' },
    ],
    latency: '120ms',
    timeSaved: '45 MIN',
    tokensSaved: '14.2k',
    svg: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M22.28 9.28a5.76 5.76 0 0 0-.49-4.73 5.82 5.82 0 0 0-6.27-2.8A5.77 5.77 0 0 0 11.18 0a5.82 5.82 0 0 0-5.55 4.03 5.77 5.77 0 0 0-3.85 2.8 5.82 5.82 0 0 0 .72 6.82 5.76 5.76 0 0 0 .49 4.73 5.82 5.82 0 0 0 6.27 2.8A5.77 5.77 0 0 0 13.6 24a5.82 5.82 0 0 0 5.55-4.03 5.77 5.77 0 0 0 3.85-2.8 5.82 5.82 0 0 0-.72-6.89zM13.6 22.5a4.3 4.3 0 0 1-2.76-1 .1.1 0 0 1 .05-.02l4.59-2.65a.74.74 0 0 0 .37-.65v-6.47l1.94 1.12a.07.07 0 0 1 .04.06v5.36A4.32 4.32 0 0 1 13.6 22.5zm-9.3-3.96a4.3 4.3 0 0 1-.52-2.89.1.1 0 0 1 .05.03l4.59 2.65a.74.74 0 0 0 .74 0l5.61-3.24v2.24a.07.07 0 0 1-.03.06L10.1 20.1a4.32 4.32 0 0 1-5.8-1.56zm-1.21-9.97a4.3 4.3 0 0 1 2.24-1.89v5.45a.74.74 0 0 0 .37.65l5.61 3.24-1.94 1.12a.07.07 0 0 1-.07 0L5.17 14.9a4.32 4.32 0 0 1-2.08-6.33zm15.95 3.7L13.43 9.03l1.94-1.12a.07.07 0 0 1 .07 0l4.13 2.38a4.32 4.32 0 0 1-.67 7.78v-5.45a.74.74 0 0 0-.36-.65zm1.93-2.9a.1.1 0 0 1-.05-.03l-4.59-2.65a.74.74 0 0 0-.74 0L10 10.93V8.69a.07.07 0 0 1 .03-.06l4.13-2.38a4.32 4.32 0 0 1 6.4 4.48l-.59-.36zm-12.16 4L7.87 12l1.94-1.12a.07.07 0 0 1 .07 0l.06.04v2.24l-1.73 1z"/></svg>,
  },
  {
    name: 'Claude',
    modelTag: 'Claude 3.5 Sonnet',
    color: '#d97706',
    glowColor: '#f59e0b',
    taskType: 'SECURITY REFACTOR',
    query: 'Refactor JWT session guard to prevent replay attacks across microservices',
    memoryId: 'MEM-312',
    memoryMatch: 'Run #312: Distributed HMAC salt rotation + Redis token revocation list',
    confidence: '99.1%',
    codeLines: [
      { num: '01', text: '// Injected zero-trust security rule verified in staging', color: '#6b7280' },
      { num: '02', text: 'const authPattern = await memoryAgent.recall("auth_replay_guard");', color: '#38bdf8' },
      { num: '03', text: 'export const sessionGuard = compose(rateLimit, authPattern.validator);', color: '#f59e0b' },
      { num: '04', text: '// Status: 42 attack vectors neutralized · 0 latency penalty', color: '#4ade80' },
    ],
    latency: '135ms',
    timeSaved: '55 MIN',
    tokensSaved: '18.5k',
    svg: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.709 15.955l4.72-2.647.08-.23-.08-.128-4.72 2.647.08.228v.13zM9.478 7.27l.08.23 4.72-2.648-.08-.228-4.72 2.647zM12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 22.5C6.201 22.5 1.5 17.799 1.5 12S6.201 1.5 12 1.5 22.5 6.201 22.5 12 17.799 22.5 12 22.5zm-2.355-6.873l-3.924-6.797L12 5.373l6.279 3.457-3.924 6.797H9.645z"/></svg>,
  },
  {
    name: 'Gemini',
    modelTag: 'Gemini 1.5 Pro',
    color: '#4285F4',
    glowColor: '#60a5fa',
    taskType: 'TELEMETRY ROOT-CAUSE',
    query: 'Synthesize distributed trace logs from 4 regions and isolate Envoy 502 root cause',
    memoryId: 'MEM-688',
    memoryMatch: 'Run #688: Correlation between Envoy edge timeout and DB connection exhaustion',
    confidence: '98.9%',
    codeLines: [
      { num: '01', text: '// Recalling multi-modal incident graph from cluster logs', color: '#6b7280' },
      { num: '02', text: 'const incidentGraph = await memoryAgent.query("envoy_502_regional");', color: '#38bdf8' },
      { num: '03', text: 'const rca = await gemini.correlate({ logs, memory: incidentGraph });', color: '#60a5fa' },
      { num: '04', text: '// Status: Root cause identified in 840ms: DB connection pool = 100', color: '#4ade80' },
    ],
    latency: '98ms',
    timeSaved: '64 MIN',
    tokensSaved: '24.5k',
    svg: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zm0 2c2.717 0 5.273 1.055 7.17 2.957L4.957 19.17A9.972 9.972 0 0 1 2 12C2 6.477 6.477 2 12 2zm0 20c-2.717 0-5.273-1.055-7.17-2.957L19.043 4.83A9.972 9.972 0 0 1 22 12c0 5.523-4.477 10-10 10z"/></svg>,
  },
  {
    name: 'Grok',
    modelTag: 'Grok-2 (xAI)',
    color: '#ffffff',
    glowColor: '#38bdf8',
    taskType: 'CLUSTER RESILIENCE',
    query: 'Resolve distributed cache stampede across 8 cluster nodes under 50k RPS peak load',
    memoryId: 'MEM-409',
    memoryMatch: 'Run #409: Exponential jitter backoff + singleflight mutex distributed lock',
    confidence: '98.6%',
    codeLines: [
      { num: '01', text: '// Applying proven singleflight mutex pattern from past spike', color: '#6b7280' },
      { num: '02', text: 'const lockStrategy = await memoryAgent.get("cache_stampede_v2");', color: '#38bdf8' },
      { num: '03', text: 'const clusterRes = await grok.applyCircuitBreaker(lockStrategy);', color: '#e2e8f0' },
      { num: '04', text: '// Status: 0 dropped requests · 50k RPS handled gracefully', color: '#4ade80' },
    ],
    latency: '110ms',
    timeSaved: '42 MIN',
    tokensSaved: '12.4k',
    svg: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>,
  },
  {
    name: 'Ollama',
    modelTag: 'Llama-3 Local (Air-gapped)',
    color: '#a855f7',
    glowColor: '#c084fc',
    taskType: 'AIR-GAPPED COMPLIANCE',
    query: 'Run private localized database migration with zero cloud data egress',
    memoryId: 'MEM-104',
    memoryMatch: 'Run #104: Local pgvector embedding retrieval with air-gapped schema checks',
    confidence: '96.4%',
    codeLines: [
      { num: '01', text: '// Local memory query · 100% on-premise execution', color: '#6b7280' },
      { num: '02', text: 'const localMemory = await pgvectorClient.query({ embedding: localEmb });', color: '#c084fc' },
      { num: '03', text: 'const ddlPlan = await ollama.generateSafeDDL({ memory: localMemory });', color: '#38bdf8' },
      { num: '04', text: '// Status: Schema migrated in 620ms · 0 bytes external egress', color: '#4ade80' },
    ],
    latency: '85ms',
    timeSaved: '30 MIN',
    tokensSaved: '8.1k',
    svg: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm-2-5.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm4 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"/></svg>,
  },
  {
    name: 'Meta',
    modelTag: 'Llama 3.1 70B',
    color: '#0081FB',
    glowColor: '#38bdf8',
    taskType: 'MULTI-TENANT PIPELINE',
    query: 'Deploy multi-tenant agent workflow with isolated memory namespaces',
    memoryId: 'MEM-742',
    memoryMatch: 'Run #742: Tenant-partitioned vector namespace with cross-org rule isolation',
    confidence: '98.2%',
    codeLines: [
      { num: '01', text: '// Loading tenant-scoped episodic memory index', color: '#6b7280' },
      { num: '02', text: 'const tenantSpace = memoryAgent.namespace("tenant_enterprise_01");', color: '#38bdf8' },
      { num: '03', text: 'const plan = await metaLlama.orchestrateWithMemory(tenantSpace);', color: '#60a5fa' },
      { num: '04', text: '// Status: 3 workflows scheduled autonomously with zero drift', color: '#4ade80' },
    ],
    latency: '105ms',
    timeSaved: '48 MIN',
    tokensSaved: '15.0k',
    svg: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.915 4.03c-1.968 0-3.683 1.28-4.871 3.113C.704 9.208 0 11.883 0 14.449c0 .706.07 1.369.21 1.973a6.624 6.624 0 0 0 .265.86 5.297 5.297 0 0 0 .371.761c.696 1.159 1.818 1.927 3.593 1.927 1.497 0 2.633-.671 3.965-2.444.76-1.012 1.144-1.626 2.663-4.32l.756-1.339.186-.325c.186.3.398.643.64 1.038l1.408 2.316c1.548 2.396 2.522 3.374 4.007 3.374 1.728 0 2.88-.65 3.866-2.244.459-.772.651-1.354.772-2.153.075-.5.117-1.024.117-1.566 0-2.565-.537-5.08-1.761-6.96C19.483 5.445 18 4.03 16.338 4.03c-1.223 0-2.333.5-3.474 1.643-.787.793-1.208 1.376-2.264 3.052-.157-.254-.314-.505-.463-.742C8.862 5.51 7.962 4.03 6.915 4.03z"/></svg>,
  },
]

// ─── Integrations Section (Futuristic 3D Cyber Model + Live Animated Text) ────
function IntegrationsSection() {
  const [activeName, setActiveName] = useState(LLM_PROVIDERS[0].name)
  const [typedQuery, setTypedQuery] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  const activeProvider = LLM_PROVIDERS.find(p => p.name === activeName) || LLM_PROVIDERS[0]

  // Live animated typing effect on query change
  useEffect(() => {
    setTypedQuery('')
    setIsTyping(true)
    const fullText = activeProvider.query
    let i = 0
    const interval = setInterval(() => {
      if (i < fullText.length) {
        setTypedQuery(fullText.slice(0, i + 1))
        i++
      } else {
        setIsTyping(false)
        clearInterval(interval)
      }
    }, 22)
    return () => clearInterval(interval)
  }, [activeProvider.name])

  return (
    <section className="py-28 px-6 bg-[#0a0010] border-t border-white/5 relative overflow-hidden">
      {/* Background ambient multi-color bloom */}
      <div
        className="absolute top-1/4 right-0 w-[700px] h-[700px] rounded-full blur-[140px] pointer-events-none opacity-40 transition-all duration-1000"
        style={{
          background: `radial-gradient(circle, ${activeProvider.glowColor}50 0%, #7c3aed30 50%, transparent 80%)`,
        }}
      />
      <div className="absolute -bottom-20 left-10 w-[500px] h-[500px] bg-fuchsia-900/15 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-start">
          
          {/* ── Left column: Model Selector ── */}
          <div className="lg:col-span-4 flex flex-col">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <p className="text-white/40 text-xs font-bold tracking-widest uppercase font-display">
                MULTI-LLM MEMORY ADAPTER
              </p>
            </div>

            <h2 className="text-white font-display font-bold text-2xl lg:text-3xl mb-4 leading-tight">
              Seamlessly works with your favorite models
            </h2>
            <p className="text-white/50 text-sm leading-relaxed mb-8">
              Plug MemoryAgent into any foundation model. The shared memory graph retains lessons across executions, preventing repeat errors and cutting token costs by up to 80%.
            </p>

            {/* Provider Buttons */}
            <div className="flex flex-col gap-2.5">
              {LLM_PROVIDERS.map((p) => {
                const isActive = activeName === p.name
                return (
                  <button
                    key={p.name}
                    onClick={() => setActiveName(p.name)}
                    className={`flex items-center justify-between px-5 py-4 rounded-xl text-left transition-all duration-300 w-full group relative overflow-hidden ${
                      isActive ? 'bg-white/[0.08]' : 'bg-white/[0.02] hover:bg-white/[0.05]'
                    }`}
                    style={{
                      border: isActive ? `1px solid ${p.color}` : '1px solid rgba(255,255,255,0.05)',
                      boxShadow: isActive ? `0 0 35px ${p.glowColor}25, inset 0 0 15px ${p.glowColor}10` : 'none',
                    }}
                  >
                    {/* Active left indicator bar */}
                    {isActive && (
                      <div
                        className="absolute left-0 top-0 bottom-0 w-1 transition-all duration-300"
                        style={{ background: p.color, boxShadow: `0 0 10px ${p.color}` }}
                      />
                    )}

                    <div className="flex items-center gap-4">
                      <div
                        className="w-6 h-6 flex-shrink-0 transition-transform duration-300 group-hover:scale-110"
                        style={{ color: isActive ? p.color : 'rgba(255,255,255,0.45)' }}
                      >
                        {p.svg}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`font-display text-[15px] font-semibold tracking-wide transition-colors ${
                            isActive ? 'text-white' : 'text-white/70 group-hover:text-white'
                          }`}>
                            {p.name}
                          </span>
                          {isActive && (
                            <span
                              className="text-[9px] font-bold font-display px-2 py-0.5 rounded-full uppercase tracking-wider"
                              style={{ background: `${p.color}25`, color: p.color, border: `1px solid ${p.color}40` }}
                            >
                              Active
                            </span>
                          )}
                        </div>
                        <p className="text-white/35 text-xs font-mono mt-0.5">{p.modelTag}</p>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-mono font-bold text-green-400 block">{p.latency}</span>
                      <span className="text-[10px] text-white/30 tracking-wider font-display">LATENCY</span>
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Sub-card: Memory Bridge Telemetry */}
            <div
              className="mt-6 p-4 rounded-xl border border-white/5 relative overflow-hidden"
              style={{ background: 'rgba(168,85,247,0.03)' }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-white/40 text-[10px] font-bold uppercase tracking-wider font-display">MEMORY BRIDGE</span>
                <span className="flex items-center gap-1.5 text-green-400 text-[11px] font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                  Synced
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-white/30 text-[10px]">REUSE HIT RATE</p>
                  <p className="text-white font-mono font-bold text-sm">87.4%</p>
                </div>
                <div>
                  <p className="text-white/30 text-[10px]">AVG RECOVERY</p>
                  <p className="text-cyan-300 font-mono font-bold text-sm">&lt; 150ms</p>
                </div>
              </div>
            </div>
          </div>

          {/* ── Right column: Interactive 3D Cyber Cockpit ── */}
          <div className="lg:col-span-8 flex flex-col">
            
            {/* 3D Glassmorphic Cockpit Card */}
            <div
              className="w-full rounded-2xl relative overflow-hidden transition-all duration-700"
              style={{
                background: 'rgba(12, 5, 24, 0.85)',
                backdropFilter: 'blur(28px)',
                border: `1px solid ${activeProvider.color}35`,
                boxShadow: `0 35px 90px rgba(0,0,0,0.7), 0 0 50px ${activeProvider.glowColor}15, inset 0 0 0 1px rgba(255,255,255,0.05)`,
              }}
            >
              {/* Window Header */}
              <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between bg-black/40">
                <div className="flex items-center gap-2.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/80 border border-red-400/40" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80 border border-yellow-400/40" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80 border border-green-400/40" />
                  <span className="text-white/30 text-xs font-mono ml-2">memory-agent@core:~</span>
                </div>

                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-display font-semibold"
                    style={{
                      background: `${activeProvider.color}18`,
                      border: `1px solid ${activeProvider.color}50`,
                      color: activeProvider.color,
                    }}
                  >
                    <div className="w-3.5 h-3.5">{activeProvider.svg}</div>
                    <span>{activeProvider.modelTag}</span>
                  </div>
                  <span className="text-white/20 text-xs font-mono hidden sm:inline">ID: {activeProvider.memoryId}</span>
                </div>
              </div>

              {/* Cockpit Body: Split into 3D Model Top & Animated Code Console Bottom */}
              <div className="relative">
                
                {/* ── Top Half: Interactive 3D WebGL Neural Model ── */}
                <div className="relative h-[250px] w-full flex items-center justify-center overflow-hidden border-b border-white/5">
                  {/* Subtle background tech grid */}
                  <div
                    className="absolute inset-0 opacity-15 pointer-events-none"
                    style={{
                      backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                      backgroundSize: '32px 32px',
                    }}
                  />

                  {/* Real Three.js 3D WebGL Neural Core */}
                  <ThreeMemoryCore
                    glowColor={activeProvider.glowColor}
                    providerName={activeProvider.name}
                  />

                  {/* Floating 3D Holographic Satellites */}
                  <div className="absolute top-4 left-5 z-20 pointer-events-none anim-float">
                    <div
                      className="px-3 py-1.5 rounded-full flex items-center gap-2 backdrop-blur-md shadow-lg"
                      style={{
                        background: 'rgba(10, 0, 30, 0.75)',
                        border: '1px solid rgba(34, 197, 94, 0.4)',
                      }}
                    >
                      <span className="w-2 h-2 rounded-full bg-green-400 animate-ping" />
                      <span className="text-green-300 text-[10px] font-bold font-mono tracking-wider">
                        ● 3D NEURAL CORE ACTIVE
                      </span>
                    </div>
                  </div>

                  <div className="absolute top-4 right-5 z-20 pointer-events-none anim-float" style={{ animationDelay: '1.2s' }}>
                    <div
                      className="px-3 py-1.5 rounded-full flex items-center gap-2 backdrop-blur-md shadow-lg"
                      style={{
                        background: 'rgba(10, 0, 30, 0.75)',
                        border: `1px solid ${activeProvider.glowColor}50`,
                      }}
                    >
                      <Zap className="w-3 h-3 text-cyan-400" />
                      <span className="text-cyan-300 text-[10px] font-bold font-mono tracking-wider">
                        INSTANT RECALL: {activeProvider.latency}
                      </span>
                    </div>
                  </div>

                  <div className="absolute bottom-3 right-5 z-20 pointer-events-none anim-float" style={{ animationDelay: '0.6s' }}>
                    <div
                      className="px-3 py-1.5 rounded-lg flex items-center gap-2 backdrop-blur-md shadow-lg"
                      style={{
                        background: 'rgba(10, 0, 30, 0.85)',
                        border: '1px solid rgba(168, 85, 247, 0.4)',
                      }}
                    >
                      <Brain className="w-3.5 h-3.5 text-fuchsia-400" />
                      <span className="text-fuchsia-300 text-[10px] font-bold font-mono">
                        {activeProvider.confidence} MATCH CONFIDENCE
                      </span>
                    </div>
                  </div>

                  <div className="absolute bottom-3 left-5 z-20 pointer-events-none anim-float" style={{ animationDelay: '1.8s' }}>
                    <div
                      className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 backdrop-blur-md shadow-lg"
                      style={{
                        background: 'rgba(10, 0, 30, 0.85)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                      }}
                    >
                      <span className="text-[10px] font-display text-white/50 uppercase tracking-wider">TASK TYPE:</span>
                      <span className="text-[10px] font-bold font-mono text-white/90">{activeProvider.taskType}</span>
                    </div>
                  </div>
                </div>

                {/* ── Lower Half: Live Animated Text Stream & Code Execution ── */}
                <div className="p-5 sm:p-7 space-y-4 bg-black/30">
                  
                  {/* User Query Input Line with live typing */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <User size={13} className="text-white/40" />
                      <span className="text-white/40 text-xs font-mono font-semibold uppercase tracking-wider">
                        Incoming Task Prompt
                      </span>
                    </div>
                    <div
                      className="px-4 py-3 rounded-xl font-mono text-[13px] text-white/90 flex items-center gap-2 transition-all"
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                      }}
                    >
                      <span className="text-fuchsia-400 font-bold">&gt;</span>
                      <span className="flex-1 font-mono">
                        {typedQuery}
                        {isTyping && <span className="inline-block w-2 h-4 bg-fuchsia-400 ml-1 animate-pulse" />}
                      </span>
                    </div>
                  </div>

                  {/* Memory Recall Injection Banner */}
                  <div
                    className="p-3.5 rounded-xl flex items-start sm:items-center justify-between gap-4 transition-all duration-500"
                    style={{
                      background: 'linear-gradient(90deg, rgba(168,85,247,0.12), rgba(34,211,238,0.08))',
                      border: '1px solid rgba(168,85,247,0.3)',
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-purple-500/20 text-purple-300 flex-shrink-0">
                        <Brain size={16} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold font-display text-white">
                            Autonomous Memory Injected
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-green-500/20 text-green-300 border border-green-500/30">
                            {activeProvider.confidence} MATCH
                          </span>
                        </div>
                        <p className="text-white/60 text-xs mt-0.5 line-clamp-1">{activeProvider.memoryMatch}</p>
                      </div>
                    </div>

                    <div className="hidden sm:flex flex-col items-end flex-shrink-0">
                      <span className="text-cyan-400 text-xs font-mono font-bold">{activeProvider.latency}</span>
                      <span className="text-[10px] text-white/40 font-display">SEARCH TIME</span>
                    </div>
                  </div>

                  {/* Code Execution Stream */}
                  <div
                    className="rounded-xl p-4 font-mono text-[12px] leading-relaxed relative overflow-hidden"
                    style={{
                      background: 'rgba(0, 0, 0, 0.6)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                    }}
                  >
                    <div className="space-y-1.5">
                      {activeProvider.codeLines.map((line, idx) => (
                        <div key={idx} className="flex items-start gap-4">
                          <span className="text-white/20 select-none w-5 text-right flex-shrink-0">{line.num}</span>
                          <span style={{ color: line.color }} className="flex-1 font-mono break-all">
                            {line.text}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Resolution Footer Banner */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 size={16} className="text-green-400 flex-shrink-0" />
                      <span className="text-white/80 text-xs font-medium">
                        Executed autonomously · <span className="text-green-300 font-semibold font-mono">Saved {activeProvider.timeSaved}</span> · Zero manual prompts
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-white/50 border border-white/10">
                        Tokens Saved: {activeProvider.tokensSaved}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                        Cost: $0.000 (Cached)
                      </span>
                    </div>
                  </div>

                </div>

                {/* ── Cockpit Bottom Metrics Ribbon ── */}
                <div className="px-6 py-4 border-t border-white/10 bg-black/50 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-white/40 text-[10px] font-bold uppercase tracking-wider font-display">LATENCY</p>
                    <p className="text-cyan-300 font-display font-bold text-lg mt-0.5">{activeProvider.latency}</p>
                  </div>
                  <div>
                    <p className="text-white/40 text-[10px] font-bold uppercase tracking-wider font-display">TOKENS SAVED</p>
                    <p className="text-green-400 font-display font-bold text-lg mt-0.5">{activeProvider.tokensSaved}</p>
                  </div>
                  <div>
                    <p className="text-white/40 text-[10px] font-bold uppercase tracking-wider font-display">TRUST SCORE</p>
                    <p className="text-fuchsia-400 font-display font-bold text-lg mt-0.5">{activeProvider.confidence}</p>
                  </div>
                  <div>
                    <p className="text-white/40 text-[10px] font-bold uppercase tracking-wider font-display">EST. SAVED</p>
                    <p className="text-white font-display font-bold text-lg mt-0.5">{activeProvider.timeSaved}</p>
                  </div>
                </div>

              </div>
            </div>

            {/* ── 2 Column Benefit Cards Beneath Cockpit ── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
              <div
                className="p-6 rounded-2xl transition-all duration-300 hover:border-fuchsia-500/30"
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-fuchsia-500/10 border border-fuchsia-500/30">
                    <Zap className="w-4 h-4 text-fuchsia-400" />
                  </div>
                  <h3 className="text-white font-semibold font-display text-[16px]">Resolutions, not just answers</h3>
                </div>
                <p className="text-white/50 text-[13px] leading-relaxed mb-4">
                  Access provisioned, code generated, and incidents resolved. Not just routed, but autonomously executed with zero hallucinations.
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-fuchsia-500/10 text-fuchsia-300 border border-fuchsia-500/20">
                    ⚡ Autonomous Execution
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-green-500/10 text-green-300 border border-green-500/20">
                    ✓ 99.2% Accuracy
                  </span>
                </div>
              </div>

              <div
                className="p-6 rounded-2xl transition-all duration-300 hover:border-cyan-500/30"
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-cyan-500/10 border border-cyan-500/30">
                    <Brain className="w-4 h-4 text-cyan-400" />
                  </div>
                  <h3 className="text-white font-semibold font-display text-[16px]">Provide the right context at the right time</h3>
                </div>
                <p className="text-white/50 text-[13px] leading-relaxed mb-4">
                  Every successful execution and edge case is reflected upon and synthesized into structured episodic memory for future runs.
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    🧠 Episodic Recall
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    📈 Self-Improving
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Before / After Section ───────────────────────────────────────────────────
const beforeSteps = [
  { text: 'Solve task from scratch every time', time: '45+ MIN' },
  { text: 'No memory of past attempts', time: '—' },
  { text: 'Repeated errors on similar tasks', time: '30+ MIN' },
  { text: 'Manual prompt engineering each run', time: '20+ MIN' },
  { text: 'No quality tracking or improvement', time: '—' },
]
const afterSteps = [
  { text: 'Retrieve 3 relevant experiences instantly', time: 'INSTANT' },
  { text: 'Execute with validated strategies', time: '2 MIN' },
  { text: 'Automatically avoids past mistakes', time: '< 1 MIN' },
  { text: 'Memory-augmented context injected', time: 'AUTO' },
  { text: 'Trust scores track & improve quality', time: 'LIVE' },
]
// ─── 3D Tilt Card wrapper ───────────────────────────────────────────────────────────
function TiltCard({
  children, glowColor, style = {},
}: {
  children: React.ReactNode
  glowColor: string
  style?: React.CSSProperties
}) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [tilt, setTilt] = useState({ x: 0, y: 0 })
  const [hovered, setHovered] = useState(false)

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = cardRef.current; if (!el) return
    const { left, top, width, height } = el.getBoundingClientRect()
    const cx = (e.clientX - left) / width - 0.5
    const cy = (e.clientY - top)  / height - 0.5
    setTilt({ x: cy * -16, y: cx * 16 })
  }

  return (
    <div style={{ perspective: '900px' }}>
      <div
        ref={cardRef}
        className="rounded-3xl p-6 relative overflow-hidden"
        style={{
          ...style,
          transformStyle: 'preserve-3d',
          transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg) scale(${hovered ? 1.025 : 1})`,
          transition: hovered
            ? 'transform 80ms linear, box-shadow 80ms linear'
            : 'transform 600ms cubic-bezier(0.23,1,0.32,1), box-shadow 600ms ease',
          boxShadow: hovered
            ? `0 30px 70px ${glowColor}40, 0 0 0 1px ${glowColor}30`
            : `0 8px 32px ${glowColor}12`,
          cursor: 'default',
        }}
        onMouseMove={onMove}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => { setTilt({ x: 0, y: 0 }); setHovered(false) }}
      >
        {/* Moving specular highlight */}
        <div
          className="absolute inset-0 rounded-3xl pointer-events-none"
          style={{
            background: hovered
              ? `radial-gradient(circle at ${50 + tilt.y * 3}% ${50 - tilt.x * 3}%, rgba(255,255,255,0.07) 0%, transparent 55%)`
              : 'transparent',
            transition: hovered ? 'background 80ms linear' : 'none',
          }}
        />
        {children}
      </div>
    </div>
  )
}

// ─── Before / After Section (Atomicwork style exact match) ───────────────────
const beforePositions = [
  { top: '15%', left: '10%', rotate: '-3deg', z: 10, bg: '#252525' },
  { top: '38%', left: '5%',  rotate: '2deg',  z: 20, bg: '#2a2a2a' },
  { top: '60%', left: '12%', rotate: '-1deg', z: 15, bg: '#222222' },
  { top: '78%', left: '20%', rotate: '4deg',  z: 25, bg: '#282828' },
  { top: '48%', left: '35%', rotate: '-2deg', z: 30, bg: '#303030' },
]

function BeforeAfterSection() {
  const [visible, setVisible] = useState(false)
  const [tick, setTick] = useState(0)
  const [mins, setMins] = useState(120)
  const [queue, setQueue] = useState(37)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.2 }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  // Continuous tick for scanning effect
  useEffect(() => {
    if (visible) {
      const id = setInterval(() => setTick(t => t + 1), 50)
      return () => clearInterval(id)
    }
  }, [visible])

  // Fast countdown animation when visible
  useEffect(() => {
    if (visible) {
      const id = setInterval(() => {
        setMins(m => (m > 5 ? m - Math.max(1, Math.ceil((m - 5) / 8)) : 5))
        setQueue(q => (q > 0 ? q - Math.max(1, Math.ceil(q / 8)) : 0))
      }, 60)
      return () => clearInterval(id)
    }
  }, [visible])

  // Calculate scanning line position (0 to 100%)
  const scanY = (Math.sin(tick * 0.06) * 0.5 + 0.5) * 100

  return (
    <section ref={ref} className="py-24 px-6 relative bg-[#0a0010] overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-1/2 left-1/4 w-[600px] h-[600px] bg-purple-900/10 rounded-full blur-[140px] pointer-events-none -translate-y-1/2" />
      <div className="absolute top-1/2 right-1/4 w-[600px] h-[600px] bg-cyan-900/10 rounded-full blur-[140px] pointer-events-none -translate-y-1/2" />

      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-4"
            style={{ background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.3)' }}>
            <Sparkles size={13} className="text-fuchsia-400" />
            <span className="text-fuchsia-300 text-xs font-bold tracking-widest uppercase font-display">
              PARADIGM COMPARISON
            </span>
          </div>
          <h2 className="font-display font-bold text-white text-3xl lg:text-5xl leading-tight mb-4">
            Stateless Guesswork <span className="text-white/40 font-normal">vs.</span> <span className="gradient-text">Adaptive Memory</span>
          </h2>
          <p className="text-white/50 text-sm sm:text-base leading-relaxed">
            Without memory, agents repeat costly failures from scratch every time. With MemoryAgent, verified strategies execute in seconds with zero human triaging.
          </p>
        </div>

        {/* ── The Contained Split Comparison Canvas ── */}
        <div
          className="rounded-3xl border border-white/10 overflow-hidden relative shadow-2xl grid grid-cols-1 lg:grid-cols-2"
          style={{
            boxShadow: '0 30px 100px rgba(0,0,0,0.8), 0 0 60px rgba(168,85,247,0.1)',
          }}
        >

          {/* ── LEFT: BEFORE (Stateless Chaos) ── */}
          <div
            className="relative h-[620px] overflow-hidden p-6 sm:p-8 flex flex-col justify-between"
            style={{
              background: 'radial-gradient(circle at 20% 80%, rgba(239,68,68,0.08) 0%, #0d0614 70%)',
              borderRight: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            {/* Top Bar */}
            <div className="flex items-center justify-between z-30 relative">
              <div
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full"
                style={{ background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.4)' }}
              >
                <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
                <span className="text-red-400 text-xs font-bold tracking-wider font-display">BEFORE · STATELESS</span>
              </div>
              <span className="text-white/30 text-xs font-mono">AVG: 45+ MIN / RUN</span>
            </div>

            {/* Subtle tech grid */}
            <div
              className="absolute inset-0 opacity-10 pointer-events-none"
              style={{
                backgroundImage: 'radial-gradient(rgba(239,68,68,0.4) 1px, transparent 1px)',
                backgroundSize: '24px 24px',
              }}
            />

            {/* Floating chaotic cards */}
            <div className="absolute inset-0">
              {beforeSteps.map((s, i) => (
                <div
                  key={i}
                  className="absolute rounded-xl p-4 shadow-2xl transition-all duration-700 hover:z-50 hover:scale-105 cursor-default group"
                  style={{
                    top: beforePositions[i].top,
                    left: beforePositions[i].left,
                    transform: `rotate(${beforePositions[i].rotate})`,
                    zIndex: beforePositions[i].z,
                    background: 'rgba(20, 12, 28, 0.92)',
                    backdropFilter: 'blur(16px)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    width: '320px',
                    opacity: visible ? 1 : 0,
                    marginTop: visible ? 0 : '40px',
                    transitionDelay: `${0.1 + i * 0.15}s`,
                    boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
                  }}
                >
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0 bg-red-950/40 border border-red-500/20 flex items-center justify-center">
                      <img src={`https://i.pravatar.cc/100?img=${i + 12}`} alt="avatar" className="w-full h-full object-cover" />
                    </div>
                    <div className="flex-1">
                      <p className="text-white/80 text-[13px] leading-snug mb-2 font-medium">{s.text}</p>
                      <div className="flex items-center justify-between">
                        {s.time !== '—' ? (
                          <span
                            className="inline-block px-2 py-0.5 rounded text-[10px] font-bold font-mono"
                            style={{ background: 'rgba(239,68,68,0.18)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}
                          >
                            {s.time}
                          </span>
                        ) : (
                          <span className="text-[10px] text-white/30 font-mono">NO MEMORY CACHE</span>
                        )}
                        <span className="text-[10px] text-red-400/60 font-mono">Cold Start</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Bottom footnote */}
            <div className="relative z-30 pt-4 border-t border-white/5 flex items-center justify-between text-xs text-white/40 font-mono">
              <span>● Repeat error rate: ~34%</span>
              <span className="text-red-400 font-semibold">High Token Burn</span>
            </div>
          </div>

          {/* ── CENTER: High-tech Energy Divider Pill ── */}
          <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-40 items-center justify-center pointer-events-none">
            <div
              className="w-11 h-11 rounded-full flex items-center justify-center shadow-2xl backdrop-blur-xl border border-white/20"
              style={{
                background: 'linear-gradient(135deg, #7c3aed, #06b6d4)',
                boxShadow: '0 0 30px rgba(168,85,247,0.7), 0 0 10px rgba(34,211,238,0.5)',
              }}
            >
              <Zap size={16} className="text-white" />
            </div>
          </div>

          {/* ── RIGHT: AFTER (Dark Cyber Nebula Velocity) ── */}
          <div
            className="relative h-[620px] overflow-hidden flex items-center justify-center p-6 lg:p-10"
            style={{
              background: 'radial-gradient(circle at 75% 30%, rgba(168,85,247,0.22) 0%, rgba(34,211,238,0.12) 45%, #0e051c 90%)',
            }}
          >
            {/* Tech grid */}
            <div
              className="absolute inset-0 opacity-20 pointer-events-none"
              style={{
                backgroundImage: 'radial-gradient(rgba(168,85,247,0.4) 1px, transparent 1px)',
                backgroundSize: '24px 24px',
              }}
            />

            {/* Animated glowing orbs */}
            <div
              className="absolute top-[10%] right-[15%] w-[260px] h-[260px] rounded-full anim-float pointer-events-none"
              style={{ background: 'radial-gradient(circle, rgba(168,85,247,0.3) 0%, transparent 70%)', filter: 'blur(45px)' }}
            />
            <div
              className="absolute bottom-[10%] left-[15%] w-[220px] h-[220px] rounded-full anim-float pointer-events-none"
              style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.2) 0%, transparent 70%)', filter: 'blur(40px)', animationDelay: '1s' }}
            />

            {/* Top Bar Badge */}
            <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-30">
              <div
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full"
                style={{ background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.4)' }}
              >
                <span className="w-2 h-2 rounded-full bg-green-400 animate-ping" />
                <span className="text-green-300 text-xs font-bold tracking-wider font-display">AFTER · MEMORYAGENT</span>
              </div>
            </div>

            {/* Central Glass Card */}
            <div
              className="w-full max-w-lg z-10 transition-all duration-1000 relative mt-6"
              style={{
                opacity: visible ? 1 : 0,
                transform: visible ? 'translateY(0)' : 'translateY(40px)',
                transitionDelay: '0.3s',
              }}
            >
              <TiltCard
                glowColor="#a855f7"
                style={{
                  background: 'rgba(14, 8, 26, 0.88)',
                  backdropFilter: 'blur(28px)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  padding: 0,
                  boxShadow: '0 30px 80px rgba(0,0,0,0.6), 0 0 40px rgba(168,85,247,0.15)',
                }}
              >
                {/* AI Scanning effect overlay */}
                <div className="absolute inset-0 pointer-events-none overflow-hidden z-20 rounded-[inherit]">
                  <div
                    className="w-full h-[2px] opacity-75"
                    style={{
                      background: 'linear-gradient(90deg, transparent, #a855f7, #22d3ee, #4ade80, transparent)',
                      boxShadow: '0 0 20px rgba(168,85,247,0.9), 0 0 10px rgba(34,211,238,0.7)',
                      position: 'absolute',
                      top: `${scanY}%`,
                    }}
                  />
                </div>

                {/* Header */}
                <div className="p-5 border-b border-white/10 flex items-start gap-3.5 relative z-30 bg-black/40">
                  <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg"
                    style={{ background: 'linear-gradient(135deg, #a855f7, #22d3ee)' }}
                  >
                    <Zap className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-[15px] font-display">
                      Tasks resolved automatically
                    </h3>
                    <p className="text-white/50 text-[11px] mt-0.5">
                      Memory-augmented context injected from past validated runs
                    </p>
                  </div>
                </div>

                {/* Rows */}
                <div className="p-4 space-y-1.5 relative z-30">
                  {afterSteps.map((s, i) => {
                    const rowY = 20 + i * 15
                    const isScanned = scanY > rowY
                    return (
                      <div
                        key={i}
                        className="flex items-center justify-between px-3.5 py-2.5 rounded-lg transition-all duration-300 relative overflow-hidden"
                        style={{
                          opacity: visible ? 1 : 0,
                          transform: visible ? 'translateX(0)' : 'translateX(20px)',
                          transitionDelay: `${0.4 + i * 0.1}s`,
                          background: isScanned ? 'rgba(255,255,255,0.04)' : 'transparent',
                        }}
                      >
                        {/* Processing sweep background */}
                        <div
                          className="absolute top-0 bottom-0 left-0 transition-all duration-[1500ms] ease-out z-0"
                          style={{
                            background: 'linear-gradient(90deg, rgba(168,85,247,0.15), transparent)',
                            width: visible && isScanned ? '100%' : '0%',
                          }}
                        />
                        <div className="flex items-center gap-3 relative z-10">
                          <CheckCircle2
                            className="w-4 h-4 transition-colors duration-500"
                            style={{ color: isScanned ? '#4ade80' : '#4b5563' }}
                          />
                          <span className="text-white/85 text-[13px]">{s.text}</span>
                        </div>
                        <span
                          className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded uppercase tracking-wider relative z-10 transition-all duration-500 ${
                            isScanned && s.time === 'LIVE' ? 'anim-pulse-ring' : ''
                          }`}
                          style={{
                            background: isScanned ? 'rgba(34,197,94,0.18)' : 'rgba(255,255,255,0.05)',
                            color: isScanned ? '#4ade80' : '#6b7280',
                            boxShadow: isScanned && s.time === 'LIVE' ? '0 0 10px rgba(34,197,94,0.4)' : 'none',
                          }}
                        >
                          {s.time}
                        </span>
                      </div>
                    )
                  })}
                </div>

                {/* Metrics Footer */}
                <div className="p-5 border-t border-white/10 flex justify-center gap-12 sm:gap-16 relative z-30 bg-black/40">
                  <div className="text-center">
                    <div className="flex items-baseline justify-center font-display font-bold">
                      <span className="text-2xl opacity-60 mr-1 text-white">~</span>
                      <span
                        className="text-4xl sm:text-5xl transition-colors duration-500"
                        style={{ color: mins <= 5 ? '#4ade80' : 'white' }}
                      >
                        {mins}
                      </span>
                    </div>
                    <p className="text-white/40 text-[9px] font-bold tracking-[0.2em] mt-1 font-display">MINUTES</p>
                  </div>
                  <div className="text-center">
                    <div className="flex items-baseline justify-center font-display font-bold h-[52px]">
                      <span
                        className="text-4xl sm:text-5xl transition-colors duration-500"
                        style={{ color: queue === 0 ? '#4ade80' : 'white', lineHeight: '52px' }}
                      >
                        {queue}
                      </span>
                    </div>
                    <p className="text-white/40 text-[9px] font-bold tracking-[0.2em] mt-1 font-display">QUEUE</p>
                  </div>
                  <div className="text-center hidden sm:block">
                    <div className="flex items-baseline justify-center font-display font-bold h-[52px]">
                      <span className="text-4xl sm:text-5xl text-cyan-400" style={{ lineHeight: '52px' }}>
                        12x
                      </span>
                    </div>
                    <p className="text-white/40 text-[9px] font-bold tracking-[0.2em] mt-1 font-display">SPEEDUP</p>
                  </div>
                </div>
              </TiltCard>
            </div>

            {/* Floating cursors/labels */}
            <div className="absolute top-20 right-[8%] anim-float hidden sm:block" style={{ animationDelay: '1s' }}>
              <div className="px-3 py-1.5 rounded-full bg-[#1e1b4b]/90 border border-[#6366f1] text-[#a5b4fc] text-[9px] font-bold tracking-widest uppercase shadow-xl flex items-center gap-2 backdrop-blur-md">
                <ArrowRight className="w-3 h-3 rotate-135" />
                DEVICE OPS ENGINEER
              </div>
            </div>
            <div className="absolute bottom-16 left-[8%] anim-float hidden sm:block" style={{ animationDelay: '0.5s' }}>
              <div className="px-3 py-1.5 rounded-full bg-[#4a044e]/90 border border-[#d946ef] text-[#f0abfc] text-[9px] font-bold tracking-widest uppercase shadow-xl flex items-center gap-2 backdrop-blur-md">
                <ArrowRight className="w-3 h-3 -rotate-45" />
                IT OPS ENGINEER
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}


// ─── Performance Graph (Exact Atomicwork Regression Stacked Area Model) ──────

const CHART_CATEGORIES = [
  {
    name: 'Onboarding Manager',
    color: '#8b5cf6',
    stroke: '#a78bfa',
    fillGradient: ['#8b5cf6', '#6d28d9'],
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
        <rect x="2" y="2" width="12" height="12" rx="3" fill="#8b5cf6" fillOpacity="0.3" stroke="#8b5cf6" strokeWidth="1.5"/>
        <path d="M5 8h6M8 5v6" stroke="#c4b5fd" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    name: 'HR Ops Specialist',
    color: '#10b981',
    stroke: '#34d399',
    fillGradient: ['#10b981', '#059669'],
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
        <circle cx="8" cy="8" r="6" fill="#10b981" fillOpacity="0.25" stroke="#10b981" strokeWidth="1.5"/>
        <circle cx="8" cy="8" r="2.5" fill="#6ee7b7"/>
      </svg>
    ),
  },
  {
    name: 'IT Ops Engineer',
    color: '#f97316',
    stroke: '#fb923c',
    fillGradient: ['#f97316', '#c2410c'],
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
        <polygon points="8,2 14,8 8,14 2,8" fill="#f97316" fillOpacity="0.25" stroke="#f97316" strokeWidth="1.5"/>
        <circle cx="8" cy="8" r="2" fill="#fdba74"/>
      </svg>
    ),
  },
  {
    name: 'Incident Manager',
    color: '#facc15',
    stroke: '#fde047',
    fillGradient: ['#facc15', '#ca8a04'],
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 1.5l2 4 4.5.7-3.2 3.1.8 4.5L8 11.6l-4.1 2.2.8-4.5-3.2-3.1 4.5-.7z" fill="#facc15" fillOpacity="0.3" stroke="#facc15" strokeWidth="1.2"/>
      </svg>
    ),
  },
]

// High-precision non-linear regression curve computation (Sigmoid + Exponential polynomial)
function evalRegressionCurve(t: number): { total: number; y0: number; y1: number; y2: number; y3: number } {
  // Sigmoid growth component + baseline exponential learning
  const s = 1 / (1 + Math.exp(-7.5 * (t - 0.65)))
  const p = Math.pow(t, 2.2)
  const raw = 0.3 * p + 0.7 * s
  const raw0 = 0.7 * (1 / (1 + Math.exp(7.5 * 0.65)))
  const raw1 = 0.3 + 0.7 * (1 / (1 + Math.exp(-7.5 * 0.35)))
  const normalized = Math.max(0, Math.min(1, (raw - raw0) / (raw1 - raw0)))
  const total = normalized * 160

  // Proportional breakdown matching Atomicwork stacked area distribution
  const y0 = total * (0.50 + 0.075 * t)       // Onboarding Manager (Purple) reaches ~92
  const y1 = total * (0.75 + 0.03125 * t)     // HR Ops Specialist (Emerald) reaches ~125
  const y2 = total * (0.90 + 0.0125 * t)      // IT Ops Engineer (Orange) reaches ~146
  const y3 = total                            // Incident Manager (Yellow) reaches 160

  return { total, y0, y1, y2, y3 }
}

function PerformanceGraph() {
  const [activeTab, setActiveTab] = useState(2) // 0: Employees, 1: IT Teams, 2: Business Leaders
  const [showConfidence, setShowConfidence] = useState(false)
  const [showPromptDetails, setShowPromptDetails] = useState(false)
  const [progress, setProgress] = useState(0)
  const [hoverT, setHoverT] = useState<number | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  const W = 720
  const H = 340
  const PAD = { l: 48, r: 24, t: 24, b: 36 }
  const gW = W - PAD.l - PAD.r
  const gH = H - PAD.t - PAD.b

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          let p = 0
          const id = setInterval(() => {
            p += 3
            setProgress(Math.min(p, 100))
            if (p >= 100) clearInterval(id)
          }, 16)
        }
      },
      { threshold: 0.2 }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  // Generate 40 dense evaluation points for mathematically smooth regression curves
  const NUM_STEPS = 40
  const points = Array.from({ length: NUM_STEPS + 1 }, (_, i) => {
    const t = i / NUM_STEPS
    const x = PAD.l + t * gW
    const vals = evalRegressionCurve(t)
    return {
      t,
      x,
      yBase: PAD.t + gH,
      y0: PAD.t + gH - (vals.y0 / 160) * gH,
      y1: PAD.t + gH - (vals.y1 / 160) * gH,
      y2: PAD.t + gH - (vals.y2 / 160) * gH,
      y3: PAD.t + gH - (vals.y3 / 160) * gH,
      vals,
    }
  })

  // SVG Area Paths
  const getAreaD = (topKey: 'y0' | 'y1' | 'y2' | 'y3', botKey: 'yBase' | 'y0' | 'y1' | 'y2') => {
    let d = `M ${points[0].x.toFixed(1)},${points[0][topKey].toFixed(1)}`
    for (let i = 1; i <= NUM_STEPS; i++) {
      d += ` L ${points[i].x.toFixed(1)},${points[i][topKey].toFixed(1)}`
    }
    for (let i = NUM_STEPS; i >= 0; i--) {
      d += ` L ${points[i].x.toFixed(1)},${points[i][botKey].toFixed(1)}`
    }
    d += ' Z'
    return d
  }

  // Boundary Stroke Paths
  const getLineD = (key: 'y0' | 'y1' | 'y2' | 'y3') => {
    let d = `M ${points[0].x.toFixed(1)},${points[0][key].toFixed(1)}`
    for (let i = 1; i <= NUM_STEPS; i++) {
      d += ` L ${points[i].x.toFixed(1)},${points[i][key].toFixed(1)}`
    }
    return d
  }

  // 95% Confidence Interval Prediction Corridor
  const getConfidenceAreaD = () => {
    let d = `M ${points[0].x.toFixed(1)},${points[0].y3.toFixed(1)}`
    for (let i = 1; i <= NUM_STEPS; i++) {
      const offset = Math.min(18, 4 + Math.sqrt(points[i].t) * 12)
      const yUpper = Math.max(PAD.t, points[i].y3 - offset)
      d += ` L ${points[i].x.toFixed(1)},${yUpper.toFixed(1)}`
    }
    for (let i = NUM_STEPS; i >= 0; i--) {
      const offset = Math.min(18, 4 + Math.sqrt(points[i].t) * 12)
      const yLower = Math.min(PAD.t + gH, points[i].y3 + offset)
      d += ` L ${points[i].x.toFixed(1)},${yLower.toFixed(1)}`
    }
    d += ' Z'
    return d
  }

  const clipW = (progress / 100) * (W - PAD.l - PAD.r)

  // Handle cursor hover scrub
  const onMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const xRatio = (e.clientX - rect.left - (PAD.l / W) * rect.width) / ((gW / W) * rect.width)
    const clampedT = Math.max(0, Math.min(1, xRatio))
    setHoverT(clampedT)
  }

  const hoverData = hoverT !== null ? evalRegressionCurve(hoverT) : null
  const hoverX = hoverT !== null ? PAD.l + hoverT * gW : 0
  const hoverDay = hoverT !== null ? Math.round(hoverT * 90) : 0

  return (
    <section className="py-24 px-6 bg-[#0a0010] relative overflow-hidden" ref={ref}>
      {/* Ambient background bloom */}
      <div className="absolute top-1/4 left-1/5 w-[650px] h-[650px] bg-purple-900/15 rounded-full blur-[160px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[550px] h-[550px] bg-emerald-900/12 rounded-full blur-[160px] pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* ── TOP SECTION HEADER & AUDIENCE TABS (Matching Atomicwork Reference) ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6 mb-8">
          <div>
            <span className="text-white/45 text-xs font-mono font-bold tracking-[0.2em] uppercase block">
              AI-NATIVE ITSM AND ESM SOLUTION
            </span>
          </div>
          <div className="flex items-center gap-4 sm:gap-8 text-xs font-mono tracking-wider">
            {[
              { id: 0, label: '1. FOR EMPLOYEES' },
              { id: 1, label: '2. FOR IT TEAMS' },
              { id: 2, label: '3. FOR BUSINESS LEADERS' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`transition-all duration-200 pb-1 cursor-pointer uppercase ${
                  activeTab === tab.id
                    ? 'text-white font-bold border-b-2 border-[#10b981]'
                    : 'text-white/40 hover:text-white/75'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Section Headline */}
        <div className="mb-10">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-white tracking-tight leading-[1.1]">
            like your teams.
          </h2>
          <p className="text-white/50 text-sm sm:text-base font-sans mt-3 max-w-2xl font-light">
            Continuous resolution intelligence modeled over 90 days. Watch autonomous agent resolutions compound across departments.
          </p>
        </div>

        {/* ── MAIN 2-COLUMN DISPLAY (Atomicwork Side-by-Side Cards) ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          
          {/* ── LEFT: Stacked Area Regression Model Chart (lg:col-span-8) ── */}
          <div className="lg:col-span-8 flex flex-col">
            
            {/* Header above chart */}
            <div className="flex items-center justify-between mb-3">
              <p className="text-white/45 text-xs font-bold font-mono tracking-widest uppercase">
                3X INCREASE IN AI RESOLUTIONS IN 3 MONTHS
              </p>
              {/* Regression Model Info & Confidence Toggle */}
              <div className="hidden sm:flex items-center gap-3">
                <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-950/40 border border-cyan-800/40 px-2 py-0.5 rounded">
                  R² = 0.994 · Poly-3
                </span>
                <button
                  onClick={() => setShowConfidence(!showConfidence)}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded transition-all cursor-pointer ${
                    showConfidence
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/50'
                      : 'bg-white/5 text-white/40 border border-white/10 hover:text-white'
                  }`}
                >
                  {showConfidence ? '✓ 95% CI Corridor' : '+ Show 95% CI'}
                </button>
              </div>
            </div>

            {/* Chart Card */}
            <div
              className="rounded-2xl p-6 sm:p-7 relative overflow-hidden flex-1 flex flex-col justify-between"
              style={{
                background: 'rgba(16, 9, 28, 0.78)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: '0 25px 70px rgba(0,0,0,0.6)',
              }}
            >
              {/* Legend matching reference screenshot */}
              <div className="flex flex-wrap items-center gap-5 sm:gap-7 mb-6">
                {CHART_CATEGORIES.map((cat) => (
                  <div key={cat.name} className="flex items-center gap-2">
                    {cat.icon}
                    <span className="text-white/60 text-xs font-sans font-medium tracking-wide">
                      {cat.name}
                    </span>
                  </div>
                ))}
              </div>

              {/* Chart SVG Canvas */}
              <div className="w-full relative">
                <svg
                  viewBox={`0 0 ${W} ${H}`}
                  className="w-full h-auto cursor-crosshair select-none"
                  preserveAspectRatio="xMidYMid meet"
                  onMouseMove={onMouseMove}
                  onMouseLeave={() => setHoverT(null)}
                >
                  <defs>
                    {/* Exact Color Gradients matching Atomicwork screenshot */}
                    <linearGradient id="grad-layer-0" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.95" />
                      <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.8" />
                    </linearGradient>
                    <linearGradient id="grad-layer-1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.95" />
                      <stop offset="100%" stopColor="#059669" stopOpacity="0.8" />
                    </linearGradient>
                    <linearGradient id="grad-layer-2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f97316" stopOpacity="0.95" />
                      <stop offset="100%" stopColor="#ea580c" stopOpacity="0.8" />
                    </linearGradient>
                    <linearGradient id="grad-layer-3" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#fde047" stopOpacity="0.95" />
                      <stop offset="100%" stopColor="#facc15" stopOpacity="0.85" />
                    </linearGradient>

                    {/* Fine stipple / grain texture overlay matching Atomicwork vector artwork */}
                    <pattern id="atomic-stipple" width="5" height="5" patternUnits="userSpaceOnUse">
                      <circle cx="1.5" cy="1.5" r="0.75" fill="#ffffff" opacity="0.18" />
                      <circle cx="4" cy="4" r="0.55" fill="#000000" opacity="0.25" />
                    </pattern>

                    {/* Entrance animation clip */}
                    <clipPath id="reg-chart-clip">
                      <rect x={PAD.l} y={PAD.t - 10} width={clipW} height={gH + 20} />
                    </clipPath>
                  </defs>

                  {/* Horizontal Grid lines matching 160, 128, 96, 64, 32, 0 */}
                  {[160, 128, 96, 64, 32, 0].map((val) => {
                    const y = PAD.t + gH - (val / 160) * gH
                    return (
                      <g key={val}>
                        <line
                          x1={PAD.l}
                          y1={y}
                          x2={W - PAD.r}
                          y2={y}
                          stroke="rgba(255, 255, 255, 0.08)"
                          strokeWidth="1"
                        />
                        {/* Y-axis numbers */}
                        <text
                          x={PAD.l - 12}
                          y={y + 4}
                          fill="rgba(255, 255, 255, 0.45)"
                          fontSize="11"
                          fontFamily="Inter, monospace"
                          textAnchor="end"
                        >
                          {val}
                        </text>
                      </g>
                    )
                  })}

                  {/* X-axis labels: Jan, Feb, Mar */}
                  <text
                    x={PAD.l}
                    y={H - 8}
                    fill="rgba(255, 255, 255, 0.45)"
                    fontSize="11"
                    fontFamily="Inter, sans-serif"
                    textAnchor="start"
                  >
                    Jan
                  </text>
                  <text
                    x={PAD.l + gW * 0.5}
                    y={H - 8}
                    fill="rgba(255, 255, 255, 0.45)"
                    fontSize="11"
                    fontFamily="Inter, sans-serif"
                    textAnchor="middle"
                  >
                    Feb
                  </text>
                  <text
                    x={W - PAD.r}
                    y={H - 8}
                    fill="rgba(255, 255, 255, 0.45)"
                    fontSize="11"
                    fontFamily="Inter, sans-serif"
                    textAnchor="end"
                  >
                    Mar
                  </text>

                  {/* Stacked Regression Model Curves (clipped with entrance animation) */}
                  <g clipPath="url(#reg-chart-clip)">
                    {/* Layer 3 (Top: Yellow - Incident Manager) */}
                    <path d={getAreaD('y3', 'y2')} fill="url(#grad-layer-3)" />
                    <path d={getAreaD('y3', 'y2')} fill="url(#atomic-stipple)" />
                    <path d={getLineD('y3')} fill="none" stroke="#fef08a" strokeWidth="1.5" />

                    {/* Layer 2 (Orange - IT Ops Engineer) */}
                    <path d={getAreaD('y2', 'y1')} fill="url(#grad-layer-2)" />
                    <path d={getAreaD('y2', 'y1')} fill="url(#atomic-stipple)" />
                    <path d={getLineD('y2')} fill="none" stroke="#fdba74" strokeWidth="1.5" />

                    {/* Layer 1 (Emerald Green - HR Ops Specialist) */}
                    <path d={getAreaD('y1', 'y0')} fill="url(#grad-layer-1)" />
                    <path d={getAreaD('y1', 'y0')} fill="url(#atomic-stipple)" />
                    <path d={getLineD('y1')} fill="none" stroke="#6ee7b7" strokeWidth="1.5" />

                    {/* Layer 0 (Bottom: Purple - Onboarding Manager) */}
                    <path d={getAreaD('y0', 'yBase')} fill="url(#grad-layer-0)" />
                    <path d={getAreaD('y0', 'yBase')} fill="url(#atomic-stipple)" />
                    <path d={getLineD('y0')} fill="none" stroke="#a78bfa" strokeWidth="1.5" />

                    {/* Optional 95% Confidence Interval Corridor */}
                    {showConfidence && (
                      <path
                        d={getConfidenceAreaD()}
                        fill="rgba(250, 204, 21, 0.15)"
                        stroke="rgba(250, 204, 21, 0.4)"
                        strokeWidth="1"
                        strokeDasharray="4 4"
                      />
                    )}
                  </g>

                  {/* Interactive Scrub Cursor Line */}
                  {hoverT !== null && hoverData && (
                    <g>
                      <line
                        x1={hoverX}
                        y1={PAD.t}
                        x2={hoverX}
                        y2={PAD.t + gH}
                        stroke="rgba(255, 255, 255, 0.65)"
                        strokeWidth="1.5"
                        strokeDasharray="4 4"
                      />
                      {/* Dots on each layer */}
                      {[
                        { y: PAD.t + gH - (hoverData.y0 / 160) * gH, color: '#a78bfa' },
                        { y: PAD.t + gH - (hoverData.y1 / 160) * gH, color: '#34d399' },
                        { y: PAD.t + gH - (hoverData.y2 / 160) * gH, color: '#fb923c' },
                        { y: PAD.t + gH - (hoverData.y3 / 160) * gH, color: '#fde047' },
                      ].map((pt, k) => (
                        <circle
                          key={k}
                          cx={hoverX}
                          cy={pt.y}
                          r="4"
                          fill={pt.color}
                          stroke="#0a0010"
                          strokeWidth="2"
                        />
                      ))}
                    </g>
                  )}
                </svg>

                {/* Floating Interactive Regression Tooltip */}
                {hoverT !== null && hoverData && (
                  <div
                    className="absolute top-2 pointer-events-none p-3.5 rounded-xl backdrop-blur-md shadow-2xl border border-white/10"
                    style={{
                      left: `${(hoverX / W) * 100}%`,
                      transform: hoverT > 0.55 ? 'translateX(-105%)' : 'translateX(12px)',
                      background: 'rgba(10, 4, 20, 0.94)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-4 mb-1">
                      <p className="text-white/40 text-[10px] font-mono uppercase tracking-wider">
                        {hoverDay <= 30 ? `Jan ${hoverDay || 1}` : hoverDay <= 60 ? `Feb ${hoverDay - 30}` : `Mar ${hoverDay - 60}`} · Day {hoverDay}
                      </p>
                      <span className="text-[9px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded">
                        Model: ŷ = f(t)
                      </span>
                    </div>

                    <p className="text-white font-display font-bold text-base mb-2">
                      Total: {Math.round(hoverData.total)} Resolutions
                    </p>

                    <div className="space-y-1 text-[11px] font-mono">
                      <div className="flex items-center justify-between gap-4 text-yellow-300">
                        <span>Incident Manager:</span>
                        <span className="font-bold">{Math.round(hoverData.y3 - hoverData.y2)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 text-orange-400">
                        <span>IT Ops Engineer:</span>
                        <span className="font-bold">{Math.round(hoverData.y2 - hoverData.y1)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 text-emerald-400">
                        <span>HR Ops Specialist:</span>
                        <span className="font-bold">{Math.round(hoverData.y1 - hoverData.y0)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 text-purple-300">
                        <span>Onboarding Manager:</span>
                        <span className="font-bold">{Math.round(hoverData.y0)}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── RIGHT: Metrics Card matching Atomicwork (lg:col-span-4) ── */}
          <div className="lg:col-span-4 flex flex-col">
            
            {/* Header above metrics card */}
            <p className="text-white/45 text-xs font-bold font-mono tracking-widest uppercase mb-3">
              20% INCREASE IN ROI IN 3 MONTHS
            </p>

            {/* Metrics Glass Card */}
            <div
              className="rounded-2xl p-7 flex flex-col justify-between flex-1"
              style={{
                background: 'rgba(16, 9, 28, 0.78)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: '0 25px 70px rgba(0,0,0,0.6)',
              }}
            >
              {/* Active AI Coworkers Header */}
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2.5 h-2.5 rounded-[2px] bg-[#10b981]" />
                  <span className="text-[#10b981] text-xs font-mono font-bold tracking-widest uppercase">
                    ACTIVE AI COWORKERS
                  </span>
                </div>
                <div className="text-[#10b981] font-display font-bold text-5xl sm:text-6xl tracking-tight">
                  156
                </div>
              </div>

              {/* 2-Column Metrics Grid matching exact screenshot */}
              <div className="grid grid-cols-2 gap-y-7 gap-x-6">
                <div>
                  <p className="text-white/40 text-[11px] font-bold font-mono tracking-wider mb-1 uppercase">
                    AI DEFLECTION RATE
                  </p>
                  <p className="text-white font-display font-bold text-2xl">
                    80%
                  </p>
                </div>

                <div>
                  <p className="text-white/40 text-[11px] font-bold font-mono tracking-wider mb-1 uppercase">
                    SLA ADHERENCE
                  </p>
                  <p className="text-white font-display font-bold text-2xl">
                    99.9%
                  </p>
                </div>

                <div>
                  <p className="text-white/40 text-[11px] font-bold font-mono tracking-wider mb-1 uppercase">
                    TIME TO FIRST RESPONSE
                  </p>
                  <p className="text-white font-display font-bold text-2xl">
                    18s
                  </p>
                </div>

                <div>
                  <p className="text-white/40 text-[11px] font-bold font-mono tracking-wider mb-1 uppercase">
                    MTTR
                  </p>
                  <p className="text-white font-display font-bold text-2xl">
                    6 min
                  </p>
                </div>

                <div>
                  <p className="text-white/40 text-[11px] font-bold font-mono tracking-wider mb-1 uppercase">
                    EMPLOYEE SATISFACTION
                  </p>
                  <p className="text-white font-display font-bold text-2xl">
                    98%
                  </p>
                </div>

                <div>
                  <p className="text-white/40 text-[11px] font-bold font-mono tracking-wider mb-1 uppercase">
                    ROI
                  </p>
                  <p className="text-white font-display font-bold text-2xl">
                    $1.8M
                  </p>
                </div>
              </div>
            </div>

          </div>

        </div>

        {/* ── FLOATING PROMPT PILL (Matching Atomicwork Reference Center) ── */}
        <div className="flex justify-center -mt-4 relative z-20">
          <button
            onClick={() => setShowPromptDetails(!showPromptDetails)}
            className="group flex items-center gap-3 px-6 py-3.5 rounded-full backdrop-blur-xl border border-white/20 hover:border-[#fb923c]/60 shadow-2xl transition-all duration-300 cursor-pointer"
            style={{
              background: 'rgba(22, 12, 38, 0.92)',
              boxShadow: '0 10px 35px rgba(0,0,0,0.5), 0 0 20px rgba(249,115,22,0.15)',
            }}
          >
            <span className="text-white/90 text-sm font-sans font-medium tracking-wide">
              What can your AI Coworkers actually resolve?
            </span>
            <div className="w-6 h-6 rounded-full bg-[#f97316] flex items-center justify-center text-white shadow group-hover:translate-x-0.5 transition-transform">
              <ArrowRight size={13} />
            </div>
          </button>
        </div>

        {/* Expandable Capabilities Drawer when clicking the pill */}
        {showPromptDetails && (
          <div className="mt-8 p-6 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md anim-float-up">
            <h4 className="text-white font-display font-bold text-base mb-4 flex items-center gap-2">
              <Sparkles size={16} className="text-[#f97316]" />
              Automated Workflows Ready to Deploy Out-of-the-Box
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-800/30">
                <span className="font-bold text-purple-300 block mb-1">Onboarding Manager</span>
                <p className="text-white/60">Automated employee SaaS provisioning, hardware request routing, and policy verification.</p>
              </div>
              <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-800/30">
                <span className="font-bold text-emerald-300 block mb-1">HR Ops Specialist</span>
                <p className="text-white/60">Instant benefits inquiry resolution, PTO policy clarification, and payroll change validation.</p>
              </div>
              <div className="p-3.5 rounded-xl bg-orange-950/20 border border-orange-800/30">
                <span className="font-bold text-orange-300 block mb-1">IT Ops Engineer</span>
                <p className="text-white/60">Single sign-on MFA resets, VPN configuration assistance, and access delegation management.</p>
              </div>
              <div className="p-3.5 rounded-xl bg-yellow-950/20 border border-yellow-800/30">
                <span className="font-bold text-yellow-300 block mb-1">Incident Manager</span>
                <p className="text-white/60">Automated alert correlation, stakeholder status page dispatch, and preliminary root cause synthesis.</p>
              </div>
            </div>
          </div>
        )}

        {/* ── 4 BOTTOM CAPABILITY PILLARS (Matching Atomicwork Reference Bottom) ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 mt-16 pt-10 border-t border-white/10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[#f97316] font-bold text-base">✓</span>
              <h4 className="text-white font-sans font-bold text-sm">
                Lifecycle management
              </h4>
            </div>
            <p className="text-white/50 text-xs font-sans leading-relaxed">
              Deploy, manage, version and govern every autonomous AI Coworker with complete auditability.
            </p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[#f97316] font-bold text-base">✓</span>
              <h4 className="text-white font-sans font-bold text-sm">
                Single AI control plane
              </h4>
            </div>
            <p className="text-white/50 text-xs font-sans leading-relaxed">
              From access to budgets to cross-model memory across OpenAI, Claude, and Gemini.
            </p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[#f97316] font-bold text-base">✓</span>
              <h4 className="text-white font-sans font-bold text-sm">
                Role-based access control
              </h4>
            </div>
            <p className="text-white/50 text-xs font-sans leading-relaxed">
              Manage every AI Coworker's permission scopes, tools, and private memory namespaces.
            </p>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[#f97316] font-bold text-base">✓</span>
              <h4 className="text-white font-sans font-bold text-sm">
                Cost and usage governance
              </h4>
            </div>
            <p className="text-white/50 text-xs font-sans leading-relaxed">
              Set budgets, spend limits and usage caps while reducing repetitive LLM token costs by 68%.
            </p>
          </div>
        </div>

      </div>
    </section>
  )
}

// ─── Features (Removed) ───────────────────────────────────────────────────────

const logos = ['pgvector', 'FastAPI', 'PostgreSQL', 'React', 'Docker', 'OpenAI', 'Supabase', 'Python']

// ─── Landing Page ─────────────────────────────────────────────────────────────
export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', fn)
    return () => window.removeEventListener('scroll', fn)
  }, [])

  return (
    <div className="min-h-screen bg-[#0a0010] font-sans overflow-x-hidden">
      <Navbar scrolled={scrolled} />

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center overflow-hidden">
        {/* Vibrant background */}
        <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: 'url(/hero-bg.jpg)' }} />
        {/* Overlay */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/70 to-black/50" />
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-[#0a0010] to-transparent" />

        {/* Floating orbs */}
        <div className="absolute top-24 left-24 w-80 h-80 bg-purple-600/15 rounded-full blur-3xl anim-float pointer-events-none" />
        <div className="absolute bottom-24 left-48 w-60 h-60 bg-fuchsia-500/10 rounded-full blur-3xl anim-float delay-300 pointer-events-none" />

        {/* Animated memory node graph on the far right */}
        <MemoryNodes />

        <div className="relative max-w-7xl mx-auto px-6 pt-32 pb-24 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* ── Left: copy ───────────────────────────────────── */}
          <div>
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-8 anim-float-up"
              style={{ background: 'rgba(168,85,247,0.15)', border: '1px solid rgba(168,85,247,0.4)' }}
            >
              <Sparkles size={13} className="text-fuchsia-400" />
              <span className="text-fuchsia-300 text-xs font-bold tracking-widest uppercase font-display">G146 · Live Agent Demo</span>
            </div>

            <h1 className="font-display font-bold leading-[1.1] mb-6 anim-float-up delay-100">
              <span className="text-white text-5xl lg:text-6xl block">Watch the Agent</span>
              <span className="anim-shimmer-text text-5xl lg:text-6xl block mt-1">Learn in Real Time</span>
            </h1>

            <p className="text-white/55 text-lg leading-relaxed mb-8 anim-float-up delay-200 font-light">
              See MemoryAgent retrieve past experiences, use them to answer better, and store new lessons —{' '}
              <span className="text-white/90 font-medium">all happening live on the right.</span>
            </p>

            {/* Mini stat badges */}
            <div className="flex flex-col gap-3 mb-8 anim-float-up delay-300">
              <StatBadge icon={Database}  val="Memories Retrieved"  label="Before every task execution" color="#a855f7" />
              <StatBadge icon={Star}      val="Trust Score Updated" label="After every outcome measured" color="#22d3ee" />
              <StatBadge icon={CheckCircle2} val="Experience Stored"  label="Reusable lesson extracted" color="#ec4899" />
            </div>

            <div className="flex gap-4 anim-float-up delay-500">
              <a
                id="hero-cta-primary"
                href="/dashboard"
                className="group flex items-center gap-2 text-white font-bold px-7 py-4 rounded-2xl cursor-pointer anim-gradient-bg hover:scale-105 transition-transform duration-200 shadow-lg text-sm"
              >
                Try it yourself <ArrowRight size={15} className="group-hover:translate-x-1 transition-transform" />
              </a>
              <a
                id="hero-cta-secondary"
                href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 font-semibold px-7 py-4 rounded-2xl cursor-pointer text-sm text-white/70 hover:text-white transition-all duration-200"
                style={{ border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.04)' }}
              >
                View GitHub
              </a>
            </div>
          </div>

          {/* ── Right: Live Demo Panel ────────────────────── */}
          <div className="flex justify-center lg:justify-end anim-slide-right">
            <LiveDemoPanel />
          </div>
        </div>
      </section>

      {/* ── Logo Marquee ─────────────────────────────────────────────────── */}
      <div className="border-y border-white/5 py-5 overflow-hidden" style={{ background: 'rgba(255,255,255,0.02)' }}>
        <div className="flex w-max marquee-track">
          {[...logos, ...logos].map((name, i) => (
            <div key={i} className="flex items-center gap-2 mx-10 opacity-30 hover:opacity-70 transition-opacity whitespace-nowrap">
              <div className="w-1.5 h-1.5 rounded-full anim-gradient-bg" />
              <span className="text-white text-sm font-semibold tracking-widest font-display">{name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Integrations Section ──────────────────────────────────────────────────── */}
      <IntegrationsSection />

      {/* ── Before / After ───────────────────────────────────────────────── */}
      <BeforeAfterSection />

      {/* ── Performance Graph ────────────────────────────────────────────── */}
      <PerformanceGraph />

      {/* ── Vibrant Stats Band ────────────────────────────────────────────── */}
      <section className="py-20 px-6 anim-gradient-bg">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { val: 'Memory ON', sub: 'vs Memory OFF evaluation' },
            { val: '< 500ms', sub: 'Experience retrieval latency' },
            { val: 'Reflexion', sub: 'Research-backed architecture' },
            { val: 'Python', sub: 'Custom agent orchestration' },
          ].map(s => (
            <div key={s.sub}>
              <p className="text-white text-2xl font-bold mb-1 font-display">{s.val}</p>
              <p className="text-white/60 text-xs">{s.sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="py-28 px-6" style={{ background: '#100020' }}>
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-display font-bold text-4xl lg:text-5xl mb-5">
            <span className="text-white">Ready to try </span>
            <span className="gradient-text-warm">MemoryAgent?</span>
          </h2>
          <p className="text-white/45 text-base mb-10 leading-relaxed">
            Submit a task. Watch it retrieve memories. See it get smarter with every run.
          </p>
          <a
            id="cta-banner-signup"
            href="/dashboard"
            className="inline-flex items-center gap-2 text-white font-bold px-10 py-4 rounded-2xl cursor-pointer anim-gradient-bg hover:scale-105 transition-transform shadow-xl"
          >
            Open Dashboard <ArrowRight size={16} />
          </a>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-8 px-6" style={{ background: '#0a0010' }}>
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center anim-gradient-bg">
              <Brain size={14} className="text-white" />
            </div>
            <span className="text-white/60 text-sm font-bold font-display">MemoryAgent · G146</span>
          </div>
          <p className="text-white/20 text-xs">Adaptive AI Agent · Kasat Sakshi Dattaprasad & Sumit Das</p>
          <div className="flex items-center gap-6">
            {['GitHub', 'Docs', 'Report'].map(link => (
              <a key={link} href="#" className="text-white/30 hover:text-white/70 text-xs transition-colors">{link}</a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}
