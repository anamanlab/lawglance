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
        accent: "#c06a4d",
        "accent-blue": "#5f84ab",
        "accent-green": "#6f8459",
        ink: "#1c1a17",
        muted: "#4f4a42",
        panel: "#dfdbcf",
        warning: "#7f4f3b"
      }
    }
  },
  plugins: []
};

export default config;
