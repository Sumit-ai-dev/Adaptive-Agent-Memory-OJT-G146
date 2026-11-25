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
    label: '1. Executive Summary & Setup',
  },
  {
    id: 'comparative-matrix',
    title: 'Comparative Matrix',
    group: 'Protocol & Suites',
    label: '2. Comparative Benchmark Matrix',
  },
  {
    id: 'confirmatory-traps',
    title: 'Conflict Resolution',
    group: 'Protocol & Suites',
    label: '3. MemoryAgentBench: Conflict Resolution',
  },
  {
    id: 'hotpotqa-contradiction',
    title: 'Accurate Retrieval',
    group: 'Protocol & Suites',
    label: '4. MemoryAgentBench: Accurate Retrieval',
  },
  {
    id: 'toolbench-deprecation',
    title: 'API Evolution',
    group: 'Performance & Rigor',
    label: '5. Python API Evolution & Quarantine',
  },
  {
    id: 'alfworld-planning',
    title: 'Long-Range Understanding',
    group: 'Performance & Rigor',
    label: '6. MemoryAgentBench: Long-Range Understanding',
  },
  {
    id: 'latency-efficiency',
    title: 'Latency & Tokens',
    group: 'Performance & Rigor',
    label: '7. Latency & Token Economy',
  },
  {
    id: 'statistical-rigor',
    title: 'AEMA-v2 Roadmap',
    group: 'Performance & Rigor',
    label: '8. Analysis & AEMA-v2 Research Roadmap',
  },
]

const BENCHMARK_KEYWORDS: Record<string, string> = {
  'executive-summary': 'executive summary pilot evaluation llama 3.1 8b ollama 525 records 105 tasks 5 conditions vanilla naive rag recency symmetric aema',
  'comparative-matrix': 'comparative benchmark matrix table conflict resolution accurate retrieval python api evolution long-range test-time learning',
  'confirmatory-traps': 'memoryagentbench conflict resolution factconsolidation obsolete intrusions exact match token f1 moscow france malaysia quarantine',
  'hotpotqa-contradiction': 'memoryagentbench accurate retrieval ruler ruler_qa1 semantic metric prompt tokens similarity threshold 0.60',
  'toolbench-deprecation': 'python api evolution pydantic model_dump dict pandas sqlalchemy pytest subprocess deprecation',
  'alfworld-planning': 'memoryagentbench long-range understanding detective_qa 4 books 311 chunks token economy prompt reduction',
  'latency-efficiency': 'latency token overhead token savings prompt tokens milliseconds efficiency execution overhead',
  'statistical-rigor': 'analysis roadmap aema-v2 adaptive retrieval threshold test-time learning demonstration buffer research limitations'
}

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
      const allIds = BENCHMARK_SECTIONS.map((s) => s.id)
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

  const groups: BenchmarkSection['group'][] = [
    'Protocol & Suites',
    'Performance & Rigor',
  ]

  const q = searchQuery.toLowerCase().trim()
  const filteredSections = BENCHMARK_SECTIONS.filter((sec) => {
    if (!q) return true
    const kw = BENCHMARK_KEYWORDS[sec.id] || ''
    return (
      sec.title.toLowerCase().includes(q) ||
      sec.label.toLowerCase().includes(q) ||
      kw.includes(q)
    )
  })

  const isSectionVisible = (id: string) => !q || filteredSections.some((s) => s.id === id)

  return (
    <div
      className={`min-h-screen flex flex-col font-sans ${
        isLight
          ? 'bg-[#FAFAF7] text-[#141413] selection:bg-[#059669]/20 selection:text-[#059669]'
          : 'bg-[#141412] text-[#EDECE8] selection:bg-[#4EAA79]/20 selection:text-[#4EAA79]'
      }`}
    >
      {/* Top Global Navigation Header */}
      <header
        className={`sticky top-0 z-40 w-full border-b backdrop-blur-md ${
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
                className={`w-full pl-8 pr-7 py-1.5 rounded-md text-xs font-mono transition-colors focus:outline-none ${
                  isLight
                    ? 'bg-[#F0EFEA] border border-[#E5E3DC] text-[#141413] placeholder-[#8A8985] focus:border-[#059669]'
                    : 'bg-[#181816] border border-[#262624] text-[#EDECE8] placeholder-[#7E7D77] focus:border-[#4EAA79]'
                }`}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-2 text-[#7E7D77] hover:text-[#EDECE8] cursor-pointer"
                  title="Clear search"
                  aria-label="Clear search"
                >
                  <X size={13} />
                </button>
              )}
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
          <div className="sm:hidden mb-4 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search benchmarks..."
              className={`w-full pl-3 pr-7 py-1.5 rounded text-xs font-mono border ${
                isLight
                  ? 'bg-white border-[#EAE8E3] text-[#141413] placeholder-[#8A8985]'
                  : 'bg-[#181816] border-[#262624] text-[#EDECE8] placeholder-[#7E7D77]'
              }`}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-2 text-[#7E7D77] hover:text-[#EDECE8] cursor-pointer"
                title="Clear search"
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            )}
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

            {/* Search Match Banner if query active */}
            {q && (
              <div
                className={`p-3 rounded-lg border text-xs font-mono flex items-center justify-between ${
                  isLight
                    ? 'bg-[#EFECE6] border-[#DCD9D0] text-[#141413]'
                    : 'bg-[#1A1A17] border-[#2A2A26] text-[#EDECE8]'
                }`}
              >
                <span>
                  Showing <strong className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}>{filteredSections.length}</strong> of{' '}
                  {BENCHMARK_SECTIONS.length} benchmark suites matching &ldquo;{searchQuery}&rdquo;
                </span>
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className={`text-[11px] underline underline-offset-2 transition-colors cursor-pointer ${
                    isLight ? 'text-[#059669] hover:text-[#047857]' : 'text-[#4EAA79] hover:text-[#5EBA89]'
                  }`}
                >
                  Clear search
                </button>
              </div>
            )}

            {/* Empty Search State */}
            {q && filteredSections.length === 0 && (
              <div className="py-16 text-center space-y-3 font-mono">
                <Search size={24} className="mx-auto text-[#7E7D77]" />
                <div className={`text-base font-semibold ${isLight ? 'text-[#141413]' : 'text-[#EDECE8]'}`}>
                  No benchmark suites match &ldquo;{searchQuery}&rdquo;
                </div>
                <p className={`text-xs ${isLight ? 'text-[#6B6A65]' : 'text-[#7E7D77]'}`}>
                  Try searching for &ldquo;mcnemar&rdquo;, &ldquo;quarantine&rdquo;, &ldquo;python&rdquo;, &ldquo;traps&rdquo;, or &ldquo;latency&rdquo;.
                </p>
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className={`px-3 py-1.5 rounded text-xs font-mono border transition-colors cursor-pointer ${
                    isLight
                      ? 'border-[#EAE8E3] bg-[#FFFFFF] text-[#141413] hover:bg-[#F5F4EF]'
                      : 'border-[#2E2E2A] bg-[#1E1E1B] text-[#EDECE8] hover:bg-[#252522]'
                  }`}
                >
                  Clear search
                </button>
              </div>
            )}

            {/* Section 1: Executive Summary & Evaluation Protocol */}
            {isSectionVisible('executive-summary') && (
            <section id="executive-summary" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                1. Executive Summary & Experimental Setup
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                The objective of this evaluation was to investigate whether an Adaptive AI Agent with Persistent Experience Memory (AEMA) can improve an AI agent's ability to use past experiences while avoiding the negative effects of unreliable, outdated, or conflicting memories.
              </p>
              <div
                className={`p-4 rounded-lg border font-mono text-xs space-y-2.5 ${
                  isLight ? 'bg-white border-[#EAE8E3]' : 'bg-[#161614] border-[#242422]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>Evaluation Phase:</span>
                  <span className="font-semibold">Pilot Benchmark Evaluation</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>Model Backend:</span>
                  <span className="font-semibold">Ollama (Llama 3.1 8B, Temp: 0, Seed: 42)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>Hardware Platform:</span>
                  <span className="font-semibold">Windows 11 PC, NVIDIA RTX 3060 12GB, 16GB RAM</span>
                </div>
                <div className="flex items-center justify-between border-t pt-2 border-[#EAE8E3] dark:border-[#242422]">
                  <span className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>Evaluation Coverage:</span>
                  <span className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                    105 Distinct Tasks &times; 5 Conditions = 525 Evaluation Records
                  </span>
                </div>
              </div>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Five comparative conditions were evaluated across identical task inputs:
              </p>
              <ul
                className={`list-disc list-inside text-xs font-mono space-y-2 pl-2 ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                <li>
                  <span className={`font-semibold ${isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'}`}>
                    Vanilla:
                  </span>{' '}
                  LLM operating without external persistent memory.
                </li>
                <li>
                  <span className="text-[#D9534F] font-semibold">Naive RAG:</span> Retrieves relevant memories solely by cosine similarity without adaptive trust management.
                </li>
                <li>
                  <span className="font-semibold text-amber-500">Recency:</span> Uses recency-oriented memory retrieval and selection.
                </li>
                <li>
                  <span className="font-semibold text-sky-500">Symmetric:</span> Uses symmetric memory-based retrieval and selection.
                </li>
                <li>
                  <span
                    className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    Adaptive (AEMA):
                  </span>{' '}
                  Reliability-aware experiential memory with Asymmetric EMA calibration and Theorem 1 deterministic quarantine.
                </li>
              </ul>
            </section>
            )}

            {/* Section 2: Comparative Matrix */}
            {isSectionVisible('comparative-matrix') && (
            <section id="comparative-matrix" className="space-y-4 scroll-mt-20">
              <div className="flex items-center justify-between">
                <h2
                  className={`text-xl font-serif tracking-tight ${
                    isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                  }`}
                >
                  2. Comparative Benchmark Matrix (5 Suites)
                </h2>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    isLight
                      ? 'bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]'
                      : 'bg-[#1E2E24] text-[#4EAA79] border-[#2E4234]'
                  }`}
                >
                  525 EVALUATIONS
                </span>
              </div>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Summary across all five empirical pilot evaluation suites:
              </p>

              {/* Live Interactive Benchmark Matrix Component */}
              <BenchmarkMatrix />
            </section>
            )}

            {/* Section 3: Conflict Resolution */}
            {isSectionVisible('confirmatory-traps') && (
            <section id="confirmatory-traps" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                3. MemoryAgentBench: Conflict Resolution
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Benchmark: MemoryAgentBench (Competency: Conflict Resolution, Split: factconsolidation_sh_6k, 25 tasks, 125 evaluation records). Evaluates whether an agent can handle conflicting information stored in memory (e.g. an earlier memory stating location is France, updated by a later memory to Malaysia).
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
                      <th className="p-3">Condition</th>
                      <th className="p-3">Semantic (SEM)</th>
                      <th className="p-3">Exact Match</th>
                      <th className="p-3">Token F1</th>
                      <th className="p-3 text-[#D9534F]">Obsolete Intrusions</th>
                      <th className="p-3">Mean Latency</th>
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
                      <td className="p-3">Vanilla</td>
                      <td className="p-3">20.0%</td>
                      <td className="p-3">16.0%</td>
                      <td className="p-3">16.4%</td>
                      <td className="p-3">0</td>
                      <td className="p-3">436.9 ms</td>
                    </tr>
                    <tr>
                      <td className="p-3 text-[#D9534F]">Naive RAG</td>
                      <td className="p-3">40.0%</td>
                      <td className="p-3">32.0%</td>
                      <td className="p-3">35.6%</td>
                      <td className="p-3 text-[#D9534F] font-bold">10</td>
                      <td className="p-3">1113.6 ms</td>
                    </tr>
                    <tr>
                      <td className="p-3">Recency</td>
                      <td className="p-3">40.0%</td>
                      <td className="p-3">28.0%</td>
                      <td className="p-3">32.9%</td>
                      <td className="p-3 text-[#D9534F]">9</td>
                      <td className="p-3">1117.9 ms</td>
                    </tr>
                    <tr>
                      <td className="p-3">Symmetric</td>
                      <td className="p-3 font-semibold">44.0%</td>
                      <td className="p-3">28.0%</td>
                      <td className="p-3">33.4%</td>
                      <td className="p-3 text-[#D9534F]">9</td>
                      <td className="p-3">1209.2 ms</td>
                    </tr>
                    <tr className={isLight ? 'bg-[#ECFDF5]/50' : 'bg-[#18201A]'}>
                      <td
                        className={`p-3 font-semibold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        AEMA (Adaptive)
                      </td>
                      <td className="p-3">40.0%</td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        40.0% (Top)
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        40.9% (Top)
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        3 (Lowest)
                      </td>
                      <td className="p-3">1039.1 ms</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p
                className={`text-xs leading-relaxed ${
                  isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'
                }`}
              >
                Key Finding: AEMA achieved the highest Exact Match (40.0%) and Token F1 (40.9%), with only 3 obsolete-memory intrusions compared to 9-10 for the retrieval baselines. In Task 24, AEMA successfully quarantined older Moscow location memories and retrieved the updated United States information.
              </p>
            </section>
            )}

            {/* Section 4: Accurate Retrieval */}
            {isSectionVisible('hotpotqa-contradiction') && (
            <section id="hotpotqa-contradiction" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                4. MemoryAgentBench: Accurate Retrieval
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Benchmark: MemoryAgentBench (Competency: Accurate Retrieval, Split: ruler_qa1_197K, 25 tasks, 125 evaluation records). Evaluates an agent's ability to locate and retrieve correct factual answers from memory.
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
                      <th className="p-3">Condition</th>
                      <th className="p-3">Semantic (SEM)</th>
                      <th className="p-3">Exact Match</th>
                      <th className="p-3">Token F1</th>
                      <th className="p-3">Mean Prompt Tokens</th>
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
                      <td className="p-3">Vanilla</td>
                      <td className="p-3">20.0%</td>
                      <td className="p-3">8.0%</td>
                      <td className="p-3">16.1%</td>
                      <td className="p-3">84.8 tokens</td>
                    </tr>
                    <tr>
                      <td className="p-3">Naive RAG</td>
                      <td className="p-3">56.0%</td>
                      <td className="p-3">44.0%</td>
                      <td className="p-3">54.8%</td>
                      <td className="p-3">537.4 tokens</td>
                    </tr>
                    <tr>
                      <td className="p-3">Recency</td>
                      <td className="p-3">60.0%</td>
                      <td className="p-3">48.0%</td>
                      <td className="p-3">59.5%</td>
                      <td className="p-3">598.2 tokens</td>
                    </tr>
                    <tr>
                      <td className="p-3">Symmetric</td>
                      <td className="p-3 font-semibold">68.0%</td>
                      <td className="p-3 font-semibold">52.0%</td>
                      <td className="p-3 font-semibold">66.4%</td>
                      <td className="p-3">603.6 tokens</td>
                    </tr>
                    <tr className={isLight ? 'bg-[#ECFDF5]/50' : 'bg-[#18201A]'}>
                      <td
                        className={`p-3 font-semibold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        AEMA (Adaptive)
                      </td>
                      <td className="p-3">40.0%</td>
                      <td className="p-3">32.0%</td>
                      <td className="p-3">39.5%</td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        233.4 tokens (61% lower)
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p
                className={`text-xs leading-relaxed ${
                  isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'
                }`}
              >
                Audit Observation: AEMA supplied substantially fewer prompt tokens (233.4 vs 603.6). Investigation showed the hardcoded 0.60 similarity threshold excluded some relevant memories, establishing an adaptive retrieval threshold as a priority for AEMA-v2.
              </p>
            </section>
            )}

            {/* Section 5: Python API Evolution */}
            {isSectionVisible('toolbench-deprecation') && (
            <section id="toolbench-deprecation" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                5. Python API Evolution & Deprecation Quarantine
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Supplementary custom benchmark (5 tasks, 25 records) evaluated with real pytest subprocess executions. Tests whether an agent avoids deprecated APIs (pandas append &rarr; concat, Pydantic dict &rarr; model_dump, SQLAlchemy engine.execute &rarr; conn.execute, inspect.getargspec &rarr; signature).
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
                    Vanilla Baseline
                  </span>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                    }`}
                  >
                    20.0% (1/5)
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Fails deprecated calls
                  </span>
                </div>
                <div
                  className={`p-4 rounded-lg border space-y-1 ${
                    isLight
                      ? 'bg-[#FFFFFF] border-[#EAE8E3]'
                      : 'bg-[#161614] border-[#242422]'
                  }`}
                >
                  <span className="text-[#D9534F] text-[10px]">Naive RAG & Recency</span>
                  <div className="text-xl font-bold text-[#D9534F]">20.0% (1/5)</div>
                  <span className="text-[10px] text-[#D9534F]">Re-injects model.dict()</span>
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
                    AEMA (Adaptive)
                  </span>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                    }`}
                  >
                    40.0% (2/5)
                  </div>
                  <span
                    className={`text-[10px] ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}
                  >
                    Quarantined dict() &rarr; model_dump()
                  </span>
                </div>
              </div>
              <p
                className={`text-xs leading-relaxed ${
                  isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'
                }`}
              >
                Key Finding: While Naive RAG and Recency repeatedly retrieved outdated memories recommending model.dict() and failed, AEMA downgraded low-trust legacy memories, allowing the model to generate model.model_dump() and pass verification.
              </p>
            </section>
            )}

            {/* Section 6: Long-Range Understanding */}
            {isSectionVisible('alfworld-planning') && (
            <section id="alfworld-planning" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                6. MemoryAgentBench: Long-Range Understanding
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                Benchmark: MemoryAgentBench (Competency: Long-Range Understanding, Split: detective_qa, 4 books, 311 chunks, 25 tasks, 125 evaluation records). Evaluates information retrieval and answer quality across long multi-chapter texts.
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
                      <th className="p-3">Condition</th>
                      <th className="p-3">Accuracy</th>
                      <th className="p-3">Exact Match</th>
                      <th className="p-3">Token F1</th>
                      <th className="p-3">Prompt Tokens</th>
                      <th className="p-3">Mean Latency</th>
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
                      <td className="p-3">Vanilla</td>
                      <td className="p-3 font-semibold">40.0% (10/25)</td>
                      <td className="p-3">0.28</td>
                      <td className="p-3">0.3594</td>
                      <td className="p-3">389.4</td>
                      <td className="p-3">1907.0 ms</td>
                    </tr>
                    <tr>
                      <td className="p-3 text-[#D9534F]">Naive RAG</td>
                      <td className="p-3">32.0% (8/25)</td>
                      <td className="p-3">0.32</td>
                      <td className="p-3">0.4462</td>
                      <td className="p-3 text-[#D9534F]">2044.1</td>
                      <td className="p-3">9274.5 ms</td>
                    </tr>
                    <tr>
                      <td className="p-3">Recency</td>
                      <td className="p-3">32.0% (8/25)</td>
                      <td className="p-3">0.32</td>
                      <td className="p-3">0.4622</td>
                      <td className="p-3 text-[#D9534F]">2050.0</td>
                      <td className="p-3">8619.9 ms</td>
                    </tr>
                    <tr>
                      <td className="p-3">Symmetric</td>
                      <td className="p-3">28.0% (7/25)</td>
                      <td className="p-3">0.24</td>
                      <td className="p-3">0.3476</td>
                      <td className="p-3 text-[#D9534F]">2050.0</td>
                      <td className="p-3">9199.2 ms</td>
                    </tr>
                    <tr className={isLight ? 'bg-[#ECFDF5]/50' : 'bg-[#18201A]'}>
                      <td
                        className={`p-3 font-semibold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        AEMA (Adaptive)
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        40.0% (Tied Top)
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        0.32
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        0.4489
                      </td>
                      <td
                        className={`p-3 font-bold ${
                          isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                        }`}
                      >
                        384.4 (81% savings)
                      </td>
                      <td className="p-3">9512.8 ms</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p
                className={`text-xs leading-relaxed ${
                  isLight ? 'text-[#6B7280]' : 'text-[#9E9D96]'
                }`}
              >
                Key Finding: AEMA tied top accuracy (40.0%) while using 384.4 prompt tokens compared to over 2,044 tokens for the retrieval baselines, demonstrating compact contextualization without sacrificing accuracy.
              </p>
            </section>
            )}

            {/* Section 7: Latency, Token Overhead & Efficiency */}
            {isSectionVisible('latency-efficiency') && (
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
                Empirical token and latency characteristics measured across pilot runs:
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
                    <span className="text-[10px] uppercase">Conflict Latency</span>
                    <Clock size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                    }`}
                  >
                    1,039 ms
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Faster than Symmetric (1209ms)
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
                    <span className="text-[10px] uppercase">Prompt Compression</span>
                    <Coins size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#059669]' : 'text-[#4EAA79]'
                    }`}
                  >
                    81.2%
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    384.4 vs 2,050 prompt tokens
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
                    <span className="text-[10px] uppercase">Retrieval Lookup</span>
                    <Zap size={13} className={isLight ? 'text-[#059669]' : 'text-[#4EAA79]'} />
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                    }`}
                  >
                    &lt; 25 ms
                  </div>
                  <span className={`text-[10px] ${isLight ? 'text-[#8C8B85]' : 'text-[#7E7D77]'}`}>
                    Local SQLite / pgvector cosine
                  </span>
                </div>
              </div>
            </section>
            )}

            {/* Section 8: Analysis & AEMA-v2 Research Roadmap */}
            {isSectionVisible('statistical-rigor') && (
            <section id="statistical-rigor" className="space-y-4 scroll-mt-20">
              <h2
                className={`text-xl font-serif tracking-tight ${
                  isLight ? 'text-[#141413]' : 'text-[#EDECE8]'
                }`}
              >
                8. Evaluation Analysis & AEMA-v2 Research Roadmap
              </h2>
              <p
                className={`text-sm leading-relaxed ${
                  isLight ? 'text-[#4A4945]' : 'text-[#9E9D96]'
                }`}
              >
                The pilot evaluation provides clear empirical evidence for reliability-aware memory management while establishing specific technical targets for the next development phase:
              </p>

              <div
                className={`p-4 rounded-lg border font-mono text-xs space-y-3 ${
                  isLight
                    ? 'border-[#EAE8E3] bg-[#FFFFFF]'
                    : 'border-[#242422] bg-[#161614]'
                }`}
              >
                <div className="space-y-1">
                  <span className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                    1. Adaptive Retrieval Threshold (AEMA-v2)
                  </span>
                  <p className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Replace the static 0.60 threshold with a dynamic function factoring semantic similarity, memory reliability, age, and recency of verification to avoid excluding useful memories.
                  </p>
                </div>
                <div className="space-y-1 border-t pt-2 border-[#EAE8E3] dark:border-[#242422]">
                  <span className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                    2. Decouple Relevance from Reliability
                  </span>
                  <p className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Maintain dual-axis scoring so memory selection evaluates semantic match independently from operational track record.
                  </p>
                </div>
                <div className="space-y-1 border-t pt-2 border-[#EAE8E3] dark:border-[#242422]">
                  <span className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                    3. Sequential Demonstration Buffering
                  </span>
                  <p className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Introduce dedicated buffering for in-context demonstrations to enable effective test-time learning before promotion into long-term memory.
                  </p>
                </div>
                <div className="space-y-1 border-t pt-2 border-[#EAE8E3] dark:border-[#242422]">
                  <span className={`font-semibold ${isLight ? 'text-[#059669]' : 'text-[#4EAA79]'}`}>
                    4. Explicit Parametric-Memory Conflict Handling
                  </span>
                  <p className={isLight ? 'text-[#6B7280]' : 'text-[#7E7D77]'}>
                    Explicitly distinguish pretrained parametric knowledge from task-specific counterfactuals to ensure the model adheres to verified retained memories.
                  </p>
                </div>
              </div>
            </section>
            )}

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
