/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sap: {
          50: '#f0f5fa',
          100: '#e1ebf5',
          200: '#c3d7eb',
          300: '#94bce0',
          400: '#5e9bd1',
          500: '#387ec1',
          600: '#0a6ed1', // Iconic SAP Gold/Blue accent
          700: '#0854a0',
          800: '#074886',
          900: '#083c6e',
          950: '#052749',
        },
        slate: {
          850: '#151d2e',
          900: '#0f172a',
          950: '#090d16',
        }
      }
    },
  },
  plugins: [],
}
