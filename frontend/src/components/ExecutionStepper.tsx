import { CheckCircle2, AlertCircle, RefreshCw, Database, Shield, Zap, Terminal } from 'lucide-react'
import type { TaskExecution, ExecutionNode } from '../types'

interface ExecutionStepperProps {
  currentStage: ExecutionNode | 'idle' | 'complete'
  execution?: TaskExecution | null
  activeExperience?: any | null
}

const STAGES: { id: ExecutionNode; label: string; desc: string; icon: any }[] = [
  { id: 'retrieval', label: 'Retrieve', desc: 'Semantic search & trust filtering', icon: Database },
  { id: 'execution', label: 'Execute', desc: 'Strategy context injection & generation', icon: Terminal },
  { id: 'evaluation', label: 'Evaluate', desc: 'Rigorous objective outcome validation', icon: CheckCircle2 },
  { id: 'reflection', label: 'Reflect', desc: 'Differential trajectory critique', icon: Zap },
  { id: 'trust_update', label: 'Trust Update', desc: 'Asymmetric EMA & Theorem 1 Quarantine', icon: Shield },
]

export default function ExecutionStepper({
  currentStage,
  execution,
}: ExecutionStepperProps) {
  const getStageIndex = (stage: ExecutionNode | 'idle' | 'complete') => {
    if (stage === 'idle') return -1
    if (stage === 'complete') return 5
    return STAGES.findIndex((s) => s.id === stage)
  }

  const currentIndex = getStageIndex(currentStage)

  return (
    <div className="rounded-lg border border-[#1E1E1C] p-3 bg-[#11110F] text-[#EDECE8] space-y-3">
      {/* Sleek Step Indicators Rail */}
      <div className="flex items-center justify-between px-1">
        {STAGES.map((step, idx) => {
          const isDone = currentIndex > idx
          const isActive = currentIndex === idx

          return (
            <div key={step.id} className="flex-1 flex flex-col items-center relative">
              {/* Connector Line between steps */}
              {idx < STAGES.length - 1 && (
                <div
                  className={`absolute top-2.5 left-1/2 w-full h-px ${
                    currentIndex > idx ? 'bg-[#3A4D3E]' : 'bg-[#1E1E1C]'
                  }`}
                />
              )}

              {/* Node Indicator */}
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-mono relative z-10 transition-colors ${
                  isDone
                    ? 'bg-[#142219] text-[#4EAA79] border border-[#2E4234]'
                    : isActive
                    ? 'bg-[#22221E] text-white border border-[#EDECE8]'
                    : 'bg-[#141412] text-[#555550] border border-[#20201E]'
                }`}
              >
                {isActive ? (
                  <RefreshCw size={10} className="animate-spin text-[#E67E22]" />
                ) : isDone ? (
                  <span>✓</span>
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>

              {/* Label */}
              <span
                className={`text-[10px] font-mono mt-1 truncate ${
                  isActive ? 'text-[#EDECE8] font-semibold' : isDone ? 'text-[#8E8D88]' : 'text-[#555550]'
                }`}
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Progressive Stage Details Box */}
      {currentIndex >= 0 && (
        <div className="rounded border border-[#1A1A18] p-2.5 text-[11px] font-mono bg-[#0C0C0B] text-[#EDECE8] space-y-2">
          {/* Stage 1: Retrieval */}
          {currentIndex >= 0 && (
            <div className="flex items-start gap-1.5 leading-tight">
              <span className="w-1 h-1 rounded-full bg-[#555550] mt-1.5 shrink-0" />
              <div>
                <span className="text-[#8E8D88]">[1. RETRIEVE]</span>{' '}
                {execution?.memoryEnabled ? (
                  execution?.retrievedExperiences?.length ? (
                    <span className="text-[#9E9D96]">
                      Query matched {execution.retrievedExperiences.length} candidate(s). Top strategy:{' '}
                      <strong className="text-[#EDECE8]">
                        "{execution.retrievedExperiences[0].experience.strategyLesson.slice(0, 70)}..."
                      </strong>{' '}
                      (Sim: {execution.retrievedExperiences[0].similarityScore.toFixed(2)}, Trust S₀={(execution.retrievedExperiences[0].empiricalTrust * 100).toFixed(1)}%)
                    </span>
                  ) : execution ? (
                    <span className="text-[#666660]">
                      Zero prior experiences passed trust threshold (similarity &gt; 0.60, trust &ge; 0.35).
                    </span>
                  ) : (
                    <span className="text-[#666660]">Searching vector index with similarity &gt; 0.60...</span>
                  )
                ) : (
                  <span className="text-[#666660]">
                    Baseline mode active (Memory disabled). No historical trajectories retrieved.
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Stage 2: Execution */}
          {currentIndex >= 1 && (
            <div className="flex items-start gap-1.5 leading-tight">
              <span className="w-1 h-1 rounded-full bg-[#555550] mt-1.5 shrink-0" />
              <div>
                <span className="text-[#8E8D88]">[2. EXECUTE]</span>{' '}
                <span className="text-[#9E9D96]">
                  {execution ? (
                    `Execution completed (${execution.latencyMs}ms · ${execution.tokensUsed} tokens)`
                  ) : (
                    'Dispatching reasoning prompt through model gateway...'
                  )}
                </span>
              </div>
            </div>
          )}

          {/* Stage 3: Evaluation */}
          {currentIndex >= 2 && (
            <div className="flex items-start gap-1.5 leading-tight">
              <span className="w-1 h-1 rounded-full bg-[#555550] mt-1.5 shrink-0" />
              <div>
                <span className="text-[#8E8D88]">[3. EVALUATE]</span>{' '}
                <span className="text-[#9E9D96]">
                  {execution ? (
                    <>
                      Outcome validated as{' '}
                      <strong
                        className={
                          execution.outcomeQuality === 'positive' || (execution.outcomeScore && execution.outcomeScore >= 0.7)
                            ? 'text-[#4EAA79]'
                            : 'text-[#D9534F]'
                        }
                      >
                        {execution.outcomeQuality ? execution.outcomeQuality.toUpperCase() : 'COMPLETED'}
                      </strong>
                      {' '}via deterministic verification.
                    </>
                  ) : (
                    'Evaluating trajectory against objective criteria...'
                  )}
                </span>
              </div>
            </div>
          )}

          {/* Stage 4: Reflection */}
          {currentIndex >= 3 && (
            <div className="flex items-start gap-1.5 leading-tight">
              <span className="w-1 h-1 rounded-full bg-[#555550] mt-1.5 shrink-0" />
              <div>
                <span className="text-[#8E8D88]">[4. REFLECT]</span>{' '}
                <span className="text-[#9E9D96]">
                  {execution?.reflectionLesson ||
                    'Distilling trajectory into structured procedural memory tuple...'}
                </span>
              </div>
            </div>
          )}

          {/* Stage 5: Trust Update & Quarantine */}
          {currentIndex >= 4 && (
            <div className="flex items-start gap-1.5 leading-tight pt-1.5 border-t border-[#1C1C1A]">
              <span className="w-1 h-1 rounded-full bg-[#555550] mt-1.5 shrink-0" />
              <div className="w-full">
                <span className="text-[#8E8D88]">[5. A-EMA TRUST UPDATE]</span>{' '}
                {execution?.trustUpdates && execution.trustUpdates.length > 0 ? (
                  execution.trustUpdates.map((tu, i) => (
                    <div key={i} className="mt-1 p-1.5 rounded bg-[#131311] border border-[#1E1E1C]">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-[#7E7D77]">
                          Memory <code className="text-[#EDECE8]">{tu.experienceId.slice(0, 8)}</code>: <code className="text-[#9E9D96]">{tu.formulaApplied}</code>
                        </span>
                        <span className="font-semibold text-[#EDECE8]">
                          {(tu.oldScore * 100).toFixed(1)}% → {(tu.newScore * 100).toFixed(1)}%
                          <span className={tu.delta >= 0 ? 'text-[#4EAA79] ml-1' : 'text-[#D9534F] ml-1'}>
                            ({tu.delta >= 0 ? '+' : ''}{(tu.delta * 100).toFixed(1)}%)
                          </span>
                        </span>
                      </div>
                      {tu.isQuarantined && (
                        <div className="mt-1 flex items-center gap-1 text-[#D9534F] text-[10px] font-semibold">
                          <AlertCircle size={11} />
                          <span>Theorem 1 Deterministic Quarantine Triggered (St &lt; 0.35)</span>
                        </div>
                      )}
                    </div>
                  ))
                ) : execution ? (
                  <span className="text-[#666660] italic block mt-0.5">
                    No retrieved memories were exposed; trust scores remain unchanged.
                  </span>
                ) : (
                  <span className="text-[#666660] italic block mt-0.5">
                    Computing Asymmetric EMA trust update...
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
