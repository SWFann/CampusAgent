from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.events.bus import DomainEvent, default_event_bus
from src.modules.conversations.events import MessageCreated
from src.modules.conversations.models import (
    Conversation,
    ConversationParticipant,
    ConversationRole,
    ConversationType,
    MessageType,
    ParticipantType,
)
from src.modules.conversations.service import create_system_message
from src.modules.scenes import chat_dorm_dinner
from src.modules.scenes.models import SceneCandidate, SceneDefinition, SceneInstance
from src.modules.users.models import GlobalRole, User, UserStatus
from src.utils.errors import NotFoundError


class _Actor:
    def __init__(self) -> None:
        self.id = uuid4()


class _Session:
    def commit(self) -> None:
        return None

    def refresh(self, _instance: object) -> None:
        return None


def test_system_scene_message_publishes_realtime_event(test_db_session: Session) -> None:
    conversation = Conversation(type=ConversationType.GROUP.value, created_by=uuid4())
    test_db_session.add(conversation)
    test_db_session.commit()
    received: list[MessageCreated] = []

    class Handler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, MessageCreated)
            received.append(event)

    default_event_bus.subscribe(MessageCreated, Handler())

    message = create_system_message(
        conversation_id=conversation.id,
        content="候选已生成",
        message_type=MessageType.SCENE_CARD.value,
        payload={"scene_id": str(uuid4())},
        session=test_db_session,
    )

    assert message["message_type"] == "SCENE_CARD"
    assert len(received) == 1
    assert received[0].conversation_id == conversation.id
    assert received[0].message_id.hex == message["id"].replace("-", "")


def test_start_scene_validates_required_location_before_creating(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = _Actor()
    created_calls = 0

    monkeypatch.setattr(chat_dorm_dinner, "_ensure_conversation_member", lambda *args: object())
    monkeypatch.setattr(chat_dorm_dinner, "_current_instance", lambda *args: None)
    monkeypatch.setattr(chat_dorm_dinner, "_active_participants", lambda *args: [])

    def create(*_args: object, **_kwargs: object) -> dict[str, str]:
        nonlocal created_calls
        created_calls += 1
        return {"id": str(uuid4())}

    monkeypatch.setattr(chat_dorm_dinner, "create_scene_instance", create)

    with pytest.raises(ValueError, match="城市和校区/出发地点"):
        chat_dorm_dinner.start_scene(actor, uuid4(), _Session(), city="", origin="")  # type: ignore[arg-type]

    assert created_calls == 0


def test_start_scene_recovers_uninitialized_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = _Actor()
    instance = SceneInstance(
        definition_id=uuid4(),
        conversation_id=uuid4(),
        created_by=actor.id,
        status="DRAFT",
        current_phase="DRAFT",
        public_context_json=None,
    )
    create_calls = 0

    monkeypatch.setattr(chat_dorm_dinner, "_ensure_conversation_member", lambda *args: object())
    monkeypatch.setattr(chat_dorm_dinner, "_current_instance", lambda *args: instance)
    monkeypatch.setattr(chat_dorm_dinner, "_post_system_message", lambda *args, **kwargs: None)

    def create(*_args: object, **_kwargs: object) -> dict[str, str]:
        nonlocal create_calls
        create_calls += 1
        return {"id": str(uuid4())}

    monkeypatch.setattr(chat_dorm_dinner, "create_scene_instance", create)
    monkeypatch.setattr(
        chat_dorm_dinner,
        "_status",
        lambda current, *_args: {"status": current.status, "city": chat_dorm_dinner._public_context(current).get("city")},
    )

    result = chat_dorm_dinner.start_scene(
        actor, instance.conversation_id, _Session(), city="上海", origin="复旦大学"  # type: ignore[arg-type]
    )

    assert create_calls == 0
    assert result == {"status": "COLLECTING_PRIVATE_INPUT", "city": "上海"}


def test_status_exposes_uninitialized_draft_as_not_started(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = _Actor()
    instance = SceneInstance(
        definition_id=uuid4(),
        conversation_id=uuid4(),
        created_by=actor.id,
        status="DRAFT",
        current_phase="DRAFT",
        public_context_json=None,
    )
    definition = type("Definition", (), {"id": uuid4()})()
    monkeypatch.setattr(chat_dorm_dinner, "_ensure_conversation_member", lambda *args: object())
    monkeypatch.setattr(chat_dorm_dinner, "_current_instance", lambda *args: instance)
    monkeypatch.setattr(chat_dorm_dinner, "_dorm_definition", lambda *args: definition)
    monkeypatch.setattr(chat_dorm_dinner, "_active_participants", lambda *args: [])

    result = chat_dorm_dinner.get_status(actor, instance.conversation_id, _Session())  # type: ignore[arg-type]

    assert result["scene_id"] is None
    assert result["status"] == "NOT_STARTED"


def _create_chat_scene(
    test_db_session: Session,
    *,
    scene_status: str,
    phase: str,
) -> tuple[User, Conversation, SceneInstance, SceneCandidate]:
    actor = User(
        email=f"chat-scene-{scene_status.lower()}@example.com",
        password_hash="fake",
        display_name="Alice",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(actor)
    test_db_session.flush()
    conversation = Conversation(
        type=ConversationType.GROUP.value,
        title="Dorm chat",
        created_by=actor.id,
    )
    test_db_session.add(conversation)
    test_db_session.flush()
    test_db_session.add(
        ConversationParticipant(
            conversation_id=conversation.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=actor.id,
            role=ConversationRole.OWNER.value,
        )
    )
    definition = SceneDefinition(
        scene_key="dorm_dinner",
        version="1.0.0",
        name="宿舍聚餐",
        enabled=True,
    )
    test_db_session.add(definition)
    test_db_session.flush()
    instance = SceneInstance(
        definition_id=definition.id,
        conversation_id=conversation.id,
        created_by=actor.id,
        status=scene_status,
        current_phase=phase,
        public_context_json='{"city":"广州","origin":"暨南大学","topic":"宿舍聚餐"}',
    )
    test_db_session.add(instance)
    test_db_session.flush()
    candidate = SceneCandidate(
        scene_instance_id=instance.id,
        candidate_key="closed-candidate",
        display_name="已关闭候选",
        status="ACTIVE",
        rank=1,
    )
    test_db_session.add(candidate)
    test_db_session.commit()
    return actor, conversation, instance, candidate


def test_closed_vote_is_not_returned_as_current_chat_scene(test_db_session: Session) -> None:
    actor, conversation, _instance, _candidate = _create_chat_scene(
        test_db_session,
        scene_status="VOTING_CLOSED",
        phase="VOTING_CLOSED",
    )

    result = chat_dorm_dinner.get_status(actor, conversation.id, test_db_session)

    assert result["scene_id"] is None
    assert result["status"] == "NOT_STARTED"


def test_cannot_vote_after_chat_vote_is_closed(test_db_session: Session) -> None:
    actor, conversation, _instance, _candidate = _create_chat_scene(
        test_db_session,
        scene_status="VOTING_CLOSED",
        phase="VOTING_CLOSED",
    )

    with pytest.raises(NotFoundError):
        chat_dorm_dinner.vote(
            actor,
            conversation.id,
            test_db_session,
            candidate_key="closed-candidate",
        )
