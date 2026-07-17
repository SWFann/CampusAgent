"""P6-07: ConsentRecord model and repository tests.

Tests:
- ConsentRecord can be created with purpose and scope.
- Purpose enum values: chat_reply, scene_execution, memory_review, recommendation.
- Scope JSON stores category/memory_id/scene_instance_id/expires_at.
- granted status default.
- revoked_at set on revoke.
"""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.memories.models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentStatus,
)
from src.modules.memories.repository import ConsentRepository
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="consent@example.com",
        password_hash="fake-hash",
        display_name="Consent User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def test_agent(test_db_session: Session, test_user: User):
    from src.modules.agents.models import Agent, AgentType, DelegationLevel

    agent = Agent(
        owner_user_id=test_user.id,
        type=AgentType.PERSONAL.value,
        name="Consent Agent",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    test_db_session.add(agent)
    test_db_session.flush()
    return agent


class TestConsentRecordModel:
    """Test ConsentRecord ORM model."""

    def test_consent_creation(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """ConsentRecord can be created."""
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.GRANTED.value,
        )
        test_db_session.add(consent)
        test_db_session.flush()
        assert consent.id is not None
        assert consent.status == "GRANTED"
        assert consent.revoked_at is None
        assert consent.granted_at is not None

    def test_consent_with_scope(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """ConsentRecord can store scope JSON."""
        scope = {"category": ["PREFERENCE", "FACT"], "memory_id": None}
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.SCENE_EXECUTION.value,
            scope_json=json.dumps(scope),
            status=ConsentStatus.GRANTED.value,
        )
        test_db_session.add(consent)
        test_db_session.flush()
        parsed = json.loads(consent.scope_json) if consent.scope_json else {}
        assert "PREFERENCE" in parsed["category"]
        assert "FACT" in parsed["category"]

    def test_consent_with_expiry(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """ConsentRecord can have expires_at."""
        future = utc_now() + timedelta(hours=24)
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.RECOMMENDATION.value,
            expires_at=future,
            status=ConsentStatus.GRANTED.value,
        )
        test_db_session.add(consent)
        test_db_session.flush()
        assert consent.expires_at is not None
        assert consent.expires_at > utc_now()

    def test_all_purpose_values(self) -> None:
        """All purpose enum values are correct."""
        assert ConsentPurpose.CHAT_REPLY == "chat_reply"
        assert ConsentPurpose.SCENE_EXECUTION == "scene_execution"
        assert ConsentPurpose.MEMORY_REVIEW == "memory_review"
        assert ConsentPurpose.RECOMMENDATION == "recommendation"

    def test_consent_status_enum(self) -> None:
        assert ConsentStatus.GRANTED == "GRANTED"
        assert ConsentStatus.REVOKED == "REVOKED"


class TestConsentRepository:
    """Test ConsentRepository."""

    def test_get_active_returns_granted(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """get_active returns active (non-expired, non-revoked) consent."""
        repo = ConsentRepository(test_db_session)
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.GRANTED.value,
        )
        repo.create(consent)
        test_db_session.flush()

        found = repo.get_active(test_user.id, test_agent.id, "chat_reply")
        assert found is not None
        assert found.id == consent.id

    def test_get_active_excludes_expired(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """get_active excludes expired consents."""
        repo = ConsentRepository(test_db_session)
        past = utc_now() - timedelta(hours=1)
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.GRANTED.value,
            expires_at=past,
        )
        repo.create(consent)
        test_db_session.flush()

        found = repo.get_active(test_user.id, test_agent.id, "chat_reply")
        assert found is None

    def test_get_active_excludes_revoked(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """get_active excludes revoked consents."""
        repo = ConsentRepository(test_db_session)
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.REVOKED.value,
            revoked_at=utc_now(),
        )
        repo.create(consent)
        test_db_session.flush()

        found = repo.get_active(test_user.id, test_agent.id, "chat_reply")
        assert found is None

    def test_revoke_sets_status_and_revoked_at(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """revoke() sets status to REVOKED and revoked_at."""
        repo = ConsentRepository(test_db_session)
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.GRANTED.value,
        )
        repo.create(consent)
        test_db_session.flush()

        repo.revoke(consent)
        test_db_session.flush()
        assert consent.status == "REVOKED"
        assert consent.revoked_at is not None

    def test_list_by_grantor(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """list_by_grantor returns all consents for a user."""
        repo = ConsentRepository(test_db_session)
        for purpose in ["chat_reply", "scene_execution", "recommendation"]:
            consent = ConsentRecord(
                grantor_user_id=test_user.id,
                grantee_agent_id=test_agent.id,
                purpose=purpose,
                status=ConsentStatus.GRANTED.value,
            )
            repo.create(consent)
        test_db_session.flush()

        consents = repo.list_by_grantor(test_user.id)
        assert len(consents) == 3
