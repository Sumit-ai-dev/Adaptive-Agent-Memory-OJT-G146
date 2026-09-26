/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        display: ['Geist', 'Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'monospace'],
      },
      colors: {
        primary: '#6B4894',
        'primary-light': '#862FE7',
        'primary-dark': '#49266E',
        accent: '#7042DD',
        surface: '#0d0718',
        atomic: {
          dark: '#0c0714',
          surface: '#150d24',
          card: '#1b122c',
          purple: '#6B4894',
          accent: '#7042DD',
          violet: '#862FE7',
          glow: '#953BFF',
          muted: '#717171',
          subtle: '#D0D5DD',
          light: '#F1F1F1',
          border: 'rgba(255, 255, 255, 0.08)',
          'border-hover': 'rgba(134, 47, 231, 0.35)',
        },
      },
      transitionTimingFunction: {
        atomic: 'cubic-bezier(0.2, 0, 0, 1)',
        'atomic-slow': 'cubic-bezier(0.445, 0.05, 0.55, 0.95)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
