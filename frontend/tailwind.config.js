/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      backgroundImage: {
        'dot-grid':
          'radial-gradient(circle at 1px 1px, rgb(148 163 184 / 0.13) 1px, transparent 0)',
      },
    },
  },
  plugins: [],
}
