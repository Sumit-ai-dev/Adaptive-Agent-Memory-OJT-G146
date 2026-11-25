import {
  LayoutDashboard,
  Terminal,
  Database,
  ListTree,
  FlaskConical,
  Settings,
  LogOut,
  Layers,
  ChevronDown,
  Sparkles,
  PanelLeftOpen,
  BookOpen,
  Award,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export type TabType = 'overview' | 'studio' | 'memory' | 'runs' | 'settings'

interface SidebarProps {
  activeTab: TabType
  onSelectTab: (tab: TabType) => void
  isDemo?: boolean
  onExitDemo?: () => void
  onOpenAuth?: () => void
  collapsed?: boolean
  onToggleCollapse?: () => void
}

const NAV_ITEMS: { id: TabType; label: string; icon: any }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'studio', label: 'Execution Studio', icon: Terminal },
  { id: 'memory', label: 'Experiential Memory', icon: Database },
  { id: 'runs', label: 'Runs & Traces', icon: ListTree },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export default function Sidebar({
  activeTab,
  onSelectTab,
  isDemo = false,
  onExitDemo,
  onOpenAuth,
  collapsed = false,
  onToggleCollapse,
}: SidebarProps) {
  const { user, signOut } = useAuth()

  const displayName = user?.name || user?.email?.split('@')[0] || (isDemo ? 'Demo Researcher' : 'User')

  if (collapsed) {
    return (
      <aside
        className="w-[64px] shrink-0 border-r border-[#242422] bg-[#161614] text-[#EDECE8] flex flex-col h-screen sticky top-0 transition-all duration-200 items-center py-3 z-30 select-none overflow-visible"
      >
        {/* Brand Icon & Expand Button with Immediate Tooltip */}
        <div className="flex flex-col items-center gap-2 pb-3 border-b border-[#242422] w-full">
          <div className="relative group/brand flex items-center justify-center">
            <div
              className="w-8 h-8 rounded-lg bg-[#20201D] border border-[#2E2E2A] flex items-center justify-center text-[#EDECE8] font-mono font-bold text-xs cursor-default"
              aria-label="AEMA Engine"
            >
              Æ
            </div>
            <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/brand:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
              <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                AEMA Engine
              </div>
            </div>
          </div>

          {onToggleCollapse && (
            <div className="relative group/expand flex items-center justify-center">
              <button
                onClick={onToggleCollapse}
                className="p-1 rounded text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#20201D] transition-colors cursor-pointer"
                aria-label="Expand main sidebar"
              >
                <PanelLeftOpen size={15} />
              </button>
              <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/expand:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
                <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                  Expand sidebar
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Workspace Icon */}
        <div className="my-2.5 w-full flex justify-center">
          <div className="relative group/ws flex items-center justify-center">
            <div
              className="w-8 h-8 rounded-lg border border-[#2E2E2A] bg-[#1A1A17] text-[#9E9D96] flex items-center justify-center cursor-default"
              aria-label={isDemo ? 'Sandbox Protocol (N=30)' : 'Production Cluster'}
            >
              <Layers size={14} />
            </div>
            <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/ws:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
              <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                {isDemo ? 'Sandbox Protocol (N=30)' : 'Production Cluster'}
              </div>
            </div>
          </div>
        </div>

        {/* Navigation List (Icon Only with Fast Instant Tooltips) */}
        <nav className="flex-1 w-full space-y-1.5 px-2 flex flex-col items-center overflow-visible">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id

            return (
              <div key={item.id} className="relative group/nav flex items-center justify-center w-full">
                <button
                  onClick={() => onSelectTab(item.id)}
                  aria-label={item.label}
                  className={`w-9 h-9 flex items-center justify-center rounded-lg transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-[#22221E] text-white border border-[#2E2E2A]'
                      : 'text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
                  }`}
                >
                  <Icon size={16} />
                </button>
                {/* Instant Obsidian Floating Tooltip (<100ms) */}
                <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/nav:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
                  <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl flex items-center gap-1.5">
                    <span>{item.label}</span>
                  </div>
                </div>
              </div>
            )
          })}

          <div className="w-6 border-t border-[#242422] my-1" />

          {/* Research & Proofs Link */}
          <div className="relative group/portal flex items-center justify-center w-full">
            <Link
              to="/research"
              aria-label="Research & Proofs"
              className="w-9 h-9 flex items-center justify-center rounded-lg text-[#7E7D77] hover:text-[#4EAA79] hover:bg-[#1E1E1B] transition-colors"
            >
              <FlaskConical size={16} />
            </Link>
            <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/portal:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
              <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                Research & Proofs
              </div>
            </div>
          </div>

          {/* Empirical Benchmarks Link */}
          <div className="relative group/bench flex items-center justify-center w-full">
            <Link
              to="/benchmarks"
              aria-label="Empirical Benchmarks"
              className="w-9 h-9 flex items-center justify-center rounded-lg text-[#7E7D77] hover:text-[#4EAA79] hover:bg-[#1E1E1B] transition-colors"
            >
              <Award size={16} />
            </Link>
            <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/bench:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
              <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                Empirical Benchmarks
              </div>
            </div>
          </div>

          {/* Documentation Link */}
          <div className="relative group/doc flex items-center justify-center w-full">
            <Link
              to="/docs"
              aria-label="Documentation"
              className="w-9 h-9 flex items-center justify-center rounded-lg text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#1E1E1B] transition-colors"
            >
              <BookOpen size={16} />
            </Link>
            <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/doc:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
              <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                Documentation
              </div>
            </div>
          </div>
        </nav>

        {/* Compact Footer */}
        <div className="pt-3 border-t border-[#242422] w-full flex flex-col items-center gap-2">
          <div className="relative group/user flex items-center justify-center">
            <div
              className="w-7 h-7 rounded-full bg-[#242420] border border-[#2E2E2A] flex items-center justify-center font-mono text-[11px] font-semibold text-[#EDECE8] cursor-default"
              aria-label={`${displayName} (${isDemo ? 'Demo Mode' : user?.email || 'Authenticated'})`}
            >
              {displayName[0].toUpperCase()}
            </div>
            <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/user:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
              <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                {displayName} ({isDemo ? 'Demo Mode' : user?.email || 'Authenticated'})
              </div>
            </div>
          </div>

          {isDemo ? (
            onExitDemo && (
              <div className="relative group/logout flex items-center justify-center">
                <button
                  onClick={onExitDemo}
                  aria-label="Exit Demo Sandbox"
                  className="p-1 rounded text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#20201D] transition-colors cursor-pointer"
                >
                  <LogOut size={14} />
                </button>
                <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/logout:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
                  <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                    Exit Demo Sandbox
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="relative group/logout flex items-center justify-center">
              <button
                onClick={() => signOut()}
                aria-label="Sign Out"
                className="p-1 rounded text-[#7E7D77] hover:text-[#D9534F] hover:bg-[#20201D] transition-colors cursor-pointer"
              >
                <LogOut size={14} />
              </button>
              <div className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 -translate-y-1/2 opacity-0 group-hover/logout:opacity-100 transition-opacity duration-100 z-50 whitespace-nowrap">
                <div className="bg-[#1C1C1A] text-[#EDECE8] border border-[#2E2E2A] px-2.5 py-1 rounded-md text-xs font-mono shadow-2xl">
                  Sign Out
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    )
  }

  return (
    <aside
      className="w-60 shrink-0 border-r border-[#242422] bg-[#161614] text-[#EDECE8] flex flex-col h-screen sticky top-0 transition-all duration-200 z-20 select-none"
    >
      {/* Brand Header (NO duplicate collapse button here) */}
      <div className="p-4 border-b border-[#242422] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-[#20201D] border border-[#2E2E2A] flex items-center justify-center text-[#EDECE8] font-mono font-bold text-xs">
            Æ
          </div>
          <div>
            <div className="font-semibold text-xs tracking-tight text-white flex items-center gap-1.5">
              <span>AEMA</span>
              <span className="text-[10px] font-mono px-1 rounded bg-[#20201D] text-[#9E9D96] border border-[#2E2E2A]">
                v0.1.0
              </span>
            </div>
            <div className="text-[10px] text-[#7E7D77] font-mono">
              Experiential Agent Core
            </div>
          </div>
        </div>
      </div>

      {/* Workspace Selector */}
      <div className="p-3 border-b border-[#242422]">
        <div className="p-2 rounded border border-[#242422] bg-[#1A1A17] flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 truncate">
            <Layers size={13} className="text-[#9E9D96] shrink-0" />
            <div className="truncate">
              <span className="font-medium block truncate text-[#EDECE8] text-[11px]">
                {isDemo ? 'Sandbox Protocol' : 'Production Cluster'}
              </span>
              <span className="text-[9px] text-[#7E7D77] font-mono block">
                {isDemo ? 'Seeded N=30 Environment' : 'Primary Agent Node'}
              </span>
            </div>
          </div>
          <ChevronDown size={12} className="text-[#7E7D77] shrink-0" />
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded text-xs transition-colors text-left cursor-pointer ${
                isActive
                  ? 'bg-[#22221E] text-white font-medium border border-[#2E2E2A]'
                  : 'text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]'
              }`}
            >
              <Icon size={15} />
              <span>{item.label}</span>
            </button>
          )
        })}

        {/* Portals & Research Links */}
        <div className="pt-3 mt-3 border-t border-[#242422] space-y-0.5">
          <div className="text-[10px] font-mono uppercase tracking-widest text-[#7E7D77] px-3 py-1 font-semibold">
            Portals & Research
          </div>
          <Link
            to="/research"
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded text-xs transition-colors text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]"
          >
            <FlaskConical size={15} className="text-[#4EAA79]" />
            <span>Research & Proofs</span>
          </Link>
          <Link
            to="/benchmarks"
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded text-xs transition-colors text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]"
          >
            <Award size={15} className="text-[#4EAA79]" />
            <span>Empirical Benchmarks</span>
          </Link>
          <Link
            to="/docs"
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded text-xs transition-colors text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#1E1E1B]"
          >
            <BookOpen size={15} className="text-[#9E9D96]" />
            <span>Documentation</span>
          </Link>
        </div>
      </nav>

      {/* Demo Mode Banner (if active) */}
      {isDemo && (
        <div className="p-3 mx-2 mb-2 rounded border border-[#262623] bg-[#1A1A17] text-[#EDECE8] text-xs">
          <div className="flex items-center gap-1.5 font-semibold font-mono text-[10px] text-[#E67E22] mb-1">
            <Sparkles size={11} />
            <span>DEMO SANDBOX</span>
          </div>
          <p className="text-[10px] text-[#7E7D77] mb-2 leading-relaxed">
            Running with protocol-frozen benchmark data.
          </p>
          {onOpenAuth && (
            <button
              onClick={onOpenAuth}
              className="w-full py-1.5 px-2 rounded bg-[#EDECE8] hover:bg-white text-[#141412] font-mono text-[10px] font-semibold transition-colors text-center cursor-pointer"
            >
              Sign In to Real Account
            </button>
          )}
        </div>
      )}

      {/* User / Session Footer */}
      <div className="p-3 border-t border-[#242422] flex items-center justify-between">
        <div className="flex items-center gap-2 truncate">
          <div className="w-6 h-6 rounded-full bg-[#20201D] border border-[#2E2E2A] flex items-center justify-center font-mono text-[10px] font-semibold text-[#EDECE8]">
            {displayName[0].toUpperCase()}
          </div>
          <div className="truncate">
            <div className="text-xs font-medium truncate text-[#EDECE8]">{displayName}</div>
            <div className="text-[9px] text-[#7E7D77] font-mono truncate">
              {isDemo ? 'demo@aema.ai' : user?.email || 'authenticated'}
            </div>
          </div>
        </div>

        {isDemo ? (
          onExitDemo && (
            <button
              onClick={onExitDemo}
              title="Exit Demo Sandbox"
              className="p-1 rounded text-[#7E7D77] hover:text-[#EDECE8] hover:bg-[#20201D] transition-colors cursor-pointer"
            >
              <LogOut size={14} />
            </button>
          )
        ) : (
          <button
            onClick={() => signOut()}
            title="Sign Out"
            className="p-1 rounded text-[#7E7D77] hover:text-[#D9534F] hover:bg-[#20201D] transition-colors cursor-pointer"
          >
            <LogOut size={14} />
          </button>
        )}
      </div>
    </aside>
  )
}
