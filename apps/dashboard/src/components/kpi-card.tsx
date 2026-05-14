import { brandTokens } from "@/lib/brand-tokens";

interface KPICardProps {
  value: string | number;
  label: string;
  sub?: string;
  accentColor?: string;
}

export function KPICard({
  value,
  label,
  sub,
  accentColor = brandTokens.colors.gold,
}: KPICardProps) {
  return (
    <div
      style={{
        ...brandTokens.card,
        display: "flex",
        gap: 16,
        alignItems: "stretch",
      }}
    >
      <div
        style={{
          width: 3,
          borderRadius: 2,
          backgroundColor: accentColor,
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 32,
            fontWeight: 300,
            color: brandTokens.colors.dark,
            lineHeight: 1,
            marginBottom: 6,
          }}
        >
          {value}
        </div>
        <div
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: "3px",
            textTransform: "uppercase" as const,
            color: brandTokens.colors.mid,
            marginBottom: sub ? 4 : 0,
          }}
        >
          {label}
        </div>
        {sub && (
          <div
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 11,
              color: brandTokens.colors.mid,
            }}
          >
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}
