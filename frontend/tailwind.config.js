/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['Newsreader', 'Georgia', 'serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'monospace'],
      },
      colors: {
        // Spring Winter Editorial Theme
        canvas: {
          DEFAULT: '#FAFAF7',
          light: '#FAFAF7',
          dark: '#141412',
        },
        obsidian: {
          DEFAULT: '#141412',
          surface: '#161614',
          elevated: '#1E1E1B',
          border: '#242422',
          subtle: '#2A2A26',
          text: '#EDECE8',
          muted: '#7E7D77',
        },
        linen: {
          canvas: '#FAFAF7',
          surface: '#FFFFFF',
          subtle: '#F7F6F2',
          border: '#EAE8E3',
          ink: '#141413',
          muted: '#6B6A65',
        },
        brand: {
          50: '#FBF8F2',
          100: '#F5EFE1',
          200: '#EADEC3',
          500: '#141413',
          600: '#1F1F1D',
          700: '#141412',
        },
        accent: {
          amber: '#E67E22',
          emerald: '#4EAA79',
          crimson: '#D9534F',
        },
      },
    },
  },
  plugins: [],
}
