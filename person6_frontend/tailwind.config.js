/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#060D1B", 900: "#0A1428", 800: "#0E1B34", 700: "#142443", 600: "#1C3156", 500: "#2A4270", 400: "#5F7196", 300: "#8C9BB8", 200: "#B9C4DA", 100: "#E4EAF5" },
        mint: { DEFAULT: "#2DDBA0", deep: "#19B884" },
      },
      fontFamily: { sans: ["Manrope", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
    },
  },
  plugins: [],
};
