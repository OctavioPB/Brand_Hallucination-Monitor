"use client";

import { useState } from "react";
import Link from "next/link";
import { brandTokens } from "@/lib/brand-tokens";
import {
  useBrand,
  useSPSScores,
  useHallucinations,
  useVectorMap,
  useUpdateBrandManifest,
} from "@/hooks/use-brands";
import { useTriggerScan, useScanJob } from "@/hooks/use-scan";
import { KPICard } from "@/components/kpi-card";
import { SPSTrendChart } from "@/components/sps-trend-chart";
import { VectorScatter } from "@/components/vector-scatter";
import { HallucinationCard } from "@/components/hallucination-card";
import { SeverityBadge } from "@/components/severity-badge";
import { Eyebrow } from "@/components/eyebrow";

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

const TABS = ["Overview", "Vector Map", "Hallucinations", "Competitors"] as const;
type Tab = (typeof TABS)[number];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function avgSPS(scores: { score: number }[]): string {
  if (!scores.length) return "—";
  const avg = scores.reduce((acc, s) => acc + s.score, 0) / scores.length;
  return `${(avg * 100).toFixed(1)}%`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Overview tab — SPS trend chart
// ---------------------------------------------------------------------------

function OverviewTab({
  brandId,
  hallucinationDates,
}: {
  brandId: string;
  hallucinationDates: string[];
}) {
  const { data: spsScores = [], isLoading } = useSPSScores(brandId);

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <Eyebrow>SPS Trend</Eyebrow>
        <h3
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 20,
            fontWeight: 300,
            color: brandTokens.colors.dark,
            margin: "4px 0 4px",
          }}
        >
          Semantic proximity{" "}
          <em style={{ fontStyle: "italic" }}>over time</em>
        </h3>
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 12,
            color: brandTokens.colors.mid,
            margin: "0 0 24px",
          }}
        >
          Cosine similarity between your brand embeddings and each intent cluster.
          ⚠ markers indicate days with detected hallucinations.
        </p>
      </div>
      <div style={{ ...brandTokens.card }}>
        <SPSTrendChart
          scores={spsScores}
          isLoading={isLoading}
          hallucinationDates={hallucinationDates}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Vector Map tab
// ---------------------------------------------------------------------------

function VectorMapTab({ brandId }: { brandId: string }) {
  const { data: vectorMap, isLoading } = useVectorMap(brandId);

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <Eyebrow>Vector Map</Eyebrow>
        <h3
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 20,
            fontWeight: 300,
            color: brandTokens.colors.dark,
            margin: "4px 0 4px",
          }}
        >
          2D semantic{" "}
          <em style={{ fontStyle: "italic" }}>position</em>
        </h3>
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 12,
            color: brandTokens.colors.mid,
            margin: "0 0 24px",
          }}
        >
          t-SNE projection of brand embedding vectors, colored by intent cluster.
          {vectorMap?.generated_at && (
            <> Last computed {formatDate(vectorMap.generated_at)}.</>
          )}
        </p>
      </div>
      <div style={{ ...brandTokens.card }}>
        <VectorScatter
          points={vectorMap?.points ?? []}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hallucinations tab
// ---------------------------------------------------------------------------

function HallucinationsTab({ brandId }: { brandId: string }) {
  const { data: hallucinations = [], isLoading } = useHallucinations(brandId);
  const withDetected = hallucinations.filter(
    (h) => h.hallucinations_detected > 0
  );

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 24,
        }}
      >
        <div>
          <Eyebrow>Hallucination Feed</Eyebrow>
          <h3
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 20,
              fontWeight: 300,
              color: brandTokens.colors.dark,
              margin: "4px 0 0",
            }}
          >
            Detected{" "}
            <em style={{ fontStyle: "italic" }}>hallucinations</em>
          </h3>
        </div>
        <div
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 11,
            color: brandTokens.colors.mid,
            textAlign: "right",
          }}
        >
          <span style={{ color: brandTokens.status.danger.text, fontWeight: 600 }}>
            {withDetected.length}
          </span>{" "}
          of {hallucinations.length} probes flagged
        </div>
      </div>

      {isLoading ? (
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.mid,
          }}
        >
          Loading probe history…
        </p>
      ) : hallucinations.length === 0 ? (
        <div
          style={{
            ...brandTokens.card,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 160,
          }}
        >
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.mid,
            }}
          >
            No probes recorded yet — run the hallucination detection DAG to populate this feed.
          </p>
        </div>
      ) : (
        hallucinations.map((h) => (
          <HallucinationCard key={h.probe_id} hallucination={h} />
        ))
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Competitors tab
// ---------------------------------------------------------------------------

function CompetitorsTab({ brandId }: { brandId: string }) {
  const { data: brand, isLoading } = useBrand(brandId);
  const { mutate: updateManifest, isPending } = useUpdateBrandManifest(brandId);
  const [input, setInput] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);

  const competitors: string[] = brand?.manifest?.competitor_list ?? [];

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const name = input.trim();
    if (!name || competitors.includes(name)) return;
    const manifest = {
      true_attributes: brand?.manifest?.true_attributes ?? [],
      false_attributes: brand?.manifest?.false_attributes ?? [],
      competitor_list: [...competitors, name],
      regulatory_claims_to_avoid: brand?.manifest?.regulatory_claims_to_avoid ?? [],
    };
    setSaveError(null);
    updateManifest(manifest, {
      onSuccess: () => setInput(""),
      onError: (err) => setSaveError(err instanceof Error ? err.message : "Save failed"),
    });
  }

  function handleRemove(name: string) {
    const manifest = {
      true_attributes: brand?.manifest?.true_attributes ?? [],
      false_attributes: brand?.manifest?.false_attributes ?? [],
      competitor_list: competitors.filter((c) => c !== name),
      regulatory_claims_to_avoid: brand?.manifest?.regulatory_claims_to_avoid ?? [],
    };
    setSaveError(null);
    updateManifest(manifest, {
      onError: (err) => setSaveError(err instanceof Error ? err.message : "Save failed"),
    });
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Eyebrow>Competitor Registry</Eyebrow>
        <h3
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 20,
            fontWeight: 300,
            color: brandTokens.colors.dark,
            margin: "4px 0 0",
          }}
        >
          Tracked{" "}
          <em style={{ fontStyle: "italic" }}>competitors</em>
        </h3>
      </div>

      {/* Add competitor form */}
      <form onSubmit={handleAdd} style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Competitor name, e.g. Rival Inc."
          disabled={isPending}
          style={{
            flex: 1, padding: "9px 12px",
            border: `1px solid ${brandTokens.colors.primary10}`,
            borderRadius: 8,
            fontFamily: brandTokens.typography.fontBody, fontSize: 13,
            color: brandTokens.colors.dark, backgroundColor: brandTokens.colors.white,
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={isPending || !input.trim()}
          style={{
            padding: "9px 18px",
            backgroundColor: input.trim() && !isPending ? brandTokens.colors.primary : brandTokens.colors.primary10,
            color: input.trim() && !isPending ? "#fff" : brandTokens.colors.mid,
            border: "none", borderRadius: 8, cursor: input.trim() && !isPending ? "pointer" : "not-allowed",
            fontFamily: brandTokens.typography.fontBody, fontSize: 10,
            fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase",
            whiteSpace: "nowrap", transition: "background 0.15s",
          }}
        >
          {isPending ? "Saving…" : "+ Add"}
        </button>
      </form>

      {saveError && (
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.status.danger.base, marginBottom: 16 }}>
          {saveError}
        </p>
      )}

      {isLoading ? (
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid }}>
          Loading…
        </p>
      ) : competitors.length === 0 ? (
        <div
          style={{
            ...brandTokens.card,
            display: "flex", alignItems: "center", justifyContent: "center", minHeight: 120,
          }}
        >
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid }}>
            No competitors yet — add one above to enable comparative hallucination analysis.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
          {competitors.map((name) => (
            <div
              key={name}
              style={{
                ...brandTokens.card,
                padding: "16px 20px",
                display: "flex", gap: 12, alignItems: "center",
                borderLeft: `3px solid ${brandTokens.colors.gold}`,
              }}
            >
              <div
                style={{
                  width: 34, height: 34, borderRadius: "50%",
                  backgroundColor: brandTokens.colors.primary10,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: brandTokens.typography.fontDisplay, fontSize: 14,
                  color: brandTokens.colors.primary60, fontWeight: 400, flexShrink: 0,
                }}
              >
                {name.charAt(0).toUpperCase()}
              </div>
              <div style={{ flex: 1, fontFamily: brandTokens.typography.fontBody, fontSize: 13, fontWeight: 600, color: brandTokens.colors.dark }}>
                {name}
              </div>
              <button
                onClick={() => handleRemove(name)}
                disabled={isPending}
                title="Remove competitor"
                style={{
                  background: "none", border: "none", cursor: isPending ? "not-allowed" : "pointer",
                  color: brandTokens.colors.mid, fontSize: 16, lineHeight: 1,
                  padding: "2px 4px", borderRadius: 4, flexShrink: 0,
                  opacity: isPending ? 0.4 : 1,
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

interface BrandPageProps {
  params: { id: string };
}

export default function BrandPage({ params }: BrandPageProps) {
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { data: brand, isLoading: brandLoading } = useBrand(params.id);
  const { data: spsScores = [] } = useSPSScores(params.id);
  const { data: hallucinations = [] } = useHallucinations(params.id);
  const { mutate: triggerScan, isPending: scanLaunching } = useTriggerScan();
  const { data: scanJob } = useScanJob(activeJobId);

  const totalHallucinations = hallucinations.reduce(
    (acc, h) => acc + h.hallucinations_detected,
    0
  );
  const lastScan =
    hallucinations.length > 0
      ? formatDate(hallucinations[0].probed_at)
      : "Never";
  const hallucinationDates = hallucinations
    .filter((h) => h.hallucinations_detected > 0)
    .map((h) => h.probed_at);

  function handleRunScan() {
    triggerScan(
      { brand_id: params.id, job_type: "llm_probe" },
      { onSuccess: (job) => setActiveJobId(job.id) }
    );
  }

  const scanStatus = scanJob?.status ?? null;
  const scanDone = scanStatus === "completed" || scanStatus === "failed";

  return (
    <div style={{ maxWidth: 1300, margin: "0 auto", padding: "56px 48px" }}>
      {/* Hero banner */}
      <div
        style={{
          ...brandTokens.heroSection,
          borderRadius: 14,
          padding: "48px",
          marginBottom: 32,
        }}
      >
        {/* Back link + scan button row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <Link
            href="/dashboard"
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: "rgba(255,255,255,0.35)",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            ← Dashboard
          </Link>

          {/* Scan trigger */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {activeJobId && scanJob && (
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {!scanDone && (
                  <span style={{
                    display: "inline-block", width: 7, height: 7, borderRadius: "50%",
                    backgroundColor: scanStatus === "running" ? brandTokens.colors.goldLight : "rgba(255,255,255,0.4)",
                    animation: !scanDone ? "pulse 1.4s ease-in-out infinite" : "none",
                  }} />
                )}
                <span style={{
                  fontFamily: brandTokens.typography.fontBody, fontSize: 9,
                  letterSpacing: "1.5px", textTransform: "uppercase",
                  color: scanStatus === "completed" ? brandTokens.status.success.base
                    : scanStatus === "failed" ? brandTokens.status.danger.base
                    : "rgba(255,255,255,0.55)",
                }}>
                  {scanStatus === "pending" ? "Queued…"
                    : scanStatus === "running" ? "Scanning…"
                    : scanStatus === "completed" ? "✓ Scan complete"
                    : scanStatus === "failed" ? `✗ ${scanJob.error_message ?? "Failed"}`
                    : scanStatus}
                </span>
                {scanDone && (
                  <button
                    onClick={() => setActiveJobId(null)}
                    style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: 14, lineHeight: 1, padding: "0 2px" }}
                  >
                    ×
                  </button>
                )}
              </div>
            )}
            <button
              onClick={handleRunScan}
              disabled={scanLaunching || (!!activeJobId && !scanDone)}
              style={{
                padding: "7px 16px",
                backgroundColor: scanLaunching || (!!activeJobId && !scanDone)
                  ? "rgba(255,255,255,0.1)"
                  : brandTokens.colors.gold,
                color: scanLaunching || (!!activeJobId && !scanDone)
                  ? "rgba(255,255,255,0.4)"
                  : brandTokens.colors.dark,
                border: "none", borderRadius: 7, cursor: scanLaunching || (!!activeJobId && !scanDone) ? "not-allowed" : "pointer",
                fontFamily: brandTokens.typography.fontBody, fontSize: 9,
                fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase",
                transition: "all 0.15s",
              }}
            >
              {scanLaunching ? "Launching…" : "Run scan"}
            </button>
          </div>
        </div>

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
          {brandLoading ? (
            <span style={{ color: "rgba(255,255,255,0.4)" }}>Loading…</span>
          ) : (
            <>
              {brand?.name ?? params.id.replace(/-/g, " ")}{" "}
              <em
                style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}
              >
                audit
              </em>
            </>
          )}
        </h1>
        {brand?.slug && (
          <p
            style={{
              fontFamily: brandTokens.typography.fontMono,
              fontSize: 11,
              color: "rgba(255,255,255,0.35)",
              margin: "0 0 24px",
            }}
          >
            {brand.slug}
          </p>
        )}

        {/* Tab switcher */}
        <div
          style={{
            display: "flex",
            gap: 4,
            borderBottom: "1px solid rgba(255,255,255,0.1)",
            marginTop: 8,
          }}
        >
          {TABS.map((tab) => {
            const active = tab === activeTab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: "none",
                  border: "none",
                  borderBottom: active
                    ? `2px solid ${brandTokens.colors.goldLight}`
                    : "2px solid transparent",
                  cursor: "pointer",
                  padding: "10px 20px",
                  marginBottom: -1,
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: "1.5px",
                  textTransform: "uppercase",
                  color: active
                    ? brandTokens.colors.goldLight
                    : "rgba(255,255,255,0.4)",
                  transition: "color 0.15s",
                }}
              >
                {tab}
              </button>
            );
          })}
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
        <KPICard
          value={avgSPS(spsScores)}
          label="Avg SPS Score"
          sub="Across all intent clusters"
        />
        <KPICard
          value={String(totalHallucinations)}
          label="Hallucinations Detected"
          sub="All-time total"
          valueColor={totalHallucinations > 0 ? brandTokens.status.danger.base : undefined}
        />
        <KPICard
          value={lastScan}
          label="Last Scan"
          sub="Most recent probe run"
        />
      </div>

      {/* Divider */}
      <div
        style={{
          height: 1,
          backgroundColor: brandTokens.colors.primary10,
          marginBottom: 40,
        }}
      />

      {/* Tab content */}
      {activeTab === "Overview" && (
        <OverviewTab
          brandId={params.id}
          hallucinationDates={hallucinationDates}
        />
      )}
      {activeTab === "Vector Map" && (
        <VectorMapTab brandId={params.id} />
      )}
      {activeTab === "Hallucinations" && (
        <HallucinationsTab brandId={params.id} />
      )}
      {activeTab === "Competitors" && (
        <CompetitorsTab brandId={params.id} />
      )}
    </div>
  );
}
