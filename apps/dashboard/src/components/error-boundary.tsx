"use client";

import React from "react";
import { brandTokens } from "@/lib/brand-tokens";
import { analytics } from "@/lib/posthog";

interface State {
  hasError: boolean;
  error: Error | null;
  issueUrl: string | null;
  reporting: boolean;
}

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, issueUrl: null, reporting: false };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info);
    analytics.issueReported(error.message);
  }

  async reportIssue() {
    const { error } = this.state;
    if (!error) return;

    this.setState({ reporting: true });

    try {
      const ghToken = process.env.NEXT_PUBLIC_GITHUB_ISSUE_TOKEN ?? "";
      if (!ghToken) {
        alert("GitHub issue token not configured. Please report manually.");
        return;
      }

      const body = [
        `## Automatic bug report`,
        ``,
        `**Error:** \`${error.message}\``,
        ``,
        `**Stack:**`,
        `\`\`\``,
        error.stack?.slice(0, 2000) ?? "(no stack)",
        `\`\`\``,
        ``,
        `**URL:** ${typeof window !== "undefined" ? window.location.href : "unknown"}`,
        `**UserAgent:** ${typeof navigator !== "undefined" ? navigator.userAgent : "unknown"}`,
      ].join("\n");

      const res = await fetch("https://api.github.com/repos/opb-ai-lab/hallucin8/issues", {
        method: "POST",
        headers: {
          Authorization: `token ${ghToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: `[UI bug] ${error.message.slice(0, 100)}`,
          body,
          labels: ["bug", "ui", "auto-reported"],
        }),
      });

      if (res.ok) {
        const data = await res.json();
        this.setState({ issueUrl: data.html_url });
      } else {
        alert(`GitHub returned ${res.status}. Please report manually.`);
      }
    } finally {
      this.setState({ reporting: false });
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    const { error, issueUrl, reporting } = this.state;

    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: brandTokens.colors.light,
          padding: 24,
        }}
      >
        <div
          style={{
            ...brandTokens.card,
            maxWidth: 520,
            width: "100%",
            borderTop: `3px solid ${brandTokens.status.danger.base}`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div
              style={{
                width: 32, height: 32, borderRadius: "50%",
                backgroundColor: brandTokens.status.danger.bg,
                display: "flex", alignItems: "center", justifyContent: "center",
                color: brandTokens.status.danger.base, fontSize: 16,
              }}
            >
              !
            </div>
            <span
              style={{
                fontFamily: brandTokens.typography.fontBody, fontSize: 9,
                fontWeight: 500, letterSpacing: "3px", textTransform: "uppercase",
                color: brandTokens.status.danger.base,
              }}
            >
              Unexpected error
            </span>
          </div>

          <h2
            style={{
              fontFamily: brandTokens.typography.fontDisplay, fontSize: 22,
              fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 8,
            }}
          >
            Something went wrong
          </h2>

          <p
            style={{
              fontFamily: brandTokens.typography.fontBody, fontSize: 13,
              color: brandTokens.colors.mid, lineHeight: 1.7, marginBottom: 20,
            }}
          >
            An unhandled error occurred in the application. You can try reloading
            the page, or report this issue to the engineering team.
          </p>

          {error && (
            <pre
              style={{
                backgroundColor: brandTokens.colors.dark, borderRadius: 6,
                padding: "12px 14px", fontFamily: brandTokens.typography.fontMono,
                fontSize: 11, color: brandTokens.status.danger.base,
                overflowX: "auto", marginBottom: 20, whiteSpace: "pre-wrap",
              }}
            >
              {error.message}
            </pre>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => window.location.reload()}
              style={{
                flex: 1, padding: "10px", backgroundColor: brandTokens.colors.primary,
                color: "#fff", border: "none", borderRadius: 8,
                fontFamily: brandTokens.typography.fontBody, fontSize: 9,
                fontWeight: 600, letterSpacing: "2px", textTransform: "uppercase", cursor: "pointer",
              }}
            >
              Reload page
            </button>

            {!issueUrl ? (
              <button
                onClick={() => this.reportIssue()}
                disabled={reporting}
                style={{
                  padding: "10px 16px", backgroundColor: "transparent",
                  color: brandTokens.status.danger.base,
                  border: `1px solid ${brandTokens.status.danger.base}`,
                  borderRadius: 8, fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9, fontWeight: 500, letterSpacing: "2px",
                  textTransform: "uppercase", cursor: reporting ? "not-allowed" : "pointer",
                  opacity: reporting ? 0.6 : 1,
                }}
              >
                {reporting ? "Reporting…" : "Report issue →"}
              </button>
            ) : (
              <a
                href={issueUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: "10px 16px", backgroundColor: brandTokens.status.success.bg,
                  color: brandTokens.status.success.base,
                  border: `1px solid ${brandTokens.status.success.base}`,
                  borderRadius: 8, fontFamily: brandTokens.typography.fontBody,
                  fontSize: 9, fontWeight: 500, letterSpacing: "2px",
                  textTransform: "uppercase", textDecoration: "none", display: "inline-flex",
                  alignItems: "center",
                }}
              >
                View issue →
              </a>
            )}
          </div>
        </div>
      </div>
    );
  }
}
