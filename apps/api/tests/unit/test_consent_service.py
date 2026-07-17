"""P6-08: Consent service tests (grant/check/revoke/expire).

Tests:
- grant then check returns True.
- revoked then check returns False.
- expired then check returns False.
- wrong purpose returns False.
- wrong category in scope returns False.
- grant is idempotent (duplicate grant returns existing).
"""
from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.agents.models import Agent, AgentType, DelegationLevel
from src.modules.memories.consent import (
    check_consent,
    grant_consent,
    list_consents,
    revoke_consent,
)
from src.modules.memories.exceptions import ConsentNotFoundError
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="consent-svc@example.com",
        password_hash="fake-hash",
        display_name="Consent Svc User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def test_agent(test_db_session: Session, test_user: User) -> Agent:
    agent = Agent(
        owner_user_id=test_user.id,
        type=AgentType.PERSONAL.value,
        name="Consent Svc Agent",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    test_db_session.add(agent)
    test_db_session.flush()
    return agent


class TestConsentGrant:
    """Test consent grant."""

    def test_grant_returns_consent(self, test_db_session: Session, test_user: User, test_agent: Agent) -> None:
        """Grant returns a consent record."""
        result = grant_consent(
            grantor_id=test_user.id,
            agent_id=test_agent.id,
            purpose="chat_reply",
            session=test_db_session,
        )
        assert result["purpose"] == "chat_reply"
        assert result["status"] == "GRANTED"
        assert result["id"] is not None

    def test_grant_idempotent(self, test_db_session: Session, test_user: User, test_agent: Agent) -> None:
        """Duplicate grant returns existing consent."""
        r1 = grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        r2 = grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        assert r1["id"] == r2["id"]

    def test_grant_with_scope(self, test_db_session: Session, test_user: User, test_agent: Agent) -> None:
        """Grant with scope stores the scope."""
        result = grant_consent(
            grantor_id=test_user.id,
            agent_id=test_agent.id,
            purpose="scene_execution",
            session=test_db_session,
            scope={"category": ["PREFERENCE"]},
        )
        assert result["scope"] is not None
        assert "PREFERENCE" in result["scope"]["category"]

    def test_grant_with_expiry(self, test_db_session: Session, test_user: User, test_agent: Agent) -> None:
        """Grant with expiry stores the expiry."""
        future = utc_now() + timedelta(hours=24)
        result = grant_consent(
            grantor_id=test_user.id,
            agent_id=test_agent.id,
            purpose="recommendation",
            session=test_db_session,
            expires_at=future,
        )
        assert result["expires_at"] is not None


class TestConsentCheck:
    """Test consent check."""

    def test_grant_then_check_true(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """After granting, check returns True."""
        grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        assert check_consent(test_user.id, test_agent.id, "chat_reply", test_db_session) is True

    def test_revoked_then_check_false(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """After revoking, check returns False."""
        result = grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        revoke_consent(test_user.id, UUID(result["id"]), test_db_session)
        assert check_consent(test_user.id, test_agent.id, "chat_reply", test_db_session) is False

    def test_expired_then_check_false(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Expired consent returns False on check."""
        past = utc_now() - timedelta(hours=1)
        grant_consent(
            test_user.id,
            test_agent.id,
            "chat_reply",
            test_db_session,
            expires_at=past,
        )
        assert check_consent(test_user.id, test_agent.id, "chat_reply", test_db_session) is False

    def test_wrong_purpose_false(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Wrong purpose returns False."""
        grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        assert check_consent(test_user.id, test_agent.id, "scene_execution", test_db_session) is False

    def test_wrong_category_in_scope_false(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Wrong category in scope returns False."""
        grant_consent(
            test_user.id,
            test_agent.id,
            "chat_reply",
            test_db_session,
            scope={"category": ["PREFERENCE"]},
        )
        assert check_consent(
            test_user.id, test_agent.id, "chat_reply", test_db_session, category="FACT"
        ) is False

    def test_correct_category_in_scope_true(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Correct category in scope returns True."""
        grant_consent(
            test_user.id,
            test_agent.id,
            "chat_reply",
            test_db_session,
            scope={"category": ["PREFERENCE", "FACT"]},
        )
        assert check_consent(
            test_user.id, test_agent.id, "chat_reply", test_db_session, category="PREFERENCE"
        ) is True

    def test_no_consent_at_all_false(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """No consent at all returns False."""
        assert check_consent(test_user.id, test_agent.id, "chat_reply", test_db_session) is False


class TestConsentRevoke:
    """Test consent revoke."""

    def test_revoke_success(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Revoke works and takes effect immediately."""
        result = grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        revoke_consent(test_user.id, UUID(result["id"]), test_db_session)
        assert check_consent(test_user.id, test_agent.id, "chat_reply", test_db_session) is False

    def test_revoke_not_found(self, test_db_session: Session, test_user: User) -> None:
        """Revoking non-existent consent raises."""
        with pytest.raises(ConsentNotFoundError):
            revoke_consent(test_user.id, uuid4(), test_db_session)

    def test_revoke_wrong_user(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Revoking another user's consent raises."""
        result = grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        other_user = User(
            email="wrong@example.com",
            password_hash="fake",
            display_name="Wrong",
            global_role=GlobalRole.STUDENT.value,
            status=UserStatus.ACTIVE.value,
        )
        test_db_session.add(other_user)
        test_db_session.flush()
        with pytest.raises(ConsentNotFoundError):
            revoke_consent(other_user.id, UUID(result["id"]), test_db_session)


class TestConsentList:
    """Test consent list."""

    def test_list_consents(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """List returns all consents for the user."""
        grant_consent(test_user.id, test_agent.id, "chat_reply", test_db_session)
        grant_consent(test_user.id, test_agent.id, "recommendation", test_db_session)
        result = list_consents(test_user.id, test_db_session)
        assert result["total"] == 2

    def test_list_consents_empty(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Empty list when no consents."""
        result = list_consents(test_user.id, test_db_session)
        assert result["total"] == 0
