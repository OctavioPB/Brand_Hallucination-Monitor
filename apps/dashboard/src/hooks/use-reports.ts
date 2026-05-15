"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAlertRule,
  deleteAlertRule,
  generateReport,
  getAlertRules,
  getReport,
  getReports,
  updateAlertRule,
  type AlertRuleCreate,
} from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const REPORTS_KEY = ["reports"] as const;
export const reportsKey = (opts?: object) => [...REPORTS_KEY, opts] as const;
export const reportKey = (id: string) => ["reports", id] as const;
export const ALERT_RULES_KEY = ["alert-rules"] as const;
export const alertRulesKey = (opts?: object) => [...ALERT_RULES_KEY, opts] as const;

// ---------------------------------------------------------------------------
// Reports hooks
// ---------------------------------------------------------------------------

export function useReports(opts?: {
  brand_id?: string;
  report_type?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: reportsKey(opts),
    queryFn: () => getReports(opts),
  });
}

export function useReport(id: string) {
  return useQuery({
    queryKey: reportKey(id),
    queryFn: () => getReport(id),
    enabled: !!id,
  });
}

export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ brandId, weekStart }: { brandId: string; weekStart?: string }) =>
      generateReport(brandId, weekStart),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
    },
  });
}

// ---------------------------------------------------------------------------
// Alert rules hooks
// ---------------------------------------------------------------------------

export function useAlertRules(opts?: { brand_id?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: alertRulesKey(opts),
    queryFn: () => getAlertRules(opts),
  });
}

export function useCreateAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AlertRuleCreate) => createAlertRule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ALERT_RULES_KEY });
    },
  });
}

export function useDeleteAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => deleteAlertRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ALERT_RULES_KEY });
    },
  });
}

export function useToggleAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, isActive }: { ruleId: string; isActive: boolean }) =>
      updateAlertRule(ruleId, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ALERT_RULES_KEY });
    },
  });
}
