"""One-shot script: apply Neo4j schema constraints + seed data.

Run after 'make up' when Neo4j is healthy:
    python scripts/seed_neo4j.py

Flags:
    --schema-only   Apply constraints/indexes only, skip seed data.
    --seed-only     Apply seed data only (assumes schema already applied).
    --verify        Print node counts and exit; do not apply anything.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Neo4j knowledge graph")
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "hallucin8pass")

    from apps.api.graph.client import Neo4jClient
    from apps.api.graph.seeder import apply_schema, apply_seed, verify_seed

    with Neo4jClient(uri=uri, user=user, password=password) as client:
        if not client.verify_connectivity():
            logger.error("Cannot connect to Neo4j", uri=uri)
            sys.exit(1)

        if args.verify:
            counts = verify_seed(client)
            logger.info("Node counts", **counts)
            return

        if not args.seed_only:
            n = apply_schema(client)
            logger.info("Schema applied", statements=n)

        if not args.schema_only:
            n = apply_seed(client)
            logger.info("Seed data applied", statements=n)

        counts = verify_seed(client)
        logger.info("Verification complete", **counts)


if __name__ == "__main__":
    main()
