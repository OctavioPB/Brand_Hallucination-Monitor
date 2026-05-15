import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.API_INTERNAL_URL ?? "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  // Sentry source-map upload — runs only when SENTRY_AUTH_TOKEN is set in CI
  silent: true,
  org: process.env.SENTRY_ORG ?? "hallucin8",
  project: process.env.SENTRY_PROJECT ?? "hallucin8-dashboard",
  widenClientFileUpload: true,
  hideSourceMaps: true,
  disableLogger: true,
});
