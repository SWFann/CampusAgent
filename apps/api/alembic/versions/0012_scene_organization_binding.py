"""bind scene instances to campus organizations

Revision ID: 0012_scene_org_binding
Revises: 0011_agent_model_route
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_scene_org_binding"
down_revision: str | None = "0011_agent_model_route"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _scene_instances_table(*, include_organization: bool) -> sa.Table:
    columns: list[sa.Column[object]] = [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("definition_id", sa.Uuid(), sa.ForeignKey("scene_definitions.id"), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("current_phase", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("public_context_json", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]
    if include_organization:
        columns[3:3] = [
            sa.Column(
                "organization_id",
                sa.Uuid(),
                sa.ForeignKey("organizations.id", name="fk_scene_instances_organization_id"),
                nullable=True,
            )
        ]
    table = sa.Table("scene_instances", sa.MetaData(), *columns)
    sa.Index("ix_scene_instances_definition_id", table.c.definition_id)
    sa.Index("ix_scene_instances_conversation_id", table.c.conversation_id)
    sa.Index("ix_scene_instances_created_by", table.c.created_by)
    sa.Index("ix_scene_instances_idempotency_key", table.c.idempotency_key)
    sa.Index("ix_scene_instances_status", table.c.status)
    if include_organization:
        sa.Index("ix_scene_instances_organization_id", table.c.organization_id)
    return table


def upgrade() -> None:
    with op.batch_alter_table(
        "scene_instances",
        copy_from=_scene_instances_table(include_organization=False),
    ) as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_scene_instances_organization_id",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_scene_instances_organization_id",
            ["organization_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "scene_instances",
        copy_from=_scene_instances_table(include_organization=True),
    ) as batch_op:
        batch_op.drop_index("ix_scene_instances_organization_id")
        batch_op.drop_constraint(
            "fk_scene_instances_organization_id",
            type_="foreignkey",
        )
        batch_op.drop_column("organization_id")
