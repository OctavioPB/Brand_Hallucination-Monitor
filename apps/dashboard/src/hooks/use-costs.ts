"use client";

import { useQuery } from "@tanstack/react-query";
import { getCostBreakdown, getCostSummary, getInfraCosts } from "@/lib/api-client";

export const COSTS_KEY = ["costs"] as const;

export function useCostSummary() {
  return useQuery({
    queryKey: [...COSTS_KEY, "summary"],
    queryFn: getCostSummary,
    refetchInterval: 60_000, // refresh every minute — spend changes slowly
  });
}

export function useCostBreakdown(days = 30) {
  return useQuery({
    queryKey: [...COSTS_KEY, "breakdown", days],
    queryFn: () => getCostBreakdown(days),
  });
}

export function useInfraCosts(days = 7) {
  return useQuery({
    queryKey: [...COSTS_KEY, "infra", days],
    queryFn: () => getInfraCosts(days),
  });
}
