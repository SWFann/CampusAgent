from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from src.events.bus import DomainEvent, default_event_bus
from src.modules.conversations.events import MessageCreated
from src.modules.conversations.models import Conversation, ConversationType, MessageType
from src.modules.conversations.service import create_system_message


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
