// hallucin8 — Neo4j Schema
// Apply once on fresh instance; all statements are idempotent.
// Run via: scripts/seed_neo4j.py --schema-only
//
// Node labels:
//   Brand         — monitored brand entity
//   Concept       — semantic concept extracted from mentions ("market_leader", "gdpr_compliant")
//   IntentCluster — canonical purchase-intent bucket ("reliability", "innovation", ...)
//   Attribute     — factual claim about a brand (may be true, false, or unverified)
//   Competitor    — a competing brand in the same market segment
//   Source        — origin of a data point (URL + source_type)

// ------------------------------------------------------------------
// Uniqueness constraints
// ------------------------------------------------------------------
CREATE CONSTRAINT brand_id_unique IF NOT EXISTS
  FOR (b:Brand) REQUIRE b.brand_id IS UNIQUE;

CREATE CONSTRAINT concept_slug_unique IF NOT EXISTS
  FOR (c:Concept) REQUIRE c.slug IS UNIQUE;

CREATE CONSTRAINT attribute_slug_unique IF NOT EXISTS
  FOR (a:Attribute) REQUIRE a.slug IS UNIQUE;

CREATE CONSTRAINT intent_cluster_slug_unique IF NOT EXISTS
  FOR (ic:IntentCluster) REQUIRE ic.slug IS UNIQUE;

CREATE CONSTRAINT competitor_id_unique IF NOT EXISTS
  FOR (comp:Competitor) REQUIRE comp.competitor_id IS UNIQUE;

CREATE CONSTRAINT source_url_unique IF NOT EXISTS
  FOR (s:Source) REQUIRE s.url IS UNIQUE;

// ------------------------------------------------------------------
// Performance indexes
// ------------------------------------------------------------------
CREATE INDEX brand_name_index IF NOT EXISTS
  FOR (b:Brand) ON (b.name);

CREATE INDEX brand_slug_index IF NOT EXISTS
  FOR (b:Brand) ON (b.slug);

CREATE INDEX concept_display_name_index IF NOT EXISTS
  FOR (c:Concept) ON (c.display_name);

CREATE INDEX attribute_polarity_index IF NOT EXISTS
  FOR (a:Attribute) ON (a.polarity);

CREATE INDEX competitor_name_index IF NOT EXISTS
  FOR (comp:Competitor) ON (comp.name);
