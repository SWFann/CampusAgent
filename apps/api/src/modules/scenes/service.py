"""Scene service — core business logic for scene lifecycle.

Responsibilities:
- Create scene instances (idempotent).
- Manage state transitions (via SceneStateMachine).
- Manage participants (invite, accept, decline, leave).
- Handle private submissions (encrypt, store, validate).
- Handle voting (one-person-one-vote, idempotent).
- Publish domain events (public-safe, no private data).

Privacy:
- Private submissions are encrypted before storage; plaintext is never
  persisted, logged, or returned in API responses.
- The response (PrivateSubmissionResponse) never echoes the raw payload.
- Only the owner can submit/replace/delete their own submission.
- Admin cannot read submission content.
- Events only contain counts and IDs — never private data.
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...events.bus import default_event_bus
from ..audit.service import log_audit
from ..organizations.repository import OrganizationMembershipRepository, OrganizationRepository
from ..users.models import User
from .events import (
    SceneCancelled,
    SceneCompleted,
    SceneExpired,
    SceneFailed,
    SceneInstanceCreated,
    ScenePhaseChanged,
)
from .exceptions import (
    SceneConsentRequiredError,
    SceneNotFoundError,
    ScenePermissionDeniedError,
    SceneStateTransitionError,
    SceneSubmissionError,
)
from .models import (
    ParticipantStatus,
    PrivateSubmission,
    SceneCandidate,
    SceneDefinition,
    SceneInstance,
    SceneParticipant,
    SceneVote,
    VoteValue,
)
from .privacy import (
    capsule_to_json,
    encrypt_payload,
    hash_payload,
    validate_capsule,
)
from .registry import get_scene_registry
from .repository import (
    PrivateSubmissionRepository,
    SceneCandidateRepository,
    SceneDefinitionRepository,
    SceneInstanceRepository,
    SceneParticipantRepository,
    SceneResultRepository,
    SceneVoteRepository,
)
from .schemas import PrivateSubmissionResponse
from .state_machine import SceneState, SceneStateMachine

logger = logging.getLogger("campus_agent.scenes.service")

# Default expiry for private submissions (24 hours).
_DEFAULT_SUBMISSION_EXPIRY = timedelta(hours=24)


def _generate_event_id() -> str:
    return secrets.token_hex(16)


def _parse_context(json_str: str | None) -> dict[str, Any] | None:
    if json_str is None:
        return None
    try:
        return cast("dict[str, Any]", json.loads(json_str))
    except (json.JSONDecodeError, TypeError):
        return None


def _ensure_aware(dt: Any) -> Any:
    """Ensure a datetime is timezone-aware (assume UTC if naive)."""
    from datetime import UTC, datetime

    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# ---------------------------------------------------------------------------
# Scene Definition management
# ---------------------------------------------------------------------------


def list_scene_definitions(session: Session) -> dict[str, Any]:
    """List all enabled scene definitions."""
    repo = SceneDefinitionRepository(session)
    definitions = repo.list_enabled()
    return {
        "scenes": [_definition_to_read(d) for d in definitions],
        "total": len(definitions),
    }


def _definition_to_read(defn: SceneDefinition) -> dict[str, Any]:
    return {
        "id": str(defn.id),
        "scene_key": defn.scene_key,
        "version": defn.version,
        "name": defn.name,
        "description": defn.description,
        "enabled": defn.enabled,
        "capabilities": _parse_context(defn.capabilities_json),
        "created_at": defn.created_at.isoformat() if defn.created_at else None,
    }


# ---------------------------------------------------------------------------
# Scene Instance management
# ---------------------------------------------------------------------------


def create_scene_instance(
    user: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Create a new scene instance.

    Args:
        user: The creating user (becomes the creator participant).
        data: SceneInstanceCreate fields.
        session: DB session.

    Returns:
        Scene instance read dict.

    Raises:
        SceneNotFoundError: If the scene_key is not registered/enabled.
        SceneAlreadyExistsError: If idempotency_key already exists.
    """
    scene_key = data["scene_key"]
    registry = get_scene_registry()

    # Check that the plugin is registered and enabled.
    if not registry.is_enabled(scene_key):
        raise SceneNotFoundError(
            details={"scene_key": scene_key, "reason": "not_registered_or_disabled"}
        )

    # Idempotency check.
    idempotency_key = data.get("idempotency_key")
    if idempotency_key:
        instance_repo = SceneInstanceRepository(session)
        existing = instance_repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return _instance_to_read(existing, session, viewer_user_id=user.id)

    # Get or create the SceneDefinition row.
    defn_repo = SceneDefinitionRepository(session)
    plugin = registry.get(scene_key)
    definition = defn_repo.get_by_key(scene_key, plugin.version)
    if definition is None:
        definition = SceneDefinition(
            scene_key=scene_key,
            version=plugin.version,
            name=plugin.name,
            description=plugin.description,
            enabled=True,
        )
        defn_repo.create(definition)

    organization_id_raw = data.get("organization_id")
    organization_id = UUID(str(organization_id_raw)) if organization_id_raw else None
    participant_user_ids = [UUID(str(uid)) for uid in data.get("participant_user_ids", [])]
    if organization_id is not None:
        organization = OrganizationRepository(session).get_active_by_id(organization_id)
        membership_repo = OrganizationMembershipRepository(session)
        actor_membership = membership_repo.get_active_by_org_user(organization_id, user.id)
        if organization is None or actor_membership is None:
            raise ScenePermissionDeniedError(
                details={"reason": "active_organization_member_required"}
            )
        participant_user_ids = [
            membership.user_id for membership in membership_repo.list_active_by_org(organization_id)
        ]

    # Create the instance.
    instance_repo = SceneInstanceRepository(session)
    instance = SceneInstance(
        definition_id=definition.id,
        conversation_id=data.get("conversation_id"),
        organization_id=organization_id,
        created_by=user.id,
        status=SceneState.DRAFT.value,
        current_phase=SceneState.DRAFT.value,
        public_context_json=json.dumps(data["public_context"])
        if data.get("public_context")
        else None,
        idempotency_key=idempotency_key,
        expires_at=data.get("expires_at"),
    )
    instance_repo.create(instance)

    # Add the creator as a participant (ACCEPTED, is_creator=True).
    part_repo = SceneParticipantRepository(session)
    creator = SceneParticipant(
        scene_instance_id=instance.id,
        user_id=user.id,
        status=ParticipantStatus.ACCEPTED.value,
        is_creator=True,
        joined_at=utc_now(),
    )
    part_repo.create(creator)

    # Add other participants (INVITED).
    for uid in participant_user_ids:
        if uid == user.id:
            continue  # Creator already added
        participant = SceneParticipant(
            scene_instance_id=instance.id,
            user_id=uid,
            status=ParticipantStatus.INVITED.value,
            is_creator=False,
        )
        part_repo.create(participant)

    session.commit()
    session.refresh(instance)

    # Publish event.
    default_event_bus.publish(
        SceneInstanceCreated(
            event_id=_generate_event_id(),
            scene_instance_id=instance.id,
            scene_key=scene_key,
            created_by=user.id,
            occurred_at=utc_now(),
        )
    )

    log_audit(
        actor_id=user.id,
        action="scene_create",
        resource_type="scene",
        resource_id=str(instance.id),
        result="SUCCESS",
        session=session,
    )

    return _instance_to_read(instance, session, viewer_user_id=user.id)


def get_scene_instance(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Get a scene instance by ID.

    Only participants can view the instance.
    """
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    # Check participation.
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None:
        raise ScenePermissionDeniedError(details={"reason": "not_a_participant"})

    return _instance_to_read(instance, session, viewer_user_id=user.id)


def list_my_scenes(
    user: User,
    session: Session,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """List scene instances the user can access as a participant."""
    instance_repo = SceneInstanceRepository(session)
    instances = instance_repo.list_by_participant(user.id, limit=limit)
    return {
        "scenes": [_instance_to_read(i, session, viewer_user_id=user.id) for i in instances],
        "total": len(instances),
    }


def transition_state(
    user: User,
    instance_id: UUID,
    action: str,
    session: Session,
    *,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Transition a scene instance to the next state via an action.

    Args:
        action: One of: publish, start_collecting, start_processing,
            candidates_ready, voting_complete, confirm, cancel, expire,
            processing_failed.

    Raises:
        SceneNotFoundError: If instance not found.
        ScenePermissionDeniedError: If user is not the creator.
        SceneStateTransitionError: If the transition is illegal.
        SQLAlchemy StaleDataError: If optimistic lock fails (concurrent modification).
    """
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    # Only the creator can trigger state transitions.
    if instance.created_by != user.id:
        raise ScenePermissionDeniedError(details={"reason": "only_creator_can_transition"})

    current_state = SceneState(instance.status)
    target_state = SceneStateMachine.get_target_state(current_state, action)
    if target_state is None:
        raise SceneStateTransitionError(
            details={
                "current_state": current_state.value,
                "action": action,
            }
        )

    # Optimistic-lock update: directly modify the instance and bump version.
    instance.status = target_state.value
    instance.current_phase = target_state.value
    instance.version += 1
    instance.updated_at = utc_now()

    # Set terminal timestamps.
    if target_state == SceneState.COMPLETED:
        instance.completed_at = utc_now()
    elif target_state == SceneState.CANCELLED:
        instance.cancelled_at = utc_now()
    elif target_state == SceneState.FAILED:
        instance.failed_reason_code = "processing_failed"

    instance_repo.save(instance)
    session.commit()
    session.refresh(instance)

    # Publish appropriate event.
    part_repo = SceneParticipantRepository(session)
    submitted_count = PrivateSubmissionRepository(session).count_by_instance(instance_id)
    participant_count = part_repo.count_accepted(instance_id)

    if target_state == SceneState.COMPLETED:
        result_repo = SceneResultRepository(session)
        result = result_repo.get_by_instance(instance_id)
        default_event_bus.publish(
            SceneCompleted(
                event_id=_generate_event_id(),
                scene_instance_id=instance_id,
                public_result_id=result.id if result else None,
                participant_count=participant_count,
                submitted_count=submitted_count,
                occurred_at=utc_now(),
            )
        )
    elif target_state == SceneState.CANCELLED:
        default_event_bus.publish(
            SceneCancelled(
                event_id=_generate_event_id(),
                scene_instance_id=instance_id,
                cancelled_by=user.id,
                occurred_at=utc_now(),
            )
        )
    elif target_state == SceneState.EXPIRED:
        default_event_bus.publish(
            SceneExpired(
                event_id=_generate_event_id(),
                scene_instance_id=instance_id,
                occurred_at=utc_now(),
            )
        )
    elif target_state == SceneState.FAILED:
        default_event_bus.publish(
            SceneFailed(
                event_id=_generate_event_id(),
                scene_instance_id=instance_id,
                reason_code="processing_failed",
                occurred_at=utc_now(),
            )
        )
    else:
        # Phase change event for non-terminal transitions.
        default_event_bus.publish(
            ScenePhaseChanged(
                event_id=_generate_event_id(),
                scene_instance_id=instance_id,
                old_phase=current_state.value,
                new_phase=target_state.value,
                submitted_count=submitted_count,
                participant_count=participant_count,
                occurred_at=utc_now(),
            )
        )

    log_audit(
        actor_id=user.id,
        action=f"scene_{action}",
        resource_type="scene",
        resource_id=str(instance_id),
        result="SUCCESS",
        session=session,
    )

    return _instance_to_read(instance, session, viewer_user_id=user.id)


def expire_stale_instances(session: Session) -> int:
    """Expire all instances past their expires_at. Returns count expired."""
    instance_repo = SceneInstanceRepository(session)
    stale = instance_repo.list_expired()
    count = 0
    for instance in stale:
        current_state = SceneState(instance.status)
        if SceneStateMachine.can_action(current_state, "expire"):
            instance_repo.update_status(
                instance.id,
                SceneState.EXPIRED.value,
                SceneState.EXPIRED.value,
                version=instance.version,
            )
            default_event_bus.publish(
                SceneExpired(
                    event_id=_generate_event_id(),
                    scene_instance_id=instance.id,
                    occurred_at=utc_now(),
                )
            )
            count += 1
    if count > 0:
        session.commit()
    return count


# ---------------------------------------------------------------------------
# Participant management
# ---------------------------------------------------------------------------


def accept_invitation(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Accept an invitation to join a scene."""
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None:
        raise SceneNotFoundError(details={"reason": "not_invited"})
    if participant.status != ParticipantStatus.INVITED.value:
        return _participant_to_read(participant)

    participant.status = ParticipantStatus.ACCEPTED.value
    participant.joined_at = utc_now()
    part_repo.save(participant)
    session.commit()

    log_audit(
        actor_id=user.id,
        action="scene_accept",
        resource_type="scene",
        resource_id=str(instance_id),
        result="SUCCESS",
        session=session,
    )
    return _participant_to_read(participant)


def decline_invitation(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Decline an invitation to join a scene."""
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None:
        raise SceneNotFoundError(details={"reason": "not_invited"})
    participant.status = ParticipantStatus.DECLINED.value
    part_repo.save(participant)
    session.commit()

    log_audit(
        actor_id=user.id,
        action="scene_decline",
        resource_type="scene",
        resource_id=str(instance_id),
        result="SUCCESS",
        session=session,
    )
    return _participant_to_read(participant)


def leave_scene(
    user: User,
    instance_id: UUID,
    session: Session,
) -> None:
    """Leave a scene instance."""
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None:
        raise SceneNotFoundError(details={"reason": "not_a_participant"})
    if participant.is_creator:
        raise ScenePermissionDeniedError(details={"reason": "creator_cannot_leave"})
    participant.status = ParticipantStatus.LEFT.value
    part_repo.save(participant)
    session.commit()

    log_audit(
        actor_id=user.id,
        action="scene_leave",
        resource_type="scene",
        resource_id=str(instance_id),
        result="SUCCESS",
        session=session,
    )


def list_participants(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """List participants in a scene instance."""
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    part_repo = SceneParticipantRepository(session)
    # Only participants can see the participant list.
    viewer = part_repo.get_by_instance_and_user(instance_id, user.id)
    if viewer is None:
        raise ScenePermissionDeniedError()

    participants = part_repo.list_by_instance(instance_id)
    return {
        "participants": [_participant_to_read(p) for p in participants],
        "total": len(participants),
    }


def _participant_to_read(p: SceneParticipant) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "user_id": str(p.user_id),
        "status": p.status,
        "is_creator": p.is_creator,
        "joined_at": p.joined_at.isoformat() if p.joined_at else None,
    }


# ---------------------------------------------------------------------------
# Private Submission management
# ---------------------------------------------------------------------------


def submit_private_preferences(
    user: User,
    instance_id: UUID,
    preferences: dict[str, Any],
    session: Session,
    *,
    save_to_long_term_memory: bool = False,
) -> dict[str, Any]:
    """Submit (or replace) a user's private preferences for a scene.

    Privacy:
    - Preferences are encrypted before storage.
    - The response never echoes the raw payload.
    - Only the owner can submit/replace their own preferences.
    - A scene-level consent is required (participant must be ACCEPTED).

    Raises:
        SceneNotFoundError: If instance not found.
        SceneConsentRequiredError: If the user is not an ACCEPTED participant.
        SceneSubmissionError: If the submission is invalid (per plugin).
    """
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    # Must be in COLLECTING_PRIVATE_INPUT phase.
    if instance.status != SceneState.COLLECTING_PRIVATE_INPUT.value:
        raise SceneStateTransitionError(
            details={
                "current_state": instance.status,
                "required_state": SceneState.COLLECTING_PRIVATE_INPUT.value,
            }
        )

    # Must be an ACCEPTED participant.
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None or participant.status != ParticipantStatus.ACCEPTED.value:
        raise SceneConsentRequiredError(details={"reason": "must_accept_invitation_first"})

    # Validate via plugin.
    registry = get_scene_registry()
    plugin = registry.get(instance.definition.scene_key, instance.definition.version)
    plugin.validate_private_submission(preferences)

    # Build capsule and validate it.
    capsule = plugin.build_private_capsule(preferences)
    validate_capsule(capsule)

    # Encrypt the raw preferences.
    ciphertext = encrypt_payload(preferences)
    payload_hash = hash_payload(preferences)
    capsule_json = capsule_to_json(capsule)
    expires_at = utc_now() + _DEFAULT_SUBMISSION_EXPIRY

    # Check for existing submission (replace).
    sub_repo = PrivateSubmissionRepository(session)
    existing = sub_repo.get_for_owner(instance_id, user.id)
    if existing is not None:
        existing.encrypted_payload = ciphertext
        existing.capsule_json = capsule_json
        existing.payload_hash = payload_hash
        existing.expires_at = expires_at
        existing.deleted_at = None
        sub_repo.save(existing)
        submission = existing
    else:
        submission = PrivateSubmission(
            scene_instance_id=instance_id,
            user_id=user.id,
            encrypted_payload=ciphertext,
            capsule_json=capsule_json,
            payload_hash=payload_hash,
            expires_at=expires_at,
        )
        sub_repo.create(submission)

    session.commit()
    session.refresh(submission)

    log_audit(
        actor_id=user.id,
        action="scene_submit_private",
        resource_type="scene_submission",
        resource_id=str(submission.id),
        result="SUCCESS",
        session=session,
    )

    # P9-14: Long-term memory confirmation.
    # By default, preferences are NOT saved to Memory.
    # Only when the user explicitly confirms (save_to_long_term_memory=True)
    # do we save the capsule (not raw preferences or notes) to Memory
    # with an explicit category and source.
    if save_to_long_term_memory:
        from ..memories.models import MemorySource, SensitivityLevel
        from ..memories.service import create_memory

        # Save only the de-identified capsule — never raw preferences or notes.
        capsule_content = json.dumps(capsule.model_dump(mode="json"))
        create_memory(
            user,
            {
                "category": "dorm_dinner_preference",
                "source": MemorySource.USER_INPUT.value,
                "sensitivity_level": SensitivityLevel.CONFIDENTIAL.value,
                "content": capsule_content,
            },
            session,
        )
        session.commit()

    # Return response WITHOUT raw content.
    return PrivateSubmissionResponse(
        submission_id=submission.id,
        submission_status="ACCEPTED",
        capsule_generated=True,
        expires_at=submission.expires_at,
    ).model_dump(mode="json")


def get_submission_status(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Get the status of the current user's submission — no raw content."""
    sub_repo = PrivateSubmissionRepository(session)
    submission = sub_repo.get_for_owner(instance_id, user.id)
    if submission is None:
        return {
            "has_submitted": False,
            "submitted_at": None,
            "expires_at": None,
            "capsule_generated": False,
        }
    return {
        "has_submitted": True,
        "submitted_at": submission.created_at.isoformat() if submission.created_at else None,
        "expires_at": submission.expires_at.isoformat() if submission.expires_at else None,
        "capsule_generated": submission.capsule_json is not None,
    }


def delete_submission(
    user: User,
    instance_id: UUID,
    session: Session,
) -> None:
    """Delete the current user's private submission."""
    sub_repo = PrivateSubmissionRepository(session)
    submission = sub_repo.get_for_owner(instance_id, user.id)
    if submission is None:
        raise SceneNotFoundError(details={"reason": "no_submission"})
    sub_repo.soft_delete(submission)
    session.commit()

    log_audit(
        actor_id=user.id,
        action="scene_delete_submission",
        resource_type="scene_submission",
        resource_id=str(submission.id),
        result="SUCCESS",
        session=session,
    )


# ---------------------------------------------------------------------------
# Voting
# ---------------------------------------------------------------------------


def cast_vote(
    user: User,
    instance_id: UUID,
    candidate_id: UUID,
    vote_value: str,
    session: Session,
    *,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Cast or replace a vote.

    Rules:
    - One person one vote (replacing is allowed).
    - Only ACCEPTED participants can vote.
    - Scene must be in VOTING phase.
    - Vote value must be APPROVE/REJECT/ABSTAIN.

    Raises:
        SceneNotFoundError: If instance or candidate not found.
        ScenePermissionDeniedError: If user is not a participant.
        SceneStateTransitionError: If not in VOTING phase.
        SceneSubmissionError: If vote_value is invalid.
    """
    # Validate vote value.
    try:
        VoteValue(vote_value)
    except ValueError:
        raise SceneSubmissionError(
            message="无效的投票值",
            details={"vote_value": vote_value, "allowed": [v.value for v in VoteValue]},
        ) from None

    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    if instance.status != SceneState.VOTING.value:
        raise SceneStateTransitionError(
            details={
                "current_state": instance.status,
                "required_state": SceneState.VOTING.value,
            }
        )

    # Must be an ACCEPTED participant.
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None or participant.status != ParticipantStatus.ACCEPTED.value:
        raise ScenePermissionDeniedError(details={"reason": "must_be_accepted_participant"})

    # Validate candidate exists in this instance.
    cand_repo = SceneCandidateRepository(session)
    candidate = cand_repo.get_by_id(candidate_id)
    if candidate is None or candidate.scene_instance_id != instance_id:
        raise SceneNotFoundError(details={"reason": "candidate_not_in_instance"})

    # Cast or replace vote.
    vote_repo = SceneVoteRepository(session)
    vote = SceneVote(
        scene_instance_id=instance_id,
        user_id=user.id,
        candidate_id=candidate_id,
        vote_value=vote_value,
        idempotency_key=idempotency_key,
    )
    vote = vote_repo.replace_vote(instance_id, user.id, vote)

    session.commit()
    session.refresh(vote)

    log_audit(
        actor_id=user.id,
        action="scene_vote",
        resource_type="scene_vote",
        resource_id=str(vote.id),
        result="SUCCESS",
        session=session,
    )

    return {
        "id": str(vote.id),
        "candidate_id": str(vote.candidate_id),
        "vote_value": vote.vote_value,
        "created_at": vote.created_at.isoformat() if vote.created_at else None,
    }


def list_candidates(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """List public candidates for a scene instance."""
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    # Must be a participant.
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None:
        raise ScenePermissionDeniedError()

    cand_repo = SceneCandidateRepository(session)
    candidates = cand_repo.list_by_instance(instance_id)
    return {
        "candidates": [_candidate_to_read(c) for c in candidates],
        "total": len(candidates),
    }


def get_scene_result(
    user: User,
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Get the public result of a completed scene."""
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    # Must be a participant.
    part_repo = SceneParticipantRepository(session)
    participant = part_repo.get_by_instance_and_user(instance_id, user.id)
    if participant is None:
        raise ScenePermissionDeniedError()

    result_repo = SceneResultRepository(session)
    result = result_repo.get_by_instance(instance_id)
    if result is None:
        raise SceneNotFoundError(details={"reason": "no_result_yet"})

    # Get selected candidate.
    cand_repo = SceneCandidateRepository(session)
    selected = None
    if result.selected_candidate_id is not None:
        c = cand_repo.get_by_id(result.selected_candidate_id)
        if c is not None:
            selected = _candidate_to_read(c)

    return {
        "id": str(result.id),
        "selected_candidate": selected,
        "public_summary": result.public_summary,
        "participant_count": result.participant_count,
        "submitted_count": result.submitted_count,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _instance_to_read(
    instance: SceneInstance,
    session: Session,
    *,
    viewer_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Convert a SceneInstance to a safe read dict — no private data."""
    part_repo = SceneParticipantRepository(session)
    sub_repo = PrivateSubmissionRepository(session)

    participant_count = part_repo.count_accepted(instance.id)
    submitted_count = sub_repo.count_by_instance(instance.id)
    viewer_participant = (
        part_repo.get_by_instance_and_user(instance.id, viewer_user_id)
        if viewer_user_id is not None
        else None
    )

    return {
        "id": str(instance.id),
        "scene_key": instance.definition.scene_key if instance.definition else None,
        "status": instance.status,
        "current_phase": instance.current_phase,
        "created_by": str(instance.created_by),
        "conversation_id": str(instance.conversation_id) if instance.conversation_id else None,
        "organization_id": str(instance.organization_id) if instance.organization_id else None,
        "public_context": _parse_context(instance.public_context_json),
        "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "cancelled_at": instance.cancelled_at.isoformat() if instance.cancelled_at else None,
        "failed_reason_code": instance.failed_reason_code,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        "participant_count": participant_count,
        "submitted_count": submitted_count,
        "participant_status": viewer_participant.status if viewer_participant else None,
        "is_creator": bool(viewer_participant and viewer_participant.is_creator),
    }


def _candidate_to_read(c: SceneCandidate) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "candidate_key": c.candidate_key,
        "display_name": c.display_name,
        "public_metadata": _parse_context(c.public_metadata_json),
        "aggregate_score": c.aggregate_score,
        "public_reason": c.public_reason,
        "status": c.status,
        "rank": c.rank,
    }
