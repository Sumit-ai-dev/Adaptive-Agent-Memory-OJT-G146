import { ArrowLeft, Shield, Lock, Eye, FileText, CheckCircle2 } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function PrivacyPage() {
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
              <Shield size={14} />
            </div>
            <span className="text-white text-sm font-semibold">MemoryAgent Legal</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/[0.05] border border-white/[0.1] text-xs font-mono text-[#D0D5DD] mb-4">
            <Lock size={12} className="text-[#862FE7]" />
            <span>ENTERPRISE DATA PRIVACY & COMPLIANCE</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-bold text-white tracking-tight mb-4">
            Privacy Policy
          </h1>
          <p className="text-sm text-[#717171] font-mono">
            Last updated: September 26, 2026 | Effective Date: September 26, 2026
          </p>
        </div>

        <div className="space-y-10 text-sm leading-relaxed">
          {/* Section 1 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <Eye size={18} className="text-[#862FE7]" />
              1. Overview and Scope
            </h2>
            <p className="mb-3">
              MemoryAgent ("we", "our", or "the Platform") is an enterprise agentic memory architecture developed to persist, retrieve, and govern cognitive experiences for autonomous AI agents. We are committed to protecting organizational data, agent execution traces, and telemetry gathered during model inference.
            </p>
            <p>
              This Privacy Policy explains how information is collected, indexed, stored, and segregated across multi-tenant agent execution environments.
            </p>
          </section>

          {/* Section 2 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <FileText size={18} className="text-[#862FE7]" />
              2. Data Collected by the Platform
            </h2>
            <ul className="list-disc list-inside space-y-2 text-[#D0D5DD]/90">
              <li>
                <strong className="text-white">Agent Execution Context:</strong> Task prompts, tool invocations, intermediate thoughts, and environmental outcomes submitted to the memory indexing service.
              </li>
              <li>
                <strong className="text-white">Memory Embeddings and Vector Indices:</strong> High-dimensional numerical vectors generated from validated experiences used strictly for approximate nearest neighbor retrieval.
              </li>
              <li>
                <strong className="text-white">Account and Authentication Records:</strong> OAuth identifiers, workspace tokens, API keys, and administrative email addresses.
              </li>
              <li>
                <strong className="text-white">Operational Telemetry:</strong> Retrieval latency, Lower Confidence Bound (LCB) bandit scores, deflection metrics, and cache utilization.
              </li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <CheckCircle2 size={18} className="text-[#862FE7]" />
              3. Zero Data Retention for Model Training
            </h2>
            <p className="mb-3">
              We enforce a strict policy: <span className="text-white font-medium">Customer data and agent task traces are never used to train or fine-tune public foundation models.</span>
            </p>
            <p>
              All experience records remain isolated to your designated tenant namespace. Memory embeddings are stored within customer-managed or securely isolated multi-tenant vector databases protected by row-level access controls and encryption at rest (AES-256).
            </p>
          </section>

          {/* Section 4 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <Shield size={18} className="text-[#862FE7]" />
              4. Data Governance and Quarantine
            </h2>
            <p className="mb-3">
              MemoryAgent features automated adversarial quarantine mechanisms. In the event of prompt injection, poisoned trajectories, or hallucinated outputs, our Bayesian verification module isolates tainted memory nodes to prevent contamination of downstream agent runs.
            </p>
            <p>
              Administrators maintain complete authority to audit, export, or purge any memory cluster on demand via our management API or web console.
            </p>
          </section>

          {/* Section 5 */}
          <section className="p-6 rounded-xl bg-[#150d24]/60 border border-white/[0.08]">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <Lock size={18} className="text-[#862FE7]" />
              5. Contact Information
            </h2>
            <p>
              For privacy inquiries, audit reports, or Data Protection Officer (DPO) requests, please contact the development team at{' '}
              <a href="mailto:security@memoryagent.ai" className="text-[#862FE7] underline hover:text-[#953BFF]">
                security@memoryagent.ai
              </a>.
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
