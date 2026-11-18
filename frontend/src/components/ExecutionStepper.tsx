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
    <div className="rounded-lg border border-[#242422] p-4 bg-[#161614] text-[#EDECE8] space-y-4">
      {/* Step Indicators Rail */}
      <div className="grid grid-cols-5 gap-2">
        {STAGES.map((step, idx) => {
          const isDone = currentIndex > idx
          const isActive = currentIndex === idx

          const IconComponent = step.icon

          return (
            <div key={step.id} className="flex flex-col items-center text-center">
              {/* Circle Node */}
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                  isDone
                    ? 'bg-[#1E2E24] text-[#4EAA79] border border-[#2E4234]'
                    : isActive
                    ? 'bg-[#22221E] text-white border border-[#4EAA79] ring-2 ring-[#4EAA79]/20'
                    : 'bg-[#141412] text-[#7E7D77] border border-[#242422]'
                }`}
              >
                {isActive ? (
                  <RefreshCw size={14} className="animate-spin text-[#E67E22]" />
                ) : (
                  <IconComponent size={14} />
                )}
              </div>

              {/* Label */}
              <div className="mt-1.5">
                <span
                  className={`text-[11px] font-mono font-medium block truncate ${
                    isActive
                      ? 'text-[#EDECE8]'
                      : isDone
                      ? 'text-[#4EAA79]'
                      : 'text-[#7E7D77]'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Progressive Stage Details Box */}
      {currentIndex >= 0 && (
        <div className="rounded-lg border border-[#242422] p-3 text-xs font-mono bg-[#141412] text-[#EDECE8] space-y-2.5">
          {/* Stage 1: Retrieval */}
          {currentIndex >= 0 && (
            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4EAA79] mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-[#EDECE8]">
                  [1. RETRIEVE]
                </span>{' '}
                {execution?.memoryEnabled ? (
                  execution?.retrievedExperiences?.length ? (
                    <span className="text-[#9E9D96]">
                      Query matched {execution.retrievedExperiences.length} candidate(s). Top strategy:{' '}
                      <strong className="text-[#4EAA79]">
                        "{execution.retrievedExperiences[0].experience.strategyLesson.slice(0, 80)}..."
                      </strong>{' '}
                      (Sim: {execution.retrievedExperiences[0].similarityScore.toFixed(2)}, Trust S₀={(execution.retrievedExperiences[0].empiricalTrust * 100).toFixed(1)}%)
                    </span>
                  ) : execution ? (
                    <span className="text-[#7E7D77]">
                      Zero prior experiences passed trust threshold (similarity &gt; 0.60, trust &ge; 0.35).
                    </span>
                  ) : (
                    <span className="text-[#7E7D77]">Searching vector index with similarity &gt; 0.60...</span>
                  )
                ) : (
                  <span className="text-[#7E7D77]">
                    Baseline mode active (Memory disabled). No historical trajectories retrieved.
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Stage 2: Execution */}
          {currentIndex >= 1 && (
            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E67E22] mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-[#EDECE8]">
                  [2. EXECUTE]
                </span>{' '}
                <span className="text-[#9E9D96]">
                  {execution ? (
                    `Execution completed. Latency: ${execution.latencyMs}ms · Tokens: ${execution.tokensUsed}`
                  ) : (
                    'Dispatching reasoning prompt through model gateway...'
                  )}
                </span>
              </div>
            </div>
          )}

          {/* Stage 3: Evaluation */}
          {currentIndex >= 2 && (
            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#4EAA79] mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-[#EDECE8]">
                  [3. EVALUATE]
                </span>{' '}
                <span className="text-[#9E9D96]">
                  {execution ? (
                    <>
                      Outcome validated as:{' '}
                      <strong
                        className={
                          execution.outcomeQuality === 'positive'
                            ? 'text-[#4EAA79] uppercase font-bold'
                            : 'text-[#D9534F] uppercase font-bold'
                        }
                      >
                        {execution.outcomeQuality || 'COMPLETED'}
                      </strong>
                      . Evaluated by backend deterministic verification engine.
                    </>
                  ) : (
                    'Evaluating trajectory against objective outcome criteria...'
                  )}
                </span>
              </div>
            </div>
          )}

          {/* Stage 4: Reflection */}
          {currentIndex >= 3 && (
            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#EDECE8] mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-[#EDECE8]">
                  [4. REFLECT]
                </span>{' '}
                <span className="text-[#9E9D96]">
                  {execution?.reflectionLesson ||
                    'Distilling trajectory into structured procedural memory tuple...'}
                </span>
              </div>
            </div>
          )}

          {/* Stage 5: Trust Update & Quarantine */}
          {currentIndex >= 4 && (
            <div className="flex items-start gap-2 pt-2 border-t border-[#242422]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E67E22] mt-1.5 shrink-0" />
              <div className="w-full">
                <span className="font-semibold text-[#EDECE8]">
                  [5. A-EMA TRUST UPDATE]
                </span>{' '}
                {execution?.trustUpdates && execution.trustUpdates.length > 0 ? (
                  execution.trustUpdates.map((tu, i) => (
                    <div key={i} className="mt-1 p-2 rounded bg-[#1A1A17] border border-[#242422]">
                      <div className="flex items-center justify-between">
                        <span className="text-[#7E7D77]">
                          Memory <code className="text-[#EDECE8] font-semibold">{tu.experienceId.slice(0, 8)}</code>: <code className="text-[#9E9D96]">{tu.formulaApplied}</code>
                        </span>
                        <span className="font-bold">
                          {(tu.oldScore * 100).toFixed(1)}% → {(tu.newScore * 100).toFixed(1)}%
                          <span className={tu.delta >= 0 ? 'text-[#4EAA79] ml-1.5' : 'text-[#D9534F] ml-1.5'}>
                            ({tu.delta >= 0 ? '+' : ''}{(tu.delta * 100).toFixed(1)}%)
                          </span>
                        </span>
                      </div>
                      {tu.isQuarantined && (
                        <div className="mt-1 flex items-center gap-1.5 text-[#D9534F] font-bold">
                          <AlertCircle size={13} />
                          <span>Theorem 1 Deterministic Quarantine Triggered (St &lt; θ=0.35)</span>
                        </div>
                      )}
                    </div>
                  ))
                ) : execution ? (
                  <span className="text-[#7E7D77] italic block mt-0.5">
                    No retrieved memories were exposed for this task; existing memory bank trust scores remain unchanged.
                  </span>
                ) : (
                  <span className="text-[#7E7D77] italic block mt-0.5">
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
