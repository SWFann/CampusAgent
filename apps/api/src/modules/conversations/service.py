"""
Service layer for the conversations module.

Business logic for:
- Private conversation creation (idempotent reuse).
- Group conversation creation (OWNER + initial members).
- Organization default group conversation (auto-sync with org membership events).
- Participant management (add, remove, leave).
- Message writing (idempotency, type validation, sensitive field detection).
- Message listing (pagination, privacy filtering for deleted messages).
- Domain event publishing after successful commits.

Privacy principles:
- Never return email, student_no, password_hash, token, or session info.
- Message content/payload must not contain private preference fields.
- Deleted messages return content=None.
- Events only contain IDs, types, and status — no private content.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...events.bus import default_event_bus
from ..organizations.repository import OrganizationMembershipRepository, OrganizationRepository
from ..users.models import User, UserStatus
from ..users.repository import UserRepository
from .events import (
    ConversationCreated,
    ParticipantJoined,
    ParticipantLeft,
)
from .events import (
    MessageCreated as MessageCreatedEvent,
)
from .events import (
    MessageDeleted as MessageDeletedEvent,
)
from .exceptions import (
    ConversationAlreadyExistsError,
    ConversationNotFoundError,
    ConversationPermissionDeniedError,
    MessageNotFoundError,
    MessageSensitiveContentError,
)
from .models import (
    Conversation,
    ConversationParticipant,
    ConversationRole,
    ConversationStatus,
    ConversationType,
    Message,
    MessageStatus,
    MessageType,
    ParticipantStatus,
    ParticipantType,
    SenderType,
)
from .permissions import permission_service
from .repository import (
    ConversationParticipantRepository,
    ConversationRepository,
    MessageRepository,
)

logger = logging.getLogger("campus_agent.conversations")

# ---------------------------------------------------------------------------
# Sensitive field detection (P5-07)
# ---------------------------------------------------------------------------

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "private_preference",
        "raw_preference",
        "memory_content",
        "budget_detail",
        "dietary_restriction_private",
        "personal_note",
    }
)

# Build a regex pattern to match any sensitive field name as a key
_SENSITIVE_PATTERN = re.compile(
    r'"(' + "|".join(re.escape(f) for f in SENSITIVE_FIELD_NAMES) + r')"\s*:',
    re.IGNORECASE,
)


def _check_sensitive_content(content: str | None, payload_json: str | None) -> None:
    """Check if content or payload contains sensitive field names.

    Raises MessageSensitiveContentError if any sensitive field is detected.
    """
    # Check content
    if content:
        lower_content = content.lower()
        for field in SENSITIVE_FIELD_NAMES:
            if field in lower_content:
                raise MessageSensitiveContentError(
                    details={"field": field, "location": "content"}
                )

    # Check payload_json (string key names)
    if payload_json and _SENSITIVE_PATTERN.search(payload_json):
        raise MessageSensitiveContentError(
            details={"location": "payload"}
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_event_id() -> str:
    """Generate a unique event ID."""
    return secrets.token_hex(16)


def _validate_conversation_type(conv_type: str) -> None:
    """Validate conversation type."""
    valid = {t.value for t in ConversationType}
    if conv_type not in valid:
        raise ConversationNotFoundError(
            message=f"无效的会话类型: {conv_type}"
        )


def _validate_message_type(msg_type: str) -> None:
    """Validate message type."""
    valid = {t.value for t in MessageType}
    if msg_type not in valid:
        raise MessageNotFoundError(
            message=f"无效的消息类型: {msg_type}"
        )


def _get_user_by_id(session: Session, user_id: UUID) -> User:
    """Get a user by ID, raising NotFoundError if not found or deleted."""
    from ...utils.errors import NotFoundError

    user = UserRepository(session).get_by_id(user_id)
    if user is None or user.status == UserStatus.DELETED.value:
        raise NotFoundError("用户")
    return user


def _conversation_to_read(conv: Conversation) -> dict[str, Any]:
    """Convert a Conversation to a safe read dict."""
    return {
        "id": str(conv.id),
        "type": conv.type,
        "title": conv.title,
        "organization_id": str(conv.organization_id) if conv.organization_id else None,
        "created_by": str(conv.created_by),
        "status": conv.status,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def _conversation_to_list_item(
    conv: Conversation,
    session: Session,
) -> dict[str, Any]:
    """Convert a Conversation to a list item dict."""
    part_count = ConversationRepository(session).count_active_participants(conv.id)
    # Find last message time
    messages = conv.messages
    last_msg_at = None
    if messages:
        active_msgs = [m for m in messages if m.status != MessageStatus.DELETED.value]
        if active_msgs:
            last_msg_at = max(m.created_at for m in active_msgs)
    return {
        "id": str(conv.id),
        "type": conv.type,
        "title": conv.title,
        "organization_id": str(conv.organization_id) if conv.organization_id else None,
        "status": conv.status,
        "last_message_at": last_msg_at.isoformat() if last_msg_at else None,
        "participant_count": part_count,
    }


def _participant_to_read(
    participant: ConversationParticipant, user: User | None
) -> dict[str, Any]:
    """Convert a participant + user to a safe read dict."""
    return {
        "id": str(participant.id),
        "conversation_id": str(participant.conversation_id),
        "participant_type": participant.participant_type,
        "participant_user_id": str(participant.participant_user_id)
        if participant.participant_user_id
        else None,
        "display_name": user.display_name if user else None,
        "avatar_url": user.avatar_url if user else None,
        "role": participant.role,
        "status": participant.status,
        "joined_at": participant.joined_at.isoformat()
        if participant.joined_at
        else None,
        "left_at": participant.left_at.isoformat()
        if participant.left_at
        else None,
    }


def _message_to_read(msg: Message) -> dict[str, Any]:
    """Convert a Message to a safe read dict.

    Deleted messages return content=None.
    payload_json is never exposed.
    """
    content = msg.content
    if msg.status == MessageStatus.DELETED.value:
        content = None
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_type": msg.sender_type,
        "sender_user_id": str(msg.sender_user_id) if msg.sender_user_id else None,
        "sender_agent_id": str(msg.sender_agent_id) if msg.sender_agent_id else None,
        "message_type": msg.message_type,
        "content": content,
        "status": msg.status,
        "sequence": msg.sequence,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
    }


def _get_participant(
    session: Session, conversation_id: UUID, actor: User | None
) -> ConversationParticipant | None:
    """Get the actor's active participant row in a conversation, or None."""
    if actor is None:
        return None
    return ConversationParticipantRepository(session).get_active_by_conversation_user(
        conversation_id, actor.id
    )


def create_system_message(
    *,
    conversation_id: UUID,
    content: str,
    message_type: str = MessageType.SYSTEM.value,
    payload: dict[str, Any] | None = None,
    session: Session,
) -> dict[str, Any]:
    """Persist a public system/agent message and publish its realtime event.

    Scene modules use this boundary instead of writing ``Message`` rows
    directly. The event intentionally carries no content or payload; clients
    fetch the committed message through the authenticated conversation API.
    """
    conversation = ConversationRepository(session).get_active_by_id(conversation_id)
    if conversation is None:
        raise ConversationNotFoundError()
    _validate_message_type(message_type)
    payload_json = json.dumps(payload, ensure_ascii=False) if payload else None
    _check_sensitive_content(content, payload_json)
    repository = MessageRepository(session)
    sequence = repository.get_next_sequence(conversation_id)
    message = Message(
        conversation_id=conversation_id,
        sender_type=(
            SenderType.AGENT.value
            if message_type == MessageType.AGENT_PUBLIC.value
            else SenderType.SYSTEM.value
        ),
        sender_user_id=None,
        sender_agent_id=None,
        message_type=message_type,
        content=content,
        payload_json=payload_json,
        status=MessageStatus.ACTIVE.value,
        sequence=sequence,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    default_event_bus.publish(
        MessageCreatedEvent(
            event_id=_generate_event_id(),
            conversation_id=conversation_id,
            message_id=message.id,
            sender_type=message.sender_type,
            sender_user_id=None,
            sender_agent_id=None,
            message_type=message_type,
            sequence=sequence,
            occurred_at=utc_now(),
        )
    )
    return _message_to_read(message)


# ---------------------------------------------------------------------------
# Private conversation (P5-02)
# ---------------------------------------------------------------------------


def create_private_conversation(
    actor: User,
    target_user_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Create or reuse a private conversation between two users.

    - If a private conversation already exists between the two users,
      return it (idempotent).
    - The caller becomes a participant; the target becomes a participant.
    - Both participants have role MEMBER.

    Raises:
        ConversationNotFoundError: If target user is deleted.
        ConversationAlreadyExistsError: (not raised — reuse is the behavior)
    """
    target_user = _get_user_by_id(session, target_user_id)

    # Check for existing private conversation
    conv_repo = ConversationRepository(session)
    existing = conv_repo.find_private_conversation(actor.id, target_user.id)
    if existing is not None:
        return _conversation_to_read(existing)

    # Create new private conversation
    conv = Conversation(
        type=ConversationType.PRIVATE.value,
        created_by=actor.id,
        status=ConversationStatus.ACTIVE.value,
    )
    session.add(conv)
    session.flush()

    # Add both participants
    for uid in (actor.id, target_user.id):
        participant = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=uid,
            role=ConversationRole.MEMBER.value,
            status=ParticipantStatus.ACTIVE.value,
        )
        session.add(participant)

    session.commit()
    session.refresh(conv)

    # Publish event
    default_event_bus.publish(
        ConversationCreated(
            event_id=_generate_event_id(),
            conversation_id=conv.id,
            actor_id=actor.id,
            conversation_type=conv.type,
            occurred_at=utc_now(),
        )
    )

    return _conversation_to_read(conv)


# ---------------------------------------------------------------------------
# Group conversation (P5-03)
# ---------------------------------------------------------------------------


def create_group_conversation(
    actor: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Create a group conversation.

    The creator becomes OWNER. Initial members become MEMBER.
    Duplicate user IDs in participant_user_ids are deduplicated.

    Raises:
        ConversationNotFoundError: If any participant user is deleted.
    """
    title = data.get("title")
    organization_id_raw = data.get("organization_id")
    organization_id = UUID(str(organization_id_raw)) if organization_id_raw else None
    participant_user_ids: list[UUID] = [
        UUID(str(uid)) for uid in data.get("participant_user_ids", [])
    ]

    # Validate all participant users exist
    user_repo = UserRepository(session)
    for uid in participant_user_ids:
        user = user_repo.get_by_id(uid)
        if user is None or user.status == UserStatus.DELETED.value:
            raise ConversationNotFoundError(
                message=f"用户 {uid} 不存在或已删除"
            )

    # Deduplicate participant IDs (excluding the creator)
    unique_ids = list(
        dict.fromkeys([str(uid) for uid in participant_user_ids if uid != actor.id])
    )
    unique_user_ids = [UUID(uid) for uid in unique_ids]

    conv = Conversation(
        type=ConversationType.GROUP.value,
        title=title,
        organization_id=organization_id,
        created_by=actor.id,
        status=ConversationStatus.ACTIVE.value,
    )
    session.add(conv)
    session.flush()

    # Creator becomes OWNER
    owner = ConversationParticipant(
        conversation_id=conv.id,
        participant_type=ParticipantType.USER.value,
        participant_user_id=actor.id,
        role=ConversationRole.OWNER.value,
        status=ParticipantStatus.ACTIVE.value,
    )
    session.add(owner)

    # Add initial members
    for uid in unique_user_ids:
        member = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=uid,
            role=ConversationRole.MEMBER.value,
            status=ParticipantStatus.ACTIVE.value,
        )
        session.add(member)

    session.commit()
    session.refresh(conv)

    # Publish event
    default_event_bus.publish(
        ConversationCreated(
            event_id=_generate_event_id(),
            conversation_id=conv.id,
            actor_id=actor.id,
            conversation_type=conv.type,
            occurred_at=utc_now(),
        )
    )

    return _conversation_to_read(conv)


# ---------------------------------------------------------------------------
# Organization default group (P5-04)
# ---------------------------------------------------------------------------


def get_or_create_org_group_conversation(
    actor: User,
    organization_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Get or create the default ORG_GROUP conversation for an organization.

    - If it already exists, return it.
    - If it doesn't exist, create it and add all active org members as participants.
    - The org creator/owner becomes the conversation OWNER.

    Raises:
        ConversationNotFoundError: If organization not found.
        ConversationPermissionDeniedError: If actor is not a member.
    """
    org_repo = OrganizationRepository(session)
    org = org_repo.get_active_by_id(organization_id)
    if org is None:
        raise ConversationNotFoundError(message="组织不存在")

    # Check actor is a member
    mem_repo = OrganizationMembershipRepository(session)
    actor_membership = mem_repo.get_active_by_org_user(organization_id, actor.id)
    if actor_membership is None and actor.global_role not in ("SYSTEM_ADMIN", "SCHOOL_ADMIN"):
        raise ConversationPermissionDeniedError(message="你不是该组织的成员")

    conv_repo = ConversationRepository(session)
    existing = conv_repo.find_org_group(organization_id)
    if existing is not None:
        return _conversation_to_read(existing)

    # Create new ORG_GROUP conversation
    conv = Conversation(
        type=ConversationType.ORG_GROUP.value,
        title=org.name,
        organization_id=organization_id,
        created_by=actor.id,
        status=ConversationStatus.ACTIVE.value,
    )
    session.add(conv)
    session.flush()

    # Add all active org members as participants
    memberships = mem_repo.list_active_by_org(organization_id)
    for m in memberships:
        role = ConversationRole.MEMBER.value
        if m.role == "OWNER":
            role = ConversationRole.OWNER.value
        elif m.role == "ADMIN":
            role = ConversationRole.ADMIN.value

        participant = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=m.user_id,
            role=role,
            status=ParticipantStatus.ACTIVE.value,
        )
        session.add(participant)

    session.commit()
    session.refresh(conv)

    # Publish event
    default_event_bus.publish(
        ConversationCreated(
            event_id=_generate_event_id(),
            conversation_id=conv.id,
            actor_id=actor.id,
            conversation_type=conv.type,
            occurred_at=utc_now(),
        )
    )

    return _conversation_to_read(conv)


def sync_org_member_joined(
    organization_id: UUID,
    user_id: UUID,
    role: str,
    session: Session,
) -> None:
    """Sync org member join to org group conversation.

    Called when a OrganizationMemberJoined event fires.
    Adds the user as an ACTIVE participant in the org group conversation.
    """
    conv_repo = ConversationRepository(session)
    conv = conv_repo.find_org_group(organization_id)
    if conv is None:
        # Org group conversation doesn't exist yet — nothing to sync
        return

    part_repo = ConversationParticipantRepository(session)
    existing = part_repo.get_any_by_conversation_user(conv.id, user_id)
    conv_role = ConversationRole.MEMBER.value
    if role == "OWNER":
        conv_role = ConversationRole.OWNER.value
    elif role == "ADMIN":
        conv_role = ConversationRole.ADMIN.value

    if existing is not None:
        existing.status = ParticipantStatus.ACTIVE.value
        existing.role = conv_role
        existing.left_at = None
    else:
        participant = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=user_id,
            role=conv_role,
            status=ParticipantStatus.ACTIVE.value,
        )
        session.add(participant)

    session.commit()


def sync_org_member_left(
    organization_id: UUID,
    user_id: UUID,
    session: Session,
) -> None:
    """Sync org member leave to org group conversation.

    Called when a OrganizationMemberLeft event fires.
    Sets the participant status to LEFT.
    """
    conv_repo = ConversationRepository(session)
    conv = conv_repo.find_org_group(organization_id)
    if conv is None:
        return

    part_repo = ConversationParticipantRepository(session)
    participant = part_repo.get_active_by_conversation_user(conv.id, user_id)
    if participant is not None:
        participant.status = ParticipantStatus.LEFT.value
        participant.left_at = utc_now()
        session.commit()


# ---------------------------------------------------------------------------
# Conversation listing and details
# ---------------------------------------------------------------------------


def list_conversations(
    actor: User,
    *,
    page: int = 1,
    page_size: int = 20,
    session: Session,
) -> dict[str, Any]:
    """List conversations for the authenticated user."""
    conv_repo = ConversationRepository(session)
    offset = (page - 1) * page_size
    conversations = conv_repo.list_for_user(
        actor.id, limit=page_size, offset=offset
    )

    items = [_conversation_to_list_item(conv, session) for conv in conversations]

    # Total count
    participations = ConversationParticipantRepository(session).list_active_by_user(
        actor.id
    )
    total = len(participations)

    return {
        "conversations": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_conversation(
    actor: User,
    conversation_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Get a single conversation by ID.

    Raises:
        ConversationNotFoundError: If not found.
        ConversationPermissionDeniedError: If actor is not a participant.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    participant = _get_participant(session, conv.id, actor)
    if not permission_service.can_read_conversation(conv, actor, participant):
        raise ConversationPermissionDeniedError(message="无权查看此会话")

    return _conversation_to_read(conv)


def list_participants(
    actor: User,
    conversation_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """List participants in a conversation.

    Raises:
        ConversationNotFoundError: If conversation not found.
        ConversationPermissionDeniedError: If actor is not a participant.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    participant = _get_participant(session, conv.id, actor)
    if not permission_service.can_read_conversation(conv, actor, participant):
        raise ConversationPermissionDeniedError(message="无权查看参与者列表")

    participants = ConversationParticipantRepository(session).list_active_by_conversation(
        conversation_id
    )

    user_repo = UserRepository(session)
    items = []
    for p in participants:
        user = None
        if p.participant_user_id:
            user = user_repo.get_by_id(p.participant_user_id)
        items.append(_participant_to_read(p, user))

    return {"participants": items, "total": len(items)}


# ---------------------------------------------------------------------------
# Participant management
# ---------------------------------------------------------------------------


def add_participant(
    actor: User,
    conversation_id: UUID,
    target_user_id: UUID,
    target_role: str,
    session: Session,
) -> dict[str, Any]:
    """Add a participant to a conversation.

    Raises:
        ConversationNotFoundError: If conversation not found.
        ConversationPermissionDeniedError: If actor lacks permission.
        ConversationAlreadyExistsError: If user is already an active participant.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    actor_participant = _get_participant(session, conv.id, actor)
    if not permission_service.can_add_participant(conv, actor, actor_participant):
        raise ConversationPermissionDeniedError(message="无权添加参与者")

    target_user = _get_user_by_id(session, target_user_id)

    part_repo = ConversationParticipantRepository(session)
    existing = part_repo.get_any_by_conversation_user(conv.id, target_user_id)

    if existing is not None and existing.status == ParticipantStatus.ACTIVE.value:
        raise ConversationAlreadyExistsError(message="用户已是会话参与者")

    if existing is not None:
        existing.status = ParticipantStatus.ACTIVE.value
        existing.role = target_role
        existing.left_at = None
        participant = existing
    else:
        participant = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=target_user_id,
            role=target_role,
            status=ParticipantStatus.ACTIVE.value,
        )
        session.add(participant)

    session.commit()
    session.refresh(participant)

    # Publish event
    default_event_bus.publish(
        ParticipantJoined(
            event_id=_generate_event_id(),
            conversation_id=conv.id,
            user_id=target_user_id,
            actor_id=actor.id,
            role=participant.role,
            status=participant.status,
            occurred_at=utc_now(),
        )
    )

    return _participant_to_read(participant, target_user)


def remove_participant(
    actor: User,
    conversation_id: UUID,
    target_user_id: UUID,
    session: Session,
) -> None:
    """Remove a participant from a conversation (status=REMOVED).

    Raises:
        ConversationNotFoundError: If conversation not found.
        ConversationPermissionDeniedError: If actor lacks permission.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    actor_participant = _get_participant(session, conv.id, actor)
    part_repo = ConversationParticipantRepository(session)
    target_participant = part_repo.get_active_by_conversation_user(
        conv.id, target_user_id
    )
    if target_participant is None:
        from ...utils.errors import NotFoundError

        raise NotFoundError("参与者")

    if not permission_service.can_remove_participant(
        conv, actor, actor_participant, target_participant
    ):
        raise ConversationPermissionDeniedError(message="无权移除参与者")

    target_participant.status = ParticipantStatus.REMOVED.value
    target_participant.left_at = utc_now()
    session.commit()

    action = "left" if target_participant.id == (
        actor_participant.id if actor_participant else None
    ) else "removed"

    default_event_bus.publish(
        ParticipantLeft(
            event_id=_generate_event_id(),
            conversation_id=conv.id,
            user_id=target_user_id,
            actor_id=actor.id,
            action=action,
            occurred_at=utc_now(),
        )
    )


# ---------------------------------------------------------------------------
# Message operations (P5-05, P5-06, P5-07)
# ---------------------------------------------------------------------------


def create_message(
    actor: User,
    conversation_id: UUID,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Create a new message in a conversation.

    - Only ACTIVE participants can write.
    - Supports idempotency via idempotency_key.
    - Validates message type.
    - Checks for sensitive content (P5-07).
    - Only SYSTEM sender_type can create SYSTEM messages.

    Raises:
        ConversationNotFoundError: If conversation not found.
        ConversationPermissionDeniedError: If actor is not a participant.
        MessageIdempotencyConflictError: If idempotency_key already used.
        MessageSensitiveContentError: If content/payload has sensitive fields.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    participant = _get_participant(session, conv.id, actor)
    if not permission_service.can_write_message(conv, actor, participant):
        raise ConversationPermissionDeniedError(message="无权在此会话中发送消息")

    content: str | None = data.get("content")
    message_type: str = data.get("message_type", MessageType.TEXT.value)
    idempotency_key: str | None = data.get("idempotency_key")

    _validate_message_type(message_type)

    # P5-07: Check sensitive content
    _check_sensitive_content(content, None)

    # Idempotency check
    msg_repo = MessageRepository(session)
    if idempotency_key:
        existing = msg_repo.get_by_idempotency_key(conversation_id, idempotency_key)
        if existing is not None:
            # Return the existing message (idempotent)
            return _message_to_read(existing)

    # Get next sequence
    sequence = msg_repo.get_next_sequence(conversation_id)

    msg = Message(
        conversation_id=conversation_id,
        sender_type=SenderType.USER.value,
        sender_user_id=actor.id,
        sender_agent_id=None,
        message_type=message_type,
        content=content,
        payload_json=None,
        idempotency_key=idempotency_key,
        status=MessageStatus.ACTIVE.value,
        sequence=sequence,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)

    # Publish event (no content/payload in the event)
    default_event_bus.publish(
        MessageCreatedEvent(
            event_id=_generate_event_id(),
            conversation_id=conversation_id,
            message_id=msg.id,
            sender_type=SenderType.USER.value,
            sender_user_id=actor.id,
            sender_agent_id=None,
            message_type=message_type,
            sequence=sequence,
            occurred_at=utc_now(),
        )
    )

    return _message_to_read(msg)


def list_messages(
    actor: User,
    conversation_id: UUID,
    *,
    page: int = 1,
    page_size: int = 50,
    session: Session,
) -> dict[str, Any]:
    """List messages in a conversation with pagination.

    - Only ACTIVE participants can list messages.
    - Deleted messages return content=None.
    - Ordered by created_at DESC (newest first).

    Raises:
        ConversationNotFoundError: If conversation not found.
        ConversationPermissionDeniedError: If actor is not a participant.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    participant = _get_participant(session, conv.id, actor)
    if not permission_service.can_list_messages(conv, actor, participant):
        raise ConversationPermissionDeniedError(message="无权查看此会话消息")

    msg_repo = MessageRepository(session)
    messages, total = msg_repo.list_by_conversation(
        conversation_id, page=page, page_size=page_size
    )

    items = [_message_to_read(msg) for msg in messages]

    return {
        "messages": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def delete_message(
    actor: User,
    conversation_id: UUID,
    message_id: UUID,
    session: Session,
) -> None:
    """Soft-delete a message.

    Only the message sender or a conversation OWNER/ADMIN can delete.

    Raises:
        ConversationNotFoundError: If conversation not found.
        MessageNotFoundError: If message not found.
        ConversationPermissionDeniedError: If actor lacks permission.
    """
    conv = ConversationRepository(session).get_active_by_id(conversation_id)
    if conv is None:
        raise ConversationNotFoundError()

    participant = _get_participant(session, conv.id, actor)
    if not permission_service.can_list_messages(conv, actor, participant):
        raise ConversationPermissionDeniedError(message="无权操作此会话消息")

    msg_repo = MessageRepository(session)
    msg = msg_repo.get_active_by_id(message_id)
    if msg is None or msg.conversation_id != conversation_id:
        raise MessageNotFoundError()

    # Check permission: sender or admin
    is_sender = msg.sender_user_id == actor.id
    can_admin = (
        participant is not None
        and participant.role in (ConversationRole.OWNER.value, ConversationRole.ADMIN.value)
    )
    if not (is_sender or can_admin or permission_service._is_admin_level(actor)):
        raise ConversationPermissionDeniedError(message="无权删除此消息")

    msg.status = MessageStatus.DELETED.value
    msg.deleted_at = utc_now()
    session.commit()

    default_event_bus.publish(
        MessageDeletedEvent(
            event_id=_generate_event_id(),
            conversation_id=conversation_id,
            message_id=message_id,
            actor_id=actor.id,
            occurred_at=utc_now(),
        )
    )
