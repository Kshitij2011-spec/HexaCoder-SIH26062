/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        // Polar slate canvas (dark background)
        slate: {
          950: '#0b1120',
          900: '#0f172a',
          850: '#131c2e',
          800: '#1e293b',
        },
      },
    },
  },
  plugins: [],
};
