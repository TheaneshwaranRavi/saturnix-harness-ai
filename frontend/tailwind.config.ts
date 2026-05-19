import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        saturnix: {
          bg: "#070A12",
          panel: "#0D1324",
          line: "#1F2A44",
          cyan: "#29D3FF",
          green: "#42F59E",
          amber: "#F6C85F",
          red: "#FF5D73"
        }
      },
      boxShadow: {
        glow: "0 0 28px rgba(41, 211, 255, 0.18)"
      }
    }
  },
  plugins: []
};

export default config;
