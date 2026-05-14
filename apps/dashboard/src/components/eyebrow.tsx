import { brandTokens } from "@/lib/brand-tokens";

interface EyebrowProps {
  children: React.ReactNode;
  light?: boolean;
}

export function Eyebrow({ children, light = false }: EyebrowProps) {
  const color = light ? brandTokens.colors.goldLight : brandTokens.colors.gold;
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        fontSize: 9,
        fontFamily: brandTokens.typography.fontBody,
        fontWeight: 500,
        letterSpacing: "4px",
        textTransform: "uppercase",
        color,
        marginBottom: 10,
      }}
    >
      <div
        style={{
          width: 24,
          height: 1,
          flexShrink: 0,
          backgroundColor: color,
        }}
      />
      {children}
    </div>
  );
}
