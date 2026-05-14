"use client";

import { useState } from "react";
import Link from "next/link";
import { brandTokens } from "@/lib/brand-tokens";
import { useAppStore } from "@/lib/store";
import { useBrands, useSPSScores, useVectorMap } from "@/hooks/use-brands";
import { useAlerts, useAcknowledgeAlert } from "@/hooks/use-alerts";
import { KPICard } from "@/components/kpi-card";
import { VectorScatter } from "@/components/vector-scatter";
import { SeverityBadge } from "@/components/severity-badge";
import { Eyebrow } from "@/components/eyebrow";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function avgSPS(scores: { score: number }[]): string {
  if (!scores.length) return "—";
  const avg = scores.reduce((acc, s) => acc + s.score, 0) / scores.length;
  return `${(avg * 100).toFixed(1)}%`;
}

function formatAlertTime(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Alert row
// ---------------------------------------------------------------------------

function AlertRow({
  alert,
  onAck,
  acking,
}: {
  alert: {
    id: string;
    severity: string;
    message: string;
    alert_type: string;
    acknowledged: boolean;
    created_at: string;
  };
  onAck: (id: string) => void;
  acking: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 12,
        padding: "14px 0",
        borderBottom: `1px solid ${brandTokens.colors.primary10}`,
      }}
    >
      <div style={{ flex: 1 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 5,
          }}
        >
          <SeverityBadge severity={alert.severity} />
          <span
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
            }}
          >
            {alert.alert_type.replace(/_/g, " ")}
          </span>
        </div>
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 12,
            color: brandTokens.colors.dark,
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          {alert.message}
        </p>
        <span
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 10,
            color: brandTokens.colors.mid,
            marginTop: 4,
            display: "block",
          }}
        >
          {formatAlertTime(alert.created_at)}
        </span>
      </div>
      {!alert.acknowledged && (
        <button
          onClick={() => onAck(alert.id)}
          disabled={acking}
          style={{
            background: "none",
            border: `1px solid ${brandTokens.colors.primary30}`,
            borderRadius: 6,
            padding: "4px 10px",
            cursor: acking ? "not-allowed" : "pointer",
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 9,
            letterSpacing: "1px",
            textTransform: "uppercase",
            color: brandTokens.colors.primary60,
            opacity: acking ? 0.5 : 1,
            flexShrink: 0,
          }}
        >
          Ack
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Brand selector
// ---------------------------------------------------------------------------

function BrandSelector({
  brands,
  selectedId,
  onSelect,
}: {
  brands: { id: string; name: string; slug: string }[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        marginBottom: 32,
        alignItems: "center",
      }}
    >
      <span
        style={{
          fontFamily: brandTokens.typography.fontBody,
          fontSize: 9,
          letterSpacing: "2px",
          textTransform: "uppercase",
          color: brandTokens.colors.mid,
          marginRight: 4,
        }}
      >
        Brand
      </span>
      {brands.map((b) => (
        <button
          key={b.id}
          onClick={() => onSelect(b.id)}
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 11,
            padding: "5px 14px",
            borderRadius: 20,
            cursor: "pointer",
            border: `1px solid ${
              selectedId === b.id
                ? brandTokens.colors.primary
                : brandTokens.colors.primary10
            }`,
            backgroundColor:
              selectedId === b.id
                ? brandTokens.colors.primary
                : brandTokens.colors.white,
            color:
              selectedId === b.id
                ? brandTokens.colors.white
                : brandTokens.colors.mid,
            transition: "all 0.15s",
          }}
        >
          {b.name}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { selectedBrandId, setSelectedBrand } = useAppStore();

  const { data: brands = [], isLoading: brandsLoading } = useBrands();
  const activeBrandId = selectedBrandId ?? brands[0]?.id ?? null;

  const { data: spsScores = [] } = useSPSScores(activeBrandId ?? "");
  const { data: vectorMap, isLoading: vectorLoading } = useVectorMap(
    activeBrandId ?? "",
    !!activeBrandId
  );
  const { data: alerts = [], isLoading: alertsLoading } = useAlerts({
    acknowledged: false,
    limit: 20,
  });

  const { mutate: ackAlert, isPending: acking } = useAcknowledgeAlert();

  const activeBrand = brands.find((b) => b.id === activeBrandId);
  const avgScore = avgSPS(spsScores);
  const unackedCount = alerts.filter((a) => !a.acknowledged).length;

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
          Monitor semantic proximity scores, detect hallucinations, and benchmark
          your brand against competitors across every major AI model.
        </p>
      </div>

      {/* KPI summary row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 24,
          marginBottom: 40,
        }}
      >
        <KPICard
          value={brandsLoading ? "…" : String(brands.length)}
          label="Brands Monitored"
          sub="Configured in this org"
        />
        <KPICard
          value={avgScore}
          label="Avg SPS Score"
          sub="Semantic proximity index"
          accentColor={brandTokens.dataSeries[1]}
        />
        <KPICard
          value={brandsLoading ? "…" : String(spsScores.length)}
          label="SPS Data Points"
          sub="Across all intent clusters"
          accentColor={brandTokens.dataSeries[2]}
        />
        <KPICard
          value={alertsLoading ? "…" : String(unackedCount)}
          label="Active Alerts"
          sub="Unacknowledged"
          accentColor={
            unackedCount > 0
              ? brandTokens.status.danger.base
              : brandTokens.status.success.base
          }
        />
      </div>

      {/* Brand selector — only shown when there are brands */}
      {brands.length > 0 && (
        <BrandSelector
          brands={brands}
          selectedId={activeBrandId}
          onSelect={setSelectedBrand}
        />
      )}

      <div
        style={{
          height: 1,
          backgroundColor: brandTokens.colors.primary10,
          marginBottom: 40,
        }}
      />

      {/* Main 2-col layout: Vector map + Alert feed */}
      <div
        style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24 }}
      >
        {/* Vector map */}
        <div style={{ ...brandTokens.card }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: 20,
            }}
          >
            <div>
              <Eyebrow>Vector map</Eyebrow>
              <h2
                style={{
                  fontFamily: brandTokens.typography.fontDisplay,
                  fontSize: 22,
                  fontWeight: 300,
                  color: brandTokens.colors.dark,
                  margin: "6px 0 0",
                }}
              >
                Semantic{" "}
                <em style={{ fontStyle: "italic" }}>position</em>
              </h2>
            </div>
            {activeBrand && (
              <Link
                href={`/brands/${activeBrand.id}`}
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9,
                  letterSpacing: "1.5px",
                  textTransform: "uppercase",
                  color: brandTokens.colors.primary60,
                  textDecoration: "none",
                  border: `1px solid ${brandTokens.colors.primary10}`,
                  borderRadius: 6,
                  padding: "5px 12px",
                }}
              >
                Full view →
              </Link>
            )}
          </div>
          <VectorScatter
            points={vectorMap?.points ?? []}
            isLoading={vectorLoading && !!activeBrandId}
          />
        </div>

        {/* Alert registry */}
        <div style={{ ...brandTokens.card }}>
          <Eyebrow>Alert registry</Eyebrow>
          <h2
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 22,
              fontWeight: 300,
              color: brandTokens.colors.dark,
              margin: "6px 0 20px",
            }}
          >
            Recent{" "}
            <em style={{ fontStyle: "italic" }}>alerts</em>
          </h2>

          {alertsLoading ? (
            <p
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 13,
                color: brandTokens.colors.mid,
              }}
            >
              Loading alerts…
            </p>
          ) : alerts.length === 0 ? (
            <p
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 13,
                color: brandTokens.colors.mid,
                lineHeight: 1.7,
              }}
            >
              No active alerts. Hallucination alerts will appear here after the
              first scan.
            </p>
          ) : (
            <div>
              {alerts.slice(0, 8).map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  onAck={ackAlert}
                  acking={acking}
                />
              ))}
              {alerts.length > 8 && (
                <p
                  style={{
                    fontFamily: brandTokens.typography.fontBody,
                    fontSize: 11,
                    color: brandTokens.colors.mid,
                    marginTop: 12,
                    textAlign: "center",
                  }}
                >
                  +{alerts.length - 8} more alerts
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Brand list — links to detail pages */}
      {brands.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <div
            style={{
              height: 1,
              backgroundColor: brandTokens.colors.primary10,
              marginBottom: 32,
            }}
          />
          <Eyebrow>Monitored brands</Eyebrow>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 16,
              marginTop: 16,
            }}
          >
            {brands.map((brand) => (
              <Link
                key={brand.id}
                href={`/brands/${brand.id}`}
                style={{ textDecoration: "none" }}
              >
                <div
                  style={{
                    ...brandTokens.card,
                    padding: "20px 24px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    transition: "box-shadow 0.15s",
                    cursor: "pointer",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: brandTokens.typography.fontDisplay,
                        fontSize: 17,
                        fontWeight: 400,
                        color: brandTokens.colors.dark,
                        marginBottom: 3,
                      }}
                    >
                      {brand.name}
                    </div>
                    <div
                      style={{
                        fontFamily: brandTokens.typography.fontMono,
                        fontSize: 10,
                        color: brandTokens.colors.mid,
                        letterSpacing: "0.5px",
                      }}
                    >
                      {brand.slug}
                    </div>
                  </div>
                  <span
                    style={{
                      fontFamily: brandTokens.typography.fontBody,
                      fontSize: 18,
                      color: brandTokens.colors.primary30,
                    }}
                  >
                    →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
