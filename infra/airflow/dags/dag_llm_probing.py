"""DAG: dag_llm_probing — daily LLM brand probing + hallucination detection.

Schedule: 04:00 UTC daily.
Tasks:
  1. fetch_active_brands       — read brands with a manifest from PostgreSQL
  2. probe_brands              — call GPT-4o / Gemini; persist ProbeResultORM rows
  3. classify_responses        — run HallucinationClassifier on each probe result
  4. write_hallucinations_to_graph — HALLUCINATED_AS edges in Neo4j
  5. publish_critical_alerts   — CRITICAL results → hallucination.alerts Kafka topic

Cost safety:
  - BrandProber checks daily spend before each model call.
  - MAX_DAILY_PROBE_COST_USD env var (default $2.00/day total).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import psycopg2
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get("DATABASE_URL", "")
_NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
_NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "hallucin8")
_KAFKA_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
_ALERTS_TOPIC = "hallucination.alerts"


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

@dag(
    dag_id="dag_llm_probing",
    schedule_interval="0 4 * * *",  # 04:00 UTC daily
    start_date=days_ago(1),
    catchup=False,
    tags=["hallucination", "probing", "sprint5"],
    doc_md=__doc__,
)
def dag_llm_probing() -> None:

    # ------------------------------------------------------------------
    # Task 1: fetch_active_brands
    # ------------------------------------------------------------------

    @task()
    def fetch_active_brands() -> list[dict[str, Any]]:
        """Return brands that have a non-null manifest from PostgreSQL."""
        conn = psycopg2.connect(_DB_URL)
        brands: list[dict[str, Any]] = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, slug, organization_id, manifest
                    FROM brands
                    WHERE manifest IS NOT NULL
                    ORDER BY name
                    """
                )
                for row in cur.fetchall():
                    brands.append(
                        {
                            "id": str(row[0]),
                            "name": row[1],
                            "slug": row[2],
                            "organization_id": row[3],
                            "manifest": row[4],  # already a dict via psycopg2 JSONB
                        }
                    )
        finally:
            conn.close()

        logger.info("Fetched %d active brands for probing", len(brands))
        return brands

    # ------------------------------------------------------------------
    # Task 2: probe_brands
    # ------------------------------------------------------------------

    @task()
    def probe_brands(brands: list[dict[str, Any]]) -> list[str]:
        """Probe each brand with all configured LLMs; persist ProbeResultORM rows.

        Returns list of probe_result IDs (UUID strings) for downstream tasks.
        """
        from ml.hallucination.prober import BrandProber

        prober = BrandProber(db_url=_DB_URL)
        probe_ids: list[str] = []

        conn = psycopg2.connect(_DB_URL)
        try:
            for brand in brands:
                manifest = brand["manifest"] or {}
                competitor_list: list[str] = manifest.get("competitor_list", [])
                competitor_name = competitor_list[0] if competitor_list else ""

                results = prober.probe_brand(
                    brand_name=brand["name"],
                    competitor_name=competitor_name,
                    dag_run_id=f"dag_llm_probing_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}",
                )

                for r in results:
                    probe_id = str(uuid.uuid4())
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO probe_results
                                  (id, brand_id, organization_id, model_name,
                                   probe_prompt, llm_response,
                                   tokens_input, tokens_output,
                                   cost_usd, latency_ms,
                                   hallucinations_detected, dag_run_id)
                                VALUES
                                  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
                                """,
                                (
                                    probe_id,
                                    brand["id"],
                                    brand["organization_id"],
                                    r.model_name,
                                    r.prompt,
                                    r.response,
                                    r.tokens_input,
                                    r.tokens_output,
                                    str(r.cost_usd),
                                    r.latency_ms,
                                    f"dag_llm_probing_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}",
                                ),
                            )
                    probe_ids.append(probe_id)

        finally:
            conn.close()

        logger.info("Persisted %d probe results", len(probe_ids))
        return probe_ids

    # ------------------------------------------------------------------
    # Task 3: classify_responses
    # ------------------------------------------------------------------

    @task()
    def classify_responses(
        probe_ids: list[str],
        brands: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run HallucinationClassifier on each probe result.

        Returns list of serialized HallucinationResult dicts (only positives).
        Also updates hallucinations_detected count on each probe row.
        """
        from apps.api.models.brand import BrandManifest
        from ml.hallucination.classifier import HallucinationClassifier

        if not probe_ids:
            return []

        classifier = HallucinationClassifier()

        # Build brand lookup keyed by brand_id
        brand_by_id: dict[str, dict[str, Any]] = {b["id"]: b for b in brands}

        conn = psycopg2.connect(_DB_URL)
        all_hallucinations: list[dict[str, Any]] = []

        try:
            with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(probe_ids))
                cur.execute(
                    f"SELECT id, brand_id, model_name, llm_response FROM probe_results "
                    f"WHERE id IN ({placeholders})",
                    probe_ids,
                )
                rows = cur.fetchall()

            for probe_id, brand_id_str, model_name, llm_response in rows:
                brand = brand_by_id.get(str(brand_id_str))
                if brand is None:
                    continue

                manifest_data = brand.get("manifest") or {}
                manifest = BrandManifest(**manifest_data)

                results = classifier.classify(
                    response_text=llm_response,
                    manifest=manifest,
                    brand_name=brand["name"],
                    model_name=model_name,
                    embedding_fn=None,  # false_attribute detection skipped (no embedding in DAG)
                )

                n_detected = len(results)
                if n_detected > 0:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE probe_results SET hallucinations_detected = %s WHERE id = %s",
                                (n_detected, str(probe_id)),
                            )

                for r in results:
                    all_hallucinations.append(
                        {
                            "probe_id": str(probe_id),
                            "brand_id": str(brand_id_str),
                            "brand_name": brand["name"],
                            **r.model_dump(),
                        }
                    )

        finally:
            conn.close()

        logger.info(
            "Classification complete: %d hallucinations across %d probes",
            len(all_hallucinations),
            len(probe_ids),
        )
        return all_hallucinations

    # ------------------------------------------------------------------
    # Task 4: write_hallucinations_to_graph
    # ------------------------------------------------------------------

    @task()
    def write_hallucinations_to_graph(hallucinations: list[dict[str, Any]]) -> int:
        """Write HALLUCINATED_AS edges to Neo4j. Fail-open — graph is non-critical."""
        if not hallucinations:
            return 0

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                _NEO4J_URI,
                auth=(_NEO4J_USER, _NEO4J_PASSWORD),
            )

            _CYPHER = """
            MATCH (b:Brand {brand_id: $brand_id})
            MERGE (a:Attribute {slug: $attribute_slug})
              ON CREATE SET a.text = $attribute_text, a.polarity = 'negative'
            MERGE (b)-[r:HALLUCINATED_AS {model: $model_name, source: 'llm_probe'}]->(a)
            SET r.confidence = $confidence, r.detected_at = datetime($detected_at)
            """

            count = 0
            with driver.session() as session:
                for h in hallucinations:
                    session.run(
                        _CYPHER,
                        brand_id=h["brand_id"],
                        attribute_slug=h["attribute_slug"],
                        attribute_text=h["attribute_text"],
                        model_name=h["model_name"],
                        confidence=float(h["confidence"]),
                        detected_at=datetime.now(tz=timezone.utc).isoformat(),
                    )
                    count += 1

            driver.close()
            logger.info("Wrote %d hallucination edges to Neo4j", count)
            return count

        except Exception:
            logger.exception("Neo4j write failed — skipping graph update")
            return 0

    # ------------------------------------------------------------------
    # Task 5: publish_critical_alerts
    # ------------------------------------------------------------------

    @task()
    def publish_critical_alerts(hallucinations: list[dict[str, Any]]) -> int:
        """Publish CRITICAL hallucinations to hallucination.alerts Kafka topic."""
        critical = [h for h in hallucinations if h.get("severity") == "CRITICAL"]
        if not critical:
            return 0

        published = 0
        try:
            from confluent_kafka import Producer

            producer = Producer({"bootstrap.servers": _KAFKA_SERVERS})

            for h in critical:
                payload = json.dumps(
                    {
                        "event_type": "hallucination_alert",
                        "severity": h["severity"],
                        "brand_id": h["brand_id"],
                        "brand_name": h["brand_name"],
                        "hallucination_type": h["hallucination_type"],
                        "attribute_slug": h["attribute_slug"],
                        "attribute_text": h["attribute_text"],
                        "model_name": h["model_name"],
                        "confidence": h["confidence"],
                        "evidence_snippet": h.get("evidence_snippet", "")[:300],
                        "detected_at": datetime.now(tz=timezone.utc).isoformat(),
                    }
                ).encode()

                producer.produce(
                    _ALERTS_TOPIC,
                    key=h["brand_id"].encode(),
                    value=payload,
                )
                published += 1

            producer.flush(timeout=10)
            logger.info("Published %d CRITICAL alerts to Kafka", published)

        except Exception:
            logger.exception("Kafka publish failed — alerts not sent")

        return published

    # ------------------------------------------------------------------
    # DAG wiring
    # ------------------------------------------------------------------
    brands_data = fetch_active_brands()
    probe_ids = probe_brands(brands_data)
    hallucinations = classify_responses(probe_ids, brands_data)
    write_hallucinations_to_graph(hallucinations)
    publish_critical_alerts(hallucinations)


dag_llm_probing()
