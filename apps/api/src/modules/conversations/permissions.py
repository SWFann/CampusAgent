"""
Centralized permission service for conversation actions.

This module implements the access control for conversations:
- Only ACTIVE participants can read messages or subscribe to WebSocket.
- OWNER can add/remove participants in GROUP conversations.
- In ORG_GROUP, all active org members can participate.
- Private conversations: only the two participants can access.
- Non-members cannot read, write, subscribe, or list messages.

Privacy requirements:
- Never expose email, student_no, password_hash, or private preference content.
"""

from __future__ import annotations

from ..users.models import GlobalRole, User
from .models import (
    Conversation,
    ConversationParticipant,
    ConversationRole,
    ConversationType,
    ParticipantStatus,
    ParticipantType,
)


class ConversationPermissionService:
    """Centralized permission checker for conversation actions."""

    def _is_system_admin(self, actor: User) -> bool:
        return actor.global_role == GlobalRole.SYSTEM_ADMIN.value

    def _is_admin_level(self, actor: User) -> bool:
        """Check if the actor has a global admin role."""
        return self._is_system_admin(actor) or actor.global_role in (
            GlobalRole.SCHOOL_ADMIN.value,
        )

    def is_participant(
        self, conversation: Conversation, actor: User | None
    ) -> bool:
        """Check if the actor is an active participant."""
        if actor is None:
            return False
        return any(
            p.participant_user_id == actor.id
            and p.participant_type == ParticipantType.USER.value
            and p.status == ParticipantStatus.ACTIVE.value
            for p in conversation.participants
        )

    def can_read_conversation(
        self,
        conversation: Conversation,
        actor: User | None,
        participant: ConversationParticipant | None,
    ) -> bool:
        """Check if the actor can read the conversation."""
        if actor is not None and self._is_admin_level(actor):
            return True
        return participant is not None and participant.status == ParticipantStatus.ACTIVE.value

    def can_list_messages(
        self,
        conversation: Conversation,
        actor: User,
        participant: ConversationParticipant | None,
    ) -> bool:
        """Check if the actor can list messages in a conversation."""
        if self._is_admin_level(actor):
            return True
        return participant is not None and participant.status == ParticipantStatus.ACTIVE.value

    def can_write_message(
        self,
        conversation: Conversation,
        actor: User,
        participant: ConversationParticipant | None,
    ) -> bool:
        """Check if the actor can write a message to a conversation."""
        if self._is_admin_level(actor):
            return True
        return participant is not None and participant.status == ParticipantStatus.ACTIVE.value

    def can_add_participant(
        self,
        conversation: Conversation,
        actor: User,
        actor_participant: ConversationParticipant | None,
    ) -> bool:
        """Check if the actor can add a participant."""
        if self._is_admin_level(actor):
            return True

        # Private conversations don't allow adding participants
        if conversation.type == ConversationType.PRIVATE.value:
            return False

        # ORG_GROUP: org members are auto-added via event sync
        if conversation.type == ConversationType.ORG_GROUP.value:
            # Only OWNER or ADMIN can manually add
            if actor_participant is None:
                return False
            if actor_participant.status != ParticipantStatus.ACTIVE.value:
                return False
            return actor_participant.role in (
                ConversationRole.OWNER.value,
                ConversationRole.ADMIN.value,
            )

        # GROUP: OWNER or ADMIN can add
        if actor_participant is None:
            return False
        if actor_participant.status != ParticipantStatus.ACTIVE.value:
            return False
        return actor_participant.role in (
            ConversationRole.OWNER.value,
            ConversationRole.ADMIN.value,
        )

    def can_remove_participant(
        self,
        conversation: Conversation,
        actor: User,
        actor_participant: ConversationParticipant | None,
        target_participant: ConversationParticipant,
    ) -> bool:
        """Check if the actor can remove a participant."""
        if self._is_admin_level(actor):
            return True

        # Self-removal (leaving) is always allowed
        if (
            actor_participant is not None
            and target_participant.id == actor_participant.id
        ):
            return True

        if actor_participant is None:
            return False
        if actor_participant.status != ParticipantStatus.ACTIVE.value:
            return False

        return actor_participant.role in (
            ConversationRole.OWNER.value,
            ConversationRole.ADMIN.value,
        )

    def can_subscribe(
        self,
        conversation: Conversation,
        actor: User,
        participant: ConversationParticipant | None,
    ) -> bool:
        """Check if the actor can subscribe to WebSocket events for a conversation."""
        if self._is_admin_level(actor):
            return True
        return participant is not None and participant.status == ParticipantStatus.ACTIVE.value


# Singleton instance for reuse
permission_service = ConversationPermissionService()
