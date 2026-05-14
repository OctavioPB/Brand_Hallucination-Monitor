"""Sprint 3: embedding_costs table + embedding_queued index on brand_mentions

Revision ID: 003
Revises: 002
Create Date: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "embedding_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dag_run_id", sa.String(256), nullable=False),
        sa.Column("model", sa.String(64), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_vectors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_cached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_embedding_costs_dag_run_id", "embedding_costs", ["dag_run_id"])
    op.create_index("ix_embedding_costs_created_at", "embedding_costs", ["created_at"])

    # Partial index: find brand_mentions not yet queued for embedding
    op.create_index(
        "ix_brand_mentions_pending_embedding",
        "brand_mentions",
        ["created_at"],
        postgresql_where=sa.text("embedding_queued = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_brand_mentions_pending_embedding", table_name="brand_mentions")
    op.drop_index("ix_embedding_costs_created_at", table_name="embedding_costs")
    op.drop_index("ix_embedding_costs_dag_run_id", table_name="embedding_costs")
    op.drop_table("embedding_costs")
