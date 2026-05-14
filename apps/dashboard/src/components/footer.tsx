import { brandTokens } from "@/lib/brand-tokens";

export function Footer() {
  const dateLabel = new Date()
    .toLocaleDateString("en-US", { year: "numeric", month: "long" })
    .toUpperCase();

  return (
    <footer style={brandTokens.footer as React.CSSProperties}>
      <span>OPB · Octavio Pérez Bravo · hallucin8</span>
      <span>{dateLabel}</span>
    </footer>
  );
}
