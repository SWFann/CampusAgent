"""Scene API routes.

Endpoints (aligned with API_CONTRACT.md):
- GET    /api/v1/scenes                      List available scene definitions
- POST   /api/v1/scenes                      Create a scene instance
- GET    /api/v1/scenes/mine                  List my scene instances
- GET    /api/v1/scenes/{instanceId}          Get scene instance details
- POST   /api/v1/scenes/{instanceId}/transition  Transition scene state
- POST   /api/v1/scenes/{instanceId}/accept   Accept invitation
- POST   /api/v1/scenes/{instanceId}/decline  Decline invitation
- POST   /api/v1/scenes/{instanceId}/leave    Leave scene
- GET    /api/v1/scenes/{instanceId}/participants  List participants
- POST   /api/v1/scenes/{instanceId}/submissions   Submit private preferences
- GET    /api/v1/scenes/{instanceId}/submissions/status  Get submission status
- DELETE /api/v1/scenes/{instanceId}/submissions   Delete submission
- GET    /api/v1/scenes/{instanceId}/candidates     List candidates
- POST   /api/v1/scenes/{instanceId}/votes          Cast a vote
- GET    /api/v1/scenes/{instanceId}/result         Get scene result

Privacy:
- Submission responses never echo the raw payload.
- All endpoints require authentication (get_current_user).
- Only participants can access scene details.
"""
from __future__ import annotations

import json
import re
from contextlib import suppress
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user
from ..users.models import User
from . import chat_dorm_dinner
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
from .schemas import (
    PrivateSubmissionCreate,
    SceneInstanceCreate,
    StateTransitionRequest,
    VoteCreate,
)
from .service import (
    accept_invitation,
    cast_vote,
    create_scene_instance,
    decline_invitation,
    delete_submission,
    get_scene_instance,
    get_scene_result,
    get_submission_status,
    leave_scene,
    list_candidates,
    list_my_scenes,
    list_participants,
    list_scene_definitions,
    submit_private_preferences,
    transition_state,
)
from .state_machine import SceneState

router = APIRouter(prefix="/api/v1/scenes", tags=["scenes"])


@router.post("/conversations/{conversation_id}/dorm_dinner", status_code=status.HTTP_201_CREATED)
async def start_chat_dorm_dinner(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    payload = await request.json()
    data = chat_dorm_dinner.start_scene(
        current_user,
        conversation_id,
        db_session,
        max_rounds=int(payload.get("max_rounds") or 3),
        city=str(payload.get("city") or ""),
        origin=str(payload.get("origin") or ""),
        topic=str(payload.get("topic") or "宿舍聚餐"),
        vote_deadline=str(payload.get("vote_deadline")) if payload.get("vote_deadline") else None,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/conversations/{conversation_id}/dorm_dinner", status_code=status.HTTP_200_OK)
def get_chat_dorm_dinner(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    data = chat_dorm_dinner.get_status(current_user, conversation_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/participation", status_code=status.HTTP_200_OK)
async def set_chat_dorm_dinner_participation(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    payload = await request.json()
    data = chat_dorm_dinner.set_participation(
        current_user,
        conversation_id,
        db_session,
        participate=bool(payload.get("participate")),
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/preferences", status_code=status.HTTP_201_CREATED)
async def submit_chat_dorm_dinner_preferences(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    payload = await request.json()
    preferences = payload.get("preferences") if isinstance(payload.get("preferences"), dict) else payload
    data = chat_dorm_dinner.submit_preferences(
        current_user,
        conversation_id,
        db_session,
        preferences=preferences,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/debate/start", status_code=status.HTTP_200_OK)
async def start_chat_dorm_dinner_debate(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    payload = await request.json()
    data = chat_dorm_dinner.run_debate(
        current_user,
        conversation_id,
        db_session,
        max_rounds=int(payload.get("max_rounds") or 3),
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/votes", status_code=status.HTTP_201_CREATED)
async def vote_chat_dorm_dinner(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    payload = await request.json()
    data = chat_dorm_dinner.vote(
        current_user,
        conversation_id,
        db_session,
        candidate_key=str(payload.get("candidate_key") or ""),
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/next-negotiation", status_code=status.HTTP_200_OK)
def request_next_chat_dorm_dinner_negotiation(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    data = chat_dorm_dinner.request_next_negotiation(
        current_user, conversation_id, db_session
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/votes/close", status_code=status.HTTP_200_OK)
def close_chat_dorm_dinner_vote(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    data = chat_dorm_dinner.close_vote(current_user, conversation_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/conversations/{conversation_id}/dorm_dinner/end", status_code=status.HTTP_200_OK)
def end_chat_dorm_dinner(
    conversation_id: UUID,
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    data = chat_dorm_dinner.end_scene(current_user, conversation_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


def _ensure_dorm_dinner_registered() -> None:
    from .plugins import DormDinnerPlugin
    from .registry import get_scene_registry

    with suppress(Exception):
        get_scene_registry().register(DormDinnerPlugin())


def _latest_dorm_dinner_instance(user: User, session: Session) -> SceneInstance | None:
    return (
        session.query(SceneInstance)
        .join(SceneDefinition, SceneInstance.definition_id == SceneDefinition.id)
        .join(SceneParticipant, SceneParticipant.scene_instance_id == SceneInstance.id)
        .filter(
            SceneDefinition.scene_key == "dorm_dinner",
            SceneParticipant.user_id == user.id,
        )
        .order_by(SceneInstance.created_at.desc())
        .first()
    )


def _open_dorm_dinner_instance(user: User, session: Session) -> SceneInstance:
    _ensure_dorm_dinner_registered()
    instance = _latest_dorm_dinner_instance(user, session)
    if instance is not None:
        return instance

    created = create_scene_instance(
        user,
        {
            "scene_key": "dorm_dinner",
            "participant_user_ids": [user.id],
            "idempotency_key": f"dorm-dinner-demo-{user.id}",
        },
        session,
    )
    instance_id = UUID(created["id"])
    transition_state(user, instance_id, "publish", session)
    transition_state(user, instance_id, "start_collecting", session)

    fresh = session.get(SceneInstance, instance_id)
    assert fresh is not None
    return fresh


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


def _normalise_dinner_preferences(payload: dict[str, Any]) -> dict[str, Any]:
    budget_min, budget_max = _parse_budget_range(
        payload.get("budget_range") or payload.get("budget")
    )
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
    raw_dietary = payload.get("dietary_restrictions") or []
    dietary = [dietary_map.get(str(item), str(item)) for item in raw_dietary]
    preferred_time = str(payload.get("preferred_time") or "")
    time_slot = time_map.get(preferred_time, "dinner")
    return {
        "budget_min": budget_min,
        "budget_max": budget_max,
        "cuisine_preferences": ["sichuan", "hotpot", "cantonese"],
        "dietary_restrictions": dietary or ["none"],
        "distance_preference": "moderate",
        "available_time": [time_slot],
        "environment_preference": "moderate",
        "notes": "",
    }


def _candidate_to_demo_read(candidate: SceneCandidate) -> dict[str, Any]:
    return {
        "id": str(candidate.id),
        "candidate_key": candidate.candidate_key,
        "display_name": candidate.display_name,
        "public_metadata": (
            json.loads(candidate.public_metadata_json)
            if candidate.public_metadata_json else None
        ),
        "aggregate_score": candidate.aggregate_score or 0.0,
        "public_reason": candidate.public_reason,
        "public_reasons": [candidate.public_reason] if candidate.public_reason else [],
        "status": candidate.status,
        "rank": candidate.rank,
    }


def _submission_to_demo_read(submission: PrivateSubmission) -> dict[str, Any]:
    return {
        "id": str(submission.id),
        "scene_key": "dorm_dinner",
        "submitted_at": submission.updated_at.isoformat()
        if submission.updated_at else submission.created_at.isoformat(),
        "status": "已提交",
    }


def _ensure_demo_candidates(instance: SceneInstance, session: Session) -> list[SceneCandidate]:
    candidates = (
        session.query(SceneCandidate)
        .filter(SceneCandidate.scene_instance_id == instance.id)
        .order_by(SceneCandidate.rank.asc().nullslast(), SceneCandidate.aggregate_score.desc())
        .all()
    )
    if candidates:
        return candidates
    demo_candidates = [
        SceneCandidate(
            scene_instance_id=instance.id,
            candidate_key="shu-xiang-ju",
            display_name="蜀香居",
            aggregate_score=0.92,
            public_reason="预算适中，口味覆盖面较广，适合宿舍聚餐。",
            status="ACTIVE",
            rank=1,
        ),
        SceneCandidate(
            scene_instance_id=instance.id,
            candidate_key="yue-wei-xuan",
            display_name="粤味轩",
            aggregate_score=0.84,
            public_reason="环境安静，菜品清淡，适合需要低刺激饮食的同学。",
            status="ACTIVE",
            rank=2,
        ),
        SceneCandidate(
            scene_instance_id=instance.id,
            candidate_key="xiao-huo-guo",
            display_name="小火锅集合店",
            aggregate_score=0.78,
            public_reason="选择灵活，时间安排方便，但预算略高。",
            status="ACTIVE",
            rank=3,
        ),
    ]
    session.add_all(demo_candidates)
    session.commit()
    return demo_candidates


@router.get("/dorm_dinner/status", status_code=status.HTTP_200_OK)
def get_dorm_dinner_status(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Demo-friendly status endpoint for the dorm dinner page."""
    instance = _open_dorm_dinner_instance(current_user, db_session)
    participant_count = (
        db_session.query(SceneParticipant)
        .filter(
            SceneParticipant.scene_instance_id == instance.id,
            SceneParticipant.status == ParticipantStatus.ACCEPTED.value,
        )
        .count()
    )
    submission = (
        db_session.query(PrivateSubmission)
        .filter(
            PrivateSubmission.scene_instance_id == instance.id,
            PrivateSubmission.user_id == current_user.id,
            PrivateSubmission.deleted_at.is_(None),
        )
        .first()
    )
    return success(data={
        "id": str(instance.id),
        "status": instance.status,
        "participant_count": participant_count,
        "has_submitted": submission is not None,
    })


@router.get("/dorm_dinner/preferences", status_code=status.HTTP_200_OK)
def list_dorm_dinner_preferences(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _latest_dorm_dinner_instance(current_user, db_session)
    if instance is None:
        return success(data=[])
    submissions = (
        db_session.query(PrivateSubmission)
        .filter(
            PrivateSubmission.scene_instance_id == instance.id,
            PrivateSubmission.user_id == current_user.id,
            PrivateSubmission.deleted_at.is_(None),
        )
        .order_by(PrivateSubmission.updated_at.desc())
        .all()
    )
    return success(data=[_submission_to_demo_read(s) for s in submissions])


@router.post("/dorm_dinner/preferences", status_code=status.HTTP_201_CREATED)
async def submit_dorm_dinner_preferences(
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _open_dorm_dinner_instance(current_user, db_session)
    if instance.status != SceneState.COLLECTING_PRIVATE_INPUT.value:
        return success(data={
            "submission_status": "ALREADY_CLOSED",
            "capsule_generated": False,
            "expires_at": None,
            "submission_id": None,
        })
    payload = await request.json()
    result = submit_private_preferences(
        current_user,
        instance.id,
        _normalise_dinner_preferences(payload),
        db_session,
    )
    return success(
        data=result,
        request_id=getattr(request.state, "correlation_id", None),
    )


@router.delete("/dorm_dinner/preferences/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dorm_dinner_preference(
    submission_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    submission = db_session.get(PrivateSubmission, submission_id)
    if submission is None or submission.user_id != current_user.id:
        return None
    submission.deleted_at = utc_now()
    db_session.commit()
    return None


@router.get("/dorm_dinner/candidates", status_code=status.HTTP_200_OK)
def list_dorm_dinner_candidates(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _open_dorm_dinner_instance(current_user, db_session)
    candidates = _ensure_demo_candidates(instance, db_session)
    return success(data=[_candidate_to_demo_read(c) for c in candidates])


@router.get("/dorm_dinner/votes", status_code=status.HTTP_200_OK)
def list_dorm_dinner_votes(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _open_dorm_dinner_instance(current_user, db_session)
    candidates = _ensure_demo_candidates(instance, db_session)
    votes = {
        str(v.candidate_id)
        for v in db_session.query(SceneVote).filter(
            SceneVote.scene_instance_id == instance.id,
            SceneVote.user_id == current_user.id,
        )
    }
    return success(data=[
        {
            "candidate_key": c.candidate_key,
            "has_voted": str(c.id) in votes,
        }
        for c in candidates
    ])


@router.post("/dorm_dinner/votes", status_code=status.HTTP_201_CREATED)
async def create_dorm_dinner_vote(
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _open_dorm_dinner_instance(current_user, db_session)
    payload = await request.json()
    candidate_key = str(payload.get("candidate_key") or "")
    candidates = _ensure_demo_candidates(instance, db_session)
    candidate = next((c for c in candidates if c.candidate_key == candidate_key), None)
    if candidate is None:
        return success(data={"vote_status": "IGNORED"})
    existing = (
        db_session.query(SceneVote)
        .filter(SceneVote.scene_instance_id == instance.id, SceneVote.user_id == current_user.id)
        .first()
    )
    if existing is None:
        existing = SceneVote(
            scene_instance_id=instance.id,
            user_id=current_user.id,
            candidate_id=candidate.id,
            vote_value=VoteValue.APPROVE.value,
        )
        db_session.add(existing)
    else:
        existing.candidate_id = candidate.id
        existing.vote_value = VoteValue.APPROVE.value
    db_session.commit()
    return success(data={"candidate_key": candidate_key, "has_voted": True})


@router.delete("/dorm_dinner/votes/{candidate_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dorm_dinner_vote(
    candidate_key: str,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    instance = _latest_dorm_dinner_instance(current_user, db_session)
    if instance is None:
        return None
    candidates = _ensure_demo_candidates(instance, db_session)
    candidate = next((c for c in candidates if c.candidate_key == candidate_key), None)
    if candidate is None:
        return None
    vote = (
        db_session.query(SceneVote)
        .filter(
            SceneVote.scene_instance_id == instance.id,
            SceneVote.user_id == current_user.id,
            SceneVote.candidate_id == candidate.id,
        )
        .first()
    )
    if vote is not None:
        db_session.delete(vote)
        db_session.commit()
    return None


@router.get("/dorm_dinner/confirmation", status_code=status.HTTP_200_OK)
def get_dorm_dinner_confirmation(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _latest_dorm_dinner_instance(current_user, db_session)
    if instance is None:
        return success(data={"confirmed": False})
    result = (
        db_session.query(SceneResult)
        .filter(SceneResult.scene_instance_id == instance.id)
        .first()
    )
    if result is None or result.selected_candidate_id is None:
        return success(data={"confirmed": False})
    candidate = db_session.get(SceneCandidate, result.selected_candidate_id)
    return success(data={
        "confirmed": True,
        "confirmed_candidate": candidate.display_name if candidate else None,
    })


@router.post("/dorm_dinner/confirmation", status_code=status.HTTP_200_OK)
async def confirm_dorm_dinner(
    request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    instance = _open_dorm_dinner_instance(current_user, db_session)
    payload = await request.json()
    candidate_key = str(payload.get("candidate_key") or "")
    candidate = next(
        (c for c in _ensure_demo_candidates(instance, db_session) if c.candidate_key == candidate_key),
        None,
    )
    if candidate is None:
        return success(data={"confirmed": False})
    result = (
        db_session.query(SceneResult)
        .filter(SceneResult.scene_instance_id == instance.id)
        .first()
    )
    if result is None:
        result = SceneResult(
            scene_instance_id=instance.id,
            selected_candidate_id=candidate.id,
            public_summary=f"已确认方案：{candidate.display_name}",
            participant_count=1,
            submitted_count=1,
        )
        db_session.add(result)
    else:
        result.selected_candidate_id = candidate.id
        result.public_summary = f"已确认方案：{candidate.display_name}"
    db_session.commit()
    return success(data={"confirmed": True, "confirmed_candidate": candidate.display_name})


# ---------------------------------------------------------------------------
# Scene definitions
# ---------------------------------------------------------------------------


@router.get("", status_code=status.HTTP_200_OK)
def list_scenes(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all available (enabled) scene definitions."""
    result = list_scene_definitions(db_session)
    return success(data=result)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_scene(
    body: SceneInstanceCreate,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new scene instance."""
    data = body.model_dump(mode="json")
    result = create_scene_instance(current_user, data, db_session)
    return success(
        data=result,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


@router.get("/mine", status_code=status.HTTP_200_OK)
def list_my_scene_instances(
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List scene instances created by the current user."""
    result = list_my_scenes(current_user, db_session)
    return success(data=result)


# ---------------------------------------------------------------------------
# Scene instance detail and transitions
# ---------------------------------------------------------------------------


@router.get("/{instance_id}", status_code=status.HTTP_200_OK)
def get_scene(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a scene instance by ID."""
    result = get_scene_instance(current_user, instance_id, db_session)
    return success(data=result)


@router.post("/{instance_id}/transition", status_code=status.HTTP_200_OK)
def transition_scene(
    instance_id: UUID,
    body: StateTransitionRequest,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Transition a scene instance to the next state."""
    result = transition_state(
        current_user,
        instance_id,
        body.action,
        db_session,
        idempotency_key=body.idempotency_key,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


# ---------------------------------------------------------------------------
# Participant management
# ---------------------------------------------------------------------------


@router.post("/{instance_id}/accept", status_code=status.HTTP_200_OK)
def accept_scene_invitation(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Accept an invitation to join a scene."""
    result = accept_invitation(current_user, instance_id, db_session)
    return success(data=result)


@router.post("/{instance_id}/decline", status_code=status.HTTP_200_OK)
def decline_scene_invitation(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Decline an invitation to join a scene."""
    result = decline_invitation(current_user, instance_id, db_session)
    return success(data=result)


@router.post("/{instance_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_scene_instance(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Leave a scene instance."""
    leave_scene(current_user, instance_id, db_session)


@router.get("/{instance_id}/participants", status_code=status.HTTP_200_OK)
def get_participants(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List participants in a scene instance."""
    result = list_participants(current_user, instance_id, db_session)
    return success(data=result)


# ---------------------------------------------------------------------------
# Private submissions
# ---------------------------------------------------------------------------


@router.post("/{instance_id}/submissions", status_code=status.HTTP_201_CREATED)
def create_submission(
    instance_id: UUID,
    body: PrivateSubmissionCreate,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Submit private preferences for a scene.

    The response NEVER echoes the raw payload — only a submission ID
    and status are returned.
    """
    result = submit_private_preferences(
        current_user,
        instance_id,
        body.preferences,
        db_session,
        save_to_long_term_memory=body.save_to_long_term_memory,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


@router.get("/{instance_id}/submissions/status", status_code=status.HTTP_200_OK)
def get_my_submission_status(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the status of the current user's submission — no raw content."""
    result = get_submission_status(current_user, instance_id, db_session)
    return success(data=result)


@router.delete("/{instance_id}/submissions", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_submission(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete the current user's private submission."""
    delete_submission(current_user, instance_id, db_session)


# ---------------------------------------------------------------------------
# Candidates and voting
# ---------------------------------------------------------------------------


@router.get("/{instance_id}/candidates", status_code=status.HTTP_200_OK)
def get_candidates(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List public candidates for a scene instance."""
    result = list_candidates(current_user, instance_id, db_session)
    return success(data=result)


@router.post("/{instance_id}/votes", status_code=status.HTTP_201_CREATED)
def create_vote(
    instance_id: UUID,
    body: VoteCreate,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Cast or replace a vote (one-person-one-vote)."""
    result = cast_vote(
        current_user,
        instance_id,
        body.candidate_id,
        body.vote_value,
        db_session,
        idempotency_key=body.idempotency_key,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@router.get("/{instance_id}/result", status_code=status.HTTP_200_OK)
def get_scene_result_endpoint(
    instance_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the public result of a completed scene."""
    result = get_scene_result(current_user, instance_id, db_session)
    return success(data=result)
