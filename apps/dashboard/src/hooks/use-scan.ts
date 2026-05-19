"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { triggerScanJob, getScanJob, type ScanJobCreate } from "@/lib/api-client";

export function useTriggerScan() {
  return useMutation({
    mutationFn: (payload: ScanJobCreate) => triggerScanJob(payload),
  });
}

export function useScanJob(jobId: string | null) {
  return useQuery({
    queryKey: ["scan-job", jobId],
    queryFn: () => getScanJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "running") return 3000;
      return false;
    },
  });
}
