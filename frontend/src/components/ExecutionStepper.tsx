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
    <div className="rounded-2xl border p-5 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] space-y-6">
      {/* Step Indicators Rail */}
      <div className="grid grid-cols-5 gap-2 sm:gap-3">
        {STAGES.map((step, idx) => {
          const isDone = currentIndex > idx
          const isActive = currentIndex === idx

          const IconComponent = step.icon

          return (
            <div key={step.id} className="flex flex-col items-center text-center">
              {/* Circle Node */}
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                  isDone
                    ? 'bg-emerald-500 text-white shadow-sm'
                    : isActive
                    ? 'bg-indigo-600 text-white shadow-md ring-4 ring-indigo-100 dark:ring-indigo-950/60 scale-105'
                    : 'bg-zinc-100 text-zinc-400 dark:bg-[#1A1F2C] dark:text-zinc-600 border border-[#E6E6E1] dark:border-[#252B3B]'
                }`}
              >
                {isActive ? (
                  <RefreshCw size={17} className="animate-spin" />
                ) : (
                  <IconComponent size={17} />
                )}
              </div>

              {/* Label */}
              <div className="mt-2">
                <span
                  className={`text-xs font-semibold block transition-colors ${
                    isActive
                      ? 'text-indigo-600 dark:text-indigo-400'
                      : isDone
                      ? 'text-[#18181B] dark:text-[#F4F4F6]'
                      : 'text-zinc-400 dark:text-zinc-600'
                  }`}
                >
                  {step.label}
                </span>
                <span className="hidden sm:block text-[10px] text-zinc-400 dark:text-zinc-500 line-clamp-1 mt-0.5">
                  {step.desc}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Progressive Stage Details Box */}
      {currentIndex >= 0 && (
        <div className="rounded-xl border p-4 text-xs font-mono bg-zinc-50 border-[#E6E6E1] dark:bg-[#1A1F2C] dark:border-[#252B3B] space-y-3 anim-fade-in">
          {/* Stage 1: Retrieval */}
          {currentIndex >= 0 && (
            <div className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                  [1. RETRIEVE]
                </span>{' '}
                {execution?.memoryEnabled ? (
                  execution?.retrievedExperiences?.length ? (
                    <span className="text-zinc-600 dark:text-zinc-400">
                      Query matched {execution.retrievedExperiences.length} candidate(s) (ID: {execution.retrievedExperiences.map(e => e.experience.id.slice(0, 8)).join(', ')}). Top strategy:{' '}
                      <strong className="text-emerald-700 dark:text-emerald-300">
                        "{execution.retrievedExperiences[0].experience.strategyLesson.slice(0, 80)}..."
                      </strong>{' '}
                      (Sim: {execution.retrievedExperiences[0].similarityScore.toFixed(2)}, Trust S₀={(execution.retrievedExperiences[0].empiricalTrust * 100).toFixed(1)}%)
                    </span>
                  ) : execution ? (
                    <span className="text-zinc-500">
                      Zero prior experiences passed trust and similarity thresholds (similarity &gt; 0.60, trust &ge; 0.35).
                    </span>
                  ) : (
                    <span className="text-zinc-500">Searching vector index with similarity &gt; 0.60...</span>
                  )
                ) : (
                  <span className="text-zinc-500">
                    Baseline mode active (Memory disabled). No historical trajectories retrieved.
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Stage 2: Execution */}
          {currentIndex >= 1 && (
            <div className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                  [2. EXECUTE]
                </span>{' '}
                <span className="text-zinc-600 dark:text-zinc-400">
                  {execution ? (
                    `Execution completed. Latency: ${execution.latencyMs}ms · Tokens consumed: ${execution.tokensUsed}`
                  ) : (
                    'Dispatching reasoning prompt through model gateway...'
                  )}
                </span>
              </div>
            </div>
          )}

          {/* Stage 3: Evaluation */}
          {currentIndex >= 2 && (
            <div className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                  [3. EVALUATE]
                </span>{' '}
                <span className="text-zinc-600 dark:text-zinc-400">
                  {execution ? (
                    <>
                      Outcome validated as:{' '}
                      <strong
                        className={
                          execution.outcomeQuality === 'positive'
                            ? 'text-emerald-600 dark:text-emerald-400 uppercase font-bold'
                            : 'text-rose-600 dark:text-rose-400 uppercase font-bold'
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
            <div className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
              <div>
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                  [4. REFLECT]
                </span>{' '}
                <span className="text-zinc-600 dark:text-zinc-400">
                  {execution?.reflectionLesson ||
                    'Distilling trajectory into structured procedural memory tuple...'}
                </span>
              </div>
            </div>
          )}

          {/* Stage 5: Trust Update & Quarantine */}
          {currentIndex >= 4 && (
            <div className="flex items-start gap-2.5 pt-1 border-t border-[#E6E6E1] dark:border-[#252B3B]">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
              <div className="w-full">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                  [5. A-EMA TRUST UPDATE]
                </span>{' '}
                {execution?.trustUpdates && execution.trustUpdates.length > 0 ? (
                  execution.trustUpdates.map((tu, i) => (
                    <div key={i} className="mt-1 p-2 rounded bg-white dark:bg-[#131722] border border-[#E6E6E1] dark:border-[#252B3B]">
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-500">
                          Memory <code className="text-indigo-600 dark:text-indigo-400 font-semibold">{tu.experienceId.slice(0, 8)}</code>: <code className="text-zinc-600 dark:text-zinc-400">{tu.formulaApplied}</code>
                        </span>
                        <span className="font-bold">
                          {(tu.oldScore * 100).toFixed(1)}% → {(tu.newScore * 100).toFixed(1)}%
                          <span className={tu.delta >= 0 ? 'text-emerald-600 ml-1.5' : 'text-rose-600 ml-1.5'}>
                            ({tu.delta >= 0 ? '+' : ''}{(tu.delta * 100).toFixed(1)}%)
                          </span>
                        </span>
                      </div>
                      {tu.isQuarantined && (
                        <div className="mt-1 flex items-center gap-1.5 text-rose-600 dark:text-rose-400 font-bold">
                          <AlertCircle size={14} />
                          <span>Theorem 1 Deterministic Quarantine Triggered (St &lt; θ=0.35)</span>
                        </div>
                      )}
                    </div>
                  ))
                ) : execution ? (
                  <span className="text-zinc-500 italic block mt-0.5">
                    No retrieved memories were exposed for this task; existing memory bank trust scores remain unchanged.
                  </span>
                ) : (
                  <span className="text-zinc-500 italic block mt-0.5">
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
