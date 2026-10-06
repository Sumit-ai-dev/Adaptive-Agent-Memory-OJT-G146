import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  History,
  Cpu,
  Clock,
  RefreshCw,
  Bot,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { TaskExecution } from '../types'
import { fetchExecutions } from '../services/api'
import WorkspaceHeader from '../components/workspace/WorkspaceHeader'
import ExecutionTraceView from '../components/workspace/ExecutionTraceView'

export default function AgentRunsPage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/', { replace: true })
    }
  }, [user, authLoading, navigate])

  const [executions, setExecutions] = useState<TaskExecution[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDomain, setSelectedDomain] = useState<string>('all')

  const loadExecutions = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchExecutions({
        domain: selectedDomain === 'all' ? undefined : selectedDomain,
        limit: 50,
      })
      setExecutions(res.items || [])
      setTotalCount(res.total || 0)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load execution runs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user) {
      loadExecutions()
    }
  }, [user, selectedDomain])

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0a0010] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="min-h-screen bg-[#0a0010] text-white selection:bg-purple-500/30 flex flex-col">
      <WorkspaceHeader />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 py-8 w-full space-y-6">
        {/* Title Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <History size={20} className="text-cyan-400" />
              <h1 className="text-2xl font-display font-bold text-white tracking-tight">
                Agent Run History & Traces
              </h1>
            </div>
            <p className="text-sm text-white/50 font-sans">
              Recorded 5-node LangGraph execution trajectories, outcome evaluations, and trust updates.
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-white/60">
            <span className="px-3 py-1.5 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
              Total Runs: {totalCount}
            </span>
            <button
              onClick={loadExecutions}
              disabled={loading}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white transition-colors cursor-pointer"
              title="Refresh runs"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="p-3 rounded-2xl glass border border-white/10 flex items-center gap-2 text-xs overflow-x-auto">
          <span className="text-white/40 font-mono text-[11px] mr-1">Domain:</span>
          {['all', 'research', 'coding', 'analysis', 'planning'].map((dom) => (
            <button
              key={dom}
              type="button"
              onClick={() => setSelectedDomain(dom)}
              className={`px-3 py-1 rounded-xl font-mono capitalize transition-all cursor-pointer ${
                selectedDomain === dom
                  ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-200 font-semibold'
                  : 'bg-white/5 border border-white/5 text-white/50 hover:text-white'
              }`}
            >
              {dom}
            </button>
          ))}
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs font-mono">
            {error}
          </div>
        )}

        {/* Executions List */}
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-white/40 font-mono text-xs">Querying execution logs...</p>
          </div>
        ) : executions.length === 0 ? (
          <div className="py-20 text-center space-y-3 glass rounded-3xl border border-white/10">
            <History size={32} className="text-white/20 mx-auto" />
            <p className="text-sm text-white/50 font-sans">No executions recorded in this session yet.</p>
            <Link
              to="/agent"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl anim-gradient-bg text-white font-mono text-xs font-semibold shadow hover:scale-105 transition-all"
            >
              <Bot size={14} />
              <span>Launch a task in Agent Workspace</span>
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {executions.map((exec) => (
              <div
                key={exec.id}
                className="p-5 rounded-2xl glass border border-white/10 space-y-4"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-white">
                      {exec.id}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-purple-500/15 border border-purple-500/30 text-[10px] font-mono text-purple-300 uppercase">
                      {exec.taskDomain}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-[10px] font-mono text-emerald-300 uppercase">
                      {exec.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[11px] font-mono text-white/40">
                    <span className="flex items-center gap-1">
                      <Clock size={11} />
                      {exec.latencyMs || 0}ms
                    </span>
                    <span className="flex items-center gap-1">
                      <Cpu size={11} />
                      {exec.tokensUsed || 120} tokens
                    </span>
                    {exec.outcomeScore !== undefined && (
                      <span className="text-emerald-400">
                        Score: {(exec.outcomeScore * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>

                {/* Task Input Prompt */}
                <div>
                  <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider block mb-1">
                    Task Prompt
                  </span>
                  <p className="text-white text-xs font-sans leading-relaxed bg-black/20 p-3 rounded-xl border border-white/5">
                    {exec.taskInput}
                  </p>
                </div>

                {/* Final Output */}
                {(exec.finalAnswer || exec.finalOutput) && (
                  <div>
                    <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider block mb-1">
                      Final Output
                    </span>
                    <div className="text-white/80 text-xs font-sans leading-relaxed bg-white/[0.02] p-3 rounded-xl border border-white/5 line-clamp-3">
                      {exec.finalAnswer || exec.finalOutput}
                    </div>
                  </div>
                )}

                {/* Execution Step Trace Accordion */}
                {exec.trajectory && exec.trajectory.length > 0 && (
                  <div>
                    <ExecutionTraceView
                      trajectory={exec.trajectory}
                      latencyMs={exec.latencyMs}
                      tokensUsed={exec.tokensUsed}
                      outcomeScore={exec.outcomeScore}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
