"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { brandTokens } from "@/lib/brand-tokens";

const NAV_LINKS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/brands", label: "Brands" },
  { href: "/alerts", label: "Alerts" },
  { href: "/info", label: "Info" },
  { href: "/admin", label: "Admin" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: brandTokens.navBar.height,
        padding: brandTokens.navBar.padding,
        background: brandTokens.navBar.background,
        backdropFilter: brandTokens.navBar.backdropFilter,
        borderBottom: brandTokens.navBar.borderBottom,
      }}
    >
      {/* OPB Monogram */}
      <Link href="/dashboard">
        <span>
          <span
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: "20px",
              fontWeight: 300,
              color: "#ffffff",
            }}
          >
            O
          </span>
          <em
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: "20px",
              fontWeight: 300,
              fontStyle: "italic",
              color: brandTokens.colors.goldLight,
            }}
          >
            PB
          </em>
        </span>
      </Link>

      {/* App title */}
      <span
        style={{
          position: "absolute",
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: "9px",
          letterSpacing: "3px",
          textTransform: "uppercase",
          color: "rgba(255,255,255,0.4)",
          fontFamily: brandTokens.typography.fontBody,
        }}
      >
        hallucin8
      </span>

      {/* Nav links + logout */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {NAV_LINKS.map(({ href, label }) => {
          const isActive = pathname.startsWith(href);
          return (
            <Link key={href} href={href} style={{ textDecoration: "none" }}>
              <button
                style={{
                  ...brandTokens.navLink,
                  ...(isActive ? brandTokens.navLinkActive : {}),
                }}
              >
                {label}
              </button>
            </Link>
          );
        })}

        <button style={brandTokens.logoutBtn}>Logout</button>
      </div>
    </nav>
  );
}
