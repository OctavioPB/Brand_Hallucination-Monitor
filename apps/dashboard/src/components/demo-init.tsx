"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function DemoInit() {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (localStorage.getItem("hallucin8_api_key")) return;

    (async () => {
      try {
        await fetch("/api/v1/onboarding/demo/seed", { method: "POST" });
        const res = await fetch("/api/v1/onboarding/demo/access");
        if (res.ok) {
          const { api_key } = await res.json();
          localStorage.setItem("hallucin8_api_key", api_key);
          await queryClient.invalidateQueries();
        }
      } catch {
        // fail silently
      }
    })();
  }, [queryClient]);

  return null;
}
