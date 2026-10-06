import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Brain,
  LayoutDashboard,
  Bot,
  Database,
  History,
  LogOut,
  ArrowLeft,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export default function WorkspaceHeader() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/')
  }

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={14} /> },
    { path: '/agent', label: 'Agent Workspace', icon: <Bot size={14} /> },
    { path: '/agent/memory', label: 'Experiences', icon: <Database size={14} /> },
    { path: '/agent/runs', label: 'Run History', icon: <History size={14} /> },
  ]

  const displayName = user?.name || user?.email?.split('@')[0] || 'User'

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 backdrop-blur-xl bg-[#0a0010]/85">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center anim-gradient-bg shadow-md group-hover:scale-105 transition-transform">
              <Brain size={16} className="text-white" />
            </div>
            <span className="text-white font-bold text-base font-display tracking-tight">
              MemoryAgent
            </span>
          </Link>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive =
                item.path === '/agent'
                  ? location.pathname === '/agent' || location.pathname === '/agent/chat'
                  : location.pathname === item.path

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono transition-all ${
                    isActive
                      ? 'bg-purple-500/20 text-purple-200 border border-purple-500/30 font-semibold shadow-sm'
                      : 'text-white/60 hover:text-white hover:bg-white/5 border border-transparent'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Right Session Controls */}
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/60 hover:text-white text-[11px] font-mono transition-colors"
          >
            <ArrowLeft size={12} />
            <span>Landing</span>
          </Link>

          {/* User badge */}
          {user && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <div className="text-left hidden sm:block">
                <div className="text-xs font-semibold text-white truncate max-w-[120px]">
                  {displayName}
                </div>
                <div className="text-[10px] font-mono text-white/40 truncate max-w-[120px]">
                  {user.email}
                </div>
              </div>
            </div>
          )}

          {/* Sign Out Button */}
          <button
            onClick={handleSignOut}
            id="workspace-signout-btn"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 hover:text-red-200 border border-red-500/30 text-xs font-mono font-semibold transition-all shadow cursor-pointer"
          >
            <LogOut size={13} />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </div>

      {/* Mobile Nav Bar */}
      <div className="md:hidden flex items-center justify-around border-t border-white/5 px-2 py-1.5 bg-[#0a0010]">
        {navItems.map((item) => {
          const isActive =
            item.path === '/agent'
              ? location.pathname === '/agent' || location.pathname === '/agent/chat'
              : location.pathname === item.path

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-mono ${
                isActive
                  ? 'text-purple-300 font-bold bg-purple-500/15'
                  : 'text-white/50'
              }`}
            >
              {item.icon}
              <span>{item.label.split(' ')[0]}</span>
            </Link>
          )
        })}
      </div>
    </header>
  )
}
