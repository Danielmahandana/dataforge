/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        openai: {
          bg: "#0d0d0e",
          sidebar: "#171717",
          panel: "#171717",
          surface: "#212121",
          border: "rgba(255, 255, 255, 0.08)",
          emerald: "#10a37f",
          emeraldHover: "#0e8e6e",
          text: "#ececec",
          secondary: "#b4b4b4",
          muted: "#707070",
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
