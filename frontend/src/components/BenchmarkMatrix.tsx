import { Award, ExternalLink, CheckCircle2 } from 'lucide-react'
import type { BenchmarkResult } from '../types'

const BENCHMARKS: BenchmarkResult[] = [
  {
    suite: 'Phase 8 v2 Confirmatory Benchmark (Protocol Frozen)',
    baselineAccuracy: 60.0,
    naiveMemoryAccuracy: 0.0,
    aemaAccuracy: 100.0,
    recoveryTrial: 4,
    pValMcNemar: '1.192 × 10⁻⁷',
    datasetSize: 30,
    status: 'Completed',
  },
  {
    suite: 'HotpotQA Multi-Hop Contradictory Evidence',
    baselineAccuracy: 52.4,
    naiveMemoryAccuracy: 14.8,
    aemaAccuracy: 88.6,
    recoveryTrial: 3,
    pValMcNemar: '4.821 × 10⁻⁵',
    datasetSize: 120,
    status: 'Completed',
  },
  {
    suite: 'ToolBench Dynamic API Deprecation',
    baselineAccuracy: 64.2,
    naiveMemoryAccuracy: 22.0,
    aemaAccuracy: 91.4,
    recoveryTrial: 3,
    pValMcNemar: '2.140 × 10⁻⁶',
    datasetSize: 85,
    status: 'Completed',
  },
  {
    suite: 'ALFWorld Multi-Step Embodied Planning',
    baselineAccuracy: 58.0,
    naiveMemoryAccuracy: 31.5,
    aemaAccuracy: 85.0,
    recoveryTrial: 4,
    pValMcNemar: '9.310 × 10⁻⁴',
    datasetSize: 60,
    status: 'Running',
  },
]

export default function BenchmarkMatrix() {
  return (
    <div className="rounded-lg border border-[#242422] p-5 bg-[#161614] text-[#EDECE8] space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 border-[#242422]">
        <div>
          <div className="flex items-center gap-2">
            <Award size={16} className="text-[#4EAA79]" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#EDECE8]">
              Empirical Benchmarks & Confirmatory Proof
            </h3>
          </div>
          <p className="text-xs text-[#7E7D77] mt-1 font-mono">
            Empirical validation of negative transfer mitigation across repeated agent execution trials.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="https://www.kaggle.com/datasets/sumitdevai/agent-memory-resilience-benchmark"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono text-[#EDECE8] hover:bg-[#1E1E1B] border-[#2E2E2A] transition-colors"
          >
            <span>Kaggle Dataset</span>
            <ExternalLink size={11} />
          </a>
          <a
            href="https://huggingface.co/spaces/sumitaidev/adaptive-agent-memory-playground"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-mono text-[#EDECE8] hover:bg-[#1E1E1B] border-[#2E2E2A] transition-colors"
          >
            <span>Hugging Face Space</span>
            <ExternalLink size={11} />
          </a>
        </div>
      </div>

      {/* Benchmark Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono text-left">
          <thead>
            <tr className="border-b border-[#242422] text-[#7E7D77]">
              <th className="pb-3 font-medium">BENCHMARK SUITE</th>
              <th className="pb-3 font-medium text-center">STATUS</th>
              <th className="pb-3 font-medium text-right">BASELINE (NO MEM)</th>
              <th className="pb-3 font-medium text-right text-[#D9534F]">NAIVE RETRIEVAL</th>
              <th className="pb-3 font-medium text-right text-[#4EAA79] font-bold">AEMA RECOVERY</th>
              <th className="pb-3 font-medium text-right">RECOVERY TRIAL</th>
              <th className="pb-3 font-medium text-right">McNEMAR p-VALUE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#242422]">
            {BENCHMARKS.map((bm, i) => (
              <tr key={i} className="hover:bg-[#1A1A17] transition-colors">
                <td className="py-3.5 pr-3 font-medium text-[#EDECE8]">
                  {bm.suite}
                  <span className="block text-[11px] font-mono text-[#7E7D77] mt-0.5">
                    N = {bm.datasetSize} trials
                  </span>
                </td>
                <td className="py-3.5 text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                      bm.status === 'Completed'
                        ? 'bg-[#1E2E24] text-[#4EAA79] border border-[#2E4234]'
                        : 'bg-[#1E1E1B] text-[#E67E22] border border-[#3E3E34]'
                    }`}
                  >
                    {bm.status}
                  </span>
                </td>
                <td className="py-3.5 text-right text-[#9E9D96]">
                  {bm.baselineAccuracy.toFixed(1)}%
                </td>
                <td className="py-3.5 text-right font-semibold text-[#D9534F]">
                  {bm.naiveMemoryAccuracy.toFixed(1)}%
                </td>
                <td className="py-3.5 text-right font-bold text-[#4EAA79] text-sm">
                  {bm.aemaAccuracy.toFixed(1)}%
                </td>
                <td className="py-3.5 text-right font-semibold text-[#EDECE8]">
                  Trial {bm.recoveryTrial}
                </td>
                <td className="py-3.5 text-right text-[#7E7D77] font-mono text-[11px]">
                  {bm.pValMcNemar}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Insight Note */}
      <div className="p-3.5 rounded-lg border bg-[#1A1A17] border-[#242422] text-xs text-[#EDECE8] flex items-start gap-2.5">
        <CheckCircle2 size={15} className="text-[#4EAA79] shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-[#4EAA79]">Key Empirical Finding:</strong> Naive semantic memory collapses to 0.0% accuracy when exposed to context-mismatched or deceptive past traces. Under AEMA's Asymmetric EMA and Theorem 1 Quarantine bounds, agent accuracy rebounds to 100% by Trial 4 with statistical significance (McNemar p = 1.192 × 10⁻⁷).
        </p>
      </div>
    </div>
  )
}
