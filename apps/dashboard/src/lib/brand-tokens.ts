/**
 * Design tokens derived from BRAND.md.
 * Import these everywhere — never hardcode hex values directly.
 */

export const brandTokens = {
  colors: {
    // Primary blue scale
    primary: "#003366",
    primary80: "#1A4D80",
    primary60: "#336699",
    primary30: "#99BBDD",
    primary10: "#E0EAF4",

    // Gold accent
    gold: "#C8982A",
    goldLight: "#E8C46A",

    // Neutrals
    dark: "#1C1C2E",
    mid: "#6B7280",
    light: "#F4F6F9",
    white: "#FFFFFF",
  },

  // Data visualization series — use in order for multi-series charts
  dataSeries: [
    "#003366", // corporate blue
    "#27B97C", // green
    "#7C4DBD", // purple
    "#F07020", // orange
    "#E05080", // pink
  ],

  // Status / severity semantic colors
  status: {
    success: { base: "#27B97C", bg: "#E0F7EF", text: "#0D5C3A" },
    danger:  { base: "#E03448", bg: "#FDEAEA", text: "#7A1020" },
    warning: { base: "#F07020", bg: "#FEF0E6", text: "#7A3800" },
    strategic: { base: "#7C4DBD", bg: "#F0EBF9", text: "#3D1F70" },
    primary: { base: "#003366", bg: "#E0EAF4", text: "#001F4D" },
  },

  typography: {
    fontDisplay: "'Fraunces', Georgia, serif",
    fontBody: "'Plus Jakarta Sans', sans-serif",
    fontMono: "'Courier New', monospace",
  },

  // Pre-built inline style blocks matching BRAND.md specs
  // Use for components that must NOT use Tailwind (nav, monogram, etc.)
  navBar: {
    background: "rgba(0, 51, 102, 0.97)",
    backdropFilter: "blur(12px)",
    height: 52,
    borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
    padding: "0 40px",
  },

  navLink: {
    background: "none",
    border: "none",
    color: "rgba(255, 255, 255, 0.45)",
    cursor: "pointer",
    fontFamily: "'Plus Jakarta Sans', sans-serif",
    fontSize: "9px",
    letterSpacing: "2px",
    textTransform: "uppercase" as const,
    padding: "5px 8px",
    borderRadius: "6px",
    transition: "color 0.15s",
  },

  navLinkActive: {
    color: "#E8C46A",
    backgroundColor: "rgba(201, 168, 76, 0.12)",
  },

  logoutBtn: {
    background: "none",
    border: "1px solid rgba(255, 255, 255, 0.2)",
    borderRadius: "6px",
    color: "rgba(255, 255, 255, 0.5)",
    cursor: "pointer",
    fontFamily: "'Plus Jakarta Sans', sans-serif",
    fontSize: "9px",
    letterSpacing: "2px",
    textTransform: "uppercase" as const,
    padding: "5px 10px",
  },

  footer: {
    backgroundColor: "#003366",
    padding: "20px 48px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontFamily: "'Plus Jakarta Sans', sans-serif",
    fontSize: "9px",
    letterSpacing: "3px",
    textTransform: "uppercase" as const,
    color: "rgba(255, 255, 255, 0.4)",
  },

  heroSection: {
    backgroundColor: "#003366",
    backgroundImage: `
      linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px)
    `,
    backgroundSize: "48px 48px",
  },

  card: {
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    boxShadow: "0 1px 4px rgba(0, 51, 102, 0.08)",
    padding: "28px",
  },
} as const;

// CSS custom properties string — inject in globals.css :root block
export const cssVariables = `
  --primary:    ${brandTokens.colors.primary};
  --primary-80: ${brandTokens.colors.primary80};
  --primary-60: ${brandTokens.colors.primary60};
  --primary-30: ${brandTokens.colors.primary30};
  --primary-10: ${brandTokens.colors.primary10};
  --gold:       ${brandTokens.colors.gold};
  --gold-light: ${brandTokens.colors.goldLight};
  --dark:       ${brandTokens.colors.dark};
  --mid:        ${brandTokens.colors.mid};
  --light:      ${brandTokens.colors.light};
  --white:      ${brandTokens.colors.white};
  --fd: ${brandTokens.typography.fontDisplay};
  --fb: ${brandTokens.typography.fontBody};
`;
