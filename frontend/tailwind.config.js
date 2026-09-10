/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: '#0891B2',
        'primary-light': '#22D3EE',
        'primary-dark': '#164E63',
        accent: '#22C55E',
        surface: '#ECFEFF',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
