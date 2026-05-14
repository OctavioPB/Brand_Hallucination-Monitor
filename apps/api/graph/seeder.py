"""Graph seeder — applies schema constraints and seed data to Neo4j.

Called from scripts/seed_neo4j.py; also usable as a library by tests.
"""
import logging
import os
from pathlib import Path

import structlog

from apps.api.graph.client import Neo4jClient

logger = structlog.get_logger(__name__)

_INFRA_NEO4J = Path(__file__).parents[3] / "infra" / "neo4j"


def apply_schema(client: Neo4jClient) -> int:
    """Apply constraints and indexes from schema.cypher. Returns statement count."""
    schema_path = _INFRA_NEO4J / "schema.cypher"
    count = client.apply_cypher_file(str(schema_path))
    logger.info("Schema applied", statements=count)
    return count


def apply_seed(client: Neo4jClient) -> int:
    """Apply seed data from seed.cypher. Returns statement count."""
    seed_path = _INFRA_NEO4J / "seed.cypher"
    count = client.apply_cypher_file(str(seed_path))
    logger.info("Seed data applied", statements=count)
    return count


def verify_seed(client: Neo4jClient) -> dict[str, int]:
    """Return node counts for each label — used to verify seed ran correctly."""
    rows = client.run("""
        MATCH (b:Brand)         WITH count(b) AS brand_count
        MATCH (c:Concept)       WITH brand_count, count(c) AS concept_count
        MATCH (ic:IntentCluster) WITH brand_count, concept_count, count(ic) AS cluster_count
        MATCH (a:Attribute)     WITH brand_count, concept_count, cluster_count, count(a) AS attr_count
        OPTIONAL MATCH (s:Source)
        RETURN brand_count, concept_count, cluster_count, attr_count, count(s) AS source_count
    """)
    if not rows:
        return {"Brand": 0, "Concept": 0, "IntentCluster": 0, "Attribute": 0, "Source": 0}
    r = rows[0]
    return {
        "Brand": int(r.get("brand_count", 0)),
        "Concept": int(r.get("concept_count", 0)),
        "IntentCluster": int(r.get("cluster_count", 0)),
        "Attribute": int(r.get("attr_count", 0)),
        "Source": int(r.get("source_count", 0)),
    }
