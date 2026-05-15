"use client";

import { useEffect, useRef } from "react";
import { analytics } from "@/lib/posthog";
import { brandTokens } from "@/lib/brand-tokens";

/**
 * Shepherd.js product tour — loaded lazily from CDN to avoid bundle bloat.
 * Styled per BRAND.md: dark navy background, gold accent, Fraunces headings.
 */

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Shepherd?: any;
  }
}

interface ProductTourProps {
  /** Called when the tour finishes or is cancelled. */
  onComplete?: () => void;
}

export function ProductTour({ onComplete }: ProductTourProps) {
  const initiated = useRef(false);

  useEffect(() => {
    if (initiated.current) return;
    initiated.current = true;

    loadShepherd().then((Shepherd) => {
      const tour = new Shepherd.Tour({
        useModalOverlay: true,
        defaultStepOptions: {
          cancelIcon: { enabled: true },
          scrollTo: { behavior: "smooth", block: "center" },
          modalOverlayOpeningRadius: 6,
        },
      });

      injectShepherdStyles();

      const steps: { attachTo?: { element: string; on: string }; title: string; text: string }[] = [
        {
          title: "Welcome to hallucin8",
          text: "This is your brand safety command centre. Let's take a 2-minute tour of the key features.",
        },
        {
          attachTo: { element: "[data-tour='brands-nav']", on: "bottom" },
          title: "Your brands",
          text: "Manage all your monitored brands here. Each brand has its own vector map and hallucination feed.",
        },
        {
          attachTo: { element: "[data-tour='sps-score']", on: "right" },
          title: "Semantic Proximity Score",
          text: "SPS measures how closely each concept is associated with your brand in AI latent space. Higher = stronger association.",
        },
        {
          attachTo: { element: "[data-tour='vector-map']", on: "left" },
          title: "Vector map",
          text: "Your brand's position relative to competitors and target concepts. Hover any point for details.",
        },
        {
          attachTo: { element: "[data-tour='alerts-nav']", on: "bottom" },
          title: "Alerts",
          text: "Set threshold rules to be notified via Slack or email when brand perception shifts.",
        },
        {
          attachTo: { element: "[data-tour='reports-nav']", on: "bottom" },
          title: "Reports",
          text: "Generate PDF audit reports on demand or schedule weekly digests.",
        },
        {
          title: "You're all set",
          text: "Trigger your first scan from the dashboard to see your brand in the vector space. Questions? Open the chat widget.",
        },
      ];

      steps.forEach((step, i) => {
        const isLast = i === steps.length - 1;
        tour.addStep({
          id: `step-${i}`,
          ...(step.attachTo ? { attachTo: step.attachTo } : {}),
          title: step.title,
          text: step.text,
          buttons: [
            ...(i > 0 ? [{ text: "Back", action: tour.back, classes: "shepherd-btn-secondary" }] : []),
            {
              text: isLast ? "Finish" : "Next →",
              action: isLast ? tour.complete : tour.next,
              classes: "shepherd-btn-primary",
            },
          ],
        });
      });

      tour.on("complete", async () => {
        analytics.tourCompleted();
        await fetch("/api/v1/onboarding/tour-complete", {
          method: "POST",
          headers: { "X-API-Key": localStorage.getItem("hallucin8_api_key") ?? "" },
        }).catch(() => undefined);
        onComplete?.();
      });

      tour.on("cancel", () => {
        onComplete?.();
      });

      tour.start();
    });
  }, [onComplete]);

  return null; // Shepherd renders its own DOM
}

async function loadShepherd(): Promise<typeof window.Shepherd> {
  if (window.Shepherd) return window.Shepherd;

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/shepherd.js@11/dist/js/shepherd.min.js";
    script.onload = () => resolve(window.Shepherd!);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function injectShepherdStyles() {
  if (document.getElementById("shepherd-brand-styles")) return;

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "https://cdn.jsdelivr.net/npm/shepherd.js@11/dist/css/shepherd.css";
  document.head.appendChild(link);

  const style = document.createElement("style");
  style.id = "shepherd-brand-styles";
  style.textContent = `
    .shepherd-element {
      border-radius: 12px !important;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
      border: 1px solid rgba(255,255,255,0.08) !important;
    }
    .shepherd-content {
      background: ${brandTokens.colors.dark} !important;
      padding: 24px !important;
    }
    .shepherd-header {
      background: transparent !important;
      padding: 0 0 12px 0 !important;
    }
    .shepherd-title {
      font-family: ${brandTokens.typography.fontDisplay} !important;
      font-size: 18px !important;
      font-weight: 300 !important;
      color: #fff !important;
    }
    .shepherd-text {
      font-family: ${brandTokens.typography.fontBody} !important;
      font-size: 13px !important;
      color: rgba(255,255,255,0.6) !important;
      line-height: 1.7 !important;
    }
    .shepherd-footer {
      padding: 16px 0 0 0 !important;
      background: transparent !important;
      border-top: 1px solid rgba(255,255,255,0.08) !important;
      gap: 8px !important;
    }
    .shepherd-btn-primary {
      background: ${brandTokens.colors.primary} !important;
      color: #fff !important;
      border: none !important;
      border-radius: 6px !important;
      font-family: ${brandTokens.typography.fontBody} !important;
      font-size: 9px !important;
      font-weight: 600 !important;
      letter-spacing: 2px !important;
      text-transform: uppercase !important;
      padding: 8px 16px !important;
      cursor: pointer !important;
    }
    .shepherd-btn-secondary {
      background: transparent !important;
      color: rgba(255,255,255,0.4) !important;
      border: 1px solid rgba(255,255,255,0.15) !important;
      border-radius: 6px !important;
      font-family: ${brandTokens.typography.fontBody} !important;
      font-size: 9px !important;
      letter-spacing: 2px !important;
      text-transform: uppercase !important;
      padding: 8px 14px !important;
      cursor: pointer !important;
    }
    .shepherd-cancel-icon {
      color: rgba(255,255,255,0.3) !important;
    }
    .shepherd-modal-overlay-container {
      fill: rgba(0,0,0,0.55) !important;
    }
  `;
  document.head.appendChild(style);
}
