"use client";

import { useEffect, useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";

interface AdminStats {
  total_orgs: number;
  active_orgs_7d: number;
  avg_nps: number | null;
  p1_open_bugs: number;
}

interface OrgRow {
  org_id: string;
  name: string;
  email: string;
  plan: string;
  is_demo: boolean;
  onboarding_completed: boolean;
  created_at: string;
  total_spend_usd: number;
  brand_count: number;
  scan_job_count: number;
}

const ADMIN_SECRET = process.env.NEXT_PUBLIC_ADMIN_SECRET ?? "";

async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { "X-Admin-Secret": ADMIN_SECRET } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [orgs, setOrgs] = useState<OrgRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [s, o] = await Promise.all([
          adminFetch<AdminStats>("/api/v1/admin/stats"),
          adminFetch<OrgRow[]>("/api/v1/admin/orgs?demo=false&limit=50"),
        ]);
        setStats(s);
        setOrgs(o);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load admin data.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <PageHeading title="Overview" />

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        <KpiCard label="Total orgs" value={stats?.total_orgs ?? 0} />
        <KpiCard label="New orgs (7d)" value={stats?.active_orgs_7d ?? 0} />
        <KpiCard label="Avg NPS" value={stats?.avg_nps != null ? stats.avg_nps.toFixed(1) : "—"} />
        <KpiCard label="P1 bugs open" value={stats?.p1_open_bugs ?? 0} accent={stats?.p1_open_bugs ? "danger" : "default"} />
      </div>

      {/* Org table */}
      <SectionHeading title="Recent organizations" />
      <div style={{ backgroundColor: "#1e293b", borderRadius: 10, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              {["Organization", "Email", "Plan", "Brands", "Scans", "Spend (USD)", "Onboarded", "Joined"].map((h) => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {orgs.map((org) => (
              <tr key={org.org_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={tdStyle}><span style={{ color: "#fff" }}>{org.name}</span><br /><span style={{ color: "rgba(255,255,255,0.3)", fontSize: 10 }}>{org.org_id}</span></td>
                <td style={tdStyle}>{org.email}</td>
                <td style={tdStyle}><PlanBadge plan={org.plan} /></td>
                <td style={tdStyle}>{org.brand_count}</td>
                <td style={tdStyle}>{org.scan_job_count}</td>
                <td style={tdStyle}>${org.total_spend_usd.toFixed(4)}</td>
                <td style={tdStyle}><StatusDot ok={org.onboarding_completed} /></td>
                <td style={tdStyle}>{new Date(org.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {orgs.length === 0 && (
              <tr><td colSpan={8} style={{ ...tdStyle, textAlign: "center", color: "rgba(255,255,255,0.25)", padding: "32px" }}>No organizations yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-pages (orgs list, scan jobs, costs, NPS) — each is its own file
// ---------------------------------------------------------------------------

function PageHeading({ title }: { title: string }) {
  return (
    <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 28, fontWeight: 300, color: "#fff", marginBottom: 28 }}>
      {title}
    </h1>
  );
}

function SectionHeading({ title }: { title: string }) {
  return (
    <h2 style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "3px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 12, marginTop: 0 }}>
      {title}
    </h2>
  );
}

function KpiCard({ label, value, accent = "default" }: { label: string; value: string | number; accent?: "danger" | "default" }) {
  const valueColor = accent === "danger" && Number(value) > 0 ? brandTokens.status.danger.base : "#fff";
  return (
    <div style={{ backgroundColor: "#1e293b", borderRadius: 10, padding: "20px 22px", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "3px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 10 }}>{label}</div>
      <div style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 32, fontWeight: 300, color: valueColor }}>{value}</div>
    </div>
  );
}

function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    trial: { bg: "rgba(255,255,255,0.08)", text: "rgba(255,255,255,0.5)" },
    beta: { bg: brandTokens.status.strategic.bg, text: brandTokens.status.strategic.base },
    pro: { bg: brandTokens.status.success.bg, text: brandTokens.status.success.base },
  };
  const c = colors[plan] ?? colors.trial;
  return (
    <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 9, fontFamily: brandTokens.typography.fontBody, letterSpacing: "2px", textTransform: "uppercase", backgroundColor: c.bg, color: c.text }}>
      {plan}
    </span>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", backgroundColor: ok ? brandTokens.status.success.base : "rgba(255,255,255,0.2)" }} />
  );
}

function LoadingState() {
  return <div style={{ color: "rgba(255,255,255,0.4)", fontFamily: brandTokens.typography.fontBody, fontSize: 13, padding: 40 }}>Loading…</div>;
}

function ErrorState({ message }: { message: string }) {
  return <div style={{ color: brandTokens.status.danger.base, fontFamily: brandTokens.typography.fontBody, fontSize: 13, padding: 40 }}>Error: {message}</div>;
}

const thStyle: React.CSSProperties = {
  padding: "10px 16px",
  textAlign: "left",
  fontFamily: brandTokens.typography.fontBody,
  fontSize: 9,
  letterSpacing: "2px",
  textTransform: "uppercase",
  color: "rgba(255,255,255,0.3)",
  fontWeight: 500,
};

const tdStyle: React.CSSProperties = {
  padding: "12px 16px",
  fontFamily: brandTokens.typography.fontBody,
  fontSize: 12,
  color: "rgba(255,255,255,0.55)",
  verticalAlign: "middle",
};
