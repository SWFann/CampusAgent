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


def upgrade() -> None:
    # Batch mode recreates the table on SQLite, where ALTER TABLE cannot
    # add named unique constraints, and remains a normal ALTER elsewhere.
    with op.batch_alter_table("student_profiles") as batch_op:
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
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.drop_constraint("uq_student_profiles_agent_code", type_="unique")
        batch_op.drop_constraint("uq_student_profiles_phone_number", type_="unique")
        batch_op.drop_column("agent_code")
        batch_op.drop_column("phone_number")
