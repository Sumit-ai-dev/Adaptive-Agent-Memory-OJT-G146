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
      className={`rounded-lg border p-4 transition-all cursor-pointer text-left ${
        isSelected
          ? 'border-[#4EAA79] bg-[#1E2E24] shadow-sm'
          : 'bg-[#161614] border-[#242422] hover:border-[#2E2E2A] hover:bg-[#1A1A17]'
      }`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#1A1A17] text-[#EDECE8] border border-[#2E2E2A]">
            {experience.id}
          </span>
          <span className="text-[11px] font-mono text-[#7E7D77] uppercase tracking-wider">
            {experience.taskDomain}
          </span>
        </div>
        <StatusBadge status={experience.status} size="sm" />
      </div>

      {/* Trigger Condition */}
      <div className="mb-3">
        <div className="text-[10px] font-mono font-medium text-[#7E7D77] uppercase tracking-wider mb-1">
          Operational Trigger
        </div>
        <div className="text-xs font-medium text-[#EDECE8] line-clamp-2">
          {experience.triggerCondition}
        </div>
      </div>

      {/* Bilateral Units: Strategy Lesson & Hazard Pitfall */}
      <div className="space-y-2 mb-3">
        {/* Strategy Lesson (Affirmative) */}
        <div className="rounded border p-2.5 bg-[#141E18] border-[#203D2A]">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-[#4EAA79] mb-1">
            <CheckCircle size={13} className="shrink-0" />
            <span>Affirmative Strategy</span>
          </div>
          <p className="text-xs text-[#EDECE8] leading-relaxed">
            {experience.strategyLesson}
          </p>
        </div>

        {/* Hazard Pitfall Warning */}
        {experience.pitfallWarning && (
          <div className="rounded border p-2.5 bg-[#221616] border-[#3E2020]">
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-[#D9534F] mb-1">
              <AlertTriangle size={13} className="shrink-0" />
              <span>Hazard Pitfall</span>
            </div>
            <p className="text-xs text-[#EDECE8] leading-relaxed">
              {experience.pitfallWarning}
            </p>
          </div>
        )}
      </div>

      {/* Metrics Footer */}
      <div className="pt-3 border-t border-[#242422] flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5" title="Asymmetric EMA Trust Score (St)">
            <Shield size={13} className="text-[#4EAA79]" />
            <span className="font-mono font-semibold text-[#EDECE8]">
              {trustPct}%
            </span>
          </div>
          <div className="flex items-center gap-1 text-[#7E7D77] font-mono text-[11px]" title="Uses and Empirical Success Rate">
            <Cpu size={12} />
            <span>{experience.usesCount} uses</span>
            <span>({successRate}% win)</span>
          </div>
        </div>

        {/* Quarantine Failures Counter if any */}
        {experience.consecutiveFailures > 0 && (
          <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-[#2E1E1E] text-[#D9534F] border border-[#4E2A2A]" title="Consecutive failures toward Theorem 1 quarantine threshold k*=3">
            k={experience.consecutiveFailures}/3
          </span>
        )}
      </div>
    </div>
  )
}
