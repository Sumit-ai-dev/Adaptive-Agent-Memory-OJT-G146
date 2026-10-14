import { useState, useMemo } from 'react'
import { Search, Database, Plus, RefreshCw, X } from 'lucide-react'
import type { Experience, TaskDomain } from '../types'
import MemoryCard from './MemoryCard'

interface MemoryExplorerProps {
  experiences: Experience[]
  onRefresh?: () => void
  onAddExperience?: (exp: Partial<Experience>) => void
}

export default function MemoryExplorer({
  experiences,
  onRefresh,
  onAddExperience,
}: MemoryExplorerProps) {
  const [search, setSearch] = useState('')
  const [selectedDomain, setSelectedDomain] = useState<TaskDomain | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'provisional' | 'quarantined'>('all')
  const [selectedExp, setSelectedExp] = useState<Experience | null>(null)
  const [isAddOpen, setIsAddOpen] = useState(false)

  // Form states for new experience
  const [newDomain, setNewDomain] = useState<TaskDomain>('research')
  const [newTrigger, setNewTrigger] = useState('')
  const [newStrategy, setNewStrategy] = useState('')
  const [newPitfall, setNewPitfall] = useState('')

  const domains: (TaskDomain | 'all')[] = ['all', 'research', 'coding', 'analysis', 'planning', 'general']

  const filtered = useMemo(() => {
    return experiences.filter((exp) => {
      const matchSearch =
        search === '' ||
        exp.triggerCondition.toLowerCase().includes(search.toLowerCase()) ||
        exp.strategyLesson.toLowerCase().includes(search.toLowerCase()) ||
        (exp.pitfallWarning && exp.pitfallWarning.toLowerCase().includes(search.toLowerCase())) ||
        exp.id.toLowerCase().includes(search.toLowerCase())

      const matchDomain = selectedDomain === 'all' || exp.taskDomain === selectedDomain
      const matchStatus = statusFilter === 'all' || exp.status === statusFilter

      return matchSearch && matchDomain && matchStatus
    })
  }, [experiences, search, selectedDomain, statusFilter])

  const counts = useMemo(() => {
    return {
      all: experiences.length,
      active: experiences.filter((e) => e.status === 'active').length,
      provisional: experiences.filter((e) => e.status === 'provisional').length,
      quarantined: experiences.filter((e) => e.status === 'quarantined').length,
    }
  }, [experiences])

  const handleCreateExperience = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTrigger.trim() || !newStrategy.trim()) return

    onAddExperience?.({
      taskDomain: newDomain,
      triggerCondition: newTrigger.trim(),
      strategyLesson: newStrategy.trim(),
      pitfallWarning: newPitfall.trim() || undefined,
      trustScore: 0.75,
      confidenceScore: 0.85,
      usesCount: 1,
      successesCount: 1,
      failuresCount: 0,
      consecutiveFailures: 0,
      status: 'active',
      trustTrajectory: [0.75],
    })

    setNewTrigger('')
    setNewStrategy('')
    setNewPitfall('')
    setIsAddOpen(false)
  }

  return (
    <div className="space-y-5">
      {/* Search and Action Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-3 text-zinc-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search triggers, verified strategies, or hazards..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border transition-colors outline-none
              bg-white border-[#E6E6E1] text-[#18181B] focus:border-indigo-600
              dark:bg-[#131722] dark:border-[#252B3B] dark:text-[#F4F4F6] dark:focus:border-indigo-400"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 rounded-xl border transition-colors text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200
                bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]"
              title="Refresh experience index"
            >
              <RefreshCw size={15} />
            </button>
          )}

          <button
            onClick={() => setIsAddOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-white transition-all
              bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500 shadow-sm"
          >
            <Plus size={14} />
            <span>Record Experience</span>
          </button>
        </div>
      </div>

      {/* Domain Filters & Status Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        {/* Domain Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1">
          {domains.map((dom) => (
            <button
              key={dom}
              onClick={() => setSelectedDomain(dom)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono capitalize transition-all ${
                selectedDomain === dom
                  ? 'bg-indigo-600 text-white font-medium shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-[#1A1F2C]'
              }`}
            >
              {dom}
            </button>
          ))}
        </div>

        {/* Status Pill Filter */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-2.5 py-1 rounded-md border transition-all ${
              statusFilter === 'all'
                ? 'border-zinc-700 bg-zinc-200/70 text-zinc-900 dark:border-zinc-400 dark:bg-zinc-800 dark:text-zinc-100 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
            }`}
          >
            All ({counts.all})
          </button>
          <button
            onClick={() => setStatusFilter('active')}
            className={`px-2.5 py-1 rounded-md border transition-all ${
              statusFilter === 'active'
                ? 'border-emerald-600 bg-emerald-50 text-emerald-800 dark:border-emerald-500 dark:bg-emerald-950/40 dark:text-emerald-300 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-emerald-600'
            }`}
          >
            Active ({counts.active})
          </button>
          <button
            onClick={() => setStatusFilter('provisional')}
            className={`px-2.5 py-1 rounded-md border transition-all ${
              statusFilter === 'provisional'
                ? 'border-amber-600 bg-amber-50 text-amber-800 dark:border-amber-500 dark:bg-amber-950/40 dark:text-amber-300 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-amber-600'
            }`}
          >
            Provisional ({counts.provisional})
          </button>
          <button
            onClick={() => setStatusFilter('quarantined')}
            className={`px-2.5 py-1 rounded-md border transition-all ${
              statusFilter === 'quarantined'
                ? 'border-rose-600 bg-rose-50 text-rose-800 dark:border-rose-500 dark:bg-rose-950/40 dark:text-rose-300 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-rose-600'
            }`}
          >
            Quarantined ({counts.quarantined})
          </button>
        </div>
      </div>

      {/* Grid of Experiences */}
      {filtered.length === 0 ? (
        <div className="rounded-xl border p-12 text-center bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B]">
          <Database size={32} className="mx-auto text-zinc-300 dark:text-zinc-600 mb-3" />
          <h3 className="text-sm font-semibold text-[#18181B] dark:text-[#F4F4F6]">
            No matching experiences found
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-sm mx-auto">
            Try adjusting your search query, domain filter, or status criteria.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((exp) => (
            <MemoryCard
              key={exp.id}
              experience={exp}
              isSelected={selectedExp?.id === exp.id}
              onSelect={setSelectedExp}
            />
          ))}
        </div>
      )}

      {/* Experience Inspection Modal */}
      {selectedExp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm anim-fade-in">
          <div className="w-full max-w-xl rounded-2xl border p-6 shadow-2xl relative
            bg-white border-[#E6E6E1] text-[#18181B]
            dark:bg-[#131722] dark:border-[#252B3B] dark:text-[#F4F4F6]"
          >
            <button
              onClick={() => setSelectedExp(null)}
              className="absolute top-5 right-5 p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-zinc-100 text-zinc-700 dark:bg-[#1A1F2C] dark:text-zinc-300 border border-[#E6E6E1] dark:border-[#252B3B]">
                {selectedExp.id}
              </span>
              <span className="font-mono text-xs uppercase text-zinc-400">
                {selectedExp.taskDomain}
              </span>
            </div>

            <h3 className="text-base font-semibold mb-3">
              Experiential Trace Details
            </h3>

            <div className="space-y-3 mb-5 text-xs">
              <div>
                <span className="font-mono font-medium text-zinc-400 block mb-1">TRIGGER CONDITION</span>
                <p className="p-2.5 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B]">
                  {selectedExp.triggerCondition}
                </p>
              </div>

              <div>
                <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400 block mb-1">AFFIRMATIVE STRATEGY LESSON</span>
                <p className="p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/50 text-emerald-950 dark:text-emerald-200">
                  {selectedExp.strategyLesson}
                </p>
              </div>

              {selectedExp.pitfallWarning && (
                <div>
                  <span className="font-mono font-medium text-rose-600 dark:text-rose-400 block mb-1">HAZARD PITFALL (NEGATIVE TRANSFER PREVENTATIVE)</span>
                  <p className="p-2.5 rounded-lg bg-rose-50/50 border border-rose-200 dark:bg-rose-950/20 dark:border-rose-900/50 text-rose-950 dark:text-rose-200">
                    {selectedExp.pitfallWarning}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B]">
                  <div className="font-mono text-[11px] text-zinc-400">TRUST (St)</div>
                  <div className="text-base font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                    {(selectedExp.trustScore * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B]">
                  <div className="font-mono text-[11px] text-zinc-400">USES / WINS</div>
                  <div className="text-base font-mono font-semibold">
                    {selectedExp.usesCount} / {selectedExp.successesCount}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-50 dark:bg-[#1A1F2C] border border-[#E6E6E1] dark:border-[#252B3B]">
                  <div className="font-mono text-[11px] text-zinc-400">QUARANTINE k</div>
                  <div className="text-base font-mono font-semibold text-rose-600 dark:text-rose-400">
                    {selectedExp.consecutiveFailures} / 3
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedExp(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-zinc-100 hover:bg-zinc-200 dark:bg-[#1A1F2C] dark:hover:bg-[#252B3B] text-zinc-800 dark:text-zinc-200 transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Record Experience Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm anim-fade-in">
          <div className="w-full max-w-lg rounded-2xl border p-6 shadow-2xl relative
            bg-white border-[#E6E6E1] text-[#18181B]
            dark:bg-[#131722] dark:border-[#252B3B] dark:text-[#F4F4F6]"
          >
            <button
              onClick={() => setIsAddOpen(false)}
              className="absolute top-5 right-5 p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
            >
              <X size={18} />
            </button>

            <h3 className="text-base font-semibold mb-1">
              Record Operational Experience
            </h3>
            <p className="text-xs text-zinc-500 mb-4">
              Add a verified operational trajectory with both affirmative lessons and pitfall warnings.
            </p>

            <form onSubmit={handleCreateExperience} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium mb-1 text-zinc-700 dark:text-zinc-300">
                  Task Domain
                </label>
                <select
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value as TaskDomain)}
                  className="w-full p-2 rounded-xl border outline-none
                    bg-white border-[#E6E6E1] dark:bg-[#1A1F2C] dark:border-[#252B3B]"
                >
                  <option value="research">Research</option>
                  <option value="coding">Coding</option>
                  <option value="analysis">Analysis</option>
                  <option value="planning">Planning</option>
                  <option value="general">General</option>
                </select>
              </div>

              <div>
                <label className="block font-medium mb-1 text-zinc-700 dark:text-zinc-300">
                  Trigger Condition (When to apply)
                </label>
                <textarea
                  required
                  rows={2}
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  placeholder="e.g. Asynchronous token refresh race conditions under concurrent 401s..."
                  className="w-full p-2 rounded-xl border outline-none
                    bg-white border-[#E6E6E1] dark:bg-[#1A1F2C] dark:border-[#252B3B]"
                />
              </div>

              <div>
                <label className="block font-medium mb-1 text-emerald-700 dark:text-emerald-400">
                  Affirmative Strategy Lesson (What works)
                </label>
                <textarea
                  required
                  rows={2}
                  value={newStrategy}
                  onChange={(e) => setNewStrategy(e.target.value)}
                  placeholder="e.g. Memoize the in-flight refresh promise so subsequent requests await the same token..."
                  className="w-full p-2 rounded-xl border outline-none
                    bg-white border-[#E6E6E1] dark:bg-[#1A1F2C] dark:border-[#252B3B]"
                />
              </div>

              <div>
                <label className="block font-medium mb-1 text-rose-700 dark:text-rose-400">
                  Hazard Pitfall Warning (What causes negative transfer)
                </label>
                <textarea
                  rows={2}
                  value={newPitfall}
                  onChange={(e) => setNewPitfall(e.target.value)}
                  placeholder="e.g. Do not fire parallel refresh calls or overwrite local storage on unresolved promises..."
                  className="w-full p-2 rounded-xl border outline-none
                    bg-white border-[#E6E6E1] dark:bg-[#1A1F2C] dark:border-[#252B3B]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-3 py-2 rounded-xl text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500 shadow-sm"
                >
                  Save Experience
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
