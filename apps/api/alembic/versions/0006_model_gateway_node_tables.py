"""create model_definition, model_node, and model_deployment tables

Revision ID: 0006_model_node
Revises: 0005_agent_memory
Create Date: 2026-07-18 20:00:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_model_node"
down_revision: str | None = "0005_agent_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # model_definitions
    op.create_table(
        "model_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model_type", sa.String(20), nullable=False),
        sa.Column("capabilities_json", sa.Text(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("default_temperature", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_definitions_name", "model_definitions", ["name"])

    # model_nodes
    op.create_table(
        "model_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("endpoint_encrypted", sa.Text(), nullable=False),
        sa.Column("credential_encrypted", sa.Text(), nullable=True),
        sa.Column("namespace", sa.String(100), nullable=True),
        sa.Column("exposure_type", sa.String(20), nullable=False),
        sa.Column("health_status", sa.String(20), nullable=False, server_default="ONLINE"),
        sa.Column("status", sa.String(20), nullable=False, server_default="registering"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capabilities_json", sa.Text(), nullable=True),
        sa.Column("models_supported_json", sa.Text(), nullable=True),
        sa.Column("max_concurrent_requests", sa.Integer(), nullable=True),
        sa.Column("current_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uptime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_model_nodes_name", "model_nodes", ["name"])

    # model_deployments
    op.create_table(
        "model_deployments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "model_id",
            sa.Uuid(),
            sa.ForeignKey("model_definitions.id"),
            nullable=False,
        ),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("model_nodes.id"),
            nullable=False,
        ),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="deployed"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("capabilities_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_deployments_model_id", "model_deployments", ["model_id"])
    op.create_index("ix_model_deployments_node_id", "model_deployments", ["node_id"])


def downgrade() -> None:
    op.drop_index("ix_model_deployments_node_id", table_name="model_deployments")
    op.drop_index("ix_model_deployments_model_id", table_name="model_deployments")
    op.drop_table("model_deployments")

    op.drop_index("ix_model_nodes_name", table_name="model_nodes")
    op.drop_table("model_nodes")

    op.drop_index("ix_model_definitions_name", table_name="model_definitions")
    op.drop_table("model_definitions")
