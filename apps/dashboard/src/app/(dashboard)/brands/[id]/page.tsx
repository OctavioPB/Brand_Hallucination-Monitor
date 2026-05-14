import { brandTokens } from "@/lib/brand-tokens";
import { Eyebrow } from "@/components/eyebrow";

const TABS = ["Overview", "Vector Map", "Hallucinations", "Competitors"];

interface BrandPageProps {
  params: { id: string };
}

export default function BrandPage({ params }: BrandPageProps) {
  return (
    <div style={{ maxWidth: 1300, margin: "0 auto", padding: "56px 48px" }}>
      {/* Page header — dark impact banner */}
      <div
        style={{
          ...brandTokens.heroSection,
          borderRadius: 14,
          padding: "48px",
          marginBottom: 32,
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
            marginBottom: 12,
          }}
        >
          Brand Detail
        </p>
        <h1
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 32,
            fontWeight: 400,
            color: "#ffffff",
            lineHeight: 1.25,
            marginBottom: 8,
          }}
        >
          Brand{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>
            {params.id}
          </em>
        </h1>

        {/* Tab switcher */}
        <div
          style={{
            display: "flex",
            gap: 4,
            borderBottom: "1px solid rgba(255,255,255,0.1)",
            marginTop: 32,
          }}
        >
          {TABS.map((tab, i) => (
            <button
              key={tab}
              style={{
                background: "none",
                border: "none",
                borderBottom: i === 0 ? `2px solid ${brandTokens.colors.goldLight}` : "2px solid transparent",
                cursor: "pointer",
                padding: "10px 20px",
                marginBottom: -1,
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 11,
                fontWeight: 500,
                letterSpacing: "1.5px",
                textTransform: "uppercase",
                color: i === 0 ? brandTokens.colors.goldLight : "rgba(255,255,255,0.4)",
                transition: "color 0.15s",
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 24,
          marginBottom: 40,
        }}
      >
        {[
          { value: "—", label: "SPS Score", sub: "Avg across intent clusters" },
          { value: "—", label: "Hallucinations", sub: "Last 30 days" },
          { value: "—", label: "Last Scan", sub: "Never" },
        ].map(({ value, label, sub }) => (
          <div
            key={label}
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
                backgroundColor: brandTokens.colors.gold,
                flexShrink: 0,
              }}
            />
            <div>
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
              <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 11, color: brandTokens.colors.mid }}>
                {sub}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div style={{ height: 1, backgroundColor: brandTokens.colors.primary10, marginBottom: 40 }} />

      {/* SPS trend placeholder */}
      <div style={{ marginBottom: 40 }}>
        <Eyebrow>SPS trend</Eyebrow>
        <h2
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 22,
            fontWeight: 300,
            color: brandTokens.colors.dark,
            marginBottom: 8,
          }}
        >
          Semantic proximity{" "}
          <em style={{ fontStyle: "italic" }}>over time</em>
        </h2>
        <div
          style={{
            ...brandTokens.card,
            minHeight: 280,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.mid,
            }}
          >
            Run a scan to populate SPS history. (Sprint 3)
          </p>
        </div>
      </div>

      {/* Hallucination feed placeholder */}
      <div>
        <Eyebrow>Hallucination feed</Eyebrow>
        <h2
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 22,
            fontWeight: 300,
            color: brandTokens.colors.dark,
            marginBottom: 8,
          }}
        >
          Detected{" "}
          <em style={{ fontStyle: "italic" }}>hallucinations</em>
        </h2>
        <div
          style={{
            ...brandTokens.card,
            minHeight: 200,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.mid,
            }}
          >
            No hallucinations detected yet. (Sprint 5)
          </p>
        </div>
      </div>
    </div>
  );
}
