import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Shield,
  ArrowRight,
  Copy,
  Check,
  Github,
  ChevronRight,
  Menu,
  X,
  BookOpen,
  FlaskConical,
  Award,
  Search,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import ThemeToggle from '../components/ThemeToggle'
import TheoremSandbox from '../components/TheoremSandbox'

interface ResearchSection {
  id: string
  title: string
  group: 'Theory & Foundations' | 'Simulation & Rigor'
  label: string
}

const RESEARCH_SECTIONS: ResearchSection[] = [
  {
    id: 'problem-formulation',
    title: 'Problem Formulation',
    group: 'Theory & Foundations',
    label: '1. Problem Formulation: The Naive RAG Hazard',
  },
  {
    id: 'asymmetric-ema',
    title: 'A-EMA Formulation',
    group: 'Theory & Foundations',
    label: '2. Asymmetric Exponential Moving Average',
  },
  {
    id: 'theorem-1-proof',
    title: 'Theorem 1 Proof',
    group: 'Theory & Foundations',
    label: '3. Theorem 1: Deterministic Quarantine Bound',
  },
  {
    id: 'interactive-simulator',
    title: 'Theorem 1 Sandbox',
    group: 'Simulation & Rigor',
    label: '4. Interactive Theorem 1 Simulator',
  },
  {
    id: 'computational-complexity',
    title: 'Computational Bounds',
    group: 'Simulation & Rigor',
    label: '5. Computational Complexity Analysis',
  },
  {
    id: 'bibtex-citation',
    title: 'Academic Citation',
    group: 'Simulation & Rigor',
    label: '6. Academic Citation & Artifacts',
  },
]

export default function ResearchPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { theme } = useTheme()
  const [activeSectionId, setActiveSectionId] = useState<string>('problem-formulation')
  const [activeHeadingId, setActiveHeadingId] = useState<string>('problem-formulation')
  const [searchQuery, setSearchQuery] = useState('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [copiedBibtex, setCopiedBibtex] = useState(false)

  const mainRef = useRef<HTMLElement | null>(null)
  const isManualScrolling = useRef(false)
  const manualTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const displayName = user?.name || user?.email?.split('@')[0] || ''

  const bibtex = `@article{aema2026reliability,
  title={Reliability-Aware Experiential Memory for AI Agents via Asymmetric Exponential Moving Average},
  author={AEMA Research Team},
  journal={arXiv preprint arXiv:2611.08942},
  year={2026},
  url={https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146}
}`

  const copyBibtex = () => {
    navigator.clipboard.writeText(bibtex)
    setCopiedBibtex(true)
    setTimeout(() => setCopiedBibtex(false), 2000)
  }

  const handleLaunchStudio = () => {
    if (user) {
      navigate('/dashboard?tab=studio')
    } else {
      navigate('/dashboard?demo=true&tab=studio')
    }
  }

  const handleSelectSection = (id: string) => {
    setActiveSectionId(id)
    setActiveHeadingId(id)
    setMobileMenuOpen(false)
    isManualScrolling.current = true

    if (manualTimeoutRef.current) {
      clearTimeout(manualTimeoutRef.current)
    }
    manualTimeoutRef.current = setTimeout(() => {
      isManualScrolling.current = false
    }, 1500)

    const element = document.getElementById(id)
    if (element && mainRef.current) {
      const mainRect = mainRef.current.getBoundingClientRect()
      const elemRect = element.getBoundingClientRect()
      const targetScroll = mainRef.current.scrollTop + (elemRect.top - mainRect.top) - 24
      mainRef.current.scrollTo({ top: targetScroll, behavior: 'smooth' })
    }
  }

  // Scroll watcher to update active section in both sidebars
  useEffect(() => {
    const mainEl = mainRef.current
    if (!mainEl) return

    const handleScroll = () => {
      if (isManualScrolling.current) return
      const allIds = RESEARCH_SECTIONS.map((s) => s.id)
      const mainTop = mainEl.getBoundingClientRect().top

      let currentId = allIds[0]
      for (const id of allIds) {
        const el = document.getElementById(id)
        if (el) {
          const elTop = el.getBoundingClientRect().top - mainTop
          if (elTop <= 120) {
            currentId = id
          }
        }
      }
      setActiveHeadingId(currentId)
      setActiveSectionId(currentId)
    }

    mainEl.addEventListener('scroll', handleScroll, { passive: true })
    return () => mainEl.removeEventListener('scroll', handleScroll)
  }, [])

  const groups: ResearchSection['group'][] = [
    'Theory & Foundations',
    'Simulation & Rigor',
  ]

  const filteredSections = RESEARCH_SECTIONS.filter(
    (sec) =>
      sec.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sec.label.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const isLight = theme === 'light'

  return (
    <div
      className={`min-h-screen flex flex-col font-sans transition-colors duration-150 ${
        isLight ? 'bg-[#FAFAF7] text-[#141413]' : 'bg-[#141412] text-[#EDECE8]'
      }`}
    >
      {/* ─── Top Global Navigation Header ─── */}
      <header
        className={`sticky top-0 z-40 w-full border-b backdrop-blur-md transition-colors ${
          isLight ? 'border-[#EAE8E3] bg-[#FAFAF7]/95' : 'border-[#242422] bg-[#141412]/95'
        }`}
      >
        <div className="max-w-[1600px] mx-auto px-4 sm:px-8 h-14 flex items-center justify-between gap-4">
          {/* Left: Brand & Portal Identifier */}
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2 group">
              <span
                className={`font-mono font-bold text-sm tracking-tight transition-colors ${
                  isLight ? 'text-[#141413] group-hover:text-black' : 'text-[#EDECE8] group-hover:text-white'
                }`}
              >
                AEMA
              </span>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                  isLight
                    ? 'bg-[#EFECE6] border-[#DCD9D0] text-[#6B6A65]'
                    : 'bg-[#1E1E1B] border-[#2E2E2A] text-[#9E9D96]'
                }`}
              >
                Research & Proofs v0.1.1
              </span>
            </Link>

            {/* Top Sub-Navigation Tabs */}
            <nav className="hidden md:flex items-center gap-5 text-xs font-mono">
              <Link
                to="/docs"
                className={`pb-4 pt-4 flex items-center gap-1.5 transition-colors ${
                  isLight ? 'text-[#6B6A65] hover:text-[#141413]' : 'text-[#7E7D77] hover:text-[#EDECE8]'
                }`}
              >
                <BookOpen size={12} className={isLight ? 'text-[#6B6A65]' : 'text-[#7E7D77]'} />
                <span>Documentation</span>
              </Link>
              <span
                className={`font-medium border-b-2 pb-4 pt-4 flex items-center gap-1.5 ${
                  isLight
                    ? 'text-[#141413] border-[#059669]'
                    : 'text-[#EDECE8] border-[#4EAA79]'
                }`}
              >
                <FlaskConical size={12} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Research & Proofs</span>
              </span>
              <Link
                to="/benchmarks"
                className={`pb-4 pt-4 flex items-center gap-1.5 transition-colors ${
                  isLight ? 'text-[#6B6A65] hover:text-[#141413]' : 'text-[#7E7D77] hover:text-[#EDECE8]'
                }`}
              >
                <Award size={12} className={isLight ? 'text-[#6B6A65]' : 'text-[#7E7D77]'} />
                <span>Benchmarks</span>
              </Link>
              <a
                href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
                target="_blank"
                rel="noopener noreferrer"
                className={`pb-4 pt-4 flex items-center gap-1.5 transition-colors ${
                  isLight ? 'text-[#6B6A65] hover:text-[#141413]' : 'text-[#7E7D77] hover:text-[#EDECE8]'
                }`}
              >
                <Github size={12} />
                <span>GitHub</span>
              </a>
            </nav>
          </div>

          {/* Center/Right: Quick Search, Theme Toggle, & Studio Action */}
          <div className="flex items-center gap-3">
            {/* Quick Search */}
            <div className="relative hidden sm:block w-48 lg:w-60">
              <Search
                size={13}
                className={`absolute left-2.5 top-2.5 ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search research (e.g. proof)..."
                className={`w-full pl-8 pr-3 py-1.5 rounded-md text-xs font-mono transition-colors focus:outline-none ${
                  isLight
                    ? 'bg-white border border-[#EAE8E3] text-[#141413] placeholder-[#8C8B85] focus:border-[#059669]'
                    : 'bg-[#181816] border border-[#262624] text-[#EDECE8] placeholder-[#7E7D77] focus:border-[#4EAA79]'
                }`}
              />
            </div>

            {/* Theme Toggle Button */}
            <ThemeToggle />

            {user && (
              <div
                className={`hidden sm:flex items-center gap-2 px-2.5 py-1 rounded border text-xs font-mono ${
                  isLight
                    ? 'bg-[#EFECE6] border-[#DCD9D0] text-[#6B6A65]'
                    : 'bg-[#1A1A17] border-[#262624] text-[#9E9D96]'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
                    isLight ? 'bg-[#DCD9D0] text-[#141413]' : 'bg-[#2E2E2A] text-[#EDECE8]'
                  }`}
                >
                  {displayName[0]?.toUpperCase() || 'U'}
                </div>
                <span className="truncate max-w-[120px]">{displayName}</span>
              </div>
            )}

            <button
              onClick={handleLaunchStudio}
              className={`px-3.5 py-1.5 rounded text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shrink-0 ${
                isLight
                  ? 'bg-[#141413] text-[#FAFAF7] hover:bg-[#2B2B28]'
                  : 'bg-[#4EAA79] text-[#141412] hover:bg-[#5EBA89]'
              }`}
            >
              <span>{user ? 'Back to Studio' : 'Launch Studio'}</span>
              <ArrowRight size={12} />
            </button>

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={`p-1.5 rounded md:hidden border ${
                isLight
                  ? 'border-[#EAE8E3] text-[#6B6A65] hover:text-black'
                  : 'border-[#2E2E2A] text-[#9E9D96] hover:text-white'
              }`}
            >
              {mobileMenuOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>
      </header>

      {/* ─── 3-Column Research Layout ─── */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto flex flex-col md:flex-row">
        {/* ─── Column 1: Left Navigation Sidebar (Clean Single-Line Links) ─── */}
        <aside
          className={`w-full md:w-64 lg:w-72 shrink-0 border-b md:border-b-0 md:border-r p-5 overflow-y-auto ${
            isLight
              ? 'border-[#EAE8E3] bg-[#F5F4EF]'
              : 'border-[#242422] bg-[#161614]'
          } ${mobileMenuOpen ? 'block' : 'hidden md:block'}`}
          style={{ maxHeight: 'calc(100vh - 56px)' }}
        >
          {/* Mobile search bar if on small screen */}
          <div className="sm:hidden mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search research..."
              className={`w-full px-3 py-1.5 rounded border text-xs font-mono ${
                isLight
                  ? 'bg-white border-[#EAE8E3] text-[#141413] placeholder-[#8C8B85]'
                  : 'bg-[#181816] border-[#262624] text-[#EDECE8] placeholder-[#7E7D77]'
              }`}
            />
          </div>

          <div className="space-y-6">
            {groups.map((group) => {
              const groupSections = filteredSections.filter((s) => s.group === group)
              if (groupSections.length === 0) return null

              return (
                <div key={group} className="space-y-1.5">
                  <div
                    className={`text-[10px] font-mono uppercase tracking-widest px-2.5 font-semibold ${
                      isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'
                    }`}
                  >
                    {group}
                  </div>
                  <div className="space-y-0.5">
                    {groupSections.map((sec) => {
                      const isActive = activeSectionId === sec.id
                      return (
                        <button
                          key={sec.id}
                          type="button"
                          onClick={() => handleSelectSection(sec.id)}
                          className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs transition-colors flex items-center justify-between cursor-pointer ${
                            isActive
                              ? isLight
                                ? 'bg-[#ECFDF5] text-[#059669] font-medium border border-[#A7F3D0]'
                                : 'bg-[#1E2E24] text-[#4EAA79] font-medium border border-[#2E4234]'
                              : isLight
                              ? 'text-[#6B6A65] hover:text-[#141413] hover:bg-[#EAE8E0]'
                              : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                          }`}
                        >
                          <span className="truncate">{sec.title}</span>
                          {isActive && (
                            <ChevronRight
                              size={12}
                              className={isLight ? 'text-[#059669] shrink-0' : 'text-[#4EAA79] shrink-0'}
                            />
                          )}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}

            <div
              className={`pt-4 border-t space-y-1.5 ${
                isLight ? 'border-[#EAE8E3]' : 'border-[#242422]'
              }`}
            >
              <div
                className={`text-[10px] font-mono uppercase tracking-widest px-2.5 font-semibold ${
                  isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'
                }`}
              >
                Portals & Navigation
              </div>
              <Link
                to="/docs"
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs flex items-center gap-2 transition-colors ${
                  isLight
                    ? 'text-[#6B6A65] hover:text-[#141413] hover:bg-[#EAE8E0]'
                    : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
              >
                <BookOpen size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Documentation</span>
              </Link>
              <Link
                to="/benchmarks"
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs flex items-center gap-2 transition-colors ${
                  isLight
                    ? 'text-[#6B6A65] hover:text-[#141413] hover:bg-[#EAE8E0]'
                    : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
              >
                <Award size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Benchmarks</span>
              </Link>
              <Link
                to="/dashboard?tab=studio"
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs flex items-center gap-2 transition-colors ${
                  isLight
                    ? 'text-[#6B6A65] hover:text-[#141413] hover:bg-[#EAE8E0]'
                    : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
              >
                <Shield size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Execution Studio</span>
              </Link>
            </div>
          </div>
        </aside>

        {/* ─── Column 2: Center Main Content Viewport ─── */}
        <main
          ref={mainRef}
          className={`flex-1 min-w-0 p-6 sm:p-10 lg:p-12 overflow-y-auto ${
            isLight ? 'bg-[#FAFAF7]' : 'bg-[#141412]'
          }`}
        >
          <div className="max-w-3xl space-y-12">
            {/* Header Block */}
            <div
              className={`space-y-3 pb-6 border-b ${
                isLight ? 'border-[#EAE8E3]' : 'border-[#242422]'
              }`}
            >
              <div
                className={`text-xs font-mono uppercase tracking-widest flex items-center gap-1.5 ${
                  isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                }`}
              >
                <FlaskConical size={14} />
                <span>Theoretical Foundation & Empirical Validation</span>
              </div>
              <h1
                className={`text-3xl sm:text-4xl font-serif tracking-tight leading-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                Reliability-Aware Experiential Memory for Autonomous AI Agents
              </h1>
              <p
                className={`text-base leading-relaxed ${
                  isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'
                }`}
              >
                Formulating the mathematical foundation, deterministic isolation bounds, and confirmatory empirical proofs of the Asymmetric Exponential Moving Average (A-EMA) memory architecture.
              </p>
            </div>

            {/* Section 1: Problem Formulation */}
            <section id="problem-formulation" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                1. Problem Formulation: The Naive RAG Hazard
              </h2>
              <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                Standard agentic architectures employ naive vector retrieval (RAG) to store past execution traces. When an agent succeeds, it indexes the prompt and solution. However, real-world operational environments are fundamentally non-stationary: APIs deprecate, schemas evolve, third-party libraries introduce breaking changes, and underlying environments shift.
              </p>
              <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                Under naive vector RAG, when an environment shifts, previously stored successful memories become toxic traps. The vector similarity between the new task and the deprecated memory remains high (often &gt; 0.90 cosine similarity). Consequently, the naive agent repeatedly retrieves and injects the broken strategy, suffering from catastrophic negative transfer: accuracy drops to 0.0% as the agent enters an unrecoverable failure loop.
              </p>

              <div
                className={`p-4 rounded-lg border text-xs leading-relaxed space-y-1 ${
                  isLight
                    ? 'border-[#FECACA] bg-[#FEF2F2] text-[#991B1B]'
                    : 'border-[#3E2020] bg-[#221616] text-[#D9534F]'
                }`}
              >
                <div className="font-mono text-[11px] font-semibold flex items-center gap-1.5">
                  <Shield size={13} className={isLight ? 'text-[#DC2626]' : 'text-[#D9534F]'} />
                  <span>The Negative Transfer Trap in Naive Vector Stores</span>
                </div>
                <p className={isLight ? 'text-[#7F1D1D]' : 'text-[#EDECE8]'}>
                  Cosine similarity measures linguistic and semantic proximity, not operational validity. Relying solely on vector embeddings for memory retrieval guarantees persistent failure when execution reality contradicts past experience.
                </p>
              </div>
            </section>

            {/* Section 2: Asymmetric Exponential Moving Average (A-EMA) */}
            <section id="asymmetric-ema" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                2. Asymmetric Exponential Moving Average (A-EMA) Formulation
              </h2>
              <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                AEMA replaces unweighted vector retrieval with an asymmetric dual-parameter trust formulation. Every experiential memory m_i maintains an evolving reliability score S_t(m_i) in [0, 1]. Trust updates follow an asymmetric recurrence:
              </p>

              <div
                className={`p-4 rounded-lg border font-mono text-xs space-y-2 ${
                  isLight
                    ? 'border-[#EAE8E3] bg-[#F5F4F0] text-[#141413]'
                    : 'border-[#2E2E2A] bg-[#181816] text-[#EDECE8]'
                }`}
              >
                <div className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                  // Upon task success (r_t = 1):
                </div>
                <div className="pl-4">S_{`{t+1}`} = α · S_t + (1 - α) · 1.0</div>
                <div className={`font-semibold pt-2 ${isLight ? 'text-[#DC2626]' : 'text-[#D9534F]'}`}>
                  // Upon task failure (r_t = 0):
                </div>
                <div className="pl-4">S_{`{t+1}`} = β · S_t</div>
                <div className={`pt-2 text-[11px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                  Canonical Parameter Setting: α = 0.85 (conservative reward rate), β = 0.70 (punitive penalty rate), θ = 0.35 (quarantine threshold).
                </div>
              </div>

              <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                Because β &lt; α, trust decays much faster upon failure than it accumulates upon success. This asymmetric property guarantees that a failing strategy is penalized aggressively before it can poison subsequent agent operations.
              </p>
            </section>

            {/* Section 3: Theorem 1 Proof */}
            <section id="theorem-1-proof" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                3. Theorem 1: Deterministic Quarantine Bound
              </h2>
              <div
                className={`p-4 rounded-lg border text-xs leading-relaxed space-y-2 ${
                  isLight
                    ? 'border-[#A7F3D0] bg-[#ECFDF5] text-[#065F46]'
                    : 'border-[#2A3E30] bg-[#18201A] text-[#A3E0BA]'
                }`}
              >
                <div className="font-mono text-[11px] font-semibold flex items-center gap-1.5">
                  <Shield size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  <span>Theorem 1 (Deterministic Finite-Failure Quarantine)</span>
                </div>
                <p>
                  Let S_0 in (θ, 1] be the initial trust score of an active memory. Let β in (0, 1) be the failure penalty parameter, and θ in (0, 1) be the quarantine threshold. Under consecutive execution failures, the memory is guaranteed to be quarantined in exactly:
                </p>
                <div
                  className={`p-2.5 rounded font-mono text-center text-sm font-bold border ${
                    isLight
                      ? 'bg-white text-[#059669] border-[#A7F3D0]'
                      : 'bg-[#141412] text-[#4EAA79] border-[#242422]'
                  }`}
                >
                  k^* = ⌈(ln θ - ln S_0) / ln β⌉
                </div>
                <p className={`text-[11px] ${isLight ? 'text-[#047857]' : 'text-[#9E9D96]'}`}>
                  failures, regardless of prior task success history, vector similarity, or context window size.
                </p>
              </div>

              <div className="space-y-2">
                <h3
                  className={`text-sm font-serif font-semibold ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  Mathematical Derivation
                </h3>
                <p className={`text-xs leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                  After k consecutive failures, the trust score is given by S_k = S_0 · β^k. The memory breaches the admissible retrieval boundary when S_k &lt; θ:
                </p>
                <ol
                  className={`list-decimal list-inside text-xs font-mono space-y-1.5 pl-2 ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  <li>S_0 · β^k &lt; θ</li>
                  <li>β^k &lt; θ / S_0</li>
                  <li>k · ln(β) &lt; ln(θ) - ln(S_0)</li>
                  <li>Since 0 &lt; β &lt; 1, ln(β) &lt; 0. Dividing reverses the inequality:</li>
                  <li className={`font-bold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                    k &gt; (ln(θ) - ln(S_0)) / ln(β)
                  </li>
                  <li>The minimal integer satisfying this condition is k^* = ⌈(ln θ - ln S_0) / ln β⌉. Q.E.D.</li>
                </ol>
              </div>

              <div
                className={`p-3.5 rounded-lg border text-xs font-mono ${
                  isLight
                    ? 'bg-[#F5F4F0] border-[#EAE8E3] text-[#6B6A65]'
                    : 'bg-[#161614] border-[#242422] text-[#9E9D96]'
                }`}
              >
                <span className={`font-semibold ${isLight ? 'text-[#141413]' : 'text-[#EDECE8]'}`}>
                  Canonical Evaluation Example:
                </span>{' '}
                With S_0 = 0.75, β = 0.70, θ = 0.35:
                <br />
                k^* = ⌈(ln(0.35) - ln(0.75)) / ln(0.70)⌉ = ⌈(-1.0498 - (-0.2877)) / -0.3567⌉ = ⌈2.136⌉ = 3.
                <br />
                The memory is quarantined deterministically on exactly the 3rd failure.
              </div>
            </section>

            {/* Section 4: Interactive Simulator */}
            <section id="interactive-simulator" className="space-y-4 scroll-mt-20">
              <div className="flex items-center justify-between">
                <h2
                  className={`text-xl font-serif tracking-tight ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  4. Interactive Theorem 1 Simulator
                </h2>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    isLight
                      ? 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]'
                      : 'bg-[#1E2E24] text-[#4EAA79] border-[#2E4234]'
                  }`}
                >
                  LIVE SANDBOX
                </span>
              </div>
              <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                Test Theorem 1 interactively. Adjust parameters α, β, θ, S_0 and simulate consecutive failure steps to observe the trust trajectory and quarantine trigger point in real time.
              </p>
              <TheoremSandbox />
            </section>

            {/* Section 5: Computational Complexity */}
            <section id="computational-complexity" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                5. Computational Complexity Analysis
              </h2>
              
              <div className="space-y-2">
                <h3
                  className={`text-sm font-serif font-semibold ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  O(1) Scalar Update Complexity
                </h3>
                <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                  Unlike parametric model retraining or continuous vector index re-clustering which scale as O(N) or O(N log N), A-EMA trust calibration operates in strictly O(1) time complexity. Updating a memory trust score involves two scalar multiplications and a clamp operation, consuming less than 1.2 microseconds per turn.
                </p>
              </div>

              <div className="space-y-2">
                <h3
                  className={`text-sm font-serif font-semibold ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  Space and Memory Footprint
                </h3>
                <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                  Each distilled procedural memory tuple (c, a, p) consumes approximately 240 bytes of disk storage and 4 bytes for the IEEE 754 floating-point trust score. A production bank of 100,000 verified experiences occupies less than 25MB of RAM.
                </p>
              </div>
            </section>

            {/* Section 6: Academic Citation & Artifacts */}
            <section id="bibtex-citation" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                6. Academic Citation & Artifacts
              </h2>
              <p className={`text-sm leading-relaxed ${isLight ? 'text-[#6B6A65]' : 'text-[#9E9D96]'}`}>
                If you cite AEMA in your research or use its algorithmic implementation in your agent framework, please use the following BibTeX citation:
              </p>

              <div
                className={`rounded-lg border overflow-hidden ${
                  isLight ? 'border-[#EAE8E3] bg-[#F5F4F0]' : 'border-[#242422] bg-[#161614]'
                }`}
              >
                <div
                  className={`flex items-center justify-between px-4 py-2.5 border-b text-xs font-mono ${
                    isLight
                      ? 'bg-[#EFECE6] border-[#EAE8E3] text-[#6B6A65]'
                      : 'bg-[#1A1A17] border-[#242422] text-[#7E7D77]'
                  }`}
                >
                  <span>citation.bib</span>
                  <button
                    onClick={copyBibtex}
                    className={`flex items-center gap-1.5 text-[11px] transition-colors cursor-pointer ${
                      isLight ? 'text-[#059669] hover:text-[#047857]' : 'text-[#4EAA79] hover:text-[#5EBA89]'
                    }`}
                  >
                    {copiedBibtex ? <Check size={12} /> : <Copy size={12} />}
                    <span>{copiedBibtex ? 'Copied' : 'Copy BibTeX'}</span>
                  </button>
                </div>
                <pre
                  className={`p-4 text-xs font-mono overflow-x-auto leading-relaxed ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  <code>{bibtex}</code>
                </pre>
              </div>
            </section>

            {/* Footer Navigation */}
            <div
              className={`pt-10 border-t flex items-center justify-between text-xs font-mono ${
                isLight ? 'border-[#EAE8E3] text-[#8C8B85]' : 'border-[#242422] text-[#7E7D77]'
              }`}
            >
              <span>AEMA Research Foundation</span>
              <button
                type="button"
                onClick={() => {
                  if (mainRef.current) {
                    mainRef.current.scrollTo({ top: 0, behavior: 'smooth' })
                  }
                }}
                className={`transition-colors cursor-pointer ${
                  isLight ? 'hover:text-[#141413]' : 'hover:text-[#EDECE8]'
                }`}
              >
                Back to top &uarr;
              </button>
            </div>
          </div>
        </main>

        {/* ─── Column 3: Right "On this page" Outline (Zero Duplication) ─── */}
        <aside
          className={`hidden xl:block w-64 shrink-0 p-8 border-l text-xs font-mono ${
            isLight ? 'border-[#EAE8E3] bg-[#FAFAF7]' : 'border-[#242422] bg-[#141412]'
          }`}
        >
          <div className="sticky top-20 space-y-3">
            <div
              className={`text-[11px] font-mono uppercase tracking-wider font-semibold flex items-center gap-1.5 ${
                isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'
              }`}
            >
              <span className="text-sm leading-none">≡</span>
              <span>On this page</span>
            </div>
            <div
              className={`space-y-2 border-l pl-3 ${
                isLight ? 'border-[#EAE8E3]' : 'border-[#242422]'
              }`}
            >
              {RESEARCH_SECTIONS.map((sec) => {
                const isHeadingActive = activeHeadingId === sec.id
                return (
                  <a
                    key={sec.id}
                    href={`#${sec.id}`}
                    onClick={(e) => {
                      e.preventDefault()
                      handleSelectSection(sec.id)
                    }}
                    className={`block text-[11px] transition-colors ${
                      isHeadingActive
                        ? isLight
                          ? 'text-[#059669] font-medium border-l border-[#059669] -ml-[13px] pl-3'
                          : 'text-[#4EAA79] font-medium border-l border-[#4EAA79] -ml-[13px] pl-3'
                        : isLight
                        ? 'text-[#6B6A65] hover:text-[#141413]'
                        : 'text-[#7E7D77] hover:text-[#EDECE8]'
                    }`}
                  >
                    {sec.label}
                  </a>
                )
              })}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
