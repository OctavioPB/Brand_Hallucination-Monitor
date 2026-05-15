"""Add Sprint 10 tables: organizations, onboarding_states, nps_responses, feature_flags.

Revision ID: 009
Revises: 008
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. organizations — canonical org record created at signup
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False, server_default="trial"),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("onboarding_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])
    op.create_unique_constraint("uq_organizations_email", "organizations", ["email"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.create_index("ix_organizations_email", "organizations", ["email"])

    # 2. onboarding_states — wizard step tracking
    op.create_table(
        "onboarding_states",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("current_step", sa.String(64), nullable=False, server_default="account_created"),
        sa.Column("brand_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("first_scan_job_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("tour_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_onboarding_states_org", "onboarding_states", ["organization_id"])
    op.create_index("ix_onboarding_states_org", "onboarding_states", ["organization_id"])

    # 3. nps_responses
    op.create_table(
        "nps_responses",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("trigger", sa.String(64), nullable=False, server_default="first_report"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_nps_responses_org", "nps_responses", ["organization_id"])

    # 4. feature_flags
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("flag_key", sa.String(128), nullable=False),
        sa.Column("organization_id", sa.String(128), nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("rollout_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_feature_flags_key", "feature_flags", ["flag_key"])
    op.create_index("ix_feature_flags_org", "feature_flags", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_feature_flags_org", table_name="feature_flags")
    op.drop_index("ix_feature_flags_key", table_name="feature_flags")
    op.drop_table("feature_flags")
    op.drop_index("ix_nps_responses_org", table_name="nps_responses")
    op.drop_table("nps_responses")
    op.drop_index("ix_onboarding_states_org", table_name="onboarding_states")
    op.drop_constraint("uq_onboarding_states_org", "onboarding_states")
    op.drop_table("onboarding_states")
    op.drop_index("ix_organizations_email", table_name="organizations")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_constraint("uq_organizations_email", "organizations")
    op.drop_constraint("uq_organizations_slug", "organizations")
    op.drop_table("organizations")
