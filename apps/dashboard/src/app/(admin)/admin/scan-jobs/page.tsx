"use client";

import { useEffect, useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";

interface ScanJobRow {
  job_id: string;
  org_id: string;
  brand_id: string;
  job_type: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

const ADMIN_SECRET = process.env.NEXT_PUBLIC_ADMIN_SECRET ?? "change-me-admin-secret";

async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { "X-Admin-Secret": ADMIN_SECRET } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  completed: { bg: brandTokens.status.success.bg, text: brandTokens.status.success.base },
  running: { bg: brandTokens.status.strategic.bg, text: brandTokens.status.strategic.base },
  failed: { bg: brandTokens.status.danger.bg, text: brandTokens.status.danger.base },
  pending: { bg: "rgba(255,255,255,0.06)", text: "rgba(255,255,255,0.4)" },
};

export default function ScanJobsPage() {
  const [jobs, setJobs] = useState<ScanJobRow[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    const qs = statusFilter ? `?status_filter=${statusFilter}&limit=200` : "?limit=200";
    adminFetch<ScanJobRow[]>(`/api/v1/admin/scan-jobs${qs}`)
      .then(setJobs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  const filters = ["", "pending", "running", "completed", "failed"];

  return (
    <div>
      <h1 style={h1}>Scan jobs</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "2px",
              textTransform: "uppercase",
              padding: "6px 14px",
              borderRadius: 6,
              border: "none",
              cursor: "pointer",
              backgroundColor: statusFilter === f ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.06)",
              color: statusFilter === f ? "#fff" : "rgba(255,255,255,0.4)",
            }}
          >
            {f || "All"}
          </button>
        ))}
      </div>

      {loading ? <Loader /> : error ? <Err msg={error} /> : (
        <div style={{ backgroundColor: "#1e293b", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {["Job ID", "Org", "Brand", "Type", "Status", "Created", "Completed"].map((h) => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const sc = STATUS_COLORS[job.status] ?? STATUS_COLORS.pending;
                return (
                  <tr key={job.job_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={td}><span style={{ fontFamily: brandTokens.typography.fontMono, fontSize: 10 }}>{job.job_id.slice(0, 8)}…</span></td>
                    <td style={td}>{job.org_id}</td>
                    <td style={td}><span style={{ fontFamily: brandTokens.typography.fontMono, fontSize: 10 }}>{job.brand_id.slice(0, 8)}…</span></td>
                    <td style={td}>{job.job_type}</td>
                    <td style={td}>
                      <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 9, fontFamily: brandTokens.typography.fontBody, letterSpacing: "2px", textTransform: "uppercase", backgroundColor: sc.bg, color: sc.text }}>
                        {job.status}
                      </span>
                    </td>
                    <td style={td}>{new Date(job.created_at).toLocaleString()}</td>
                    <td style={td}>{job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}</td>
                  </tr>
                );
              })}
              {jobs.length === 0 && (
                <tr><td colSpan={7} style={{ ...td, textAlign: "center", color: "rgba(255,255,255,0.25)", padding: 32 }}>No scan jobs.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
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
