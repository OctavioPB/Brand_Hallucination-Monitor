"""Neo4jClient — driver lifecycle management and parameterized query execution.

Design:
- Sync driver (neo4j.GraphDatabase) because Airflow tasks are sync.
- FastAPI routes call graph functions via run_in_executor.
- Never use string interpolation in Cypher — always $param syntax.
- get_neo4j_client() FastAPI dependency returns a singleton per process.
"""
import logging
from functools import lru_cache
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class Neo4jClient:
    """Thin wrapper around the neo4j sync driver."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        try:
            from neo4j import GraphDatabase  # lazy — not required for tests without Neo4j
        except ImportError as exc:
            raise RuntimeError(
                "neo4j package not installed. Add 'neo4j>=5.0.0' to dependencies."
            ) from exc

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Neo4j driver initialized", uri=uri, user=user)

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def run(self, query: str, **params: Any) -> list[dict[str, Any]]:
        """Execute a read query and return all records as dicts.

        Args:
            query: Cypher query string with $param placeholders.
            **params: Keyword arguments bound to $param placeholders.

        Returns:
            List of record dicts. Empty list if no results.
        """
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [dict(record) for record in result]

    def run_write(self, query: str, **params: Any) -> list[dict[str, Any]]:
        """Execute a write query inside a write transaction.

        Retries on transient failures per neo4j driver defaults.
        """
        def _tx(tx: Any) -> list[dict[str, Any]]:
            result = tx.run(query, **params)
            return [dict(record) for record in result]

        with self._driver.session() as session:
            return session.execute_write(_tx)

    def run_write_batch(self, query: str, rows: list[dict[str, Any]]) -> int:
        """Execute a write query with an UNWIND $rows pattern for batch operations.

        Args:
            query: Cypher query that uses UNWIND $rows AS row.
            rows: List of dicts bound to $rows.

        Returns:
            Number of rows passed (not guaranteed to equal nodes created due to MERGE).
        """
        def _tx(tx: Any) -> None:
            tx.run(query, rows=rows)

        with self._driver.session() as session:
            session.execute_write(_tx)
        return len(rows)

    def apply_cypher_file(self, path: str) -> int:
        """Apply a .cypher file (semicolon-separated statements). Returns statement count."""
        import re

        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Strip single-line comments before splitting
        content = re.sub(r"//[^\n]*", "", content)
        statements = [s.strip() for s in content.split(";") if s.strip()]

        with self._driver.session() as session:
            for stmt in statements:
                session.run(stmt)

        logger.info("Applied Cypher file", path=path, statements=len(statements))
        return len(statements)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def verify_connectivity(self) -> bool:
        """Ping Neo4j. Returns True if reachable."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_client(uri: str, user: str, password: str) -> Neo4jClient:
    return Neo4jClient(uri=uri, user=user, password=password)


def get_neo4j_client() -> Neo4jClient:
    """FastAPI dependency — returns the process-level Neo4j client singleton."""
    import os

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "hallucin8pass")
    return _build_client(uri=uri, user=user, password=password)
