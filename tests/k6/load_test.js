/**
 * k6 Load Test — hallucin8 Dashboard API
 *
 * Simulates 100 concurrent dashboard users hitting the key read endpoints.
 * Target: P95 latency < 200ms for all endpoints.
 *
 * Usage:
 *   k6 run tests/k6/load_test.js
 *   k6 run --env BASE_URL=https://api.hallucin8.io tests/k6/load_test.js
 *   k6 run --env VIRTUAL_USERS=50 --env DURATION=60s tests/k6/load_test.js
 *
 * Requirements:
 *   brew install k6           (macOS)
 *   choco install k6          (Windows)
 *   apt install k6            (Ubuntu/Debian)
 *
 * Environment variables:
 *   BASE_URL      API base URL (default: http://localhost:8000)
 *   API_TOKEN     Bearer token for authentication (required for authed endpoints)
 *   VIRTUAL_USERS Number of concurrent VUs (default: 100)
 *   DURATION      Test duration (default: 5m)
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API_TOKEN = __ENV.API_TOKEN || "";
const VUS = parseInt(__ENV.VIRTUAL_USERS || "100");
const DURATION = __ENV.DURATION || "5m";

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const errorRate = new Rate("error_rate");
const vectorMapLatency = new Trend("vector_map_latency", true);
const reportsLatency = new Trend("reports_latency", true);
const alertsLatency = new Trend("alerts_latency", true);

// ---------------------------------------------------------------------------
// k6 options
// ---------------------------------------------------------------------------

export const options = {
  scenarios: {
    dashboard_users: {
      executor: "constant-vus",
      vus: VUS,
      duration: DURATION,
    },
    ramp_up: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: VUS },
        { duration: "4m", target: VUS },
        { duration: "30s", target: 0 },
      ],
      startTime: "0s",
    },
  },
  thresholds: {
    // P95 < 200ms for all requests (Sprint 9 SLA)
    http_req_duration: ["p(95)<200"],
    // Vector map is the most expensive endpoint — still < 200ms with Redis cache
    vector_map_latency: ["p(95)<200"],
    reports_latency: ["p(95)<300"],
    alerts_latency: ["p(95)<150"],
    // Error rate < 1%
    error_rate: ["rate<0.01"],
    http_req_failed: ["rate<0.01"],
  },
};

// ---------------------------------------------------------------------------
// Auth headers
// ---------------------------------------------------------------------------

function authHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (API_TOKEN) {
    headers["Authorization"] = `Bearer ${API_TOKEN}`;
  }
  return headers;
}

// ---------------------------------------------------------------------------
// Test data — realistic brand IDs seeded by scripts/seed_data.py
// ---------------------------------------------------------------------------

const BRAND_IDS = [
  "00000000-0000-0000-0000-000000000001",
  "00000000-0000-0000-0000-000000000002",
  "00000000-0000-0000-0000-000000000003",
];

function randomBrandId() {
  return BRAND_IDS[Math.floor(Math.random() * BRAND_IDS.length)];
}

// ---------------------------------------------------------------------------
// Main VU function
// ---------------------------------------------------------------------------

export default function () {
  const headers = authHeaders();
  const brandId = randomBrandId();

  group("health", () => {
    const res = http.get(`${BASE_URL}/health`, { headers });
    check(res, { "health ok": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });

  sleep(0.5);

  group("brands list", () => {
    const res = http.get(`${BASE_URL}/api/v1/brands`, { headers });
    const ok = check(res, {
      "brands 200": (r) => r.status === 200,
      "brands has data": (r) => {
        try { return Array.isArray(JSON.parse(r.body)); }
        catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  sleep(0.3);

  group("vector map (cached)", () => {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/brands/${brandId}/vector-map`, { headers });
    vectorMapLatency.add(Date.now() - start);
    const ok = check(res, {
      "vector map 200": (r) => r.status === 200 || r.status === 404,
    });
    errorRate.add(res.status >= 500);
  });

  sleep(0.4);

  group("alerts feed", () => {
    const start = Date.now();
    const res = http.get(
      `${BASE_URL}/api/v1/alerts?acknowledged=false&limit=20`,
      { headers }
    );
    alertsLatency.add(Date.now() - start);
    const ok = check(res, { "alerts 200": (r) => r.status === 200 });
    errorRate.add(!ok);
  });

  sleep(0.3);

  group("reports list", () => {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/reports?limit=10`, { headers });
    reportsLatency.add(Date.now() - start);
    const ok = check(res, { "reports 200": (r) => r.status === 200 });
    errorRate.add(!ok);
  });

  sleep(0.5);

  group("sps scores", () => {
    const res = http.get(
      `${BASE_URL}/api/v1/brands/${brandId}/sps`,
      { headers }
    );
    check(res, { "sps 200 or 404": (r) => r.status === 200 || r.status === 404 });
    errorRate.add(res.status >= 500);
  });

  sleep(0.3);

  group("cost summary", () => {
    const res = http.get(`${BASE_URL}/api/v1/costs/summary`, { headers });
    check(res, { "costs 200": (r) => r.status === 200 });
    errorRate.add(res.status >= 500);
  });

  // Pace each VU iteration to ~3s total think time
  sleep(0.7);
}

// ---------------------------------------------------------------------------
// Summary output
// ---------------------------------------------------------------------------

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration?.values?.["p(95)"] ?? "N/A";
  const p99 = data.metrics.http_req_duration?.values?.["p(99)"] ?? "N/A";
  const errors = data.metrics.error_rate?.values?.rate ?? 0;
  const rps = data.metrics.http_reqs?.values?.rate ?? 0;

  console.log("\n============================================================");
  console.log("  hallucin8 Load Test Summary");
  console.log("============================================================");
  console.log(`  VUs:         ${VUS}`);
  console.log(`  Duration:    ${DURATION}`);
  console.log(`  Req/s:       ${rps.toFixed(1)}`);
  console.log(`  P95 latency: ${typeof p95 === "number" ? p95.toFixed(1) + "ms" : p95}`);
  console.log(`  P99 latency: ${typeof p99 === "number" ? p99.toFixed(1) + "ms" : p99}`);
  console.log(`  Error rate:  ${(errors * 100).toFixed(2)}%`);
  console.log(`  SLA pass:    ${typeof p95 === "number" && p95 < 200 ? "✓ YES" : "✗ NO"}`);
  console.log("============================================================\n");

  return {
    stdout: JSON.stringify(data, null, 2),
  };
}
