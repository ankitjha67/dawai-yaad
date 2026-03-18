/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#059669', dark: '#047857', light: '#10B981' },
      },
    },
  },
  plugins: [],
};
