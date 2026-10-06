import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Activity,
  Search,
  Cpu,
  CheckCircle2,
  Brain,
  ShieldCheck,
  Clock,
  Layers,
} from 'lucide-react'
import { ExecutionStepTrace } from '../../types'

interface ExecutionTraceViewProps {
  trajectory?: ExecutionStepTrace[]
  latencyMs?: number
  tokensUsed?: number
  outcomeScore?: number
}

export default function ExecutionTraceView({
  trajectory = [],
  latencyMs,
  tokensUsed,
  outcomeScore,
}: ExecutionTraceViewProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [expandedStepIndex, setExpandedStepIndex] = useState<number | null>(null)

  if (!trajectory || trajectory.length === 0) {
    return null
  }

  const toggleStep = (idx: number) => {
    setExpandedStepIndex((prev) => (prev === idx ? null : idx))
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-[#0d0217]/80 backdrop-blur-md overflow-hidden text-xs">
      {/* Header bar / accordion trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-white/5 hover:bg-white/10 transition-colors text-left cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <Layers size={14} className="text-purple-400" />
          <span className="font-display font-semibold text-white tracking-tight text-xs">
            Cognitive Execution Trace
          </span>
          <span className="px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/30 text-[10px] font-mono text-purple-300">
            {trajectory.length} steps
          </span>
        </div>

        <div className="flex items-center gap-4 text-white/50 font-mono text-[11px]">
          {latencyMs !== undefined && (
            <span className="flex items-center gap-1">
              <Clock size={11} />
              {latencyMs}ms
            </span>
          )}
          {tokensUsed !== undefined && (
            <span className="flex items-center gap-1">
              <Cpu size={11} />
              {tokensUsed} tokens
            </span>
          )}
          {outcomeScore !== undefined && (
            <span className="text-emerald-400">
              Score: {(outcomeScore * 100).toFixed(0)}%
            </span>
          )}
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {/* Expanded Trace Body */}
      {isOpen && (
        <div className="p-4 border-t border-white/10 space-y-2.5">
          <div className="text-[11px] text-white/40 font-mono uppercase tracking-wider mb-2">
            5-Node StateGraph Lifecycle
          </div>

          <div className="relative pl-6 space-y-3 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-white/10">
            {trajectory.map((step, idx) => {
              const isExpanded = expandedStepIndex === idx
              const icon = getNodeIcon(step.node || step.type)

              return (
                <div key={step.id || idx} className="relative group">
                  {/* Step node indicator icon */}
                  <div className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-[#120022] border border-purple-500/40 flex items-center justify-center text-purple-300 shadow">
                    {icon}
                  </div>

                  {/* Step row */}
                  <div
                    onClick={() => toggleStep(idx)}
                    className="p-2.5 rounded-xl border border-white/5 hover:border-white/15 bg-white/[0.03] hover:bg-white/[0.06] transition-all cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-purple-300 font-semibold text-[11px]">
                          {formatNodeName(step.node || step.type)}
                        </span>
                        <span className="text-white font-medium text-xs">
                          {step.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-white/40">
                        {step.durationMs !== undefined && (
                          <span>{step.durationMs}ms</span>
                        )}
                        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      </div>
                    </div>

                    {/* Step detail expansion */}
                    {isExpanded && (
                      <div className="mt-2.5 pt-2 border-t border-white/10 text-white/70 font-sans text-xs space-y-1.5">
                        <p className="leading-relaxed whitespace-pre-wrap">{step.detail}</p>
                        {step.toolsCalled && step.toolsCalled.length > 0 && (
                          <div className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-300">
                            <span>Tools called:</span>
                            {step.toolsCalled.map((t, tidx) => (
                              <span
                                key={tidx}
                                className="px-1.5 py-0.5 rounded bg-cyan-500/15 border border-cyan-500/30"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function getNodeIcon(nodeName?: string) {
  const n = (nodeName || '').toLowerCase()
  if (n.includes('retrieve')) return <Search size={10} />
  if (n.includes('execute')) return <Cpu size={10} />
  if (n.includes('evaluate')) return <CheckCircle2 size={10} />
  if (n.includes('reflect')) return <Brain size={10} />
  if (n.includes('trust')) return <ShieldCheck size={10} />
  return <Activity size={10} />
}

function formatNodeName(nodeName?: string): string {
  const n = (nodeName || '').toLowerCase()
  if (n.includes('retrieve')) return 'retrieve_node'
  if (n.includes('execute')) return 'execute_node'
  if (n.includes('evaluate')) return 'evaluate_node'
  if (n.includes('reflect')) return 'reflect_node'
  if (n.includes('trust')) return 'trust_node'
  return nodeName || 'step'
}
