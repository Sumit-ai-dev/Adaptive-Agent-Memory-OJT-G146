import { useState } from 'react'
import {
  Shield,
  AlertTriangle,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Database,
  Info,
  X,
  ExternalLink,
} from 'lucide-react'
import { RetrievedMemoryItem, TrustUpdateItem, Experience } from '../../types'

interface MemoryContextPanelProps {
  retrievedMemories?: RetrievedMemoryItem[]
  trustUpdates?: TrustUpdateItem[]
  memoryEnabled: boolean
}

export default function MemoryContextPanel({
  retrievedMemories = [],
  trustUpdates = [],
  memoryEnabled,
}: MemoryContextPanelProps) {
  const [selectedExperience, setSelectedExperience] = useState<Experience | null>(null)

  return (
    <div className="h-full flex flex-col bg-[#0b0014]/60 backdrop-blur-xl border-l border-white/10 p-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Database size={13} />
          </div>
          <div>
            <h3 className="font-display font-bold text-white text-xs tracking-tight">
              Experience Context
            </h3>
            <span className="text-[10px] font-mono text-white/40">
              Persistent Memory Plane
            </span>
          </div>
        </div>

        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
            memoryEnabled
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
              : 'bg-white/5 text-white/40 border-white/10'
          }`}
        >
          {memoryEnabled ? 'Active' : 'Bypassed'}
        </span>
      </div>

      {/* Trust Update summary for this response (if any) */}
      {trustUpdates.length > 0 && (
        <div className="mb-4 p-3 rounded-xl bg-purple-500/10 border border-purple-500/25 space-y-2">
          <div className="flex items-center gap-1.5 text-purple-300 font-mono text-[11px] font-semibold">
            <Sparkles size={12} />
            <span>Reliability Updates</span>
          </div>
          <div className="space-y-1.5">
            {trustUpdates.map((update, idx) => (
              <div
                key={update.experienceId || idx}
                className="flex items-center justify-between text-xs font-mono bg-black/30 px-2.5 py-1.5 rounded-lg border border-white/5"
              >
                <span className="text-white/60 truncate max-w-[130px]">
                  {update.experienceId.slice(0, 8)}...
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="text-white/40">
                    {(update.oldScore * 100).toFixed(1)}%
                  </span>
                  <span className="text-white/30">→</span>
                  <span className="text-white font-semibold">
                    {(update.newScore * 100).toFixed(1)}%
                  </span>
                  {update.delta >= 0 ? (
                    <span className="text-emerald-400 flex items-center text-[10px]">
                      <TrendingUp size={11} />
                      +{(update.delta * 100).toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-red-400 flex items-center text-[10px]">
                      <TrendingDown size={11} />
                      {(update.delta * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Retrieved Memories List */}
      <div className="space-y-3 flex-1">
        <div className="flex items-center justify-between text-[11px] font-mono text-white/40 uppercase tracking-wider">
          <span>Relevant Experiences ({retrievedMemories.length})</span>
        </div>

        {retrievedMemories.length === 0 ? (
          <div className="p-6 rounded-2xl border border-dashed border-white/10 text-center space-y-2">
            <Info size={18} className="text-white/20 mx-auto" />
            <p className="text-xs text-white/40 font-sans">
              No previous experiences influenced this response.
            </p>
            <p className="text-[10px] text-white/25 font-mono">
              Ask questions related to research, coding, or analytics to trigger verified lessons.
            </p>
          </div>
        ) : (
          retrievedMemories.map((item, idx) => {
            const exp = item.experience
            const isQuarantined =
              exp.trustScore < 0.35 || exp.status === 'deprecated'

            return (
              <div
                key={exp.id || idx}
                className={`p-3.5 rounded-2xl border transition-all ${
                  isQuarantined
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-white/[0.04] hover:bg-white/[0.07] border-white/10'
                }`}
              >
                {/* Header: Title / Status */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="px-2 py-0.5 rounded-md bg-purple-500/15 border border-purple-500/30 text-[10px] font-mono text-purple-300 uppercase tracking-wider">
                      {exp.taskDomain}
                    </span>
                    {isQuarantined ? (
                      <span className="px-2 py-0.5 rounded-md bg-red-500/20 border border-red-500/40 text-[10px] font-mono text-red-300 font-bold flex items-center gap-1">
                        <AlertTriangle size={10} />
                        QUARANTINED
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-[10px] font-mono text-emerald-300">
                        ACTIVE
                      </span>
                    )}
                  </div>

                  {/* Trust Score Badge */}
                  <div
                    className={`flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[11px] font-semibold ${
                      isQuarantined
                        ? 'bg-red-500/20 text-red-300'
                        : exp.trustScore >= 0.7
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : 'bg-amber-500/20 text-amber-300'
                    }`}
                  >
                    <Shield size={11} />
                    <span>{(exp.trustScore * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Strategy Lesson */}
                <p className="text-xs text-white/90 font-sans leading-relaxed line-clamp-3 mb-2.5">
                  {exp.strategyLesson}
                </p>

                {/* Quarantined Warning Notice */}
                {isQuarantined && (
                  <div className="mb-2 p-2 rounded-lg bg-red-500/15 border border-red-500/30 text-[11px] text-red-200 font-sans">
                    Repeatedly produced suboptimal or incorrect outcomes. Quarantined from active agent guidance.
                  </div>
                )}

                {/* Stats Footer */}
                <div className="flex items-center justify-between text-[10px] font-mono text-white/40 pt-2 border-t border-white/5">
                  <span>Used {exp.usesCount || 0} times</span>
                  {exp.successesCount !== undefined && (
                    <span className="text-emerald-400">
                      Helpful: {exp.successesCount}
                    </span>
                  )}
                  <button
                    onClick={() => setSelectedExperience(exp)}
                    type="button"
                    className="text-purple-300 hover:text-purple-200 transition-colors flex items-center gap-0.5 cursor-pointer"
                  >
                    <span>View details</span>
                    <ExternalLink size={10} />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Experience Details Modal */}
      {selectedExperience && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0e001a] border border-white/20 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Database size={16} className="text-purple-400" />
                <h4 className="font-display font-bold text-white text-sm">
                  Experience Inspection
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
    </div>
  )
}
