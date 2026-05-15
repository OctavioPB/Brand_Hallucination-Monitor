"use client";

import { useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";
import { analytics } from "@/lib/posthog";

interface NpsSurveyProps {
  onDismiss: () => void;
}

export function NpsSurvey({ onDismiss }: NpsSurveyProps) {
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    if (score === null) return;
    setLoading(true);
    try {
      await fetch("/api/v1/onboarding/nps", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": localStorage.getItem("hallucin8_api_key") ?? "",
        },
        body: JSON.stringify({ score, comment: comment || null, trigger: "first_report" }),
      });
      analytics.npsSubmitted(score);
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        width: 360,
        backgroundColor: brandTokens.colors.dark,
        borderRadius: 12,
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        border: "1px solid rgba(255,255,255,0.08)",
        padding: 24,
        zIndex: 1000,
      }}
    >
      {/* Close */}
      <button
        onClick={onDismiss}
        style={{ position: "absolute", top: 12, right: 14, background: "none", border: "none", color: "rgba(255,255,255,0.3)", fontSize: 18, cursor: "pointer", lineHeight: 1 }}
        aria-label="Dismiss"
      >
        ×
      </button>

      {submitted ? (
        <div>
          <div style={{ fontSize: 22, marginBottom: 8 }}>🙏</div>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 14, color: "#fff", margin: 0 }}>
            Thanks for your feedback!
          </p>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 4 }}>
            Your input shapes the product roadmap.
          </p>
          <button
            onClick={onDismiss}
            style={{ marginTop: 16, padding: "8px 16px", backgroundColor: brandTokens.colors.primary, color: "#fff", border: "none", borderRadius: 6, fontSize: 9, fontFamily: brandTokens.typography.fontBody, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer" }}
          >
            Close
          </button>
        </div>
      ) : (
        <>
          <p style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 16, fontWeight: 300, color: "#fff", margin: "0 0 4px 0" }}>
            How likely are you to recommend hallucin8?
          </p>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 11, color: "rgba(255,255,255,0.4)", margin: "0 0 16px 0" }}>
            0 = not likely · 10 = extremely likely
          </p>

          {/* Score buttons */}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 16 }}>
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                onClick={() => setScore(i)}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  border: score === i ? `2px solid ${brandTokens.colors.gold}` : "1px solid rgba(255,255,255,0.15)",
                  backgroundColor: score === i ? "rgba(200,152,42,0.15)" : "rgba(255,255,255,0.04)",
                  color: score === i ? brandTokens.colors.goldLight : "rgba(255,255,255,0.6)",
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 12,
                  fontWeight: score === i ? 600 : 400,
                  cursor: "pointer",
                  transition: "all 0.1s",
                }}
              >
                {i}
              </button>
            ))}
          </div>

          {/* Comment */}
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What's the main reason for your score? (optional)"
            style={{
              width: "100%",
              height: 64,
              padding: "8px 10px",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 6,
              backgroundColor: "rgba(255,255,255,0.04)",
              color: "#fff",
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 12,
              resize: "none",
              outline: "none",
              boxSizing: "border-box",
              marginBottom: 12,
            }}
          />

          <button
            onClick={handleSubmit}
            disabled={score === null || loading}
            style={{
              width: "100%",
              padding: "10px",
              backgroundColor: score === null ? "rgba(255,255,255,0.06)" : brandTokens.colors.primary,
              color: score === null ? "rgba(255,255,255,0.25)" : "#fff",
              border: "none",
              borderRadius: 6,
              fontFamily: brandTokens.typography.fontBody,
              fontSize: 9,
              fontWeight: 600,
              letterSpacing: "2px",
              textTransform: "uppercase",
              cursor: score === null ? "not-allowed" : "pointer",
              transition: "all 0.15s",
            }}
          >
            {loading ? "Submitting…" : "Submit feedback →"}
          </button>
        </>
      )}
    </div>
  );
}
