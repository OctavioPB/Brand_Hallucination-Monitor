"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { brandTokens } from "@/lib/brand-tokens";
import { Footer } from "@/components/footer";

// ---------------------------------------------------------------------------
// Step types
// ---------------------------------------------------------------------------
type Step = "brand" | "attributes" | "review";

const STEPS: { key: Step; label: string }[] = [
  { key: "brand", label: "Brand identity" },
  { key: "attributes", label: "Brand attributes" },
  { key: "review", label: "Launch scan" },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<Step>("brand");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [brandName, setBrandName] = useState("");
  const [brandSlug, setBrandSlug] = useState("");
  const [trueAttrs, setTrueAttrs] = useState("");
  const [falseAttrs, setFalseAttrs] = useState("");
  const [competitors, setCompetitors] = useState("");

  function autoSlug(name: string) {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64);
  }

  async function handleFinish() {
    setLoading(true);
    setError(null);
    try {
      const apiKey = typeof window !== "undefined" ? localStorage.getItem("hallucin8_api_key") ?? "" : "";
      const res = await fetch("/api/v1/onboarding/brand-wizard", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          brand_name: brandName,
          brand_slug: brandSlug || autoSlug(brandName),
          true_attributes: trueAttrs.split(",").map((s) => s.trim()).filter(Boolean),
          false_attributes: falseAttrs.split(",").map((s) => s.trim()).filter(Boolean),
          competitor_names: competitors.split(",").map((s) => s.trim()).filter(Boolean),
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail ?? `Error ${res.status}`);
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Setup failed.");
    } finally {
      setLoading(false);
    }
  }

  const stepIdx = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: brandTokens.colors.light }}>
      {/* Hero */}
      <div style={{ ...brandTokens.heroSection, padding: "48px 48px 40px", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "4px", textTransform: "uppercase", color: "rgba(255,255,255,0.45)", marginBottom: 20 }}>
          Brand setup wizard
        </div>
        {/* Step indicators */}
        <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
          {STEPS.map((step, i) => {
            const done = i < stepIdx;
            const active = i === stepIdx;
            return (
              <div key={step.key} style={{ display: "flex", alignItems: "center" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: "50%",
                    backgroundColor: done ? brandTokens.colors.gold : active ? "#fff" : "rgba(255,255,255,0.15)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: brandTokens.typography.fontBody, fontSize: 11, fontWeight: 600,
                    color: done ? "#fff" : active ? brandTokens.colors.primary : "rgba(255,255,255,0.4)",
                    transition: "all 0.2s",
                  }}>
                    {done ? "✓" : i + 1}
                  </div>
                  <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: active ? "#fff" : "rgba(255,255,255,0.35)" }}>
                    {step.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{ width: 60, height: 1, backgroundColor: done ? brandTokens.colors.gold : "rgba(255,255,255,0.15)", margin: "0 8px", marginBottom: 22 }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Card */}
      <div style={{ flex: 1, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "40px 24px" }}>
        <div style={{ ...brandTokens.card, width: "100%", maxWidth: 560 }}>
          {currentStep === "brand" && (
            <StepBrand
              brandName={brandName}
              setBrandName={(v) => { setBrandName(v); setBrandSlug(autoSlug(v)); }}
              brandSlug={brandSlug}
              setBrandSlug={setBrandSlug}
              onNext={() => setCurrentStep("attributes")}
            />
          )}
          {currentStep === "attributes" && (
            <StepAttributes
              trueAttrs={trueAttrs}
              setTrueAttrs={setTrueAttrs}
              falseAttrs={falseAttrs}
              setFalseAttrs={setFalseAttrs}
              competitors={competitors}
              setCompetitors={setCompetitors}
              onBack={() => setCurrentStep("brand")}
              onNext={() => setCurrentStep("review")}
            />
          )}
          {currentStep === "review" && (
            <StepReview
              brandName={brandName}
              brandSlug={brandSlug}
              trueAttrs={trueAttrs}
              falseAttrs={falseAttrs}
              competitors={competitors}
              loading={loading}
              error={error}
              onBack={() => setCurrentStep("attributes")}
              onFinish={handleFinish}
            />
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step components
// ---------------------------------------------------------------------------

function StepBrand({ brandName, setBrandName, brandSlug, setBrandSlug, onNext }: {
  brandName: string; setBrandName: (v: string) => void;
  brandSlug: string; setBrandSlug: (v: string) => void;
  onNext: () => void;
}) {
  return (
    <>
      <StepHeading eyebrow="Step 1 of 3" title="Your brand identity" />
      <Field label="Brand name" htmlFor="bn">
        <input id="bn" type="text" required value={brandName} onChange={(e) => setBrandName(e.target.value)} placeholder="Acme Corp" style={inputStyle} />
      </Field>
      <Field label="URL slug (used in API paths)" htmlFor="bs">
        <input id="bs" type="text" required value={brandSlug} onChange={(e) => setBrandSlug(e.target.value)} placeholder="acme-corp" style={inputStyle} />
      </Field>
      <Hint>The slug identifies your brand in API calls. Lowercase letters, numbers, and hyphens only.</Hint>
      <NavButtons onNext={onNext} nextDisabled={!brandName || !brandSlug} />
    </>
  );
}

function StepAttributes({ trueAttrs, setTrueAttrs, falseAttrs, setFalseAttrs, competitors, setCompetitors, onBack, onNext }: {
  trueAttrs: string; setTrueAttrs: (v: string) => void;
  falseAttrs: string; setFalseAttrs: (v: string) => void;
  competitors: string; setCompetitors: (v: string) => void;
  onBack: () => void; onNext: () => void;
}) {
  return (
    <>
      <StepHeading eyebrow="Step 2 of 3" title="Brand attributes" />
      <Field label="True attributes (comma-separated)" htmlFor="ta">
        <textarea id="ta" value={trueAttrs} onChange={(e) => setTrueAttrs(e.target.value)} placeholder="reliable, enterprise-grade, SOC2-certified" style={{ ...inputStyle, height: 72, resize: "vertical" }} />
      </Field>
      <Field label="False attributes — things you are NOT" htmlFor="fa">
        <textarea id="fa" value={falseAttrs} onChange={(e) => setFalseAttrs(e.target.value)} placeholder="open-source, free, consumer-focused" style={{ ...inputStyle, height: 72, resize: "vertical" }} />
      </Field>
      <Field label="Competitors to track (comma-separated)" htmlFor="comp">
        <input id="comp" type="text" value={competitors} onChange={(e) => setCompetitors(e.target.value)} placeholder="Rival Inc., FastStart SaaS" style={inputStyle} />
      </Field>
      <Hint>These attributes define your brand manifest — the ground truth used to detect hallucinations.</Hint>
      <NavButtons onBack={onBack} onNext={onNext} />
    </>
  );
}

function StepReview({ brandName, brandSlug, trueAttrs, falseAttrs, competitors, loading, error, onBack, onFinish }: {
  brandName: string; brandSlug: string;
  trueAttrs: string; falseAttrs: string; competitors: string;
  loading: boolean; error: string | null;
  onBack: () => void; onFinish: () => void;
}) {
  return (
    <>
      <StepHeading eyebrow="Step 3 of 3" title="Review and launch" />
      <ReviewRow label="Brand name" value={brandName} />
      <ReviewRow label="Slug" value={brandSlug} />
      <ReviewRow label="True attributes" value={trueAttrs || "—"} />
      <ReviewRow label="False attributes" value={falseAttrs || "—"} />
      <ReviewRow label="Competitors" value={competitors || "—"} />

      {error && <p style={{ color: brandTokens.status.danger.base, fontSize: 13, fontFamily: brandTokens.typography.fontBody, marginBottom: 12 }}>{error}</p>}

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button onClick={onBack} style={backBtnStyle}>← Back</button>
        <button onClick={onFinish} disabled={loading} style={{ ...primaryBtnStyle, flex: 1, opacity: loading ? 0.6 : 1, cursor: loading ? "not-allowed" : "pointer" }}>
          {loading ? "Launching scan…" : "Launch first scan →"}
        </button>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

function StepHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 9, fontFamily: brandTokens.typography.fontBody, fontWeight: 500, letterSpacing: "4px", textTransform: "uppercase", color: brandTokens.colors.gold, marginBottom: 8 }}>{eyebrow}</div>
      <h2 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 22, fontWeight: 300, color: brandTokens.colors.dark, margin: 0 }}>{title}</h2>
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

function Hint({ children }: { children: React.ReactNode }) {
  return <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: brandTokens.colors.mid, lineHeight: 1.6, marginBottom: 20 }}>{children}</p>;
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 12, padding: "10px 0", borderBottom: `1px solid ${brandTokens.colors.primary10}` }}>
      <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 500, letterSpacing: "2px", textTransform: "uppercase", color: brandTokens.colors.mid, width: 140, flexShrink: 0 }}>{label}</span>
      <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.dark }}>{value}</span>
    </div>
  );
}

function NavButtons({ onBack, onNext, nextDisabled }: { onBack?: () => void; onNext?: () => void; nextDisabled?: boolean }) {
  return (
    <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
      {onBack && <button onClick={onBack} style={backBtnStyle}>← Back</button>}
      {onNext && (
        <button onClick={onNext} disabled={nextDisabled} style={{ ...primaryBtnStyle, flex: 1, opacity: nextDisabled ? 0.5 : 1, cursor: nextDisabled ? "not-allowed" : "pointer" }}>
          Continue →
        </button>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 12px",
  border: `1px solid ${brandTokens.colors.primary10}`, borderRadius: 8,
  fontFamily: brandTokens.typography.fontBody, fontSize: 14,
  color: brandTokens.colors.dark, backgroundColor: brandTokens.colors.light,
  outline: "none", boxSizing: "border-box",
};

const primaryBtnStyle: React.CSSProperties = {
  padding: "12px", backgroundColor: brandTokens.colors.primary,
  color: "#fff", border: "none", borderRadius: 8,
  fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 600,
  letterSpacing: "2px", textTransform: "uppercase",
};

const backBtnStyle: React.CSSProperties = {
  padding: "12px 16px", backgroundColor: "transparent",
  color: brandTokens.colors.mid, border: `1px solid ${brandTokens.colors.primary10}`,
  borderRadius: 8, fontFamily: brandTokens.typography.fontBody, fontSize: 10,
  fontWeight: 500, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer",
};
