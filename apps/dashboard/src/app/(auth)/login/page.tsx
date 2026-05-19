"use client";

import { useState } from "react";
import { brandTokens } from "@/lib/brand-tokens";
import { Footer } from "@/components/footer";

export default function LoginPage() {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");

  function enter() {
    const key = apiKey.trim();
    if (!key) { setError("Paste your API key first."); return; }
    if (!key.startsWith("hk_")) { setError("API keys start with hk_"); return; }
    localStorage.setItem("hallucin8_api_key", key);
    window.location.href = "/dashboard";
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: brandTokens.colors.light }}>
      <div style={{ ...brandTokens.heroSection, padding: "96px 48px 64px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
        <div style={{ marginBottom: 32 }}>
          <span style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 32, fontWeight: 300, color: "#fff" }}>O</span>
          <em style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 32, fontWeight: 300, fontStyle: "italic", color: brandTokens.colors.goldLight }}>PB</em>
        </div>
        <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 48, fontWeight: 300, color: "#fff", maxWidth: 560, lineHeight: 1.25, marginBottom: 16 }}>
          Brand safety in{" "}
          <em style={{ fontStyle: "italic", color: brandTokens.colors.goldLight }}>every model.</em>
        </h1>
      </div>

      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 24px" }}>
        <div style={{ ...brandTokens.card, width: "100%", maxWidth: 420, borderTop: `3px solid ${brandTokens.colors.gold}` }}>
          <h2 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 22, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 8 }}>
            Access your workspace
          </h2>
          <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid, marginBottom: 20 }}>
            Paste the API key you received when you signed up.
          </p>

          <label style={{ display: "block", fontSize: 10, fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", color: brandTokens.colors.mid, marginBottom: 6, fontFamily: brandTokens.typography.fontBody }}>
            API Key
          </label>
          <input
            type="text"
            placeholder="hk_..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && enter()}
            style={{ width: "100%", padding: "10px 12px", border: `1px solid ${brandTokens.colors.primary10}`, borderRadius: 8, fontSize: 13, color: brandTokens.colors.dark, backgroundColor: brandTokens.colors.light, outline: "none", boxSizing: "border-box", marginBottom: 12 }}
          />

          {error && (
            <p style={{ color: "#e53e3e", fontSize: 13, marginBottom: 12, fontFamily: brandTokens.typography.fontBody }}>{error}</p>
          )}

          <button
            type="button"
            onClick={enter}
            style={{ width: "100%", padding: "12px", backgroundColor: brandTokens.colors.primary, color: "#fff", border: "none", borderRadius: 8, fontSize: 10, fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer", fontFamily: brandTokens.typography.fontBody }}
          >
            Enter workspace →
          </button>

          <p style={{ marginTop: 16, fontSize: 12, color: brandTokens.colors.mid, textAlign: "center", fontFamily: brandTokens.typography.fontBody }}>
            No account?{" "}
            <a href="/signup" style={{ color: brandTokens.colors.primary60, textDecoration: "none", fontWeight: 500 }}>Sign up free →</a>
          </p>
        </div>
      </div>

      <Footer />
    </div>
  );
}
