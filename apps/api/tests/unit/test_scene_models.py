"""P8-03: Scene ORM model tests.

Tests:
- All models can be created and persisted.
- Relationships work (definition→instances→participants→submissions).
- PrivateSubmission repr does not expose plaintext.
- SceneCandidate only stores public data.
- SceneResult only stores public data.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.models import (
    CandidateStatus,
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
from src.modules.scenes.state_machine import SceneState
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="scene@example.com",
        password_hash="fake",
        display_name="Scene User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def scene_definition(test_db_session: Session) -> SceneDefinition:
    defn = SceneDefinition(
        scene_key="test_scene",
        version="1.0.0",
        name="Test Scene",
        description="A test scene",
        enabled=True,
    )
    test_db_session.add(defn)
    test_db_session.flush()
    return defn


@pytest.fixture()
def scene_instance(
    test_db_session: Session,
    scene_definition: SceneDefinition,
    test_user: User,
) -> SceneInstance:
    instance = SceneInstance(
        definition_id=scene_definition.id,
        created_by=test_user.id,
        status=SceneState.DRAFT.value,
        current_phase=SceneState.DRAFT.value,
    )
    test_db_session.add(instance)
    test_db_session.flush()
    return instance


class TestSceneDefinition:
    def test_create_and_retrieve(self, test_db_session: Session, scene_definition: SceneDefinition) -> None:
        retrieved = test_db_session.get(SceneDefinition, scene_definition.id)
        assert retrieved is not None
        assert retrieved.scene_key == "test_scene"
        assert retrieved.version == "1.0.0"
        assert retrieved.enabled is True

    def test_repr_no_sensitive_data(self, scene_definition: SceneDefinition) -> None:
        repr_str = repr(scene_definition)
        assert "scene_key=test_scene" in repr_str
        assert "enabled=True" in repr_str


class TestSceneInstance:
    def test_create_and_retrieve(
        self, test_db_session: Session, scene_instance: SceneInstance
    ) -> None:
        retrieved = test_db_session.get(SceneInstance, scene_instance.id)
        assert retrieved is not None
        assert retrieved.status == SceneState.DRAFT.value
        assert retrieved.current_phase == SceneState.DRAFT.value

    def test_repr_no_sensitive_data(self, scene_instance: SceneInstance) -> None:
        repr_str = repr(scene_instance)
        assert "status=" in repr_str
        assert "phase=" in repr_str
        # Should not contain any private data fields
        assert "payload" not in repr_str.lower()
        assert "capsule" not in repr_str.lower()


class TestPrivateSubmission:
    def test_create_with_encrypted_payload(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
        test_user: User,
    ) -> None:
        sub = PrivateSubmission(
            scene_instance_id=scene_instance.id,
            user_id=test_user.id,
            encrypted_payload="gAAAAAB...ciphertext...",
            capsule_json='{"hard_constraints": {}}',
            payload_hash="abc123",
        )
        test_db_session.add(sub)
        test_db_session.flush()

        retrieved = test_db_session.get(PrivateSubmission, sub.id)
        assert retrieved is not None
        assert retrieved.encrypted_payload == "gAAAAAB...ciphertext..."
        assert retrieved.deleted_at is None

    def test_repr_does_not_expose_plaintext(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
        test_user: User,
    ) -> None:
        sub = PrivateSubmission(
            scene_instance_id=scene_instance.id,
            user_id=test_user.id,
            encrypted_payload="gAAAAAB...ciphertext...",
        )
        repr_str = repr(sub)
        assert "has_payload=True" in repr_str
        assert "gAAAAAB" not in repr_str  # ciphertext not in repr
        assert "plaintext" not in repr_str.lower()


class TestSceneCandidate:
    def test_create_with_public_data(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
    ) -> None:
        candidate = SceneCandidate(
            scene_instance_id=scene_instance.id,
            candidate_key="restaurant_1",
            display_name="Restaurant One",
            aggregate_score=0.85,
            public_reason="Good rating and nearby",
            status=CandidateStatus.ACTIVE.value,
            rank=1,
        )
        test_db_session.add(candidate)
        test_db_session.flush()

        retrieved = test_db_session.get(SceneCandidate, candidate.id)
        assert retrieved is not None
        assert retrieved.candidate_key == "restaurant_1"
        assert retrieved.aggregate_score == 0.85

    def test_repr_no_private_data(self, test_db_session: Session, scene_instance: SceneInstance) -> None:
        candidate = SceneCandidate(
            scene_instance_id=scene_instance.id,
            candidate_key="c1",
            display_name="C1",
        )
        repr_str = repr(candidate)
        assert "key=c1" in repr_str
        assert "payload" not in repr_str.lower()


class TestSceneVote:
    def test_create_vote(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
        test_user: User,
    ) -> None:
        candidate = SceneCandidate(
            scene_instance_id=scene_instance.id,
            candidate_key="c1",
            display_name="C1",
        )
        test_db_session.add(candidate)
        test_db_session.flush()

        vote = SceneVote(
            scene_instance_id=scene_instance.id,
            user_id=test_user.id,
            candidate_id=candidate.id,
            vote_value=VoteValue.APPROVE.value,
        )
        test_db_session.add(vote)
        test_db_session.flush()

        retrieved = test_db_session.get(SceneVote, vote.id)
        assert retrieved is not None
        assert retrieved.vote_value == VoteValue.APPROVE.value


class TestSceneResult:
    def test_create_result(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
    ) -> None:
        result = SceneResult(
            scene_instance_id=scene_instance.id,
            public_summary="Selected restaurant A",
            participant_count=5,
            submitted_count=4,
        )
        test_db_session.add(result)
        test_db_session.flush()

        retrieved = test_db_session.get(SceneResult, result.id)
        assert retrieved is not None
        assert retrieved.public_summary == "Selected restaurant A"
        assert retrieved.participant_count == 5

    def test_result_one_per_instance(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
    ) -> None:
        """SceneResult has a unique constraint on scene_instance_id."""
        result1 = SceneResult(
            scene_instance_id=scene_instance.id,
            public_summary="First",
            participant_count=1,
            submitted_count=1,
        )
        test_db_session.add(result1)
        test_db_session.flush()

        result2 = SceneResult(
            scene_instance_id=scene_instance.id,
            public_summary="Second",
            participant_count=1,
            submitted_count=1,
        )
        test_db_session.add(result2)
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            test_db_session.flush()


class TestRelationships:
    def test_definition_instance_relationship(
        self,
        test_db_session: Session,
        scene_definition: SceneDefinition,
        scene_instance: SceneInstance,
    ) -> None:
        test_db_session.refresh(scene_definition)
        assert len(scene_definition.instances) >= 1
        assert scene_definition.instances[0].id == scene_instance.id

    def test_instance_participant_relationship(
        self,
        test_db_session: Session,
        scene_instance: SceneInstance,
        test_user: User,
    ) -> None:
        participant = SceneParticipant(
            scene_instance_id=scene_instance.id,
            user_id=test_user.id,
            status=ParticipantStatus.ACCEPTED.value,
            is_creator=True,
        )
        test_db_session.add(participant)
        test_db_session.flush()
        test_db_session.refresh(scene_instance)
        assert len(scene_instance.participants) >= 1
