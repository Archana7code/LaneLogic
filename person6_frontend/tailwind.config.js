/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
    "../person5_gis/**/*.jsx",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B1220",
          900: "#101A2E",
          800: "#182742",
          700: "#22314F",
          600: "#3A4A6B",
        },
        signal: {
          amber: "#F5A623",
          green: "#22C55E",
          yellow: "#EAB308",
          orange: "#F97316",
          red: "#EF4444",
          maroon: "#991B1B",
        },
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(11, 18, 32, 0.06)",
      },
    },
  },
  plugins: [],
};
