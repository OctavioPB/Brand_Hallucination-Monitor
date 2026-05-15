import { brandTokens } from "@/lib/brand-tokens";

export const metadata = { title: "Terms of Service — hallucin8" };

export default function TermsPage() {
  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "48px 24px" }}>
      <div style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 9, letterSpacing: "4px", textTransform: "uppercase", color: brandTokens.colors.gold, marginBottom: 12 }}>
        Legal
      </div>
      <h1 style={{ fontFamily: brandTokens.typography.fontDisplay, fontSize: 36, fontWeight: 300, color: brandTokens.colors.dark, marginBottom: 8 }}>
        Terms of Service
      </h1>
      <p style={{ fontFamily: brandTokens.typography.fontBody, fontSize: 12, color: brandTokens.colors.mid, marginBottom: 40 }}>
        Last updated: 15 May 2026 · Effective: 15 May 2026
      </p>

      <ProseSection title="1. Acceptance">
        <p>By creating an account or using hallucin8 you agree to these Terms. If you are accepting on behalf of a company, you represent you have authority to bind that company.</p>
      </ProseSection>

      <ProseSection title="2. The service">
        <p>hallucin8 provides brand monitoring, AI-model perception analysis, hallucination detection, and reporting tools (&ldquo;the Service&rdquo;). The Service is provided &ldquo;as is&rdquo; during the beta period.</p>
      </ProseSection>

      <ProseSection title="3. Acceptable use">
        <p>You may not use the Service to:</p>
        <ul>
          <li>Monitor individuals or engage in surveillance of natural persons</li>
          <li>Generate or distribute disinformation or synthetic propaganda</li>
          <li>Attempt to manipulate AI models in a deceptive or harmful manner</li>
          <li>Violate any applicable law or third-party terms of service</li>
          <li>Resell or white-label the Service without written permission</li>
        </ul>
      </ProseSection>

      <ProseSection title="4. Data ownership">
        <p>You retain full ownership of your brand manifests, monitoring data, and reports. By using the Service you grant us a limited licence to process that data solely to deliver the Service to you. We do not use your brand data to train AI models.</p>
      </ProseSection>

      <ProseSection title="5. Subscription and billing">
        <p>The beta period is free. Paid plans will be announced with at least 30 days notice before any charges apply. Billing is handled by Stripe; we do not store card details.</p>
      </ProseSection>

      <ProseSection title="6. Intellectual property">
        <p>hallucin8 and its underlying software remain the intellectual property of OPB AI Mastery Lab. You receive a non-exclusive, non-transferable licence to access the Service during your subscription.</p>
      </ProseSection>

      <ProseSection title="7. Limitation of liability">
        <p>To the maximum extent permitted by law, our liability is limited to the fees you paid in the 12 months preceding the claim. We are not liable for indirect, incidental, or consequential damages. Brand monitoring results are informational and not legal or compliance advice.</p>
      </ProseSection>

      <ProseSection title="8. Termination">
        <p>Either party may terminate at any time. Upon termination, your data will be retained for 30 days (allowing export) and then permanently deleted, including all backups.</p>
      </ProseSection>

      <ProseSection title="9. Governing law">
        <p>These Terms are governed by the laws of Mexico (CDMX). Disputes shall be resolved by the courts of Mexico City.</p>
      </ProseSection>

      <ProseSection title="10. Changes">
        <p>We may update these Terms with 14 days notice via email and in-app banner. Continued use after the effective date constitutes acceptance.</p>
      </ProseSection>

      <ProseSection title="11. Contact">
        <p>Legal questions: <a href="mailto:legal@hallucin8.io" style={{ color: brandTokens.colors.primary60 }}>legal@hallucin8.io</a></p>
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
