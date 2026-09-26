import { ArrowLeft, Scale, ShieldCheck, Terminal, AlertCircle, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0c0714] text-[#D0D5DD] font-sans antialiased selection:bg-[#7042DD]/30">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#0c0714]/80 border-b border-white/[0.08] px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-white hover:text-white/80 transition-colors">
            <ArrowLeft size={16} />
            <span className="text-sm font-medium">Back to Home</span>
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-[#7042DD] flex items-center justify-center text-white">
              <Scale size={14} />
            </div>
            <span className="text-white text-sm font-semibold">MemoryAgent Legal</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/[0.05] border border-white/[0.1] text-xs font-mono text-[#D0D5DD] mb-4">
            <Scale size={12} className="text-[#862FE7]" />
            <span>TERMS OF SERVICE & PLATFORM AGREEMENT</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-bold text-white tracking-tight mb-4">
            Terms and Conditions
          </h1>
          <p className="text-sm text-[#717171] font-mono">
            Last updated: September 26, 2026 | Effective Date: September 26, 2026
          </p>
        </div>

        <div className="space-y-10 text-sm leading-relaxed">
          {/* Section 1 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <Terminal size={18} className="text-[#862FE7]" />
              1. Acceptance of Terms
            </h2>
            <p className="mb-3">
              By accessing, integrating, or utilizing MemoryAgent APIs, SDKs, web dashboards, or background services, you agree to be bound by these Terms and Conditions. If you are entering into this agreement on behalf of an enterprise or organization, you represent that you possess the necessary authorization to bind that entity.
            </p>
          </section>

          {/* Section 2 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <ShieldCheck size={18} className="text-[#862FE7]" />
              2. Permitted Use and Agent Governance
            </h2>
            <p className="mb-3">
              MemoryAgent provides algorithmic memory indexing, Bayesian confidence scoring, and experience retrieval for autonomous agents. You agree not to:
            </p>
            <ul className="list-disc list-inside space-y-2 text-[#D0D5DD]/90">
              <li>Deploy MemoryAgent for malicious agentic activities, automated exploit generation, or unauthorized reconnaissance.</li>
              <li>Attempt to intentionally poison global memory indices through adversarial prompt injection or manipulated feedback loops.</li>
              <li>Reverse engineer or decompile the internal Bayesian bandit optimization algorithms or proprietary embeddings routing layer.</li>
              <li>Exceed stated rate limits or attempt denial-of-service vectors against shared vector index endpoints.</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <RefreshCw size={18} className="text-[#862FE7]" />
              3. Service Level and Retrieval Latency
            </h2>
            <p className="mb-3">
              We strive to maintain high-availability memory endpoints with sub-500ms retrieval latencies across global clusters. However, scheduled maintenance, upstream foundation model outages, or cloud infrastructure disruptions may affect real-time inference speeds.
            </p>
            <p>
              We provide no guarantee of continuous uninterrupted service for free development tiers or community installations.
            </p>
          </section>

          {/* Section 4 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <AlertCircle size={18} className="text-[#862FE7]" />
              4. Limitation of Liability
            </h2>
            <p className="mb-3">
              Autonomous agents execute nondeterministic reasoning paths. MemoryAgent provides historical grounding and probabilistic ranking, but does not warrant that agent actions, tool calls, or generated outputs will be entirely free of errors or hallucinations.
            </p>
            <p>
              Under no circumstances shall the project maintainers or developers be liable for direct, indirect, or consequential damages resulting from agent execution outcomes.
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/[0.08] py-8 px-6 text-center text-xs text-[#717171]">
        <p>&copy; 2026 MemoryAgent. Built by Kasat Sakshi Dattaprasad &amp; Sumit Das. All rights reserved.</p>
      </footer>
    </div>
  )
}
