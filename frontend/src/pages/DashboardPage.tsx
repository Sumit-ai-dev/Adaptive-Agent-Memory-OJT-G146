import { useNavigate, Link } from 'react-router-dom'
import {
  Brain,
  LogOut,
  ArrowLeft,
  Database,
  Sparkles,
  Shield,
  Zap,
  Activity,
  CheckCircle2,
  Clock,
  HardDrive
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function DashboardPage() {
  const { user, signOut, isConfigured } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/')
  }

  const displayName = user?.name || user?.email?.split('@')[0] || 'Agent Developer'
  const userEmail = user?.email || 'authenticated-user@supabase.co'

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
              Live Dashboard
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

            {/* User session status badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <div className="text-left hidden sm:block">
                <div className="text-xs font-semibold text-white truncate max-w-[150px]">
                  {displayName}
                </div>
                <div className="text-[10px] font-mono text-white/40 truncate max-w-[150px]">
                  {userEmail}
                </div>
              </div>
            </div>

            {/* Prominent Sign out button */}
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
        {/* Welcome Section */}
        <div className="p-8 rounded-3xl mb-8 relative overflow-hidden glass border border-white/10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-3 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-mono">
                <CheckCircle2 size={13} />
                <span>{isConfigured ? '🟢 Live Supabase Session Active' : '🟣 Dev Session Active'}</span>
              </div>
              <h1 className="text-3xl font-display font-extrabold text-white tracking-tight">
                Welcome back, <span className="text-transparent bg-clip-text anim-gradient-bg">{displayName}</span>
              </h1>
              <p className="text-white/60 text-sm font-sans mt-2 max-w-2xl">
                Your adaptive agent memory cluster is connected and ready. Telemetry, regression-backed trust calibration, and persistent reflections are indexed in real-time.
              </p>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <Link
                to="/"
                className="px-5 py-2.5 rounded-xl font-display font-bold text-xs text-white anim-gradient-bg shadow-lg hover:scale-105 transition-all"
              >
                Run Interactive Demo
              </Link>
            </div>
          </div>
        </div>

        {/* Telemetry Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Experiences</span>
              <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center">
                <Database size={16} />
              </div>
            </div>
            <div className="text-2xl font-display font-bold text-white">48 Total</div>
            <div className="text-emerald-400 text-xs font-mono mt-1 flex items-center gap-1">
              <Zap size={12} />
              <span>+12 saved this week</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Mean Trust Score</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center">
                <Shield size={16} />
              </div>
            </div>
            <div className="text-2xl font-display font-bold text-white">92.4%</div>
            <div className="text-emerald-400 text-xs font-mono mt-1 flex items-center gap-1">
              <Sparkles size={12} />
              <span>Calibrated via regression</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Retrieval Latency</span>
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-300 flex items-center justify-center">
                <Clock size={16} />
              </div>
            </div>
            <div className="text-2xl font-display font-bold text-white">18.2 ms</div>
            <div className="text-white/40 text-xs font-mono mt-1 flex items-center gap-1">
              <HardDrive size={12} />
              <span>Cosine similarity + metadata</span>
            </div>
          </div>

          <div className="p-5 rounded-2xl glass border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white/50 text-xs font-mono uppercase tracking-wider">Active Model</span>
              <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center">
                <Activity size={16} />
              </div>
            </div>
            <div className="text-2xl font-display font-bold text-white">Atomicwork</div>
            <div className="text-purple-300 text-xs font-mono mt-1 flex items-center gap-1">
              <span>96.2% Confidence (R²=0.88)</span>
            </div>
          </div>
        </div>

        {/* User Details & Identity Card */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 p-6 rounded-3xl glass border border-white/10">
            <h3 className="text-base font-display font-bold text-white mb-4 flex items-center gap-2">
              <Shield size={16} className="text-purple-400" />
              <span>Authenticated Identity</span>
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-white/40 text-[11px] font-mono uppercase block mb-1">Email</label>
                <div className="text-sm font-mono text-white/90 bg-white/5 p-2.5 rounded-xl border border-white/10 break-all">
                  {userEmail}
                </div>
              </div>

              <div>
                <label className="text-white/40 text-[11px] font-mono uppercase block mb-1">Provider</label>
                <div className="text-sm font-mono text-purple-300 bg-purple-500/10 p-2.5 rounded-xl border border-purple-500/20 flex items-center justify-between">
                  <span>Supabase OAuth</span>
                  <span className="text-emerald-400 text-xs font-bold">Verified</span>
                </div>
              </div>

              <div>
                <label className="text-white/40 text-[11px] font-mono uppercase block mb-1">User ID</label>
                <div className="text-xs font-mono text-white/60 bg-white/5 p-2.5 rounded-xl border border-white/10 break-all">
                  {user?.id || 'usr_83ce9b2a8e494b32'}
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleSignOut}
                  className="w-full py-2.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/30 text-xs font-mono font-bold transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <LogOut size={14} />
                  <span>Sign out now</span>
                </button>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 p-6 rounded-3xl glass border border-white/10">
            <h3 className="text-base font-display font-bold text-white mb-4 flex items-center gap-2">
              <Database size={16} className="text-emerald-400" />
              <span>Recent Memory Experiences</span>
            </h3>

            <div className="space-y-3">
              {[
                { title: 'Customer Support Escalation Handling', score: '96% Trust', tag: 'Voyager Skill', time: '12m ago' },
                { title: 'PostgreSQL Connection Pooling Optimization', score: '93% Trust', tag: 'Reflexion Loop', time: '1h ago' },
                { title: 'Vector Similarity Reranking Strategy', score: '91% Trust', tag: 'Atomicwork Regression', time: '3h ago' },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 transition-colors flex items-center justify-between"
                >
                  <div>
                    <h4 className="text-sm font-medium text-white">{item.title}</h4>
                    <div className="flex items-center gap-2 text-xs font-mono text-white/40 mt-1">
                      <span className="text-purple-300">{item.tag}</span>
                      <span>•</span>
                      <span>{item.time}</span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                    {item.score}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
