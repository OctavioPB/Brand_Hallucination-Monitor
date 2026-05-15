import { brandTokens } from "@/lib/brand-tokens";

interface ChangelogEntry {
  version: string;
  date: string;
  type: "feature" | "fix" | "improvement" | "security";
  title: string;
  description: string;
}

const CHANGELOG: ChangelogEntry[] = [
  {
    version: "0.10.0",
    date: "2026-05-15",
    type: "feature",
    title: "Beta Launch — self-serve onboarding",
    description:
      "Self-serve signup flow with multi-step brand setup wizard. Interactive product tour (Shepherd.js). Sample data mode for evaluation. Onboarding email sequence (D+0, D+3, D+7).",
  },
  {
    version: "0.10.0",
    date: "2026-05-15",
    type: "feature",
    title: "Internal admin panel",
    description:
      "Internal /admin dashboard for org management, scan job oversight, per-org cost aggregation, and NPS response tracking.",
  },
  {
    version: "0.10.0",
    date: "2026-05-15",
    type: "security",
    title: "GDPR right-to-erasure endpoint",
    description:
      "DELETE /api/v1/organizations/{id} cascades all org data: brands, scan jobs, reports, costs, API keys. Qdrant and Neo4j vectors deleted best-effort.",
  },
  {
    version: "0.9.0",
    date: "2026-05-14",
    type: "improvement",
    title: "Performance & cost optimization",
    description:
      "Vector map API cached in Redis (1h TTL, < 200ms P95). Tiered probing: GPT-4o-mini daily, Gemini 1.5 Pro weekly. Hard daily budget cap via CostGuard. Qdrant scalar INT8 quantization (4x storage reduction).",
  },
  {
    version: "0.9.0",
    date: "2026-05-14",
    type: "feature",
    title: "Circuit breakers on external APIs",
    description:
      "Circuit breakers (tenacity + Redis) on OpenAI, Slack, and Resend — prevents cascade failures when upstream APIs degrade. Idempotent Kafka consumers with 48h Redis deduplication guard.",
  },
  {
    version: "0.9.0",
    date: "2026-05-14",
    type: "improvement",
    title: "Observability stack",
    description:
      "Prometheus metrics endpoint. Grafana dashboards for Kafka lag, embedding costs, and Airflow DAG health. Sentry integration (backend + frontend). On-call runbooks added to docs/runbooks/.",
  },
  {
    version: "0.8.0",
    date: "2026-05-14",
    type: "feature",
    title: "Brand Safety Reports & Alerts",
    description:
      "PDF report generation via ReportLab. Alert rules engine with SPS threshold, competitor rank, and cooldown logic. Slack Block Kit + Resend email + HMAC webhook delivery. Weekly Airflow report digest.",
  },
  {
    version: "0.7.0",
    date: "2026-05-13",
    type: "feature",
    title: "Multi-tenant dashboard MVP",
    description:
      "Interactive vector map (t-SNE scatter plot). SPS score cards. Hallucination feed. Competitor benchmark table. Full API layer with per-org RLS.",
  },
];

const TYPE_COLORS: Record<ChangelogEntry["type"], { bg: string; text: string; label: string }> = {
  feature:     { bg: brandTokens.status.primary.bg,   text: brandTokens.status.primary.base,   label: "Feature" },
  fix:         { bg: brandTokens.status.danger.bg,    text: brandTokens.status.danger.base,    label: "Fix" },
  improvement: { bg: brandTokens.status.success.bg,   text: brandTokens.status.success.base,   label: "Improvement" },
  security:    { bg: brandTokens.status.warning.bg,   text: brandTokens.status.warning.base,   label: "Security" },
};

export default function ChangelogPage() {
  // Group by version
  const versions = Array.from(new Set(CHANGELOG.map((e) => e.version)));

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "48px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 48 }}>
        <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "4px", textTransform: "uppercase", color: brandTokens.colors.gold, marginBottom: 12 }}>
          Changelog
        </div>
        <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 36, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 12 }}>
          What&apos;s new in hallucin8
        </h1>
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 14, color: brandTokens.colors.mid, lineHeight: 1.75 }}>
          A running record of features, improvements, and security updates.
          Subscribe to the Slack #product-updates channel for real-time notifications.
        </p>
      </div>

      {/* Timeline */}
      <div style={{ position: "relative" }}>
        {/* Vertical line */}
        <div style={{ position: "absolute", left: 7, top: 0, bottom: 0, width: 1, backgroundColor: brandTokens.colors.primary10 }} />

        {versions.map((version) => {
          const entries = CHANGELOG.filter((e) => e.version === version);
          const date = entries[0].date;
          return (
            <div key={version} style={{ position: "relative", paddingLeft: 36, marginBottom: 48 }}>
              {/* Dot */}
              <div style={{
                position: "absolute", left: 0, top: 4,
                width: 14, height: 14, borderRadius: "50%",
                backgroundColor: brandTokens.colors.primary,
                border: `2px solid ${brandTokens.colors.light}`,
                zIndex: 1,
              }} />

              {/* Version header */}
              <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 20 }}>
                <span style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 22, fontWeight: 300, color: brandTokens.colors.dark }}>
                  v{version}
                </span>
                <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 11, color: brandTokens.colors.mid }}>
                  {new Date(date).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
                </span>
              </div>

              {/* Entries */}
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {entries.map((entry, i) => {
                  const tc = TYPE_COLORS[entry.type];
                  return (
                    <div key={i} style={{ backgroundColor: brandTokens.colors.white, borderRadius: 10, padding: "18px 20px", boxShadow: "0 1px 3px rgba(0,51,102,0.07)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                        <span style={{ padding: "2px 8px", borderRadius: 4, backgroundColor: tc.bg, color: tc.text, fontFamily: brandTokens.typography.fontBody, fontSize: 9, fontWeight: 500, letterSpacing: "2px", textTransform: "uppercase" }}>
                          {tc.label}
                        </span>
                        <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, fontWeight: 600, color: brandTokens.colors.dark }}>
                          {entry.title}
                        </span>
                      </div>
                      <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid, lineHeight: 1.7, margin: 0 }}>
                        {entry.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
