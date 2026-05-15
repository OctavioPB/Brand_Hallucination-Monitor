/**
 * PostHog analytics client — tracks key user actions.
 * Loaded only in the browser; no PII is sent.
 */

declare global {
  interface Window {
    posthog?: {
      capture: (event: string, props?: Record<string, unknown>) => void;
      identify: (distinctId: string, traits?: Record<string, unknown>) => void;
      reset: () => void;
    };
  }
}

function ph() {
  if (typeof window === "undefined") return null;
  return window.posthog ?? null;
}

export const analytics = {
  /** Called once on login / session start. */
  identify(orgId: string) {
    ph()?.identify(orgId, { org_id: orgId });
  },

  /** User triggered a scan job. */
  scanTriggered(brandId: string, jobType: string) {
    ph()?.capture("scan_triggered", { brand_id: brandId, job_type: jobType });
  },

  /** User downloaded a report PDF. */
  reportDownloaded(reportId: string) {
    ph()?.capture("report_downloaded", { report_id: reportId });
  },

  /** User acknowledged an alert. */
  alertAcknowledged(alertId: string, severity: string) {
    ph()?.capture("alert_acknowledged", { alert_id: alertId, severity });
  },

  /** User completed the onboarding wizard. */
  onboardingCompleted(brandSlug: string) {
    ph()?.capture("onboarding_completed", { brand_slug: brandSlug });
  },

  /** User finished the product tour. */
  tourCompleted() {
    ph()?.capture("tour_completed");
  },

  /** User submitted NPS score. */
  npsSubmitted(score: number) {
    ph()?.capture("nps_submitted", { score });
  },

  /** User clicked "Report Issue" in error boundary. */
  issueReported(errorMessage: string) {
    ph()?.capture("issue_reported", { error_message: errorMessage.slice(0, 200) });
  },

  reset() {
    ph()?.reset();
  },
};

/** Call once from app layout to bootstrap PostHog. */
export function initPostHog(apiKey: string, host = "https://app.posthog.com") {
  if (typeof window === "undefined" || !apiKey || window.posthog) return;

  const script = document.createElement("script");
  script.innerHTML = `
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]);t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+" (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys onSessionId".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
    posthog.init('${apiKey}', {api_host: '${host}', autocapture: false, capture_pageview: true});
  `;
  document.head.appendChild(script);
}
