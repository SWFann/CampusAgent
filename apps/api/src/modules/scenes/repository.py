"""Scene repository — database access for all scene models.

Privacy:
- PrivateSubmission.encrypted_payload is never selected or returned in
  any listing method. Only the service layer (which has the user context)
  may access it via ``get_submission_for_owner``.
- Repository methods return ORM objects; the service layer is responsible
  for stripping sensitive fields before returning to the API.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from .models import (
    CandidateStatus,
    ParticipantStatus,
    PrivateSubmission,
    SceneCandidate,
    SceneDefinition,
    SceneInstance,
    SceneParticipant,
    SceneResult,
    SceneVote,
)


class SceneDefinitionRepository:
    """Repository for SceneDefinition ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, definition: SceneDefinition) -> SceneDefinition:
        self._session.add(definition)
        self._session.flush()
        return definition

    def get_by_id(self, definition_id: UUID) -> SceneDefinition | None:
        return self._session.get(SceneDefinition, definition_id)

    def get_by_key(self, scene_key: str, version: str = "1.0.0") -> SceneDefinition | None:
        return (
            self._session.query(SceneDefinition)
            .filter(
                SceneDefinition.scene_key == scene_key,
                SceneDefinition.version == version,
            )
            .first()
        )

    def list_enabled(self) -> list[SceneDefinition]:
        return (
            self._session.query(SceneDefinition)
            .filter(SceneDefinition.enabled.is_(True))
            .order_by(SceneDefinition.created_at.desc())
            .all()
        )

    def list_all(self) -> list[SceneDefinition]:
        return (
            self._session.query(SceneDefinition)
            .order_by(SceneDefinition.created_at.desc())
            .all()
        )

    def set_enabled(self, definition_id: UUID, enabled: bool) -> None:
        defn = self._session.get(SceneDefinition, definition_id)
        if defn is not None:
            defn.enabled = enabled


class SceneInstanceRepository:
    """Repository for SceneInstance ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, instance: SceneInstance) -> SceneInstance:
        self._session.add(instance)
        self._session.flush()
        return instance

    def get_by_id(self, instance_id: UUID) -> SceneInstance | None:
        return self._session.get(SceneInstance, instance_id)

    def get_by_idempotency_key(self, key: str) -> SceneInstance | None:
        return (
            self._session.query(SceneInstance)
            .filter(SceneInstance.idempotency_key == key)
            .first()
        )

    def list_by_creator(self, user_id: UUID, *, limit: int = 50) -> list[SceneInstance]:
        return (
            self._session.query(SceneInstance)
            .filter(SceneInstance.created_by == user_id)
            .order_by(SceneInstance.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_active(self, *, limit: int = 100) -> list[SceneInstance]:
        """List non-terminal scene instances."""
        from .state_machine import TERMINAL_STATES

        terminal_values = [s.value for s in TERMINAL_STATES]
        return (
            self._session.query(SceneInstance)
            .filter(SceneInstance.status.notin_(terminal_values))
            .order_by(SceneInstance.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_expired(self, *, limit: int = 50) -> list[SceneInstance]:
        """List active instances that have passed their expires_at."""
        from .state_machine import TERMINAL_STATES

        now = utc_now()
        terminal_values = [s.value for s in TERMINAL_STATES]
        return (
            self._session.query(SceneInstance)
            .filter(
                SceneInstance.expires_at.is_not(None),
                SceneInstance.expires_at < now,
                SceneInstance.status.notin_(terminal_values),
            )
            .limit(limit)
            .all()
        )

    def save(self, instance: SceneInstance) -> SceneInstance:
        self._session.flush()
        return instance

    def update_status(
        self,
        instance_id: UUID,
        status: str,
        current_phase: str,
        *,
        version: int | None = None,
    ) -> bool:
        """Optimistic-lock update of status and phase.

        Returns True if the row was updated, False if the version check
        failed (concurrency conflict).
        """
        if version is not None:
            result = (
                self._session.query(SceneInstance)
                .filter(
                    SceneInstance.id == instance_id,
                    SceneInstance.version == version,
                )
                .update(
                    {
                        SceneInstance.status: status,
                        SceneInstance.current_phase: current_phase,
                        SceneInstance.version: version + 1,
                        SceneInstance.updated_at: utc_now(),
                    },
                    synchronize_session=False,
                )
            )
            return result > 0
        instance = self._session.get(SceneInstance, instance_id)
        if instance is None:
            return False
        instance.status = status
        instance.current_phase = current_phase
        instance.version += 1
        instance.updated_at = utc_now()
        return True


class SceneParticipantRepository:
    """Repository for SceneParticipant ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, participant: SceneParticipant) -> SceneParticipant:
        self._session.add(participant)
        self._session.flush()
        return participant

    def get_by_id(self, participant_id: UUID) -> SceneParticipant | None:
        return self._session.get(SceneParticipant, participant_id)

    def get_by_instance_and_user(
        self, instance_id: UUID, user_id: UUID
    ) -> SceneParticipant | None:
        return (
            self._session.query(SceneParticipant)
            .filter(
                SceneParticipant.scene_instance_id == instance_id,
                SceneParticipant.user_id == user_id,
            )
            .first()
        )

    def list_by_instance(self, instance_id: UUID) -> list[SceneParticipant]:
        return (
            self._session.query(SceneParticipant)
            .filter(SceneParticipant.scene_instance_id == instance_id)
            .order_by(SceneParticipant.created_at.asc())
            .all()
        )

    def list_accepted(self, instance_id: UUID) -> list[SceneParticipant]:
        return (
            self._session.query(SceneParticipant)
            .filter(
                SceneParticipant.scene_instance_id == instance_id,
                SceneParticipant.status == ParticipantStatus.ACCEPTED.value,
            )
            .all()
        )

    def count_accepted(self, instance_id: UUID) -> int:
        return (
            self._session.query(SceneParticipant)
            .filter(
                SceneParticipant.scene_instance_id == instance_id,
                SceneParticipant.status == ParticipantStatus.ACCEPTED.value,
            )
            .count()
        )

    def save(self, participant: SceneParticipant) -> SceneParticipant:
        self._session.flush()
        return participant


class PrivateSubmissionRepository:
    """Repository for PrivateSubmission ORM.

    Privacy: methods here return ORM objects including encrypted_payload.
    The service layer is responsible for never returning encrypted_payload
    or decrypted content in API responses.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, submission: PrivateSubmission) -> PrivateSubmission:
        self._session.add(submission)
        self._session.flush()
        return submission

    def get_by_id(self, submission_id: UUID) -> PrivateSubmission | None:
        return self._session.get(PrivateSubmission, submission_id)

    def get_for_owner(
        self, instance_id: UUID, user_id: UUID
    ) -> PrivateSubmission | None:
        """Get a user's submission (including encrypted_payload).

        Only the service layer should call this, and only when acting on
        behalf of the owning user.
        """
        return (
            self._session.query(PrivateSubmission)
            .filter(
                PrivateSubmission.scene_instance_id == instance_id,
                PrivateSubmission.user_id == user_id,
                PrivateSubmission.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_instance(self, instance_id: UUID) -> list[PrivateSubmission]:
        """List all non-deleted submissions for an instance.

        Returns ORM objects with encrypted_payload — the coordinator
        uses this to decrypt and process during GENERATING_CANDIDATES.
        """
        return (
            self._session.query(PrivateSubmission)
            .filter(
                PrivateSubmission.scene_instance_id == instance_id,
                PrivateSubmission.deleted_at.is_(None),
            )
            .all()
        )

    def count_by_instance(self, instance_id: UUID) -> int:
        return (
            self._session.query(PrivateSubmission)
            .filter(
                PrivateSubmission.scene_instance_id == instance_id,
                PrivateSubmission.deleted_at.is_(None),
            )
            .count()
        )

    def soft_delete(self, submission: PrivateSubmission) -> None:
        submission.deleted_at = utc_now()

    def hard_delete_payload(self, instance_id: UUID) -> int:
        """Permanently clear encrypted_payload and capsule for all
        submissions in an instance.

        Returns the number of rows affected.
        """
        submissions = (
            self._session.query(PrivateSubmission)
            .filter(
                PrivateSubmission.scene_instance_id == instance_id,
                PrivateSubmission.deleted_at.is_(None),
            )
            .all()
        )
        count = 0
        for sub in submissions:
            sub.encrypted_payload = ""
            sub.capsule_json = None
            sub.deleted_at = utc_now()
            count += 1
        self._session.flush()
        return count

    def list_expired(self, *, limit: int = 100) -> list[PrivateSubmission]:
        """List submissions past their expiry that haven't been deleted."""
        now = utc_now()
        return (
            self._session.query(PrivateSubmission)
            .filter(
                PrivateSubmission.expires_at.is_not(None),
                PrivateSubmission.expires_at < now,
                PrivateSubmission.deleted_at.is_(None),
            )
            .limit(limit)
            .all()
        )

    def save(self, submission: PrivateSubmission) -> PrivateSubmission:
        self._session.flush()
        return submission


class SceneCandidateRepository:
    """Repository for SceneCandidate ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, candidate: SceneCandidate) -> SceneCandidate:
        self._session.add(candidate)
        self._session.flush()
        return candidate

    def create_batch(self, candidates: list[SceneCandidate]) -> list[SceneCandidate]:
        for c in candidates:
            self._session.add(c)
        self._session.flush()
        return candidates

    def get_by_id(self, candidate_id: UUID) -> SceneCandidate | None:
        return self._session.get(SceneCandidate, candidate_id)

    def list_by_instance(self, instance_id: UUID) -> list[SceneCandidate]:
        return (
            self._session.query(SceneCandidate)
            .filter(SceneCandidate.scene_instance_id == instance_id)
            .order_by(SceneCandidate.rank.asc().nullslast(), SceneCandidate.aggregate_score.desc())
            .all()
        )

    def list_active(self, instance_id: UUID) -> list[SceneCandidate]:
        return (
            self._session.query(SceneCandidate)
            .filter(
                SceneCandidate.scene_instance_id == instance_id,
                SceneCandidate.status == CandidateStatus.ACTIVE.value,
            )
            .order_by(SceneCandidate.rank.asc().nullslast())
            .all()
        )

    def save(self, candidate: SceneCandidate) -> SceneCandidate:
        self._session.flush()
        return candidate

    def save_batch(self, candidates: list[SceneCandidate]) -> None:
        self._session.flush()


class SceneVoteRepository:
    """Repository for SceneVote ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, vote: SceneVote) -> SceneVote:
        self._session.add(vote)
        self._session.flush()
        return vote

    def get_by_instance_and_user(
        self, instance_id: UUID, user_id: UUID
    ) -> SceneVote | None:
        return (
            self._session.query(SceneVote)
            .filter(
                SceneVote.scene_instance_id == instance_id,
                SceneVote.user_id == user_id,
            )
            .first()
        )

    def list_by_instance(self, instance_id: UUID) -> list[SceneVote]:
        return (
            self._session.query(SceneVote)
            .filter(SceneVote.scene_instance_id == instance_id)
            .all()
        )

    def list_by_candidate(self, candidate_id: UUID) -> list[SceneVote]:
        return (
            self._session.query(SceneVote)
            .filter(SceneVote.candidate_id == candidate_id)
            .all()
        )

    def count_by_instance(self, instance_id: UUID) -> int:
        return (
            self._session.query(SceneVote)
            .filter(SceneVote.scene_instance_id == instance_id)
            .count()
        )

    def count_by_value(self, candidate_id: UUID, value: str) -> int:
        return (
            self._session.query(SceneVote)
            .filter(
                SceneVote.candidate_id == candidate_id,
                SceneVote.vote_value == value,
            )
            .count()
        )

    def replace_vote(self, instance_id: UUID, user_id: UUID, vote: SceneVote) -> SceneVote:
        """Replace an existing vote (one-person-one-vote with replacement)."""
        existing = self.get_by_instance_and_user(instance_id, user_id)
        if existing is not None:
            existing.candidate_id = vote.candidate_id
            existing.vote_value = vote.vote_value
            existing.idempotency_key = vote.idempotency_key
            self._session.flush()
            return existing
        self._session.add(vote)
        self._session.flush()
        return vote


class SceneResultRepository:
    """Repository for SceneResult ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, result: SceneResult) -> SceneResult:
        self._session.add(result)
        self._session.flush()
        return result

    def get_by_instance(self, instance_id: UUID) -> SceneResult | None:
        return (
            self._session.query(SceneResult)
            .filter(SceneResult.scene_instance_id == instance_id)
            .first()
        )

    def save(self, result: SceneResult) -> SceneResult:
        self._session.flush()
        return result
