"""create organization and organization_memberships tables

Revision ID: 0003_org_member
Revises: 0002_user_auth
Create Date: 2026-07-17 10:00:00

This migration creates the two P4 tables:
- ``organizations``: campus organization entity with tree structure
- ``organization_memberships``: user-to-org membership with role and status

Downgrade drops both tables in reverse dependency order.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_org_member"
down_revision: str | None = "0002_user_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create organizations and organization_memberships tables."""

    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=True, unique=True),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "visibility",
            sa.String(40),
            nullable=False,
            server_default="PUBLIC",
        ),
        sa.Column(
            "join_policy",
            sa.String(40),
            nullable=False,
            server_default="INVITE_ONLY",
        ),
        sa.Column(
            "status",
            sa.String(40),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_organizations_parent_id", "organizations", ["parent_id"])
    op.create_index("ix_organizations_type", "organizations", ["type"])
    op.create_index("ix_organizations_status", "organizations", ["status"])

    # --- organization_memberships ---
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(40),
            nullable=False,
            server_default="MEMBER",
        ),
        sa.Column(
            "status",
            sa.String(40),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "invited_by",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_org_user",
        ),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_memberships_user_id",
        "organization_memberships",
        ["user_id"],
    )
    op.create_index(
        "ix_organization_memberships_role",
        "organization_memberships",
        ["role"],
    )
    op.create_index(
        "ix_organization_memberships_status",
        "organization_memberships",
        ["status"],
    )


def downgrade() -> None:
    """Drop organization_memberships and organizations tables."""
    op.drop_index(
        "ix_organization_memberships_status",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_role",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_user_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")

    op.drop_index("ix_organizations_status", table_name="organizations")
    op.drop_index("ix_organizations_type", table_name="organizations")
    op.drop_index("ix_organizations_parent_id", table_name="organizations")
    op.drop_table("organizations")
