import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
      extend: {
        colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: "var(--surface)",
        "surface-muted": "var(--surface-muted)",
        "surface-elevated": "var(--surface-elevated)",
        border: "var(--border)",
        "text-muted": "var(--text-muted)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Arial", "sans-serif"],
      },
      borderRadius: {
        cockpit: "18px",
      },
      keyframes: {
        "motion-fade-up": {
          "0%": { opacity: "0", transform: "translate3d(0, var(--motion-distance, 16px), 0)" },
          "100%": { opacity: "1", transform: "translate3d(0, 0, 0)" },
        },
        "motion-fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "motion-scale-subtle": {
          "0%": { opacity: "0", transform: "scale(0.985)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "motion-shimmer": {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        "motion-pulse-dot": {
          "0%, 100%": { opacity: "0.45" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "motion-fade-up":
          "motion-fade-up var(--motion-duration, 560ms) cubic-bezier(0.16, 1, 0.35, 1)",
        "motion-fade-in":
          "motion-fade-in var(--motion-duration, 560ms) cubic-bezier(0.16, 1, 0.35, 1)",
        "motion-scale-subtle":
          "motion-scale-subtle var(--motion-duration, 560ms) cubic-bezier(0.16, 1, 0.35, 1)",
        "motion-shimmer": "motion-shimmer 1.2s linear infinite",
        "motion-pulse-dot": "motion-pulse-dot 1.2s ease-in-out infinite",
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        soft: "var(--shadow-soft)",
        glow: "var(--shadow-glow)",
      },
    },
  },
};

export default config;
