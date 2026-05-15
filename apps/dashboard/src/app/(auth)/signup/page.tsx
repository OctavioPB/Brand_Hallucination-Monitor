"use client";

import { useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";
import { Footer } from "@/components/footer";

interface SignupResponse {
  organization_id: string;
  org_name: string;
  slug: string;
  raw_api_key: string;
  message: string;
}

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [orgName, setOrgName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SignupResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/onboarding/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, org_name: orgName }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail ?? `Error ${res.status}`);
      }
      const data: SignupResponse = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return <SignupSuccess result={result} />;
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: brandTokens.colors.light }}>
      <div style={{ ...brandTokens.heroSection, padding: "80px 48px 56px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
        <div style={{ marginBottom: 28 }}>
          <span style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 28, fontWeight: 300, color: "#fff" }}>O</span>
          <em style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 28, fontWeight: 300, fontStyle: "italic", color: brandTokens.colors.goldLight }}>PB</em>
        </div>
        <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 40, fontWeight: 300, color: "#fff", maxWidth: 520, lineHeight: 1.25, marginBottom: 12 }}>
          Start your{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>brand safety</em>
          {" "}audit
        </h1>
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: "rgba(255,255,255,0.55)", lineHeight: 1.7, maxWidth: 420 }}>
          Monitor how every major AI model perceives your brand. Free 14-day trial.
        </p>
      </div>

      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "56px 24px" }}>
        <div style={{ ...brandTokens.card, width: "100%", maxWidth: 440, borderTop: `3px solid ${brandTokens.colors.gold}` }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 9, fontFamily: brandTokens.typography.fontBody, fontWeight: 500, letterSpacing: "4px", textTransform: "uppercase", color: brandTokens.colors.gold, marginBottom: 18 }}>
            <div style={{ width: 20, height: 1, backgroundColor: brandTokens.colors.gold }} />
            Create account
          </div>

          <h2 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 22, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 24 }}>
            Set up your workspace
          </h2>

          <form onSubmit={handleSubmit}>
            <Field label="Work email" htmlFor="email">
              <input
                id="email"
                type="email"
                required
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
              />
            </Field>

            <Field label="Organization name" htmlFor="orgName">
              <input
                id="orgName"
                type="text"
                required
                placeholder="Acme Corp"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                style={inputStyle}
              />
            </Field>

            {error && (
              <p style={{ color: brandTokens.status.danger.base, fontSize: 13, fontFamily: brandTokens.typography.fontBody, marginBottom: 12 }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                padding: "12px",
                backgroundColor: loading ? brandTokens.colors.primary60 : brandTokens.colors.primary,
                color: "#fff",
                border: "none",
                borderRadius: 8,
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "2px",
                textTransform: "uppercase",
                cursor: loading ? "not-allowed" : "pointer",
                marginTop: 8,
              }}
            >
              {loading ? "Creating workspace…" : "Create workspace →"}
            </button>
          </form>

          <p style={{ marginTop: 16, fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: brandTokens.colors.mid, textAlign: "center" }}>
            Already have an account?{" "}
            <a href="/login" style={{ color: brandTokens.colors.primary60, textDecoration: "none" }}>Sign in</a>
          </p>
        </div>
      </div>

      <Footer />
    </div>
  );
}

function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label htmlFor={htmlFor} style={{ display: "block", fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 500, letterSpacing: "3px", textTransform: "uppercase", color: brandTokens.colors.mid, marginBottom: 6 }}>
        {label}
      </label>
      {children}
    </div>
  );
}

function SignupSuccess({ result }: { result: SignupResponse }) {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: brandTokens.colors.light }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "80px 24px" }}>
        <div style={{ ...brandTokens.card, width: "100%", maxWidth: 520, borderTop: `3px solid ${brandTokens.status.success.base}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", backgroundColor: brandTokens.status.success.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ color: brandTokens.status.success.base, fontSize: 16 }}>✓</span>
            </div>
            <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 500, letterSpacing: "3px", textTransform: "uppercase", color: brandTokens.status.success.base }}>
              Workspace created
            </span>
          </div>

          <h2 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 24, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 8 }}>
            Welcome to hallucin8, {result.org_name}
          </h2>

          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid, lineHeight: 1.7, marginBottom: 24 }}>
            Your workspace is ready. Save your API key below — it is shown once and cannot be recovered.
          </p>

          <div style={{ backgroundColor: brandTokens.colors.dark, borderRadius: 8, padding: "14px 16px", marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <code style={{ fontFamily: brandTokens.typography.fontMono, fontSize: 12, color: brandTokens.colors.goldLight, wordBreak: "break-all" }}>
              {result.raw_api_key}
            </code>
            <button
              onClick={() => navigator.clipboard.writeText(result.raw_api_key)}
              style={{ flexShrink: 0, padding: "6px 10px", backgroundColor: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 6, color: "rgba(255,255,255,0.6)", fontSize: 9, fontFamily: brandTokens.typography.fontBody, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer" }}
            >
              Copy
            </button>
          </div>

          <a
            href="/onboarding"
            style={{
              display: "block",
              width: "100%",
              textAlign: "center",
              padding: "12px",
              backgroundColor: brandTokens.colors.primary,
              color: "#fff",
              borderRadius: 8,
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "2px",
              textTransform: "uppercase",
              textDecoration: "none",
            }}
          >
            Set up your brand →
          </a>
        </div>
      </div>
      <Footer />
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  border: `1px solid ${brandTokens.colors.primary10}`,
  borderRadius: 8,
  fontFamily: brandTokens.typography.fontBody,
  fontSize: 14,
  color: brandTokens.colors.dark,
  backgroundColor: brandTokens.colors.light,
  outline: "none",
  boxSizing: "border-box",
};
