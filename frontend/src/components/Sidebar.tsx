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
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from './ThemeToggle'

export type TabType = 'overview' | 'studio' | 'memory' | 'runs' | 'research' | 'settings'

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
  { id: 'research', label: 'Research & Proofs', icon: FlaskConical },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export default function Sidebar({
  activeTab,
  onSelectTab,
  isDemo = false,
  onExitDemo,
  onOpenAuth,
}: SidebarProps) {
  const { user, signOut } = useAuth()

  const displayName = user?.name || user?.email?.split('@')[0] || (isDemo ? 'Demo Researcher' : 'User')

  return (
    <aside className="w-64 shrink-0 border-r flex flex-col h-screen sticky top-0 transition-colors
      bg-[#FFFFFF] border-[#E6E6E1] text-[#18181B]
      dark:bg-[#0C0E14] dark:border-[#252B3B] dark:text-[#F4F4F6]"
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm font-mono font-bold text-sm">
            Æ
          </div>
          <div>
            <div className="font-semibold text-sm tracking-tight flex items-center gap-1.5">
              <span>AEMA</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600 dark:bg-[#1A1F2C] dark:text-zinc-400 border border-[#E6E6E1] dark:border-[#252B3B]">
                v0.1.0
              </span>
            </div>
            <div className="text-[11px] text-zinc-400 font-mono">
              Agent Memory Engine
            </div>
          </div>
        </div>

        <ThemeToggle />
      </div>

      {/* Workspace Selector */}
      <div className="p-3 border-b border-[#E6E6E1] dark:border-[#252B3B]">
        <div className="p-2 rounded-xl border flex items-center justify-between text-xs transition-colors
          bg-zinc-50 border-[#E6E6E1] text-zinc-800
          dark:bg-[#131722] dark:border-[#252B3B] dark:text-zinc-200"
        >
          <div className="flex items-center gap-2 truncate">
            <Layers size={14} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
            <div className="truncate">
              <span className="font-medium block truncate">
                {isDemo ? 'Sandbox Protocol' : 'Production Cluster'}
              </span>
              <span className="text-[10px] text-zinc-400 font-mono block">
                {isDemo ? 'Seeded N=30 Environment' : 'Primary Agent Node'}
              </span>
            </div>
          </div>
          <ChevronDown size={14} className="text-zinc-400 shrink-0" />
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all text-left cursor-pointer ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-[#131722]'
              }`}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* Demo Mode Banner (if active) */}
      {isDemo && (
        <div className="p-3 mx-3 mb-2 rounded-xl border bg-indigo-50/70 border-indigo-200 dark:bg-indigo-950/30 dark:border-indigo-900/50 text-indigo-950 dark:text-indigo-200 text-xs">
          <div className="flex items-center gap-1.5 font-semibold font-mono text-[11px] mb-1">
            <Sparkles size={12} className="text-indigo-600 dark:text-indigo-400" />
            <span>DEMO SANDBOX</span>
          </div>
          <p className="text-[11px] text-zinc-600 dark:text-zinc-400 mb-2 leading-relaxed">
            Running with protocol-frozen benchmark data.
          </p>
          {onOpenAuth && (
            <button
              onClick={onOpenAuth}
              className="w-full py-1.5 px-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-[11px] font-semibold transition-colors text-center cursor-pointer"
            >
              Sign In to Real Account
            </button>
          )}
        </div>
      )}

      {/* User / Session Footer */}
      <div className="p-3 border-t border-[#E6E6E1] dark:border-[#252B3B] flex items-center justify-between">
        <div className="flex items-center gap-2 truncate">
          <div className="w-7 h-7 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center font-mono text-xs font-semibold text-zinc-700 dark:text-zinc-300">
            {displayName[0].toUpperCase()}
          </div>
          <div className="truncate">
            <div className="text-xs font-medium truncate">{displayName}</div>
            <div className="text-[10px] text-zinc-400 font-mono truncate">
              {isDemo ? 'demo@aema.ai' : user?.email || 'authenticated'}
            </div>
          </div>
        </div>

        {isDemo ? (
          onExitDemo && (
            <button
              onClick={onExitDemo}
              title="Exit Demo Sandbox"
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-[#131722] transition-colors"
            >
              <LogOut size={15} />
            </button>
          )
        ) : (
          <button
            onClick={() => signOut()}
            title="Sign Out"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
          >
            <LogOut size={15} />
          </button>
        )}
      </div>
    </aside>
  )
}
