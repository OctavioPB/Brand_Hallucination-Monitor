"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAlerts, acknowledgeAlert } from "@/lib/api-client";

export const ALERTS_KEY = ["alerts"] as const;

export function useAlerts(opts?: {
  acknowledged?: boolean;
  severity?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: [...ALERTS_KEY, opts],
    queryFn: () => getAlerts(opts),
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ALERTS_KEY });
    },
  });
}
