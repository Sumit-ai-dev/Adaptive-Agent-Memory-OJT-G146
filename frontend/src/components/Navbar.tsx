import { Link, useNavigate } from 'react-router-dom'
import { Github } from 'lucide-react'
import ThemeToggle from './ThemeToggle'
import { useAuth } from '../context/AuthContext'

interface NavbarProps {
  onOpenAuth: (mode: 'signin' | 'signup') => void
}

export default function Navbar({ onOpenAuth }: NavbarProps) {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 z-40 border-b backdrop-blur-md transition-colors
      bg-[#F8F8F6]/90 border-[#E5E5DF] text-[#1A1A1A]
      dark:bg-[#0D0F12]/90 dark:border-[#232832] dark:text-[#F4F4F6]"
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Left: Brand Identity with subtle version */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <span className="font-mono font-bold text-base tracking-tight text-indigo-600 dark:text-indigo-400">
              Æ
            </span>
            <span className="font-semibold text-sm tracking-tight text-[#1A1A1A] dark:text-[#F4F4F6]">
              AEMA
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border text-zinc-500 bg-zinc-100 border-zinc-200 dark:bg-zinc-800/60 dark:border-zinc-700/60 dark:text-zinc-400">
              v0.1.0
            </span>
          </Link>

          {/* Navigation Links (Horizontal, calm spacing) */}
          <nav className="hidden lg:flex items-center gap-6 text-xs text-zinc-600 dark:text-zinc-300">
            <a
              href="#why-aema"
              className="hover:text-[#1A1A1A] dark:hover:text-white transition-colors"
            >
              Solutions
            </a>
            <a
              href="#developers"
              className="hover:text-[#1A1A1A] dark:hover:text-white transition-colors"
            >
              Developers
            </a>
            <a
              href="#how-it-works"
              className="hover:text-[#1A1A1A] dark:hover:text-white transition-colors"
            >
              Architecture
            </a>
            <a
              href="#research"
              className="hover:text-[#1A1A1A] dark:hover:text-white transition-colors"
            >
              Research
            </a>
            <a
              href="https://github.com/Sumit-ai-dev/Adaptive-Agent-Memory-OJT-G146"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 hover:text-[#1A1A1A] dark:hover:text-white transition-colors"
            >
              <Github size={13} />
              <span>GitHub</span>
            </a>
          </nav>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-3">
          <ThemeToggle />

          {user ? (
            <Link
              to="/dashboard"
              className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500 transition-colors shadow-sm"
            >
              Open Workspace
            </Link>
          ) : (
            <>
              <button
                onClick={() => onOpenAuth('signin')}
                className="text-xs text-zinc-600 hover:text-[#1A1A1A] dark:text-zinc-300 dark:hover:text-white px-2 py-1.5 transition-colors cursor-pointer"
              >
                Log In
              </button>

              <button
                onClick={() => onOpenAuth('signup')}
                className="hidden sm:inline-block text-xs text-zinc-700 hover:text-[#1A1A1A] dark:text-zinc-200 dark:hover:text-white px-2.5 py-1.5 transition-colors cursor-pointer"
              >
                Sign Up
              </button>

              <button
                onClick={() => navigate('/dashboard?demo=true')}
                className="px-3.5 py-1.5 rounded-xl border text-xs font-medium transition-colors cursor-pointer
                  bg-white border-[#E5E5DF] text-[#1A1A1A] hover:bg-[#F1F1ED]
                  dark:bg-[#14171C] dark:border-[#232832] dark:text-[#F4F4F6] dark:hover:bg-[#1A1E24]"
              >
                Explore Demo
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
