"""Typed Python wrappers for Neo4j Cypher queries.

All queries use parameterized $param syntax — never string interpolation.
Return types are Pydantic models for API serialization safety.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from apps.api.graph.client import Neo4jClient


# ---------------------------------------------------------------------------
# Return models
# ---------------------------------------------------------------------------

class ConceptAssociation(BaseModel):
    concept_slug: str
    concept_name: str
    score: float = Field(ge=0.0, le=1.0)
    source: str
    timestamp: str | None = None
    cluster_slug: str | None = None


class CompetitorConceptScore(BaseModel):
    concept_slug: str
    score: float


class CompetitorProximity(BaseModel):
    competitor_id: str
    competitor_name: str
    market_segment: str | None = None
    concept_scores: list[CompetitorConceptScore] = Field(default_factory=list)


class HallucinationRecord(BaseModel):
    attribute_slug: str
    attribute_text: str
    polarity: str | None = None
    model: str
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: str | None = None


class ClusterRanking(BaseModel):
    cluster_slug: str
    cluster_name: str
    avg_score: float = Field(ge=0.0, le=1.0)
    concept_count: int


# ---------------------------------------------------------------------------
# Write models
# ---------------------------------------------------------------------------

class AssociationWrite(BaseModel):
    """Payload for writing a brand → concept association edge."""
    brand_id: str
    brand_name: str
    brand_slug: str
    organization_id: str
    concept_slug: str
    concept_display_name: str
    score: float = Field(ge=0.0, le=1.0)
    source: str = "embedding_batch"
    timestamp: str  # ISO-8601


# ---------------------------------------------------------------------------
# Query 1: Brand → Concept associations
# ---------------------------------------------------------------------------

_BRAND_CONCEPT_ASSOCIATIONS = """
MATCH (b:Brand {brand_id: $brand_id})-[r:ASSOCIATED_WITH]->(c:Concept)
OPTIONAL MATCH (c)-[:BELONGS_TO_CLUSTER]->(ic:IntentCluster)
RETURN
    c.slug           AS concept_slug,
    c.display_name   AS concept_name,
    r.score          AS score,
    r.source         AS source,
    toString(r.timestamp) AS timestamp,
    ic.slug          AS cluster_slug
ORDER BY r.score DESC
LIMIT $limit
"""


def get_brand_concept_associations(
    client: Neo4jClient,
    brand_id: str,
    limit: int = 20,
) -> list[ConceptAssociation]:
    """Return top-N concept associations for a brand, sorted by score descending."""
    rows = client.run(_BRAND_CONCEPT_ASSOCIATIONS, brand_id=brand_id, limit=limit)
    return [
        ConceptAssociation(
            concept_slug=r["concept_slug"],
            concept_name=r["concept_name"] or r["concept_slug"],
            score=float(r["score"]),
            source=r["source"] or "unknown",
            timestamp=r.get("timestamp"),
            cluster_slug=r.get("cluster_slug"),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Query 2: Competitor proximity map
# ---------------------------------------------------------------------------

_COMPETITOR_PROXIMITY = """
MATCH (b:Brand {brand_id: $brand_id})-[cr:COMPETES_WITH]->(comp:Brand)
OPTIONAL MATCH (comp)-[r:ASSOCIATED_WITH]->(c:Concept)
WITH comp, cr, collect(
    CASE WHEN c IS NOT NULL
         THEN {concept_slug: c.slug, score: r.score}
         ELSE null END
) AS raw_scores
RETURN
    comp.brand_id       AS competitor_id,
    comp.name           AS competitor_name,
    cr.market_segment   AS market_segment,
    [s IN raw_scores WHERE s IS NOT NULL] AS concept_scores
"""


def get_competitor_proximity_map(
    client: Neo4jClient,
    brand_id: str,
) -> list[CompetitorProximity]:
    """Return all competitors for a brand with their concept association scores."""
    rows = client.run(_COMPETITOR_PROXIMITY, brand_id=brand_id)
    result = []
    for r in rows:
        scores = [
            CompetitorConceptScore(
                concept_slug=s["concept_slug"],
                score=float(s["score"]),
            )
            for s in (r["concept_scores"] or [])
            if s.get("concept_slug") and s.get("score") is not None
        ]
        result.append(
            CompetitorProximity(
                competitor_id=r["competitor_id"],
                competitor_name=r["competitor_name"],
                market_segment=r.get("market_segment"),
                concept_scores=scores,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Query 3: Hallucination history
# ---------------------------------------------------------------------------

_HALLUCINATION_HISTORY = """
MATCH (b:Brand {brand_id: $brand_id})-[r:HALLUCINATED_AS]->(a:Attribute)
WHERE $model_name = '' OR r.model = $model_name
RETURN
    a.slug                AS attribute_slug,
    a.text                AS attribute_text,
    a.polarity            AS polarity,
    r.model               AS model,
    r.confidence          AS confidence,
    toString(r.detected_at) AS detected_at
ORDER BY r.detected_at DESC
LIMIT 100
"""


def get_hallucination_history(
    client: Neo4jClient,
    brand_id: str,
    model_name: str = "",
) -> list[HallucinationRecord]:
    """Return hallucination history for a brand, optionally filtered by LLM model."""
    rows = client.run(_HALLUCINATION_HISTORY, brand_id=brand_id, model_name=model_name)
    return [
        HallucinationRecord(
            attribute_slug=r["attribute_slug"],
            attribute_text=r["attribute_text"] or "",
            polarity=r.get("polarity"),
            model=r["model"],
            confidence=float(r["confidence"]),
            detected_at=r.get("detected_at"),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Query 4: Intent cluster ranking
# ---------------------------------------------------------------------------

_INTENT_CLUSTER_RANKING = """
MATCH (b:Brand {brand_id: $brand_id})-[r:ASSOCIATED_WITH]->(c:Concept)
MATCH (c)-[:BELONGS_TO_CLUSTER]->(ic:IntentCluster)
WITH ic, avg(r.score) AS avg_score, count(c) AS concept_count
RETURN
    ic.slug          AS cluster_slug,
    ic.display_name  AS cluster_name,
    avg_score,
    concept_count
ORDER BY avg_score DESC
"""


def get_intent_cluster_ranking(
    client: Neo4jClient,
    brand_id: str,
) -> list[ClusterRanking]:
    """Return intent clusters ranked by average SPS score for a brand."""
    rows = client.run(_INTENT_CLUSTER_RANKING, brand_id=brand_id)
    return [
        ClusterRanking(
            cluster_slug=r["cluster_slug"],
            cluster_name=r["cluster_name"] or r["cluster_slug"],
            avg_score=float(r["avg_score"]),
            concept_count=int(r["concept_count"]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Write: Batch upsert brand → concept associations
# ---------------------------------------------------------------------------

_WRITE_ASSOCIATIONS_BATCH = """
UNWIND $rows AS row
MERGE (b:Brand {brand_id: row.brand_id})
  ON CREATE SET
    b.name            = row.brand_name,
    b.slug            = row.brand_slug,
    b.organization_id = row.organization_id
MERGE (c:Concept {slug: row.concept_slug})
  ON CREATE SET c.display_name = row.concept_display_name
MERGE (b)-[r:ASSOCIATED_WITH {source: row.source}]->(c)
SET
  r.score     = row.score,
  r.timestamp = datetime(row.timestamp)
"""


def write_associations_batch(
    client: Neo4jClient,
    associations: list[AssociationWrite],
) -> int:
    """Batch upsert Brand → Concept ASSOCIATED_WITH edges.

    Uses MERGE so repeated writes with the same brand_id+concept_slug+source
    update the score rather than creating duplicate edges.
    """
    if not associations:
        return 0

    rows = [a.model_dump() for a in associations]
    return client.run_write_batch(_WRITE_ASSOCIATIONS_BATCH, rows=rows)


# ---------------------------------------------------------------------------
# Write: Hallucination detection result → HALLUCINATED_AS relationship
# ---------------------------------------------------------------------------

_WRITE_HALLUCINATION = """
MATCH (b:Brand {brand_id: $brand_id})
MERGE (a:Attribute {slug: $attribute_slug})
  ON CREATE SET a.text = $attribute_text, a.polarity = $polarity
MERGE (b)-[r:HALLUCINATED_AS {model: $model_name, source: $source}]->(a)
SET r.confidence = $confidence, r.detected_at = datetime($detected_at)
"""


def write_hallucination_to_graph(
    client: Neo4jClient,
    brand_id: str,
    attribute_slug: str,
    attribute_text: str,
    model_name: str,
    confidence: float,
    polarity: str = "negative",
    source: str = "llm_probe",
    detected_at: str | None = None,
) -> None:
    """Upsert a Brand → Attribute HALLUCINATED_AS edge in the graph.

    Uses MERGE on (brand_id, model, source) so re-running for the same
    probe session updates confidence rather than creating duplicate edges.
    """
    if detected_at is None:
        detected_at = datetime.utcnow().isoformat() + "Z"

    client.run_write(
        _WRITE_HALLUCINATION,
        brand_id=brand_id,
        attribute_slug=attribute_slug,
        attribute_text=attribute_text,
        polarity=polarity,
        model_name=model_name,
        confidence=confidence,
        source=source,
        detected_at=detected_at,
    )
