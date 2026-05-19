"use client";

import { useEffect, useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";

interface CostRow {
  org_id: string;
  total_spend_usd: number;
  api_calls: number;
  tokens_total: number;
}

const ADMIN_SECRET = process.env.NEXT_PUBLIC_ADMIN_SECRET ?? "change-me-admin-secret";

async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { "X-Admin-Secret": ADMIN_SECRET } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export default function CostsPage() {
  const [rows, setRows] = useState<CostRow[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    adminFetch<CostRow[]>(`/api/v1/admin/costs?days=${days}`)
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [days]);

  const totalSpend = rows.reduce((s, r) => s + r.total_spend_usd, 0);
  const totalCalls = rows.reduce((s, r) => s + r.api_calls, 0);
  const totalTokens = rows.reduce((s, r) => s + r.tokens_total, 0);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 28 }}>
        <h1 style={h1}>Cost per job type</h1>
        <div style={{ display: "flex", gap: 8 }}>
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 9,
                letterSpacing: "2px",
                textTransform: "uppercase",
                padding: "6px 14px",
                borderRadius: 6,
                border: "none",
                cursor: "pointer",
                backgroundColor: days === d ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.06)",
                color: days === d ? "#fff" : "rgba(255,255,255,0.4)",
              }}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 28 }}>
        <KpiCard label="Total spend" value={`$${totalSpend.toFixed(4)}`} />
        <KpiCard label="API calls" value={totalCalls.toLocaleString()} />
        <KpiCard label="Tokens used" value={totalTokens.toLocaleString()} />
      </div>

      {loading ? <Loader /> : error ? <Err msg={error} /> : (
        <div style={{ backgroundColor: "#1e293b", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {["Job type", "Spend (USD)", "API calls", "Tokens"].map((h) => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.org_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={td}><span style={{ color: "#fff" }}>{row.org_id}</span></td>
                  <td style={td}>${row.total_spend_usd.toFixed(6)}</td>
                  <td style={td}>{row.api_calls.toLocaleString()}</td>
                  <td style={td}>{row.tokens_total.toLocaleString()}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={4} style={{ ...td, textAlign: "center", color: "rgba(255,255,255,0.25)", padding: 32 }}>No cost data for this period.</td></tr>
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
      <div style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 28, fontWeight: 300, color: "#fff" }}>{value}</div>
    </div>
  );
}

function Loader() {
  return <p style={{ color: "rgba(255,255,255,0.4)", fontFamily: brandTokens.typography.fontBody, fontSize: 13, padding: 40 }}>Loading…</p>;
}

function Err({ msg }: { msg: string }) {
  return <p style={{ color: brandTokens.status.danger.base, fontFamily: brandTokens.typography.fontBody, fontSize: 13, padding: 40 }}>Error: {msg}</p>;
}

const h1: React.CSSProperties = { fontFamily: brandTokens.typography.fontDisplay, fontSize: 28, fontWeight: 300, color: "#fff", margin: 0 };
const th: React.CSSProperties = { padding: "10px 16px", textAlign: "left", fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", fontWeight: 500 };
const td: React.CSSProperties = { padding: "12px 16px", fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.55)", verticalAlign: "middle" };
