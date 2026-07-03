import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#2563eb", dark: "#1d4ed8" },
        surface: { light: "#f8fafc", dark: "#0f172a" },
        panel: { light: "#ffffff", dark: "#1e293b" },
        border: { light: "#e2e8f0", dark: "#334155" },
      },
    },
  },
  plugins: [],
};
export default config;
