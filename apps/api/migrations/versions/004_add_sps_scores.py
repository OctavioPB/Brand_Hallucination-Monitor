"""Sprint 3: sps_scores time-series table

Revision ID: 004
Revises: 003
Create Date: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sps_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intent_cluster_slug", sa.String(64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "model_version",
            sa.String(64),
            nullable=False,
            server_default="text-embedding-3-small",
        ),
        sa.Column("dag_run_id", sa.String(256), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sps_scores_brand_id", "sps_scores", ["brand_id"])
    op.create_index("ix_sps_scores_cluster_slug", "sps_scores", ["intent_cluster_slug"])
    op.create_index("ix_sps_scores_calculated_at", "sps_scores", ["calculated_at"])
    # Composite index for the most common query: latest SPS for brand × cluster
    op.create_index(
        "ix_sps_scores_brand_cluster_time",
        "sps_scores",
        ["brand_id", "intent_cluster_slug", "calculated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sps_scores_brand_cluster_time", table_name="sps_scores")
    op.drop_index("ix_sps_scores_calculated_at", table_name="sps_scores")
    op.drop_index("ix_sps_scores_cluster_slug", table_name="sps_scores")
    op.drop_index("ix_sps_scores_brand_id", table_name="sps_scores")
    op.drop_table("sps_scores")
