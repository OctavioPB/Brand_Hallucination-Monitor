import { brandTokens } from "@/lib/brand-tokens";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "#0f172a" }}>
      {/* Admin nav bar */}
      <nav style={{
        backgroundColor: "#1e293b",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        padding: "0 32px",
        height: 48,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 18, fontWeight: 300, color: "#fff" }}>O</span>
          <em style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 18, fontWeight: 300, fontStyle: "italic", color: brandTokens.colors.goldLight }}>PB</em>
          <div style={{ width: 1, height: 20, backgroundColor: "rgba(255,255,255,0.15)", margin: "0 8px" }} />
          <span style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "3px", textTransform: "uppercase", color: "rgba(255,255,255,0.45)" }}>
            Admin Panel
          </span>
        </div>
        <a href="/dashboard" style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", textDecoration: "none" }}>
          ← Back to dashboard
        </a>
      </nav>

      {/* Sidebar + content */}
      <div style={{ flex: 1, display: "flex" }}>
        <aside style={{ width: 200, backgroundColor: "#1e293b", borderRight: "1px solid rgba(255,255,255,0.06)", padding: "24px 0", flexShrink: 0 }}>
          {[
            { href: "/admin", label: "Overview" },
            { href: "/admin/orgs", label: "Organizations" },
            { href: "/admin/scan-jobs", label: "Scan jobs" },
            { href: "/admin/costs", label: "Cost per org" },
            { href: "/admin/nps", label: "NPS responses" },
          ].map(({ href, label }) => (
            <a
              key={href}
              href={href}
              style={{
                display: "block",
                padding: "8px 24px",
                fontFamily: brandTokens.typography.fontBody,
                fontSize: 11,
                color: "rgba(255,255,255,0.5)",
                textDecoration: "none",
                letterSpacing: "1px",
              }}
            >
              {label}
            </a>
          ))}
        </aside>

        <main style={{ flex: 1, padding: "32px", overflowY: "auto" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
