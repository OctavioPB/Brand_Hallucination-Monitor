"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getBrands,
  getBrand,
  getSPSScores,
  getHallucinations,
  getVectorMap,
  getCompetitors,
  updateBrandManifest,
  type BrandManifest,
} from "@/lib/api-client";

export const BRANDS_KEY = ["brands"] as const;
export const brandKey = (id: string) => ["brands", id] as const;
export const spsKey = (id: string) => ["brands", id, "sps"] as const;
export const hallucinationsKey = (id: string) => ["brands", id, "hallucinations"] as const;
export const vectorMapKey = (id: string) => ["brands", id, "vector-map"] as const;
export const competitorsKey = (id: string) => ["brands", id, "competitors"] as const;

export function useBrands() {
  return useQuery({ queryKey: BRANDS_KEY, queryFn: getBrands });
}

export function useBrand(id: string) {
  return useQuery({ queryKey: brandKey(id), queryFn: () => getBrand(id) });
}

export function useSPSScores(brandId: string) {
  return useQuery({
    queryKey: spsKey(brandId),
    queryFn: () => getSPSScores(brandId),
    enabled: !!brandId,
  });
}

export function useHallucinations(brandId: string, enabled = true) {
  return useQuery({
    queryKey: hallucinationsKey(brandId),
    queryFn: () => getHallucinations(brandId),
    enabled: enabled && !!brandId,
  });
}

export function useVectorMap(brandId: string, enabled = true) {
  return useQuery({
    queryKey: vectorMapKey(brandId),
    queryFn: () => getVectorMap(brandId),
    enabled: enabled && !!brandId,
    refetchInterval: 30_000,
  });
}

export function useCompetitors(brandId: string, enabled = true) {
  return useQuery({
    queryKey: competitorsKey(brandId),
    queryFn: () => getCompetitors(brandId),
    enabled: enabled && !!brandId,
  });
}

export function useUpdateBrandManifest(brandId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (manifest: BrandManifest) => updateBrandManifest(brandId, manifest),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: brandKey(brandId) });
    },
  });
}
