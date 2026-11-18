import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

interface ThemeToggleProps {
  className?: string
}

export default function ThemeToggle({ className = '' }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      className={`p-1.5 rounded-lg border text-xs transition-colors cursor-pointer ${
        theme === 'light'
          ? 'bg-white border-[#E6E6E1] text-[#52525B] hover:text-[#18181B] hover:bg-[#F4F4F0]'
          : 'bg-[#1E1E1B] border-[#2E2E2A] text-[#9E9D96] hover:text-[#EDECE8] hover:bg-[#252522]'
      } ${className}`}
      title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} theme`}
    >
      {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
    </button>
  )
}
