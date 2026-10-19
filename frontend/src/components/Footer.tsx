import { ExternalLink, Github } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="border-t py-12 transition-colors
      bg-[#FFFFFF] border-[#E6E6E1] text-[#18181B]
      dark:bg-[#0C0E14] dark:border-[#252B3B] dark:text-[#F4F4F6]"
    >
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Col 1: Identity & Authors */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-indigo-600 flex items-center justify-center text-white font-mono font-bold text-xs">
                Æ
              </div>
              <span className="font-semibold text-sm">AEMA</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-md leading-relaxed">
              Reliability-Aware Experiential Memory for Autonomous AI Agents. Isolating negative transfer via Asymmetric Exponential Moving Average (A-EMA) and Theorem 1 Deterministic Quarantine.
            </p>
            <div className="text-xs text-zinc-600 dark:text-zinc-400 pt-1">
              Co-developed & researched by{' '}
              <a
                href="https://github.com/Sumit-ai-dev"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                Sumit Das (@Sumit-ai-dev)
              </a>{' '}
              and{' '}
              <a
                href="https://github.com/SakshiKasat18"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                Kasat Sakshi Dattaprasad (@SakshiKasat18)
              </a>.
            </div>
          </div>

          {/* Col 2: Packages & Ecosystem */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-3">
              Packages & Ecosystem
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://pypi.org/project/aema/0.1.0/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-zinc-600 hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-indigo-400 transition-colors"
                >
                  <span>PyPI: aema 0.1.0</span>
                  <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a
                  href="https://www.npmjs.com/package/aema-memory"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-zinc-600 hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-indigo-400 transition-colors"
                >
                  <span>npm: aema-memory 0.1.0</span>
                  <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-zinc-600 hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-indigo-400 transition-colors"
                >
                  <Github size={12} />
                  <span>GitHub Repository</span>
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Research & Reproducibility */}
          <div>
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-3">
              Research Proofs
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://huggingface.co/spaces/sumitaidev/adaptive-agent-memory-playground"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-zinc-600 hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-indigo-400 transition-colors"
                >
                  <span>Hugging Face Space</span>
                  <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a
                  href="https://www.kaggle.com/datasets/sumitdevai/agent-memory-resilience-benchmark"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-zinc-600 hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-indigo-400 transition-colors"
                >
                  <span>Kaggle Benchmark Dataset</span>
                  <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <a
                  href="https://huggingface.co/datasets/sumitaidev/agent-memory-resilience-benchmark"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-zinc-600 hover:text-indigo-600 dark:text-zinc-400 dark:hover:text-indigo-400 transition-colors"
                >
                  <span>Hugging Face Dataset</span>
                  <ExternalLink size={11} />
                </a>
              </li>
              <li>
                <span className="text-zinc-400 text-[11px] font-mono">
                  IEEE Conference Pre-registration
                </span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-[#E6E6E1] dark:border-[#252B3B] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-zinc-400">
          <div>
            © 2026 AEMA Contributors · Open Source under MIT License
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>PyPI & npm Released</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
