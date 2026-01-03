/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['\"Geist Sans\"', 'ui-sans-serif', 'system-ui', 'sans-serif', '\"Apple Color Emoji\"', '\"Segoe UI Emoji\"', '\"Segoe UI Symbol\"', '\"Noto Color Emoji\"'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
