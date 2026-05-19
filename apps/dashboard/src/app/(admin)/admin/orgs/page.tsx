"use client";

import { useEffect, useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";

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

async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { "X-Admin-Secret": ADMIN_SECRET } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export default function OrgsPage() {
  const [orgs, setOrgs] = useState<OrgRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminFetch<OrgRow[]>("/api/v1/admin/orgs?limit=200")
      .then(setOrgs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;
  if (error) return <Err msg={error} />;

  return (
    <div>
      <h1 style={h1}>Organizations</h1>
      <div style={{ backgroundColor: "#1e293b", borderRadius: 10, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              {["Organization", "Email", "Plan", "Demo", "Brands", "Scans", "Spend (USD)", "Onboarded", "Joined"].map((h) => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {orgs.map((org) => (
              <tr key={org.org_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={td}>
                  <span style={{ color: "#fff" }}>{org.name}</span>
                  <br />
                  <span style={{ color: "rgba(255,255,255,0.3)", fontSize: 10 }}>{org.org_id}</span>
                </td>
                <td style={td}>{org.email}</td>
                <td style={td}><PlanBadge plan={org.plan} /></td>
                <td style={td}>{org.is_demo ? "✓" : "—"}</td>
                <td style={td}>{org.brand_count}</td>
                <td style={td}>{org.scan_job_count}</td>
                <td style={td}>${org.total_spend_usd.toFixed(4)}</td>
                <td style={td}><Dot ok={org.onboarding_completed} /></td>
                <td style={td}>{new Date(org.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {orgs.length === 0 && (
              <tr><td colSpan={9} style={{ ...td, textAlign: "center", color: "rgba(255,255,255,0.25)", padding: 32 }}>No organizations.</td></tr>
            )}
          </tbody>
        </table>
      </div>
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

function Dot({ ok }: { ok: boolean }) {
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", backgroundColor: ok ? brandTokens.status.success.base : "rgba(255,255,255,0.2)" }} />;
}

function Loader() {
  return <p style={{ color: "rgba(255,255,255,0.4)", fontFamily: brandTokens.typography.fontBody, fontSize: 13, padding: 40 }}>Loading…</p>;
}

function Err({ msg }: { msg: string }) {
  return <p style={{ color: brandTokens.status.danger.base, fontFamily: brandTokens.typography.fontBody, fontSize: 13, padding: 40 }}>Error: {msg}</p>;
}

const h1: React.CSSProperties = { fontFamily: brandTokens.typography.fontDisplay, fontSize: 28, fontWeight: 300, color: "#fff", marginBottom: 28 };
const th: React.CSSProperties = { padding: "10px 16px", textAlign: "left", fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", fontWeight: 500 };
const td: React.CSSProperties = { padding: "12px 16px", fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.55)", verticalAlign: "middle" };
