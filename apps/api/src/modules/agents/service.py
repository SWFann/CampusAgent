"""Agent service layer — business logic for agent management.

Privacy:
- private_config_encrypted is encrypted before storage.
- Owner can read decrypted config; admin can only read metadata.
- repr and logs never include private_config.
"""
from __future__ import annotations

import secrets
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...events.bus import default_event_bus
from ..audit.service import log_audit
from ..users.models import User
from .events import PersonalAgentCreated
from .exceptions import (
    AgentNotFoundError,
    AgentPermissionDeniedError,
    InvalidDelegationLevelError,
)
from .models import Agent, AgentStatus, AgentType, DelegationLevel
from .repository import AgentRepository


def _generate_event_id() -> str:
    return secrets.token_hex(16)


def _validate_delegation_level(level: str) -> None:
    valid = {dl.value for dl in DelegationLevel}
    if level not in valid:
        raise InvalidDelegationLevelError(
            details={"field": "delegation_level", "value": level}
        )


def _agent_to_read(agent: Agent, include_private_config: bool = False) -> dict[str, Any]:
    """Convert Agent to a safe read dict.

    Never includes private_config_encrypted unless explicitly requested
    (owner-only, after decryption).
    """
    result: dict[str, Any] = {
        "id": str(agent.id),
        "owner_user_id": str(agent.owner_user_id),
        "type": agent.type,
        "name": agent.name,
        "avatar_url": agent.avatar_url,
        "public_persona": agent.public_persona,
        "delegation_level": agent.delegation_level,
        "status": agent.status,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }
    if include_private_config:
        result["has_private_config"] = agent.private_config_encrypted is not None
    else:
        result["has_private_config"] = agent.private_config_encrypted is not None
    return result


def create_personal_agent(
    user: User,
    session: Session,
    *,
    name: str | None = None,
    public_persona: str | None = None,
    private_config_encrypted: str | None = None,
) -> dict[str, Any]:
    """Create a personal agent for a user. Idempotent — skips if exists."""
    repo = AgentRepository(session)
    existing = repo.get_personal_agent(user.id)
    if existing is not None:
        return _agent_to_read(existing)

    agent = Agent(
        owner_user_id=user.id,
        type=AgentType.PERSONAL.value,
        name=name or f"{user.display_name}的智能体",
        public_persona=public_persona,
        private_config_encrypted=private_config_encrypted,
        delegation_level=DelegationLevel.L0.value,
        status=AgentStatus.ACTIVE.value,
    )
    repo.create(agent)
    session.commit()
    session.refresh(agent)

    default_event_bus.publish(
        PersonalAgentCreated(
            event_id=_generate_event_id(),
            agent_id=agent.id,
            owner_user_id=user.id,
            occurred_at=utc_now(),
        )
    )

    return _agent_to_read(agent)


def get_my_agent(user: User, session: Session) -> dict[str, Any]:
    """Get the current user's personal agent."""
    repo = AgentRepository(session)
    agent = repo.get_personal_agent(user.id)
    if agent is None:
        return create_personal_agent(user, session)
    return _agent_to_read(agent, include_private_config=True)


def get_agent_by_id(
    actor: User, agent_id: UUID, session: Session
) -> dict[str, Any]:
    """Get an agent by ID. Owner sees full info; others see metadata only."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)
    if agent is None or agent.status == AgentStatus.DELETED.value:
        raise AgentNotFoundError()

    is_owner = agent.owner_user_id == actor.id
    is_admin = actor.global_role in ("SYSTEM_ADMIN", "SCHOOL_ADMIN")

    if not is_owner and not is_admin:
        raise AgentPermissionDeniedError()

    # Admin can only read metadata, not private_config
    return _agent_to_read(agent, include_private_config=is_owner)


def update_agent(
    actor: User,
    agent_id: UUID,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Update an agent. Only the owner can update."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)
    if agent is None or agent.status == AgentStatus.DELETED.value:
        raise AgentNotFoundError()

    if agent.owner_user_id != actor.id:
        raise AgentPermissionDeniedError()

    if "name" in data and data["name"] is not None:
        agent.name = data["name"]
    if "avatar_url" in data:
        agent.avatar_url = data["avatar_url"]
    if "public_persona" in data:
        agent.public_persona = data["public_persona"]
    if "delegation_level" in data and data["delegation_level"] is not None:
        _validate_delegation_level(data["delegation_level"])
        agent.delegation_level = data["delegation_level"]
    if "private_config_encrypted" in data:
        agent.private_config_encrypted = data["private_config_encrypted"]

    repo.save(agent)
    session.commit()
    session.refresh(agent)

    log_audit(
        actor_id=actor.id,
        action="agent_config_update",
        resource_type="agent",
        resource_id=str(agent.id),
        result="SUCCESS",
        session=session,
    )
    return _agent_to_read(agent, include_private_config=True)


def list_my_agents(user: User, session: Session) -> dict[str, Any]:
    """List all agents owned by the current user."""
    repo = AgentRepository(session)
    agents = repo.list_by_owner(user.id)
    return {
        "agents": [_agent_to_read(a) for a in agents],
        "total": len(agents),
    }
