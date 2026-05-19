"use client";

import { useState } from "react";
import { brandTokens as t } from "@/lib/brand-tokens";
import { Eyebrow } from "@/components/eyebrow";
import {
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  useWebhooks,
  useCreateWebhook,
} from "@/hooks/use-settings";

// ---------------------------------------------------------------------------
// API Key Management
// ---------------------------------------------------------------------------

function ApiKeysSection() {
  const { data: keys = [], isLoading } = useApiKeys();
  const { mutate: createKey, isPending: creating } = useCreateApiKey();
  const { mutate: revokeKey, isPending: revoking } = useRevokeApiKey();

  const [name, setName] = useState("");
  const [role, setRole] = useState<"admin" | "analyst" | "viewer">("analyst");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreateError(null);
    createKey({ name: name.trim(), role }, {
      onSuccess: (created) => {
        setNewKey(created.raw_key);
        setName("");
        setRole("analyst");
      },
      onError: (err) => setCreateError(err instanceof Error ? err.message : "Failed to create key"),
    });
  }

  function handleCopy() {
    if (!newKey) return;
    navigator.clipboard.writeText(newKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handleRevoke(keyId: string) {
    if (confirmRevoke !== keyId) { setConfirmRevoke(keyId); return; }
    revokeKey(keyId, { onSettled: () => setConfirmRevoke(null) });
  }

  const ROLE_COLORS: Record<string, { bg: string; text: string }> = {
    admin:   { bg: t.status.primary.bg,    text: t.status.primary.base },
    analyst: { bg: t.status.strategic.bg,  text: t.status.strategic.base },
    viewer:  { bg: t.colors.primary10,     text: t.colors.mid },
  };

  return (
    <section style={{ marginBottom: 56 }}>
      <Eyebrow>Authentication</Eyebrow>
      <h2 style={{ fontFamily: t.typography.fontDisplay, fontSize: 26, fontWeight: 300, color: t.colors.dark, margin: "10px 0 6px" }}>
        API <em style={{ fontStyle: "italic" }}>keys</em>
      </h2>
      <p style={{ fontFamily: t.typography.fontBody, fontSize: 13, color: t.colors.mid, marginBottom: 24, lineHeight: 1.7 }}>
        Keys authenticate requests to <code style={inlineCode}>X-API-Key</code>. Roles: <strong>admin</strong> can create/revoke keys; <strong>analyst</strong> can read and trigger scans; <strong>viewer</strong> is read-only.
      </p>

      {/* Create form */}
      <form onSubmit={handleCreate} style={{ ...t.card, display: "flex", gap: 10, alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ flex: "2 1 200px" }}>
          <label style={fieldLabel}>Key name</label>
          <input
            type="text" required value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. CI pipeline, Zapier integration"
            style={inputStyle}
          />
        </div>
        <div style={{ flex: "1 1 130px" }}>
          <label style={fieldLabel}>Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value as typeof role)} style={inputStyle}>
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
        <button
          type="submit" disabled={creating || !name.trim()}
          style={{ ...primaryBtn, opacity: creating || !name.trim() ? 0.5 : 1, cursor: creating || !name.trim() ? "not-allowed" : "pointer", flexShrink: 0 }}
        >
          {creating ? "Creating…" : "+ Create key"}
        </button>
      </form>

      {createError && <p style={errorText}>{createError}</p>}

      {/* Newly created key — show raw value once */}
      {newKey && (
        <div style={{ ...t.card, borderLeft: `4px solid ${t.colors.gold}`, marginBottom: 20 }}>
          <p style={{ fontFamily: t.typography.fontBody, fontSize: 12, color: t.colors.mid, marginBottom: 8 }}>
            Copy this key now — it will not be shown again.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <code style={{ fontFamily: t.typography.fontMono, fontSize: 12, color: t.colors.primary, backgroundColor: t.colors.primary10, padding: "8px 14px", borderRadius: 6, flex: 1, wordBreak: "break-all" }}>
              {newKey}
            </code>
            <button onClick={handleCopy} style={{ ...secondaryBtn, flexShrink: 0 }}>
              {copied ? "✓ Copied" : "Copy"}
            </button>
            <button onClick={() => setNewKey(null)} style={{ background: "none", border: "none", cursor: "pointer", color: t.colors.mid, fontSize: 18, lineHeight: 1, padding: "4px" }}>
              ×
            </button>
          </div>
        </div>
      )}

      {/* Keys table */}
      {isLoading ? (
        <p style={loadingText}>Loading keys…</p>
      ) : keys.length === 0 ? (
        <div style={{ ...t.card, textAlign: "center", padding: "32px", color: t.colors.mid, fontFamily: t.typography.fontBody, fontSize: 13 }}>
          No API keys yet.
        </div>
      ) : (
        <div style={{ borderRadius: 12, overflow: "hidden", border: `1px solid ${t.colors.primary10}` }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ backgroundColor: t.colors.primary }}>
                {["Name", "Role", "Status", "Last used", "Created", ""].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keys.map((k, i) => {
                const rc = ROLE_COLORS[k.role] ?? ROLE_COLORS.viewer;
                return (
                  <tr key={k.id} style={{ backgroundColor: i % 2 === 0 ? t.colors.white : t.colors.primary10 }}>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 600, color: t.colors.dark }}>{k.name}</span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 9, fontFamily: t.typography.fontBody, letterSpacing: "1.5px", textTransform: "uppercase", backgroundColor: rc.bg, color: rc.text }}>
                        {k.role}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontFamily: t.typography.fontBody, fontSize: 11, color: k.is_active ? t.status.success.text : t.colors.mid }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: k.is_active ? t.status.success.base : t.colors.mid, display: "inline-block" }} />
                        {k.is_active ? "Active" : "Revoked"}
                      </span>
                    </td>
                    <td style={tdStyle}>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "—"}</td>
                    <td style={tdStyle}>{new Date(k.created_at).toLocaleDateString()}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {k.is_active && (
                        <button
                          onClick={() => handleRevoke(k.id)}
                          disabled={revoking}
                          style={{
                            padding: "4px 10px", border: `1px solid ${confirmRevoke === k.id ? t.status.danger.base : t.colors.primary10}`,
                            borderRadius: 6, cursor: "pointer", background: "none",
                            fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "1px", textTransform: "uppercase",
                            color: confirmRevoke === k.id ? t.status.danger.base : t.colors.mid,
                            opacity: revoking ? 0.5 : 1,
                          }}
                        >
                          {confirmRevoke === k.id ? "Confirm?" : "Revoke"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Webhook Management
// ---------------------------------------------------------------------------

const SEVERITY_OPTIONS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

function WebhooksSection() {
  const { data: webhooks = [], isLoading } = useWebhooks();
  const { mutate: addWebhook, isPending: adding } = useCreateWebhook();

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [severities, setSeverities] = useState<string[]>(["CRITICAL", "HIGH"]);
  const [addError, setAddError] = useState<string | null>(null);

  function toggleSeverity(s: string) {
    setSeverities((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  }

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;
    setAddError(null);
    addWebhook(
      { name: name.trim(), url: url.trim(), severity_filter: severities.join(",") },
      {
        onSuccess: () => { setName(""); setUrl(""); setSeverities(["CRITICAL", "HIGH"]); },
        onError: (err) => setAddError(err instanceof Error ? err.message : "Failed to add webhook"),
      }
    );
  }

  const SEV_COLORS: Record<string, { bg: string; text: string }> = {
    CRITICAL: { bg: t.status.danger.bg,    text: t.status.danger.base },
    HIGH:     { bg: "#FFF3EA",             text: t.status.warning.base },
    MEDIUM:   { bg: t.status.strategic.bg, text: t.status.strategic.base },
    LOW:      { bg: t.colors.primary10,    text: t.colors.mid },
  };

  return (
    <section style={{ marginBottom: 56 }}>
      <Eyebrow>Notifications</Eyebrow>
      <h2 style={{ fontFamily: t.typography.fontDisplay, fontSize: 26, fontWeight: 300, color: t.colors.dark, margin: "10px 0 6px" }}>
        Webhook <em style={{ fontStyle: "italic" }}>endpoints</em>
      </h2>
      <p style={{ fontFamily: t.typography.fontBody, fontSize: 13, color: t.colors.mid, marginBottom: 24, lineHeight: 1.7 }}>
        hallucin8 sends a POST request to each active endpoint when an alert fires. Payload is JSON with <code style={inlineCode}>id</code>, <code style={inlineCode}>severity</code>, <code style={inlineCode}>message</code>, and <code style={inlineCode}>brand_id</code>.
      </p>

      {/* Add webhook form */}
      <form onSubmit={handleAdd} style={{ ...t.card, marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
          <div style={{ flex: "1 1 180px" }}>
            <label style={fieldLabel}>Endpoint name</label>
            <input
              type="text" required value={name} onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Slack #brand-alerts"
              style={inputStyle}
            />
          </div>
          <div style={{ flex: "3 1 280px" }}>
            <label style={fieldLabel}>URL</label>
            <input
              type="url" required value={url} onChange={(e) => setUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/…"
              style={inputStyle}
            />
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ ...fieldLabel, display: "block", marginBottom: 8 }}>Fire on severity</label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {SEVERITY_OPTIONS.map((s) => {
              const active = severities.includes(s);
              const sc = SEV_COLORS[s];
              return (
                <button
                  key={s} type="button" onClick={() => toggleSeverity(s)}
                  style={{
                    padding: "5px 14px", borderRadius: 6, cursor: "pointer",
                    fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "1.5px", textTransform: "uppercase",
                    border: `1px solid ${active ? sc.text : t.colors.primary10}`,
                    backgroundColor: active ? sc.bg : t.colors.white,
                    color: active ? sc.text : t.colors.mid,
                    transition: "all 0.12s",
                  }}
                >
                  {s}
                </button>
              );
            })}
          </div>
        </div>
        {addError && <p style={{ ...errorText, marginBottom: 12 }}>{addError}</p>}
        <button
          type="submit" disabled={adding || !name.trim() || !url.trim() || severities.length === 0}
          style={{ ...primaryBtn, opacity: adding || !name.trim() || !url.trim() || severities.length === 0 ? 0.5 : 1, cursor: adding || !name.trim() || !url.trim() ? "not-allowed" : "pointer" }}
        >
          {adding ? "Adding…" : "+ Add webhook"}
        </button>
      </form>

      {/* Webhooks list */}
      {isLoading ? (
        <p style={loadingText}>Loading webhooks…</p>
      ) : webhooks.length === 0 ? (
        <div style={{ ...t.card, textAlign: "center", padding: "32px", color: t.colors.mid, fontFamily: t.typography.fontBody, fontSize: 13 }}>
          No webhooks configured yet.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {webhooks.map((w) => (
            <div key={w.id} style={{ ...t.card, borderLeft: `3px solid ${w.is_active ? t.colors.gold : t.colors.primary10}`, display: "flex", gap: 16, alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ fontFamily: t.typography.fontBody, fontSize: 13, fontWeight: 600, color: t.colors.dark }}>{w.name}</span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 10, fontFamily: t.typography.fontBody, color: w.is_active ? t.status.success.text : t.colors.mid }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: w.is_active ? t.status.success.base : t.colors.mid, display: "inline-block" }} />
                    {w.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <code style={{ fontFamily: t.typography.fontMono, fontSize: 11, color: t.colors.primary60, wordBreak: "break-all" }}>
                  {w.url}
                </code>
                <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
                  {w.severity_filter.split(",").map((s) => {
                    const sc = SEV_COLORS[s.trim()] ?? SEV_COLORS.LOW;
                    return (
                      <span key={s} style={{ padding: "2px 8px", borderRadius: 4, fontSize: 9, fontFamily: t.typography.fontBody, letterSpacing: "1.5px", textTransform: "uppercase", backgroundColor: sc.bg, color: sc.text }}>
                        {s.trim()}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  return (
    <div>
      {/* Hero */}
      <div style={{ ...t.heroSection, padding: "56px 48px 40px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Eyebrow light>Organisation</Eyebrow>
          <h1 style={{ fontFamily: t.typography.fontDisplay, fontSize: 36, fontWeight: 300, color: "#fff", margin: "14px 0 10px", lineHeight: 1.2 }}>
            Settings
          </h1>
          <p style={{ fontFamily: t.typography.fontBody, fontSize: 14, color: "rgba(255,255,255,0.5)", lineHeight: 1.7, maxWidth: 520 }}>
            Manage API keys and webhook delivery endpoints for your organisation.
          </p>
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: t.colors.light, borderTop: `1px solid ${t.colors.primary10}` }}>
        <div style={{ maxWidth: 900, margin: "0 auto", padding: "48px 48px" }}>
          <ApiKeysSection />
          <WebhooksSection />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const fieldLabel: React.CSSProperties = {
  display: "block", fontFamily: t.typography.fontBody, fontSize: 9,
  fontWeight: 500, letterSpacing: "2.5px", textTransform: "uppercase",
  color: t.colors.mid, marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px",
  border: `1px solid ${t.colors.primary10}`, borderRadius: 8,
  fontFamily: t.typography.fontBody, fontSize: 13,
  color: t.colors.dark, backgroundColor: t.colors.white,
  outline: "none", boxSizing: "border-box",
};

const primaryBtn: React.CSSProperties = {
  padding: "10px 18px", backgroundColor: t.colors.primary,
  color: "#fff", border: "none", borderRadius: 8,
  fontFamily: t.typography.fontBody, fontSize: 10,
  fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase",
};

const secondaryBtn: React.CSSProperties = {
  padding: "6px 14px", backgroundColor: t.colors.light,
  color: t.colors.mid, border: `1px solid ${t.colors.primary10}`, borderRadius: 6,
  fontFamily: t.typography.fontBody, fontSize: 9,
  fontWeight: 600, letterSpacing: "1.5px", textTransform: "uppercase", cursor: "pointer",
};

const thStyle: React.CSSProperties = {
  padding: "10px 16px", textAlign: "left",
  fontFamily: t.typography.fontBody, fontSize: 9,
  letterSpacing: "2px", textTransform: "uppercase",
  color: "#ffffff", fontWeight: 600,
};

const tdStyle: React.CSSProperties = {
  padding: "12px 16px", fontFamily: t.typography.fontBody,
  fontSize: 12, color: t.colors.mid, verticalAlign: "middle",
};

const inlineCode: React.CSSProperties = {
  fontFamily: t.typography.fontMono, fontSize: 11,
  color: t.colors.primary, backgroundColor: t.colors.primary10,
  padding: "1px 5px", borderRadius: 3,
};

const loadingText: React.CSSProperties = {
  fontFamily: t.typography.fontBody, fontSize: 13, color: t.colors.mid, padding: "16px 0",
};

const errorText: React.CSSProperties = {
  fontFamily: t.typography.fontBody, fontSize: 13, color: t.status.danger.base, marginBottom: 8,
};
