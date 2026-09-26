/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        card: 'var(--card)',
        'card-foreground': 'var(--card-foreground)',
        popover: 'var(--popover)',
        'popover-foreground': 'var(--popover-foreground)',
        primary: 'var(--primary)',
        'primary-foreground': 'var(--primary-foreground)',
        secondary: 'var(--secondary)',
        'secondary-foreground': 'var(--secondary-foreground)',
        muted: 'var(--muted)',
        'muted-foreground': 'var(--muted-foreground)',
        accent: 'var(--accent)',
        'accent-foreground': 'var(--accent-foreground)',
        destructive: 'var(--destructive)',
        'destructive-foreground': 'var(--destructive-foreground)',
        border: 'var(--border)',
        input: 'var(--input)',
        ring: 'var(--ring)',
        'rs-navy-900': '#081229',
        'rs-navy-800': '#0d1c40',
        'rs-navy': '#12275c',
        'rs-blue-700': '#1b48c9',
        'rs-blue': '#1e5eff',
        'rs-blue-500': '#2d7bff',
        'rs-blue-bright': '#3a86ff',
        'rs-sky': '#eaf1ff',
        'rs-sky-2': '#f5f8ff',
        'rs-ink': '#0b1733',
        'rs-body': '#475573',
        'rs-muted': '#7180a0',
        'rs-line': '#e7ecf7',
        'rs-line-2': '#eef2fb',
      },
      backgroundImage: {
        'dot-grid':
          'radial-gradient(circle at 1px 1px, rgb(148 163 184 / 0.11) 1px, transparent 0)',
        'rs-grad': 'linear-gradient(135deg,#0a1733 0%,#1e5eff 58%,#3a86ff 100%)',
        'rs-grad-cta': 'linear-gradient(135deg,#1e5eff 0%,#2d7bff 100%)',
        'rs-grad-soft': 'linear-gradient(135deg,#eef4ff 0%,#f7faff 100%)',
      },
      boxShadow: {
        'rs-sm': '0 2px 8px rgba(17,39,92,.06)',
        rs: '0 18px 40px -18px rgba(20,53,140,.28)',
        'rs-lg': '0 40px 80px -28px rgba(15,40,110,.34)',
      },
      borderRadius: {
        'rs-sm': '14px',
        rs: '20px',
        'rs-lg': '28px',
        'rs-xl': '36px',
      },
      maxWidth: {
        wrap: '1200px',
      },
      transitionTimingFunction: {
        rs: 'cubic-bezier(.22,.61,.36,1)',
      },
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans Variable"',
          '"Plus Jakarta Sans"',
          'system-ui',
          'sans-serif',
        ],
      },
      screens: {
        nav: '1120px',
      },
    },
  },
  plugins: [],
}
