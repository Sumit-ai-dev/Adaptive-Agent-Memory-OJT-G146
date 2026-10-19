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
    <div className="rounded-2xl border p-6 bg-white border-[#E6E6E1] dark:bg-[#131722] dark:border-[#252B3B] space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 border-[#E6E6E1] dark:border-[#252B3B]">
        <div>
          <div className="flex items-center gap-2">
            <Award size={18} className="text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-sm font-semibold text-[#18181B] dark:text-[#F4F4F6]">
              Empirical Benchmarks & Confirmatory Proof
            </h3>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Empirical validation of negative transfer mitigation across repeated agent execution trials.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="https://www.kaggle.com/datasets/sumitdevai/agent-memory-resilience-benchmark"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-medium text-zinc-600 hover:text-indigo-600 dark:text-zinc-300 dark:hover:text-indigo-400 border-[#E6E6E1] dark:border-[#252B3B] transition-colors"
          >
            <span>Kaggle Dataset</span>
            <ExternalLink size={12} />
          </a>
          <a
            href="https://huggingface.co/spaces/sumitaidev/adaptive-agent-memory-playground"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-medium text-zinc-600 hover:text-indigo-600 dark:text-zinc-300 dark:hover:text-indigo-400 border-[#E6E6E1] dark:border-[#252B3B] transition-colors"
          >
            <span>Hugging Face Space</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {/* Benchmark Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono text-left">
          <thead>
            <tr className="border-b border-[#E6E6E1] dark:border-[#252B3B] text-zinc-400 dark:text-zinc-500">
              <th className="pb-3 font-medium">BENCHMARK SUITE</th>
              <th className="pb-3 font-medium text-center">STATUS</th>
              <th className="pb-3 font-medium text-right">BASELINE (NO MEM)</th>
              <th className="pb-3 font-medium text-right text-rose-600 dark:text-rose-400">NAIVE RETRIEVAL</th>
              <th className="pb-3 font-medium text-right text-emerald-600 dark:text-emerald-400 font-bold">AEMA RECOVERY</th>
              <th className="pb-3 font-medium text-right">RECOVERY TRIAL</th>
              <th className="pb-3 font-medium text-right">McNEMAR p-VALUE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E6E6E1] dark:divide-[#252B3B]">
            {BENCHMARKS.map((bm, i) => (
              <tr key={i} className="hover:bg-zinc-50/50 dark:hover:bg-[#1A1F2C]/40 transition-colors">
                <td className="py-3.5 pr-3 font-sans font-medium text-[#18181B] dark:text-[#F4F4F6]">
                  {bm.suite}
                  <span className="block text-[11px] font-mono text-zinc-400 mt-0.5">
                    N = {bm.datasetSize} trials
                  </span>
                </td>
                <td className="py-3.5 text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                      bm.status === 'Completed'
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                        : 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                    }`}
                  >
                    {bm.status}
                  </span>
                </td>
                <td className="py-3.5 text-right text-zinc-600 dark:text-zinc-400">
                  {bm.baselineAccuracy.toFixed(1)}%
                </td>
                <td className="py-3.5 text-right font-semibold text-rose-600 dark:text-rose-400">
                  {bm.naiveMemoryAccuracy.toFixed(1)}%
                </td>
                <td className="py-3.5 text-right font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                  {bm.aemaAccuracy.toFixed(1)}%
                </td>
                <td className="py-3.5 text-right font-semibold text-indigo-600 dark:text-indigo-400">
                  Trial {bm.recoveryTrial}
                </td>
                <td className="py-3.5 text-right text-zinc-500 font-mono text-[11px]">
                  {bm.pValMcNemar}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Insight Note */}
      <div className="p-3.5 rounded-xl border bg-emerald-50/40 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/50 text-xs text-emerald-950 dark:text-emerald-200 flex items-start gap-2.5">
        <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Key Empirical Finding:</strong> Naive semantic memory collapses to 0.0% accuracy when exposed to context-mismatched or deceptive past traces. Under AEMA's Asymmetric EMA and Theorem 1 Quarantine bounds, agent accuracy rebounds to 100% by Trial 4 with statistical significance (McNemar p = 1.192 × 10⁻⁷).
        </p>
      </div>
    </div>
  )
}
