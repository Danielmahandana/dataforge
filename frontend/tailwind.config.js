/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkroom: {
          bg: "#09090b",
          surface: "#121215",
          card: "#18181b",
          border: "#27272a",
          borderLight: "#3f3f46",
          navy: "#182232",
          navyLight: "#233348",
          gold: "#e2b714",
          goldHover: "#f5cc24",
          goldLight: "rgba(226, 183, 20, 0.12)",
          emerald: "#10a37f",
          emeraldHover: "#12b88f",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
          text: "#f4f4f5",
          muted: "#a1a1aa",
        }
      },
      fontFamily: {
        sans: ["Open Sans", "Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      }
    },
  },
  plugins: [],
}
