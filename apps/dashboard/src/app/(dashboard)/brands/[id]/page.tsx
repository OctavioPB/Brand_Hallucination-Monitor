"use client";

import { useState } from "react";
import Link from "next/link";
import { brandTokens } from "@/lib/brand-tokens";
import {
  useBrand,
  useSPSScores,
  useHallucinations,
  useVectorMap,
  useCompetitors,
} from "@/hooks/use-brands";
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
  const { data: competitors = [], isLoading } = useCompetitors(brandId);

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

      {isLoading ? (
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.mid,
          }}
        >
          Loading competitors…
        </p>
      ) : competitors.length === 0 ? (
        <div
          style={{
            ...brandTokens.card,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 120,
          }}
        >
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.mid,
            }}
          >
            No competitors configured — add them via the API to enable comparative analysis.
          </p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 16,
          }}
        >
          {competitors.map((c) => (
            <div
              key={c.id}
              style={{
                ...brandTokens.card,
                padding: "18px 22px",
                display: "flex",
                gap: 14,
                alignItems: "center",
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  backgroundColor: brandTokens.colors.primary10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: brandTokens.typography.fontDisplay,
                  fontSize: 14,
                  color: brandTokens.colors.primary60,
                  fontWeight: 400,
                  flexShrink: 0,
                }}
              >
                {c.competitor_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div
                  style={{
                    fontFamily: brandTokens.typography.fontBody,
                    fontSize: 13,
                    fontWeight: 600,
                    color: brandTokens.colors.dark,
                    marginBottom: 2,
                  }}
                >
                  {c.competitor_name}
                </div>
                {c.competitor_slug && (
                  <div
                    style={{
                      fontFamily: brandTokens.typography.fontMono,
                      fontSize: 10,
                      color: brandTokens.colors.mid,
                    }}
                  >
                    {c.competitor_slug}
                  </div>
                )}
              </div>
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

  const { data: brand, isLoading: brandLoading } = useBrand(params.id);
  const { data: spsScores = [] } = useSPSScores(params.id);
  const { data: hallucinations = [] } = useHallucinations(params.id);

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
        {/* Back link */}
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
            marginBottom: 20,
          }}
        >
          ← Dashboard
        </Link>

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
          accentColor={
            totalHallucinations > 0
              ? brandTokens.status.danger.base
              : brandTokens.status.success.base
          }
        />
        <KPICard
          value={lastScan}
          label="Last Scan"
          sub="Most recent probe run"
          accentColor={brandTokens.dataSeries[2]}
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
