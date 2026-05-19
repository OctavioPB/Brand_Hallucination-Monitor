"use client";

import { useEffect, useRef } from "react";

export function DemoInit() {
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    if (localStorage.getItem("hallucin8_api_key")) return;

    (async () => {
      try {
        await fetch("/api/v1/onboarding/demo/seed", { method: "POST" });
        const res = await fetch("/api/v1/onboarding/demo/access");
        if (res.ok) {
          const { api_key } = await res.json();
          localStorage.setItem("hallucin8_api_key", api_key);
          window.location.reload();
        }
      } catch {
        // fail silently
      }
    })();
  }, []);

  return null;
}
