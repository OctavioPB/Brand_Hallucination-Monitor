"use client";

import { useState } from "react";
import { brandTokens as t } from "@/lib/brand-tokens";
import { Eyebrow } from "@/components/eyebrow";

type View = "business" | "engineering";

export default function InfoPage() {
  const [view, setView] = useState<View>("business");
  return (
    <div style={{ backgroundColor: "#080e1c", minHeight: "100vh" }}>
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "64px 48px" }}>
        <p style={{ fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "4px", textTransform: "uppercase", color: t.colors.goldLight, marginBottom: 14 }}>
          hallucin8 — product overview
        </p>
        <h1 style={{ fontFamily: t.typography.fontDisplay, fontSize: 46, fontWeight: 300, color: "#fff", lineHeight: 1.15, margin: "0 0 18px" }}>
          How it works
        </h1>
        <p style={{ fontFamily: t.typography.fontBody, fontSize: 15, color: "rgba(255,255,255,0.5)", lineHeight: 1.75, maxWidth: 640, marginBottom: 48 }}>
          A semantic intelligence layer that measures how AI language models perceive, describe,
          and position any brand — continuously, across models and intent domains.
        </p>

        <div style={{ display: "flex", gap: 2, borderBottom: "1px solid rgba(255,255,255,0.07)", marginBottom: 56 }}>
          {(["business", "engineering"] as View[]).map((v) => (
            <button key={v} onClick={() => setView(v)} style={{
              fontFamily: t.typography.fontBody, fontSize: 10, letterSpacing: "2.5px",
              textTransform: "uppercase", padding: "12px 24px", background: "none", border: "none",
              cursor: "pointer",
              color: view === v ? t.colors.goldLight : "rgba(255,255,255,0.35)",
              borderBottom: view === v ? `2px solid ${t.colors.gold}` : "2px solid transparent",
              marginBottom: -1,
            }}>
              {v === "business" ? "Business view" : "Engineering view"}
            </button>
          ))}
        </div>

        {view === "business" ? <BusinessView /> : <EngineeringView />}
      </div>
    </div>
  );
}

// ── Business View ─────────────────────────────────────────────────────────────

function BusinessView() {
  return (
    <div>
      <Section eyebrow="The problem" title={<>AI is the new discovery layer —{" "}<em style={{ fontStyle: "italic" }}>and it has opinions</em></>}>
        <p style={body}>
          When a potential customer asks ChatGPT, Gemini, or Perplexity which vendor to use,
          the AI model — not your marketing team — constructs the answer. That model has processed
          billions of documents and built an internal representation of your brand: what it does,
          who it serves, how it compares to competitors, and what it costs. That representation
          may be accurate. It may also attribute capabilities your product lacks, conflate your
          brand with a competitor, or position you in the wrong market segment entirely.
        </p>
        <p style={{ ...body, marginTop: 16 }}>
          This is not a fringe scenario. Every AI-mediated interaction draws from the model&apos;s
          latent knowledge, and that knowledge updates asynchronously as models are retrained.
          There is no notification system, no audit trail, and no baseline — which means brand
          teams have no visibility into what AI is saying about them at the moment it matters most.
        </p>
      </Section>

      <Section eyebrow="What it does" title="Three core capabilities">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
          <CapCard num="01" accent={t.status.danger.base} title="Hallucination detection"
            body="The system sends structured probe prompts to each configured LLM on a schedule. Responses are compared against the brand manifest — verified attributes, known false claims, regulatory phrases, competitor names — and flagged when the model's output deviates from ground truth." />
          <CapCard num="02" accent={t.colors.goldLight} title="Semantic proximity scoring"
            body="Every brand occupies a measurable position in a model's latent vector space. The Semantic Proximity Score quantifies how strongly a model associates your brand with specific concepts — reliability, compliance, market leadership — on a continuous 0–1 scale per intent cluster, tracked over time." />
          <CapCard num="03" accent={t.status.success.base} title="Drift alerting"
            body="Configurable rules trigger when SPS scores cross thresholds or when a probe result crosses a severity boundary. Alerts route to the dashboard, webhook endpoints, or email — providing structured signal at the moment a model's perception shifts." />
        </div>
      </Section>

      <Section eyebrow="Audience" title="Who it helps">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
          <AudienceCard role="Brand & Communications"
            description="Identifies when AI narratives diverge from official positioning before they reach buyers. Provides evidence-backed data to track the gap between intended and perceived brand identity." />
          <AudienceCard role="Product Marketing"
            description="Shows which intent clusters the brand wins and loses in AI-mediated discovery, at the model level. Informs content strategy based on what models currently believe, not just what was published." />
          <AudienceCard role="Compliance & Legal"
            description="Audits LLM outputs for regulatory claims — HIPAA-compliant, FDA-cleared, guaranteed returns — that must never be attributed to the brand. Provides timestamped evidence of what each model said and when." />
          <AudienceCard role="Demand Generation"
            description="Maps how AI shapes top-of-funnel discovery before a prospect reaches the website. Surfaces the intent categories where AI positions the brand strongly versus where it defers to competitors." />
        </div>
      </Section>

      <Section eyebrow="Measurement framework" title="Six intent clusters"
        description="Brand perception is structured around six clusters derived from purchase-intent research. Each cluster is scored independently, giving teams a multidimensional view of how AI models position the brand relative to competitors.">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {([
            ["Reliability",       t.colors.primary60],
            ["Innovation",        t.status.strategic.base],
            ["Pricing / Value",   t.status.warning.base],
            ["Market Leadership", t.colors.goldLight],
            ["Compliance",        t.status.success.base],
            ["Support Quality",   t.status.danger.base],
          ] as [string, string][]).map(([label, color]) => (
            <div key={label} style={{ padding: "10px 20px", borderRadius: 8, border: `1px solid ${color}40`, backgroundColor: `${color}14`, fontFamily: t.typography.fontBody, fontSize: 12, color, letterSpacing: "0.5px" }}>
              {label}
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Continuous monitoring" title="The measurement loop">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 1, backgroundColor: "rgba(255,255,255,0.06)", borderRadius: 10, overflow: "hidden" }}>
          {[
            { step: "1", label: "Probe",  detail: "Scheduled queries to GPT-4o, Gemini, Claude, Perplexity against your brand manifest at configurable intervals." },
            { step: "2", label: "Embed",  detail: "Responses and brand signals are embedded into 1536-dim vectors via OpenAI text-embedding-3-small." },
            { step: "3", label: "Score",  detail: "Cosine similarity is computed against concept anchors for each of the six intent clusters, producing SPS scores." },
            { step: "4", label: "Alert",  detail: "Score deltas are evaluated against configurable rules. Violations trigger structured alerts via dashboard, webhook, or email." },
          ].map(({ step, label, detail }) => (
            <div key={step} style={{ backgroundColor: "#0d1424", padding: "24px 20px" }}>
              <div style={{ fontFamily: t.typography.fontDisplay, fontSize: 36, fontWeight: 300, color: "rgba(255,255,255,0.12)", lineHeight: 1, marginBottom: 10 }}>{step}</div>
              <div style={{ fontFamily: t.typography.fontBody, fontSize: 13, color: "#fff", fontWeight: 500, marginBottom: 8 }}>{label}</div>
              <div style={{ fontFamily: t.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.45)", lineHeight: 1.7 }}>{detail}</div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

// ── Engineering View ──────────────────────────────────────────────────────────

function EngineeringView() {
  return (
    <div>
      <Section eyebrow="System architecture" title="Component overview"
        description="Four horizontal layers: ingestion, processing, persistence, and delivery. All embedding and scoring work is asynchronous — nothing compute-intensive runs on the API request thread.">
        <div style={{ backgroundColor: "#0d1424", borderRadius: 10, padding: 24, border: "1px solid rgba(255,255,255,0.06)" }}>
          <ArchitectureDiagram />
        </div>
      </Section>

      <Section eyebrow="Data flow" title="Pipeline steps">
        <div>
          {[
            { n: "01", title: "Dual ingestion",
              detail: "Data enters through two parallel paths. A Kafka consumer processes brand mention events from external crawlers and review aggregators. In parallel, a Celery beat scheduler dispatches probe queries to configured LLMs (GPT-4o, Gemini 1.5 Pro, Claude Opus) at configurable intervals." },
            { n: "02", title: "Embedding",
              detail: "Workers consume raw text from both paths, apply cleaning and chunking, then call the OpenAI Embeddings API (text-embedding-3-small) in batches. Results are 1536-dimensional float32 vectors. Identical inputs are cached in Redis to avoid redundant API calls." },
            { n: "03", title: "Vector storage & graph write",
              detail: "Vectors are upserted into Qdrant, partitioned by brand ID and intent cluster. The scoring engine computes cosine similarity between each new vector and pre-anchored concept vectors for all six clusters, producing SPS scores written to PostgreSQL. Semantic relationships are written to Neo4j as (Brand)-[:ASSOCIATED_WITH {score}]->(Concept) edges." },
            { n: "04", title: "Hallucination evaluation",
              detail: "LLM probe responses are parsed against the brand manifest across three detection categories: attribute errors (false_attributes), competitor confusion (competitor_list), and regulatory claims (regulatory_claims_to_avoid). Each match is stored as a ProbeResultORM with LLM source, prompt, response excerpt, and confidence score." },
            { n: "05", title: "Alert evaluation & delivery",
              detail: "After each scoring cycle, configured alert rules are evaluated. A rule fires when an SPS delta exceeds a threshold, when a score falls below a floor, or when a probe result crosses a severity boundary. Triggered rules create AlertORM records and dispatch via HTTP webhook, Resend email, and in-dashboard notifications." },
          ].map(({ n, title, detail }, i, arr) => (
            <div key={n} style={{ display: "flex", gap: 24, padding: "24px 0", borderBottom: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.06)" : "none" }}>
              <div style={{ fontFamily: t.typography.fontDisplay, fontSize: 28, fontWeight: 300, color: "rgba(255,255,255,0.15)", flexShrink: 0, width: 40, paddingTop: 2 }}>{n}</div>
              <div>
                <div style={{ fontFamily: t.typography.fontBody, fontSize: 13, fontWeight: 600, color: "#fff", marginBottom: 8 }}>{title}</div>
                <p style={{ fontFamily: t.typography.fontBody, fontSize: 13, color: "rgba(255,255,255,0.5)", lineHeight: 1.75, margin: 0 }}>{detail}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Core algorithm" title="Semantic Proximity Score">
        <p style={body}>
          The Semantic Proximity Score is a cosine similarity measure between a brand embedding and a
          concept anchor vector, both in the 1536-dimensional space produced by text-embedding-3-small.
        </p>
        <div style={{ backgroundColor: "#0d1424", borderRadius: 10, padding: "20px 28px", border: "1px solid rgba(255,255,255,0.08)", margin: "20px 0", fontFamily: t.typography.fontMono, fontSize: 14, color: t.colors.goldLight, letterSpacing: "0.5px" }}>
          SPS(b, c) = cos(b, c) = (b · c) / (‖b‖ · ‖c‖)
        </div>
        <p style={body}>
          Where <code style={inlineCode}>b ∈ ℝ¹⁵³⁶</code> is the brand&apos;s mean embedding (computed over the
          N most recent probe results or from the brand manifest attributes), and{" "}
          <code style={inlineCode}>c ∈ ℝ¹⁵³⁶</code> is the concept anchor vector for a given intent cluster.
          Concept anchor vectors are computed as the centroid of 50–200 representative text fragments per
          cluster from a curated seed dataset. Scores are computed per cluster per LLM, producing a
          [brand × cluster × model] matrix over time.
        </p>
        <div style={{ marginTop: 28 }}>
          <p style={{ fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "3px", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 16 }}>
            Computation pipeline
          </p>
          <SpsFlowDiagram />
        </div>
      </Section>

      <Section eyebrow="Detection" title="Hallucination categories">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
          {[
            { label: "Attribute error",     accent: t.status.danger.base,    field: "false_attributes",
              description: "The model attributes a property to the brand that appears in false_attributes. Example: claiming a B2B enterprise product is free, open-source, or consumer-focused." },
            { label: "Competitor confusion", accent: t.status.warning.base,   field: "competitor_list",
              description: "The model conflates the brand with a name from competitor_list — applying competitor-specific claims, pricing, or features when describing the monitored brand." },
            { label: "Regulatory claim",    accent: t.status.strategic.base, field: "regulatory_claims_to_avoid",
              description: "The model outputs a phrase from regulatory_claims_to_avoid when describing the brand. Example: attributing HIPAA compliance or FDA clearance without those certifications." },
          ].map(({ label, accent, field, description }) => (
            <div key={label} style={{ backgroundColor: "#0d1424", borderRadius: 10, padding: "20px 22px", border: `1px solid ${accent}30` }}>
              <div style={{ fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: accent, marginBottom: 10 }}>{label}</div>
              <p style={{ fontFamily: t.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.5)", lineHeight: 1.7, margin: "0 0 14px" }}>{description}</p>
              <code style={{ fontFamily: t.typography.fontMono, fontSize: 9, color: t.colors.goldLight, backgroundColor: "rgba(200,152,42,0.12)", padding: "2px 6px", borderRadius: 4 }}>
                manifest.{field}
              </code>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Implementation" title="Tech stack">
        <div style={{ backgroundColor: "#0d1424", borderRadius: 10, overflow: "hidden", border: "1px solid rgba(255,255,255,0.06)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {["Layer", "Technology", "Role"].map((h) => (
                  <th key={h} style={{ padding: "10px 20px", textAlign: "left", fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: "rgba(255,255,255,0.3)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ["API",          "FastAPI 0.111 + SQLAlchemy 2",              "Async REST/SSE — request handling, auth, CRUD"],
                ["Task queue",   "Celery + Redis",                            "Background embedding jobs, probe scheduling, alert delivery"],
                ["Stream",       "Apache Kafka",                              "Brand mention ingestion — multi-consumer fan-out"],
                ["Embeddings",   "OpenAI text-embedding-3-small",             "1536-dim vector generation, ~$0.00002 / 1K tokens"],
                ["Vector DB",    "Qdrant",                                    "Cosine similarity search, partitioned by brand and cluster"],
                ["Graph DB",     "Neo4j 5",                                   "Semantic relationship storage, Cypher traversal"],
                ["Relational",   "PostgreSQL + Alembic",                      "Orgs, brands, SPS scores, probe results, alerts, scan jobs"],
                ["Cache",        "Redis 7",                                   "Embedding cache, rate limit counters, Celery broker"],
                ["LLM probing",  "GPT-4o · Gemini 1.5 Pro · Claude Opus",    "Structured brand perception probe queries"],
                ["Frontend",     "Next.js 14 (App Router)",                  "Dashboard — React Server Components, TanStack Query v5"],
                ["Orchestration","Apache Airflow 2.9",                        "Scheduled vector ETL DAGs"],
                ["Auth",         "Per-org API keys (X-API-Key)",             "PBKDF2-HMAC-SHA256 hashed, scoped per organization"],
              ].map(([layer, tech, role]) => (
                <tr key={layer} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: "12px 20px", fontFamily: t.typography.fontBody, fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "1px", textTransform: "uppercase", whiteSpace: "nowrap" }}>{layer}</td>
                  <td style={{ padding: "12px 20px", fontFamily: t.typography.fontMono, fontSize: 11, color: t.colors.goldLight }}>{tech}</td>
                  <td style={{ padding: "12px 20px", fontFamily: t.typography.fontBody, fontSize: 12, color: "rgba(255,255,255,0.45)" }}>{role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Interface" title="API surface">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
          {[
            { label: "REST endpoints",
              content: "/api/v1/brands           CRUD brand records and manifests\n/api/v1/brands/{id}/scores  SPS history per cluster\n/api/v1/brands/{id}/probes  probe results and hallucinations\n/api/v1/alerts             alert management and acknowledgement\n/api/v1/scan-jobs          job dispatch and status polling" },
            { label: "SSE streaming",
              content: "GET /api/v1/brands/{id}/scores/stream\n\nPushes score updates in real time as each scan job completes. Clients receive JSON events:\n{ cluster, sps, delta, timestamp }\nConnection kept alive with 30-second heartbeats." },
            { label: "Authentication",
              content: "Tenant requests: X-API-Key: hk_...\nScoped per organization. Keys stored as PBKDF2-HMAC-SHA256 hashes with random 32-byte salt.\n\nAdmin endpoints: X-Admin-Secret header. Separate auth flow — not part of the per-org key system." },
            { label: "Rate limiting",
              content: "Sliding window per org, configurable per plan tier. State stored in Redis.\n\nResponse headers:\nX-RateLimit-Limit\nX-RateLimit-Remaining\nX-RateLimit-Reset" },
          ].map(({ label, content }) => (
            <div key={label} style={{ backgroundColor: "#0d1424", borderRadius: 10, padding: "20px 22px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div style={{ fontFamily: t.typography.fontBody, fontSize: 9, letterSpacing: "2px", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 12 }}>{label}</div>
              <pre style={{ fontFamily: t.typography.fontMono, fontSize: 11, color: "rgba(255,255,255,0.55)", lineHeight: 1.8, margin: 0, whiteSpace: "pre-wrap" }}>{content}</pre>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

// ── Architecture SVG ──────────────────────────────────────────────────────────

function SvgBox({ x, y, w = 166, h = 70, label, sub, accent }: {
  x: number; y: number; w?: number; h?: number; label: string; sub?: string; accent: string;
}) {
  const cx = x + w / 2;
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={5} fill="rgba(8,14,28,0.95)" stroke={accent} strokeWidth={1} />
      <text x={cx} y={y + (sub ? h / 2 - 9 : h / 2)} textAnchor="middle" dominantBaseline="central"
            fill="white" fontSize={11} style={{ fontFamily: t.typography.fontBody, fontWeight: "500" }}>
        {label}
      </text>
      {sub && (
        <text x={cx} y={y + h / 2 + 11} textAnchor="middle" dominantBaseline="central"
              fill="rgba(255,255,255,0.38)" fontSize={8.5} style={{ fontFamily: t.typography.fontBody }}>
          {sub}
        </text>
      )}
    </g>
  );
}

function SvgArrow({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.22)" strokeWidth={1.2} markerEnd="url(#ah)" />;
}

function ArchitectureDiagram() {
  // Layout constants
  // Rows: y=13, 120, 227, 334  h=70  bands: y=0,107,214,321  h=96
  // Row 1 & 4: 3 boxes  w=226  gap=15  x: 80, 321, 562
  // Row 2 & 3: 4 boxes  w=166  gap=15  x: 80, 261, 442, 623
  return (
    <svg viewBox="0 0 790 420" style={{ width: "100%", display: "block" }}>
      <defs>
        <marker id="ah" markerWidth={7} markerHeight={5} refX={7} refY={2.5} orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill="rgba(255,255,255,0.3)" />
        </marker>
      </defs>

      {/* Swimlane bands */}
      <rect x={0} y={0}   width={790} height={96} rx={6} fill="rgba(0,51,102,0.3)" />
      <rect x={0} y={107} width={790} height={96} rx={6} fill="rgba(124,77,189,0.18)" />
      <rect x={0} y={214} width={790} height={96} rx={6} fill="rgba(39,185,124,0.13)" />
      <rect x={0} y={321} width={790} height={96} rx={6} fill="rgba(200,152,42,0.1)" />

      {/* Swimlane labels — rotated vertical text */}
      {([["INGESTION", 48], ["PROCESSING", 155], ["PERSISTENCE", 262], ["DELIVERY", 369]] as [string, number][]).map(([lbl, cy]) => (
        <text key={lbl} transform={`rotate(-90, 36, ${cy})`} x={36} y={cy}
              textAnchor="middle" dominantBaseline="central"
              fill="rgba(255,255,255,0.28)" fontSize={7} letterSpacing={1.8}
              style={{ fontFamily: t.typography.fontBody }}>
          {lbl}
        </text>
      ))}

      {/* ROW 1 — INGESTION */}
      <SvgBox x={80}  y={13} w={226} h={70} label="External Sources"  sub="brand mentions · reviews · articles"    accent="rgba(0,82,163,0.85)" />
      <SvgBox x={321} y={13} w={226} h={70} label="LLM Probe Engine"  sub="GPT-4o · Gemini 1.5 · Claude Opus"      accent="rgba(0,82,163,0.85)" />
      <SvgBox x={562} y={13} w={226} h={70} label="Brand Manifest"    sub="true attrs · false attrs · competitors"  accent="rgba(200,152,42,0.75)" />

      {/* ROW 2 — PROCESSING */}
      <SvgBox x={80}  y={120} label="Kafka Topics"       sub="brand-events stream"      accent="rgba(124,77,189,0.8)" />
      <SvgBox x={261} y={120} label="Celery Workers"     sub="async task pool · Redis"  accent="rgba(124,77,189,0.8)" />
      <SvgBox x={442} y={120} label="OpenAI Embeddings"  sub="text-embedding-3-small"   accent="rgba(124,77,189,0.8)" />
      <SvgBox x={623} y={120} label="Scoring Engine"     sub="cosine sim · SPS [0–1]"   accent="rgba(124,77,189,0.8)" />

      {/* ROW 3 — PERSISTENCE */}
      <SvgBox x={80}  y={227} label="Qdrant"      sub="vector store · 1536-dim"    accent="rgba(39,185,124,0.7)" />
      <SvgBox x={261} y={227} label="Neo4j"       sub="knowledge graph"             accent="rgba(39,185,124,0.7)" />
      <SvgBox x={442} y={227} label="PostgreSQL"  sub="metadata · orgs · jobs"      accent="rgba(39,185,124,0.7)" />
      <SvgBox x={623} y={227} label="Redis"       sub="cache · queues · rate lim"   accent="rgba(39,185,124,0.7)" />

      {/* ROW 4 — DELIVERY */}
      <SvgBox x={80}  y={334} w={226} h={70} label="FastAPI REST / SSE"  sub="/api/v1/ · versioned · auth"    accent="rgba(200,152,42,0.75)" />
      <SvgBox x={321} y={334} w={226} h={70} label="Next.js Dashboard"  sub="App Router · TanStack Query"    accent="rgba(200,152,42,0.75)" />
      <SvgBox x={562} y={334} w={226} h={70} label="Webhooks / Alerts"  sub="HTTP · Resend email · push"     accent="rgba(200,152,42,0.75)" />

      {/* ARROWS row1 → row2 */}
      <SvgArrow x1={193} y1={83} x2={163} y2={120} />
      <SvgArrow x1={434} y1={83} x2={344} y2={120} />
      <SvgArrow x1={675} y1={83} x2={706} y2={120} />

      {/* ARROWS row2 horizontal (gap=15, arrow crosses it) */}
      <SvgArrow x1={246} y1={155} x2={261} y2={155} />
      <SvgArrow x1={427} y1={155} x2={442} y2={155} />
      <SvgArrow x1={608} y1={155} x2={623} y2={155} />

      {/* ARROWS row2 → row3 (straight down, cx aligned) */}
      <SvgArrow x1={163} y1={190} x2={163} y2={227} />
      <SvgArrow x1={344} y1={190} x2={344} y2={227} />
      <SvgArrow x1={525} y1={190} x2={525} y2={227} />
      <SvgArrow x1={706} y1={190} x2={706} y2={227} />

      {/* ARROWS row3 → row4 */}
      <SvgArrow x1={163} y1={297} x2={193} y2={334} />
      <path d="M 525 297 Q 360 315 193 334"
            stroke="rgba(255,255,255,0.18)" strokeWidth={1.2} fill="none" markerEnd="url(#ah)" />

      {/* ARROWS row4 horizontal */}
      <SvgArrow x1={306} y1={369} x2={321} y2={369} />
      <SvgArrow x1={547} y1={369} x2={562} y2={369} />
    </svg>
  );
}

// ── SPS Flow Diagram ──────────────────────────────────────────────────────────

function SpsFlowDiagram() {
  const steps = [
    { label: "Brand query",             sub: "natural language" },
    { label: "text-embedding-3-small",  sub: "OpenAI API" },
    { label: "1536-dim vector",         sub: "float32" },
    { label: "Cosine similarity",       sub: "vs concept anchors" },
    { label: "SPS  0.0 – 1.0",          sub: "per intent cluster" },
    { label: "Drift  Δ",                sub: "vs 30-day baseline" },
    { label: "Alert?",                  sub: "if Δ > threshold" },
  ];
  const nodes: React.ReactNode[] = [];
  steps.forEach((s, i) => {
    nodes.push(
      <div key={s.label} style={{ backgroundColor: "#131c30", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "11px 14px" }}>
        <div style={{ fontFamily: t.typography.fontBody, fontSize: 11, fontWeight: 500, color: "#fff", whiteSpace: "nowrap" }}>{s.label}</div>
        <div style={{ fontFamily: t.typography.fontBody, fontSize: 9, color: "rgba(255,255,255,0.38)", marginTop: 4, whiteSpace: "nowrap" }}>{s.sub}</div>
      </div>
    );
    if (i < steps.length - 1) {
      nodes.push(<div key={`a${i}`} style={{ color: "rgba(255,255,255,0.22)", fontSize: 16, padding: "0 4px", flexShrink: 0 }}>→</div>);
    }
  });
  return <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", rowGap: 12 }}>{nodes}</div>;
}

// ── Shared helpers ────────────────────────────────────────────────────────────

function Section({ eyebrow, title, description, children }: {
  eyebrow: string; title: React.ReactNode; description?: string; children?: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 72 }}>
      <Eyebrow light>{eyebrow}</Eyebrow>
      <h2 style={{ fontFamily: t.typography.fontDisplay, fontSize: 32, fontWeight: 300, color: "#fff", margin: "10px 0 16px", lineHeight: 1.2 }}>{title}</h2>
      {description && <p style={{ fontFamily: t.typography.fontBody, fontSize: 14, color: "rgba(255,255,255,0.5)", lineHeight: 1.8, maxWidth: 700, marginBottom: 32 }}>{description}</p>}
      {children}
    </div>
  );
}

function CapCard({ num, accent, title, body: bodyText }: { num: string; accent: string; title: string; body: string }) {
  return (
    <div style={{ backgroundColor: "#0d1424", borderRadius: 12, padding: "24px 22px", border: `1px solid ${accent}25` }}>
      <div style={{ fontFamily: t.typography.fontDisplay, fontSize: 36, fontWeight: 300, color: `${accent}40`, marginBottom: 14, lineHeight: 1 }}>{num}</div>
      <div style={{ fontFamily: t.typography.fontBody, fontSize: 13, fontWeight: 600, color: accent, marginBottom: 12 }}>{title}</div>
      <p style={{ fontFamily: t.typography.fontBody, fontSize: 13, color: "rgba(255,255,255,0.5)", lineHeight: 1.75, margin: 0 }}>{bodyText}</p>
    </div>
  );
}

function AudienceCard({ role, description }: { role: string; description: string }) {
  return (
    <div style={{ backgroundColor: "#0d1424", borderRadius: 10, padding: "22px", border: "1px solid rgba(255,255,255,0.06)" }}>
      <div style={{ fontFamily: t.typography.fontBody, fontSize: 12, fontWeight: 600, color: "#fff", marginBottom: 10 }}>{role}</div>
      <p style={{ fontFamily: t.typography.fontBody, fontSize: 13, color: "rgba(255,255,255,0.45)", lineHeight: 1.75, margin: 0 }}>{description}</p>
    </div>
  );
}

const body: React.CSSProperties = {
  fontFamily: t.typography.fontBody, fontSize: 14, color: "rgba(255,255,255,0.5)", lineHeight: 1.8, margin: 0,
};

const inlineCode: React.CSSProperties = {
  fontFamily: t.typography.fontMono, fontSize: 12, color: t.colors.goldLight,
  backgroundColor: "rgba(200,152,42,0.12)", padding: "2px 6px", borderRadius: 4,
};
