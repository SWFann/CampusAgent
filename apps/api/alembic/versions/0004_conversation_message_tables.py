"""create conversation, participant, and message tables

Revision ID: 0004_convo_msg
Revises: 0003_org_member
Create Date: 2026-07-17 12:00:00

This migration creates the three P5 tables:
- ``conversations``: chat containers (PRIVATE/GROUP/ORG_GROUP/SCENE)
- ``conversation_participants``: user/agent membership in conversations
- ``messages``: individual messages within conversations

Downgrade drops all three tables in reverse dependency order.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_convo_msg"
down_revision: str | None = "0003_org_member"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create conversations, conversation_participants, and messages tables."""

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(40),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_conversations_type", "conversations", ["type"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index(
        "ix_conversations_organization_id", "conversations", ["organization_id"]
    )

    # --- conversation_participants ---
    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "participant_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "participant_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("participant_agent_id", sa.Uuid(), nullable=True),
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
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "conversation_id",
            "participant_type",
            "participant_user_id",
            "participant_agent_id",
            name="uq_conversation_participants_unique",
        ),
    )
    op.create_index(
        "ix_conversation_participants_conversation_id",
        "conversation_participants",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_participants_participant_user_id",
        "conversation_participants",
        ["participant_user_id"],
    )
    op.create_index(
        "ix_conversation_participants_status",
        "conversation_participants",
        ["status"],
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "sender_type",
            sa.String(20),
            nullable=False,
            server_default="USER",
        ),
        sa.Column(
            "sender_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("sender_agent_id", sa.Uuid(), nullable=True),
        sa.Column(
            "message_type",
            sa.String(40),
            nullable=False,
            server_default="TEXT",
        ),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=True),
        sa.Column(
            "status",
            sa.String(40),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_messages_conversation_id", "messages", ["conversation_id"]
    )
    op.create_index(
        "ix_messages_created_at", "messages", ["created_at"]
    )
    op.create_index(
        "ix_messages_idempotency_key", "messages", ["idempotency_key"]
    )
    op.create_index("ix_messages_status", "messages", ["status"])
    # Composite index for pagination: conversation_id + created_at
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    """Drop messages, conversation_participants, and conversations tables."""
    op.drop_index("ix_messages_status", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_messages_idempotency_key", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index(
        "ix_conversation_participants_status",
        table_name="conversation_participants",
    )
    op.drop_index(
        "ix_conversation_participants_participant_user_id",
        table_name="conversation_participants",
    )
    op.drop_index(
        "ix_conversation_participants_conversation_id",
        table_name="conversation_participants",
    )
    op.drop_table("conversation_participants")

    op.drop_index("ix_conversations_organization_id", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_index("ix_conversations_type", table_name="conversations")
    op.drop_table("conversations")
