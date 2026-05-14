// hallucin8 — Seed Data
// Seeds intent clusters, canonical concepts, 3 test brands, and sample relationships.
// Run via: scripts/seed_neo4j.py
// All MERGE statements are idempotent — safe to re-run.

// ------------------------------------------------------------------
// Intent Clusters (6 canonical purchase-intent buckets)
// ------------------------------------------------------------------
MERGE (ic1:IntentCluster {slug: 'reliability'})
  SET ic1.display_name = 'Reliability & Trust';

MERGE (ic2:IntentCluster {slug: 'innovation'})
  SET ic2.display_name = 'Innovation & Technology';

MERGE (ic3:IntentCluster {slug: 'pricing_value'})
  SET ic3.display_name = 'Pricing & Value';

MERGE (ic4:IntentCluster {slug: 'market_leadership'})
  SET ic4.display_name = 'Market Leadership';

MERGE (ic5:IntentCluster {slug: 'compliance'})
  SET ic5.display_name = 'Compliance & Security';

MERGE (ic6:IntentCluster {slug: 'support_quality'})
  SET ic6.display_name = 'Support & Customer Experience';

// ------------------------------------------------------------------
// Concept nodes — 24 semantic concepts across 6 clusters
// ------------------------------------------------------------------

// Reliability (4)
MERGE (c01:Concept {slug: 'uptime_guarantee'})    SET c01.display_name = 'Uptime Guarantee';
MERGE (c02:Concept {slug: 'zero_downtime'})       SET c02.display_name = 'Zero Downtime';
MERGE (c03:Concept {slug: 'sla_compliance'})      SET c03.display_name = 'SLA Compliance';
MERGE (c04:Concept {slug: 'fault_tolerant'})      SET c04.display_name = 'Fault Tolerant';

// Innovation (4)
MERGE (c05:Concept {slug: 'ai_powered'})          SET c05.display_name = 'AI-Powered';
MERGE (c06:Concept {slug: 'api_first'})           SET c06.display_name = 'API-First';
MERGE (c07:Concept {slug: 'real_time_processing'}) SET c07.display_name = 'Real-Time Processing';
MERGE (c08:Concept {slug: 'cloud_native'})        SET c08.display_name = 'Cloud Native';

// Pricing & Value (4)
MERGE (c09:Concept {slug: 'competitive_pricing'}) SET c09.display_name = 'Competitive Pricing';
MERGE (c10:Concept {slug: 'free_tier'})           SET c10.display_name = 'Free Tier Available';
MERGE (c11:Concept {slug: 'roi_positive'})        SET c11.display_name = 'Positive ROI';
MERGE (c12:Concept {slug: 'cost_effective'})      SET c12.display_name = 'Cost Effective';

// Market Leadership (4)
MERGE (c13:Concept {slug: 'market_leader'})       SET c13.display_name = 'Market Leader';
MERGE (c14:Concept {slug: 'industry_standard'})   SET c14.display_name = 'Industry Standard';
MERGE (c15:Concept {slug: 'trusted_by_enterprises'}) SET c15.display_name = 'Trusted by Enterprises';
MERGE (c16:Concept {slug: 'award_winning'})       SET c16.display_name = 'Award Winning';

// Compliance (4)
MERGE (c17:Concept {slug: 'gdpr_compliant'})      SET c17.display_name = 'GDPR Compliant';
MERGE (c18:Concept {slug: 'soc2_certified'})      SET c18.display_name = 'SOC 2 Certified';
MERGE (c19:Concept {slug: 'hipaa_ready'})         SET c19.display_name = 'HIPAA Ready';
MERGE (c20:Concept {slug: 'iso_27001'})           SET c20.display_name = 'ISO 27001 Certified';

// Support Quality (4)
MERGE (c21:Concept {slug: '24_7_support'})        SET c21.display_name = '24/7 Support';
MERGE (c22:Concept {slug: 'dedicated_csm'})       SET c22.display_name = 'Dedicated CSM';
MERGE (c23:Concept {slug: 'fast_response_times'}) SET c23.display_name = 'Fast Response Times';
MERGE (c24:Concept {slug: 'onboarding_support'})  SET c24.display_name = 'Onboarding Support';

// ------------------------------------------------------------------
// BELONGS_TO_CLUSTER relationships
// ------------------------------------------------------------------
MATCH (c:Concept {slug: 'uptime_guarantee'}),     (ic:IntentCluster {slug: 'reliability'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'zero_downtime'}),        (ic:IntentCluster {slug: 'reliability'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'sla_compliance'}),       (ic:IntentCluster {slug: 'reliability'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'fault_tolerant'}),       (ic:IntentCluster {slug: 'reliability'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);

MATCH (c:Concept {slug: 'ai_powered'}),           (ic:IntentCluster {slug: 'innovation'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'api_first'}),            (ic:IntentCluster {slug: 'innovation'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'real_time_processing'}), (ic:IntentCluster {slug: 'innovation'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'cloud_native'}),         (ic:IntentCluster {slug: 'innovation'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);

MATCH (c:Concept {slug: 'competitive_pricing'}),  (ic:IntentCluster {slug: 'pricing_value'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'free_tier'}),            (ic:IntentCluster {slug: 'pricing_value'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'roi_positive'}),         (ic:IntentCluster {slug: 'pricing_value'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'cost_effective'}),       (ic:IntentCluster {slug: 'pricing_value'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);

MATCH (c:Concept {slug: 'market_leader'}),        (ic:IntentCluster {slug: 'market_leadership'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'industry_standard'}),    (ic:IntentCluster {slug: 'market_leadership'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'trusted_by_enterprises'}),(ic:IntentCluster {slug: 'market_leadership'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'award_winning'}),        (ic:IntentCluster {slug: 'market_leadership'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);

MATCH (c:Concept {slug: 'gdpr_compliant'}),       (ic:IntentCluster {slug: 'compliance'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'soc2_certified'}),       (ic:IntentCluster {slug: 'compliance'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'hipaa_ready'}),          (ic:IntentCluster {slug: 'compliance'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'iso_27001'}),            (ic:IntentCluster {slug: 'compliance'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);

MATCH (c:Concept {slug: '24_7_support'}),         (ic:IntentCluster {slug: 'support_quality'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'dedicated_csm'}),        (ic:IntentCluster {slug: 'support_quality'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'fast_response_times'}),  (ic:IntentCluster {slug: 'support_quality'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);
MATCH (c:Concept {slug: 'onboarding_support'}),   (ic:IntentCluster {slug: 'support_quality'})
MERGE (c)-[:BELONGS_TO_CLUSTER]->(ic);

// ------------------------------------------------------------------
// Known Attributes (factual claims that can be hallucinated)
// ------------------------------------------------------------------
MERGE (a1:Attribute {slug: 'has_open_source_edition'})
  SET a1.text = 'Has an open-source community edition', a1.polarity = 'positive';

MERGE (a2:Attribute {slug: 'no_free_tier'})
  SET a2.text = 'Does not offer a free tier', a2.polarity = 'negative';

MERGE (a3:Attribute {slug: 'requires_annual_contract'})
  SET a3.text = 'Requires annual contract commitment', a3.polarity = 'negative';

MERGE (a4:Attribute {slug: 'founded_pre_2010'})
  SET a4.text = 'Founded before 2010', a4.polarity = 'neutral';

MERGE (a5:Attribute {slug: 'publicly_traded'})
  SET a5.text = 'Is a publicly traded company', a5.polarity = 'neutral';

MERGE (a6:Attribute {slug: 'acquired_competitor'})
  SET a6.text = 'Has acquired a major competitor', a6.polarity = 'neutral';

// CONTRADICTS relationships (mutually exclusive attributes)
MATCH (a:Attribute {slug: 'has_open_source_edition'}), (b:Attribute {slug: 'no_free_tier'})
MERGE (a)-[:CONTRADICTS]->(b);
MERGE (b)-[:CONTRADICTS]->(a);

// ------------------------------------------------------------------
// Test Brands (3 brands as required by DoD)
// ------------------------------------------------------------------
MERGE (b1:Brand {brand_id: 'seed-brand-001'})
  SET b1.name = 'AcmeCorp', b1.slug = 'acmecorp', b1.organization_id = 'seed-org-001';

MERGE (b2:Brand {brand_id: 'seed-brand-002'})
  SET b2.name = 'BetaTech', b2.slug = 'betatech', b2.organization_id = 'seed-org-001';

MERGE (b3:Brand {brand_id: 'seed-brand-003'})
  SET b3.name = 'GammaSoft', b3.slug = 'gammasoft', b3.organization_id = 'seed-org-002';

// Competitor relationships
MATCH (b1:Brand {brand_id: 'seed-brand-001'}), (b2:Brand {brand_id: 'seed-brand-002'})
MERGE (b1)-[:COMPETES_WITH {market_segment: 'enterprise_saas'}]->(b2);
MERGE (b2)-[:COMPETES_WITH {market_segment: 'enterprise_saas'}]->(b1);

MATCH (b1:Brand {brand_id: 'seed-brand-001'}), (b3:Brand {brand_id: 'seed-brand-003'})
MERGE (b1)-[:COMPETES_WITH {market_segment: 'data_infrastructure'}]->(b3);

// Sample ASSOCIATED_WITH relationships for AcmeCorp
MATCH (b:Brand {brand_id: 'seed-brand-001'}), (c:Concept {slug: 'uptime_guarantee'})
MERGE (b)-[r:ASSOCIATED_WITH {source: 'seed'}]->(c)
  SET r.score = 0.87, r.timestamp = datetime();

MATCH (b:Brand {brand_id: 'seed-brand-001'}), (c:Concept {slug: 'soc2_certified'})
MERGE (b)-[r:ASSOCIATED_WITH {source: 'seed'}]->(c)
  SET r.score = 0.92, r.timestamp = datetime();

MATCH (b:Brand {brand_id: 'seed-brand-001'}), (c:Concept {slug: 'market_leader'})
MERGE (b)-[r:ASSOCIATED_WITH {source: 'seed'}]->(c)
  SET r.score = 0.74, r.timestamp = datetime();

MATCH (b:Brand {brand_id: 'seed-brand-001'}), (c:Concept {slug: 'ai_powered'})
MERGE (b)-[r:ASSOCIATED_WITH {source: 'seed'}]->(c)
  SET r.score = 0.68, r.timestamp = datetime();

// Sample ASSOCIATED_WITH for BetaTech
MATCH (b:Brand {brand_id: 'seed-brand-002'}), (c:Concept {slug: 'competitive_pricing'})
MERGE (b)-[r:ASSOCIATED_WITH {source: 'seed'}]->(c)
  SET r.score = 0.81, r.timestamp = datetime();

MATCH (b:Brand {brand_id: 'seed-brand-002'}), (c:Concept {slug: 'api_first'})
MERGE (b)-[r:ASSOCIATED_WITH {source: 'seed'}]->(c)
  SET r.score = 0.77, r.timestamp = datetime();

// Sample HALLUCINATED_AS (false positive by GPT-4o for AcmeCorp)
MATCH (b:Brand {brand_id: 'seed-brand-001'}), (a:Attribute {slug: 'founded_pre_2010'})
MERGE (b)-[r:HALLUCINATED_AS {model: 'gpt-4o', source: 'seed'}]->(a)
  SET r.confidence = 0.76, r.detected_at = datetime();

MATCH (b:Brand {brand_id: 'seed-brand-001'}), (a:Attribute {slug: 'has_open_source_edition'})
MERGE (b)-[r:HALLUCINATED_AS {model: 'gemini-1.5-pro', source: 'seed'}]->(a)
  SET r.confidence = 0.61, r.detected_at = datetime();
