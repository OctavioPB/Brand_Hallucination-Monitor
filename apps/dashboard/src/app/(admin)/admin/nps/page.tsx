"use client";

import { useEffect, useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";

interface NpsRow {
  org_id: string;
  score: number;
  comment: string | null;
  trigger: string;
  created_at: string;
}

const ADMIN_SECRET = process.env.NEXT_PUBLIC_ADMIN_SECRET ?? "change-me-admin-secret";

async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { "X-Admin-Secret": ADMIN_SECRET } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function scoreColor(score: number) {
  if (score >= 9) return brandTokens.status.success.base;
  if (score >= 7) return brandTokens.status.strategic.base;
  return brandTokens.status.danger.base;
}

export default function NpsPage() {
  const [rows, setRows] = useState<NpsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminFetch<NpsRow[]>("/api/v1/admin/nps?limit=500")
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const avg = rows.length > 0 ? rows.reduce((s, r) => s + r.score, 0) / rows.length : null;
  const promoters = rows.filter((r) => r.score >= 9).length;
  const detractors = rows.filter((r) => r.score <= 6).length;
  const nps = rows.length > 0 ? Math.round(((promoters - detractors) / rows.length) * 100) : null;

  return (
    <div>
      <h1 style={h1}>NPS responses</h1>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 28 }}>
        <KpiCard label="Responses" value={rows.length.toString()} />
        <KpiCard label="Avg score" value={avg != null ? avg.toFixed(1) : "—"} />
        <KpiCard label="NPS" value={nps != null ? nps.toString() : "—"} />
        <KpiCard label="Promoters" value={promoters.toString()} />
      </div>

      {loading ? <Loader /> : error ? <Err msg={error} /> : (
        <div style={{ backgroundColor: "#1e293b", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {["Org", "Score", "Comment", "Trigger", "Date"].map((h) => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={td}>{row.org_id}</td>
                  <td style={td}>
                    <span style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 20, fontWeight: 300, color: scoreColor(row.score) }}>
                      {row.score}
                    </span>
                    <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>/10</span>
                  </td>
                  <td style={{ ...td, maxWidth: 300 }}>
                    <span style={{ color: row.comment ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.2)" }}>
                      {row.comment ?? "—"}
                    </span>
                  </td>
                  <td style={td}>
                    <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 9, fontFamily: brandTokens.typography.fontBody, letterSpacing: "1px", textTransform: "uppercase", backgroundColor: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.45)" }}>
                      {row.trigger}
                    </span>
                  </td>
                  <td style={td}>{new Date(row.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={5} style={{ ...td, textAlign: "center", color: "rgba(255,255,255,0.25)", padding: 32 }}>No NPS responses yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ backgroundColor: "#1e293b", borderRadius: 10, padding: "20px 22px", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "3px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 10 }}>{label}</div>
      <div style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 32, fontWeight: 300, color: "#fff" }}>{value}</div>
    </div>
  );
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
