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

const ADMIN_SECRET = process.env.NEXT_PUBLIC_ADMIN_SECRET ?? "change-me-admin-secret";

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "X-Admin-Secret": ADMIN_SECRET, ...(init?.headers ?? {}) },
  });
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

      {/* Data management */}
      <DataManagement />

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
// Data management panel
// ---------------------------------------------------------------------------

function DataManagement() {
  const [clearState, setClearState] = useState<"idle" | "confirming" | "loading" | "done" | "error">("idle");
  const [seedState, setSeedState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [clearMsg, setClearMsg] = useState("");
  const [seedMsg, setSeedMsg] = useState("");

  async function handleClear() {
    if (clearState === "idle") { setClearState("confirming"); return; }
    if (clearState !== "confirming") return;
    setClearState("loading");
    try {
      await adminFetch("/api/v1/admin/db/clear", { method: "POST" });
      setClearState("done");
      setClearMsg("All data cleared. Reload the page.");
    } catch (e) {
      setClearState("error");
      setClearMsg(e instanceof Error ? e.message : "Failed");
    }
  }

  async function handleSeed() {
    setSeedState("loading");
    try {
      const res = await adminFetch<{ status: string }>("/api/v1/admin/db/seed", { method: "POST" });
      setSeedState("done");
      setSeedMsg(`Done — status: ${res.status}. Reload the dashboard.`);
    } catch (e) {
      setSeedState("error");
      setSeedMsg(e instanceof Error ? e.message : "Failed");
    }
  }

  const panelStyle: React.CSSProperties = {
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: "24px 28px",
    border: "1px solid rgba(255,255,255,0.06)",
    marginBottom: 32,
  };

  const btnBase: React.CSSProperties = {
    fontFamily: brandTokens.typography.fontBody,
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: "2px",
    textTransform: "uppercase",
    border: "none",
    borderRadius: 8,
    padding: "10px 20px",
    cursor: "pointer",
  };

  return (
    <div style={panelStyle}>
      <h2 style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "3px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 20, marginTop: 0 }}>
        Data management
      </h2>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Clear database */}
        <div style={{ backgroundColor: "#0f172a", borderRadius: 8, padding: "20px 22px", border: `1px solid ${clearState === "confirming" ? brandTokens.status.danger.base : "rgba(255,255,255,0.06)"}` }}>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: "#fff", fontWeight: 500, marginBottom: 6 }}>
            Clear database
          </p>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.45)", lineHeight: 1.6, marginBottom: 16 }}>
            Deletes all rows from every table — orgs, brands, SPS scores, alerts, API keys. Schema is preserved.
          </p>

          {clearState === "confirming" && (
            <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: brandTokens.status.danger.base, marginBottom: 12 }}>
              ⚠ This cannot be undone. Click again to confirm.
            </p>
          )}
          {(clearState === "done" || clearState === "error") && (
            <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: clearState === "done" ? brandTokens.status.success.base : brandTokens.status.danger.base, marginBottom: 12 }}>
              {clearMsg}
            </p>
          )}

          <button
            onClick={handleClear}
            disabled={clearState === "loading" || clearState === "done"}
            style={{
              ...btnBase,
              backgroundColor: clearState === "confirming" ? brandTokens.status.danger.base : "rgba(224,52,72,0.15)",
              color: clearState === "confirming" ? "#fff" : brandTokens.status.danger.base,
              opacity: clearState === "loading" || clearState === "done" ? 0.5 : 1,
              cursor: clearState === "loading" || clearState === "done" ? "not-allowed" : "pointer",
            }}
          >
            {clearState === "loading" ? "Clearing…" : clearState === "confirming" ? "⚠ Confirm clear" : clearState === "done" ? "Cleared" : "Clear database"}
          </button>
          {clearState === "confirming" && (
            <button onClick={() => setClearState("idle")} style={{ ...btnBase, backgroundColor: "transparent", color: "rgba(255,255,255,0.35)", marginLeft: 8 }}>
              Cancel
            </button>
          )}
        </div>

        {/* Seed AcmeCorp */}
        <div style={{ backgroundColor: "#0f172a", borderRadius: 8, padding: "20px 22px", border: "1px solid rgba(255,255,255,0.06)" }}>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: "#fff", fontWeight: 500, marginBottom: 6 }}>
            Seed AcmeCorp demo
          </p>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.45)", lineHeight: 1.6, marginBottom: 16 }}>
            Creates (or re-creates) the AcmeCorp demo org with SPS scores, hallucination probes, and alerts pre-populated.
          </p>

          {(seedState === "done" || seedState === "error") && (
            <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: seedState === "done" ? brandTokens.status.success.base : brandTokens.status.danger.base, marginBottom: 12 }}>
              {seedMsg}
            </p>
          )}

          <button
            onClick={handleSeed}
            disabled={seedState === "loading"}
            style={{
              ...btnBase,
              backgroundColor: "rgba(39,185,124,0.15)",
              color: brandTokens.status.success.base,
              opacity: seedState === "loading" ? 0.5 : 1,
              cursor: seedState === "loading" ? "not-allowed" : "pointer",
            }}
          >
            {seedState === "loading" ? "Seeding…" : seedState === "done" ? "✓ Seeded" : "Seed AcmeCorp data"}
          </button>
          {seedState === "done" && (
            <button onClick={() => setSeedState("idle")} style={{ ...btnBase, backgroundColor: "transparent", color: "rgba(255,255,255,0.35)", marginLeft: 8 }}>
              Reset
            </button>
          )}
        </div>
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
