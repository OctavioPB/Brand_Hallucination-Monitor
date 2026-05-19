"""Add infra_costs table and org_id column to embedding_costs.

Sprint 9 additions:
- infra_costs: DAG-level cost aggregation (Airflow task cost tagging)
- embedding_costs.org_id: enables per-org budget enforcement via CostGuard

Revision ID: 008
Revises: 007
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add org_id + logged_at to embedding_costs for budget tracking
    op.add_column(
        "embedding_costs",
        sa.Column("org_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "embedding_costs",
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_embedding_costs_org_date",
        "embedding_costs",
        ["org_id", "logged_at"],
    )

    # 2. infra_costs: per-DAG-run aggregated cost record (all task types)
    op.create_table(
        "infra_costs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.String(255), nullable=False),
        sa.Column("dag_run_id", sa.String(255), nullable=False),
        sa.Column("dag_id", sa.String(255), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("cost_component", sa.String(64), nullable=False),  # embedding | llm_probe | storage
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("units", sa.String(32), nullable=True),          # tokens | requests | gb-hours
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_infra_costs_org_dag", "infra_costs", ["organization_id", "dag_run_id"])
    op.create_index("ix_infra_costs_recorded_at", "infra_costs", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_infra_costs_recorded_at", table_name="infra_costs")
    op.drop_index("ix_infra_costs_org_dag", table_name="infra_costs")
    op.drop_table("infra_costs")
    op.drop_index("ix_embedding_costs_org_date", table_name="embedding_costs")
    op.drop_column("embedding_costs", "logged_at")
    op.drop_column("embedding_costs", "org_id")
