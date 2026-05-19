/**
 * Typed API client for hallucin8 backend.
 * All paths are relative — Next.js rewrites proxy /api/v1/* to the FastAPI server.
 */

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

export interface BrandManifest {
  true_attributes: string[];
  false_attributes: string[];
  competitor_list: string[];
  regulatory_claims_to_avoid: string[];
}

export interface Brand {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  manifest: BrandManifest | null;
  created_at: string;
  updated_at: string;
}

export interface BrandCreate {
  organization_id: string;
  name: string;
  slug: string;
  manifest?: BrandManifest;
}

export interface Alert {
  id: string;
  organization_id: string;
  brand_id: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  alert_type: string;
  message: string;
  acknowledged: boolean;
  created_at: string;
}

export interface SPSScore {
  id: string;
  brand_id: string;
  intent_cluster_slug: string;
  score: number;
  model_version: string;
  dag_run_id: string;
  calculated_at: string;
}

export interface HallucinationSummary {
  probe_id: string;
  model_name: string;
  probe_prompt: string;
  llm_response: string;
  hallucinations_detected: number;
  cost_usd: number;
  dag_run_id: string;
  probed_at: string;
}

export interface VectorPoint {
  label: string;
  x: number;
  y: number;
  cluster_slug: string;
  score: number;
}

export interface VectorMapSnapshot {
  brand_id: string;
  brand_name: string;
  points: VectorPoint[];
  generated_at: string;
}

export interface Competitor {
  id: string;
  brand_id: string;
  competitor_name: string;
  competitor_slug: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Auth token resolution
// ---------------------------------------------------------------------------

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return (
    localStorage.getItem("hallucin8_api_key") ??
    (process.env.NEXT_PUBLIC_DEV_TOKEN || null)
  );
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("hallucin8_api_key", token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("hallucin8_api_key");
  }
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string
  ) {
    super(message);
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) {
    headers["X-API-Key"] = token;
  }

  const res = await fetch(path, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body?.error?.message ?? body?.detail ?? `HTTP ${res.status}`;
    const code = body?.error?.code ?? String(res.status);
    throw new ApiError(message, res.status, code);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Brands
// ---------------------------------------------------------------------------

export const getBrands = () => apiFetch<Brand[]>("/api/v1/brands");

export const getBrand = (id: string) => apiFetch<Brand>(`/api/v1/brands/${id}`);

export const createBrand = (payload: BrandCreate) =>
  apiFetch<Brand>("/api/v1/brands", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getSPSScores = (brandId: string, cluster?: string) => {
  const params = cluster ? `?cluster=${cluster}` : "";
  return apiFetch<SPSScore[]>(`/api/v1/brands/${brandId}/sps${params}`);
};

export const getHallucinations = (brandId: string, onlyDetected = false) => {
  const params = onlyDetected ? "?only_detected=true" : "";
  return apiFetch<HallucinationSummary[]>(
    `/api/v1/brands/${brandId}/hallucinations${params}`
  );
};

export const getVectorMap = (brandId: string) =>
  apiFetch<VectorMapSnapshot>(`/api/v1/brands/${brandId}/vector-map`);

// ---------------------------------------------------------------------------
// Competitors
// ---------------------------------------------------------------------------

export const getCompetitors = (brandId: string) =>
  apiFetch<Competitor[]>(`/api/v1/brands/${brandId}/competitors`);

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export const getAlerts = (opts?: {
  severity?: string;
  acknowledged?: boolean;
  limit?: number;
}) => {
  const params = new URLSearchParams();
  if (opts?.severity) params.set("severity", opts.severity);
  if (opts?.acknowledged !== undefined)
    params.set("acknowledged", String(opts.acknowledged));
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return apiFetch<Alert[]>(`/api/v1/alerts${qs ? `?${qs}` : ""}`);
};

export const acknowledgeAlert = (alertId: string) =>
  apiFetch<Alert>(`/api/v1/alerts/${alertId}/acknowledge`, {
    method: "PATCH",
  });

// ---------------------------------------------------------------------------
// Reports (Sprint 8)
// ---------------------------------------------------------------------------

export interface ReportSummary {
  id: string;
  organization_id: string;
  brand_id: string;
  report_type: string;
  title: string;
  week_start: string | null;
  generated_at: string;
  has_pdf: boolean;
}

export interface ReportDetail extends ReportSummary {
  content_json: Record<string, unknown>;
}

export interface AlertRule {
  id: string;
  organization_id: string;
  brand_id: string;
  rule_type: "sps_threshold" | "competitor_rank";
  cluster_slug: string | null;
  threshold: number | null;
  competitor_name: string | null;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  is_active: boolean;
  created_at: string;
  last_triggered_at: string | null;
}

export interface AlertRuleCreate {
  brand_id: string;
  rule_type: "sps_threshold" | "competitor_rank";
  cluster_slug?: string;
  threshold?: number;
  competitor_name?: string;
  severity?: string;
}

export const getReports = (opts?: {
  brand_id?: string;
  report_type?: string;
  limit?: number;
}) => {
  const params = new URLSearchParams();
  if (opts?.brand_id) params.set("brand_id", opts.brand_id);
  if (opts?.report_type) params.set("report_type", opts.report_type);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return apiFetch<ReportSummary[]>(`/api/v1/reports${qs ? `?${qs}` : ""}`);
};

export const getReport = (id: string) =>
  apiFetch<ReportDetail>(`/api/v1/reports/${id}`);

export const generateReport = (brandId: string, weekStart?: string) =>
  apiFetch<ReportSummary>("/api/v1/reports/generate", {
    method: "POST",
    body: JSON.stringify({
      brand_id: brandId,
      ...(weekStart ? { week_start: weekStart } : {}),
    }),
  });

export const getAlertRules = (opts?: {
  brand_id?: string;
  is_active?: boolean;
}) => {
  const params = new URLSearchParams();
  if (opts?.brand_id) params.set("brand_id", opts.brand_id);
  if (opts?.is_active !== undefined) params.set("is_active", String(opts.is_active));
  const qs = params.toString();
  return apiFetch<AlertRule[]>(`/api/v1/alert-rules${qs ? `?${qs}` : ""}`);
};

export const createAlertRule = (payload: AlertRuleCreate) =>
  apiFetch<AlertRule>("/api/v1/alert-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const deleteAlertRule = (ruleId: string) =>
  apiFetch<void>(`/api/v1/alert-rules/${ruleId}`, { method: "DELETE" });

export const updateAlertRule = (
  ruleId: string,
  patch: Partial<Pick<AlertRule, "is_active" | "threshold" | "severity">>
) =>
  apiFetch<AlertRule>(`/api/v1/alert-rules/${ruleId}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });

// ---------------------------------------------------------------------------
// Costs (Sprint 9)
// ---------------------------------------------------------------------------

export interface CostSummary {
  date: string;
  total_cost_usd: number;
  budget_cap_usd: number;
  budget_remaining_usd: number;
  budget_used_pct: number;
  api_calls: number;
  tokens_consumed: number;
  vectors_from_cache: number;
}

export interface CostBreakdownRow {
  day: string;
  job_type: string;
  cost_usd: number;
  tokens: number;
  calls: number;
}

export interface InfraCostRow {
  dag_run_id: string;
  dag_id: string;
  task_id: string;
  cost_component: string;
  model: string | null;
  cost_usd: number;
  recorded_at: string;
}

export const getCostSummary = () => apiFetch<CostSummary>("/api/v1/costs/summary");

export const getCostBreakdown = (days = 30) =>
  apiFetch<CostBreakdownRow[]>(`/api/v1/costs/breakdown?days=${days}`);

export const getInfraCosts = (days = 7) =>
  apiFetch<InfraCostRow[]>(`/api/v1/costs/infra?days=${days}`);
