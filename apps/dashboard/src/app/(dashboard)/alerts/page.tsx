"use client";

import { useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";
import { useAlerts, useAcknowledgeAlert } from "@/hooks/use-alerts";
import { SeverityBadge } from "@/components/severity-badge";
import { Eyebrow } from "@/components/eyebrow";

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function AlertsPage() {
  const [severityFilter, setSeverityFilter] = useState<string | undefined>();
  const [showAcked, setShowAcked] = useState(false);

  const { data: alerts = [], isLoading } = useAlerts({
    severity: severityFilter,
    acknowledged: showAcked ? undefined : false,
    limit: 100,
  });

  const { mutate: ackAlert, isPending: acking } = useAcknowledgeAlert();

  const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "56px 48px" }}>
      {/* Hero */}
      <div style={{ ...brandTokens.heroSection, borderRadius: 14, padding: "48px", marginBottom: 40 }}>
        <Eyebrow light>Alert registry</Eyebrow>
        <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 32, fontWeight: 300, color: "#fff", marginTop: 10 }}>
          Brand safety{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>alerts</em>
        </h1>
        <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: "rgba(255,255,255,0.55)", marginTop: 8, lineHeight: 1.7 }}>
          Hallucination detections, competitor confusion events, and SPS threshold breaches.
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 24, alignItems: "center" }}>
        <button
          onClick={() => setSeverityFilter(undefined)}
          style={{
            fontFamily: brandTokens.typography.fontBody, fontSize: 10, letterSpacing: "1.5px",
            textTransform: "uppercase", padding: "5px 14px", borderRadius: 20, cursor: "pointer",
            border: `1px solid ${!severityFilter ? brandTokens.colors.primary : brandTokens.colors.primary10}`,
            backgroundColor: !severityFilter ? brandTokens.colors.primary : brandTokens.colors.white,
            color: !severityFilter ? "#fff" : brandTokens.colors.mid,
          }}
        >
          All
        </button>
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setSeverityFilter(severityFilter === s ? undefined : s)}
            style={{
              fontFamily: brandTokens.typography.fontBody, fontSize: 10, letterSpacing: "1.5px",
              textTransform: "uppercase", padding: "5px 14px", borderRadius: 20, cursor: "pointer",
              border: `1px solid ${severityFilter === s ? brandTokens.colors.primary : brandTokens.colors.primary10}`,
              backgroundColor: severityFilter === s ? brandTokens.colors.primary : brandTokens.colors.white,
              color: severityFilter === s ? "#fff" : brandTokens.colors.mid,
            }}
          >
            {s}
          </button>
        ))}

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 11, color: brandTokens.colors.mid, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={showAcked} onChange={(e) => setShowAcked(e.target.checked)} />
            Show acknowledged
          </label>
        </div>
      </div>

      {/* Alert list */}
      <div style={{ ...brandTokens.card, padding: 0 }}>
        {isLoading ? (
          <p style={{ padding: 28, fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid }}>
            Loading alerts…
          </p>
        ) : alerts.length === 0 ? (
          <p style={{ padding: 28, fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid }}>
            No alerts found.
          </p>
        ) : (
          alerts.map((alert, i) => (
            <div
              key={alert.id}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16,
                padding: "20px 28px",
                borderBottom: i < alerts.length - 1 ? `1px solid ${brandTokens.colors.primary10}` : "none",
                opacity: alert.acknowledged ? 0.5 : 1,
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <SeverityBadge severity={alert.severity} />
                  <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "1.5px", textTransform: "uppercase", color: brandTokens.colors.mid }}>
                    {alert.alert_type.replace(/_/g, " ")}
                  </span>
                </div>
                <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.dark, lineHeight: 1.6, margin: 0 }}>
                  {alert.message}
                </p>
                <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 10, color: brandTokens.colors.mid, marginTop: 4, display: "block" }}>
                  {formatDate(alert.created_at)}
                  {alert.acknowledged && " · Acknowledged"}
                </span>
              </div>
              {!alert.acknowledged && (
                <button
                  onClick={() => ackAlert(String(alert.id))}
                  disabled={acking}
                  style={{
                    flexShrink: 0, border: `1px solid ${brandTokens.colors.primary30}`, background: "none",
                    borderRadius: 6, padding: "5px 12px", cursor: acking ? "not-allowed" : "pointer",
                    fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "1px",
                    textTransform: "uppercase", color: brandTokens.colors.primary60,
                    opacity: acking ? 0.5 : 1,
                  }}
                >
                  Acknowledge
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
