import { useState, useMemo } from 'react'
import { Search, Database, Plus, RefreshCw, X } from 'lucide-react'
import type { Experience, TaskDomain } from '../types'
import MemoryCard from './MemoryCard'

interface MemoryExplorerProps {
  experiences: Experience[]
  isDemo?: boolean
  onRefresh?: (domain?: TaskDomain | 'all', search?: string, status?: string) => void
  onAddExperience?: (exp: Partial<Experience>) => void
  onDeleteExperience?: (id: string) => void
}

export default function MemoryExplorer({
  experiences,
  isDemo = false,
  onRefresh,
  onAddExperience,
  onDeleteExperience,
}: MemoryExplorerProps) {
  const [search, setSearch] = useState('')
  const [selectedDomain, setSelectedDomain] = useState<TaskDomain | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'candidate' | 'deprecated'>('all')
  const [selectedExp, setSelectedExp] = useState<Experience | null>(null)
  const [isAddOpen, setIsAddOpen] = useState(false)

  // Form states for new experience
  const [newDomain, setNewDomain] = useState<TaskDomain>('research')
  const [newTrigger, setNewTrigger] = useState('')
  const [newStrategy, setNewStrategy] = useState('')
  const [newPitfall, setNewPitfall] = useState('')

  const domains: (TaskDomain | 'all')[] = ['all', 'research', 'coding', 'analysis', 'planning', 'general']

  const handleDomainChange = (dom: TaskDomain | 'all') => {
    setSelectedDomain(dom)
    onRefresh?.(dom, search, statusFilter)
  }

  const handleStatusChange = (stat: 'all' | 'active' | 'candidate' | 'deprecated') => {
    setStatusFilter(stat)
    onRefresh?.(selectedDomain, search, stat)
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onRefresh?.(selectedDomain, search, statusFilter)
  }

  const filtered = useMemo(() => {
    return experiences.filter((exp) => {
      const matchSearch =
        search === '' ||
        exp.triggerCondition.toLowerCase().includes(search.toLowerCase()) ||
        exp.strategyLesson.toLowerCase().includes(search.toLowerCase()) ||
        (exp.pitfallWarning && exp.pitfallWarning.toLowerCase().includes(search.toLowerCase())) ||
        exp.id.toLowerCase().includes(search.toLowerCase())

      const matchDomain = selectedDomain === 'all' || exp.taskDomain === selectedDomain

      let matchStatus = true
      if (statusFilter === 'active') {
        matchStatus = exp.status === 'active'
      } else if (statusFilter === 'candidate') {
        matchStatus = exp.status === 'candidate' || (exp.status as string) === 'provisional'
      } else if (statusFilter === 'deprecated') {
        matchStatus = exp.status === 'deprecated' || (exp.status as string) === 'quarantined'
      }

      return matchSearch && matchDomain && matchStatus
    })
  }, [experiences, search, selectedDomain, statusFilter])

  const counts = useMemo(() => {
    return {
      all: experiences.length,
      active: experiences.filter((e) => e.status === 'active').length,
      candidate: experiences.filter((e) => e.status === 'candidate' || (e.status as string) === 'provisional').length,
      deprecated: experiences.filter((e) => e.status === 'deprecated' || (e.status as string) === 'quarantined' || (e.trustScore ?? 0) < 0.35).length,
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
      {/* Demo Sandbox Alert Banner */}
      {isDemo && (
        <div className="p-3 rounded-lg border bg-[#1A1A17] border-[#242422] text-[#EDECE8] text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold px-2 py-0.5 rounded bg-[#1E1E1B] border border-[#3E3E34] text-[#E67E22] text-[10px]">
              DEMO SANDBOX
            </span>
            <span className="text-[#9E9D96]">Displaying pre-seeded benchmark memories. Additions and updates in this mode run in-memory.</span>
          </div>
        </div>
      )}

      {/* Search and Action Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search Input Form */}
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-2.5 text-[#7E7D77]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search triggers, verified strategies, or hazards (press Enter to query backend)..."
            className="w-full pl-9 pr-4 py-2 text-xs font-mono rounded-lg border transition-colors outline-none
              bg-[#141412] border-[#2E2E2A] text-[#EDECE8] placeholder-[#5A5955] focus:border-[#4EAA79]"
          />
        </form>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={() => onRefresh(selectedDomain, search, statusFilter)}
              className="p-2 rounded-lg border transition-colors text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#1E1E1B]
                bg-[#141412] border-[#2E2E2A] cursor-pointer"
              title="Refresh experience index from backend"
            >
              <RefreshCw size={14} />
            </button>
          )}

          <button
            onClick={() => setIsAddOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-mono font-semibold text-[#141412] bg-[#EDECE8] hover:bg-white transition-colors shadow-sm cursor-pointer"
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
              onClick={() => handleDomainChange(dom)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-mono capitalize transition-all cursor-pointer ${
                selectedDomain === dom
                  ? 'bg-[#22221E] text-white font-medium border border-[#2E2E2A]'
                  : 'text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
              }`}
            >
              {dom}
            </button>
          ))}
        </div>

        {/* Status Pill Filter */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <button
            onClick={() => handleStatusChange('all')}
            className={`px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
              statusFilter === 'all'
                ? 'border-[#2E2E2A] bg-[#22221E] text-[#EDECE8] font-semibold'
                : 'border-transparent text-[#7E7D77] hover:text-[#EDECE8]'
            }`}
          >
            All ({counts.all})
          </button>
          <button
            onClick={() => handleStatusChange('active')}
            className={`px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
              statusFilter === 'active'
                ? 'border-[#2E4234] bg-[#1E2E24] text-[#4EAA79] font-semibold'
                : 'border-transparent text-[#7E7D77] hover:text-[#4EAA79]'
            }`}
          >
            Active ({counts.active})
          </button>
          <button
            onClick={() => handleStatusChange('candidate')}
            className={`px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
              statusFilter === 'candidate'
                ? 'border-[#3E3E34] bg-[#1E1E1B] text-[#E67E22] font-semibold'
                : 'border-transparent text-[#7E7D77] hover:text-[#E67E22]'
            }`}
          >
            Candidate ({counts.candidate})
          </button>
          <button
            onClick={() => handleStatusChange('deprecated')}
            className={`px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
              statusFilter === 'deprecated'
                ? 'border-[#4E2A2A] bg-[#2E1E1E] text-[#D9534F] font-semibold'
                : 'border-transparent text-[#7E7D77] hover:text-[#D9534F]'
            }`}
          >
            Quarantined ({counts.deprecated})
          </button>
        </div>
      </div>

      {/* Grid of Experiences */}
      {filtered.length === 0 ? (
        <div className="rounded-lg border p-12 text-center bg-[#161614] border-[#242422]">
          <Database size={28} className="mx-auto text-[#7E7D77] mb-3 opacity-50" />
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#EDECE8]">
            {experiences.length === 0
              ? isDemo
                ? 'No experiences in demo sandbox'
                : 'No persistent experiences recorded yet'
              : 'No matching experiences found'}
          </h3>
          <p className="text-xs text-[#7E7D77] font-mono mt-1 max-w-sm mx-auto">
            {experiences.length === 0
              ? isDemo
                ? 'The demo sandbox environment has no loaded memories.'
                : 'Experiences are distilled automatically after task runs in Execution Studio, or you can record one manually.'
              : 'Try adjusting your search query, domain filter, or status criteria.'}
          </p>
          {experiences.length === 0 && (
            <button
              onClick={() => setIsAddOpen(true)}
              className="mt-4 px-3.5 py-2 rounded-lg text-xs font-mono font-semibold text-[#141412] bg-[#EDECE8] hover:bg-white transition-colors cursor-pointer"
            >
              Record First Experience
            </button>
          )}
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
          <div className="w-full max-w-xl rounded-lg border p-6 shadow-2xl relative
            bg-[#161614] border-[#242422] text-[#EDECE8]"
          >
            <button
              onClick={() => setSelectedExp(null)}
              className="absolute top-5 right-5 p-1 rounded-lg text-[#7E7D77] hover:text-white"
            >
              <X size={16} />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#1A1A17] text-[#EDECE8] border border-[#2E2E2A]">
                {selectedExp.id}
              </span>
              <span className="font-mono text-xs uppercase text-[#7E7D77]">
                {selectedExp.taskDomain}
              </span>
            </div>

            <h3 className="text-sm font-semibold mb-3 text-[#EDECE8]">
              Experiential Trace Details
            </h3>

            <div className="space-y-3 mb-5 text-xs font-mono">
              <div>
                <span className="font-mono text-[10px] text-[#7E7D77] block mb-1">TRIGGER CONDITION</span>
                <p className="p-2.5 rounded-lg bg-[#141412] border border-[#242422] text-[#EDECE8]">
                  {selectedExp.triggerCondition}
                </p>
              </div>

              <div>
                <span className="font-mono text-[10px] text-[#4EAA79] block mb-1">AFFIRMATIVE STRATEGY LESSON</span>
                <p className="p-2.5 rounded-lg bg-[#141E18] border border-[#203D2A] text-[#EDECE8]">
                  {selectedExp.strategyLesson}
                </p>
              </div>

              {selectedExp.pitfallWarning && (
                <div>
                  <span className="font-mono text-[10px] text-[#D9534F] block mb-1">HAZARD PITFALL (NEGATIVE TRANSFER PREVENTATIVE)</span>
                  <p className="p-2.5 rounded-lg bg-[#221616] border border-[#3E2020] text-[#EDECE8]">
                    {selectedExp.pitfallWarning}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="p-2.5 rounded-lg bg-[#141412] border border-[#242422]">
                  <div className="font-mono text-[10px] text-[#7E7D77]">TRUST (St)</div>
                  <div className="text-sm font-mono font-semibold text-[#4EAA79]">
                    {(selectedExp.trustScore * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-[#141412] border border-[#242422]">
                  <div className="font-mono text-[10px] text-[#7E7D77]">USES / WINS</div>
                  <div className="text-sm font-mono font-semibold text-[#EDECE8]">
                    {selectedExp.usesCount} / {selectedExp.successesCount}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-[#141412] border border-[#242422]">
                  <div className="font-mono text-[10px] text-[#7E7D77]">QUARANTINE k</div>
                  <div className="text-sm font-mono font-semibold text-[#D9534F]">
                    {selectedExp.consecutiveFailures} / 3
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 pt-2">
              {onDeleteExperience && (
                <button
                  type="button"
                  onClick={() => {
                    if (
                      window.confirm(
                        `Quarantine or delete experience ${selectedExp.id}? This will isolate it from agent task retrieval under Theorem 1.`
                      )
                    ) {
                      onDeleteExperience(selectedExp.id)
                      setSelectedExp(null)
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium text-[#D9534F] hover:bg-[#2E1E1E] border border-[#4E2A2A] transition-colors cursor-pointer"
                >
                  Quarantine / Delete
                </button>
              )}
              <button
                onClick={() => setSelectedExp(null)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold bg-[#1E1E1B] hover:bg-[#252522] border border-[#2E2E2A] text-[#EDECE8] transition-colors ml-auto cursor-pointer"
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
          <div className="w-full max-w-lg rounded-lg border p-6 shadow-2xl relative
            bg-[#161614] border-[#242422] text-[#EDECE8]"
          >
            <button
              onClick={() => setIsAddOpen(false)}
              className="absolute top-5 right-5 p-1 rounded-lg text-[#7E7D77] hover:text-white"
            >
              <X size={16} />
            </button>

            <h3 className="text-sm font-semibold mb-1 text-[#EDECE8]">
              Record Operational Experience
            </h3>
            <p className="text-xs text-[#7E7D77] mb-4 font-mono">
              Add a verified operational trajectory with both affirmative lessons and pitfall warnings.
            </p>

            <form onSubmit={handleCreateExperience} className="space-y-3 text-xs font-mono">
              <div>
                <label className="block font-medium mb-1 text-[#9E9D96]">
                  Task Domain
                </label>
                <select
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value as TaskDomain)}
                  className="w-full p-2 rounded-lg border outline-none
                    bg-[#141412] border-[#2E2E2A] text-[#EDECE8]"
                >
                  <option value="research">Research</option>
                  <option value="coding">Coding</option>
                  <option value="analysis">Analysis</option>
                  <option value="planning">Planning</option>
                  <option value="general">General</option>
                </select>
              </div>

              <div>
                <label className="block font-medium mb-1 text-[#9E9D96]">
                  Trigger Condition (When to apply)
                </label>
                <textarea
                  required
                  rows={2}
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  placeholder="e.g. Asynchronous token refresh race conditions under concurrent 401s..."
                  className="w-full p-2 rounded-lg border outline-none
                    bg-[#141412] border-[#2E2E2A] text-[#EDECE8] placeholder-[#5A5955]"
                />
              </div>

              <div>
                <label className="block font-medium mb-1 text-[#4EAA79]">
                  Affirmative Strategy Lesson (What works)
                </label>
                <textarea
                  required
                  rows={2}
                  value={newStrategy}
                  onChange={(e) => setNewStrategy(e.target.value)}
                  placeholder="e.g. Memoize the in-flight refresh promise so subsequent requests await the same token..."
                  className="w-full p-2 rounded-lg border outline-none
                    bg-[#141412] border-[#2E2E2A] text-[#EDECE8] placeholder-[#5A5955]"
                />
              </div>

              <div>
                <label className="block font-medium mb-1 text-[#D9534F]">
                  Hazard Pitfall Warning (What causes negative transfer)
                </label>
                <textarea
                  rows={2}
                  value={newPitfall}
                  onChange={(e) => setNewPitfall(e.target.value)}
                  placeholder="e.g. Do not fire parallel refresh calls or overwrite local storage on unresolved promises..."
                  className="w-full p-2 rounded-lg border outline-none
                    bg-[#141412] border-[#2E2E2A] text-[#EDECE8] placeholder-[#5A5955]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono text-[#7E7D77] hover:text-[#EDECE8] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg text-xs font-mono font-semibold text-[#141412] bg-[#EDECE8] hover:bg-white transition-colors cursor-pointer"
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
