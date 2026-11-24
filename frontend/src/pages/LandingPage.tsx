import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowRight,
  Copy,
  Check,
  CheckCircle2,
  Terminal,
  Activity,
  Plus,
  Play,
  Pause,
  Cpu,
} from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import AuthModal from '../components/AuthModal'

interface RuntimeStage {
  node: string
  title: string
  detail: string
  meta?: string
  badge?: string
  badgeType?: 'success' | 'danger' | 'neutral'
}

interface RuntimeScenario {
  id: string
  taskTitle: string
  taskDomain: string
  statusType: 'success' | 'warn'
  stages: RuntimeStage[]
}

const RUNTIME_SCENARIOS: RuntimeScenario[] = [
  {
    id: 'stream_decode',
    taskTitle: 'task_stream_decode.py: Parse raw socket stream with surrogate recovery',
    taskDomain: 'coding',
    statusType: 'success',
    stages: [
      {
        node: '1. RETRIEVE',
        title: 'SQLite Local Vector Store Query',
        detail: '> Active Strategy: "Surrogateescape byte fallback" (St = 0.94)\n> Quarantined Hazard: "Strict UTF-8 decode" (St = 0.31, Theorem 1 isolated)\n> Filtered Result: 1 safe procedural pattern injected into context',
        badge: '94% trust',
        badgeType: 'success',
      },
      {
        node: '2. EXECUTE',
        title: 'Parameter-Guarded Code Generation',
        detail: 'def parse_stream(chunk: bytes):\n    # Memory Injected: Apply surrogateescape before json.loads\n    raw = chunk.decode("utf-8", errors="surrogateescape")\n    return json.loads(raw)\n> Execution: Parsed 1,420 stream records in 210ms',
        meta: '0 prompt bloat',
      },
      {
        node: '3. EVALUATE',
        title: 'Deterministic Assertion Verification',
        detail: '> test_stream_decode() ...... PASSED\n> test_malformed_bytes() .... PASSED\n> Binary Outcome: 1.00 (Pass@1 Confirmed)',
        badge: '100% PASS',
        badgeType: 'success',
      },
      {
        node: '4. REFLECT',
        title: 'Procedural Reflection Distillation',
        detail: 'Lesson: "Surrogateescape safely recovers all chunk boundaries without socket termination."\nTuple Minted: (c="stream bytes", a="surrogateescape", p="strict decode")',
        meta: 'Tuple Minted',
      },
      {
        node: '5. CALIBRATE',
        title: 'Asymmetric EMA Calibration',
        detail: 'Formula: St+1 = 0.85 · 0.94 + 0.15 = 0.960 (+0.020 delta)\nReliability Status: Verified Ground Truth (Active)',
        badge: 'St = 0.96',
        badgeType: 'success',
      },
    ],
  },
  {
    id: 'db_migration',
    taskTitle: 'task_db_lock.py: Multi-threaded SQLite writes without WAL mode (Negative Trap)',
    taskDomain: 'coding',
    statusType: 'warn',
    stages: [
      {
        node: '1. RETRIEVE',
        title: 'SQLite Local Vector Store Query',
        detail: '> Query: "High-concurrency SQLite bulk writes"\n> Candidate Memory: "Naive in-memory write buffer" (St = 0.50, Unverified)',
        badge: '50% unverified',
        badgeType: 'neutral',
      },
      {
        node: '2. EXECUTE',
        title: 'Execution with Unverified Strategy',
        detail: 'def bulk_insert(records):\n    cursor.executemany("INSERT INTO logs...", records)\n> Error: sqlite3.OperationalError: database is locked',
        badge: 'Crash',
        badgeType: 'danger',
      },
      {
        node: '3. EVALUATE',
        title: 'Deterministic Assertion Verification',
        detail: '> test_concurrent_writes() ... FAILED (OperationalError)\n> Outcome Score: 0.00 (Failure)\n> Consecutive Failures: k = 3 (Critical Bound Reached)',
        badge: 'FAIL',
        badgeType: 'danger',
      },
      {
        node: '4. REFLECT',
        title: 'Failure Mode Reflection & Trap Identification',
        detail: 'Identified Trap: Parallel transactions without WAL mode cause database locks.\nAction: Flag naive buffer as deprecated anti-pattern.',
        meta: 'Hazard Isolated',
      },
      {
        node: '5. CALIBRATE',
        title: 'Asymmetric EMA Penalty & Theorem 1 Quarantine',
        detail: 'Formula: St+1 = beta · St = 0.70 · 0.50 = 0.350 <= theta (0.35)\nTheorem 1 Triggered: k* <= 3 consecutive failures.\nStrategy permanently quarantined from future context.',
        badge: 'QUARANTINED',
        badgeType: 'danger',
      },
    ],
  },
]

const FAQ_ITEMS = [
  {
    num: '01',
    q: 'Does AEMA introduce latency to agent execution?',
    a: 'Memory retrieval executes in under 25 milliseconds via indexed local vectors. Reflection, evaluation, and trust calibration run asynchronously in the background after the response is sent, adding zero blocking overhead to your agent.',
  },
  {
    num: '02',
    q: 'Where is my data stored?',
    a: 'By default, everything runs locally using SQLite and Chroma on your machine with zero external network requests. For production clusters, AEMA connects directly to your existing PostgreSQL instance with pgvector for strict multi-tenant isolation.',
  },
  {
    num: '03',
    q: 'Can I test the studio without signing up?',
    a: 'Yes. The studio runs in local guest mode by default. You can test prompts, inspect cognitive node transitions, and observe memory quarantine in real time without providing credentials.',
  },
  {
    num: '04',
    q: 'How does Theorem 1 isolate failing strategies without deleting helpful memories?',
    a: 'Theorem 1 deterministic quarantine applies a threshold filter (theta = 0.35). When a specific strategy repeatedly causes test failures, its trust score decays exponentially below 0.35 within at most 3 runs (k* <= 3) and is excluded from retrieval. Useful, orthogonal skills remain untouched.',
  },
  {
    num: '05',
    q: 'Can I bring my own LLM API keys (BYOK) or local models?',
    a: 'Yes. AEMA supports hosted models (Groq, OpenAI, Google Gemini, Anthropic) as well as 100% offline local Ollama instances (e.g. Llama 3.2, Qwen). Keys can be provided via environment variables or directly in the studio browser cache.',
  },
  {
    num: '06',
    q: 'How does AEMA prevent prompt bloat and token consumption limits?',
    a: 'The engine features a Dynamic Context Compactor with token budget circuit breakers. Retrieved memories are compressed and prioritized so only the highest-reliability lessons enter the prompt context within your specified budget.',
  },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<'signin' | 'signup'>('signin')

  // Integration Tabs State
  const [activeTab, setActiveTab] = useState<'python' | 'typescript' | 'mcp' | 'rest'>('python')
  const [copiedCode, setCopiedCode] = useState(false)

  // Enforce light linen canvas on landing page to eliminate overscroll dark bounce
  useEffect(() => {
    document.documentElement.classList.remove('dark')
    document.documentElement.style.backgroundColor = '#FAFAF7'
    document.body.style.backgroundColor = '#FAFAF7'
    return () => {
      document.documentElement.style.backgroundColor = ''
      document.body.style.backgroundColor = ''
    }
  }, [])

  // Continuous Live AEMA 5-Node Cognitive Execution State
  const [activeScenarioIdx, setActiveScenarioIdx] = useState(0)
  const [activeStageIdx, setActiveStageIdx] = useState(0)
  const [isPaused, setIsPaused] = useState(false)

  // FAQ Accordion: Set of open indices (all collapsed by default)
  const [openFaqs, setOpenFaqs] = useState<number[]>([])

  const toggleFaq = (index: number) => {
    setOpenFaqs((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    )
  }

  useEffect(() => {
    if (isPaused) return

    const timer = setInterval(() => {
      setActiveStageIdx((prevStage) => {
        if (prevStage >= 4) {
          setActiveScenarioIdx((prevScen) => (prevScen + 1) % RUNTIME_SCENARIOS.length)
          return 0
        }
        return prevStage + 1
      })
    }, 2400)

    return () => clearInterval(timer)
  }, [isPaused])

  const activeScenario = RUNTIME_SCENARIOS[activeScenarioIdx]
  const currentStage = activeScenario.stages[activeStageIdx]

  const handleOpenAuth = (mode: 'signin' | 'signup') => {
    setAuthModalMode(mode)
    setAuthModalOpen(true)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCode(true)
    setTimeout(() => setCopiedCode(false), 2000)
  }

  const snippets = {
    python: `# 1. Install via pip
# pip install aema

from aema import AdaptiveMemory

# Initialize zero-config local memory (SQLite + Chroma)
memory = AdaptiveMemory(user_id="dev_01")

# Retrieve verified strategies before executing LLM task
context = memory.retrieve("Parse nested stream with custom byte encoding")

# Report verified outcome (repeated failures trigger Theorem 1 quarantine)
memory.feedback(task_id="task_104", success=True)`,

    typescript: `// 1. Install via npm
// npm i @sumitaidev/aema

import { AemaClient } from "@sumitaidev/aema";

const client = new AemaClient({ apiKey: process.env.AEMA_API_KEY });

// Retrieve high-trust execution lessons
const memory = await client.retrieve("PostgreSQL connection pool retry");

// Report outcome back to A-EMA calibration engine
await client.feedback({ memoryId: memory.id, success: true });`,

    mcp: `// Claude Desktop / Cursor IDE Model Context Protocol Config
// Add to claude_desktop_config.json or cursor settings:
{
  "mcpServers": {
    "aema-memory": {
      "command": "npx",
      "args": ["-y", "--package=@sumitaidev/aema", "aema-mcp"]
    }
  }
}`,

    rest: `# Direct HTTP REST API (Any Language or Framework)
curl -X POST https://api.aema.dev/api/agent/execute \\
  -H "Authorization: Bearer $AEMA_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "taskInput": "Implement recursive directory walk with symlink guards",
    "taskDomain": "coding",
    "memoryEnabled": true
  }'`,
  }

  return (
    <div className="min-h-screen bg-[#FAFAF7] text-[#141413] flex flex-col selection:bg-[#EAE8E3]">
      {/* ── Top Atmospheric Hero Header (Atmospheric Sky Aesthetic) ── */}
      <div className="relative overflow-hidden w-full border-b border-[#EAE8E3]/60">
        {/* Layer 1: Ethereal Sky & Soft Cloud Backdrop */}
        <div
          className="absolute inset-0 z-0 bg-top bg-cover bg-no-repeat pointer-events-none opacity-95 transition-opacity duration-300"
          style={{
            backgroundImage: "url('/images/hero-sky-bg.jpg')",
            maskImage: "linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.95) 60%, rgba(0,0,0,0) 100%)",
            WebkitMaskImage: "linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.95) 60%, rgba(0,0,0,0) 100%)",
          }}
        />

        {/* Layer 2: Ethereal Atmospheric Mesh Gradient (Pale Sky + Diffuse Mist) */}
        <div
          className="absolute inset-0 z-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(200, 230, 255, 0.35) 0%, rgba(240, 248, 255, 0.1) 70%, transparent 100%), linear-gradient(to bottom, transparent 50%, #FAFAF7 100%)",
          }}
        />

        {/* 1. Header Navigation Floating on Sky */}
        <Navbar onOpenAuth={handleOpenAuth} />

        {/* 2. Expansive Hero Section (Balanced 2-Column Desktop Grid) */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 pt-12 sm:pt-16 pb-20 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            {/* Left Column: Hero Text & Actions (Col 7) */}
            <div className="lg:col-span-7 space-y-6">
              {/* Eyebrow Tag */}
              <div className="text-xs font-mono uppercase tracking-widest text-[#7E7D77]">
                Experiential Memory for Autonomous Agents
              </div>

              {/* Headline */}
              <h1 className="font-serif-headline text-5xl sm:text-6xl lg:text-[64px] font-normal tracking-tight text-[#141413] leading-[1.1]">
                Memory that actually learns <br className="hidden sm:inline" />
                from <span className="italic font-normal">what went wrong</span>.
              </h1>

              {/* Subtitle */}
              <p className="text-base sm:text-lg text-[#5A5955] leading-relaxed max-w-xl font-normal">
                Most agents run blind: when an execution fails, the mistake is forgotten and repeated tomorrow. AEMA scores every run, isolates failing patterns, and turns past executions into reliable ground truth.
              </p>

              {/* Primary Actions */}
              <div className="flex flex-wrap items-center gap-4 pt-2">
                <button
                  onClick={() => navigate('/dashboard?demo=true&tab=overview')}
                  className="px-5 py-2.5 rounded bg-[#141413] text-[#FAFAF7] text-xs font-medium hover:bg-[#2B2B28] transition-colors flex items-center gap-2 cursor-pointer shadow-sm"
                >
                  <span>Launch Studio</span>
                  <ArrowRight size={14} />
                </button>
                <Link
                  to="/docs"
                  className="px-5 py-2.5 rounded border border-[#D5D3CC] bg-white/90 backdrop-blur-sm text-[#141413] text-xs font-medium hover:bg-white transition-colors"
                >
                  Read Documentation
                </Link>
              </div>

              {/* Four Trust Badges: Strict 2x2 Grid with Exact Vertical Alignment */}
              <div className="pt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2.5 text-xs text-[#5A5955] font-mono max-w-lg">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 size={13} className="text-[#4EAA79] shrink-0" />
                  <span>Deterministic Bound (k* &le; 3)</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 size={13} className="text-[#4EAA79] shrink-0" />
                  <span>Asymmetric Calibration (&beta; &gt; &alpha;)</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 size={13} className="text-[#4EAA79] shrink-0" />
                  <span>Air-Gapped Local SQLite</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 size={13} className="text-[#4EAA79] shrink-0" />
                  <span>&lt;25ms Vector Retrieval</span>
                </span>
              </div>
            </div>

            {/* Right Column: Live AEMA Cognitive Execution Runtime Console (Col 5) */}
            <div className="lg:col-span-5">
              <div className="rounded-2xl border border-[#2E2E2A] bg-[#141412] text-[#EDECE8] shadow-2xl w-full overflow-hidden select-none">
                {/* Window Header Strip */}
                <div className="px-4 py-3 bg-[#181816] border-b border-[#242422] flex items-center justify-between">
                  {/* Window Control Dots */}
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F56]" />
                    <span className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]" />
                    <span className="w-2.5 h-2.5 rounded-full bg-[#27C93F]" />
                  </div>

                  {/* Script Name */}
                  <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#9E9D96]">
                    <Terminal size={12} className="text-[#6366F1]" />
                    <span>aema/runtime.py</span>
                  </div>

                  {/* Stage Status */}
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#4EAA79] animate-pulse" />
                    <span className="text-[10px] font-mono text-[#4EAA79] uppercase font-semibold">
                      {currentStage.node.split('.')[1]?.trim() || 'CALIBRATE'}
                    </span>
                  </div>
                </div>

                {/* Scenario Selector & Auto-cycle Strip */}
                <div className="px-3.5 py-2 bg-[#121210] border-b border-[#242422] flex items-center justify-between gap-2 text-xs font-mono">
                  <div className="flex items-center gap-1.5">
                    {RUNTIME_SCENARIOS.map((scen, idx) => (
                      <button
                        key={scen.id}
                        type="button"
                        onClick={() => {
                          setActiveScenarioIdx(idx)
                          setActiveStageIdx(0)
                        }}
                        className={`px-2.5 py-1 rounded text-[11px] transition-colors cursor-pointer ${
                          activeScenarioIdx === idx
                            ? 'bg-[#22221E] text-white font-medium border border-[#3E3E38]'
                            : 'text-[#7E7D77] hover:text-[#EDECE8] border border-transparent'
                        }`}
                      >
                        {idx === 0 ? 'Trial 1: Recovery' : 'Trial 2: Trap Trap (k*<=3)'}
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => setIsPaused(!isPaused)}
                    className="text-[10px] text-[#7E7D77] hover:text-[#EDECE8] flex items-center gap-1 transition-colors cursor-pointer px-2 py-0.5 rounded bg-[#181816] border border-[#262624]"
                    title={isPaused ? 'Resume auto-cycle' : 'Pause auto-cycle'}
                  >
                    {isPaused ? <Play size={10} /> : <Pause size={10} />}
                    <span>{isPaused ? 'Resume' : 'Auto'}</span>
                  </button>
                </div>

                {/* 5-Node Progress Stepper Bar */}
                <div className="grid grid-cols-5 border-b border-[#242422] bg-[#161614] text-[10px] font-mono">
                  {['Retrieve', 'Execute', 'Evaluate', 'Reflect', 'Calibrate'].map((stepName, sIdx) => {
                    const isCurrent = activeStageIdx === sIdx
                    const isPast = activeStageIdx > sIdx
                    return (
                      <button
                        key={stepName}
                        type="button"
                        onClick={() => setActiveStageIdx(sIdx)}
                        className={`py-1.5 px-1 text-center transition-colors border-r last:border-r-0 border-[#242422] flex flex-col items-center gap-0.5 cursor-pointer ${
                          isCurrent
                            ? 'bg-[#1E1E1B] text-white font-semibold border-b-2 border-b-[#4EAA79]'
                            : isPast
                            ? 'text-[#9E9D96]'
                            : 'text-[#5A5955] hover:text-[#7E7D77]'
                        }`}
                      >
                        <span className="text-[9px] text-[#7E7D77]">{sIdx + 1}</span>
                        <span className="truncate w-full">{stepName}</span>
                      </button>
                    )
                  })}
                </div>

                {/* Active Task Identifier Bar */}
                <div className="p-3 bg-[#141412] border-b border-[#20201D] flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 truncate mr-2">
                    <Cpu size={13} className="text-[#6366F1] shrink-0" />
                    <span className="font-mono text-[#D8D7D2] text-[11px] truncate">
                      {activeScenario.taskTitle}
                    </span>
                  </div>
                  <span className="shrink-0 text-[10px] font-mono px-2 py-0.5 rounded bg-[#1C1C18] border border-[#2E2E2A] text-[#9E9D96]">
                    {activeScenario.taskDomain}
                  </span>
                </div>

                {/* Live Console Output Box */}
                <div className="p-4 bg-[#10100E] min-h-[220px] flex flex-col justify-between font-mono text-xs">
                  <div className="space-y-2.5">
                    {/* Node Title & Stage Badge */}
                    <div className="flex items-center justify-between">
                      <span className="text-[#4EAA79] text-xs font-semibold flex items-center gap-1.5">
                        <Activity size={12} className="text-[#4EAA79]" />
                        <span>{currentStage.node}: {currentStage.title}</span>
                      </span>
                      {currentStage.badge && (
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            currentStage.badgeType === 'danger'
                              ? 'bg-[#2E1E1E] text-[#D9534F] border-[#4E2A2A]'
                              : currentStage.badgeType === 'neutral'
                              ? 'bg-[#242420] text-[#E67E22] border-[#3E3E34]'
                              : 'bg-[#1A261E] text-[#4EAA79] border-[#2E4234]'
                          }`}
                        >
                          {currentStage.badge}
                        </span>
                      )}
                    </div>

                    {/* Detail Preformatted Box */}
                    <div className="p-3 rounded-lg bg-[#141412] border border-[#242422] text-[#B8B7B2] text-[11px] leading-relaxed whitespace-pre-wrap font-mono">
                      {currentStage.detail}
                    </div>
                  </div>

                  {/* Theoretical Bound Footer */}
                  <div className="pt-3 mt-3 border-t border-[#1C1C18] flex items-center justify-between text-[10px] text-[#7E7D77]">
                    <span>Deterministic Bound: k* &le; 3 quarantine</span>
                    <span className="text-[#4EAA79] font-medium">&lt;25ms retrieval latency</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 pb-24 w-full">
        {/* 3. The Core Problem Section (Full Width 3-Column Grid) */}
        <section className="mt-16 pt-8 w-full">
          <div className="max-w-3xl mb-12">
            <div className="text-xs font-mono uppercase tracking-widest text-[#7E7D77] mb-2">
              The Problem with Standard Memory
            </div>
            <h2 className="font-serif-headline text-3xl sm:text-4xl font-normal text-[#141413]">
              The difference between storing logs and <span className="italic">learning</span>
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#6B6A65] leading-relaxed">
              Standard vector databases store everything uncritically. If an agent previously hallucinated a deprecated library or a broken SQL pattern, a vector search retrieves it again simply because the words match.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-xs leading-relaxed">
            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5">
              <div className="font-mono text-[11px] uppercase tracking-wider text-[#7E7D77] mb-2 font-medium">
                1. Stateless Agents
              </div>
              <p className="text-[#6B6A65]">
                Every run begins as a blank slate. When an agent discovers a tricky edge case or API workaround, that insight vanishes when the session ends. Tomorrow, it hits the exact same bug again.
              </p>
            </div>

            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5">
              <div className="font-mono text-[11px] uppercase tracking-wider text-[#D9534F] mb-2 font-medium">
                2. Blind Vector RAG
              </div>
              <p className="text-[#6B6A65]">
                Treats every past generation as equal. When an agent invents an invalid function call, that mistake is saved into the index. Over repeated runs, error patterns multiply and poison subsequent prompts.
              </p>
            </div>

            <div className="border-2 border-[#141413] bg-white rounded-lg p-5 relative shadow-sm">
              <div className="font-mono text-[11px] uppercase tracking-wider text-[#141413] font-bold mb-2">
                3. AEMA Experiential Memory
              </div>
              <p className="text-[#141413]">
                Tracks the empirical outcome of each run. Negative strategies are penalized faster than positive ones are rewarded (&beta; &gt; &alpha;). Failing strategies are mathematically quarantined so they never reach context again.
              </p>
            </div>
          </div>
        </section>

        {/* 4. The Five-Stage Cognitive Cycle (Clear, Accessible Descriptions) */}
        <section className="mt-20 pt-16 border-t border-[#EAE8E3] w-full">
          <div className="max-w-3xl mb-12">
            <div className="text-xs font-mono uppercase tracking-widest text-[#7E7D77] mb-2">
              Empirical Pipeline
            </div>
            <h2 className="font-serif-headline text-3xl sm:text-4xl font-normal text-[#141413]">
              The five-stage cognitive cycle
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#6B6A65] leading-relaxed">
              Every query executes through an empirical five-node loop: finding verified memories, guiding the agent, running tests, extracting lessons, and updating mathematical trust.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 w-full text-xs">
            {/* Stage 1 */}
            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5 flex flex-col justify-between">
              <div>
                <div className="font-mono text-[11px] font-bold text-[#141413] mb-2">
                  01 / RETRIEVE
                </div>
                <div className="font-medium text-[#141413] text-xs mb-1.5">
                  Smart Memory Search
                </div>
                <p className="text-[#6B6A65] text-[11px] leading-relaxed">
                  Finds relevant past experiences and checks their reliability score. Failing patterns that were previously quarantined are automatically ignored.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#F0EFEA] font-mono text-[10px] text-[#7E7D77]">
                Fast &lt;25ms lookup
              </div>
            </div>

            {/* Stage 2 */}
            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5 flex flex-col justify-between">
              <div>
                <div className="font-mono text-[11px] font-bold text-[#141413] mb-2">
                  02 / EXECUTE
                </div>
                <div className="font-medium text-[#141413] text-xs mb-1.5">
                  Guarded Generation
                </div>
                <p className="text-[#6B6A65] text-[11px] leading-relaxed">
                  Guides the agent with proven solutions and clear warnings about known mistakes before it generates code or takes action.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#F0EFEA] font-mono text-[10px] text-[#7E7D77]">
                Zero prompt clutter
              </div>
            </div>

            {/* Stage 3 */}
            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5 flex flex-col justify-between">
              <div>
                <div className="font-mono text-[11px] font-bold text-[#141413] mb-2">
                  03 / EVALUATE
                </div>
                <div className="font-medium text-[#141413] text-xs mb-1.5">
                  Automatic Verification
                </div>
                <p className="text-[#6B6A65] text-[11px] leading-relaxed">
                  Runs real tests to check if the agent's answer actually works. Passes increase confidence; unexpected errors are flagged immediately.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#F0EFEA] font-mono text-[10px] text-[#7E7D77]">
                Instant pass/fail check
              </div>
            </div>

            {/* Stage 4 */}
            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5 flex flex-col justify-between">
              <div>
                <div className="font-mono text-[11px] font-bold text-[#141413] mb-2">
                  04 / REFLECT
                </div>
                <div className="font-medium text-[#141413] text-xs mb-1.5">
                  Lesson Extraction
                </div>
                <p className="text-[#6B6A65] text-[11px] leading-relaxed">
                  Extracts the exact lesson from what succeeded or what went wrong, turning the run into a reusable rule for future tasks.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#F0EFEA] font-mono text-[10px] text-[#7E7D77]">
                Learns automatically
              </div>
            </div>

            {/* Stage 5 */}
            <div className="border-2 border-[#141413] bg-white rounded-lg p-5 flex flex-col justify-between shadow-sm">
              <div>
                <div className="font-mono text-[11px] font-bold text-[#141413] mb-2">
                  05 / CALIBRATE
                </div>
                <div className="font-medium text-[#141413] text-xs mb-1.5">
                  Trust Update &amp; Safety Lock
                </div>
                <p className="text-[#141413] text-[11px] leading-relaxed">
                  Adjusts the trust score. Mistakes drop trust quickly so bad habits cannot repeat. If an action fails 3 times, it is permanently locked out.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-[#EAE8E3] font-mono text-[10px] text-[#4EAA79] font-semibold">
                Theorem 1 Bound (k* &le; 3)
              </div>
            </div>
          </div>
        </section>

        {/* 5. Three Architectural Guarantees (Full Width 3-Column Grid) */}
        <section className="mt-20 pt-16 border-t border-[#EAE8E3] w-full">
          <div className="max-w-3xl mb-12">
            <div className="text-xs font-mono uppercase tracking-widest text-[#7E7D77] mb-2">
              System Architecture
            </div>
            <h2 className="font-serif-headline text-3xl sm:text-4xl font-normal text-[#141413]">
              Three architectural guarantees
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#6B6A65] leading-relaxed">
              AEMA makes agent memory predictable, testable, and mathematically bounded rather than relying on prompt heuristics.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-xs leading-relaxed">
            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5">
              <div className="font-mono text-[11px] uppercase tracking-wider text-[#141413] font-semibold mb-2">
                1. Deterministic Quarantine
              </div>
              <p className="text-[#6B6A65]">
                Failing strategies are mathematically bounded. If an action repeatedly causes test failures, trust drops below the critical threshold within at most 3 runs (k* &le; 3), locking it in quarantine so it cannot corrupt future generations.
              </p>
            </div>

            <div className="border border-[#EAE8E3] bg-white rounded-lg p-5">
              <div className="font-mono text-[11px] uppercase tracking-wider text-[#141413] font-semibold mb-2">
                2. Asymmetric Calibration
              </div>
              <p className="text-[#6B6A65]">
                Penalties for failure are weighted more heavily than rewards for success (&beta; &gt; &alpha;). A single unverified run cannot dominate retrieval, protecting the agent against premature overconfidence.
              </p>
            </div>

            <div className="border-2 border-[#141413] bg-white rounded-lg p-5 relative shadow-sm">
              <div className="font-mono text-[11px] uppercase tracking-wider text-[#141413] font-bold mb-2">
                3. Zero-Leak Infrastructure
              </div>
              <p className="text-[#141413]">
                Runs completely air-gapped on local SQLite and Chroma for development, with zero external network calls. In production, it connects seamlessly to PostgreSQL with pgvector for strict multi-tenant isolation.
              </p>
            </div>
          </div>
        </section>

        {/* 5. Empirical Benchmarks Table (Full Width Table) */}
        <section id="benchmarks" className="mt-20 pt-16 border-t border-[#EAE8E3] w-full">
          <div className="max-w-3xl mb-10">
            <div className="text-xs font-mono uppercase tracking-widest text-[#7E7D77] mb-2">
              Empirical Findings
            </div>
            <h2 className="font-serif-headline text-3xl sm:text-4xl font-normal text-[#141413]">
              Benchmarked against negative transfer
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#6B6A65] leading-relaxed">
              When exposed to contradictory evidence and deprecated tool parameters, naive memory agents experience severe performance degradation. AEMA isolates the failures and recovers accuracy.
            </p>
          </div>

          <div className="border border-[#EAE8E3] rounded-lg bg-white overflow-hidden w-full shadow-sm">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#EAE8E3] bg-[#F7F6F2] font-mono text-[11px] text-[#7E7D77]">
                  <th className="py-3 px-5 font-medium">Evaluation Suite</th>
                  <th className="py-3 px-5 font-medium">Task Domain</th>
                  <th className="py-3 px-5 font-medium">Stateless Baseline</th>
                  <th className="py-3 px-5 font-medium">Naive Vector RAG</th>
                  <th className="py-3 px-5 font-medium text-[#141413]">AEMA Engine</th>
                  <th className="py-3 px-5 font-medium">p-value (McNemar)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EAE8E3] text-[#6B6A65] font-mono text-[11px]">
                <tr>
                  <td className="py-3.5 px-5 font-sans text-xs text-[#141413] font-medium">Confirmatory Trap Suite</td>
                  <td className="py-3.5 px-5">Coding & Tool Use</td>
                  <td className="py-3.5 px-5">60.0%</td>
                  <td className="py-3.5 px-5 text-[#D9534F] font-semibold">0.0% (Poisoned)</td>
                  <td className="py-3.5 px-5 text-[#4EAA79] font-semibold">100.0%</td>
                  <td className="py-3.5 px-5">p = 1.192 &times; 10⁻⁷</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-5 font-sans text-xs text-[#141413] font-medium">HotpotQA Multi-Hop Contradiction</td>
                  <td className="py-3.5 px-5">Multi-Hop Research</td>
                  <td className="py-3.5 px-5">52.4%</td>
                  <td className="py-3.5 px-5 text-[#D9534F] font-semibold">14.8%</td>
                  <td className="py-3.5 px-5 text-[#4EAA79] font-semibold">88.6%</td>
                  <td className="py-3.5 px-5">p = 4.821 &times; 10⁻⁵</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-5 font-sans text-xs text-[#141413] font-medium">ToolBench API Deprecation</td>
                  <td className="py-3.5 px-5">Tool Calling</td>
                  <td className="py-3.5 px-5">64.2%</td>
                  <td className="py-3.5 px-5 text-[#D9534F] font-semibold">22.0%</td>
                  <td className="py-3.5 px-5 text-[#4EAA79] font-semibold">91.4%</td>
                  <td className="py-3.5 px-5">p = 2.140 &times; 10⁻⁶</td>
                </tr>
                <tr>
                  <td className="py-3.5 px-5 font-sans text-xs text-[#141413] font-medium">ALFWorld Embodied Planning</td>
                  <td className="py-3.5 px-5">Planning & Reasoning</td>
                  <td className="py-3.5 px-5">58.0%</td>
                  <td className="py-3.5 px-5 text-[#D9534F] font-semibold">31.5%</td>
                  <td className="py-3.5 px-5 text-[#4EAA79] font-semibold">85.0%</td>
                  <td className="py-3.5 px-5">p = 9.310 &times; 10⁻⁴</td>
                </tr>
              </tbody>
            </table>
            <div className="px-5 py-3 border-t border-[#EAE8E3] bg-[#FAF9F5] text-[11px] text-[#7E7D77] flex items-center justify-between">
              <span>*Statistically significant across repeated trials (p &lt; 0.001)</span>
              <span className="font-mono text-[#141413]">Protocol Frozen (PR #88)</span>
            </div>
          </div>
        </section>

        {/* 6. Multi-Tab Code Integration (Full Width) */}
        <section id="docs" className="mt-20 pt-16 border-t border-[#EAE8E3] w-full">
          <div className="max-w-3xl mb-8">
            <h2 className="font-serif-headline text-3xl sm:text-4xl font-normal text-[#141413]">
              Integrates into existing agent code
            </h2>
            <p className="mt-2 text-xs sm:text-sm text-[#6B6A65]">
              AEMA is framework-agnostic. Use it with LangGraph, CrewAI, standalone scripts, Claude Desktop, Cursor, or direct REST calls.
            </p>
          </div>

          <div className="rounded-lg border border-[#242422] bg-[#141412] text-[#EDECE8] shadow-sm w-full overflow-hidden">
            {/* Tabs Header */}
            <div className="flex items-center justify-between px-4 border-b border-[#242422] bg-[#161614]">
              <div className="flex items-center gap-1 font-mono text-xs">
                <button
                  onClick={() => setActiveTab('python')}
                  className={`px-3.5 py-2.5 border-b-2 transition-colors cursor-pointer ${
                    activeTab === 'python'
                      ? 'border-[#EDECE8] text-white font-medium'
                      : 'border-transparent text-[#7E7D77] hover:text-[#EDECE8]'
                  }`}
                >
                  Python SDK
                </button>
                <button
                  onClick={() => setActiveTab('typescript')}
                  className={`px-3.5 py-2.5 border-b-2 transition-colors cursor-pointer ${
                    activeTab === 'typescript'
                      ? 'border-[#EDECE8] text-white font-medium'
                      : 'border-transparent text-[#7E7D77] hover:text-[#EDECE8]'
                  }`}
                >
                  TypeScript SDK
                </button>
                <button
                  onClick={() => setActiveTab('mcp')}
                  className={`px-3.5 py-2.5 border-b-2 transition-colors cursor-pointer ${
                    activeTab === 'mcp'
                      ? 'border-[#EDECE8] text-white font-medium'
                      : 'border-transparent text-[#7E7D77] hover:text-[#EDECE8]'
                  }`}
                >
                  MCP Server
                </button>
                <button
                  onClick={() => setActiveTab('rest')}
                  className={`px-3.5 py-2.5 border-b-2 transition-colors cursor-pointer ${
                    activeTab === 'rest'
                      ? 'border-[#EDECE8] text-white font-medium'
                      : 'border-transparent text-[#7E7D77] hover:text-[#EDECE8]'
                  }`}
                >
                  REST API
                </button>
              </div>

              <button
                onClick={() => copyToClipboard(snippets[activeTab])}
                className="flex items-center gap-1.5 text-[11px] font-mono text-[#7E7D77] hover:text-white transition-colors cursor-pointer"
              >
                {copiedCode ? <Check size={12} className="text-[#4EAA79]" /> : <Copy size={12} />}
                <span>{copiedCode ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {/* Snippet Display */}
            <pre className="p-6 font-mono text-xs leading-relaxed text-[#B8B7B2] overflow-x-auto min-h-[170px]">
              <code>{snippets[activeTab]}</code>
            </pre>
          </div>
        </section>

        {/* 7. Frequently Asked Questions (Numbered Accordion Layout) */}
        <section className="mt-20 pt-16 border-t border-[#EAE8E3] w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14">
            {/* Left Column: Context & Docs Link (Col 4) */}
            <div className="lg:col-span-4 space-y-4">
              <h2 className="font-serif-headline text-3xl sm:text-4xl font-normal text-[#141413] tracking-tight">
                Frequently asked questions.
              </h2>
              <p className="text-xs sm:text-sm text-[#5A5955] leading-relaxed">
                Learn how AEMA secures agent experiential memory, prevents negative transfer, and integrates into existing pipelines.
              </p>
              <div className="pt-2">
                <Link
                  to="/docs"
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-[#141413] hover:text-[#5A5955] transition-colors group cursor-pointer"
                >
                  <span>Read the docs</span>
                  <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
              </div>
            </div>

            {/* Right Column: Numbered Hairline Accordion (Col 8) */}
            <div className="lg:col-span-8 border-b border-[#EAE8E3]">
              {FAQ_ITEMS.map((item, idx) => {
                const isOpen = openFaqs.includes(idx)
                return (
                  <div
                    key={item.num}
                    className="border-t border-[#EAE8E3] py-5 sm:py-6 transition-colors"
                  >
                    <div
                      onClick={() => toggleFaq(idx)}
                      className="flex items-start justify-between gap-4 cursor-pointer select-none group"
                    >
                      {/* Left: Number + Question */}
                      <div className="flex items-baseline gap-4 sm:gap-6">
                        <span className="font-mono text-xs text-[#9E9D96] shrink-0 font-normal">
                          {item.num}
                        </span>
                        <span className="font-medium text-base sm:text-lg text-[#141413] group-hover:text-[#3A3A38] transition-colors tracking-tight leading-snug">
                          {item.q}
                        </span>
                      </div>

                      {/* Right: Circular Toggle Button (Turns solid black when open!) */}
                      <button
                        type="button"
                        aria-label={isOpen ? 'Collapse answer' : 'Expand answer'}
                        className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-200 cursor-pointer ${
                          isOpen
                            ? 'bg-[#141413] text-white border border-[#141413]'
                            : 'bg-white text-[#141413] border border-[#D5D3CC] group-hover:border-[#141413]'
                        }`}
                      >
                        <Plus
                          size={15}
                          className={`transition-transform duration-200 ${isOpen ? 'rotate-45' : 'rotate-0'}`}
                        />
                      </button>
                    </div>

                    {/* Expandable Answer */}
                    <div
                      className={`grid transition-all duration-300 ease-in-out overflow-hidden ${
                        isOpen ? 'grid-rows-[1fr] opacity-100 pt-3' : 'grid-rows-[0fr] opacity-0 pt-0'
                      }`}
                    >
                      <div className="overflow-hidden pl-7 sm:pl-10 pr-6 sm:pr-12">
                        <p className="text-xs sm:text-sm text-[#5A5955] leading-relaxed">
                          {item.a}
                        </p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      </main>

      {/* 8. Minimal Footer */}
      <Footer />

      {/* 9. Two-Column Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </div>
  )
}
