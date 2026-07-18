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

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.dependencies import get_current_user
from ..users.models import User
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

router = APIRouter(prefix="/api/v1/scenes", tags=["scenes"])


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
