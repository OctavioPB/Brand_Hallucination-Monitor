import type { Config } from "tailwindcss";
import { brandTokens } from "./src/lib/brand-tokens";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: brandTokens.colors.primary,
          80: brandTokens.colors.primary80,
          60: brandTokens.colors.primary60,
          30: brandTokens.colors.primary30,
          10: brandTokens.colors.primary10,
        },
        gold: {
          DEFAULT: brandTokens.colors.gold,
          light: brandTokens.colors.goldLight,
        },
        dark: brandTokens.colors.dark,
        mid: brandTokens.colors.mid,
        light: brandTokens.colors.light,
        // Status / semantic
        success: {
          DEFAULT: "#27B97C",
          bg: "#E0F7EF",
          text: "#0D5C3A",
        },
        danger: {
          DEFAULT: "#E03448",
          bg: "#FDEAEA",
          text: "#7A1020",
        },
        warning: {
          DEFAULT: "#F07020",
          bg: "#FEF0E6",
          text: "#7A3800",
        },
        strategic: {
          DEFAULT: "#7C4DBD",
          bg: "#F0EBF9",
          text: "#3D1F70",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Plus Jakarta Sans", "sans-serif"],
        mono: ["Courier New", "monospace"],
      },
      fontSize: {
        label: ["10px", { letterSpacing: "3px" }],
        caption: ["12px", { lineHeight: "1.5" }],
        body: ["15px", { lineHeight: "1.7" }],
        h3: ["16px", { fontWeight: "600" }],
        h2: ["22px", { fontWeight: "300" }],
        h1: ["32px", { fontWeight: "400" }],
        hero: ["48px", { fontWeight: "300" }],
      },
      borderRadius: {
        card: "12px",
        pill: "20px",
      },
      boxShadow: {
        card: "0 1px 4px rgba(0, 51, 102, 0.08)",
        "card-md": "0 1px 6px rgba(0, 51, 102, 0.09)",
      },
      maxWidth: {
        content: "1200px",
        dashboard: "1300px",
      },
      // Data viz series (order matches BRAND.md)
      // Usage: brandColors[0] = first series, etc.
    },
  },
  plugins: [],
};

export default config;
