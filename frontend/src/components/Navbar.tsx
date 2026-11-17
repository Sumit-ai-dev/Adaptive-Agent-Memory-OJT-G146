import { Link, useNavigate } from 'react-router-dom'
import { Github, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

interface NavbarProps {
  onOpenAuth: (mode: 'signin' | 'signup') => void
}

export default function Navbar({ onOpenAuth }: NavbarProps) {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-40 w-full border-b border-black/[0.05] bg-white/40 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-16 h-14 flex items-center justify-between">
        {/* Left: Brand Wordmark */}
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 group">
            <span className="font-mono font-bold text-sm tracking-tight text-[#141413]">
              AEMA
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden sm:flex items-center gap-6 text-xs text-[#6B6A65]">
            <Link
              to="/docs"
              className="hover:text-[#141413] transition-colors"
            >
              Documentation
            </Link>
            <Link
              to="/dashboard?demo=true&tab=research"
              className="hover:text-[#141413] transition-colors"
            >
              Research
            </Link>
            <Link
              to="/docs#benchmarks"
              className="hover:text-[#141413] transition-colors"
            >
              Benchmarks
            </Link>
            <a
              href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 hover:text-[#141413] transition-colors"
            >
              <Github size={13} />
              <span>GitHub</span>
            </a>
          </nav>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-4">
          {user ? (
            <Link
              to="/dashboard?tab=overview"
              className="px-3.5 py-1.5 rounded text-xs font-medium text-[#FAFAF7] bg-[#141413] hover:bg-[#2B2B28] transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <span>Open Studio</span>
              <ArrowRight size={13} />
            </Link>
          ) : (
            <>
              <button
                onClick={() => onOpenAuth('signin')}
                className="text-xs text-[#6B6A65] hover:text-[#141413] transition-colors cursor-pointer"
              >
                Sign In
              </button>

              <button
                onClick={() => navigate('/dashboard?demo=true&tab=overview')}
                className="px-3.5 py-1.5 rounded text-xs font-medium text-[#FAFAF7] bg-[#141413] hover:bg-[#2B2B28] transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                <span>Launch Studio</span>
                <ArrowRight size={13} />
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
