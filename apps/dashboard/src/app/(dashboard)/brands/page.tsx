"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { brandTokens } from "@/lib/brand-tokens";
import { createBrand, seedBrandData } from "@/lib/api-client";
import { useBrands, BRANDS_KEY } from "@/hooks/use-brands";
import { Eyebrow } from "@/components/eyebrow";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function slugify(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64);
}

function splitTags(raw: string): string[] {
  return raw.split(",").map((s) => s.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------------
// Input field wrapper
// ---------------------------------------------------------------------------

function Field({
  label, hint, children,
}: {
  label: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <label style={{ display: "block", fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 500, letterSpacing: "2.5px", textTransform: "uppercase", color: brandTokens.colors.mid, marginBottom: 6 }}>
        {label}
      </label>
      {children}
      {hint && (
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 11, color: brandTokens.colors.mid, marginTop: 4 }}>
          {hint}
        </p>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px",
  border: `1px solid ${brandTokens.colors.primary10}`, borderRadius: 8,
  fontFamily: brandTokens.typography.fontBody, fontSize: 13,
  color: brandTokens.colors.dark, backgroundColor: brandTokens.colors.white,
  outline: "none", boxSizing: "border-box",
};

// ---------------------------------------------------------------------------
// Create Brand Modal
// ---------------------------------------------------------------------------

function CreateBrandModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [trueAttrs, setTrueAttrs] = useState("");
  const [falseAttrs, setFalseAttrs] = useState("");
  const [competitors, setCompetitors] = useState("");
  const [regulatory, setRegulatory] = useState("");
  const [seedData, setSeedData] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleNameChange(v: string) {
    setName(v);
    if (!slugEdited) setSlug(slugify(v));
  }

  function handleSlugChange(v: string) {
    setSlugEdited(true);
    setSlug(v.toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 64));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const brand = await createBrand({
        organization_id: "demo",
        name: name.trim(),
        slug: slug.trim(),
        manifest: {
          true_attributes: splitTags(trueAttrs),
          false_attributes: splitTags(falseAttrs),
          competitor_list: splitTags(competitors),
          regulatory_claims_to_avoid: splitTags(regulatory),
        },
      });

      if (seedData) {
        await seedBrandData(brand.id);
      }

      await queryClient.invalidateQueries({ queryKey: BRANDS_KEY });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create brand.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.45)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{ ...brandTokens.card, width: "100%", maxWidth: 540, maxHeight: "90vh", overflowY: "auto", borderTop: `3px solid ${brandTokens.colors.gold}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <Eyebrow>New brand</Eyebrow>
            <h2 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 22, fontWeight: 300, color: brandTokens.colors.dark, margin: "6px 0 0" }}>
              Configure brand manifest
            </h2>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: brandTokens.colors.mid, lineHeight: 1 }}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <Field label="Brand name">
            <input
              style={inputStyle} type="text" required placeholder="e.g. Acme Corp"
              value={name} onChange={(e) => handleNameChange(e.target.value)}
            />
          </Field>

          <Field label="Brand slug" hint="URL-safe identifier — auto-generated, can be edited.">
            <input
              style={inputStyle} type="text" required placeholder="e.g. acme-corp"
              value={slug} onChange={(e) => handleSlugChange(e.target.value)}
            />
          </Field>

          <Field label="True attributes" hint="What the brand genuinely is — separate with commas.">
            <input
              style={inputStyle} type="text"
              placeholder="e.g. reliable, SOC2-certified, enterprise-grade"
              value={trueAttrs} onChange={(e) => setTrueAttrs(e.target.value)}
            />
          </Field>

          <Field label="False attributes" hint="Claims that are factually wrong — hallucinations to detect.">
            <input
              style={inputStyle} type="text"
              placeholder="e.g. open-source, free, consumer-focused"
              value={falseAttrs} onChange={(e) => setFalseAttrs(e.target.value)}
            />
          </Field>

          <Field label="Competitors" hint="Brand names that should not be confused with yours.">
            <input
              style={inputStyle} type="text"
              placeholder="e.g. Rival Inc., FastStart SaaS"
              value={competitors} onChange={(e) => setCompetitors(e.target.value)}
            />
          </Field>

          <Field label="Regulatory claims to avoid" hint="Phrases that must never appear in AI responses.">
            <input
              style={inputStyle} type="text"
              placeholder="e.g. HIPAA-compliant, FDA-cleared"
              value={regulatory} onChange={(e) => setRegulatory(e.target.value)}
            />
          </Field>

          {/* Seed checkbox */}
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "14px 16px", backgroundColor: brandTokens.status.primary.bg, borderRadius: 8, marginBottom: 20 }}>
            <input
              id="seed" type="checkbox" checked={seedData}
              onChange={(e) => setSeedData(e.target.checked)}
              style={{ marginTop: 2, cursor: "pointer", accentColor: brandTokens.colors.primary }}
            />
            <label htmlFor="seed" style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.dark, lineHeight: 1.6, cursor: "pointer" }}>
              <strong style={{ display: "block", marginBottom: 2 }}>Seed with sample data</strong>
              Populates SPS scores across 6 intent clusters, 3 probe results, and a baseline alert so charts show immediately.
            </label>
          </div>

          {error && (
            <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.status.danger.base, marginBottom: 14 }}>
              {error}
            </p>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button
              type="button" onClick={onClose}
              style={{ flex: 1, padding: "11px", backgroundColor: brandTokens.colors.light, color: brandTokens.colors.mid, border: `1px solid ${brandTokens.colors.primary10}`, borderRadius: 8, fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="submit" disabled={loading || !name.trim() || !slug.trim()}
              style={{ flex: 2, padding: "11px", backgroundColor: loading ? brandTokens.colors.primary60 : brandTokens.colors.primary, color: "#fff", border: "none", borderRadius: 8, fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "Creating…" : seedData ? "Create & seed data →" : "Create brand →"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function BrandsPage() {
  const { data: brands = [], isLoading } = useBrands();
  const [showModal, setShowModal] = useState(false);

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "56px 48px" }}>
      {/* Hero */}
      <div style={{ ...brandTokens.heroSection, borderRadius: 14, padding: "48px", marginBottom: 40, display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <Eyebrow light>Brand registry</Eyebrow>
          <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 32, fontWeight: 300, color: "#fff", marginTop: 10 }}>
            Monitored{" "}
            <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>brands</em>
          </h1>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: "rgba(255,255,255,0.55)", marginTop: 8, lineHeight: 1.7 }}>
            Each brand has its own SPS scores, hallucination history, and vector map.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          style={{ flexShrink: 0, padding: "10px 20px", backgroundColor: brandTokens.colors.gold, color: brandTokens.colors.dark, border: "none", borderRadius: 8, fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer", whiteSpace: "nowrap" }}
        >
          + New brand
        </button>
      </div>

      {isLoading ? (
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid }}>
          Loading brands…
        </p>
      ) : brands.length === 0 ? (
        <div style={{ textAlign: "center", padding: "64px 0" }}>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 14, color: brandTokens.colors.mid, marginBottom: 20 }}>
            No brands yet — add your first one.
          </p>
          <button
            onClick={() => setShowModal(true)}
            style={{ padding: "11px 24px", backgroundColor: brandTokens.colors.primary, color: "#fff", border: "none", borderRadius: 8, fontFamily: brandTokens.typography.fontBody, fontSize: 10, fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer" }}
          >
            + Add brand
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 20 }}>
          {brands.map((brand) => (
            <Link key={brand.id} href={`/brands/${brand.id}`} style={{ textDecoration: "none" }}>
              <div
                style={{ ...brandTokens.card, borderTop: `3px solid ${brandTokens.colors.gold}`, display: "flex", flexDirection: "column", gap: 10, cursor: "pointer" }}
              >
                <div style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 20, fontWeight: 400, color: brandTokens.colors.dark }}>
                  {brand.name}
                </div>
                <div style={{ fontFamily: brandTokens.typography.fontMono, fontSize: 10, color: brandTokens.colors.mid, letterSpacing: "0.5px" }}>
                  {brand.slug}
                </div>
                {brand.manifest && brand.manifest.true_attributes.length > 0 && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                    {brand.manifest.true_attributes.slice(0, 3).map((attr) => (
                      <span key={attr} style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase", padding: "3px 8px", borderRadius: 10, backgroundColor: brandTokens.status.primary.bg, color: brandTokens.status.primary.text }}>
                        {attr}
                      </span>
                    ))}
                  </div>
                )}
                <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: brandTokens.colors.primary60, marginTop: 4 }}>
                  View detail →
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showModal && <CreateBrandModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
