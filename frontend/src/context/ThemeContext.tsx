import React, { createContext, useContext, useEffect, useState } from 'react'
import { flushSync } from 'react-dom'

type Theme = 'light' | 'dark'

interface ThemeContextType {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('aema_theme')
    if (saved === 'light' || saved === 'dark') return saved
    // Default to dark for technical developer console, or honor system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light'
    }
    return 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }
    localStorage.setItem('aema_theme', theme)
  }, [theme])

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light'
    const root = document.documentElement
    if (nextTheme === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }
    localStorage.setItem('aema_theme', nextTheme)

    // If the browser supports View Transitions API, execute a synchronized single-shot crossfade
    if (typeof document !== 'undefined' && 'startViewTransition' in document) {
      ;(document as any).startViewTransition(() => {
        flushSync(() => {
          setThemeState(nextTheme)
        })
      })
    } else {
      setThemeState(nextTheme)
    }
  }

  const setTheme = (t: Theme) => {
    const root = document.documentElement
    if (t === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }
    localStorage.setItem('aema_theme', t)

    if (typeof document !== 'undefined' && 'startViewTransition' in document) {
      ;(document as any).startViewTransition(() => {
        flushSync(() => {
          setThemeState(t)
        })
      })
    } else {
      setThemeState(t)
    }
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
