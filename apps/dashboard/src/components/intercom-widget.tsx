"use client";

import { useEffect } from "react";

/**
 * Intercom support widget — lazy-loaded, respects NEXT_PUBLIC_INTERCOM_APP_ID.
 * The launcher button is styled by Intercom's own SDK; we control only the
 * custom launcher offset to avoid overlapping our NPS survey.
 */

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Intercom?: (...args: any[]) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    intercomSettings?: Record<string, any>;
  }
}

interface IntercomWidgetProps {
  orgId?: string;
  email?: string;
  name?: string;
}

export function IntercomWidget({ orgId, email, name }: IntercomWidgetProps) {
  const appId = process.env.NEXT_PUBLIC_INTERCOM_APP_ID;

  useEffect(() => {
    if (!appId) return;

    window.intercomSettings = {
      api_base: "https://api-iam.intercom.io",
      app_id: appId,
      // Position above the NPS survey widget that sits at bottom-right
      vertical_padding: 80,
      horizontal_padding: 24,
      ...(orgId ? { company: { company_id: orgId, name: orgId } } : {}),
      ...(email ? { email } : {}),
      ...(name ? { name } : {}),
    };

    if (window.Intercom) {
      window.Intercom("reattach_activator");
      window.Intercom("update", window.intercomSettings);
      return;
    }

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://widget.intercom.io/widget/${appId}`;
    document.head.appendChild(script);
    script.onload = () => window.Intercom?.("boot", window.intercomSettings);
  }, [appId, orgId, email, name]);

  return null;
}
