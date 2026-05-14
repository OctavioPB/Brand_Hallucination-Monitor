import { brandTokens } from "@/lib/brand-tokens";

type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

const SEVERITY_MAP: Record<
  Severity,
  { dot: string; bg: string; text: string; label: string }
> = {
  LOW:      { dot: brandTokens.status.primary.base,   bg: brandTokens.status.primary.bg,   text: brandTokens.status.primary.text,   label: "Low" },
  MEDIUM:   { dot: brandTokens.status.warning.base,   bg: brandTokens.status.warning.bg,   text: brandTokens.status.warning.text,   label: "Medium" },
  HIGH:     { dot: brandTokens.status.danger.base,    bg: brandTokens.status.danger.bg,    text: brandTokens.status.danger.text,    label: "High" },
  CRITICAL: { dot: brandTokens.status.strategic.base, bg: brandTokens.status.strategic.bg, text: brandTokens.status.strategic.text, label: "Critical" },
};

interface SeverityBadgeProps {
  severity: Severity | string;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const cfg = SEVERITY_MAP[(severity as Severity)] ?? SEVERITY_MAP.LOW;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        borderRadius: 20,
        padding: "4px 12px",
        backgroundColor: cfg.bg,
        color: cfg.text,
        fontFamily: brandTokens.typography.fontBody,
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: "0.5px",
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          backgroundColor: cfg.dot,
          flexShrink: 0,
        }}
      />
      {cfg.label}
    </span>
  );
}
