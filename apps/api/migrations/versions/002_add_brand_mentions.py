"""Add brand_mentions table for tracking ingested mention events

Revision ID: 002
Revises: 001
Create Date: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.String(128), nullable=False),
        # Source metadata
        sa.Column("source_type", sa.String(32), nullable=False),  # rss|reddit|review|manual
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_id", sa.String(256), nullable=True),    # external ID (e.g. reddit post ID)
        # Content
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),  # SHA-256, used for dedup
        # Enrichment metadata
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Pipeline state
        sa.Column("kafka_offset", sa.BigInteger(), nullable=True),
        sa.Column("kafka_partition", sa.Integer(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("embedding_queued", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brand_mentions_brand_id", "brand_mentions", ["brand_id"])
    op.create_index("ix_brand_mentions_org_id", "brand_mentions", ["organization_id"])
    op.create_index("ix_brand_mentions_content_hash", "brand_mentions", ["content_hash"], unique=True)
    op.create_index("ix_brand_mentions_source_type", "brand_mentions", ["source_type"])
    op.create_index(
        "ix_brand_mentions_unprocessed",
        "brand_mentions",
        ["processed", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("brand_mentions")
