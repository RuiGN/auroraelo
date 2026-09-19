/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./**/*.{html,js,jsx,ts,tsx}",
    "./components/**/*.{html,js}",
    "./pages/**/*.{html,js}"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        aurora: {
          50: '#f0f7ff',
          100: '#e0f0fe',
          200: '#bae0fd',
          300: '#7cc7fb',
          400: '#38a9f8',
          500: '#0ea5e9',
          600: '#0284c7', // "Elo" primary cerulean
          700: '#0369a1',
          800: '#075985',
          900: '#0a2540', // "Aurora" primary midnight navy
          950: '#051424',
        },
        elo: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4', // Vibrant teal from ribbon
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
        },
        healing: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        alert: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        },
        crisis: {
          50: '#fff1f2',
          100: '#ffe4e6',
          500: '#f43f5e',
          600: '#e11d48',
          700: '#be123c',
        },
        zen: {
          50: '#f5f3ff',
          100: '#ede9fe',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
        display: ['Outfit', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'aurora-sm': '0 2px 8px -2px rgba(10, 37, 64, 0.08)',
        'aurora': '0 8px 24px -4px rgba(10, 37, 64, 0.12), 0 2px 6px -1px rgba(2, 132, 199, 0.06)',
        'aurora-lg': '0 16px 40px -8px rgba(10, 37, 64, 0.16), 0 4px 12px -2px rgba(2, 132, 199, 0.1)',
        'aurora-glow': '0 0 24px rgba(14, 165, 233, 0.3)',
        'crisis-glow': '0 0 24px rgba(244, 63, 94, 0.3)',
      },
      backgroundImage: {
        'aurora-gradient': 'linear-gradient(135deg, #0a2540 0%, #0369a1 50%, #06b6d4 100%)',
        'aurora-glow-gradient': 'linear-gradient(90deg, #0ea5e9, #06b6d4, #10b981)',
        'aurora-soft': 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f8fafc 100%)',
        'aurora-card-dark': 'linear-gradient(145deg, #07172c 0%, #0a2540 100%)',
      }
    },
  },
  plugins: [],
}
