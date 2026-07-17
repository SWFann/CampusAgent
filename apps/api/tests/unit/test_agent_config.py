"""P6-03: Agent configuration API tests.

Tests:
- GET /agents/me returns the current user's agent.
- GET /agents/{id} returns metadata for owner.
- GET /agents/{id} returns metadata only for admin (no private_config).
- PATCH /agents/{id} updates agent config (owner only).
- Non-owner cannot read agent details.
- Admin cannot read private_config.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.modules.agents.exceptions import (
    AgentNotFoundError,
    AgentPermissionDeniedError,
    InvalidDelegationLevelError,
)
from src.modules.agents.models import Agent
from src.modules.agents.service import (
    create_personal_agent,
    get_agent_by_id,
    get_my_agent,
    update_agent,
)
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def owner(test_db_session: Session) -> User:
    user = User(
        email="owner@example.com",
        password_hash="fake-hash",
        display_name="Owner",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def other_user(test_db_session: Session) -> User:
    user = User(
        email="other@example.com",
        password_hash="fake-hash",
        display_name="Other",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def admin_user(test_db_session: Session) -> User:
    user = User(
        email="admin@example.com",
        password_hash="fake-hash",
        display_name="Admin",
        global_role=GlobalRole.SYSTEM_ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def owner_agent(test_db_session: Session, owner: User) -> Agent:
    create_personal_agent(owner, test_db_session)
    repo = AgentRepository(test_db_session)
    return repo.get_personal_agent(owner.id)  # type: ignore[return-value]


from src.modules.agents.repository import AgentRepository  # noqa: E402


class TestAgentConfig:
    """Test agent configuration service."""

    def test_get_my_agent(self, test_db_session: Session, owner: User) -> None:
        """Owner can get their own agent."""
        create_personal_agent(owner, test_db_session)
        result = get_my_agent(owner, test_db_session)
        assert result["type"] == "PERSONAL"
        assert result["owner_user_id"] == str(owner.id)

    def test_get_my_agent_not_found(self, test_db_session: Session, owner: User) -> None:
        """If no agent exists, raises AgentNotFoundError."""
        with pytest.raises(AgentNotFoundError):
            get_my_agent(owner, test_db_session)

    def test_get_agent_by_id_owner(
        self, test_db_session: Session, owner: User, owner_agent: Agent
    ) -> None:
        """Owner can get their agent by ID."""
        result = get_agent_by_id(owner, owner_agent.id, test_db_session)
        assert result["id"] == str(owner_agent.id)
        assert result["has_private_config"] is False  # No private config set

    def test_get_agent_by_id_admin_no_private_config(
        self, test_db_session: Session, admin_user: User, owner: User, owner_agent: Agent
    ) -> None:
        """Admin can read agent metadata but not private_config."""
        # Set a private config
        owner_agent.private_config_encrypted = "encrypted-secret"
        test_db_session.flush()

        result = get_agent_by_id(admin_user, owner_agent.id, test_db_session)
        assert result["id"] == str(owner_agent.id)
        # Admin should only see has_private_config=True, not the value
        assert result["has_private_config"] is True
        assert "private_config_encrypted" not in result
        assert "encrypted-secret" not in str(result)

    def test_get_agent_by_id_non_owner_denied(
        self, test_db_session: Session, other_user: User, owner_agent: Agent
    ) -> None:
        """Non-owner, non-admin cannot read agent."""
        with pytest.raises(AgentPermissionDeniedError):
            get_agent_by_id(other_user, owner_agent.id, test_db_session)

    def test_update_agent_owner(
        self, test_db_session: Session, owner: User, owner_agent: Agent
    ) -> None:
        """Owner can update agent."""
        result = update_agent(
            owner,
            owner_agent.id,
            {"name": "New Name", "delegation_level": "L1"},
            test_db_session,
        )
        assert result["name"] == "New Name"
        assert result["delegation_level"] == "L1"

    def test_update_agent_non_owner_denied(
        self, test_db_session: Session, other_user: User, owner_agent: Agent
    ) -> None:
        """Non-owner cannot update agent."""
        with pytest.raises(AgentPermissionDeniedError):
            update_agent(other_user, owner_agent.id, {"name": "Hacked"}, test_db_session)

    def test_update_agent_invalid_delegation(
        self, test_db_session: Session, owner: User, owner_agent: Agent
    ) -> None:
        """L4 delegation level is rejected on update."""
        with pytest.raises(InvalidDelegationLevelError):
            update_agent(owner, owner_agent.id, {"delegation_level": "L4"}, test_db_session)

    def test_update_agent_not_found(self, test_db_session: Session, owner: User) -> None:
        """Updating non-existent agent raises."""
        with pytest.raises(AgentNotFoundError):
            update_agent(owner, uuid4(), {"name": "X"}, test_db_session)

    def test_update_agent_private_config(
        self, test_db_session: Session, owner: User, owner_agent: Agent
    ) -> None:
        """Owner can set private_config_encrypted."""
        result = update_agent(
            owner,
            owner_agent.id,
            {"private_config_encrypted": "my-encrypted-config"},
            test_db_session,
        )
        assert result["has_private_config"] is True
        # The actual encrypted value should not be in the response
        assert "my-encrypted-config" not in str(result)

    def test_update_agent_public_persona(
        self, test_db_session: Session, owner: User, owner_agent: Agent
    ) -> None:
        """Owner can update public_persona."""
        result = update_agent(
            owner,
            owner_agent.id,
            {"public_persona": "Friendly assistant"},
            test_db_session,
        )
        assert result["public_persona"] == "Friendly assistant"
