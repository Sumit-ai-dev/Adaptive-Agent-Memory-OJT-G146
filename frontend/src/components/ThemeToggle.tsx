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
      className={`p-2 rounded-lg border text-sm transition-colors cursor-pointer ${
        theme === 'light'
          ? 'bg-white border-[#E6E6E1] text-[#52525B] hover:text-[#18181B] hover:bg-[#F4F4F0]'
          : 'bg-[#131722] border-[#252B3B] text-[#94A3B8] hover:text-[#F4F4F6] hover:bg-[#1A1F2C]'
      } ${className}`}
      title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} theme`}
    >
      {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
    </button>
  )
}
