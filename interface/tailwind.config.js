/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        caract: {
          light: '#fef2f2',
          border: '#ef4444',
          text: '#dc2626',
        },
        lieux: {
          light: '#fffbeb',
          border: '#f59e0b',
          text: '#d97706',
        },
        vehicules: {
          light: '#eff6ff',
          border: '#3b82f6',
          text: '#2563eb',
        },
        usagers: {
          light: '#ecfdf5',
          border: '#10b981',
          text: '#059669',
        }
      }
    },
  },
  plugins: [],
}
