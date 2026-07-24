"""student phone and agent code

Revision ID: 0009_student_phone_agent_code
Revises: 0008_contact_relationships
Create Date: 2026-07-20 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_student_phone_agent_code"
down_revision: str | None = "0008_contact_relationships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _student_profiles_table(*, include_phone_agent: bool) -> sa.Table:
    columns: list[sa.Column[object]] = [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("student_no", sa.String(length=50), nullable=False, unique=True),
        sa.Column("enrollment_year", sa.Integer(), nullable=True),
        sa.Column("major_name", sa.String(length=200), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("profile_visibility", sa.String(length=20), nullable=False, server_default="PUBLIC"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]
    if include_phone_agent:
        columns[3:3] = [
            sa.Column("phone_number", sa.String(length=24), nullable=True),
            sa.Column("agent_code", sa.String(length=80), nullable=True),
        ]
    constraints: list[sa.Constraint] = []
    if include_phone_agent:
        constraints.extend(
            [
                sa.UniqueConstraint("phone_number", name="uq_student_profiles_phone_number"),
                sa.UniqueConstraint("agent_code", name="uq_student_profiles_agent_code"),
            ]
        )
    table = sa.Table(
        "student_profiles",
        sa.MetaData(),
        *columns,
        *constraints,
    )
    sa.Index("ix_student_profiles_student_no", table.c.student_no, unique=True)
    return table


def upgrade() -> None:
    # Batch mode recreates the table on SQLite, where ALTER TABLE cannot
    # add named unique constraints, and remains a normal ALTER elsewhere.
    with op.batch_alter_table(
        "student_profiles",
        copy_from=_student_profiles_table(include_phone_agent=False),
    ) as batch_op:
        batch_op.add_column(sa.Column("phone_number", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("agent_code", sa.String(length=80), nullable=True))
        batch_op.create_unique_constraint(
            "uq_student_profiles_phone_number",
            ["phone_number"],
        )
        batch_op.create_unique_constraint(
            "uq_student_profiles_agent_code",
            ["agent_code"],
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "student_profiles",
        copy_from=_student_profiles_table(include_phone_agent=True),
    ) as batch_op:
        batch_op.drop_constraint("uq_student_profiles_agent_code", type_="unique")
        batch_op.drop_constraint("uq_student_profiles_phone_number", type_="unique")
        batch_op.drop_column("agent_code")
        batch_op.drop_column("phone_number")
