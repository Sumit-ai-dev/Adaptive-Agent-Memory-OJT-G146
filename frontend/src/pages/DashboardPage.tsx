import { useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Brain,
  LogOut,
  ArrowLeft,
  Database,
  Shield,
  Activity,
  Clock,
  Inbox,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function DashboardPage() {
  const { user, signOut, loading } = useAuth()
  const navigate = useNavigate()

  // Route guard — redirect unauthenticated users before rendering anything
  useEffect(() => {
    if (!loading && !user) {
      navigate('/', { replace: true })
    }
  }, [user, loading, navigate])

  const handleSignOut = async () => {
    await signOut()
    navigate('/')
  }

  // Show spinner while auth session is being determined
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0010] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  // Guard: never render with null user (redirect is already fired via useEffect)
  if (!user) return null

  const displayName = user.name || user.email.split('@')[0]

  return (
    <div className="min-h-screen bg-[#0a0010] text-white selection:bg-purple-500/30">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/4 w-[600px] h-[600px] bg-purple-600/10 rounded-full blur-[120px]" />
        <div className="absolute top-1/3 right-10 w-[500px] h-[500px] bg-emerald-600/10 rounded-full blur-[140px]" />
      </div>

      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-white/10 backdrop-blur-xl bg-[#0a0010]/80">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center anim-gradient-bg shadow-lg group-hover:scale-105 transition-transform">
                <Brain size={18} className="text-white" />
              </div>
              <span className="text-white font-bold text-lg font-display tracking-tight">
                MemoryAgent
              </span>
            </Link>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider bg-purple-500/15 border border-purple-500/30 text-purple-300">
              Dashboard
            </span>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white text-xs font-mono transition-colors"
            >
              <ArrowLeft size={13} />
              <span>Back to Landing</span>
            </Link>

            {/* User session badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <div className="text-left hidden sm:block">
                <div className="text-xs font-semibold text-white truncate max-w-[150px]">
                  {displayName}
                </div>
                <div className="text-[10px] font-mono text-white/40 truncate max-w-[150px]">
                  {user.email}
                </div>
              </div>
            </div>

            <button
              onClick={handleSignOut}
              id="dashboard-signout-btn"
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 hover:text-red-200 border border-red-500/30 text-xs font-mono font-bold transition-all shadow-md hover:scale-105 active:scale-95 cursor-pointer"
            >
              <LogOut size={14} />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative max-w-7xl mx-auto px-6 py-10">

        {/* Welcome Section — compact, no colored block */}
        <div className="mb-10">
          <h1 className="text-2xl font-display font-bold text-white tracking-tight">
            Welcome back, <span className="text-purple-300">{displayName}</span>
          </h1>
          <p className="text-white/50 text-sm font-sans mt-1">
            Your agent workspace is ready. Backend and memory store are not yet connected.
          </p>
        </div>

        {/* Stat Cards — honest empty states */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Experiences</span>
              <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center">
                <Database size={16} />
              </div>
            </div>
            <div className="text-lg font-display font-bold text-white/40">No experiences yet</div>
            <div className="text-white/25 text-xs font-mono mt-1">Connect backend to populate</div>
          </div>

          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Mean Trust Score</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center">
                <Shield size={16} />
              </div>
            </div>
            <div className="text-lg font-display font-bold text-white/40">—</div>
            <div className="text-white/25 text-xs font-mono mt-1">No data yet</div>
          </div>

          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Retrieval Latency</span>
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-300 flex items-center justify-center">
                <Clock size={16} />
              </div>
            </div>
            <div className="text-lg font-display font-bold text-white/40">—</div>
            <div className="text-white/25 text-xs font-mono mt-1">No data yet</div>
          </div>

          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Active Model</span>
              <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center">
                <Activity size={16} />
              </div>
            </div>
            <div className="text-lg font-display font-bold text-white/40">Not configured</div>
            <div className="text-white/25 text-xs font-mono mt-1">Backend not yet connected</div>
          </div>
        </div>

        {/* Recent Experiences — full width, honest empty state */}
        <div className="p-6 rounded-3xl glass border border-white/10">
          <h3 className="text-base font-display font-bold text-white mb-4 flex items-center gap-2">
            <Database size={16} className="text-emerald-400" />
            <span>Recent Memory Experiences</span>
          </h3>

          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Inbox size={32} className="text-white/20 mb-3" />
            <p className="text-white/40 text-sm font-sans">No experiences recorded yet</p>
            <p className="text-white/25 text-xs font-mono mt-1">
              Experiences will appear here once the agent backend is connected.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
