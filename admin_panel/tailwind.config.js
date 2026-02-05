/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          yellow: '#FFD700',
          blue: '#1E40AF',
          lightBlue: '#3B82F6',
          lightYellow: '#FEF3C7',
          darkBlue: '#1E3A8A',
          darkYellow: '#F59E0B'
        }
      }
    },
  },
  plugins: [],
}

