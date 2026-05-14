"""Sprint 5: probe_results table for LLM probing audit trail

Revision ID: 005
Revises: 004
Create Date: 2026-05-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "probe_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("model_name", sa.String(64), nullable=False),
        sa.Column("probe_prompt", sa.Text(), nullable=False),
        sa.Column("llm_response", sa.Text(), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hallucinations_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dag_run_id", sa.String(256), nullable=False, server_default="manual"),
        sa.Column(
            "probed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_probe_results_brand_id", "probe_results", ["brand_id"])
    op.create_index("ix_probe_results_model_name", "probe_results", ["model_name"])
    op.create_index("ix_probe_results_probed_at", "probe_results", ["probed_at"])
    op.create_index(
        "ix_probe_results_org_model",
        "probe_results",
        ["organization_id", "model_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_probe_results_org_model", table_name="probe_results")
    op.drop_index("ix_probe_results_probed_at", table_name="probe_results")
    op.drop_index("ix_probe_results_model_name", table_name="probe_results")
    op.drop_index("ix_probe_results_brand_id", table_name="probe_results")
    op.drop_table("probe_results")
