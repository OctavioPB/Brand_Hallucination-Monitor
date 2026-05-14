import { brandTokens } from "@/lib/brand-tokens";
import { Footer } from "@/components/footer";

export default function LoginPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: brandTokens.colors.light,
      }}
    >
      {/* Hero / cover — dark navy + grid texture */}
      <div
        style={{
          ...brandTokens.heroSection,
          padding: "96px 48px 64px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
        }}
      >
        {/* OPB Monogram */}
        <div style={{ marginBottom: 32 }}>
          <span
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 32,
              fontWeight: 300,
              color: "#ffffff",
            }}
          >
            O
          </span>
          <em
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 32,
              fontWeight: 300,
              fontStyle: "italic",
              color: brandTokens.colors.goldLight,
            }}
          >
            PB
          </em>
        </div>

        <h1
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 48,
            fontWeight: 300,
            color: "#ffffff",
            maxWidth: 560,
            lineHeight: 1.25,
            marginBottom: 16,
          }}
        >
          Brand safety in{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>
            every model.
          </em>
        </h1>

        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 14,
            color: "rgba(255,255,255,0.6)",
            lineHeight: 1.75,
            maxWidth: 480,
          }}
        >
          Monitor how AI models perceive your brand. Detect hallucinations before they spread.
        </p>
      </div>

      {/* Login card */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "64px 24px",
        }}
      >
        <div
          style={{
            ...brandTokens.card,
            width: "100%",
            maxWidth: 420,
            borderTop: `3px solid ${brandTokens.colors.gold}`,
          }}
        >
          {/* Eyebrow */}
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
              color: brandTokens.colors.gold,
              marginBottom: 20,
            }}
          >
            <div
              style={{ width: 24, height: 1, backgroundColor: brandTokens.colors.gold }}
            />
            Sign in
          </div>

          <h2
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 22,
              fontWeight: 300,
              color: brandTokens.colors.dark,
              marginBottom: 24,
            }}
          >
            Access your workspace
          </h2>

          {/* Email field */}
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: "block",
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 10,
                fontWeight: 500,
                letterSpacing: "3px",
                textTransform: "uppercase",
                color: brandTokens.colors.mid,
                marginBottom: 6,
              }}
            >
              Email
            </label>
            <input
              type="email"
              placeholder="you@company.com"
              style={{
                width: "100%",
                padding: "10px 12px",
                border: `1px solid ${brandTokens.colors.primary10}`,
                borderRadius: 8,
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 14,
                color: brandTokens.colors.dark,
                backgroundColor: brandTokens.colors.light,
                outline: "none",
              }}
            />
          </div>

          {/* CTA */}
          <button
            style={{
              width: "100%",
              padding: "12px",
              backgroundColor: brandTokens.colors.primary,
              color: "#ffffff",
              border: "none",
              borderRadius: 8,
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "2px",
              textTransform: "uppercase",
              cursor: "pointer",
              marginTop: 8,
            }}
          >
            Send magic link →
          </button>

          <p
            style={{
              marginTop: 16,
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 12,
              color: brandTokens.colors.mid,
              textAlign: "center",
            }}
          >
            No password required. We email you a sign-in link.
          </p>
        </div>
      </div>

      <Footer />
    </div>
  );
}
