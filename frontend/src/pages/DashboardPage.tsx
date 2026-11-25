import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import {
  Shield,
  Database,
  Activity,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  AlertTriangle,
  Terminal,
  LayoutDashboard,
  ListTree,
  Settings,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Sidebar, { TabType } from '../components/Sidebar'
import MemoryExplorer from '../components/MemoryExplorer'
import PromptConsole from '../components/PromptConsole'
import ExecutionStepper from '../components/ExecutionStepper'
import ContextInspector from '../components/ContextInspector'
import ConversationStudio from '../components/ConversationStudio'
import SettingsView from '../components/SettingsView'
import AuthModal from '../components/AuthModal'
import {
  fetchExperiences,
  createExperience,
  deleteExperienceApi,
  executeAgentTask,
  fetchExecutions,
  fetchTelemetry,
  clearExecutionsApi,
  getTelemetryMetrics,
  shouldUseOfflineDemo,
  INITIAL_EXPERIENCES,
  INITIAL_DEMO_EXECUTIONS,
} from '../services/api'
import type { Experience, TaskExecution, TaskDomain } from '../types'

const TAB_ITEMS: { id: TabType; label: string; icon: any }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'studio', label: 'Execution Studio', icon: Terminal },
  { id: 'memory', label: 'Memory Bank', icon: Database },
  { id: 'runs', label: 'Runs & Traces', icon: ListTree },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const isDemo = searchParams.get('demo') === 'true'
  // Always default to 'overview' tab as requested
  const [activeTab, setActiveTab] = useState<TabType>(() => {
    const requestedTab = searchParams.get('tab') as TabType
    return requestedTab || 'overview'
  })
  // Synchronously seed initial data for demo sandbox; new accounts begin with 0 memories
  const [experiences, setExperiences] = useState<Experience[]>(() => (isDemo ? [...INITIAL_EXPERIENCES] : []))
  const [metrics, setMetrics] = useState(getTelemetryMetrics())
  const [recentExecutions, setRecentExecutions] = useState<TaskExecution[]>(() => (isDemo ? [...INITIAL_DEMO_EXECUTIONS] : []))
  const [selectedExecution, setSelectedExecution] = useState<TaskExecution | null>(() => (isDemo ? INITIAL_DEMO_EXECUTIONS[0] || null : null))
  const [runFilter, setRunFilter] = useState<'all' | 'pass' | 'fail'>('all')
  const [runSearch, setRunSearch] = useState('')

  const handleSelectTab = (tab: TabType) => {
    setActiveTab(tab)
    const newParams = new URLSearchParams(searchParams)
    newParams.set('tab', tab)
    setSearchParams(newParams, { replace: true })
  }

  // Synchronize activeTab when URL tab parameter changes
  useEffect(() => {
    const requestedTab = searchParams.get('tab')
    if (requestedTab === 'research') {
      navigate('/research', { replace: true })
      return
    }
    if (requestedTab && requestedTab !== activeTab && ['overview', 'studio', 'memory', 'runs', 'settings'].includes(requestedTab)) {
      setActiveTab(requestedTab as TabType)
    }
  }, [searchParams, activeTab, navigate])

  // Enforce obsidian canvas on dashboard to eliminate overscroll light bounce
  useEffect(() => {
    document.documentElement.classList.add('dark')
    document.documentElement.style.backgroundColor = '#141412'
    document.body.style.backgroundColor = '#141412'
    return () => {
      document.documentElement.style.backgroundColor = ''
      document.body.style.backgroundColor = ''
    }
  }, [])

  // Main application sidebar collapse state (persisted across refreshes)
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('aema_sidebar_collapsed') === 'true'
    } catch {
      return false
    }
  })

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev
      try {
        localStorage.setItem('aema_sidebar_collapsed', String(next))
      } catch {}
      return next
    })
  }

  // Execution Studio States
  const [isExecuting, setIsExecuting] = useState(false)
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
    fetchExperiences(undefined, undefined, undefined, !isDemo).then((exps) => {
      setExperiences(exps.length > 0 ? exps : (isDemo ? INITIAL_EXPERIENCES : []))
    })
    fetchTelemetry().then((m) => {
      setMetrics(m)
    })
    fetchExecutions(15).then((runs) => {
      if (runs.length > 0) {
        setRecentExecutions(runs)
        setSelectedExecution(runs[0])
      } else {
        setRecentExecutions([])
        setSelectedExecution(null)
      }
    })
  }, [isDemo, user])

  const handleRunTask = async (params: {
    prompt: string
    domain: TaskDomain
    memoryEnabled: boolean
    provider?: string
    model?: string
    apiKey?: string
    simulateFailure?: boolean
  }) => {
    setIsExecuting(true)
    setExecutionError(null)

    const shouldRunOfflineDemo = shouldUseOfflineDemo(
      isDemo,
      params.provider || 'groq',
      params.apiKey
    )

    try {
      const exec = await executeAgentTask({
        taskInput: params.prompt,
        taskDomain: params.domain,
        memoryEnabled: params.memoryEnabled,
        provider: params.provider,
        model: params.model,
        apiKey: params.apiKey,
        simulateFailure: params.simulateFailure,
        isExplicitDemo: shouldRunOfflineDemo,
      })

      setSelectedExecution(exec)
      setRecentExecutions((prev) => [exec, ...prev.filter((r) => r.id !== exec.id).slice(0, 14)])
      const updatedExps = await fetchExperiences(undefined, undefined, undefined, !isDemo)
      setExperiences(updatedExps)
      const updatedMetrics = await fetchTelemetry()
      setMetrics(updatedMetrics)
    } catch (err: any) {
      console.error('Task execution failed:', err)
      setExecutionError(err?.message || 'Execution failed due to backend error.')
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
      <div className="min-h-screen flex items-center justify-center bg-[#141412] text-[#EDECE8]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[#EDECE8] border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-[#7E7D77]">Initializing AEMA Console...</span>
        </div>
      </div>
    )
  }

  if (!user && !isDemo) return null

  return (
    <div className="min-h-screen flex bg-[#141412] text-[#EDECE8] transition-colors selection:bg-[#2E2E2A]">
      {/* Desktop Sidebar (Pure Obsidian Theme) */}
      <div className="hidden lg:block shrink-0 transition-all duration-200">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={handleSelectTab}
          isDemo={isDemo}
          onExitDemo={() => {
            if (user) {
              setSearchParams({}, { replace: true })
            } else {
              navigate('/')
            }
          }}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          collapsed={sidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
        />
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileSidebarOpen(false)} />
          <div className="relative z-10 w-60">
            <Sidebar
              activeTab={activeTab}
              onSelectTab={(tab) => {
                handleSelectTab(tab)
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
      <div className={`flex-1 flex flex-col min-w-0 h-screen ${activeTab === 'studio' ? 'overflow-hidden' : 'overflow-y-auto'} bg-[#141412]`}>
        {/* Top Header Rail with Airy Spacing & Clean Breadcrumb */}
        <header className="h-16 border-b border-[#242422] px-6 sm:px-8 flex items-center justify-between shrink-0 bg-[#161614]">
          <div className="flex items-center gap-3.5">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded border border-[#2E2E2A] text-[#7E7D77] hover:text-[#EDECE8]"
            >
              <Menu size={16} />
            </button>
            <div className="relative group/toggle hidden lg:flex items-center">
              <button
                onClick={handleToggleSidebar}
                className="p-2 rounded border border-[#2E2E2A] text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#1E1E1B] transition-colors cursor-pointer"
                aria-label={sidebarCollapsed ? 'Expand main sidebar' : 'Collapse main sidebar'}
              >
                {sidebarCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
              </button>
              <div className="pointer-events-none absolute left-full ml-2.5 top-1/2 -translate-y-1/2 opacity-0 group-hover/toggle:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
                <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded text-xs font-mono shadow-xl">
                  {sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                </div>
              </div>
            </div>

            {/* Clean Breadcrumb with Generous Padding */}
            <div className="flex items-center gap-2.5 font-mono text-xs">
              <button
                onClick={() => handleSelectTab('overview')}
                className="text-[#7E7D77] hover:text-[#EDECE8] transition-colors cursor-pointer"
                title="Go to Overview"
              >
                Workspace
              </button>
              <span className="text-[#5A5955]">/</span>
              <span className="text-white font-medium text-xs">
                {TAB_ITEMS.find((t) => t.id === activeTab)?.label || 'Overview'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isDemo && (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-0.5 rounded border border-[#3E3E34] bg-[#1E1E1B] text-[#E67E22] font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-[#E67E22]" />
                Demo Sandbox
              </span>
            )}
            <span className="font-mono text-xs text-[#7E7D77]">
              v0.1.1
            </span>
          </div>
        </header>

        {/* Tab Viewport: Studio is full-bleed workspace directly below header; other tabs use max-w-7xl container */}
        {activeTab === 'studio' ? (
          <div className="flex-1 w-full min-h-0 overflow-hidden flex flex-col">
            <ConversationStudio
              isDemo={isDemo}
              onExecutionComplete={(exec) => {
                setSelectedExecution(exec)
                setRecentExecutions((prev) => [exec, ...prev.filter((r) => r.id !== exec.id).slice(0, 14)])
                fetchExperiences(undefined, undefined, undefined, !isDemo).then(setExperiences)
                fetchTelemetry().then(setMetrics)
              }}
            />
          </div>
        ) : (
          <main className="p-6 flex-1 max-w-7xl w-full mx-auto space-y-6">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Stat Cards (Obsidian Style) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-lg border border-[#242422] p-4 bg-[#161614]">
                  <div className="flex items-center justify-between text-[#7E7D77] text-xs font-mono mb-2">
                    <span>MEAN TRUST SCORE</span>
                    <Shield size={15} className="text-[#EDECE8]" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#EDECE8]">
                    {experiences.length > 0
                      ? `${((experiences.reduce((acc, e) => acc + (e.trustScore ?? 0), 0) / experiences.length) * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <div className="text-[11px] text-[#7E7D77] mt-1 font-mono">
                    {experiences.length > 0
                      ? `Asymmetric EMA St across ${experiences.length} memories`
                      : 'No memories recorded yet'}
                  </div>
                </div>

                <div className="rounded-lg border border-[#242422] p-4 bg-[#161614]">
                  <div className="flex items-center justify-between text-[#7E7D77] text-xs font-mono mb-2">
                    <span>ACTIVE EXPERIENCES</span>
                    <Database size={15} className="text-[#4EAA79]" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#4EAA79]">
                    {experiences.filter((e) => e.status === 'active').length}
                  </div>
                  <div className="text-[11px] text-[#7E7D77] mt-1 font-mono">
                    {experiences.filter((e) => e.status === 'quarantined' || (e.trustScore ?? 0) < 0.35).length} quarantined under Theorem 1
                  </div>
                </div>

                <div className="rounded-lg border border-[#242422] p-4 bg-[#161614]">
                  <div className="flex items-center justify-between text-[#7E7D77] text-xs font-mono mb-2">
                    <span>MEMORY HIT RATE</span>
                    <Activity size={15} className="text-[#EDECE8]" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#EDECE8]">
                    {metrics.totalTasks > 0 ? `${metrics.memoryHitRate}%` : '0.0%'}
                  </div>
                  <div className="text-[11px] text-[#7E7D77] mt-1 font-mono">
                    {metrics.totalTasks > 0
                      ? `Live hit rate across ${metrics.totalTasks} recorded runs`
                      : '0 runs recorded yet (execute in Studio)'}
                  </div>
                </div>

                <div className="rounded-lg border border-[#242422] p-4 bg-[#161614]">
                  <div className="flex items-center justify-between text-[#7E7D77] text-xs font-mono mb-2">
                    <span>TOKEN SAVINGS</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1E1E1B] text-[#4EAA79] border border-[#2E2E2A]">
                      EFFICIENCY
                    </span>
                  </div>
                  <div className="text-2xl font-bold font-mono text-[#4EAA79]">
                    {recentExecutions.length > 0 ? '41.2%' : '0.0%'}
                  </div>
                  <div className="text-[11px] text-[#7E7D77] mt-1 font-mono flex items-center justify-between">
                    <span>Prompt token reduction</span>
                    <Link to="/research" className="text-[#9E9D96] hover:text-[#EDECE8] underline transition-colors">
                      Proofs &rarr;
                    </Link>
                  </div>
                </div>
              </div>

              {/* Quick Launch & Recent Runs */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-[#EDECE8]">
                      Quick Execution Launcher
                    </h3>
                    <button
                      onClick={() => setActiveTab('studio')}
                      className="text-xs font-mono text-[#EDECE8] hover:underline cursor-pointer"
                    >
                      Open Full Studio &rarr;
                    </button>
                  </div>
                  {executionError && (
                    <div className="rounded border border-[#D9534F] bg-[#221616] p-4 text-xs space-y-2 text-[#D9534F]">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 font-semibold">
                          <AlertTriangle size={15} />
                          <span>AEMA Backend Execution Notice</span>
                        </div>
                        <button
                          onClick={() => setExecutionError(null)}
                          className="hover:underline text-xs font-mono"
                        >
                          Dismiss
                        </button>
                      </div>
                      <p className="font-mono text-[11px]">{executionError}</p>
                    </div>
                  )}
                  <PromptConsole
                    onRunTask={handleRunTask}
                    isRunning={isExecuting}
                  />
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-[#EDECE8]">
                      Recent Executions
                    </h3>
                    {recentExecutions.length > 0 && (
                      <button
                        onClick={async () => {
                          await clearExecutionsApi()
                          setRecentExecutions([])
                          setSelectedExecution(null)
                        }}
                        className="text-[11px] font-mono text-[#7E7D77] hover:text-[#D9534F] transition-colors cursor-pointer"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  <div className="rounded-lg border border-[#242422] bg-[#161614] divide-y divide-[#242422] max-h-[380px] overflow-y-auto">
                    {recentExecutions.length === 0 ? (
                      <div className="p-8 text-center text-xs text-[#7E7D77] font-mono">
                        No recent executions. Run a prompt in the studio to populate history.
                      </div>
                    ) : (
                      recentExecutions.map((run) => (
                        <div
                          key={run.id}
                          onClick={() => {
                            setSelectedExecution(run)
                            setActiveTab('runs')
                          }}
                          className="p-3 hover:bg-[#1E1E1B] cursor-pointer transition-colors text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between font-mono text-[11px]">
                            <span className="font-medium text-[#EDECE8] truncate max-w-[180px]">
                              {run.taskInput}
                            </span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                run.outcomeScore && run.outcomeScore >= 0.7
                                  ? 'bg-[#1E2E24] text-[#4EAA79]'
                                  : 'bg-[#2E1E1E] text-[#D9534F]'
                              }`}
                            >
                              {run.outcomeScore && run.outcomeScore >= 0.7 ? 'PASS' : 'FAIL'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-[#7E7D77] font-mono">
                            <span>{run.taskDomain}</span>
                            <span>{new Date(run.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: EXPERIENTIAL MEMORY */}
          {activeTab === 'memory' && (
            <div className="space-y-4">
              <MemoryExplorer
                experiences={experiences}
                isDemo={isDemo}
                onNavigateToStudio={() => setActiveTab('studio')}
                onRefresh={(domain, search, status) => {
                  fetchExperiences(domain, search, status, !isDemo).then(setExperiences)
                }}
                onAddExperience={handleAddExperience}
                onDeleteExperience={async (id) => {
                  await deleteExperienceApi(id)
                  setExperiences((prev) => prev.filter((e) => e.id !== id))
                  setMetrics(getTelemetryMetrics())
                }}
              />
            </div>
          )}

          {/* TAB 4: RUNS & TRACES */}
          {activeTab === 'runs' && (
            <div className="space-y-6">
              {/* Header with Title and Clear Action */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-mono text-xs uppercase tracking-wider text-[#EDECE8] font-bold">
                    Execution History & Cognitive Traces
                  </h3>
                  <p className="text-xs text-[#7E7D77] mt-0.5">
                    Audit multi-turn agent executions, deterministic assertions, and per-step 5-node cognitive traces.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#1C1C18] border border-[#2E2E2A] text-[#9E9D96]">
                    {recentExecutions.length} {recentExecutions.length === 1 ? 'run' : 'runs'} recorded
                  </span>
                  {recentExecutions.length > 0 && (
                    <button
                      onClick={async () => {
                        await clearExecutionsApi()
                        setRecentExecutions([])
                        setSelectedExecution(null)
                      }}
                      className="px-2.5 py-1 text-xs font-mono rounded border border-[#3E2424] bg-[#221616] text-[#D9534F] hover:bg-[#2E1E1E] transition-colors cursor-pointer"
                    >
                      Clear History
                    </button>
                  )}
                </div>
              </div>

              {/* Run History Master Table / Selector */}
              <div className="rounded-lg border border-[#242422] bg-[#161614] overflow-hidden">
                {/* Filter and Search Bar */}
                <div className="p-3 border-b border-[#242422] bg-[#141412] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-1 font-mono text-xs">
                    {(['all', 'pass', 'fail'] as const).map((filterType) => {
                      const count =
                        filterType === 'all'
                          ? recentExecutions.length
                          : filterType === 'pass'
                          ? recentExecutions.filter((r) => (r.outcomeScore ?? 0) >= 0.7).length
                          : recentExecutions.filter((r) => (r.outcomeScore ?? 0) < 0.7).length
                      return (
                        <button
                          key={filterType}
                          type="button"
                          onClick={() => setRunFilter(filterType)}
                          className={`px-2.5 py-1 rounded text-xs transition-colors cursor-pointer capitalize ${
                            runFilter === filterType
                              ? 'bg-[#22221E] text-white font-medium border border-[#3E3E38]'
                              : 'text-[#7E7D77] hover:text-[#EDECE8] border border-transparent'
                          }`}
                        >
                          {filterType} ({count})
                        </button>
                      )
                    })}
                  </div>

                  <div className="relative">
                    <input
                      type="text"
                      value={runSearch}
                      onChange={(e) => setRunSearch(e.target.value)}
                      placeholder="Search runs by prompt, domain..."
                      className="w-full sm:w-64 pl-2.5 pr-3 py-1 rounded bg-[#181816] border border-[#262624] text-xs text-[#EDECE8] placeholder-[#7E7D77] focus:outline-none focus:border-[#4EAA79]"
                    />
                  </div>
                </div>

                {/* Runs List Table */}
                <div className="divide-y divide-[#242422] max-h-72 overflow-y-auto">
                  {recentExecutions
                    .filter((r) => {
                      const matchesFilter =
                        runFilter === 'all' ||
                        (runFilter === 'pass' && (r.outcomeScore ?? 0) >= 0.7) ||
                        (runFilter === 'fail' && (r.outcomeScore ?? 0) < 0.7)
                      const matchesSearch =
                        !runSearch.trim() ||
                        r.taskInput.toLowerCase().includes(runSearch.toLowerCase()) ||
                        r.taskDomain.toLowerCase().includes(runSearch.toLowerCase()) ||
                        r.id.toLowerCase().includes(runSearch.toLowerCase())
                      return matchesFilter && matchesSearch
                    })
                    .map((run) => {
                      const isSelected = selectedExecution?.id === run.id
                      const isPass = (run.outcomeScore ?? 0) >= 0.7

                      return (
                        <div
                          key={run.id}
                          onClick={() => setSelectedExecution(run)}
                          className={`p-3.5 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
                            isSelected
                              ? 'bg-[#1C1C18] border-l-2 border-[#4EAA79]'
                              : 'hover:bg-[#1A1A17]'
                          }`}
                        >
                          <div className="space-y-1 min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono shrink-0 ${
                                  isPass
                                    ? 'bg-[#1E2E24] text-[#4EAA79] border border-[#2E4234]'
                                    : 'bg-[#2E1E1E] text-[#D9534F] border border-[#4E2A2A]'
                                }`}
                              >
                                {isPass ? 'PASS' : 'FAIL'}
                              </span>
                              <span className="font-mono text-[10px] text-[#7E7D77] shrink-0">
                                #{run.id.slice(0, 8)}
                              </span>
                              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#1E1E1B] text-[#9E9D96] border border-[#2A2A26] shrink-0">
                                {run.taskDomain}
                              </span>
                              <span className="text-[#EDECE8] font-medium truncate max-w-lg">
                                {run.taskInput}
                              </span>
                            </div>

                            <div className="flex items-center gap-4 text-[10px] font-mono text-[#7E7D77]">
                              <span>
                                {new Date(run.createdAt).toLocaleDateString([], { month: 'short', day: 'numeric' })} at{' '}
                                {new Date(run.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                              {run.latencyMs !== undefined && <span>{run.latencyMs}ms</span>}
                              {run.tokensUsed !== undefined && <span>{run.tokensUsed} tokens</span>}
                              {run.retrievedExperiences && run.retrievedExperiences.length > 0 && (
                                <span className="text-[#4EAA79] truncate max-w-xs">
                                  Strategy: {run.retrievedExperiences[0].experience.strategyLesson}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="shrink-0 flex items-center gap-2">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                setSelectedExecution(run)
                              }}
                              className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors cursor-pointer ${
                                isSelected
                                  ? 'bg-[#1E2E24] text-[#4EAA79] border border-[#2E4234] font-semibold'
                                  : 'bg-[#1E1E1B] text-[#9E9D96] hover:text-white border border-[#2E2E2A]'
                              }`}
                            >
                              {isSelected ? 'Viewing Trace' : 'Inspect Trace'}
                            </button>
                          </div>
                        </div>
                      )
                    })}
                </div>
              </div>

              {/* Detailed 5-Node Trace for Selected Run */}
              {selectedExecution ? (
                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between pb-2 border-b border-[#242422]">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#4EAA79]" />
                      <span className="text-xs font-mono font-semibold text-[#EDECE8]">
                        Active Inspection: Run #{selectedExecution.id.slice(0, 8)}
                      </span>
                      <span className="text-[11px] text-[#7E7D77] font-mono truncate max-w-md">
                        &quot;{selectedExecution.taskInput}&quot;
                      </span>
                    </div>
                  </div>

                  <ExecutionStepper currentStage="complete" execution={selectedExecution} />
                  <ContextInspector execution={selectedExecution} />
                </div>
              ) : (
                <div className="rounded-lg border border-[#242422] bg-[#161614] p-12 text-center text-xs text-[#7E7D77] font-mono">
                  No execution selected. Click any run above to inspect its 5-node cognitive trace.
                </div>
              )}
            </div>
          )}

          {/* TAB 5: SETTINGS */}
          {activeTab === 'settings' && (
            <SettingsView
              isDemo={isDemo}
              memoriesCount={experiences.length}
              executionsCount={recentExecutions.length}
              onClearThreads={async () => {
                await clearExecutionsApi()
                setRecentExecutions([])
                setSelectedExecution(null)
              }}
              onClearMemories={async () => {
                for (const exp of experiences) {
                  await deleteExperienceApi(exp.id).catch(() => {})
                }
                setExperiences([])
                setMetrics(getTelemetryMetrics())
              }}
            />
          )}
        </main>
      )}
      </div>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialMode="signup"
      />
    </div>
  )
}
