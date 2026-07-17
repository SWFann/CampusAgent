"""create agent, memory, consent, audit, and agent_run tables

Revision ID: 0005_agent_memory
Revises: 0004_convo_msg
Create Date: 2026-07-17 14:00:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_agent_memory"
down_revision: str | None = "0004_convo_msg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("public_persona", sa.Text(), nullable=True),
        sa.Column("private_config_encrypted", sa.Text(), nullable=True),
        sa.Column("delegation_level", sa.String(10), nullable=False, server_default="L0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agents_owner_user_id", "agents", ["owner_user_id"])

    # agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("input_hash", sa.String(128), nullable=True),
        sa.Column("output_hash", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="SUCCESS"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_runs_agent_id", "agent_runs", ["agent_id"])
    op.create_index("ix_agent_runs_actor_user_id", "agent_runs", ["actor_user_id"])

    # memory_items
    op.create_table(
        "memory_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("sensitivity_level", sa.String(20), nullable=False, server_default="INTERNAL"),
        sa.Column("source", sa.String(40), nullable=False, server_default="USER_INPUT"),
        sa.Column("content_encrypted", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("encryption_key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_items_owner_user_id", "memory_items", ["owner_user_id"])
    op.create_index("ix_memory_items_agent_id", "memory_items", ["agent_id"])
    op.create_index("ix_memory_items_category", "memory_items", ["category"])

    # consent_records
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("grantor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("grantee_agent_id", sa.Uuid(), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("scope_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="GRANTED"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("memory_id", sa.Uuid(), sa.ForeignKey("memory_items.id"), nullable=True),
    )
    op.create_index("ix_consent_records_grantor_user_id", "consent_records", ["grantor_user_id"])
    op.create_index("ix_consent_records_grantee_agent_id", "consent_records", ["grantee_agent_id"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("purpose", sa.String(50), nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_consent_records_grantee_agent_id", table_name="consent_records")
    op.drop_index("ix_consent_records_grantor_user_id", table_name="consent_records")
    op.drop_table("consent_records")

    op.drop_index("ix_memory_items_category", table_name="memory_items")
    op.drop_index("ix_memory_items_agent_id", table_name="memory_items")
    op.drop_index("ix_memory_items_owner_user_id", table_name="memory_items")
    op.drop_table("memory_items")

    op.drop_index("ix_agent_runs_actor_user_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_agent_id", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_agents_owner_user_id", table_name="agents")
    op.drop_table("agents")
