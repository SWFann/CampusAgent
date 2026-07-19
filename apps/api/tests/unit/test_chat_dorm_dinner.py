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
from src.modules.scenes.dinner_search import (
    AgentRestaurantProposal,
    DebateOpening,
    DebateRound,
    DebateTurn,
    DinnerCandidate,
    NegotiationResult,
    SearchEvidence,
)
from src.modules.scenes.models import (
    ParticipantStatus as SceneParticipantStatus,
)
from src.modules.scenes.models import (
    PrivateSubmission,
    SceneCandidate,
    SceneDefinition,
    SceneInstance,
    SceneParticipant,
)
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


def test_run_debate_publishes_hosted_multi_agent_transcript(
    monkeypatch: pytest.MonkeyPatch,
    test_db_session: Session,
) -> None:
    actor, conversation, instance, _candidate = _create_chat_scene(
        test_db_session,
        scene_status="COLLECTING_PRIVATE_INPUT",
        phase="COLLECTING_PRIVATE_INPUT",
    )
    bob = User(
        email="chat-debate-bob@example.com",
        password_hash="fake",
        display_name="Bob",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(bob)
    test_db_session.flush()
    test_db_session.add(
        ConversationParticipant(
            conversation_id=conversation.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=bob.id,
            role=ConversationRole.MEMBER.value,
        )
    )
    test_db_session.add_all(
        [
            SceneParticipant(
                scene_instance_id=instance.id,
                user_id=actor.id,
                status=SceneParticipantStatus.ACCEPTED.value,
                is_creator=True,
            ),
            SceneParticipant(
                scene_instance_id=instance.id,
                user_id=bob.id,
                status=SceneParticipantStatus.ACCEPTED.value,
                is_creator=False,
            ),
            PrivateSubmission(
                scene_instance_id=instance.id,
                user_id=actor.id,
                encrypted_payload="encrypted",
                capsule_json='{"notes":"想吃川菜","budget_max":60}',
            ),
            PrivateSubmission(
                scene_instance_id=instance.id,
                user_id=bob.id,
                encrypted_payload="encrypted",
                capsule_json='{"notes":"希望离宿舍近","budget_max":60}',
            ),
        ]
    )
    test_db_session.commit()
    monkeypatch.setattr(chat_dorm_dinner.settings, "ENABLE_EXTERNAL_MODEL", True)

    evidence = SearchEvidence(
        title="校外川菜馆",
        url="https://example.com/sichuan",
        snippet="适合聚餐",
        retrieved_at=chat_dorm_dinner.utc_now(),
    )

    class Provider:
        searches: list[str] = []

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def search(self, query: str, limit: int = 10) -> list[SearchEvidence]:
            self.searches.append(query)
            return [evidence]

        def negotiate(self, **_kwargs: object) -> NegotiationResult:
            candidate = DinnerCandidate(
                candidate_key="sichuan",
                display_name="校外川菜馆",
                address="学校西门外",
                price_hint="人均 55 元",
                business_hours_hint="晚餐营业",
                public_reason="预算匹配，适合多人聚餐。",
                source_urls=["https://example.com/sichuan"],
                sources=[evidence],
            )
            return NegotiationResult(
                opening=DebateOpening(speaker="主持人Agent", content="欢迎进入宿舍聚餐辩论。"),
                agent_proposals=[
                    AgentRestaurantProposal(
                        agent_name="Alice Agent",
                        preference_summary="想吃川菜，预算 60 内。",
                        proposals=[candidate],
                    )
                ],
                rounds=[
                    DebateRound(
                        round=1,
                        turns=[
                            DebateTurn(
                                agent_name="Alice Agent",
                                position="我支持校外川菜馆，因为预算和聚餐氛围都匹配。",
                                stance="support",
                                target_candidate_keys=["sichuan"],
                                source_urls=["https://example.com/sichuan"],
                            ),
                            DebateTurn(
                                agent_name="Bob Agent",
                                position="我认可预算，但提醒要确认距离。",
                                stance="challenge",
                                target_candidate_keys=["sichuan"],
                                source_urls=["https://example.com/sichuan"],
                            ),
                        ],
                        host_summary="本轮保留校外川菜馆，距离需确认。",
                    )
                ],
                agents=[],
                coordinator_summary="最终协调Agent建议把校外川菜馆放入投票。",
                candidates=[candidate],
            )

    monkeypatch.setattr(chat_dorm_dinner, "StepFunDinnerProvider", Provider)

    result = chat_dorm_dinner.run_debate(actor, conversation.id, test_db_session, max_rounds=2)

    phases = [turn["phase"] for turn in result["debate_turns"]]
    assert phases == ["opening", "proposal", "debate", "debate", "host_summary", "coordinator_summary"]
    assert result["debate_turns"][1]["proposals"][0]["display_name"] == "校外川菜馆"
    assert result["debate_turns"][-1]["speaker"] == "最终协调Agent"
    assert len(Provider.searches) >= 2
    assert any("校外" in query or "周边" in query for query in Provider.searches)

    messages = [
        message.content
        for message in conversation.messages
        if message.message_type == MessageType.AGENT_PUBLIC.value
    ]
    assert any(content == "主持人Agent：欢迎进入宿舍聚餐辩论。" for content in messages)
    assert any("Alice Agent 提案" in str(content) for content in messages)
    assert any("Bob Agent：我认可预算" in str(content) for content in messages)
    assert any("最终协调Agent：最终协调Agent建议" in str(content) for content in messages)


def test_search_debate_evidence_filters_non_restaurant_pages() -> None:
    now = chat_dorm_dinner.utc_now()

    class Provider:
        def search(self, query: str, limit: int = 10) -> list[SearchEvidence]:
            return [
                SearchEvidence(
                    title="全景中的大学之最",
                    url=f"https://example.com/campus-{query[-1]}",
                    snippet="介绍大学校园风景",
                    retrieved_at=now,
                ),
                SearchEvidence(
                    title="学校附近火锅店",
                    url="https://example.com/hotpot",
                    snippet="人均 58 元，适合学生聚餐，晚餐营业",
                    retrieved_at=now,
                ),
            ]

    evidence = chat_dorm_dinner._search_debate_evidence(Provider(), ["query1", "query2"])  # type: ignore[arg-type]

    assert [item.title for item in evidence] == ["学校附近火锅店"]
