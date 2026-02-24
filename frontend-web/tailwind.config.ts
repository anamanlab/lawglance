import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        accent: "#0284c7",
        ink: "#0f172a",
        muted: "#475569",
        panel: "#f8fafc",
        warning: "#a16207"
      }
    }
  },
  plugins: []
};

export default config;
