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
    localStorage.getItem("hallucin8_token") ??
    (process.env.NEXT_PUBLIC_DEV_TOKEN || null)
  );
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("hallucin8_token", token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("hallucin8_token");
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
    headers["Authorization"] = `Bearer ${token}`;
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
