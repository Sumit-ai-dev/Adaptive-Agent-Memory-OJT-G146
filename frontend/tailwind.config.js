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
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        // Semantic Token Mapping
        canvas: {
          light: '#FBFBFA',
          dark: '#0C0E14',
        },
        surface: {
          light: '#FFFFFF',
          dark: '#131722',
        },
        subtle: {
          light: '#F4F4F0',
          dark: '#1A1F2C',
        },
        border: {
          light: '#E6E6E1',
          dark: '#252B3B',
        },
        ink: {
          light: '#18181B',
          dark: '#F4F4F6',
        },
        muted: {
          light: '#71717A',
          dark: '#94A3B8',
        },
        // Brand & Accents (Restrained Indigo)
        brand: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1',
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
        },
        // Semantic States (Emerald, Amber, Crimson)
        success: {
          DEFAULT: '#059669',
          dark: '#10B981',
          light: '#ECFDF5',
          border: '#A7F3D0',
        },
        warning: {
          DEFAULT: '#D97706',
          dark: '#F59E0B',
          light: '#FFFBEB',
          border: '#FDE68A',
        },
        danger: {
          DEFAULT: '#DC2626',
          dark: '#F43F5E',
          light: '#FEF2F2',
          border: '#FECACA',
        },
      },
    },
  },
  plugins: [],
}
