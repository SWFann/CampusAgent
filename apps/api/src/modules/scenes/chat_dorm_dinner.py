"""Chat-native dorm dinner scene helpers.

This module provides a demo-ready vertical slice that binds the dorm dinner
scene to an existing conversation. It deliberately reuses the existing scene
tables so the workflow can ship without a new migration.

Privacy:
- Raw preferences are passed only to ``submit_private_preferences``.
- Chat messages contain public state/counts only.
- Debate text is public and generated from aggregate counts/candidates, not
  from named raw preferences.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...config import settings
from ...db.time import utc_now
from ...utils.errors import AuthorizationError, NotFoundError
from ..conversations.models import (
    Conversation,
    ConversationParticipant,
    MessageType,
)
from ..conversations.models import (
    ParticipantStatus as ConversationParticipantStatus,
)
from ..conversations.service import create_system_message
from ..users.models import User
from .dinner_search import DinnerSearchError, StepFunDinnerProvider
from .models import (
    ParticipantStatus,
    PrivateSubmission,
    SceneCandidate,
    SceneDefinition,
    SceneInstance,
    SceneParticipant,
    SceneResult,
    SceneVote,
    VoteValue,
)
from .service import create_scene_instance, submit_private_preferences
from .state_machine import TERMINAL_STATES, SceneState

CHAT_SCENE_CLOSED_STATUSES = {"VOTING_CLOSED"}


def _active_participants(conversation_id: UUID, session: Session) -> list[ConversationParticipant]:
    return (
        session.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.participant_type == "USER",
            ConversationParticipant.status == ConversationParticipantStatus.ACTIVE.value,
        )
        .all()
    )


def _ensure_conversation_member(actor: User, conversation_id: UUID, session: Session) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation")
    participant = (
        session.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.participant_user_id == actor.id,
            ConversationParticipant.status == ConversationParticipantStatus.ACTIVE.value,
        )
        .first()
    )
    if participant is None:
        raise AuthorizationError("你不是此会话成员")
    return conversation


def _dorm_definition(session: Session) -> SceneDefinition:
    definition = (
        session.query(SceneDefinition)
        .filter(SceneDefinition.scene_key == "dorm_dinner")
        .first()
    )
    if definition is not None:
        return definition
    definition = SceneDefinition(
        scene_key="dorm_dinner",
        version="1.0.0",
        name="宿舍聚餐",
        description="群聊内宿舍聚餐协商场景",
        enabled=True,
        capabilities_json=json.dumps({"chat_native": True}, ensure_ascii=False),
    )
    session.add(definition)
    session.commit()
    session.refresh(definition)
    return definition


def _current_instance(conversation_id: UUID, session: Session) -> SceneInstance | None:
    terminal_values = {state.value for state in TERMINAL_STATES} | CHAT_SCENE_CLOSED_STATUSES
    return (
        session.query(SceneInstance)
        .join(SceneDefinition, SceneInstance.definition_id == SceneDefinition.id)
        .filter(
            SceneDefinition.scene_key == "dorm_dinner",
            SceneInstance.conversation_id == conversation_id,
            SceneInstance.cancelled_at.is_(None),
            SceneInstance.status.notin_(terminal_values),
        )
        .order_by(SceneInstance.created_at.desc())
        .first()
    )


def _public_context(instance: SceneInstance) -> dict[str, Any]:
    if not instance.public_context_json:
        return {}
    try:
        parsed = json.loads(instance.public_context_json)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _save_public_context(instance: SceneInstance, context: dict[str, Any]) -> None:
    instance.public_context_json = json.dumps(context, ensure_ascii=False)


def _parse_budget_range(value: Any) -> tuple[float, float]:
    text = str(value or "").strip()
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    if len(numbers) >= 2:
        low, high = numbers[0], numbers[1]
    elif len(numbers) == 1:
        low, high = 0.0, numbers[0]
    else:
        low, high = 20.0, 60.0
    if high < low:
        low, high = high, low
    return low, high


def _normalise_preferences(payload: dict[str, Any]) -> dict[str, Any]:
    if {"budget_min", "budget_max", "cuisine_preferences", "available_time"} <= set(payload):
        return payload
    budget_min, budget_max = _parse_budget_range(
        payload.get("budget_range") or payload.get("budget")
    )
    raw_dietary = payload.get("dietary_restrictions") or []
    dietary_map = {
        "素食": "vegetarian",
        "清真": "halal",
        "不吃辣": "no_spicy",
        "无麸质": "gluten_free",
        "无": "none",
    }
    time_map = {
        "17:00": "early_dinner",
        "18:00": "dinner",
        "19:00": "dinner",
        "20:00": "late_dinner",
    }
    preferred_time = str(payload.get("preferred_time") or "")
    return {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "cuisine_preferences": payload.get("cuisine_preferences") or ["sichuan", "hotpot", "cantonese"],
        "dietary_restrictions": [dietary_map.get(str(item), str(item)) for item in raw_dietary] or ["none"],
        "distance_preference": payload.get("distance_preference") or "moderate",
        "available_time": payload.get("available_time") or [time_map.get(preferred_time, "dinner")],
        "environment_preference": payload.get("environment_preference") or "moderate",
        "notes": str(payload.get("notes") or ""),
    }


def _post_system_message(
    conversation_id: UUID,
    session: Session,
    *,
    content: str,
    message_type: str = MessageType.SYSTEM.value,
    payload: dict[str, Any] | None = None,
) -> None:
    create_system_message(
        conversation_id=conversation_id,
        content=content,
        message_type=message_type,
        payload=payload,
        session=session,
    )


def _candidate_read(candidate: SceneCandidate) -> dict[str, Any]:
    metadata = None
    if candidate.public_metadata_json:
        with_context = json.loads(candidate.public_metadata_json)
        metadata = with_context if isinstance(with_context, dict) else None
    return {
        "id": str(candidate.id),
        "candidate_key": candidate.candidate_key,
        "display_name": candidate.display_name,
        "public_metadata": metadata,
        "aggregate_score": candidate.aggregate_score or 0.0,
        "public_reason": candidate.public_reason,
        "rank": candidate.rank,
    }


def _ensure_participant_rows(instance: SceneInstance, session: Session) -> None:
    existing_user_ids = {
        p.user_id
        for p in session.query(SceneParticipant)
        .filter(SceneParticipant.scene_instance_id == instance.id)
        .all()
    }
    for participant in _active_participants(instance.conversation_id, session):  # type: ignore[arg-type]
        if participant.participant_user_id and participant.participant_user_id not in existing_user_ids:
            session.add(
                SceneParticipant(
                    scene_instance_id=instance.id,
                    user_id=participant.participant_user_id,
                    status=ParticipantStatus.INVITED.value,
                    is_creator=False,
                )
            )


def _status(instance: SceneInstance, actor: User, session: Session) -> dict[str, Any]:
    _ensure_participant_rows(instance, session)
    session.flush()
    participants = (
        session.query(SceneParticipant)
        .filter(SceneParticipant.scene_instance_id == instance.id)
        .all()
    )
    joined = [p for p in participants if p.status == ParticipantStatus.ACCEPTED.value]
    skipped = [p for p in participants if p.status == ParticipantStatus.DECLINED.value]
    submissions = (
        session.query(PrivateSubmission)
        .filter(
            PrivateSubmission.scene_instance_id == instance.id,
            PrivateSubmission.deleted_at.is_(None),
        )
        .all()
    )
    submitted_user_ids = {s.user_id for s in submissions}
    context = _public_context(instance)
    candidates = (
        session.query(SceneCandidate)
        .filter(SceneCandidate.scene_instance_id == instance.id)
        .order_by(SceneCandidate.rank.asc().nullslast())
        .all()
    )
    votes = (
        session.query(SceneVote)
        .filter(SceneVote.scene_instance_id == instance.id)
        .all()
    )
    result = (
        session.query(SceneResult)
        .filter(SceneResult.scene_instance_id == instance.id)
        .first()
    )
    return {
        "scene_id": str(instance.id),
        "conversation_id": str(instance.conversation_id),
        "phase": instance.current_phase,
        "status": instance.status,
        "scene_version": instance.version,
        "participant_count": len(participants),
        "joined_count": len(joined),
        "skipped_count": len(skipped),
        "submitted_count": len(submitted_user_ids & {p.user_id for p in joined}),
        "ready_for_debate": bool(joined) and all(p.user_id in submitted_user_ids for p in joined),
        "my_participation": next((p.status for p in participants if p.user_id == actor.id), None),
        "my_submitted": actor.id in submitted_user_ids,
        "max_rounds": int(context.get("max_rounds") or 3),
        "current_round": int(context.get("current_round") or 0),
        "debate_turns": context.get("debate_turns") or [],
        "negotiations": context.get("negotiations") or [],
        "city": context.get("city") or "",
        "origin": context.get("origin") or "",
        "topic": context.get("topic") or "宿舍聚餐",
        "vote_deadline": context.get("vote_deadline"),
        "public_error": context.get("public_error"),
        "next_negotiation_requests": int(context.get("next_negotiation_requests") or 0),
        "display_mode": context.get("display_mode") or "anonymous",
        "capabilities": {
            "can_manage": instance.created_by == actor.id,
            "can_start_debate": instance.created_by == actor.id,
            "can_close": instance.created_by == actor.id,
        },
        "candidates": [_candidate_read(c) for c in candidates],
        "votes": [
            {
                "candidate_id": str(v.candidate_id),
                "user_id": str(v.user_id),
                "vote_value": v.vote_value,
            }
            for v in votes
        ],
        "result": {
            "selected_candidate_id": str(result.selected_candidate_id) if result.selected_candidate_id else None,
            "public_summary": result.public_summary,
        } if result else None,
    }


def start_scene(
    actor: User,
    conversation_id: UUID,
    session: Session,
    *,
    max_rounds: int = 3,
    city: str = "",
    origin: str = "",
    topic: str = "宿舍聚餐",
    vote_deadline: str | None = None,
) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    city = city.strip()
    origin = origin.strip()
    if not city or not origin:
        raise ValueError("城市和校区/出发地点为必填项")

    existing = _current_instance(conversation_id, session)
    recoverable_draft = (
        existing is not None
        and existing.created_by == actor.id
        and existing.status == SceneState.DRAFT.value
        and not existing.public_context_json
    )
    if existing is not None and not recoverable_draft:
        return _status(existing, actor, session)

    instance = existing
    created_new = False
    if instance is None:
        participant_user_ids = [
            p.participant_user_id
            for p in _active_participants(conversation_id, session)
            if p.participant_user_id is not None
        ]
        created = create_scene_instance(
            actor,
            {
                "scene_key": "dorm_dinner",
                "conversation_id": conversation_id,
                "participant_user_ids": participant_user_ids,
            },
            session,
        )
        instance = session.get(SceneInstance, UUID(created["id"]))
        assert instance is not None
        created_new = True

    instance.status = SceneState.COLLECTING_PRIVATE_INPUT.value
    instance.current_phase = SceneState.COLLECTING_PRIVATE_INPUT.value
    _save_public_context(instance, {
        "max_rounds": max(1, min(max_rounds, 10)),
        "current_round": 0,
        "city": city[:80],
        "origin": origin[:160],
        "topic": topic.strip()[:120] or "宿舍聚餐",
        "vote_deadline": vote_deadline,
        "negotiations": [],
        "display_mode": "anonymous",
    })
    try:
        _post_system_message(
            conversation_id,
            session,
            content="已发起宿舍聚餐协商。请在场景卡片中选择参与或不参与。",
            message_type=MessageType.SCENE_CARD.value,
            payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id)},
        )
        session.commit()
    except Exception:
        session.rollback()
        if created_new:
            persisted = session.get(SceneInstance, instance.id)
            if persisted is not None:
                session.delete(persisted)
                session.commit()
        raise
    session.refresh(instance)
    return _status(instance, actor, session)


def get_status(actor: User, conversation_id: UUID, session: Session) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if (
        instance is not None
        and instance.created_by == actor.id
        and instance.status == SceneState.DRAFT.value
        and not instance.public_context_json
    ):
        # A previous failed initialization left a recoverable shell. Present
        # it as not started so the creator can submit the required fields and
        # let ``start_scene`` initialize the same row safely.
        instance = None
    if instance is None:
        definition = _dorm_definition(session)
        return {
            "scene_id": None,
            "conversation_id": str(conversation_id),
            "phase": "NOT_STARTED",
            "status": "NOT_STARTED",
            "participant_count": len(_active_participants(conversation_id, session)),
            "joined_count": 0,
            "skipped_count": 0,
            "submitted_count": 0,
            "ready_for_debate": False,
            "my_participation": None,
            "my_submitted": False,
            "max_rounds": 3,
            "current_round": 0,
            "debate_turns": [],
            "candidates": [],
            "votes": [],
            "result": None,
            "scene_version": 0,
            "city": "",
            "origin": "",
            "topic": "宿舍聚餐",
            "vote_deadline": None,
            "negotiations": [],
            "public_error": None,
            "next_negotiation_requests": 0,
            "display_mode": "anonymous",
            "capabilities": {"can_manage": False, "can_start_debate": False, "can_close": False},
            "definition_id": str(definition.id),
        }
    return _status(instance, actor, session)


def set_participation(
    actor: User,
    conversation_id: UUID,
    session: Session,
    *,
    participate: bool,
) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        start_scene(actor, conversation_id, session)
        instance = _current_instance(conversation_id, session)
    assert instance is not None
    participant = (
        session.query(SceneParticipant)
        .filter(SceneParticipant.scene_instance_id == instance.id, SceneParticipant.user_id == actor.id)
        .first()
    )
    if participant is None:
        participant = SceneParticipant(
            scene_instance_id=instance.id,
            user_id=actor.id,
            status=ParticipantStatus.INVITED.value,
            is_creator=False,
        )
        session.add(participant)
    participant.status = ParticipantStatus.ACCEPTED.value if participate else ParticipantStatus.DECLINED.value
    if participate:
        participant.joined_at = participant.joined_at or utc_now()
    _post_system_message(
        conversation_id,
        session,
        content=f"{actor.display_name} 已选择{'参与' if participate else '不参与'}宿舍聚餐协商。",
    )
    session.commit()
    session.refresh(instance)
    return _status(instance, actor, session)


def submit_preferences(
    actor: User,
    conversation_id: UUID,
    session: Session,
    preferences: dict[str, Any],
) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        start_scene(actor, conversation_id, session)
        instance = _current_instance(conversation_id, session)
    assert instance is not None
    participant = (
        session.query(SceneParticipant)
        .filter(SceneParticipant.scene_instance_id == instance.id, SceneParticipant.user_id == actor.id)
        .first()
    )
    if participant is None or participant.status != ParticipantStatus.ACCEPTED.value:
        set_participation(actor, conversation_id, session, participate=True)
        instance = _current_instance(conversation_id, session)
        assert instance is not None
    submit_private_preferences(actor, instance.id, _normalise_preferences(preferences), session)
    status = _status(instance, actor, session)
    _post_system_message(
        conversation_id,
        session,
        content=f"{actor.display_name} 已提交私密偏好。当前 {status['submitted_count']}/{status['joined_count']} 人已提交。",
        message_type=MessageType.SCENE_CARD.value,
        payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id)},
    )
    session.commit()
    return _status(instance, actor, session)


def run_debate(
    actor: User,
    conversation_id: UUID,
    session: Session,
    *,
    max_rounds: int = 3,
) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        start_scene(actor, conversation_id, session, max_rounds=max_rounds)
        instance = _current_instance(conversation_id, session)
    assert instance is not None
    if instance.created_by != actor.id:
        raise AuthorizationError("只有聚餐发起人可以启动智能体协商")
    status = _status(instance, actor, session)
    if not status["ready_for_debate"]:
        return status

    max_rounds = max(1, min(max_rounds, 10))
    context = _public_context(instance)
    if not settings.ENABLE_EXTERNAL_MODEL:
        context["public_error"] = "真实联网搜索尚未启用，请配置 StepFun API 后重试。"
        _save_public_context(instance, context)
        session.commit()
        return _status(instance, actor, session)

    submissions = (
        session.query(PrivateSubmission)
        .filter(
            PrivateSubmission.scene_instance_id == instance.id,
            PrivateSubmission.deleted_at.is_(None),
        )
        .all()
    )
    member_preferences: list[dict[str, Any]] = []
    for index, submission in enumerate(sorted(submissions, key=lambda item: str(item.user_id))):
        capsule: dict[str, Any] = {}
        if submission.capsule_json:
            parsed = json.loads(submission.capsule_json)
            capsule = parsed if isinstance(parsed, dict) else {}
        member_preferences.append({
            "agent_name": f"成员{chr(65 + index)} Agent",
            "preferences": capsule,
        })
    provider = StepFunDinnerProvider(
        base_url=settings.MODEL_GATEWAY_BASE_URL,
        model=settings.MODEL_GATEWAY_MODEL,
        api_key=settings.MODEL_GATEWAY_API_KEY,
        timeout_ms=settings.MODEL_GATEWAY_TIMEOUT_MS,
    )
    query = f"{context.get('city', '')} {context.get('origin', '')} 附近 {context.get('topic', '聚餐')} 餐厅 推荐 价格 地址 营业时间"
    try:
        evidence = provider.search(query, limit=6)
        negotiation = provider.negotiate(
            city=str(context.get("city") or ""),
            origin=str(context.get("origin") or ""),
            topic=str(context.get("topic") or "宿舍聚餐"),
            round_count=max_rounds,
            member_preferences=member_preferences,
            previous_memory=list(context.get("negotiations") or []),
            evidence=evidence,
        )
    except DinnerSearchError as exc:
        context["public_error"] = str(exc)
        _save_public_context(instance, context)
        session.commit()
        return _status(instance, actor, session)

    session.query(SceneCandidate).filter(
        SceneCandidate.scene_instance_id == instance.id
    ).delete(synchronize_session=False)
    turns = [
        {
            "round": turn.round,
            "speaker": turn.agent_name,
            "content": turn.position,
            "search_summary": turn.search_summary,
            "source_urls": turn.source_urls,
        }
        for turn in negotiation.agents
    ]
    turns.append({
        "round": max_rounds,
        "speaker": "聚餐协调Agent",
        "content": negotiation.coordinator_summary,
        "search_summary": "",
        "source_urls": [],
    })
    for turn in turns:
        _post_system_message(
            conversation_id,
            session,
            content=f"{turn['speaker']}：{turn['content']}",
            message_type=MessageType.AGENT_PUBLIC.value,
            payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id), "round": turn["round"]},
        )
    for rank, candidate in enumerate(negotiation.candidates, start=1):
        session.add(SceneCandidate(
            scene_instance_id=instance.id,
            candidate_key=candidate.candidate_key[:100],
            display_name=candidate.display_name[:200],
            public_metadata_json=json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False),
            aggregate_score=max(0.0, 1.0 - ((rank - 1) * 0.1)),
            public_reason=candidate.public_reason,
            status="ACTIVE",
            rank=rank,
        ))
    negotiations = list(context.get("negotiations") or [])
    negotiations.append({
        "number": len(negotiations) + 1,
        "round_count": max_rounds,
        "turns": turns,
        "coordinator_summary": negotiation.coordinator_summary,
        "source_count": len(evidence),
        "created_at": utc_now().isoformat(),
    })
    context.update({
        "max_rounds": max_rounds,
        "current_round": max_rounds,
        "debate_turns": turns,
        "negotiations": negotiations,
        "public_error": None,
    })
    _save_public_context(instance, context)
    instance.status = SceneState.VOTING.value
    instance.current_phase = SceneState.VOTING.value
    _post_system_message(
        conversation_id,
        session,
        content="宿舍聚餐候选方案已生成，请在场景卡片中投票。",
        message_type=MessageType.SCENE_CARD.value,
        payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id)},
    )
    session.commit()
    session.refresh(instance)
    return _status(instance, actor, session)


def close_vote(actor: User, conversation_id: UUID, session: Session) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        raise NotFoundError("Dorm dinner scene")
    if instance.created_by != actor.id:
        raise AuthorizationError("只有聚餐发起人可以关闭投票")
    instance.status = "VOTING_CLOSED"
    instance.current_phase = "VOTING_CLOSED"
    instance.version += 1
    _post_system_message(
        conversation_id,
        session,
        content="发起人已关闭宿舍聚餐投票。",
        message_type=MessageType.RESULT.value,
        payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id)},
    )
    return get_status(actor, conversation_id, session)


def end_scene(actor: User, conversation_id: UUID, session: Session) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        raise NotFoundError("Dorm dinner scene")
    if instance.created_by != actor.id:
        raise AuthorizationError("只有聚餐发起人可以结束聚餐")
    instance.status = SceneState.COMPLETED.value
    instance.current_phase = SceneState.COMPLETED.value
    instance.completed_at = utc_now()
    instance.version += 1
    _post_system_message(
        conversation_id,
        session,
        content="发起人已结束本次宿舍聚餐。",
        message_type=MessageType.RESULT.value,
        payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id)},
    )
    return get_status(actor, conversation_id, session)


def vote(
    actor: User,
    conversation_id: UUID,
    session: Session,
    *,
    candidate_key: str,
) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        raise NotFoundError("Dorm dinner scene")
    candidate = (
        session.query(SceneCandidate)
        .filter(
            SceneCandidate.scene_instance_id == instance.id,
            SceneCandidate.candidate_key == candidate_key,
        )
        .first()
    )
    if candidate is None:
        raise NotFoundError("Scene candidate")
    existing = (
        session.query(SceneVote)
        .filter(SceneVote.scene_instance_id == instance.id, SceneVote.user_id == actor.id)
        .first()
    )
    if existing is None:
        session.add(
            SceneVote(
                scene_instance_id=instance.id,
                user_id=actor.id,
                candidate_id=candidate.id,
                vote_value=VoteValue.APPROVE.value,
            )
        )
    else:
        existing.candidate_id = candidate.id
        existing.vote_value = VoteValue.APPROVE.value
    _post_system_message(
        conversation_id,
        session,
        content=f"{actor.display_name} 已完成投票。",
        message_type=MessageType.VOTE.value,
    )
    session.commit()
    return _status(instance, actor, session)


def request_next_negotiation(
    actor: User,
    conversation_id: UUID,
    session: Session,
) -> dict[str, Any]:
    _ensure_conversation_member(actor, conversation_id, session)
    instance = _current_instance(conversation_id, session)
    if instance is None:
        raise NotFoundError("Dorm dinner scene")
    participant = (
        session.query(SceneParticipant)
        .filter(
            SceneParticipant.scene_instance_id == instance.id,
            SceneParticipant.user_id == actor.id,
            SceneParticipant.status == ParticipantStatus.ACCEPTED.value,
        )
        .first()
    )
    if participant is None:
        raise AuthorizationError("只有参与协商的成员可以请求下一次协商")
    context = _public_context(instance)
    requesters = set(context.get("next_negotiation_requesters") or [])
    requester_token = hashlib.sha256(f"{instance.id}:{actor.id}".encode()).hexdigest()
    requesters.add(requester_token)
    context["next_negotiation_requesters"] = sorted(requesters)
    context["next_negotiation_requests"] = len(requesters)
    _save_public_context(instance, context)
    instance.current_phase = "DISAGREEMENT"
    instance.version += 1
    _post_system_message(
        conversation_id,
        session,
        content=f"有成员不同意当前候选，已请求下一次智能体协商（{len(requesters)} 人）。",
        message_type=MessageType.VOTE.value,
        payload={"scene_key": "dorm_dinner", "scene_id": str(instance.id)},
    )
    return _status(instance, actor, session)
