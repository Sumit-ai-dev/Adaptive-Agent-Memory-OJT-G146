import { Shield, AlertTriangle, CheckCircle, Cpu } from 'lucide-react'
import type { Experience } from '../types'
import StatusBadge from './StatusBadge'

interface MemoryCardProps {
  experience: Experience
  onSelect?: (exp: Experience) => void
  isSelected?: boolean
}

export default function MemoryCard({
  experience,
  onSelect,
  isSelected = false,
}: MemoryCardProps) {
  const trustPct = (experience.trustScore * 100).toFixed(1)
  const successRate =
    experience.usesCount > 0
      ? ((experience.successesCount / experience.usesCount) * 100).toFixed(0)
      : '100'

  return (
    <div
      onClick={() => onSelect?.(experience)}
      className={`rounded-xl border p-4 transition-all cursor-pointer text-left ${
        isSelected
          ? 'border-indigo-600 bg-indigo-50/30 dark:border-indigo-500 dark:bg-indigo-950/20 shadow-sm'
          : 'bg-white border-[#E6E6E1] hover:border-zinc-400 dark:bg-[#131722] dark:border-[#252B3B] dark:hover:border-zinc-600'
      }`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-zinc-100 text-zinc-700 dark:bg-[#1A1F2C] dark:text-zinc-300 border border-[#E6E6E1] dark:border-[#252B3B]">
            {experience.id}
          </span>
          <span className="text-[11px] font-mono text-zinc-500 uppercase tracking-wider">
            {experience.taskDomain}
          </span>
        </div>
        <StatusBadge status={experience.status} size="sm" />
      </div>

      {/* Trigger Condition */}
      <div className="mb-3">
        <div className="text-[11px] font-mono font-medium text-zinc-400 dark:text-zinc-500 uppercase tracking-wider mb-1">
          Operational Trigger
        </div>
        <div className="text-xs font-medium text-[#18181B] dark:text-[#F4F4F6] line-clamp-2">
          {experience.triggerCondition}
        </div>
      </div>

      {/* Bilateral Units: Strategy Lesson & Hazard Pitfall */}
      <div className="space-y-2 mb-3">
        {/* Strategy Lesson (Affirmative) */}
        <div className="rounded-lg border p-2.5 bg-emerald-50/60 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/50">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-emerald-800 dark:text-emerald-400 mb-1">
            <CheckCircle size={13} className="shrink-0" />
            <span>Affirmative Strategy</span>
          </div>
          <p className="text-xs text-emerald-950 dark:text-emerald-200 leading-relaxed">
            {experience.strategyLesson}
          </p>
        </div>

        {/* Hazard Pitfall Warning */}
        {experience.pitfallWarning && (
          <div className="rounded-lg border p-2.5 bg-rose-50/60 border-rose-200 dark:bg-rose-950/20 dark:border-rose-900/50">
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-rose-800 dark:text-rose-400 mb-1">
              <AlertTriangle size={13} className="shrink-0" />
              <span>Hazard Pitfall</span>
            </div>
            <p className="text-xs text-rose-950 dark:text-rose-200 leading-relaxed">
              {experience.pitfallWarning}
            </p>
          </div>
        )}
      </div>

      {/* Metrics Footer */}
      <div className="pt-3 border-t border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5" title="Asymmetric EMA Trust Score (St)">
            <Shield size={13} className="text-indigo-600 dark:text-indigo-400" />
            <span className="font-mono font-semibold text-[#18181B] dark:text-[#F4F4F6]">
              {trustPct}%
            </span>
          </div>
          <div className="flex items-center gap-1 text-zinc-500 dark:text-zinc-400 font-mono text-[11px]" title="Uses and Empirical Success Rate">
            <Cpu size={12} />
            <span>{experience.usesCount} uses</span>
            <span>({successRate}% win)</span>
          </div>
        </div>

        {/* Quarantine Failures Counter if any */}
        {experience.consecutiveFailures > 0 && (
          <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300 border border-rose-200 dark:border-rose-800" title="Consecutive failures toward Theorem 1 quarantine threshold k*=3">
            k={experience.consecutiveFailures}/3
          </span>
        )}
      </div>
    </div>
  )
}
