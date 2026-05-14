"use client";

import { useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";
import { SeverityBadge } from "@/components/severity-badge";
import type { HallucinationSummary } from "@/lib/api-client";

function deriveSeverity(
  detected: number
): "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" {
  if (detected >= 3) return "CRITICAL";
  if (detected >= 2) return "HIGH";
  if (detected === 1) return "MEDIUM";
  return "LOW";
}

interface HallucinationCardProps {
  hallucination: HallucinationSummary;
}

export function HallucinationCard({ hallucination }: HallucinationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const severity = deriveSeverity(hallucination.hallucinations_detected);

  const date = new Date(hallucination.probed_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const borderColor =
    severity === "CRITICAL" || severity === "HIGH"
      ? brandTokens.status.danger.base
      : severity === "MEDIUM"
      ? brandTokens.status.warning.base
      : brandTokens.colors.primary10;

  return (
    <div
      style={{
        backgroundColor: brandTokens.colors.white,
        borderRadius: 12,
        boxShadow: "0 1px 4px rgba(0,51,102,0.08)",
        padding: "18px 24px",
        marginBottom: 12,
        borderLeft: `3px solid ${borderColor}`,
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
        }}
      >
        <div style={{ flex: 1 }}>
          {/* Badge + model + date */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              flexWrap: "wrap",
              marginBottom: 8,
            }}
          >
            <SeverityBadge severity={severity} />
            <span
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "2px",
                textTransform: "uppercase",
                color: brandTokens.colors.primary60,
              }}
            >
              {hallucination.model_name}
            </span>
            <span
              style={{
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 11,
                color: brandTokens.colors.mid,
              }}
            >
              {date}
            </span>
          </div>

          {/* Probe prompt */}
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.dark,
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            {hallucination.probe_prompt}
          </p>
        </div>

        {/* Hallucinations count */}
        <div
          style={{
            textAlign: "center",
            flexShrink: 0,
            padding: "4px 12px",
            backgroundColor:
              hallucination.hallucinations_detected > 0
                ? brandTokens.status.danger.bg
                : brandTokens.status.success.bg,
            borderRadius: 8,
          }}
        >
          <div
            style={{
              fontFamily: brandTokens.typography.fontDisplay,
              fontSize: 28,
              fontWeight: 300,
              color:
                hallucination.hallucinations_detected > 0
                  ? brandTokens.status.danger.text
                  : brandTokens.status.success.text,
              lineHeight: 1,
            }}
          >
            {hallucination.hallucinations_detected}
          </div>
          <div
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
              marginTop: 2,
            }}
          >
            flagged
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div
          style={{
            marginTop: 14,
            padding: "14px 16px",
            backgroundColor: brandTokens.colors.light,
            borderRadius: 8,
          }}
        >
          <div
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              letterSpacing: "2px",
              textTransform: "uppercase",
              color: brandTokens.colors.mid,
              marginBottom: 6,
            }}
          >
            LLM Response
          </div>
          <p
            style={{
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 13,
              color: brandTokens.colors.dark,
              lineHeight: 1.75,
              margin: 0,
              whiteSpace: "pre-wrap",
            }}
          >
            {hallucination.llm_response || "Response not available."}
          </p>

          <div
            style={{
              marginTop: 12,
              paddingTop: 12,
              borderTop: `1px solid ${brandTokens.colors.primary10}`,
              display: "flex",
              gap: 24,
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9,
                  letterSpacing: "2px",
                  textTransform: "uppercase",
                  color: brandTokens.colors.mid,
                }}
              >
                Cost
              </div>
              <div
                style={{
                  fontFamily: brandTokens.typography.fontDisplay,
                  fontSize: 15,
                  fontWeight: 300,
                  color: brandTokens.colors.dark,
                }}
              >
                ${hallucination.cost_usd.toFixed(4)}
              </div>
            </div>
            <div>
              <div
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9,
                  letterSpacing: "2px",
                  textTransform: "uppercase",
                  color: brandTokens.colors.mid,
                }}
              >
                DAG Run
              </div>
              <div
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 12,
                  color: brandTokens.colors.dark,
                  fontFamily: brandTokens.typography.fontMono,
                }}
              >
                {hallucination.dag_run_id}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          marginTop: 10,
          background: "none",
          border: "none",
          cursor: "pointer",
          fontFamily: brandTokens.typography.fontBody,
          fontSize: 10,
          letterSpacing: "1.5px",
          textTransform: "uppercase",
          color: brandTokens.colors.primary60,
          padding: 0,
          display: "flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {expanded ? "↑ Collapse" : "↓ View response"}
      </button>
    </div>
  );
}
