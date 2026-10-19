import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Shield,
  Database,
  Activity,
  Award,
  CheckCircle2,
  Clock,
  Menu,
  ExternalLink,
  AlertTriangle,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Sidebar, { TabType } from '../components/Sidebar'
import MemoryExplorer from '../components/MemoryExplorer'
import PromptConsole from '../components/PromptConsole'
import ExecutionStepper from '../components/ExecutionStepper'
import ContextInspector from '../components/ContextInspector'
import TheoremSandbox from '../components/TheoremSandbox'
import BenchmarkMatrix from '../components/BenchmarkMatrix'
import AuthModal from '../components/AuthModal'
import {
  fetchExperiences,
  createExperience,
  executeAgentTask,
  fetchExecutions,
  fetchTelemetry,
  clearExecutionsApi,
  getTelemetryMetrics,
  INITIAL_EXPERIENCES,
  ALPHA_SUCCESS,
  BETA_FAILURE,
  QUARANTINE_THRESHOLD,
  CONSECUTIVE_FAILURES_BOUND,
} from '../services/api'
import type { Experience, TaskExecution, TaskDomain } from '../types'

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const isDemo = searchParams.get('demo') === 'true'
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [experiences, setExperiences] = useState<Experience[]>([])
  const [metrics, setMetrics] = useState(getTelemetryMetrics())
  const [recentExecutions, setRecentExecutions] = useState<TaskExecution[]>([])
  const [selectedExecution, setSelectedExecution] = useState<TaskExecution | null>(null)

  // Execution Studio States
  const [isExecuting, setIsExecuting] = useState(false)
  const [currentStage, setCurrentStage] = useState<'retrieval' | 'execution' | 'evaluation' | 'reflection' | 'trust_update' | 'idle' | 'complete'>('idle')
  const [activeExecution, setActiveExecution] = useState<TaskExecution | null>(null)
  const [executionError, setExecutionError] = useState<string | null>(null)

  // Auth modal triggered from demo banner
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  // Route guard: if not loading and neither authenticated nor in demo mode, redirect
  useEffect(() => {
    if (!loading && !user && !isDemo) {
      navigate('/', { replace: true })
    }
  }, [user, loading, isDemo, navigate])

  // Load real persistent experiences, telemetry, and execution runs from backend
  useEffect(() => {
    fetchExperiences().then((exps) => {
      setExperiences(exps.length > 0 ? exps : INITIAL_EXPERIENCES)
    })
    fetchTelemetry().then((m) => {
      setMetrics(m)
    })
    fetchExecutions(15).then((runs) => {
      if (runs.length > 0) {
        setRecentExecutions(runs)
        setSelectedExecution(runs[0])
      }
    })
  }, [])

  const handleRunTask = async (params: {
    prompt: string
    domain: TaskDomain
    memoryEnabled: boolean
    provider?: string
    apiKey?: string
    simulateFailure?: boolean
  }) => {
    setIsExecuting(true)
    setCurrentStage('retrieval')
    setExecutionError(null)

    try {
      const exec = await executeAgentTask({
        taskInput: params.prompt,
        taskDomain: params.domain,
        memoryEnabled: params.memoryEnabled,
        provider: params.provider,
        apiKey: params.apiKey,
        simulateFailure: params.simulateFailure,
        isExplicitDemo: isDemo,
        onStageChange: (stage) => setCurrentStage(stage),
      })

      setActiveExecution(exec)
      setSelectedExecution(exec)
      setRecentExecutions((prev) => [exec, ...prev.filter((r) => r.id !== exec.id).slice(0, 14)])
      // Refresh experiences to reflect any real trust update or quarantine
      const updatedExps = await fetchExperiences()
      setExperiences(updatedExps)
      const updatedMetrics = await fetchTelemetry()
      setMetrics(updatedMetrics)
      setCurrentStage('complete')
    } catch (err: any) {
      console.error('Task execution failed:', err)
      setExecutionError(err?.message || 'Execution failed due to backend error.')
      setCurrentStage('idle')
    } finally {
      setIsExecuting(false)
    }
  }

  const handleAddExperience = async (exp: Partial<Experience>) => {
    const created = await createExperience(exp)
    setExperiences((prev) => [created, ...prev])
    setMetrics(getTelemetryMetrics())
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FBFBFA] dark:bg-[#0C0E14]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-zinc-500">Initializing AEMA Console...</span>
        </div>
      </div>
    )
  }

  if (!user && !isDemo) return null

  return (
    <div className="min-h-screen flex bg-[#FBFBFA] dark:bg-[#0C0E14] text-[#18181B] dark:text-[#F4F4F6] transition-colors">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          isDemo={isDemo}
          onExitDemo={() => {
            if (user) {
              setSearchParams({}, { replace: true })
            } else {
              navigate('/')
            }
          }}
          onOpenAuth={() => setIsAuthModalOpen(true)}
        />
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileSidebarOpen(false)} />
          <div className="relative z-10 w-64">
            <Sidebar
              activeTab={activeTab}
              onSelectTab={(tab) => {
                setActiveTab(tab)
                setMobileSidebarOpen(false)
              }}
              isDemo={isDemo}
              onExitDemo={() => {
                setMobileSidebarOpen(false)
                if (user) {
                  setSearchParams({}, { replace: true })
                } else {
                  navigate('/')
                }
              }}
              onOpenAuth={() => {
                setMobileSidebarOpen(false)
                setIsAuthModalOpen(true)
              }}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Top Header Rail */}
        <header className="h-14 border-b px-6 flex items-center justify-between shrink-0 bg-white/70 dark:bg-[#131722]/70 backdrop-blur-md border-[#E6E6E1] dark:border-[#252B3B]">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-lg border border-[#E6E6E1] dark:border-[#252B3B] text-zinc-500"
            >
              <Menu size={16} />
            </button>
            <div className="font-semibold text-xs capitalize tracking-wide flex items-center gap-2">
              <span className="text-zinc-400 font-mono">Workspace /</span>
              <span>{activeTab === 'runs' ? 'Runs & Traces' : activeTab}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isDemo && (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                Demo Sandbox (Simulated)
              </span>
            )}
            <span className="font-mono text-xs text-zinc-400">
              AEMA 0.1.0
            </span>
          </div>
        </header>

        {/* Tab Viewport */}
        <main className="p-6 flex-1 max-w-7xl w-full mx-auto space-y-6">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6 anim-fade-in">
              {/* Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-xl border p-4 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]">
                  <div className="flex items-center justify-between text-zinc-400 text-xs font-mono mb-2">
                    <span>MEAN TRUST SCORE</span>
                    <Shield size={16} className="text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#18181B] dark:text-[#F4F4F6]">
                    {(metrics.meanTrustScore * 100).toFixed(1)}%
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-1">
                    Asymmetric EMA St across {experiences.length} memories
                  </div>
                </div>

                <div className="rounded-xl border p-4 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]">
                  <div className="flex items-center justify-between text-zinc-400 text-xs font-mono mb-2">
                    <span>ACTIVE EXPERIENCES</span>
                    <Database size={16} className="text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                    {metrics.activeMemories}
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-1">
                    {metrics.quarantinedMemories} quarantined under Theorem 1
                  </div>
                </div>

                <div className="rounded-xl border p-4 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]">
                  <div className="flex items-center justify-between text-zinc-400 text-xs font-mono mb-2">
                    <span>MEMORY HIT RATE</span>
                    <Activity size={16} className="text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#18181B] dark:text-[#F4F4F6]">
                    {metrics.memoryHitRate}%
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-1">
                    Similarity &gt; 0.70 with valid trust
                  </div>
                </div>

                <div className="rounded-xl border p-4 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]">
                  <div className="flex items-center justify-between text-zinc-400 text-xs font-mono mb-2">
                    <span>BENCHMARK RESILIENCE</span>
                    <Award size={16} className="text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                    {metrics.benchmarkNegativeTransferReduction ?? metrics.negativeTransferReduction ?? 100}%
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-1">
                    Fixed Benchmark: {metrics.benchmarkSource || 'Phase 8 v2 McNemar test (p=1.192e-7)'}
                  </div>
                </div>
              </div>

              {/* Quick Launch & Recent Runs */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                      Quick Execution Launcher
                    </h3>
                    <button
                      onClick={() => setActiveTab('studio')}
                      className="text-xs font-mono text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      Open Full Studio →
                    </button>
                  </div>
                  {executionError && (
                    <div className="rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 p-4 text-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-semibold">
                          <AlertTriangle size={16} />
                          <span>AEMA Backend Execution Failed (Integrity Policy: No Mock Fallback)</span>
                        </div>
                        <button
                          onClick={() => setExecutionError(null)}
                          className="text-rose-500 hover:text-rose-700 dark:hover:text-rose-300 text-xs font-mono"
                        >
                          Dismiss
                        </button>
                      </div>
                      <p className="text-rose-800 dark:text-rose-300 font-mono text-[11px] break-all">
                        {executionError}
                      </p>
                      <div className="text-[11px] text-rose-600 dark:text-rose-400">
                        Live execution integrity enforced: Failed backend requests are never silently simulated as successful runs.
                      </div>
                    </div>
                  )}
                  <PromptConsole onRunTask={handleRunTask} isRunning={isExecuting} />
                  {currentStage !== 'idle' && (
                    <ExecutionStepper currentStage={currentStage} execution={activeExecution} />
                  )}
                </div>

                {/* Right: Operational Status & Ecosystem */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                    Engine Status
                  </h3>
                  <div className="rounded-2xl border p-4 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] space-y-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">Persistence:</span>
                      <span className="font-mono font-semibold">PostgreSQL (pgvector)</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">Quarantine Bound:</span>
                      <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
                        k* = {CONSECUTIVE_FAILURES_BOUND} failures
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">Success Momentum (α):</span>
                      <span className="font-mono font-semibold">{ALPHA_SUCCESS}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">Failure Penalty (β):</span>
                      <span className="font-mono font-semibold">{BETA_FAILURE}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">Isolation Cutoff (θ):</span>
                      <span className="font-mono font-semibold">{QUARANTINE_THRESHOLD}</span>
                    </div>
                    <div className="pt-2 border-t border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">PyPI SDK:</span>
                      <a
                        href="https://pypi.org/project/aema/0.1.0/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                      >
                        <span>aema 0.1.0</span>
                        <ExternalLink size={11} />
                      </a>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500 font-mono">npm & MCP:</span>
                      <a
                        href="https://www.npmjs.com/package/aema-memory"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                      >
                        <span>aema-memory 0.1.0</span>
                        <ExternalLink size={11} />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: STUDIO */}
          {activeTab === 'studio' && (
            <div className="space-y-6 anim-fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                    Execution Studio
                  </h2>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    Visibly track: Retrieve → Execute → Evaluate → Reflect → Trust Update.
                  </p>
                </div>
              </div>

              {executionError && (
                <div className="rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 p-4 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400 font-semibold">
                      <AlertTriangle size={16} />
                      <span>AEMA Backend Execution Failed (Integrity Policy: No Mock Fallback)</span>
                    </div>
                    <button
                      onClick={() => setExecutionError(null)}
                      className="text-rose-500 hover:text-rose-700 dark:hover:text-rose-300 text-xs font-mono"
                    >
                      Dismiss
                    </button>
                  </div>
                  <p className="text-rose-800 dark:text-rose-300 font-mono text-[11px] break-all">
                    {executionError}
                  </p>
                  <div className="text-[11px] text-rose-600 dark:text-rose-400">
                    Live execution integrity enforced: Failed backend requests are never silently simulated as successful runs.
                  </div>
                </div>
              )}

              <PromptConsole onRunTask={handleRunTask} isRunning={isExecuting} />
              <ExecutionStepper currentStage={currentStage} execution={activeExecution} />
              <ContextInspector execution={activeExecution} />
            </div>
          )}

          {/* TAB 3: MEMORY */}
          {activeTab === 'memory' && (
            <div className="space-y-6 anim-fade-in">
              <div>
                <h2 className="text-base font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                  Experiential Memory Index
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  7-tuple operational memories containing affirmative lessons and negative transfer pitfall bounds.
                </p>
              </div>

              <MemoryExplorer
                experiences={experiences}
                onRefresh={async () => {
                  const exps = await fetchExperiences()
                  setExperiences(exps)
                }}
                onAddExperience={handleAddExperience}
              />
            </div>
          )}

          {/* TAB 4: RUNS & TRACES */}
          {activeTab === 'runs' && (
            <div className="space-y-6 anim-fade-in">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                    Execution Runs & Traces
                  </h2>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    Inspect historical agent trajectories, retrieved context augmentations, and trust updates.
                  </p>
                </div>

                {recentExecutions.length > 0 && (
                  <button
                    onClick={async () => {
                      const adminKey = prompt(
                        'Enter ADMIN_API_KEY to authorize clearing history (or leave blank if VITE_ADMIN_API_KEY is configured):'
                      )
                      if (adminKey === null) return // User cancelled prompt
                      const res = await clearExecutionsApi(adminKey.trim() || undefined)
                      if (res.success) {
                        setRecentExecutions([])
                        setSelectedExecution(null)
                        const updatedMetrics = await fetchTelemetry()
                        setMetrics(updatedMetrics)
                      } else {
                        alert(`Authorization Failed: ${res.error || 'Invalid Admin Key'}`)
                      }
                    }}
                    className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono text-zinc-500 hover:text-rose-600 hover:border-rose-300 dark:hover:border-rose-800 border-zinc-200 dark:border-zinc-800 transition-colors cursor-pointer"
                  >
                    <span>Clear All History</span>
                  </button>
                )}
              </div>

              {recentExecutions.length === 0 ? (
                <div className="rounded-xl border p-12 text-center bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]">
                  <Clock size={32} className="mx-auto text-zinc-300 dark:text-zinc-600 mb-3" />
                  <h3 className="text-sm font-semibold">No execution runs in this session</h3>
                  <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
                    Execute a prompt in the Studio or Overview launcher to record live execution traces.
                  </p>
                  <button
                    onClick={() => setActiveTab('studio')}
                    className="mt-4 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                  >
                    Launch a Task
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left List of Runs */}
                  <div className="lg:col-span-1 space-y-2">
                    {recentExecutions.map((run) => (
                      <div
                        key={run.id}
                        onClick={() => setSelectedExecution(run)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          selectedExecution?.id === run.id
                            ? 'border-indigo-600 bg-indigo-50/30 dark:bg-indigo-950/20'
                            : 'bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] hover:border-zinc-400'
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-mono text-[11px] font-semibold">{run.id}</span>
                          <span
                            className={`font-mono text-[10px] font-bold uppercase ${
                              run.outcomeQuality === 'positive'
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-rose-600 dark:text-rose-400'
                            }`}
                          >
                            {run.outcomeQuality || 'COMPLETED'}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-700 dark:text-zinc-300 line-clamp-1">
                          {run.taskInput}
                        </p>
                        <div className="mt-2 text-[10px] font-mono text-zinc-400 flex items-center justify-between">
                          <span>{run.taskDomain}</span>
                          <span>{run.latencyMs}ms · {run.tokensUsed} tokens</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Right Inspector */}
                  <div className="lg:col-span-2">
                    <ContextInspector execution={selectedExecution} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: RESEARCH */}
          {activeTab === 'research' && (
            <div className="space-y-6 anim-fade-in">
              <div>
                <h2 className="text-base font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                  Research Proofs & Theory Sandbox
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  Theorem 1 deterministic quarantine bounds and protocol-frozen confirmatory benchmarks.
                </p>
              </div>

              <TheoremSandbox />
              <BenchmarkMatrix />
            </div>
          )}

          {/* TAB 6: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="space-y-6 anim-fade-in">
              <div>
                <h2 className="text-base font-semibold text-[#18181B] dark:text-[#F4F4F6]">
                  System Settings & Deployment
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  Inspect persistent storage configurations, backend endpoints, and AEMA hyperparameters.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Supabase Status */}
                <div className="rounded-2xl border p-5 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] space-y-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-500" />
                    <h3 className="text-xs font-mono font-semibold uppercase tracking-wider">
                      Supabase Cloud Storage
                    </h3>
                  </div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-400 space-y-1 font-mono">
                    <div>URL: <code className="text-[#18181B] dark:text-[#F4F4F6]">{import.meta.env.VITE_SUPABASE_URL || 'https://fuwtdoxzfmghdxgferyf.supabase.co'}</code></div>
                    <div>Auth Provider: Email + Password & Google OAuth</div>
                    <div>RLS Engine: Enabled</div>
                  </div>
                </div>

                {/* Local Engine */}
                <div className="rounded-2xl border p-5 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] space-y-3">
                  <div className="flex items-center gap-2">
                    <Database size={16} className="text-indigo-600 dark:text-indigo-400" />
                    <h3 className="text-xs font-mono font-semibold uppercase tracking-wider">
                      PostgreSQL / pgvector
                    </h3>
                  </div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-400 space-y-1 font-mono">
                    <div>Vector Dimension: 384 (all-MiniLM-L6-v2)</div>
                    <div>Index Algorithm: HNSW (m=16, ef_construction=64)</div>
                    <div>Distance Metric: Cosine (&lt;=&gt;)</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Auth Modal for Switching from Demo */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={() => {
          setSearchParams({})
          setIsAuthModalOpen(false)
        }}
        initialMode="signup"
      />
    </div>
  )
}
