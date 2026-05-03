import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "Arial", "sans-serif"],
      },
      boxShadow: {
        panel: "0 18px 60px rgba(15, 23, 42, 0.08)",
      },
    },
  },
};

export default config;
