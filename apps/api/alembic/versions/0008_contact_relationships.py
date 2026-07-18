"""contact relationships

Revision ID: 0008_contact_relationships
Revises: 0007_scene_core
Create Date: 2026-07-18 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_contact_relationships"
down_revision: str | None = "0007_scene_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contact_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requester_id", sa.Uuid(), nullable=False),
        sa.Column("addressee_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["addressee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_contacts_pair"),
    )
    op.create_index(
        op.f("ix_contact_relationships_requester_id"),
        "contact_relationships",
        ["requester_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_contact_relationships_addressee_id"),
        "contact_relationships",
        ["addressee_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_contact_relationships_addressee_id"),
        table_name="contact_relationships",
    )
    op.drop_index(
        op.f("ix_contact_relationships_requester_id"),
        table_name="contact_relationships",
    )
    op.drop_table("contact_relationships")
