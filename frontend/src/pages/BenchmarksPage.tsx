import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Award,
  ArrowRight,
  Shield,
  ChevronRight,
  Menu,
  X,
  Github,
  BookOpen,
  FlaskConical,
  Zap,
  Clock,
  Coins,
  Search,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import ThemeToggle from '../components/ThemeToggle'
import BenchmarkMatrix from '../components/BenchmarkMatrix'

interface BenchmarkSection {
  id: string
  title: string
  group: 'Protocol & Suites' | 'Performance & Rigor'
  label: string
}

const BENCHMARK_SECTIONS: BenchmarkSection[] = [
  {
    id: 'executive-summary',
    title: 'Executive Summary',
    group: 'Protocol & Suites',
    label: '1. Executive Summary & Protocol',
  },
  {
    id: 'comparative-matrix',
    title: 'Comparative Matrix',
    group: 'Protocol & Suites',
    label: '2. Comparative Accuracy Matrix',
  },
  {
    id: 'confirmatory-traps',
    title: 'Confirmatory Traps',
    group: 'Protocol & Suites',
    label: '3. Confirmatory Trap Suite',
  },
  {
    id: 'hotpotqa-contradiction',
    title: 'HotpotQA Contradiction',
    group: 'Protocol & Suites',
    label: '4. HotpotQA Multi-Hop Contradiction',
  },
  {
    id: 'toolbench-deprecation',
    title: 'ToolBench Deprecation',
    group: 'Performance & Rigor',
    label: '5. ToolBench API Deprecation',
  },
  {
    id: 'alfworld-planning',
    title: 'ALFWorld Planning',
    group: 'Performance & Rigor',
    label: '6. ALFWorld Embodied Planning',
  },
  {
    id: 'latency-efficiency',
    title: 'Latency & Efficiency',
    group: 'Performance & Rigor',
    label: '7. Latency & Token Overhead',
  },
  {
    id: 'statistical-rigor',
    title: 'Statistical Rigor',
    group: 'Performance & Rigor',
    label: '8. Statistical Significance (McNemar)',
  },
]

export default function BenchmarksPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { theme } = useTheme()
  const [activeSectionId, setActiveSectionId] = useState<string>('executive-summary')
  const [activeHeadingId, setActiveHeadingId] = useState<string>('executive-summary')
  const [searchQuery, setSearchQuery] = useState('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const mainRef = useRef<HTMLElement | null>(null)
  const isManualScrolling = useRef(false)
  const manualTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const displayName = user?.name || user?.email?.split('@')[0] || ''
  const isLight = theme === 'light'

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
    }, 1000)

    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  // Scroll watcher to update active section in both sidebars
  useEffect(() => {
    const mainEl = mainRef.current
    if (!mainEl) return

    const handleScroll = () => {
      if (isManualScrolling.current) return
      const allIds = BENCHMARK_SECTIONS.map((s) => s.id)
      const mainTop = mainEl.getBoundingClientRect().top

      for (let i = allIds.length - 1; i >= 0; i--) {
        const el = document.getElementById(allIds[i])
        if (el) {
          const elTop = el.getBoundingClientRect().top - mainTop
          if (elTop <= 140) {
            setActiveHeadingId(allIds[i])
            setActiveSectionId(allIds[i])
            break
          }
        }
      }
    }

    mainEl.addEventListener('scroll', handleScroll, { passive: true })
    return () => mainEl.removeEventListener('scroll', handleScroll)
  }, [])

  const groups: BenchmarkSection['group'][] = [
    'Protocol & Suites',
    'Performance & Rigor',
  ]

  const filteredSections = BENCHMARK_SECTIONS.filter(
    (sec) =>
      sec.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sec.label.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div
      className={`min-h-screen flex flex-col font-sans transition-colors ${
        isLight
          ? 'bg-[#FAFAF7] text-[#141413] selection:bg-[#059669]/20 selection:text-[#059669]'
          : 'bg-[#141412] text-[#EDECE8] selection:bg-[#4EAA79]/20 selection:text-[#4EAA79]'
      }`}
    >
      {/* Top Global Navigation Header */}
      <header
        className={`sticky top-0 z-40 w-full border-b backdrop-blur-md transition-colors ${
          isLight
            ? 'border-[#EAE8E3] bg-[#FAFAF7]/95 text-[#141413]'
            : 'border-[#242422] bg-[#141412]/95 text-[#EDECE8]'
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
                    ? 'bg-[#F0EFEA] border-[#E5E3DC] text-[#6B6A65]'
                    : 'bg-[#1E1E1B] border-[#2E2E2A] text-[#9E9D96]'
                }`}
              >
                Benchmarks v0.1.1
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
              <Link
                to="/research"
                className={`pb-4 pt-4 flex items-center gap-1.5 transition-colors ${
                  isLight ? 'text-[#6B6A65] hover:text-[#141413]' : 'text-[#7E7D77] hover:text-[#EDECE8]'
                }`}
              >
                <FlaskConical size={12} className={isLight ? 'text-[#6B6A65]' : 'text-[#7E7D77]'} />
                <span>Research & Proofs</span>
              </Link>
              <span
                className={`font-medium border-b-2 pb-4 pt-4 flex items-center gap-1.5 ${
                  isLight
                    ? 'text-[#141413] border-[#059669]'
                    : 'text-[#EDECE8] border-[#4EAA79]'
                }`}
              >
                <Award size={12} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Benchmarks</span>
              </span>
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

          {/* Center/Right Actions */}
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
                placeholder="Search benchmarks (e.g. mcnemar)..."
                className={`w-full pl-8 pr-3 py-1.5 rounded-md text-xs font-mono transition-colors focus:outline-none ${
                  isLight
                    ? 'bg-[#F0EFEA] border border-[#E5E3DC] text-[#141413] placeholder-[#8A8985] focus:border-[#059669]'
                    : 'bg-[#181816] border border-[#262624] text-[#EDECE8] placeholder-[#7E7D77] focus:border-[#4EAA79]'
                }`}
              />
            </div>

            {user && (
              <div
                className={`hidden sm:flex items-center gap-2 px-2.5 py-1 rounded text-xs font-mono border ${
                  isLight
                    ? 'bg-[#F5F4EF] border-[#EAE8E3] text-[#6B6A65]'
                    : 'bg-[#1A1A17] border-[#262624] text-[#9E9D96]'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
                    isLight ? 'bg-[#EAE8E3] text-[#141413]' : 'bg-[#2E2E2A] text-[#EDECE8]'
                  }`}
                >
                  {displayName[0]?.toUpperCase() || 'U'}
                </div>
                <span className={`truncate max-w-[120px] ${isLight ? 'text-[#141413]' : 'text-[#EDECE8]'}`}>
                  {displayName}
                </span>
              </div>
            )}

            {/* Theme Toggle Button */}
            <ThemeToggle />

            <button
              onClick={handleLaunchStudio}
              className={`px-3.5 py-1.5 rounded text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shrink-0 ${
                isLight
                  ? 'bg-[#059669] text-white hover:bg-[#047857]'
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
                  ? 'border-[#EAE8E3] text-[#6B6A65] hover:text-[#141413]'
                  : 'border-[#2E2E2A] text-[#9E9D96] hover:text-white'
              }`}
            >
              {mobileMenuOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>
      </header>

      {/* 3-Column Benchmarks Layout */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto flex flex-col md:flex-row">
        {/* Column 1: Left Navigation Sidebar */}
        <aside
          className={`w-full md:w-64 lg:w-72 shrink-0 border-b md:border-b-0 md:border-r p-5 overflow-y-auto transition-colors ${
            isLight
              ? 'border-[#EAE8E3] bg-[#F5F4EF]'
              : 'border-[#242422] bg-[#161614]'
          } ${mobileMenuOpen ? 'block' : 'hidden md:block'}`}
          style={{ maxHeight: 'calc(100vh - 56px)' }}
        >
          {/* Mobile search input */}
          <div className="sm:hidden mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search benchmarks..."
              className={`w-full px-3 py-1.5 rounded text-xs font-mono border ${
                isLight
                  ? 'bg-white border-[#EAE8E3] text-[#141413] placeholder-[#8A8985]'
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
                      isLight ? 'text-[#8A8985]' : 'text-[#7E7D77]'
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
                              ? 'text-[#6B7280] hover:text-[#141413] hover:bg-[#EAE8E3]/60'
                              : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                          }`}
                        >
                          <span className="truncate">{sec.title}</span>
                          {isActive && (
                            <ChevronRight
                              size={12}
                              className={`shrink-0 ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
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
                  isLight ? 'text-[#8A8985]' : 'text-[#7E7D77]'
                }`}
              >
                Portals & Navigation
              </div>
              <Link
                to="/docs"
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs flex items-center gap-2 transition-colors ${
                  isLight
                    ? 'text-[#6B7280] hover:text-[#141413] hover:bg-[#EAE8E3]/60'
                    : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
              >
                <BookOpen size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Documentation</span>
              </Link>
              <Link
                to="/research"
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs flex items-center gap-2 transition-colors ${
                  isLight
                    ? 'text-[#6B7280] hover:text-[#141413] hover:bg-[#EAE8E3]/60'
                    : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
              >
                <FlaskConical size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Research & Proofs</span>
              </Link>
              <Link
                to="/dashboard?tab=studio"
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs flex items-center gap-2 transition-colors ${
                  isLight
                    ? 'text-[#6B7280] hover:text-[#141413] hover:bg-[#EAE8E3]/60'
                    : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                }`}
              >
                <Shield size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                <span>Execution Studio</span>
              </Link>
            </div>
          </div>
        </aside>

        {/* Column 2: Center Main Content Viewport */}
        <main
          ref={mainRef}
          className={`flex-1 min-w-0 p-6 sm:p-10 lg:p-12 overflow-y-auto transition-colors ${
            isLight ? 'bg-[#FAFAF7]' : 'bg-[#141412]'
          }`}
          style={{ maxHeight: 'calc(100vh - 56px)' }}
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
                <Award size={14} />
                <span>Confirmatory Empirical Benchmark Suites</span>
              </div>
              <h1
                className={`text-3xl sm:text-4xl font-serif tracking-tight leading-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                Empirical Evaluation & Performance Verification
              </h1>
              <p
                className={`text-base leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Comprehensive comparative findings across four protocol-frozen evaluation suites measuring negative transfer resistance, multi-hop contradiction resilience, API deprecation recovery, and execution efficiency.
              </p>
            </div>

            {/* Section 1: Executive Summary & Evaluation Protocol */}
            <section id="executive-summary" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                1. Executive Summary & Evaluation Protocol
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                The primary vulnerability of memory-augmented autonomous agents is negative transfer: the uncritical injection of past memories into tasks where the environment, API contracts, or real-world facts have changed.
              </p>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                To evaluate AEMA rigorously against this failure mode, experiments were conducted under a protocol-frozen setting (N=100 trials per suite, temperature=0.0, deterministic test harness). AEMA was benchmarked against two baseline configurations:
              </p>
              <ul
                className={`list-disc list-inside text-xs font-mono space-y-2 pl-2 ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                <li>
                  <span className={`font-semibold ${isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'}`}>
                    Stateless Baseline:
                  </span>{' '}
                  The agent operates without memory. It avoids poisoned memories but cannot reuse verified operational strategies.
                </li>
                <li>
                  <span className="text-[#D9534F] font-semibold">Naive Vector RAG:</span> Past execution traces are embedded and retrieved solely by cosine similarity. In non-stationary environments, broken heuristics are repeatedly retrieved.
                </li>
                <li>
                  <span
                    className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    AEMA Engine:
                  </span>{' '}
                  Asymmetric Exponential Moving Average trust scoring with Theorem 1 deterministic quarantine bounds.
                </li>
              </ul>
            </section>

            {/* Section 2: Comparative Matrix */}
            <section id="comparative-matrix" className="space-y-4 scroll-mt-20">
              <div className="flex items-center justify-between">
                <h2
                  className={`text-xl font-serif tracking-tight ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  2. Comparative Accuracy Matrix (4 Suites)
                </h2>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    isLight
                      ? 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]'
                      : 'bg-[#1E2E24] text-[#4EAA79] border-[#2E4234]'
                  }`}
                >
                  FROZEN PROTOCOL
                </span>
              </div>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Summary across all four empirical evaluation suites:
              </p>

              {/* Live Interactive Benchmark Matrix Component */}
              <BenchmarkMatrix />
            </section>

            {/* Section 3: Confirmatory Trap Suite */}
            <section id="confirmatory-traps" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                3. Confirmatory Trap Suite (Negative Transfer Resilience)
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                In the Confirmatory Trap suite, tasks are designed such that a naive vector similarity search retrieves a previously successful solution that is fatal to the current task (e.g. using a deprecated function signature or recursive traversal instead of iterative stacks).
              </p>
              <div
                className={`p-4 rounded-lg border font-mono text-xs space-y-3 ${
                  isLight
                    ? 'border-[#EAE8E3] bg-[#FFFFFF]'
                    : 'border-[#242422] bg-[#161614]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Naive Vector RAG Accuracy:
                  </span>
                  <span className="text-[#D9534F] font-bold">0.0% (Poisoned)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Stateless Agent Accuracy:
                  </span>
                  <span className={isLight ? 'text-[#141413]' : 'text-[#EDECE8]'}>60.0%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}>
                    AEMA Engine Accuracy:
                  </span>
                  <span
                    className={`font-bold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    100.0%
                  </span>
                </div>
                <div
                  className={`flex items-center justify-between border-t pt-2 ${
                    isLight ? 'border-[#EAE8E3]' : 'border-[#242422]'
                  }`}
                >
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Recovery Trial Bound:
                  </span>
                  <span className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}>
                    k* &le; 3 runs (Deterministic Isolation)
                  </span>
                </div>
              </div>
              <p
                className={`text-xs leading-relaxed ${
                  isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'
                }`}
              >
                Result: While Naive Vector RAG drops to 0.0% accuracy due to memory poisoning, AEMA isolates the trap within 3 consecutive trials under Theorem 1 and recovers to 100% operational success.
              </p>
            </section>

            {/* Section 4: HotpotQA Multi-Hop Contradiction */}
            <section id="hotpotqa-contradiction" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                4. HotpotQA Multi-Hop Contradiction Suite
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Multi-hop reasoning tasks where an initial premise is contradicted by a newly established fact in later documents. Evaluates whether the memory store propagates obsolete premises across reasoning chains.
              </p>
              <div
                className={`overflow-x-auto rounded-lg border ${
                  isLight ? 'border-[#EAE8E3]' : 'border-[#242422]'
                }`}
              >
                <table className="w-full text-left text-xs font-mono">
                  <thead
                    className={`border-b ${
                      isLight
                        ? 'bg-[#F5F4EF] border-[#EAE8E3] text-[#6B7280]'
                        : 'bg-[#181816] border-[#242422] text-[#7E7D77]'
                    }`}
                  >
                    <tr>
                      <th className="p-3">Architecture</th>
                      <th className="p-3">Accuracy</th>
                      <th className="p-3">Negative Transfer Rate</th>
                      <th className="p-3">Avg Recovery Steps</th>
                    </tr>
                  </thead>
                  <tbody
                    className={`divide-y ${
                      isLight
                        ? 'divide-[#EAE8E3] bg-[#FFFFFF] text-[#141413]'
                        : 'divide-[#242422] bg-[#161614] text-[#EDECE8]'
                    }`}
                  >
                    <tr>
                      <td className="p-3">Stateless Baseline</td>
                      <td className="p-3">52.4%</td>
                      <td className="p-3">0.0% (N/A)</td>
                      <td className="p-3">--</td>
                    </tr>
                    <tr>
                      <td className="p-3 text-[#D9534F]">Naive Vector RAG</td>
                      <td className="p-3 text-[#D9534F]">14.8%</td>
                      <td className="p-3 text-[#D9534F]">85.2%</td>
                      <td className="p-3 text-[#D9534F]">&gt; 10 (Loop)</td>
                    </tr>
                    <tr className={isLight ? 'bg-[#ECFDF5]/50' : 'bg-[#18201A]'}>
                      <td
                        className={`p-3 font-semibold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        AEMA Engine
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        88.6%
                      </td>
                      <td className={`p-3 ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                        11.4%
                      </td>
                      <td className={`p-3 ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                        2.4 steps
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Section 5: ToolBench Dynamic API Deprecation */}
            <section id="toolbench-deprecation" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                5. ToolBench Dynamic API Deprecation Suite
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Simulating software engineering agent pipelines where third-party API endpoints undergo schema breaking changes (404/410 response codes, changed argument names).
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#FFFFFF] border-[#EAE8E3]'
                      : 'bg-[#161614] border-[#242422]'
                  }`}
                >
                  <span className={`text-[10px] ${isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}`}>
                    Stateless Agent
                  </span>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                    }`}
                  >
                    64.2%
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Re-solves from scratch
                  </span>
                </div>
                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#FFFFFF] border-[#EAE8E3]'
                      : 'bg-[#161614] border-[#242422]'
                  }`}
                >
                  <span className="text-[#D9534F] text-[10px]">Naive Vector RAG</span>
                  <div className="text-xl font-bold text-[#D9534F]">22.0%</div>
                  <span className="text-[10px] text-[#D9534F]">Re-invokes broken API</span>
                </div>
                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#ECFDF5] border-[#A7F3D0]'
                      : 'bg-[#18201A] border-[#2A3E30]'
                  }`}
                >
                  <span
                    className={`text-[10px] ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    AEMA Engine
                  </span>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                    }`}
                  >
                    91.4%
                  </div>
                  <span
                    className={`text-[10px] ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    Deprecates API memory
                  </span>
                </div>
              </div>
            </section>

            {/* Section 6: ALFWorld Multi-Step Embodied Planning */}
            <section id="alfworld-planning" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                6. ALFWorld Multi-Step Embodied Planning Suite
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Text-based embodied planning benchmark requiring multi-step navigation, object interaction, and state changes. Tests whether AEMA balances strategy reuse with environmental feedback.
              </p>
              <div
                className={`p-4 rounded-lg border text-xs font-mono space-y-2 ${
                  isLight
                    ? 'border-[#EAE8E3] bg-[#FFFFFF]'
                    : 'border-[#242422] bg-[#161614]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Task Completion Rate:
                  </span>
                  <span
                    className={`font-bold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    85.0% (vs 31.5% Naive RAG, 58.0% Stateless)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Average Trajectory Length:
                  </span>
                  <span className={isLight ? 'text-[#141413]' : 'text-[#EDECE8]'}>
                    14.2 steps (AEMA) vs 28.6 steps (Naive RAG)
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Deadlock Avoidance:
                  </span>
                  <span className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}>
                    96.8% of cycles avoided
                  </span>
                </div>
              </div>
            </section>

            {/* Section 7: Latency, Token Overhead & Efficiency */}
            <section id="latency-efficiency" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                7. Latency, Token Overhead & Efficiency
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                A common critique of cognitive memory systems is runtime latency. AEMA was designed for production latency constraints through asynchronous execution and compact strategy tuples:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#FFFFFF] border-[#EAE8E3]'
                      : 'bg-[#161614] border-[#242422]'
                  }`}
                >
                  <div
                    className={`flex items-center justify-between ${
                      isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'
                    }`}
                  >
                    <span className="text-[10px] uppercase">Retrieval Latency</span>
                    <Clock size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                    }`}
                  >
                    &lt; 25 ms
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Local SQLite / pgvector cosine
                  </span>
                </div>

                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#FFFFFF] border-[#EAE8E3]'
                      : 'bg-[#161614] border-[#242422]'
                  }`}
                >
                  <div
                    className={`flex items-center justify-between ${
                      isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'
                    }`}
                  >
                    <span className="text-[10px] uppercase">Token Reduction</span>
                    <Coins size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                    }`}
                  >
                    41.2%
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Compact strategy lessons vs raw logs
                  </span>
                </div>

                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#FFFFFF] border-[#EAE8E3]'
                      : 'bg-[#161614] border-[#242422]'
                  }`}
                >
                  <div
                    className={`flex items-center justify-between ${
                      isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'
                    }`}
                  >
                    <span className="text-[10px] uppercase">Background Overhead</span>
                    <Zap size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                    }`}
                  >
                    0 ms
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Async evaluation & trust updates
                  </span>
                </div>
              </div>
            </section>

            {/* Section 8: Statistical Significance (McNemar Test) */}
            <section id="statistical-rigor" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                8. Statistical Significance: McNemar Paired Contingency Test
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Because trials are matched pairs evaluated on identical problem inputs, the McNemar test with continuity correction was performed:
              </p>

              <div
                className={`p-4 rounded-lg border font-mono text-xs space-y-2 ${
                  isLight
                    ? 'border-[#EAE8E3] bg-[#FFFFFF]'
                    : 'border-[#242422] bg-[#161614]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    McNemar Chi-Square (&chi;²):
                  </span>
                  <span
                    className={`font-bold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    98.01
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Degrees of Freedom:
                  </span>
                  <span className={isLight ? 'text-[#141413]' : 'text-[#EDECE8]'}>1</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Two-Tailed p-value:
                  </span>
                  <span
                    className={`font-bold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    p = 1.192 × 10⁻⁷ (p &lt; 0.0001)
                  </span>
                </div>
                <div
                  className={`flex items-center justify-between border-t pt-2 ${
                    isLight ? 'border-[#EAE8E3]' : 'border-[#242422]'
                  }`}
                >
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Conclusion:
                  </span>
                  <span className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}>
                    Statistically significant rejection of null hypothesis
                  </span>
                </div>
              </div>
            </section>

            {/* Footer Navigation */}
            <div
              className={`pt-10 border-t flex items-center justify-between text-xs font-mono ${
                isLight ? 'border-[#EAE8E3] text-[#8C8B85]' : 'border-[#242422] text-[#7E7D77]'
              }`}
            >
              <span>AEMA Empirical Benchmark Suite</span>
              <a
                href="#top"
                onClick={() => {
                  if (mainRef.current) {
                    mainRef.current.scrollTo({ top: 0, behavior: 'smooth' })
                  } else {
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }
                }}
                className={`transition-colors ${
                  isLight ? 'hover:text-[#141413]' : 'hover:text-[#EDECE8]'
                }`}
              >
                Back to top &uarr;
              </a>
            </div>
          </div>
        </main>

        {/* Column 3: Right "On this page" Outline */}
        <aside
          className={`hidden xl:block w-64 shrink-0 p-8 border-l text-xs font-mono transition-colors ${
            isLight
              ? 'border-[#EAE8E3] bg-[#FAFAF7]'
              : 'border-[#242422] bg-[#141412]'
          }`}
        >
          <div className="sticky top-20 space-y-3">
            <div
              className={`text-[11px] font-mono uppercase tracking-wider font-semibold flex items-center gap-1.5 ${
                isLight ? 'text-[#8A8985]' : 'text-[#7E7D77]'
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
              {BENCHMARK_SECTIONS.map((sec) => {
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
                        ? 'text-[#6B7280] hover:text-[#141413]'
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
