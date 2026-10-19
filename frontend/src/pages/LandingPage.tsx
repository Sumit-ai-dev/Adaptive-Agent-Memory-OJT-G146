import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  Terminal,
  Code,
  Copy,
  Check,
  Layers,
  Play,
  Compass,
  GitBranch,
} from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import AuthModal from '../components/AuthModal'
import StatusBadge from '../components/StatusBadge'
import TheoremSandbox from '../components/TheoremSandbox'
import BenchmarkMatrix from '../components/BenchmarkMatrix'
import PromptConsole from '../components/PromptConsole'
import ExecutionStepper from '../components/ExecutionStepper'
import { executeAgentTask } from '../services/api'
import type { TaskExecution, TaskDomain } from '../types'

export default function LandingPage() {
  const navigate = useNavigate()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState<'signin' | 'signup'>('signin')

  // Interactive Execution Preview State
  const [previewRunning, setPreviewRunning] = useState(false)
  const [previewStage, setPreviewStage] = useState<'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update' | 'idle' | 'complete'>('idle')
  const [previewExecution, setPreviewExecution] = useState<TaskExecution | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Copy States
  const [copiedPypi, setCopiedPypi] = useState(false)
  const [copiedNpm, setCopiedNpm] = useState(false)
  const [copiedMcp, setCopiedMcp] = useState(false)

  const handleOpenAuth = (mode: 'signin' | 'signup') => {
    setAuthModalMode(mode)
    setAuthModalOpen(true)
  }

  const handleRunHeroPreview = async (params: {
    prompt: string
    domain: TaskDomain
    memoryEnabled: boolean
    simulateFailure?: boolean
  }) => {
    setPreviewRunning(true)
    setPreviewStage('retrieval')
    setPreviewError(null)
    try {
      const exec = await executeAgentTask({
        taskInput: params.prompt,
        taskDomain: params.domain,
        memoryEnabled: params.memoryEnabled,
        simulateFailure: params.simulateFailure,
        isExplicitDemo: true,
        onStageChange: (stage) => setPreviewStage(stage),
      })
      setPreviewExecution(exec)
      setPreviewStage('complete')
    } catch (err: any) {
      console.error('Public preview execution error:', err)
      setPreviewError(err?.message || 'Public preview execution encountered an error.')
      setPreviewStage('idle')
    } finally {
      setPreviewRunning(false)
    }
  }

  const copyToClipboard = (text: string, setter: (val: boolean) => void) => {
    navigator.clipboard.writeText(text)
    setter(true)
    setTimeout(() => setter(false), 2000)
  }

  const mcpConfigCode = `{
  "mcpServers": {
    "aema": {
      "command": "npx",
      "args": ["-y", "-p", "aema-memory", "aema-mcp"]
    }
  }
}`

  const pythonSnippet = `from aema import AEMAMemoryManager

# Initialize reliability-aware memory manager (canonical defaults)
manager = AEMAMemoryManager(alpha=0.85, beta=0.70, theta=0.35, s0=0.75)

# Record experiential outcome
manager.record_outcome(memory_id="mem_42", success=False)

# Retrieve only empirical, non-quarantined memories
safe_memories = manager.get_active_memories()`

  return (
    <div className="min-h-screen bg-[#F8F8F6] dark:bg-[#0D0F12] text-[#1A1A1A] dark:text-[#F4F4F6] transition-colors selection:bg-indigo-100 dark:selection:bg-indigo-950 font-sans">
      {/* Horizontal Navbar */}
      <Navbar onOpenAuth={handleOpenAuth} />

      {/* ─── Hero Section (Asymmetric 55/45 Split) ─────────────────────────── */}
      <section className="relative pt-16 pb-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832] overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
            
            {/* Left Column: Narrative, Problem, Intent (7 cols on desktop) */}
            <div className="lg:col-span-7 space-y-6 text-left">
              {/* Monospace Descriptor */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md border text-xs font-mono bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-zinc-500 dark:text-zinc-400">
                  Adaptive Experience Memory Architecture
                </span>
                <span className="text-zinc-300 dark:text-zinc-700">/</span>
                <span className="text-indigo-600 dark:text-indigo-400 font-semibold">
                  v0.1.0 Released
                </span>
              </div>

              {/* Editorial Headline */}
              <h1 className="text-4xl sm:text-5xl lg:text-[54px] font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6] leading-[1.12]">
                Reliable experiential memory for autonomous AI agents.
              </h1>

              {/* Explanatory Paragraph (Plain English, High Clarity) */}
              <p className="text-base text-zinc-600 dark:text-zinc-300 max-w-xl leading-relaxed">
                Standard agent memory retrieves past experiences by semantic similarity alone, blindly repeating past mistakes and causing task performance to collapse. AEMA separates semantic relevance from empirical reliability, updating trust asymmetrically and isolating negative transfer.
              </p>

              {/* Research Attribution */}
              <div className="text-xs text-zinc-500 dark:text-zinc-400 pt-1">
                Researched and co-developed by{' '}
                <a
                  href="https://github.com/Sumit-ai-dev"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#1A1A1A] dark:text-zinc-200 font-medium hover:underline"
                >
                  Sumit Das (@Sumit-ai-dev)
                </a>{' '}
                and{' '}
                <a
                  href="https://github.com/SakshiKasat18"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#1A1A1A] dark:text-zinc-200 font-medium hover:underline"
                >
                  Kasat Sakshi Dattaprasad (@SakshiKasat18)
                </a>.
              </div>

              {/* Strictly Two Focused CTAs */}
              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={() => navigate('/dashboard?demo=true')}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500 transition-all shadow-sm cursor-pointer"
                >
                  <Play size={14} />
                  <span>Explore Demo</span>
                </button>

                <a
                  href="#research"
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border text-xs font-medium transition-colors text-zinc-700 dark:text-zinc-300 hover:text-black dark:hover:text-white border-[#E5E5DF] dark:border-[#232832] bg-white dark:bg-[#14171C]"
                >
                  <span>Read the Research</span>
                  <ArrowRight size={13} />
                </a>
              </div>

              {/* Compact Package Pills */}
              <div className="pt-2 flex flex-wrap items-center gap-2 text-xs font-mono">
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832]">
                  <span className="text-zinc-400">$</span>
                  <span className="text-zinc-800 dark:text-zinc-200">pip install aema</span>
                  <button
                    onClick={() => copyToClipboard('pip install aema', setCopiedPypi)}
                    className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 ml-1 cursor-pointer"
                    title="Copy command"
                  >
                    {copiedPypi ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  </button>
                </div>

                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832]">
                  <span className="text-zinc-400">$</span>
                  <span className="text-zinc-800 dark:text-zinc-200">npm i aema-memory</span>
                  <button
                    onClick={() => copyToClipboard('npm i aema-memory', setCopiedNpm)}
                    className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 ml-1 cursor-pointer"
                    title="Copy command"
                  >
                    {copiedNpm ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Right Column: Serene Landscape Atmosphere + Layered Product Window (5 cols) */}
            <div className="lg:col-span-5 relative">
              {/* Nature Atmospheric Background Plate */}
              <div className="relative rounded-2xl overflow-hidden border border-[#E5E5DF] dark:border-[#232832] shadow-md bg-zinc-100 dark:bg-zinc-900">
                <img
                  src="/images/hero-nature.jpg"
                  alt="Atmospheric alpine misty landscape"
                  className="w-full h-56 object-cover object-center filter saturate-90 brightness-95"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
                <div className="absolute bottom-3 left-4 text-white text-xs font-mono font-medium flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>AEMA Operational Core: Protocol Sandbox</span>
                </div>
              </div>

              {/* Layered Real AEMA Studio Window */}
              <div className="mt-4 rounded-xl border p-4 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] shadow-lg text-left text-xs space-y-3">
                <div className="flex items-center justify-between border-b pb-2.5 border-[#E5E5DF] dark:border-[#232832]">
                  <div className="flex items-center gap-2">
                    <Terminal size={14} className="text-indigo-600 dark:text-indigo-400" />
                    <span className="font-mono text-[11px] font-semibold text-zinc-700 dark:text-zinc-300">
                      Live Studio Cycle
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-emerald-700 dark:text-emerald-400 font-semibold px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800">
                    S(t+1) = 0.85*St + 0.15
                  </span>
                </div>

                {/* Micro Stage Rail */}
                <div className="grid grid-cols-5 gap-1.5 text-center font-mono text-[10px]">
                  <div className="p-1 rounded bg-zinc-100 dark:bg-[#1C2026] text-zinc-700 dark:text-zinc-300">
                    Retrieve
                  </div>
                  <div className="p-1 rounded bg-zinc-100 dark:bg-[#1C2026] text-zinc-700 dark:text-zinc-300">
                    Execute
                  </div>
                  <div className="p-1 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 font-semibold">
                    Evaluate
                  </div>
                  <div className="p-1 rounded bg-zinc-100 dark:bg-[#1C2026] text-zinc-700 dark:text-zinc-300">
                    Reflect
                  </div>
                  <div className="p-1 rounded bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-300 font-semibold">
                    Trust
                  </div>
                </div>

                {/* Live Strategy Injected */}
                <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-[#1C2026] border border-[#E5E5DF] dark:border-[#232832] font-mono text-[11px] text-zinc-700 dark:text-zinc-300">
                  <span className="text-zinc-400 block mb-0.5 text-[10px]">RETRIEVED STRATEGY (exp-001):</span>
                  "Split schema modifications into non-blocking dual-write phases."
                </div>

                {/* Score Shift */}
                <div className="flex items-center justify-between text-[11px] font-mono pt-1 text-zinc-500">
                  <span>Trust Score: 91.0% to 92.4%</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">+1.4% gain</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ─── 01 / PRINCIPLE: WHY AEMA (Editorial 2-Tier Layout) ─────────────── */}
      <section id="why-aema" className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Header Tier */}
          <div className="space-y-4">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              01 / Principle
            </span>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <div className="lg:col-span-7">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6] leading-snug">
                  Memory is not just retrieval. It is the ability to know what to repeat, and what to avoid.
                </h2>
              </div>
              <div className="lg:col-span-5">
                <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  When an autonomous agent recalls a flawed or outdated solution, semantic matching reinforces the failure. AEMA turns experiential memory into an empirical feedback loop where past outcomes govern future retrieval.
                </p>
              </div>
            </div>
          </div>

          {/* Three Structural Columns with Hairline Vertical Rules */}
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#E5E5DF] dark:divide-[#232832] pt-4">
            {/* Column 1 */}
            <div className="py-6 md:py-0 md:pr-8 space-y-2.5">
              <div className="font-mono text-xs text-indigo-600 dark:text-indigo-400 font-semibold uppercase">
                1. Remember What Worked
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Bilateral Operational Units
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Rather than storing unstructured chat logs, memories are structured as 7-tuple operative lessons: situational triggers, affirmative strategies, and negative transfer hazard bounds.
              </p>
            </div>

            {/* Column 2 */}
            <div className="py-6 md:py-0 md:px-8 space-y-2.5">
              <div className="font-mono text-xs text-emerald-600 dark:text-emerald-400 font-semibold uppercase">
                2. Measure What to Trust
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Asymmetric EMA Updating
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Trust climbs cautiously on verified success (alpha = 0.85) but drops sharply upon failure (beta = 0.70). This asymmetry prevents deceptive experiences from masquerading as reliable advice.
              </p>
            </div>

            {/* Column 3 */}
            <div className="py-6 md:py-0 md:pl-8 space-y-2.5">
              <div className="font-mono text-xs text-rose-600 dark:text-rose-400 font-semibold uppercase">
                3. Isolate What Failed
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Theorem 1 Quarantine Bounds
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Persistently harmful experiences are provably isolated after exactly k* = 3 consecutive failures. Once quarantined, memories are automatically excluded from subsequent retrievals.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 02 / CAUSAL PIPELINE: HOW AEMA WORKS ──────────────────────────── */}
      <section id="how-it-works" className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="space-y-2">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              02 / Architecture
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
              The Causal Engineering Pipeline
            </h2>
            <p className="text-xs sm:text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl">
              How experiential memory moves from task inception to verified trust update.
            </p>
          </div>

          {/* Fine-line Pipeline Flow */}
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 font-mono text-xs">
            <div className="rounded-xl border p-4 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2">
              <span className="text-zinc-400 text-[11px] font-semibold">STAGE 01</span>
              <div className="font-semibold text-sm font-sans">Trigger</div>
              <p className="text-[11px] text-zinc-500 font-sans leading-relaxed">
                Agent receives task with specific operational context and constraints.
              </p>
            </div>

            <div className="rounded-xl border p-4 bg-white dark:bg-[#14171C] border-indigo-200 dark:border-indigo-900/60 space-y-2">
              <span className="text-indigo-600 dark:text-indigo-400 text-[11px] font-semibold">STAGE 02</span>
              <div className="font-semibold text-sm font-sans">Bi-Metric Retrieval</div>
              <p className="text-[11px] text-zinc-500 font-sans leading-relaxed">
                Rank = 0.70 × similarity + 0.30 × trust. Quarantined memories (St &lt; 0.35) are filtered out.
              </p>
            </div>

            <div className="rounded-xl border p-4 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2">
              <span className="text-zinc-400 text-[11px] font-semibold">STAGE 03</span>
              <div className="font-semibold text-sm font-sans">Context Injection</div>
              <p className="text-[11px] text-zinc-500 font-sans leading-relaxed">
                Inject verified strategy lesson and hazard warning into model prompt.
              </p>
            </div>

            <div className="rounded-xl border p-4 bg-white dark:bg-[#14171C] border-emerald-200 dark:border-emerald-900/60 space-y-2">
              <span className="text-emerald-600 dark:text-emerald-400 text-[11px] font-semibold">STAGE 04</span>
              <div className="font-semibold text-sm font-sans">Evaluation</div>
              <p className="text-[11px] text-zinc-500 font-sans leading-relaxed">
                Objective evaluator validates execution outcome against criteria.
              </p>
            </div>

            <div className="rounded-xl border p-4 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2">
              <span className="text-zinc-400 text-[11px] font-semibold">STAGE 05</span>
              <div className="font-semibold text-sm font-sans">Trust Update</div>
              <p className="text-[11px] text-zinc-500 font-sans leading-relaxed">
                Asymmetric EMA update. If failures reach k* = 3, quarantine triggers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 03 / PRODUCT: AEMA IN ACTION (Interactive Studio Console) ─────── */}
      <section className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-8">
          <div className="space-y-2">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              03 / Product
            </span>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
                  AEMA in Action
                </h2>
                <p className="text-xs sm:text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                  Experience the live 5-node stepper and observe how trust recalculates in real time.
                </p>
              </div>
              <StatusBadge status="Available Now" size="sm" />
            </div>
          </div>

          <div className="rounded-2xl border p-6 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-5">
            {previewError && (
              <div className="rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 p-4 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-semibold">
                    <AlertTriangle size={16} />
                    <span>Public Preview Execution Failed</span>
                  </div>
                  <button
                    onClick={() => setPreviewError(null)}
                    className="text-rose-500 hover:text-rose-700 dark:hover:text-rose-300 text-xs font-mono"
                  >
                    Dismiss
                  </button>
                </div>
                <p className="text-rose-800 dark:text-rose-300 font-mono text-[11px] break-all">
                  {previewError}
                </p>
              </div>
            )}
            <PromptConsole onRunTask={handleRunHeroPreview} isRunning={previewRunning} />
            {previewStage !== 'idle' && (
              <ExecutionStepper currentStage={previewStage} execution={previewExecution} />
            )}
          </div>
        </div>
      </section>

      {/* --- 04 / RESEARCH: THEOREM 1 & BENCHMARKS ---------------------------- */}
      <section id="research" className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="space-y-2">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              04 / Research Foundations
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
              Mathematical Proofs and Confirmatory Benchmark
            </h2>
            <p className="text-xs sm:text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl">
              Explore the Theorem 1 deterministic quarantine derivation with canonical S₀ = 0.75, and review our frozen N=30 confirmatory trial results.
            </p>
          </div>

          <TheoremSandbox />
          <BenchmarkMatrix />
        </div>
      </section>

      {/* ─── 05 / USE CASES: OPERATIONAL SCENARIOS ──────────────────────────── */}
      <section className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="space-y-2">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              05 / Operational Use Cases
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
              Where Reliable Memory Matters
            </h2>
            <p className="text-xs sm:text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl">
              Real agent workflows where standard semantic retrieval causes negative transfer.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="rounded-2xl border p-5 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <Code size={16} />
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Coding & Refactoring
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Eliminates recurring API deprecation traps, locking migrations, and token refresh race conditions across code repos.
              </p>
            </div>

            <div className="rounded-2xl border p-5 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <Compass size={16} />
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Fact Verification
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Prevents hallucination cascades when researching conflicting biomedical preprint claims by enforcing peer-reviewed verification.
              </p>
            </div>

            <div className="rounded-2xl border p-5 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <Database size={16} />
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Financial Time Series
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Avoids naive ordinary least squares on heavy-tailed revenue series by systematically applying Huber robust loss.
              </p>
            </div>

            <div className="rounded-2xl border p-5 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <GitBranch size={16} />
              </div>
              <h3 className="text-sm font-semibold text-[#1A1A1A] dark:text-[#F4F4F6]">
                Planning & DAG Dispatch
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Injects exponential backoff with full jitter and maintains token concurrency buffers for high-priority agent reflection cycles.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 06 / DEVELOPERS & ECOSYSTEM ───────────────────────────────────── */}
      <section id="developers" className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="space-y-2">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              06 / Developers
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
              Production SDKs and MCP Server
            </h2>
            <p className="text-xs sm:text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl">
              Integrate reliability-aware experiential memory in Python, TypeScript, Claude Desktop, or Cursor.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Python SDK */}
            <div className="rounded-2xl border p-6 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code size={16} className="text-indigo-600 dark:text-indigo-400" />
                  <h3 className="text-sm font-semibold">Python SDK (pip install aema)</h3>
                </div>
                <StatusBadge status="Available Now" size="sm" />
              </div>
              <pre className="p-4 rounded-xl text-xs font-mono bg-[#F8F8F6] dark:bg-[#1C2026] border border-[#E5E5DF] dark:border-[#232832] overflow-x-auto text-zinc-800 dark:text-zinc-200">
                {pythonSnippet}
              </pre>
            </div>

            {/* Model Context Protocol (MCP) */}
            <div className="rounded-2xl border p-6 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers size={16} className="text-indigo-600 dark:text-indigo-400" />
                  <h3 className="text-sm font-semibold">Model Context Protocol (MCP Server)</h3>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyToClipboard(mcpConfigCode, setCopiedMcp)}
                    className="flex items-center gap-1 text-[11px] font-mono text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors cursor-pointer"
                  >
                    {copiedMcp ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                    <span>{copiedMcp ? 'Copied' : 'Copy'}</span>
                  </button>
                  <StatusBadge status="Available Now" size="sm" />
                </div>
              </div>
              <pre className="p-4 rounded-xl text-xs font-mono bg-[#F8F8F6] dark:bg-[#1C2026] border border-[#E5E5DF] dark:border-[#232832] overflow-x-auto text-zinc-800 dark:text-zinc-200">
                {mcpConfigCode}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ─── 07 / PLATFORM ROADMAP (Honest Status Badging) ─────────────────── */}
      <section className="py-20 px-6 border-b border-[#E5E5DF] dark:border-[#232832]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="space-y-2">
            <span className="font-mono text-xs font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              07 / Roadmap
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
              Platform Roadmap & Capabilities
            </h2>
            <p className="text-xs sm:text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl">
              Transparent distinction between current releases, interactive demo features, and planned capabilities.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-2xl border p-6 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Open Source Core</h3>
                <StatusBadge status="Available Now" size="sm" />
              </div>
              <ul className="text-xs space-y-2 text-zinc-600 dark:text-zinc-400">
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                  <span>PyPI Package <code>aema 0.1.0</code></span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                  <span>npm Package <code>aema-memory 0.1.0</code></span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                  <span>Theorem 1 Deterministic Quarantine</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                  <span>PostgreSQL pgvector & SQLite stores</span>
                </li>
              </ul>
            </div>

            <div className="rounded-2xl border p-6 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">AEMA Cloud Console</h3>
                <StatusBadge status="Demo" size="sm" />
              </div>
              <ul className="text-xs space-y-2 text-zinc-600 dark:text-zinc-400">
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-500 shrink-0" />
                  <span>Interactive 5-node Execution Studio</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-500 shrink-0" />
                  <span>Supabase Authentication & RLS</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-500 shrink-0" />
                  <span>Memory Explorer & Quarantine Filters</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-500 shrink-0" />
                  <span>Live Sandbox with N=30 Benchmark seeds</span>
                </li>
              </ul>
            </div>

            <div className="rounded-2xl border p-6 bg-white dark:bg-[#14171C] border-[#E5E5DF] dark:border-[#232832] space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Enterprise Federation</h3>
                <StatusBadge status="Planned" size="sm" />
              </div>
              <ul className="text-xs space-y-2 text-zinc-600 dark:text-zinc-400">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 shrink-0" />
                  <span>Multi-tenant memory partitioning</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 shrink-0" />
                  <span>Distributed consensus across agent fleets</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 shrink-0" />
                  <span>Automated red-team adversarial injection</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 shrink-0" />
                  <span>SOC2 compliance logging</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <Footer />

      {/* Auth Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={() => navigate('/dashboard')}
        initialMode={authModalMode}
      />
    </div>
  )
}
