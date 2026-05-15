"use client";

import { useState } from "react";
import Link from "next/link";
import { brandTokens } from "@/lib/brand-tokens";
import { useBrands } from "@/hooks/use-brands";
import {
  useReports,
  useGenerateReport,
  useAlertRules,
  useCreateAlertRule,
  useDeleteAlertRule,
  useToggleAlertRule,
} from "@/hooks/use-reports";
import { KPICard } from "@/components/kpi-card";
import { SeverityBadge } from "@/components/severity-badge";
import { Eyebrow } from "@/components/eyebrow";
import type { AlertRuleCreate } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const CLUSTER_LABELS: Record<string, string> = {
  reliability: "Reliability",
  innovation: "Innovation",
  pricing_value: "Pricing & Value",
  market_leadership: "Market Leadership",
  compliance: "Compliance",
  support_quality: "Support Quality",
};

// ---------------------------------------------------------------------------
// Report row
// ---------------------------------------------------------------------------

function ReportRow({
  report,
}: {
  report: {
    id: string;
    title: string;
    report_type: string;
    brand_id: string;
    week_start: string | null;
    generated_at: string;
    has_pdf: boolean;
  };
}) {
  const typeLabel =
    report.report_type === "weekly" ? "Weekly" : "On-Demand";
  const typeColor =
    report.report_type === "weekly"
      ? brandTokens.status.primary.base
      : brandTokens.dataSeries[2];

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 16,
        padding: "16px 0",
        borderBottom: `1px solid ${brandTokens.colors.primary10}`,
      }}
    >
      <div style={{ flex: 1 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 4,
          }}
        >
          <span
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: typeColor,
              fontWeight: 600,
            }}
          >
            {typeLabel}
          </span>
          {report.week_start && (
            <span
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 10,
                color: brandTokens.colors.mid,
              }}
            >
              · week of {formatDate(report.week_start)}
            </span>
          )}
        </div>
        <div
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.dark,
            fontWeight: 500,
          }}
        >
          {report.title}
        </div>
        <div
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 10,
            color: brandTokens.colors.mid,
            marginTop: 2,
          }}
        >
          Generated {formatDate(report.generated_at)}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <Link
          href={`/reports/${report.id}`}
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 9,
            letterSpacing: "1px",
            textTransform: "uppercase",
            color: brandTokens.colors.primary60,
            textDecoration: "none",
            border: `1px solid ${brandTokens.colors.primary10}`,
            borderRadius: 6,
            padding: "4px 10px",
          }}
        >
          View
        </Link>
        {report.has_pdf && (
          <a
            href={`/api/v1/reports/${report.id}/download`}
            download
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1px",
              textTransform: "uppercase",
              color: brandTokens.colors.white,
              textDecoration: "none",
              backgroundColor: brandTokens.colors.gold,
              borderRadius: 6,
              padding: "4px 10px",
            }}
          >
            PDF
          </a>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert rule row
// ---------------------------------------------------------------------------

function AlertRuleRow({
  rule,
  onDelete,
  onToggle,
  deleting,
  toggling,
}: {
  rule: {
    id: string;
    rule_type: string;
    cluster_slug: string | null;
    threshold: number | null;
    competitor_name: string | null;
    severity: string;
    is_active: boolean;
    last_triggered_at: string | null;
  };
  onDelete: (id: string) => void;
  onToggle: (id: string, active: boolean) => void;
  deleting: boolean;
  toggling: boolean;
}) {
  const description =
    rule.rule_type === "sps_threshold"
      ? `SPS for "${rule.cluster_slug}" < ${((rule.threshold ?? 0) * 100).toFixed(0)}%`
      : `"${rule.competitor_name}" may outrank in ${rule.cluster_slug}`;

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        padding: "14px 0",
        borderBottom: `1px solid ${brandTokens.colors.primary10}`,
        opacity: rule.is_active ? 1 : 0.5,
      }}
    >
      <div style={{ flex: 1 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 3,
          }}
        >
          <SeverityBadge severity={rule.severity} />
          <span
            style={{
              fontFamily: brandTokens.typography.fontMono,
              fontSize: 10,
              color: brandTokens.colors.mid,
            }}
          >
            {rule.rule_type}
          </span>
        </div>
        <div
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 12,
            color: brandTokens.colors.dark,
          }}
        >
          {description}
        </div>
        {rule.last_triggered_at && (
          <div
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 10,
              color: brandTokens.colors.mid,
              marginTop: 2,
            }}
          >
            Last fired: {formatDate(rule.last_triggered_at)}
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <button
          onClick={() => onToggle(rule.id, !rule.is_active)}
          disabled={toggling}
          style={{
            background: "none",
            border: `1px solid ${brandTokens.colors.primary10}`,
            borderRadius: 6,
            padding: "4px 10px",
            cursor: toggling ? "not-allowed" : "pointer",
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 9,
            letterSpacing: "1px",
            textTransform: "uppercase",
            color: brandTokens.colors.primary60,
          }}
        >
          {rule.is_active ? "Pause" : "Resume"}
        </button>
        <button
          onClick={() => onDelete(rule.id)}
          disabled={deleting}
          style={{
            background: "none",
            border: `1px solid ${brandTokens.status.danger.base}`,
            borderRadius: 6,
            padding: "4px 10px",
            cursor: deleting ? "not-allowed" : "pointer",
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 9,
            letterSpacing: "1px",
            textTransform: "uppercase",
            color: brandTokens.status.danger.base,
          }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// New rule form
// ---------------------------------------------------------------------------

function NewRuleForm({
  brands,
  onCreate,
  creating,
}: {
  brands: { id: string; name: string }[];
  onCreate: (payload: AlertRuleCreate) => void;
  creating: boolean;
}) {
  const [brandId, setBrandId] = useState(brands[0]?.id ?? "");
  const [ruleType, setRuleType] = useState<"sps_threshold" | "competitor_rank">("sps_threshold");
  const [cluster, setCluster] = useState("reliability");
  const [threshold, setThreshold] = useState("0.55");
  const [competitor, setCompetitor] = useState("");
  const [severity, setSeverity] = useState("HIGH");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: AlertRuleCreate = {
      brand_id: brandId,
      rule_type: ruleType,
      cluster_slug: cluster,
      severity,
      ...(ruleType === "sps_threshold"
        ? { threshold: parseFloat(threshold) }
        : { competitor_name: competitor }),
    };
    onCreate(payload);
  };

  const inputStyle: React.CSSProperties = {
    fontFamily: brandTokens.typography.fontBody,
    fontSize: 11,
    padding: "6px 10px",
    border: `1px solid ${brandTokens.colors.primary10}`,
    borderRadius: 6,
    backgroundColor: brandTokens.colors.white,
    color: brandTokens.colors.dark,
    width: "100%",
    boxSizing: "border-box",
  };

  return (
    <form onSubmit={handleSubmit}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <div>
          <label
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
              display: "block",
              marginBottom: 4,
            }}
          >
            Brand
          </label>
          <select
            value={brandId}
            onChange={(e) => setBrandId(e.target.value)}
            style={inputStyle}
          >
            {brands.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
              display: "block",
              marginBottom: 4,
            }}
          >
            Rule Type
          </label>
          <select
            value={ruleType}
            onChange={(e) =>
              setRuleType(e.target.value as "sps_threshold" | "competitor_rank")
            }
            style={inputStyle}
          >
            <option value="sps_threshold">SPS Threshold</option>
            <option value="competitor_rank">Competitor Rank</option>
          </select>
        </div>
        <div>
          <label
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
              display: "block",
              marginBottom: 4,
            }}
          >
            Intent Cluster
          </label>
          <select value={cluster} onChange={(e) => setCluster(e.target.value)} style={inputStyle}>
            {Object.entries(CLUSTER_LABELS).map(([slug, label]) => (
              <option key={slug} value={slug}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {ruleType === "sps_threshold" ? (
          <div>
            <label
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 9,
                letterSpacing: "1.5px",
                textTransform: "uppercase",
                color: brandTokens.colors.mid,
                display: "block",
                marginBottom: 4,
              }}
            >
              Threshold (0–1)
            </label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              style={inputStyle}
            />
          </div>
        ) : (
          <div>
            <label
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 9,
                letterSpacing: "1.5px",
                textTransform: "uppercase",
                color: brandTokens.colors.mid,
                display: "block",
                marginBottom: 4,
              }}
            >
              Competitor Name
            </label>
            <input
              type="text"
              value={competitor}
              onChange={(e) => setCompetitor(e.target.value)}
              placeholder="e.g. RivalCorp"
              style={inputStyle}
            />
          </div>
        )}
        <div>
          <label
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
              display: "block",
              marginBottom: 4,
            }}
          >
            Severity
          </label>
          <select value={severity} onChange={(e) => setSeverity(e.target.value)} style={inputStyle}>
            {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>
      <button
        type="submit"
        disabled={creating}
        style={{
          fontFamily: brandTokens.typography.fontBody,
          fontSize: 10,
          letterSpacing: "1.5px",
          textTransform: "uppercase",
          backgroundColor: brandTokens.colors.primary,
          color: brandTokens.colors.white,
          border: "none",
          borderRadius: 6,
          padding: "8px 20px",
          cursor: creating ? "not-allowed" : "pointer",
          opacity: creating ? 0.6 : 1,
        }}
      >
        {creating ? "Creating…" : "Create Rule"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ReportsPage() {
  const [showNewRuleForm, setShowNewRuleForm] = useState(false);
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);

  const { data: brands = [] } = useBrands();
  const activeBrandId = selectedBrandId ?? brands[0]?.id ?? null;

  const { data: reports = [], isLoading: reportsLoading } = useReports({
    brand_id: activeBrandId ?? undefined,
    limit: 20,
  });
  const { data: alertRules = [], isLoading: rulesLoading } = useAlertRules({
    brand_id: activeBrandId ?? undefined,
  });

  const { mutate: generateReport, isPending: generating } = useGenerateReport();
  const { mutate: createRule, isPending: creatingRule } = useCreateAlertRule();
  const { mutate: deleteRule, isPending: deletingRule } = useDeleteAlertRule();
  const { mutate: toggleRule, isPending: togglingRule } = useToggleAlertRule();

  const activeRules = alertRules.filter((r) => r.is_active).length;

  return (
    <div style={{ maxWidth: 1300, margin: "0 auto", padding: "56px 48px" }}>
      {/* Hero banner */}
      <div
        style={{
          ...brandTokens.heroSection,
          borderRadius: 14,
          padding: "48px",
          marginBottom: 40,
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
          Reports & Alerts
        </p>
        <h1
          style={{
            fontFamily: brandTokens.typography.fontDisplay,
            fontSize: 32,
            fontWeight: 300,
            color: "#ffffff",
            lineHeight: 1.3,
            marginBottom: 8,
          }}
        >
          Brand safety{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>
            reports
          </em>
        </h1>
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: "rgba(255,255,255,0.6)",
            lineHeight: 1.7,
            maxWidth: 520,
          }}
        >
          Weekly PDF reports delivered to your inbox. Alert rules that fire when
          AI models drift away from your brand truth.
        </p>
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
          value={String(reports.length)}
          label="Reports Generated"
          sub="This org"
        />
        <KPICard
          value={String(alertRules.length)}
          label="Alert Rules"
          sub={`${activeRules} active`}
          accentColor={brandTokens.dataSeries[2]}
        />
        <KPICard
          value={reports.filter((r) => r.has_pdf).length.toString()}
          label="PDFs Available"
          sub="Download any time"
          accentColor={brandTokens.colors.gold}
        />
      </div>

      {/* Brand filter */}
      {brands.length > 1 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 32, alignItems: "center" }}>
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
            Filter
          </span>
          <button
            onClick={() => setSelectedBrandId(null)}
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 11,
              padding: "5px 14px",
              borderRadius: 20,
              cursor: "pointer",
              border: `1px solid ${!activeBrandId ? brandTokens.colors.primary : brandTokens.colors.primary10}`,
              backgroundColor: !activeBrandId ? brandTokens.colors.primary : brandTokens.colors.white,
              color: !activeBrandId ? brandTokens.colors.white : brandTokens.colors.mid,
            }}
          >
            All brands
          </button>
          {brands.map((b) => (
            <button
              key={b.id}
              onClick={() => setSelectedBrandId(b.id)}
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 11,
                padding: "5px 14px",
                borderRadius: 20,
                cursor: "pointer",
                border: `1px solid ${activeBrandId === b.id ? brandTokens.colors.primary : brandTokens.colors.primary10}`,
                backgroundColor:
                  activeBrandId === b.id ? brandTokens.colors.primary : brandTokens.colors.white,
                color: activeBrandId === b.id ? brandTokens.colors.white : brandTokens.colors.mid,
              }}
            >
              {b.name}
            </button>
          ))}
        </div>
      )}

      {/* Main 2-col layout */}
      <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 32 }}>
        {/* Reports archive */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: 20,
            }}
          >
            <div>
              <Eyebrow>Report Archive</Eyebrow>
              <h2
                style={{
                  fontFamily: brandTokens.typography.fontDisplay,
                  fontSize: 22,
                  fontWeight: 300,
                  color: brandTokens.colors.dark,
                  margin: "4px 0 0",
                }}
              >
                Generated{" "}
                <em style={{ fontStyle: "italic" }}>reports</em>
              </h2>
            </div>
            {activeBrandId && (
              <button
                onClick={() =>
                  generateReport({ brandId: activeBrandId })
                }
                disabled={generating}
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9,
                  letterSpacing: "1.5px",
                  textTransform: "uppercase",
                  backgroundColor: brandTokens.colors.gold,
                  color: brandTokens.colors.white,
                  border: "none",
                  borderRadius: 6,
                  padding: "7px 14px",
                  cursor: generating ? "not-allowed" : "pointer",
                  opacity: generating ? 0.6 : 1,
                }}
              >
                {generating ? "Generating…" : "Generate Report"}
              </button>
            )}
          </div>

          <div style={{ ...brandTokens.card, padding: "8px 24px" }}>
            {reportsLoading ? (
              <p
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 13,
                  color: brandTokens.colors.mid,
                  padding: "16px 0",
                }}
              >
                Loading reports…
              </p>
            ) : reports.length === 0 ? (
              <p
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 13,
                  color: brandTokens.colors.mid,
                  padding: "24px 0",
                  textAlign: "center",
                  lineHeight: 1.7,
                }}
              >
                No reports yet — generate one manually or wait for the weekly DAG
                to run on Sunday at 08:00 UTC.
              </p>
            ) : (
              reports.map((r) => <ReportRow key={r.id} report={r} />)
            )}
          </div>
        </div>

        {/* Alert rules */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              marginBottom: 20,
            }}
          >
            <div>
              <Eyebrow>Alert Rules</Eyebrow>
              <h2
                style={{
                  fontFamily: brandTokens.typography.fontDisplay,
                  fontSize: 22,
                  fontWeight: 300,
                  color: brandTokens.colors.dark,
                  margin: "4px 0 0",
                }}
              >
                Threshold{" "}
                <em style={{ fontStyle: "italic" }}>rules</em>
              </h2>
            </div>
            {activeBrandId && (
              <button
                onClick={() => setShowNewRuleForm((v) => !v)}
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9,
                  letterSpacing: "1.5px",
                  textTransform: "uppercase",
                  background: "none",
                  border: `1px solid ${brandTokens.colors.primary10}`,
                  borderRadius: 6,
                  padding: "5px 12px",
                  cursor: "pointer",
                  color: brandTokens.colors.primary60,
                }}
              >
                {showNewRuleForm ? "Cancel" : "+ New Rule"}
              </button>
            )}
          </div>

          {showNewRuleForm && activeBrandId && (
            <div
              style={{
                ...brandTokens.card,
                marginBottom: 16,
                padding: "20px 24px",
                borderLeft: `3px solid ${brandTokens.colors.gold}`,
              }}
            >
              <p
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 11,
                  color: brandTokens.colors.mid,
                  marginBottom: 16,
                }}
              >
                Rules fire an alert when the condition is met. They respect a
                60-minute cooldown between firings.
              </p>
              <NewRuleForm
                brands={brands.filter((b) => !activeBrandId || b.id === activeBrandId)}
                onCreate={(payload) => {
                  createRule(payload);
                  setShowNewRuleForm(false);
                }}
                creating={creatingRule}
              />
            </div>
          )}

          <div style={{ ...brandTokens.card, padding: "8px 24px" }}>
            {rulesLoading ? (
              <p
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 13,
                  color: brandTokens.colors.mid,
                  padding: "16px 0",
                }}
              >
                Loading rules…
              </p>
            ) : alertRules.length === 0 ? (
              <p
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 13,
                  color: brandTokens.colors.mid,
                  padding: "24px 0",
                  textAlign: "center",
                  lineHeight: 1.7,
                }}
              >
                No alert rules configured. Create one to get notified when SPS
                drops below a threshold.
              </p>
            ) : (
              alertRules.map((rule) => (
                <AlertRuleRow
                  key={rule.id}
                  rule={rule}
                  onDelete={(id) => deleteRule(id)}
                  onToggle={(id, active) => toggleRule({ ruleId: id, isActive: active })}
                  deleting={deletingRule}
                  toggling={togglingRule}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
