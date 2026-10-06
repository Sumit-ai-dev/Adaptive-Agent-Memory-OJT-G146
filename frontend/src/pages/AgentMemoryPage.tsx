import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Database,
  Search,
  Shield,
  RefreshCw,
  X,
  SlidersHorizontal,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Experience, TaskDomain } from '../types'
import { fetchExperiences } from '../services/api'
import WorkspaceHeader from '../components/workspace/WorkspaceHeader'

export default function AgentMemoryPage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/', { replace: true })
    }
  }, [user, authLoading, navigate])

  const [experiences, setExperiences] = useState<Experience[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [selectedDomain, setSelectedDomain] = useState<TaskDomain | 'all'>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedExperience, setSelectedExperience] = useState<Experience | null>(null)

  const loadMemories = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchExperiences({
        domain: selectedDomain,
        status: selectedStatus,
        search: searchQuery,
        limit: 50,
      })
      setExperiences(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query memories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user) {
      loadMemories()
    }
  }, [user, selectedDomain, selectedStatus])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    loadMemories()
  }

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
        {/* Title bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Database size={20} className="text-purple-400" />
              <h1 className="text-2xl font-display font-bold text-white tracking-tight">
                Persistent Experience Memory Store
              </h1>
            </div>
            <p className="text-sm text-white/50 font-sans">
              Curated lessons, strategy distillation, and reliability weights stored in SQLite.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-white/60">
            <span className="px-3 py-1.5 rounded-xl bg-purple-500/15 border border-purple-500/30 text-purple-300">
              Total Records: {experiences.length}
            </span>
            <button
              onClick={loadMemories}
              disabled={loading}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white transition-colors cursor-pointer"
              title="Refresh"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="p-4 rounded-2xl glass border border-white/10 flex flex-col md:flex-row items-center justify-between gap-4 text-xs">
          {/* Domain tabs */}
          <div className="flex items-center gap-1.5 flex-wrap w-full md:w-auto">
            <span className="text-white/40 font-mono text-[11px] mr-1 flex items-center gap-1">
              <SlidersHorizontal size={12} />
              <span>Domain:</span>
            </span>
            {(['all', 'research', 'coding', 'analysis', 'planning'] as const).map((dom) => (
              <button
                key={dom}
                type="button"
                onClick={() => setSelectedDomain(dom)}
                className={`px-3 py-1.5 rounded-xl font-mono capitalize transition-all cursor-pointer ${
                  selectedDomain === dom
                    ? 'bg-purple-500/25 border border-purple-500/40 text-white font-semibold'
                    : 'bg-white/5 border border-white/5 text-white/60 hover:text-white'
                }`}
              >
                {dom}
              </button>
            ))}
          </div>

          {/* Status filter & Semantic search */}
          <div className="flex items-center gap-3 w-full md:w-auto">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-[#140026] text-white border border-white/10 rounded-xl px-3 py-1.5 font-mono text-xs focus:outline-none focus:border-purple-400"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="candidate">Candidate Only</option>
              <option value="deprecated">Quarantined / Deprecated</option>
            </select>

            <form onSubmit={handleSearchSubmit} className="relative flex-1 md:w-64">
              <input
                type="text"
                placeholder="Search lessons..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#140026] text-white border border-white/10 rounded-xl pl-8 pr-3 py-1.5 font-mono text-xs focus:outline-none focus:border-purple-400 placeholder:text-white/30"
              />
              <Search size={13} className="absolute left-2.5 top-2 text-white/40" />
            </form>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs font-mono">
            {error}
          </div>
        )}

        {/* Experience Cards Grid */}
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-white/40 font-mono text-xs">Querying experience store...</p>
          </div>
        ) : experiences.length === 0 ? (
          <div className="py-20 text-center space-y-2 glass rounded-3xl border border-white/10">
            <Database size={28} className="text-white/20 mx-auto" />
            <p className="text-sm text-white/50 font-sans">No experiences match the selected criteria.</p>
            <button
              onClick={() => {
                setSelectedDomain('all')
                setSelectedStatus('all')
                setSearchQuery('')
              }}
              className="text-purple-300 font-mono text-xs hover:underline cursor-pointer"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {experiences.map((exp) => {
              const isQuarantined = exp.trustScore < 0.35 || exp.status === 'deprecated'

              return (
                <div
                  key={exp.id}
                  onClick={() => setSelectedExperience(exp)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                    isQuarantined
                      ? 'bg-red-500/[0.06] border-red-500/30 hover:border-red-500/50'
                      : 'glass hover:bg-white/[0.08] border-white/10 hover:border-purple-400/40'
                  }`}
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-0.5 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300 font-mono text-[10px] uppercase">
                        {exp.taskDomain}
                      </span>

                      <div
                        className={`flex items-center gap-1 font-mono text-xs font-semibold px-2 py-0.5 rounded-full ${
                          isQuarantined
                            ? 'bg-red-500/20 text-red-300'
                            : exp.trustScore >= 0.7
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}
                      >
                        <Shield size={11} />
                        <span>{(exp.trustScore * 100).toFixed(0)}% trust</span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] font-mono text-white/40 block mb-0.5 uppercase tracking-wider">
                        Trigger:
                      </span>
                      <p className="text-white/70 font-sans text-xs line-clamp-1">
                        {exp.triggerCondition}
                      </p>
                    </div>

                    <div>
                      <span className="text-[10px] font-mono text-white/40 block mb-0.5 uppercase tracking-wider">
                        Lesson:
                      </span>
                      <p className="text-white font-sans text-xs line-clamp-3 leading-relaxed">
                        {exp.strategyLesson}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 mt-3 border-t border-white/5 text-[10px] font-mono text-white/40">
                    <span>Used: {exp.usesCount || 0}</span>
                    <span>Status: {exp.status}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Modal for Experience Inspection */}
        {selectedExperience && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0e001a] border border-white/20 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <Database size={16} className="text-purple-400" />
                  <h4 className="font-display font-bold text-white text-sm">
                    Experience Record Detail
                  </h4>
                </div>
                <button
                  onClick={() => setSelectedExperience(null)}
                  className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white flex items-center justify-center transition-colors cursor-pointer"
                >
                  <X size={14} />
                </button>
              </div>

              <div className="space-y-3 text-xs font-sans">
                <div>
                  <span className="text-white/40 font-mono text-[10px] uppercase tracking-wider block mb-1">
                    Trigger Condition
                  </span>
                  <p className="text-white/80 bg-white/5 p-3 rounded-xl border border-white/5 font-mono text-[11px]">
                    {selectedExperience.triggerCondition}
                  </p>
                </div>

                <div>
                  <span className="text-white/40 font-mono text-[10px] uppercase tracking-wider block mb-1">
                    Validated Strategy Lesson
                  </span>
                  <p className="text-white bg-purple-500/10 p-3 rounded-xl border border-purple-500/25 leading-relaxed">
                    {selectedExperience.strategyLesson}
                  </p>
                </div>

                {selectedExperience.pitfall && (
                  <div>
                    <span className="text-white/40 font-mono text-[10px] uppercase tracking-wider block mb-1">
                      Mitigated Pitfall
                    </span>
                    <p className="text-amber-200/90 bg-amber-500/10 p-3 rounded-xl border border-amber-500/25 leading-relaxed">
                      {selectedExperience.pitfall}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-3 gap-2 font-mono text-center pt-2">
                  <div className="p-2 rounded-xl bg-white/5 border border-white/5">
                    <div className="text-white/40 text-[10px]">Trust Score</div>
                    <div className="text-white font-bold text-sm">
                      {(selectedExperience.trustScore * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-2 rounded-xl bg-white/5 border border-white/5">
                    <div className="text-white/40 text-[10px]">Uses</div>
                    <div className="text-white font-bold text-sm">
                      {selectedExperience.usesCount}
                    </div>
                  </div>
                  <div className="p-2 rounded-xl bg-white/5 border border-white/5">
                    <div className="text-white/40 text-[10px]">Status</div>
                    <div className="text-white font-bold text-sm uppercase">
                      {selectedExperience.status}
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedExperience(null)}
                className="w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white font-mono text-xs font-semibold transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
