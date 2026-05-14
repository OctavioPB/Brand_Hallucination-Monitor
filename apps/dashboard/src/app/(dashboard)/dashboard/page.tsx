import { brandTokens } from "@/lib/brand-tokens";
import { Eyebrow } from "@/components/eyebrow";

const KPI_CARDS = [
  { value: "—", label: "Brands Monitored", sub: "Set up a brand to begin" },
  { value: "—", label: "Avg SPS Score", sub: "Semantic proximity index" },
  { value: "—", label: "Hallucinations (7d)", sub: "Across all probed models" },
  { value: "—", label: "Active Alerts", sub: "Unacknowledged" },
];

export default function DashboardPage() {
  return (
    <div style={{ maxWidth: 1300, margin: "0 auto", padding: "56px 48px" }}>
      {/* Hero banner */}
      <div
        style={{
          ...brandTokens.heroSection,
          borderRadius: 14,
          padding: "56px 48px",
          marginBottom: 48,
        }}
      >
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "4px",
            textTransform: "uppercase",
            color: "rgba(255,255,255,0.35)",
            marginBottom: 16,
          }}
        >
          Brand Safety Dashboard
        </p>
        <h1
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 36,
            fontWeight: 300,
            color: "#ffffff",
            maxWidth: 640,
            lineHeight: 1.3,
            marginBottom: 12,
          }}
        >
          Where does your brand{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>
            live
          </em>{" "}
          in AI?
        </h1>
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 14,
            color: "rgba(255,255,255,0.6)",
            lineHeight: 1.75,
            maxWidth: 540,
          }}
        >
          Monitor semantic proximity scores, detect hallucinations, and benchmark your
          brand against competitors across every major AI model.
        </p>
      </div>

      {/* KPI summary row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 24,
          marginBottom: 48,
        }}
      >
        {KPI_CARDS.map(({ value, label, sub }) => (
          <div
            key={label}
            style={{
              ...brandTokens.card,
              display: "flex",
              gap: 16,
              alignItems: "stretch",
            }}
          >
            {/* Left accent bar */}
            <div
              style={{
                width: 3,
                borderRadius: 2,
                backgroundColor: brandTokens.colors.gold,
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
                  textTransform: "uppercase",
                  color: brandTokens.colors.mid,
                  marginBottom: 4,
                }}
              >
                {label}
              </div>
              <div
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 11,
                  color: brandTokens.colors.mid,
                }}
              >
                {sub}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Main sections placeholder */}
      <div style={{ height: 1, backgroundColor: brandTokens.colors.primary10, marginBottom: 48 }} />

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24 }}>
        {/* Vector map placeholder */}
        <div style={{ ...brandTokens.card, minHeight: 320 }}>
          <Eyebrow>Vector map</Eyebrow>
          <h2
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 22,
              fontWeight: 300,
              color: brandTokens.colors.dark,
              marginBottom: 8,
            }}
          >
            Semantic{" "}
            <em style={{ fontStyle: "italic" }}>position</em>
          </h2>
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.mid,
              lineHeight: 1.7,
            }}
          >
            Add a brand and run a scan to see your position in the AI vector space.
          </p>
        </div>

        {/* Alert feed placeholder */}
        <div style={{ ...brandTokens.card, minHeight: 320 }}>
          <Eyebrow>Alert registry</Eyebrow>
          <h2
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 22,
              fontWeight: 300,
              color: brandTokens.colors.dark,
              marginBottom: 8,
            }}
          >
            Recent{" "}
            <em style={{ fontStyle: "italic" }}>alerts</em>
          </h2>
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.mid,
              lineHeight: 1.7,
            }}
          >
            No alerts yet. Hallucination alerts will appear here after the first scan.
          </p>
        </div>
      </div>
    </div>
  );
}
