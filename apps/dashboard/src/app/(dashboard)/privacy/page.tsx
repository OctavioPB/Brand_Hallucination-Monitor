import { brandTokens } from "@/lib/brand-tokens";

export const metadata = { title: "Privacy Policy — hallucin8" };

export default function PrivacyPage() {
  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "48px 24px" }}>
      <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "4px", textTransform: "uppercase", color: brandTokens.colors.gold, marginBottom: 12 }}>
        Legal
      </div>
      <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 36, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 8 }}>
        Privacy Policy
      </h1>
      <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: brandTokens.colors.mid, marginBottom: 40 }}>
        Last updated: 15 May 2026 · Effective: 15 May 2026
      </p>

      <ProseSection title="1. Controller">
        <p>hallucin8 is operated by OPB AI Mastery Lab (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;). For questions about this policy, contact <a href="mailto:privacy@hallucin8.io" style={{ color: brandTokens.colors.primary60 }}>privacy@hallucin8.io</a>.</p>
      </ProseSection>

      <ProseSection title="2. Data we collect">
        <ul>
          <li><strong>Account data:</strong> Organization name, work email address. No personal payment data — billing is handled by Stripe.</li>
          <li><strong>Brand manifest:</strong> Brand attributes and competitor names you provide. These are your data and remain under your control.</li>
          <li><strong>Usage analytics:</strong> Anonymised event telemetry via PostHog (page views, feature interactions). No PII is sent.</li>
          <li><strong>Support conversations:</strong> Messages sent through the Intercom chat widget.</li>
          <li><strong>Log data:</strong> Server logs (IP address, timestamps, request paths) retained for 30 days.</li>
        </ul>
      </ProseSection>

      <ProseSection title="3. How we use your data">
        <ul>
          <li>Providing the hallucin8 service (brand monitoring, hallucination detection, report generation)</li>
          <li>Sending transactional emails (signup confirmation, onboarding sequence, report digests)</li>
          <li>Improving the product based on aggregated usage analytics</li>
          <li>Customer support</li>
        </ul>
        <p>We do <strong>not</strong> sell your data to third parties.</p>
      </ProseSection>

      <ProseSection title="4. Third-party processors">
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${brandTokens.colors.primary10}` }}>
              <Th>Processor</Th><Th>Purpose</Th><Th>Region</Th>
            </tr>
          </thead>
          <tbody>
            {[
              ["OpenAI", "Embedding generation, LLM probing", "US"],
              ["Google (Gemini)", "Weekly deep probing", "US"],
              ["Resend", "Transactional email delivery", "US"],
              ["PostHog", "Product analytics (anonymised)", "EU (cloud.posthog.com)"],
              ["Intercom", "Customer support chat", "US"],
              ["Sentry", "Error tracking", "US"],
              ["Google Cloud Platform", "Infrastructure hosting", "EU (europe-west4)"],
            ].map(([p, pur, reg]) => (
              <tr key={p} style={{ borderBottom: `1px solid ${brandTokens.colors.primary10}` }}>
                <Td>{p}</Td><Td>{pur}</Td><Td>{reg}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </ProseSection>

      <ProseSection title="5. Data retention">
        <p>We retain your account and brand data for as long as your account is active. You may request deletion at any time (see §7). Log data is deleted after 30 days. Backups are retained for 30 days then purged.</p>
      </ProseSection>

      <ProseSection title="6. Security">
        <p>Data in transit is encrypted with TLS 1.3. Data at rest is encrypted with AES-256. We enforce strict per-organisation data isolation (Row Level Security) — one customer cannot access another&apos;s data. API keys are stored as bcrypt hashes and the raw value is shown only once at creation.</p>
      </ProseSection>

      <ProseSection title="7. Your rights (GDPR)">
        <p>If you are in the EEA or UK, you have the right to access, rectify, port, restrict, and erase your personal data. To exercise any of these rights, email <a href="mailto:privacy@hallucin8.io" style={{ color: brandTokens.colors.primary60 }}>privacy@hallucin8.io</a> or call our data deletion API endpoint: <code style={{ fontFamily: brandTokens.typography.fontMono, fontSize: 12, backgroundColor: brandTokens.colors.primary10, padding: "2px 6px", borderRadius: 4 }}>DELETE /api/v1/organizations/{"{your-org-id}"}</code>. This cascades all data associated with your organisation.</p>
      </ProseSection>

      <ProseSection title="8. Cookies">
        <p>We use only technically necessary cookies (session authentication). We do not use third-party advertising cookies.</p>
      </ProseSection>

      <ProseSection title="9. Changes to this policy">
        <p>We will notify you by email and in-app at least 14 days before making material changes. The effective date at the top of this page indicates the current version.</p>
      </ProseSection>
    </div>
  );
}

function ProseSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 36 }}>
      <h2 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 20, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 12, borderBottom: `1px solid ${brandTokens.colors.primary10}`, paddingBottom: 8 }}>
        {title}
      </h2>
      <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 14, color: brandTokens.colors.mid, lineHeight: 1.8 }}>
        {children}
      </div>
    </section>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ padding: "8px 12px", textAlign: "left", fontFamily: brandTokens.typography.fontBody, fontSize: 10, letterSpacing: "2px", textTransform: "uppercase", color: brandTokens.colors.mid, fontWeight: 500 }}>{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: "10px 12px", fontFamily: brandTokens.typography.fontBody, fontSize: 13, color: brandTokens.colors.mid }}>{children}</td>;
}
