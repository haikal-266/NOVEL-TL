/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"Space Mono"', 'monospace'],
      },
      colors: {
        'neo-dark': '#55423C',
        'neo-peach': '#FFC0AD',
        'neo-peach-light': '#FFD7CB',
        'neo-pink': '#E78FB3',
        'neo-lime': '#D7FF28',
        'neo-canvas': '#FBFAF6',
      },
      boxShadow: {
        'neo-xs': '2px 2px 0px #000000',
        'neo-sm': '3px 3px 0px #000000',
        'neo': '4px 4px 0px #000000',
        'neo-md': '5px 5px 0px #000000',
        'neo-lg': '6px 6px 0px #000000',
      }
    },
  },
  plugins: [],
}
