"""add encrypted personal workspace task threads

Revision ID: 0010_workspace_threads
Revises: 0009_student_phone_agent_code
Create Date: 2026-07-21 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_workspace_threads"
down_revision: str | None = "0009_student_phone_agent_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False, server_default="新的个人任务"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_workspace_threads_owner_user_id", "workspace_threads", ["owner_user_id"])
    op.create_index(
        "ix_workspace_threads_owner_updated",
        "workspace_threads",
        ["owner_user_id", "updated_at"],
    )

    op.create_table(
        "workspace_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "thread_id",
            sa.Uuid(),
            sa.ForeignKey("workspace_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content_encrypted", sa.Text(), nullable=False),
        sa.Column("encryption_key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_messages_thread_id", "workspace_messages", ["thread_id"])
    op.create_index(
        "ix_workspace_messages_thread_created",
        "workspace_messages",
        ["thread_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_messages_thread_created", table_name="workspace_messages")
    op.drop_index("ix_workspace_messages_thread_id", table_name="workspace_messages")
    op.drop_table("workspace_messages")
    op.drop_index("ix_workspace_threads_owner_updated", table_name="workspace_threads")
    op.drop_index("ix_workspace_threads_owner_user_id", table_name="workspace_threads")
    op.drop_table("workspace_threads")
