import { useState, useMemo } from 'react'
import { ShieldAlert, RefreshCw, CheckCircle, Calculator } from 'lucide-react'

export default function TheoremSandbox() {
  const [alpha, setAlpha] = useState(0.85)
  const [beta, setBeta] = useState(0.70)
  const [theta, setTheta] = useState(0.35)
  const [s0, setS0] = useState(0.75)
  const [simFailures, setSimFailures] = useState(0)

  // Theorem 1 deterministic bound calculation: k* = ceil((ln(theta) - ln(S0)) / ln(beta))
  const kStar = useMemo(() => {
    if (beta >= 1.0 || beta <= 0 || theta <= 0 || s0 <= 0 || theta >= s0) return 0
    const numerator = Math.log(theta) - Math.log(s0)
    const denominator = Math.log(beta)
    return Math.ceil(numerator / denominator)
  }, [beta, theta, s0])

  // Trust trajectory over consecutive failures
  const trajectory = useMemo(() => {
    const steps = []
    let currentTrust = s0
    steps.push({ step: 0, trust: currentTrust, quarantined: currentTrust < theta })

    for (let i = 1; i <= Math.max(kStar + 1, 5); i++) {
      currentTrust = currentTrust * beta
      steps.push({
        step: i,
        trust: currentTrust,
        quarantined: currentTrust < theta,
      })
    }
    return steps
  }, [s0, beta, theta, kStar])

  const currentSimTrust = Math.max(0, s0 * Math.pow(beta, simFailures))
  const isCurrentlyQuarantined = currentSimTrust < theta

  return (
    <div className="rounded-lg border border-[#242422] p-5 bg-[#161614] text-[#EDECE8] space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-4 border-[#242422]">
        <div>
          <div className="flex items-center gap-2">
            <Calculator size={16} className="text-[#4EAA79]" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#EDECE8]">
              Theorem 1 Deterministic Quarantine Sandbox
            </h3>
          </div>
          <p className="text-xs text-[#7E7D77] mt-1 font-mono">
            Isolating negative transfer within exactly <code className="font-mono font-bold text-[#4EAA79]">k*</code> consecutive failures.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-3 py-1 rounded-lg border bg-[#141412] border-[#2E2E2A] text-[#EDECE8]">
            Theorem 1 Bound: <strong className="text-[#4EAA79]">k* = {kStar} Failures</strong>
          </span>
        </div>
      </div>

      {/* Hyperparameter Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs font-mono">
        <div>
          <label className="block text-[#9E9D96] mb-1">
            Success Momentum (α): <strong className="text-[#EDECE8]">{alpha.toFixed(2)}</strong>
          </label>
          <input
            type="range"
            min="0.50"
            max="0.95"
            step="0.01"
            value={alpha}
            onChange={(e) => setAlpha(parseFloat(e.target.value))}
            className="w-full accent-[#4EAA79] cursor-pointer"
          />
        </div>

        <div>
          <label className="block text-[#9E9D96] mb-1">
            Failure Penalty (β): <strong className="text-[#EDECE8]">{beta.toFixed(2)}</strong>
          </label>
          <input
            type="range"
            min="0.40"
            max="0.90"
            step="0.01"
            value={beta}
            onChange={(e) => setBeta(parseFloat(e.target.value))}
            className="w-full accent-[#D9534F] cursor-pointer"
          />
        </div>

        <div>
          <label className="block text-[#9E9D96] mb-1">
            Quarantine Threshold (θ): <strong className="text-[#EDECE8]">{theta.toFixed(2)}</strong>
          </label>
          <input
            type="range"
            min="0.10"
            max="0.60"
            step="0.01"
            value={theta}
            onChange={(e) => setTheta(parseFloat(e.target.value))}
            className="w-full accent-[#E67E22] cursor-pointer"
          />
        </div>

        <div>
          <label className="block text-[#9E9D96] mb-1">
            Initial Trust (S₀): <strong className="text-[#EDECE8]">{s0.toFixed(2)}</strong>
          </label>
          <input
            type="range"
            min="0.50"
            max="1.00"
            step="0.01"
            value={s0}
            onChange={(e) => setS0(parseFloat(e.target.value))}
            className="w-full accent-[#EDECE8] cursor-pointer"
          />
        </div>
      </div>

      {/* Mathematical Proof Visualizer */}
      <div className="p-4 rounded-lg border bg-[#141412] border-[#242422] space-y-3">
        <div className="text-xs font-mono text-[#9E9D96] flex items-center justify-between">
          <span>Formula: <code className="text-[#4EAA79]">k* = ⌈(ln θ - ln S₀) / ln β⌉</code></span>
          <span>= ⌈(ln({theta.toFixed(2)}) - ln({s0.toFixed(2)})) / ln({beta.toFixed(2)})⌉ = <strong className="text-[#EDECE8]">{kStar}</strong></span>
        </div>

        {/* Trajectory Table / Steps */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
          {trajectory.slice(0, 5).map((step) => (
            <div
              key={step.step}
              className={`p-2.5 rounded-lg border text-center font-mono text-xs transition-all ${
                step.quarantined
                  ? 'bg-[#2E1E1E] border-[#4E2A2A] text-[#D9534F]'
                  : 'bg-[#181816] border-[#2E2E2A] text-[#EDECE8]'
              }`}
            >
              <div className="text-[10px] text-[#7E7D77]">
                {step.step === 0 ? 'Initial (t=0)' : `Failure ${step.step}`}
              </div>
              <div className="text-sm font-bold mt-1">
                {(step.trust * 100).toFixed(1)}%
              </div>
              <div className="text-[10px] mt-1 font-semibold">
                {step.quarantined ? 'QUARANTINED' : 'ACTIVE'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive Failure Simulation Tester */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-3">
          <div className="text-xs font-mono text-[#9E9D96]">
            Simulated Failures: <strong className="text-[#EDECE8]">{simFailures}</strong>
          </div>
          <div className="text-xs font-mono text-[#9E9D96]">
            Current St: <strong className={isCurrentlyQuarantined ? 'text-[#D9534F]' : 'text-[#4EAA79]'}>
              {(currentSimTrust * 100).toFixed(1)}%
            </strong>
          </div>
          {isCurrentlyQuarantined ? (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded border border-[#4E2A2A] bg-[#2E1E1E] text-[#D9534F] font-semibold flex items-center gap-1">
              <ShieldAlert size={12} />
              Quarantined
            </span>
          ) : (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded border border-[#2E4234] bg-[#1E2E24] text-[#4EAA79] font-semibold flex items-center gap-1">
              <CheckCircle size={12} />
              Active in Retrieval
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setSimFailures((f) => f + 1)}
            className="px-3 py-1.5 rounded-lg text-xs font-mono font-medium text-white bg-[#D9534F] hover:bg-[#c8433f] transition-colors cursor-pointer"
          >
            +1 Simulated Failure
          </button>
          <button
            onClick={() => setSimFailures(0)}
            className="p-1.5 rounded-lg border text-[#7E7D77] hover:text-[#EDECE8] border-[#2E2E2A] bg-[#141412] cursor-pointer"
            title="Reset failures"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
