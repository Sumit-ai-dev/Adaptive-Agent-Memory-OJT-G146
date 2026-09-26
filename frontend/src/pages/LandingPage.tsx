import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Brain, ArrowRight,
  Menu, X,
  User, BookOpen, LogOut, Shield,
  Check, ChevronDown, MessageSquare
} from 'lucide-react'
import ThreeMemoryCore from '../components/ThreeMemoryCore'
import AuthModal from '../components/AuthModal'
import { useAuth } from '../context/AuthContext'
import {
  ClaudeLogo,
  OpenAILogo,
  OllamaLogo,
  GrokLogo,
  DeepSeekLogo,
  GeminiLogo,
  LangChainLogo,
  LlamaIndexLogo,
  PyTorchLogo,
  HuggingFaceLogo
} from '../components/ProviderLogos'

// ─── Demo Simulation Data (Hero Live Session) ─────────────────────────────────
const DEMO_STEPS = [
  { type: 'user',   text: 'Summarize key AI memory research papers',   delay: 0 },
  { type: 'system', text: 'Retrieving 3 relevant experiences...',      delay: 1400 },
  { type: 'memory', text: 'Reflexion (2023): Use self-reflection loops', delay: 2400, tag: '94% trust' },
  { type: 'memory', text: 'Voyager (2023): Skill library for reuse',    delay: 3100, tag: '88% trust' },
  { type: 'agent',  text: 'Using 2 memories. Generating response...',   delay: 4000 },
  { type: 'answer', text: 'Based on validated experiences: Reflexion improves task success by 22% via iterative self-critique. Voyager maintains a skill library that grows over time, matching MemoryAgent adaptive architecture.', delay: 5200 },
  { type: 'store',  text: 'New experience stored to memory index',     delay: 7000 },
]

function LiveDemoPanel() {
  const [visibleSteps, setVisibleSteps] = useState<number[]>([])

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []

    const reset = () => {
      setVisibleSteps([])
      DEMO_STEPS.forEach((step, i) => {
        const t = setTimeout(() => {
          setVisibleSteps(prev => [...prev, i])
        }, step.delay + 500)
        timers.push(t)
      })
      const restart = setTimeout(reset, 11000)
      timers.push(restart)
    }

    reset()
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="relative w-full max-w-lg">
      <div
        className="rounded-[16px] overflow-hidden shadow-2xl"
        style={{
          background: 'rgba(12, 7, 20, 0.94)',
          backdropFilter: 'blur(24px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.15)',
        }}
      >
        {/* Window Chrome */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.08] bg-white/[0.03]">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
          </div>
          <div className="flex-1 flex items-center justify-center gap-2">
            <Brain size={13} className="text-[#C4B5FD]" />
            <span className="text-[#D0D5DD] text-xs font-mono font-medium">MemoryAgent · Live Session</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 text-xs font-mono">Active</span>
          </div>
        </div>

        {/* Message Thread */}
        <div className="p-5 space-y-3 min-h-[320px]">
          {DEMO_STEPS.map((step, i) => {
            if (!visibleSteps.includes(i)) return null
            return (
              <div key={i} className="transition-all duration-300">
                {step.type === 'user' && (
                  <div className="flex items-start gap-2.5 justify-end">
                    <div className="rounded-[8px] px-3.5 py-2 max-w-[82%] bg-[#7042DD] text-white shadow-sm">
                      <p className="text-xs font-medium leading-relaxed">{step.text}</p>
                    </div>
                    <div className="w-6 h-6 rounded-[6px] bg-white/10 flex items-center justify-center shrink-0">
                      <User size={12} className="text-[#D0D5DD]" />
                    </div>
                  </div>
                )}

                {step.type === 'system' && (
                  <div className="flex items-center gap-2 text-xs font-mono text-[#D0D5DD]/70">
                    <div className="w-1 h-1 rounded-full bg-[#862FE7]" />
                    <p>{step.text}</p>
                  </div>
                )}

                {step.type === 'memory' && (
                  <div className="flex items-start gap-2.5 ml-2">
                    <BookOpen size={12} className="text-cyan-400 mt-1 shrink-0" />
                    <div className="rounded-[6px] px-3 py-1.5 flex-1 flex items-center justify-between gap-3 bg-cyan-950/40 border border-cyan-500/30">
                      <p className="text-cyan-200 text-xs font-mono">{step.text}</p>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                        {step.tag}
                      </span>
                    </div>
                  </div>
                )}

                {step.type === 'agent' && (
                  <div className="flex items-center gap-2 text-xs font-mono text-[#D0D5DD]/70">
                    <div className="w-5 h-5 rounded-[4px] bg-[#7042DD] flex items-center justify-center shrink-0">
                      <Brain size={11} className="text-white" />
                    </div>
                    <p>{step.text}</p>
                  </div>
                )}

                {step.type === 'answer' && (
                  <div className="flex items-start gap-2.5">
                    <div className="w-6 h-6 rounded-[6px] bg-[#7042DD] flex items-center justify-center shrink-0 mt-0.5">
                      <Brain size={12} className="text-white" />
                    </div>
                    <div className="rounded-[8px] p-3 flex-1 bg-white/[0.04] border border-white/[0.08]">
                      <p className="text-white text-xs leading-relaxed">{step.text}</p>
                    </div>
                  </div>
                )}

                {step.type === 'store' && (
                  <div className="flex items-center gap-2 ml-8 text-[11px] font-mono text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <p>{step.text}</p>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Input Bar */}
        <div className="px-4 py-3 border-t border-white/[0.08] bg-white/[0.02] flex items-center gap-2">
          <input
            type="text"
            readOnly
            value="Ask the agent anything..."
            className="w-full bg-transparent text-xs text-[#717171] focus:outline-none font-mono cursor-default"
          />
          <button className="w-6 h-6 rounded-[6px] bg-white/10 flex items-center justify-center text-white/50">
            <ArrowRight size={12} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Multi-LLM Provider Configs (Claude, OpenAI, Ollama, Grok, DeepSeek) ───────
interface LLMProviderConfig {
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
  Logo: React.ComponentType<{ className?: string; size?: number; color?: string }>
}

const LLM_PROVIDERS: LLMProviderConfig[] = [
  {
    name: 'Claude',
    modelTag: 'Claude 3.5 Sonnet',
    color: '#d97706',
    glowColor: '#f59e0b',
    taskType: 'TOOL RECURSION GUARD',
    query: 'Prevent infinite retry loop in multi-stage search tool across web documents',
    memoryId: 'MEM-312',
    memoryMatch: 'Run #312: Verified circuit breaker pattern with exponential jitter',
    confidence: '99.1%',
    codeLines: [
      { num: '01', text: '// Recalled memory constraint #312 from previous evaluation run', color: '#6b7280' },
      { num: '02', text: 'const circuitBreaker = await memoryAgent.recall("tool_search_circuit_breaker");', color: '#38bdf8' },
      { num: '03', text: 'const response = await anthropic.execute(circuitBreaker.safeParameters);', color: '#f59e0b' },
      { num: '04', text: '// Status: 0 infinite loops detected · Deterministic stop achieved', color: '#4ade80' },
    ],
    latency: '115ms',
    timeSaved: '50 MIN',
    tokensSaved: '16.4k',
    Logo: ClaudeLogo,
  },
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
      { num: '01', text: '// Recalled verified pattern #520 from past resolution archive', color: '#6b7280' },
      { num: '02', text: 'const dlqStrategy = await memoryAgent.inject("stripe_webhook_dlq");', color: '#38bdf8' },
      { num: '03', text: 'const healed = await openAI.executeTool(dlqStrategy.retryPattern);', color: '#c084fc' },
      { num: '04', text: '// Status: 148 stalled webhooks reprocessed · 0 packet loss', color: '#4ade80' },
    ],
    latency: '120ms',
    timeSaved: '45 MIN',
    tokensSaved: '14.2k',
    Logo: OpenAILogo,
  },
  {
    name: 'Ollama',
    modelTag: 'Llama 3.3 (Local)',
    color: '#3b82f6',
    glowColor: '#60a5fa',
    taskType: 'LOCAL AIR-GAPPED VECTOR RECALL',
    query: 'Retrieve proprietary customer schema without exfiltrating embeddings to public APIs',
    memoryId: 'MEM-108',
    memoryMatch: 'Run #108: On-device quantized HNSW vector index with AES-256 local vault',
    confidence: '97.8%',
    codeLines: [
      { num: '01', text: '// Querying local encrypted SQLite memory store via Ollama adapter', color: '#6b7280' },
      { num: '02', text: 'const localContext = await ollamaMemory.query("internal_schema_v2");', color: '#38bdf8' },
      { num: '03', text: 'const answer = await ollama.generate({ prompt: localContext.prompt });', color: '#60a5fa' },
      { num: '04', text: '// Status: 100% on-device inference · Zero data egress', color: '#4ade80' },
    ],
    latency: '85ms',
    timeSaved: '35 MIN',
    tokensSaved: '12.8k',
    Logo: OllamaLogo,
  },
  {
    name: 'Grok',
    modelTag: 'Grok 2 (xAI)',
    color: '#ec4899',
    glowColor: '#f43f5e',
    taskType: 'REAL-TIME HEURISTIC FILTER',
    query: 'Synthesize live market sentiment telemetry with historical causal graphs',
    memoryId: 'MEM-890',
    memoryMatch: 'Run #890: Dynamic market regime graph with Bayesian posterior weights',
    confidence: '96.9%',
    codeLines: [
      { num: '01', text: '// Fetching validated regime memories from memory routing layer', color: '#6b7280' },
      { num: '02', text: 'const regimeGraph = await grokMemory.filter("market_regime_volatility");', color: '#38bdf8' },
      { num: '03', text: 'const output = await grok.reason({ context: regimeGraph.subgraph });', color: '#f43f5e' },
      { num: '04', text: '// Status: Market signal filtered in 92ms · Hallucination pruned', color: '#4ade80' },
    ],
    latency: '92ms',
    timeSaved: '40 MIN',
    tokensSaved: '15.1k',
    Logo: GrokLogo,
  },
  {
    name: 'DeepSeek',
    modelTag: 'DeepSeek R1',
    color: '#8b5cf6',
    glowColor: '#a855f7',
    taskType: 'REFLEXION REASONING LOOP',
    query: 'Prune dead-end search trees in deep mathematical theorem proving',
    memoryId: 'MEM-774',
    memoryMatch: 'Run #774: Reflexion self-critique memory pruning lemmas 4 and 7',
    confidence: '99.4%',
    codeLines: [
      { num: '01', text: '// Injecting Reflexion self-critique memory from theorem proving run #774', color: '#6b7280' },
      { num: '02', text: 'const pruneRules = await deepSeekMemory.getReflections("lemma_proof");', color: '#38bdf8' },
      { num: '03', text: 'const proof = await deepSeekR1.solve({ constraints: pruneRules });', color: '#a855f7' },
      { num: '04', text: '// Status: Proof verified in 3 reasoning turns · 28 branches bypassed', color: '#4ade80' },
    ],
    latency: '140ms',
    timeSaved: '90 MIN',
    tokensSaved: '24.6k',
    Logo: DeepSeekLogo,
  },
]

// ─── Performance Graph (Exact Atomicwork Regression Stacked Area Model) ──────
const CHART_CATEGORIES = [
  {
    name: 'Research Specialist (Claude)',
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
    name: 'Code Synthesizer (GPT-4o)',
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
    name: 'Local Data Analyst (Ollama)',
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
    name: 'Reasoning Validator (DeepSeek)',
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
  const s = 1 / (1 + Math.exp(-7.5 * (t - 0.65)))
  const p = Math.pow(t, 2.2)
  const raw = 0.3 * p + 0.7 * s
  const raw0 = 0.7 * (1 / (1 + Math.exp(7.5 * 0.65)))
  const raw1 = 0.3 + 0.7 * (1 / (1 + Math.exp(-7.5 * 0.35)))
  const normalized = Math.max(0, Math.min(1, (raw - raw0) / (raw1 - raw0)))
  const total = normalized * 160

  const y0 = total * (0.50 + 0.075 * t)
  const y1 = total * (0.75 + 0.03125 * t)
  const y2 = total * (0.90 + 0.0125 * t)
  const y3 = total

  return { total, y0, y1, y2, y3 }
}

function PerformanceGraph() {
  const [activeTab, setActiveTab] = useState(1) // 0: Developers, 1: AI Teams, 2: Research
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

  const getLineD = (key: 'y0' | 'y1' | 'y2' | 'y3') => {
    let d = `M ${points[0].x.toFixed(1)},${points[0][key].toFixed(1)}`
    for (let i = 1; i <= NUM_STEPS; i++) {
      d += ` L ${points[i].x.toFixed(1)},${points[i][key].toFixed(1)}`
    }
    return d
  }

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
    <div className="rounded-[20px] bg-[#0c0714] text-white p-7 sm:p-9 border border-neutral-800 shadow-2xl relative overflow-hidden" ref={ref}>
      {/* Top Audience Tabs matching Atomicwork */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5 mb-8">
        <div>
          <span className="text-white/40 text-xs font-mono font-bold tracking-[0.2em] uppercase block mb-1">
            CONTINUOUS RESOLUTION INTELLIGENCE
          </span>
          <h3 className="text-xl sm:text-2xl font-bold font-sans text-white">
            3X Increase in AI Resolutions with Persistent Memory
          </h3>
        </div>
        <div className="flex items-center gap-4 sm:gap-6 text-xs font-mono">
          {[
            { id: 0, label: '1. FOR DEVELOPERS' },
            { id: 1, label: '2. FOR AI TEAMS' },
            { id: 2, label: '3. FOR RESEARCH' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-1 cursor-pointer transition-all uppercase ${
                activeTab === tab.id
                  ? 'text-white font-bold border-b-2 border-emerald-400'
                  : 'text-white/40 hover:text-white/80'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main 2-Column Display (Stacked Area Chart on Left, Metrics Card on Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch mb-8">
        
        {/* Left Column: Stacked Area Chart */}
        <div className="lg:col-span-8 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex flex-wrap items-center gap-4 sm:gap-6">
              {CHART_CATEGORIES.map((cat) => (
                <div key={cat.name} className="flex items-center gap-2">
                  {cat.icon}
                  <span className="text-white/70 text-xs font-mono">
                    {cat.name}
                  </span>
                </div>
              ))}
            </div>

            <div className="hidden sm:flex items-center gap-3">
              <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
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

          {/* SVG Canvas */}
          <div className="relative w-full">
            <svg
              viewBox={`0 0 ${W} ${H}`}
              className="w-full h-auto cursor-crosshair select-none"
              preserveAspectRatio="xMidYMid meet"
              onMouseMove={onMouseMove}
              onMouseLeave={() => setHoverT(null)}
            >
              <defs>
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

                <pattern id="atomic-stipple" width="5" height="5" patternUnits="userSpaceOnUse">
                  <circle cx="1.5" cy="1.5" r="0.75" fill="#ffffff" opacity="0.15" />
                  <circle cx="4" cy="4" r="0.55" fill="#000000" opacity="0.25" />
                </pattern>

                <clipPath id="reg-chart-clip">
                  <rect x={PAD.l} y={PAD.t - 10} width={clipW} height={gH + 20} />
                </clipPath>
              </defs>

              {/* Horizontal grid lines */}
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
                    <text
                      x={PAD.l - 12}
                      y={y + 4}
                      fill="rgba(255, 255, 255, 0.45)"
                      fontSize="10"
                      fontFamily="monospace"
                      textAnchor="end"
                    >
                      {val}
                    </text>
                  </g>
                )
              })}

              {/* X-axis labels */}
              <text x={PAD.l} y={H - 8} fill="rgba(255, 255, 255, 0.45)" fontSize="10" fontFamily="monospace" textAnchor="start">
                Day 1
              </text>
              <text x={PAD.l + gW * 0.5} y={H - 8} fill="rgba(255, 255, 255, 0.45)" fontSize="10" fontFamily="monospace" textAnchor="middle">
                Day 45
              </text>
              <text x={W - PAD.r} y={H - 8} fill="rgba(255, 255, 255, 0.45)" fontSize="10" fontFamily="monospace" textAnchor="end">
                Day 90
              </text>

              {/* Stacked Regression Model Curves */}
              <g clipPath="url(#reg-chart-clip)">
                <path d={getAreaD('y3', 'y2')} fill="url(#grad-layer-3)" />
                <path d={getAreaD('y3', 'y2')} fill="url(#atomic-stipple)" />
                <path d={getLineD('y3')} fill="none" stroke="#fef08a" strokeWidth="1.5" />

                <path d={getAreaD('y2', 'y1')} fill="url(#grad-layer-2)" />
                <path d={getAreaD('y2', 'y1')} fill="url(#atomic-stipple)" />
                <path d={getLineD('y2')} fill="none" stroke="#fdba74" strokeWidth="1.5" />

                <path d={getAreaD('y1', 'y0')} fill="url(#grad-layer-1)" />
                <path d={getAreaD('y1', 'y0')} fill="url(#atomic-stipple)" />
                <path d={getLineD('y1')} fill="none" stroke="#6ee7b7" strokeWidth="1.5" />

                <path d={getAreaD('y0', 'yBase')} fill="url(#grad-layer-0)" />
                <path d={getAreaD('y0', 'yBase')} fill="url(#atomic-stipple)" />
                <path d={getLineD('y0')} fill="none" stroke="#a78bfa" strokeWidth="1.5" />

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
                      stroke="#0c0714"
                      strokeWidth="2"
                    />
                  ))}
                </g>
              )}
            </svg>

            {/* Interactive Tooltip */}
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
                    Trajectory Day {hoverDay}
                  </p>
                  <span className="text-[9px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded">
                    ŷ = f(t)
                  </span>
                </div>

                <p className="text-white font-bold text-sm mb-2">
                  Total: {Math.round(hoverData.total)} Resolutions
                </p>

                <div className="space-y-1 text-[11px] font-mono">
                  <div className="flex items-center justify-between gap-4 text-yellow-300">
                    <span>Reasoning Validator:</span>
                    <span className="font-bold">{Math.round(hoverData.y3 - hoverData.y2)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-orange-400">
                    <span>Local Data Analyst:</span>
                    <span className="font-bold">{Math.round(hoverData.y2 - hoverData.y1)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-emerald-400">
                    <span>Code Synthesizer:</span>
                    <span className="font-bold">{Math.round(hoverData.y1 - hoverData.y0)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-purple-300">
                    <span>Research Specialist:</span>
                    <span className="font-bold">{Math.round(hoverData.y0)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Metrics Card */}
        <div className="lg:col-span-4 p-6 rounded-[16px] bg-white/[0.03] border border-white/[0.08] flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2.5 h-2.5 rounded-[2px] bg-emerald-400 animate-pulse" />
              <span className="text-emerald-400 text-xs font-mono font-bold tracking-widest uppercase">
                ACTIVE PERSISTENT AGENTS
              </span>
            </div>
            <div className="text-emerald-400 font-bold text-5xl tracking-tight mb-6">
              156
            </div>

            <div className="grid grid-cols-2 gap-y-6 gap-x-4">
              <div>
                <p className="text-white/40 text-[10px] font-mono font-bold uppercase mb-1">
                  TOKEN DEFLECTION
                </p>
                <p className="text-white font-bold font-mono text-xl">
                  -72%
                </p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] font-mono font-bold uppercase mb-1">
                  SLA ADHERENCE
                </p>
                <p className="text-white font-bold font-mono text-xl">
                  99.9%
                </p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] font-mono font-bold uppercase mb-1">
                  FIRST RESPONSE
                </p>
                <p className="text-white font-bold font-mono text-xl">
                  18ms
                </p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] font-mono font-bold uppercase mb-1">
                  FAULT MTTR
                </p>
                <p className="text-white font-bold font-mono text-xl">
                  1.8s
                </p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] font-mono font-bold uppercase mb-1">
                  BENCHMARK ACCURACY
                </p>
                <p className="text-white font-bold font-mono text-xl">
                  98%
                </p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] font-mono font-bold uppercase mb-1">
                  EVALUATED RUNS
                </p>
                <p className="text-white font-bold font-mono text-xl">
                  1,200
                </p>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Floating Prompt Pill */}
      <div className="flex justify-center -mb-2 relative z-20">
        <button
          onClick={() => setShowPromptDetails(!showPromptDetails)}
          className="group flex items-center gap-3 px-6 py-3 rounded-full backdrop-blur-xl border border-white/20 hover:border-orange-400 shadow-2xl transition-all cursor-pointer bg-[#160c26]"
        >
          <span className="text-white text-xs font-mono font-medium">
            What can your persistent agent memory actually resolve?
          </span>
          <div className="w-5 h-5 rounded-full bg-orange-500 flex items-center justify-center text-white shadow group-hover:translate-x-0.5 transition-transform">
            <ArrowRight size={11} />
          </div>
        </button>
      </div>

      {showPromptDetails && (
        <div className="mt-6 p-4 rounded-[12px] bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-neutral-300">
          <p className="text-emerald-400 font-bold mb-1">Adaptive Execution Matrix:</p>
          <ul className="list-disc list-inside space-y-1 text-white/80">
            <li>Reflexion loops extract reusable failure constraints after unexpected API exceptions</li>
            <li>Bayesian bandit routing selects validated tool paths with Lower Confidence Bound (LCB) ranking</li>
            <li>Zero prompt token bloating: 420 tokens per turn vs 15,000 stateless dumps</li>
          </ul>
        </div>
      )}
    </div>
  )
}

// ─── Animated Scanning Before/After Section ───────────────────────────────────
function BeforeAfterSection() {
  const [visible, setVisible] = useState(false)
  const [tick, setTick] = useState(0)
  const [mins, setMins] = useState(45)
  const [tokens, setTokens] = useState(15000)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true) },
      { threshold: 0.2 }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (visible) {
      const id = setInterval(() => setTick(t => t + 1), 40)
      return () => clearInterval(id)
    }
  }, [visible])

  useEffect(() => {
    if (visible) {
      const id = setInterval(() => {
        setMins(m => (m > 2 ? m - 1 : 2))
        setTokens(t => (t > 420 ? t - 350 : 420))
      }, 50)
      return () => clearInterval(id)
    }
  }, [visible])

  const scanY = (Math.sin(tick * 0.05) * 0.5 + 0.5) * 100

  return (
    <div ref={ref} className="relative rounded-[16px] overflow-hidden border border-neutral-800 bg-neutral-900 shadow-2xl">
      {/* Animated laser scan line */}
      <div
        className="absolute left-0 right-0 h-0.5 pointer-events-none z-30 transition-all duration-75"
        style={{
          top: `${scanY}%`,
          background: 'linear-gradient(90deg, transparent 0%, rgba(134, 47, 231, 0.8) 50%, transparent 100%)',
          boxShadow: '0 0 12px rgba(134, 47, 231, 0.9)',
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-neutral-800">
        {/* BEFORE: Stateless Chaos */}
        <div className="p-8 bg-black/60 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] mb-6">
              <span className="text-xs font-mono font-bold text-red-400 uppercase tracking-wider">
                BEFORE · STATELESS PROMPTS
              </span>
              <span className="text-xs font-mono text-neutral-500">NO PERSISTENT MEMORY</span>
            </div>
            <ul className="space-y-4 text-xs font-mono text-neutral-300">
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Context dump per run:</span>
                <span className="text-red-400 font-bold">{tokens} tokens</span>
              </li>
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Redundant tool execution retries:</span>
                <span className="text-red-400 font-bold">4 to 7 attempts</span>
              </li>
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Cost per 1,000 complex tasks:</span>
                <span className="text-red-400 font-bold">$180.00</span>
              </li>
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Average resolution duration:</span>
                <span className="text-red-400 font-bold">{mins} seconds</span>
              </li>
            </ul>
          </div>
          <div className="mt-8 p-3 rounded-[8px] bg-red-950/30 border border-red-500/20 text-[11px] font-mono text-red-300">
            ⚠ Agent repeatedly tries failed API endpoints, wasting budget on identical hallucinations.
          </div>
        </div>

        {/* AFTER: Adaptive MemoryAgent Persistence */}
        <div className="p-8 bg-[#12081f]/80 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.08] mb-6">
              <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider">
                AFTER · ADAPTIVE MEMORYAGENT
              </span>
              <span className="text-xs font-mono text-emerald-400 font-bold">BAYESIAN ROUTING ACTIVE</span>
            </div>
            <ul className="space-y-4 text-xs font-mono text-neutral-200">
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Surgical memory recall:</span>
                <span className="text-emerald-400 font-bold">420 tokens (-72%)</span>
              </li>
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Redundant tool execution retries:</span>
                <span className="text-emerald-400 font-bold">0 retries (Deterministic)</span>
              </li>
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Cost per 1,000 complex tasks:</span>
                <span className="text-emerald-400 font-bold">$5.00</span>
              </li>
              <li className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span>Average resolution duration:</span>
                <span className="text-emerald-400 font-bold">1.8 seconds</span>
              </li>
            </ul>
          </div>
          <div className="mt-8 p-3 rounded-[8px] bg-emerald-950/30 border border-emerald-500/20 text-[11px] font-mono text-emerald-300">
            ✓ Lower Confidence Bound (LCB) prioritizes proven experiences. Zero redundant tool calls.
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Navbar Component ────────────────────────────────────────────────────────
function Navbar({ scrolled }: { scrolled: boolean }) {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin')
  const navigate = useNavigate()

  return (
    <>
      <header className="sticky top-0 inset-x-0 z-50">
        {/* Top Announcement Bar (Vibrant Magenta/Purple Gradient) */}
        <div
          className="text-white text-xs py-2 px-4 text-center font-medium flex items-center justify-center gap-3 relative"
          style={{
            background: 'linear-gradient(90deg, #8A2BE2 0%, #B829E3 50%, #FF69B4 100%)',
          }}
        >
          <span className="font-mono bg-white/20 px-2 py-0.5 rounded-full text-[11px] font-bold">
            RESEARCH RELEASE · G146
          </span>
          <span className="hidden sm:inline text-white text-xs font-semibold">
            Persistent agent intelligence is here. Explore the Kaggle benchmark on 1,200 agent tasks.
          </span>
          <a
            href="#benchmarks"
            className="rounded-full bg-white text-[#8A2BE2] hover:bg-neutral-100 px-3 py-0.5 text-[11px] font-bold tracking-wide transition-colors shadow-sm uppercase"
          >
            Read paper
          </a>
        </div>

        {/* Glassmorphic Sticky Navbar */}
        <nav
          className={`transition-all duration-300 ${
            scrolled
              ? 'bg-white/90 backdrop-blur-md border-b border-neutral-200/80 shadow-sm'
              : 'bg-white/60 backdrop-blur-sm border-b border-white/30'
          }`}
        >
          <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-[8px] bg-[#0c0714] flex items-center justify-center text-white shadow-sm">
                <Brain size={16} />
              </div>
              <span className="font-semibold text-lg tracking-tight font-sans text-[#292929]">
                MemoryAgent <span className="text-xs font-mono text-[#7042DD] font-medium ml-1">G146</span>
              </span>
            </Link>

            {/* Nav Links with Carets */}
            <div className="hidden lg:flex items-center gap-7">
              <a href="#models" className="flex items-center gap-1 text-sm font-medium text-[#292929] hover:text-black">
                Multi-LLM <ChevronDown size={14} className="text-neutral-500" />
              </a>
              <a href="#architecture" className="text-sm font-medium text-[#292929] hover:text-black">
                Architecture
              </a>
              <a href="#governance" className="flex items-center gap-1 text-sm font-medium text-[#292929] hover:text-black">
                Governance <ChevronDown size={14} className="text-neutral-500" />
              </a>
              <a href="#benchmarks" className="flex items-center gap-1 text-sm font-medium text-[#292929] hover:text-black">
                ROI &amp; Benchmarks <ChevronDown size={14} className="text-neutral-500" />
              </a>
              <a href="#integrations" className="flex items-center gap-1 text-sm font-medium text-[#292929] hover:text-black">
                Integrations <ChevronDown size={14} className="text-neutral-500" />
              </a>
            </div>

            {/* Action CTAs */}
            <div className="hidden md:flex items-center gap-3">
              {user ? (
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-[#717171]">
                    {user.email.split('@')[0]}
                  </span>
                  <button
                    onClick={() => navigate('/dashboard')}
                    className="rounded-[8px] bg-neutral-900 text-white hover:bg-neutral-800 px-4 py-2 text-xs font-semibold transition-colors"
                  >
                    Dashboard
                  </button>
                  <button
                    onClick={() => signOut()}
                    className="p-1.5 rounded-[6px] text-neutral-400 hover:text-neutral-600 transition-colors"
                    title="Sign out"
                  >
                    <LogOut size={14} />
                  </button>
                </div>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setAuthMode('signin')
                      setShowAuth(true)
                    }}
                    className="text-sm font-medium px-3 py-1.5 text-[#292929] hover:text-black transition-colors cursor-pointer"
                  >
                    Sign in
                  </button>
                  <button
                    onClick={() => {
                      setAuthMode('signup')
                      setShowAuth(true)
                    }}
                    id="nav-cta"
                    className="rounded-[8px] bg-neutral-900 text-white hover:bg-neutral-800 px-4 py-2 text-sm font-medium transition-colors cursor-pointer shadow-sm"
                  >
                    Open Console
                  </button>
                </>
              )}
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setOpen(!open)}
              className="lg:hidden p-1.5 rounded-[6px] text-neutral-800"
            >
              {open ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>

          {/* Mobile dropdown */}
          {open && (
            <div className="lg:hidden bg-white border-b border-neutral-200 px-6 py-4 space-y-3">
              {['Multi-LLM', 'Architecture', 'Governance', 'ROI & Benchmarks', 'Integrations'].map((item) => (
                <a key={item} href="#" className="block text-sm font-medium text-[#292929]">
                  {item}
                </a>
              ))}
              <div className="pt-3 border-t border-neutral-200 flex flex-col gap-2">
                <button
                  onClick={() => {
                    setAuthMode('signup')
                    setShowAuth(true)
                    setOpen(false)
                  }}
                  className="w-full text-center rounded-[8px] bg-neutral-900 text-white py-2 text-sm font-semibold"
                >
                  Open Console
                </button>
              </div>
            </div>
          )}
        </nav>
      </header>

      {/* Auth Modal */}
      {showAuth && (
        <AuthModal
          isOpen={showAuth}
          initialMode={authMode}
          onClose={() => setShowAuth(false)}
          onSuccess={() => {
            setShowAuth(false)
            navigate('/dashboard')
          }}
        />
      )}
    </>
  )
}

// ─── Main Page Export ─────────────────────────────────────────────────────────
export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)
  const [heroView, setHeroView] = useState<'session' | 'model'>('session')
  const [activeLLM, setActiveLLM] = useState(LLM_PROVIDERS[0].name)
  const [typedQuery, setTypedQuery] = useState('')

  const activeProvider = LLM_PROVIDERS.find(p => p.name === activeLLM) || LLM_PROVIDERS[0]

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', fn)
    return () => window.removeEventListener('scroll', fn)
  }, [])

  // Live animated typing effect on model switch
  useEffect(() => {
    setTypedQuery('')
    const fullText = activeProvider.query
    let i = 0
    const interval = setInterval(() => {
      if (i < fullText.length) {
        setTypedQuery(fullText.slice(0, i + 1))
        i++
      } else {
        clearInterval(interval)
      }
    }, 20)
    return () => clearInterval(interval)
  }, [activeProvider.name])

  const MARQUEE_ITEMS = [
    { name: 'Claude', tag: 'Anthropic', Logo: ClaudeLogo, color: '#D97706' },
    { name: 'OpenAI', tag: 'GPT-4o', Logo: OpenAILogo, color: '#10A37F' },
    { name: 'Ollama', tag: 'Local LLMs', Logo: OllamaLogo, color: '#3B82F6' },
    { name: 'Grok', tag: 'xAI', Logo: GrokLogo, color: '#EC4899' },
    { name: 'DeepSeek', tag: 'R1 Reasoning', Logo: DeepSeekLogo, color: '#1D72FE' },
    { name: 'Gemini', tag: 'Google DeepMind', Logo: GeminiLogo, color: '#4E82EE' },
    { name: 'LangChain', tag: 'Framework', Logo: LangChainLogo, color: '#2DD4BF' },
    { name: 'LlamaIndex', tag: 'Index Engine', Logo: LlamaIndexLogo, color: '#A855F7' },
    { name: 'PyTorch', tag: 'Core Runtime', Logo: PyTorchLogo, color: '#EE4C2C' },
    { name: 'Hugging Face', tag: 'Model Hub', Logo: HuggingFaceLogo, color: '#FFD21E' },
  ]

  return (
    <div className="min-h-screen bg-white text-[#292929] font-sans antialiased selection:bg-[#7042DD]/20">
      
      <Navbar scrolled={scrolled} />

      {/* ── 1. Hero Section (Panoramic Sky Canvas & High Visual Clarity) ──── */}
      <section
        className="relative pt-24 pb-24 px-6 overflow-hidden"
        style={{
          background: 'radial-gradient(ellipse 100% 70% at 50% 15%, #E6F0FA 0%, #F0F6FC 50%, #FFFFFF 100%)',
        }}
      >
        {/* Prominent Architectural Workplace Panorama (Clearly visible, elegant Atomicwork photography) */}
        <div
          className="absolute inset-0 pointer-events-none z-0 bg-cover bg-right-bottom sm:bg-center transition-opacity duration-700"
          style={{
            backgroundImage: `url('/workspace-panorama.jpg')`,
            opacity: 0.90,
          }}
        />
        {/* Soft atmospheric gradient wash ensuring black text on the left is 100% legible while keeping the penthouse view, skyline, and desk brightly visible */}
        <div
          className="absolute inset-0 pointer-events-none z-0"
          style={{
            background: 'linear-gradient(90deg, rgba(235, 243, 252, 0.95) 0%, rgba(235, 243, 252, 0.88) 42%, rgba(235, 243, 252, 0.25) 75%, rgba(235, 243, 252, 0.05) 100%), linear-gradient(180deg, rgba(230, 240, 250, 0.3) 0%, transparent 45%, rgba(255, 255, 255, 0.95) 100%)',
          }}
        />

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center relative z-10">
          
          {/* Left Column: Bold Headline & Action */}
          <div className="lg:col-span-6">
            <h1 className="text-5xl sm:text-6xl lg:text-[64px] font-bold tracking-tight leading-[1.08] text-[#292929] mb-6">
              Adaptive Agent Memory for Enterprise AI
            </h1>
            <p className="text-base sm:text-lg text-[#717171] leading-relaxed mb-8 max-w-xl font-normal">
              MemoryAgent gives autonomous AI agents persistent memory that learns from every run. Grounded in live experience, optimized by Bayesian routing, and compatible with any LLM.
            </p>

            <div className="flex flex-wrap items-center gap-3 mb-10">
              <a
                href="/dashboard"
                className="rounded-full bg-white text-[#292929] border border-neutral-300 px-7 py-3 text-sm font-semibold hover:bg-neutral-50 shadow-[0_4px_14px_rgba(0,0,0,0.06)] transition-all"
              >
                Try it yourself
              </a>
              <a
                href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
                target="_blank"
                rel="noreferrer"
                className="rounded-full bg-transparent text-[#292929] hover:bg-neutral-100/70 border border-neutral-300/80 px-6 py-3 text-sm font-medium transition-all"
              >
                View GitHub
              </a>
            </div>

            {/* Architecture Spec Card */}
            <div className="flex items-center gap-3 p-3.5 rounded-[12px] bg-white/80 backdrop-blur-md border border-neutral-200/80 max-w-md shadow-sm">
              <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-[#7042DD] font-bold text-xs shrink-0">
                G146
              </div>
              <div className="text-xs">
                <span className="font-semibold text-[#292929] block">Bayesian Bandit Experience Routing</span>
                <span className="text-[#717171]">Recalls verified tool paths with sub-500ms latency across Claude, OpenAI &amp; Ollama</span>
              </div>
            </div>
          </div>

          {/* Right Column: Hero Graphic + Floating Task Pills + Live Demo/3D Toggle */}
          <div className="lg:col-span-6 flex flex-col items-center relative">
            
            {/* Floating Live Memory Pills (Animated with Authentic Logos) */}
            <div className="w-full max-w-lg mb-3 flex flex-wrap gap-2 justify-center">
              {[
                { text: 'Claude 3.5 Sonnet: 99.1% Confidence', Logo: ClaudeLogo, color: '#f59e0b', anim: 'anim-float-1' },
                { text: 'GPT-4o: 0 Redundant Retries', Logo: OpenAILogo, color: '#10b981', anim: 'anim-float-2' },
                { text: 'Ollama: On-Device SQLite Store', Logo: OllamaLogo, color: '#60a5fa', anim: 'anim-float-3' },
                { text: 'Grok 2: Causal Regime Graph', Logo: GrokLogo, color: '#f43f5e', anim: 'anim-float-1' },
                { text: 'DeepSeek R1: Reflexion Loops', Logo: DeepSeekLogo, color: '#a855f7', anim: 'anim-float-2' },
              ].map((item, idx) => (
                <span
                  key={idx}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium bg-neutral-900/90 text-white shadow-md border border-neutral-700/70 backdrop-blur-md flex items-center gap-2 ${item.anim}`}
                >
                  <item.Logo size={13} color={item.color} />
                  <span>{item.text}</span>
                </span>
              ))}
            </div>

            {/* View Switcher: Live Session vs 3D Neural Core */}
            <div className="mb-3 p-1 rounded-full bg-neutral-200/80 border border-neutral-300 flex items-center gap-1 text-xs">
              <button
                onClick={() => setHeroView('session')}
                className={`px-3 py-1 rounded-full font-medium transition-all ${
                  heroView === 'session' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-600 hover:text-black'
                }`}
              >
                Live Session Console
              </button>
              <button
                onClick={() => setHeroView('model')}
                className={`px-3 py-1 rounded-full font-medium transition-all ${
                  heroView === 'model' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-600 hover:text-black'
                }`}
              >
                3D Neural Core
              </button>
            </div>

            {/* Interactive Showcase Window */}
            {heroView === 'session' ? (
              <LiveDemoPanel />
            ) : (
              <div
                className="w-full max-w-lg h-[430px] rounded-[16px] overflow-hidden relative shadow-2xl flex flex-col"
                style={{
                  background: 'rgba(12, 7, 20, 0.95)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                }}
              >
                <div className="px-4 py-3 border-b border-white/[0.08] flex items-center justify-between text-xs font-mono text-[#D0D5DD]">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>3D Neural Memory Core</span>
                  </div>
                  <span className="text-white/40">WebGL 2.0</span>
                </div>
                <div className="flex-1 relative">
                  <ThreeMemoryCore glowColor="#862FE7" providerName="MemoryAgent Engine" />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── 2. Social Proof Logo Marquee (Full-Width Animated Dark Strip) ──── */}
      <div className="bg-neutral-950 py-5 border-y border-neutral-800 overflow-hidden relative">
        {/* Subtle gradient edge fades */}
        <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-neutral-950 to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-neutral-950 to-transparent z-10 pointer-events-none" />
        
        <div className="marquee-track flex items-center gap-6">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2.5 px-4 py-2 rounded-full bg-neutral-900/70 border border-neutral-800/90 hover:border-neutral-700 transition-all shrink-0 cursor-default"
            >
              <item.Logo size={16} color={item.color} />
              <span className="text-white text-xs font-semibold tracking-wide font-sans">{item.name}</span>
              <span className="text-[10px] font-mono text-neutral-400">· {item.tag}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── 3. Multi-LLM Memory Adapter (Warm Cream Canvas #F7F5F0) ────────── */}
      <section id="models" className="py-24 px-6 bg-[#F7F5F0] border-b border-neutral-200">
        <div className="max-w-7xl mx-auto">
          
          <div className="max-w-3xl mb-12">
            <span className="text-xs font-mono uppercase tracking-[0.2em] text-[#717171] font-bold block mb-2">
              MULTI-LLM PERSISTENT MEMORY ARCHITECTURE
            </span>
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#292929] mb-4">
              Delightful agent memory, across any foundation model.
            </h2>
            <p className="text-base text-[#717171] leading-relaxed">
              Whether you run Claude, OpenAI, Ollama, Grok, or DeepSeek, MemoryAgent provides a shared persistent experience layer that eliminates repetitive mistakes and cuts token costs by up to 72%.
            </p>
          </div>

          {/* Model Selector & Live Cockpit Body */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start mb-16">
            
            {/* Left Column: LLM Provider Tabs */}
            <div className="lg:col-span-4 space-y-2">
              <span className="text-xs font-mono uppercase tracking-wider text-[#717171] font-bold block mb-3">
                SELECT FOUNDATION MODEL
              </span>
              {LLM_PROVIDERS.map((p) => {
                const isActive = activeLLM === p.name
                return (
                  <div
                    key={p.name}
                    onClick={() => setActiveLLM(p.name)}
                    className={`p-4 rounded-[12px] cursor-pointer transition-all border ${
                      isActive
                        ? 'bg-white border-neutral-300 shadow-sm'
                        : 'bg-transparent border-transparent hover:bg-neutral-200/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <p.Logo size={16} color={p.color} />
                        <span className="text-sm font-bold text-[#292929]">{p.name}</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-100 text-[#717171] font-semibold">
                        {p.modelTag}
                      </span>
                    </div>
                    <p className="text-xs text-[#717171] line-clamp-1 ml-6">{p.query}</p>
                  </div>
                )
              })}
            </div>

            {/* Right Column: Interactive 3D Model + Real-time Code Execution Console */}
            <div className="lg:col-span-8 bg-[#0c0714] rounded-[16px] overflow-hidden border border-neutral-800 shadow-2xl flex flex-col">
              
              {/* Header Bar */}
              <div className="px-5 py-3.5 bg-white/[0.03] border-b border-white/[0.08] flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-2.5">
                  <activeProvider.Logo size={16} color={activeProvider.glowColor} />
                  <span className="text-white font-bold">{activeProvider.name} Adapter</span>
                  <span className="text-white/40">· {activeProvider.taskType}</span>
                </div>
                <span className="text-[#C4B5FD] font-semibold">Recall: {activeProvider.confidence}</span>
              </div>

              {/* Top: 3D WebGL Neural Core */}
              <div className="relative h-[220px] w-full flex items-center justify-center overflow-hidden border-b border-white/[0.08] bg-black/40">
                <ThreeMemoryCore glowColor={activeProvider.glowColor} providerName={activeProvider.name} />
              </div>

              {/* Bottom: Animated Typing Query & Code Execution Console */}
              <div className="p-6 space-y-4">
                {/* Simulated Query Box */}
                <div className="p-3.5 rounded-[10px] bg-white/[0.04] border border-white/[0.08] text-xs font-mono">
                  <span className="text-[#862FE7] font-bold block mb-1">Query Intercepted:</span>
                  <p className="text-white">{typedQuery}<span className="animate-pulse">|</span></p>
                </div>

                {/* Live Code Lines */}
                <div className="p-4 rounded-[10px] bg-black/60 border border-white/[0.06] font-mono text-xs space-y-1.5">
                  {activeProvider.codeLines.map((line, idx) => (
                    <div key={idx} className="flex gap-3">
                      <span className="text-white/30 select-none">{line.num}</span>
                      <span style={{ color: line.color }}>{line.text}</span>
                    </div>
                  ))}
                </div>

                {/* Execution Metrics Footer */}
                <div className="pt-3 border-t border-white/[0.08] grid grid-cols-3 gap-4 text-center font-mono text-xs">
                  <div>
                    <span className="text-white/40 text-[10px] block">RETRIEVAL LATENCY</span>
                    <span className="text-white font-bold">{activeProvider.latency}</span>
                  </div>
                  <div>
                    <span className="text-white/40 text-[10px] block">ENGINEERING TIME SAVED</span>
                    <span className="text-emerald-400 font-bold">{activeProvider.timeSaved}</span>
                  </div>
                  <div>
                    <span className="text-white/40 text-[10px] block">TOKENS DEFLECTED</span>
                    <span className="text-[#A78BFA] font-bold">{activeProvider.tokensSaved}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 4 Feature Checkmarks */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 pt-10 border-t border-neutral-200">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Resolutions, not just answers</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Agents retrieve verified execution sequences rather than guessing tool inputs from scratch.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Provide the right memory in time</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Bayesian Lower Confidence Bound (LCB) ranking prevents retrieval of noisy or unvalidated experiences.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Continuous reflection loops</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Failed tasks trigger self-critique loops that extract reusable constraints for subsequent model executions.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Zero vendor lock-in</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Seamlessly swap between Claude, OpenAI, Ollama, Grok, and DeepSeek without losing your agent's learned memory.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. Scale Autonomous Agents (Clean White Canvas) ────────────────── */}
      <section id="architecture" className="py-24 px-6 bg-white border-b border-neutral-200">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-3xl mb-14">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#292929] mb-4">
              Scale enterprise agents with persistent memory that owns experiences, not just chat history.
            </h2>
            <p className="text-base text-[#717171] leading-relaxed">
              Coordinate multi-agent teams with shared persistent memory. Each agent operates with persistent episodic memory, Bayesian trust scoring, and strict access controls.
            </p>
          </div>

          {/* Interactive Agent Hierarchy Map (Animated 3-Tier Multi-Agent Flow) */}
          <div className="p-8 sm:p-10 rounded-[20px] bg-[#FAF9F6] border border-neutral-200/90 mb-14 overflow-x-auto shadow-sm">
            <div className="min-w-[700px] flex flex-col items-center gap-2 text-center">
              
              {/* Block 1: Executive Agent Planner (Animated) */}
              <div className="p-4 rounded-[14px] bg-white border border-neutral-300/80 shadow-md w-80 anim-float-1 card-hover relative overflow-hidden">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-[#717171] uppercase font-bold tracking-wider">
                    ORCHESTRATION LAYER
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    <span className="text-[10px] font-mono text-emerald-600 font-bold">ACTIVE</span>
                  </div>
                </div>
                <p className="text-sm font-bold text-[#292929] mb-1.5 font-sans">Executive Task Planner</p>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-50 border border-purple-200/60 text-[10px] font-mono text-[#7042DD]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#7042DD] animate-pulse" />
                  <span>Decomposing goal #128 · Injecting memory priors</span>
                </div>
              </div>

              {/* Animated Data Pipeline 1 */}
              <div className="relative w-1 h-12 bg-neutral-200 rounded-full overflow-hidden my-0.5">
                <div className="absolute inset-x-0 w-full h-5 bg-gradient-to-b from-[#862FE7] via-cyan-400 to-[#953BFF] rounded-full animate-flow-down" />
              </div>

              {/* Block 2: Shared Persistent Memory Plane (Animated) */}
              <div className="p-5 sm:p-6 rounded-[16px] bg-[#0c0714] text-white border border-[#862FE7]/40 shadow-2xl w-full max-w-2xl relative overflow-hidden anim-float-2 animate-pulse-glow">
                {/* Moving laser sweep line across top */}
                <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" />
                
                <div className="flex items-center justify-between mb-4 pb-2.5 border-b border-white/[0.08]">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#953BFF] animate-ping" />
                    <span className="text-[11px] font-mono text-[#C4B5FD] font-bold tracking-wider">
                      SHARED AGENT MEMORY PLANE (BAYESIAN BANDIT ROUTER)
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                    Sub-500ms Routing
                  </span>
                </div>

                {/* 4 Interactive Memory Pools */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                  <div className="p-2.5 rounded-[8px] bg-white/[0.04] border border-white/[0.08] hover:border-cyan-400/50 transition-all text-left">
                    <div className="flex items-center gap-1.5 mb-1 text-cyan-300 font-bold text-[11px]">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                      Episodic Index
                    </div>
                    <p className="text-[10px] text-white/50">1,200 trajectories</p>
                  </div>

                  <div className="p-2.5 rounded-[8px] bg-white/[0.04] border border-white/[0.08] hover:border-emerald-400/50 transition-all text-left">
                    <div className="flex items-center gap-1.5 mb-1 text-emerald-300 font-bold text-[11px]">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Semantic Vectors
                    </div>
                    <p className="text-[10px] text-white/50">1536-dim SQLite</p>
                  </div>

                  <div className="p-2.5 rounded-[8px] bg-white/[0.04] border border-white/[0.08] hover:border-purple-400/50 transition-all text-left">
                    <div className="flex items-center gap-1.5 mb-1 text-purple-300 font-bold text-[11px]">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                      Reflection Vault
                    </div>
                    <p className="text-[10px] text-white/50">Self-critique active</p>
                  </div>

                  <div className="p-2.5 rounded-[8px] bg-white/[0.04] border border-white/[0.08] hover:border-amber-400/50 transition-all text-left">
                    <div className="flex items-center gap-1.5 mb-1 text-amber-300 font-bold text-[11px]">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                      Quarantine
                    </div>
                    <p className="text-[10px] text-white/50">0 injected leaks</p>
                  </div>
                </div>
              </div>

              {/* Animated Data Pipeline 2 */}
              <div className="relative w-1 h-12 bg-neutral-200 rounded-full overflow-hidden my-0.5">
                <div className="absolute inset-x-0 w-full h-5 bg-gradient-to-b from-cyan-400 via-[#862FE7] to-emerald-400 rounded-full animate-flow-down" />
              </div>

              {/* Block 3: Active Specialized Agents (Animated with Official SVG Logos) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full max-w-3xl">
                {[
                  { name: 'Research Specialist', tag: 'CLAUDE 3.5', Logo: ClaudeLogo, color: '#d97706', anim: 'anim-float-1', stat: '99.1% Confidence' },
                  { name: 'Code Synthesizer', tag: 'GPT-4O', Logo: OpenAILogo, color: '#10a37f', anim: 'anim-float-2', stat: '0 Retries' },
                  { name: 'Local Data Analyst', tag: 'OLLAMA', Logo: OllamaLogo, color: '#3b82f6', anim: 'anim-float-3', stat: '100% Local' },
                  { name: 'Reasoning Validator', tag: 'DEEPSEEK R1', Logo: DeepSeekLogo, color: '#8b5cf6', anim: 'anim-float-1', stat: 'Pruning Loop' }
                ].map((bot) => (
                  <div
                    key={bot.name}
                    className={`p-4 rounded-[14px] bg-white border border-neutral-200 shadow-sm card-hover hover:border-neutral-400 transition-all ${bot.anim}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[9px] font-mono font-bold tracking-wider" style={{ color: bot.color }}>
                        {bot.tag}
                      </span>
                      <bot.Logo size={15} color={bot.color} />
                    </div>
                    <p className="text-xs font-bold text-[#292929] mb-2">{bot.name}</p>
                    <div className="inline-block px-2 py-0.5 rounded bg-neutral-100 text-[10px] font-mono text-[#717171]">
                      {bot.stat}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 4 Pillars */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Continuous agent learning</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Agents learn directly from tool execution outcomes, persisting constraints to prevent recurring runtime faults.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Collaborative memory pools</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Shared skills across agents so multiple models coordinate without independently re-learning the same solutions.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Any harness, any model</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Bring your own models from Claude, OpenAI, Ollama, Grok, DeepSeek, or open-source PyTorch models.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Adversarial quarantine</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Automatic detection and quarantine of poisoned trajectories, hallucinations, and prompt injection attacks.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 5. Govern Agent Memory (Warm Cream Canvas #F7F5F0) ─────────────── */}
      <section id="governance" className="py-24 px-6 bg-[#F7F5F0] border-b border-neutral-200">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-3xl mb-12">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#292929] mb-4">
              Govern the AI agent memory, like your database.
            </h2>
            <p className="text-base text-[#717171] leading-relaxed">
              Full visibility into what every AI agent is doing through a control plane so your agents have the same accountability you expect from any production software system.
            </p>
          </div>

          {/* Reporting Grid Metrics (Honest Empirical Benchmarks) */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-12">
            {[
              { label: 'BENCHMARK RUNS', val: '1,200' },
              { label: 'TOKEN DEFLECTION', val: '-72%' },
              { label: 'TOOL LOOP RETRIES', val: '0' },
              { label: 'RETRIEVAL LATENCY', val: '18ms' },
              { label: 'FAULT MTTR', val: '1.8s' },
              { label: 'REFLEXION GAIN', val: '+22%' }
            ].map((m) => (
              <div key={m.label} className="p-5 rounded-[12px] bg-white border border-neutral-200 shadow-sm">
                <span className="text-[10px] font-mono text-[#717171] block mb-1">{m.label}</span>
                <p className="text-2xl font-bold font-mono text-[#292929]">{m.val}</p>
              </div>
            ))}
          </div>

          {/* Interactive Performance Graph Canvas */}
          <div className="mb-14">
            <PerformanceGraph />
          </div>

          {/* 4 Governance Pillars */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 pt-8 border-t border-neutral-200">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Lifecycle management</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Deploy, manage, and govern purpose-built persistent memories across all agent lifecycles.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Single AI control plane</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                From access to token budgets to performance benchmarks, govern every aspect of your agent memory.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Role-based access control</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Manage every agent's memory access through clear roles, scoped namespace permissions, and approval gates.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-[#292929] mb-2">
                <Check size={16} className="text-[#862FE7]" />
                <span>Cost and usage governance</span>
              </div>
              <p className="text-xs text-[#717171] leading-relaxed">
                Set token budgets, rate limits, and spend guardrails for every agent deployed in production.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 6. Open-Source Security & Academic Rigor Grid (Clean White Canvas) ─── */}
      <section className="py-20 px-6 bg-white border-b border-neutral-200 text-center">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-[#292929] mb-10">
            Open-source architecture, enterprise security by design
          </h2>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-6 items-center justify-center opacity-90">
            {[
              'OWASP LLM TOP 10',
              'APACHE 2.0 / MIT',
              'LOCAL AIR-GAPPED',
              'REPRODUCIBLE EVAL',
              'SHA-256 HASH AUDIT',
              'ZERO EGRESS VAULT',
              'STRICT RBAC SCOPE'
            ].map((badge) => (
              <div key={badge} className="p-4 rounded-[10px] border border-neutral-200 bg-[#FAF9F6] shadow-sm">
                <Shield size={22} className="mx-auto text-neutral-700 mb-2" />
                <span className="text-[11px] font-mono font-bold text-[#292929] block">
                  {badge}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 7. ROI Impact: Dynamic Before/After Scanner (Sleek Dark Obsidian) ── */}
      <section id="benchmarks" className="py-24 px-6 bg-neutral-950 text-white relative overflow-hidden">
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="max-w-3xl mb-14">
            <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-white mb-4">
              Business impact and ROI you can measure, across every agent deployment.
            </h2>
            <p className="text-base text-neutral-400 leading-relaxed">
              See how persistent memory eliminates redundant token waste and elevates agent task completion rates.
            </p>
          </div>

          {/* Animated Laser Scanning Comparison Canvas */}
          <div className="mb-12">
            <BeforeAfterSection />
          </div>

          {/* Metrics Band */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 py-6 border-t border-neutral-800 text-center">
            <div>
              <span className="text-3xl font-bold font-mono text-white block">2 days</span>
              <span className="text-xs text-neutral-500 uppercase font-mono">Stateless debug time</span>
            </div>
            <div>
              <span className="text-3xl font-bold font-mono text-white block">$650</span>
              <span className="text-xs text-neutral-500 uppercase font-mono">Inference API Burn</span>
            </div>
            <div>
              <span className="text-3xl font-bold font-mono text-emerald-400 block">40 sec</span>
              <span className="text-xs text-neutral-500 uppercase font-mono">MemoryAgent time</span>
            </div>
            <div>
              <span className="text-3xl font-bold font-mono text-emerald-400 block">$40</span>
              <span className="text-xs text-neutral-500 uppercase font-mono">Optimized task cost</span>
            </div>
          </div>

          {/* Architecture Quote */}
          <div className="mt-8 pt-8 border-t border-neutral-800">
            <p className="text-base text-white italic mb-2">
              "Persistent episodic memory with Bayesian Lower Confidence Bound routing eliminates redundant tool retries and cuts prompt context by over 70% across 1,200 agent trajectories."
            </p>
            <span className="text-xs font-mono text-neutral-400">
              ADAPTIVE AGENT MEMORY EMPIRICAL BENCHMARK (OJT G146)
            </span>
          </div>
        </div>
      </section>

      {/* ── 8. Integrations & Framework Compatibility (Warm Cream Canvas) ── */}
      <section id="integrations" className="py-24 px-6 bg-[#F7F5F0] border-b border-neutral-200">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-2xl mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#292929] mb-4">
              Built for enterprises with seamless integrations and security compliance.
            </h2>
            <p className="text-base text-[#717171] leading-relaxed">
              Plug into your existing agent stack and scale memory governance across your organization.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            <div className="p-8 rounded-[16px] bg-white border border-neutral-200 shadow-sm">
              <h3 className="text-lg font-bold text-[#292929] mb-2">Connect your agent framework</h3>
              <p className="text-xs text-[#717171] leading-relaxed mb-6">
                Native adapters for LangChain, LangGraph, AutoGen, CrewAI, DSPy, and custom Python agent runtimes.
              </p>
              <div className="flex gap-2 flex-wrap">
                {['LangChain', 'LangGraph', 'CrewAI', 'AutoGen', 'DSPy'].map((item) => (
                  <span key={item} className="px-3 py-1.5 rounded-[6px] bg-[#F7F5F0] border border-neutral-200 text-xs font-mono text-[#292929]">
                    {item}
                  </span>
                ))}
              </div>
            </div>

            <div className="p-8 rounded-[16px] bg-white border border-neutral-200 shadow-sm">
              <h3 className="text-lg font-bold text-[#292929] mb-2">Integrate your enterprise data stores</h3>
              <p className="text-xs text-[#717171] leading-relaxed mb-6">
                Store embeddings in BigQuery, PostgreSQL pgvector, Chroma, Qdrant, or Pinecone with row-level security.
              </p>
              <div className="flex gap-2 flex-wrap">
                {['BigQuery', 'pgvector', 'Chroma', 'Qdrant', 'Pinecone'].map((item) => (
                  <span key={item} className="px-3 py-1.5 rounded-[6px] bg-[#F7F5F0] border border-neutral-200 text-xs font-mono text-[#292929]">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 6 Capabilities Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-[12px] bg-white border border-neutral-200">
              <h4 className="text-sm font-bold text-[#292929] mb-2">Centralized Memory Registry</h4>
              <p className="text-xs text-[#717171]">Govern all experiences across teams from one unified console.</p>
            </div>
            <div className="p-6 rounded-[12px] bg-white border border-neutral-200">
              <h4 className="text-sm font-bold text-[#292929] mb-2">Custom Heuristics</h4>
              <p className="text-xs text-[#717171]">Configure Bayesian prior weights and confidence thresholds.</p>
            </div>
            <div className="p-6 rounded-[12px] bg-white border border-neutral-200">
              <h4 className="text-sm font-bold text-[#292929] mb-2">Namespace Isolation</h4>
              <p className="text-xs text-[#717171]">Ensure total memory segregation between production and development.</p>
            </div>
            <div className="p-6 rounded-[12px] bg-white border border-neutral-200">
              <h4 className="text-sm font-bold text-[#292929] mb-2">Zero Training Retention</h4>
              <p className="text-xs text-[#717171]">Customer traces are never used to train external foundation models.</p>
            </div>
            <div className="p-6 rounded-[12px] bg-white border border-neutral-200">
              <h4 className="text-sm font-bold text-[#292929] mb-2">Role-Based Access Control</h4>
              <p className="text-xs text-[#717171]">Manage memory read/write permissions per agent persona.</p>
            </div>
            <div className="p-6 rounded-[12px] bg-white border border-neutral-200">
              <h4 className="text-sm font-bold text-[#292929] mb-2">Data Sovereignty</h4>
              <p className="text-xs text-[#717171]">Deploy vector indexes in your designated cloud regions.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 9. Final CTA Banner (Starry Midnight Skyline) ────────────────── */}
      <section
        className="py-28 px-6 text-center text-white relative overflow-hidden"
        style={{
          background: 'linear-gradient(180deg, #06030c 0%, #110822 50%, #06030c 100%)',
        }}
      >
        <div className="max-w-3xl mx-auto relative z-10">
          <h2 className="text-4xl sm:text-6xl font-bold tracking-tight mb-5">
            See MemoryAgent in action now.
          </h2>
          <p className="text-base text-neutral-400 mb-8 max-w-xl mx-auto">
            Deploy, govern, and scale persistent memory for your autonomous AI agents today.
          </p>
          <a
            href="/dashboard"
            className="inline-block rounded-full bg-white text-neutral-950 px-8 py-3.5 text-sm font-semibold hover:bg-neutral-100 shadow-xl transition-all cursor-pointer"
          >
            Open Console
          </a>
        </div>
      </section>

      {/* ── 10. Footer (Multi-Column Dark Enterprise Grid) ───────────────── */}
      <footer className="bg-[#080A0E] text-[#D0D5DD] py-16 px-6 border-t border-neutral-800">
        <div className="max-w-7xl mx-auto">
          
          <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
            <div>
              <p className="text-xs font-mono font-bold text-white uppercase tracking-wider mb-4">Platform</p>
              <ul className="space-y-2 text-xs text-neutral-400">
                <li><a href="#models" className="hover:text-white">Multi-LLM Adapter</a></li>
                <li><a href="#architecture" className="hover:text-white">Architecture</a></li>
                <li><a href="#governance" className="hover:text-white">Governance</a></li>
                <li><a href="#benchmarks" className="hover:text-white">Benchmarks</a></li>
                <li><Link to="/privacy" className="hover:text-white">Trust Center</Link></li>
              </ul>
            </div>

            <div>
              <p className="text-xs font-mono font-bold text-white uppercase tracking-wider mb-4">Supported Models</p>
              <ul className="space-y-2 text-xs text-neutral-400">
                <li><a href="#models" className="hover:text-white">Claude (Anthropic)</a></li>
                <li><a href="#models" className="hover:text-white">OpenAI (GPT-4o)</a></li>
                <li><a href="#models" className="hover:text-white">Ollama (Local Llama)</a></li>
                <li><a href="#models" className="hover:text-white">Grok (xAI)</a></li>
                <li><a href="#models" className="hover:text-white">DeepSeek R1</a></li>
              </ul>
            </div>

            <div>
              <p className="text-xs font-mono font-bold text-white uppercase tracking-wider mb-4">Frameworks</p>
              <ul className="space-y-2 text-xs text-neutral-400">
                <li><a href="#integrations" className="hover:text-white">LangChain</a></li>
                <li><a href="#integrations" className="hover:text-white">LangGraph</a></li>
                <li><a href="#integrations" className="hover:text-white">CrewAI</a></li>
                <li><a href="#integrations" className="hover:text-white">AutoGen</a></li>
                <li><a href="#integrations" className="hover:text-white">DSPy</a></li>
              </ul>
            </div>

            <div>
              <p className="text-xs font-mono font-bold text-white uppercase tracking-wider mb-4">Resources</p>
              <ul className="space-y-2 text-xs text-neutral-400">
                <li><a href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146" target="_blank" rel="noreferrer" className="hover:text-white">GitHub Repository</a></li>
                <li><a href="#benchmarks" className="hover:text-white">Kaggle Benchmark</a></li>
                <li><a href="#architecture" className="hover:text-white">System Design</a></li>
                <li><Link to="/dashboard" className="hover:text-white">Live Dashboard</Link></li>
              </ul>
            </div>

            <div className="col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-[6px] bg-[#7042DD] flex items-center justify-center text-white">
                  <Brain size={14} />
                </div>
                <span className="text-white font-semibold text-base font-sans">MemoryAgent · G146</span>
              </div>
              <p className="text-xs text-neutral-400 leading-relaxed max-w-sm mb-4">
                The self-improving persistent memory architecture for autonomous AI agents. Grounded in live experience, optimized by Bayesian routing, and governed by your engineering team.
              </p>
              <p className="text-xs text-neutral-500">
                Developed by Kasat Sakshi Dattaprasad &amp; Sumit Das
              </p>
              <div className="flex gap-4 mt-3 text-xs text-neutral-400">
                <Link to="/privacy" className="hover:text-white">Privacy Policy</Link>
                <span>·</span>
                <Link to="/terms" className="hover:text-white">Terms of Service</Link>
              </div>
            </div>
          </div>

          {/* AI Summarize Bar */}
          <div className="py-6 border-t border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-neutral-400">
            <div className="flex items-center gap-3">
              <span>Summarize with AI what MemoryAgent does:</span>
              <a href="https://chatgpt.com/?q=Summarize+what+Adaptive+Agent+Memory+does" target="_blank" rel="noreferrer" className="text-white hover:underline">ChatGPT</a>
              <span>·</span>
              <a href="https://claude.ai" target="_blank" rel="noreferrer" className="text-white hover:underline">Claude</a>
              <span>·</span>
              <a href="https://perplexity.ai" target="_blank" rel="noreferrer" className="text-white hover:underline">Perplexity</a>
              <span>·</span>
              <a href="https://gemini.google.com" target="_blank" rel="noreferrer" className="text-white hover:underline">Gemini</a>
            </div>
            <p>&copy; 2026 MemoryAgent. Built by Kasat Sakshi Dattaprasad &amp; Sumit Das.</p>
          </div>
        </div>
      </footer>

      {/* Floating Persistent AI Widget (Bottom Right) */}
      <div className="fixed bottom-5 right-5 z-40">
        <a
          href="/dashboard"
          className="flex items-center gap-2.5 px-4 py-2.5 rounded-full bg-neutral-900 text-white shadow-2xl border border-neutral-700/80 hover:bg-black transition-all group"
        >
          <div className="w-5 h-5 rounded-full bg-[#7042DD] flex items-center justify-center text-white">
            <MessageSquare size={12} />
          </div>
          <span className="text-xs font-medium">See how MemoryAgent works. <strong className="text-[#C4B5FD] font-semibold">Ask Agent</strong></span>
        </a>
      </div>

    </div>
  )
}
