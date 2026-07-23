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


def upgrade() -> None:
    with op.batch_alter_table("scene_instances") as batch_op:
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
    with op.batch_alter_table("scene_instances") as batch_op:
        batch_op.drop_index("ix_scene_instances_organization_id")
        batch_op.drop_constraint(
            "fk_scene_instances_organization_id",
            type_="foreignkey",
        )
        batch_op.drop_column("organization_id")
