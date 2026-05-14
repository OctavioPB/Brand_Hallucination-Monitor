"""Graph API router — 4 typed endpoints over the Neo4j knowledge graph."""
import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.graph.client import Neo4jClient, get_neo4j_client
from apps.api.graph.queries import (
    ClusterRanking,
    CompetitorProximity,
    ConceptAssociation,
    HallucinationRecord,
    get_brand_concept_associations,
    get_competitor_proximity_map,
    get_hallucination_history,
    get_intent_cluster_ranking,
)

router = APIRouter(prefix="/api/v1/brands", tags=["graph"])

logger = structlog.get_logger(__name__)

Neo4jDep = Annotated[Neo4jClient, Depends(get_neo4j_client)]


def _raise_if_unreachable(client: Neo4jClient) -> None:
    if not client.verify_connectivity():
        raise HTTPException(status_code=503, detail="Knowledge graph unavailable")


@router.get(
    "/{brand_id}/concept-associations",
    response_model=list[ConceptAssociation],
    summary="Top concept associations for a brand",
)
async def concept_associations(
    brand_id: str,
    client: Neo4jDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ConceptAssociation]:
    """Return the top-N semantic concepts associated with this brand in the knowledge graph.

    Ordered by association score descending. Score is cosine similarity [0, 1]
    between the brand's embedding and the concept centroid.
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None,
            lambda: get_brand_concept_associations(client, brand_id, limit),
        )
    except Exception as exc:
        logger.exception("concept_associations failed", brand_id=brand_id)
        raise HTTPException(status_code=503, detail="Graph query failed") from exc


@router.get(
    "/{brand_id}/competitor-proximity",
    response_model=list[CompetitorProximity],
    summary="Competitor concept association map",
)
async def competitor_proximity(
    brand_id: str,
    client: Neo4jDep,
) -> list[CompetitorProximity]:
    """Return all known competitors and their concept association scores.

    Useful for competitive gap analysis: which concepts is the competitor
    associated with that you are not?
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None,
            lambda: get_competitor_proximity_map(client, brand_id),
        )
    except Exception as exc:
        logger.exception("competitor_proximity failed", brand_id=brand_id)
        raise HTTPException(status_code=503, detail="Graph query failed") from exc


@router.get(
    "/{brand_id}/hallucination-history",
    response_model=list[HallucinationRecord],
    summary="Detected LLM hallucinations for a brand",
)
async def hallucination_history(
    brand_id: str,
    client: Neo4jDep,
    model_name: str = Query(default="", description="Filter by LLM model name"),
) -> list[HallucinationRecord]:
    """Return the history of detected hallucinations for this brand.

    A hallucination is a factual attribute that an LLM incorrectly associated
    with the brand. Optionally filter by model (e.g. 'gpt-4o', 'gemini-1.5-pro').
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None,
            lambda: get_hallucination_history(client, brand_id, model_name),
        )
    except Exception as exc:
        logger.exception("hallucination_history failed", brand_id=brand_id)
        raise HTTPException(status_code=503, detail="Graph query failed") from exc


@router.get(
    "/{brand_id}/cluster-ranking",
    response_model=list[ClusterRanking],
    summary="Intent cluster ranking by average SPS score",
)
async def cluster_ranking(
    brand_id: str,
    client: Neo4jDep,
) -> list[ClusterRanking]:
    """Return intent clusters ranked by average Semantic Proximity Score.

    Higher rank = the brand is more strongly associated with that intent cluster
    in the AI model's latent space. First cluster is the brand's strongest
    perceived attribute category.
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None,
            lambda: get_intent_cluster_ranking(client, brand_id),
        )
    except Exception as exc:
        logger.exception("cluster_ranking failed", brand_id=brand_id)
        raise HTTPException(status_code=503, detail="Graph query failed") from exc
