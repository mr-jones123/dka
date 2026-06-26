import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Quiapo", "system-ui", "sans-serif"],
        placard: ["Cubao", "ui-monospace", "monospace"],
      },
      colors: {
        parchment: "#efe6d2",
        bone: "#f5ebd9",
        gold: "#e8b840",
        oxblood: "#5a1e13",
        carbon: "#2b160e",
        ink: "#1a0d08",
      },
    },
  },
  plugins: [],
} satisfies Config;
