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
        accent: "#d97757",
        "accent-blue": "#6a9bcc",
        "accent-green": "#788c5d",
        ink: "#141413",
        muted: "#666259",
        panel: "#e8e6dc",
        warning: "#d97757"
      }
    }
  },
  plugins: []
};

export default config;
