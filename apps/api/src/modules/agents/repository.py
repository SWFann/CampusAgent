"""Agent repository for database access."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from .models import Agent, AgentRun, AgentStatus


class AgentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, agent: Agent) -> Agent:
        self._session.add(agent)
        self._session.flush()
        return agent

    def get_by_id(self, agent_id: UUID) -> Agent | None:
        return self._session.get(Agent, agent_id)

    def get_personal_agent(self, user_id: UUID) -> Agent | None:
        return (
            self._session.query(Agent)
            .filter(
                Agent.owner_user_id == user_id,
                Agent.type == "PERSONAL",
                Agent.status != AgentStatus.DELETED.value,
            )
            .first()
        )

    def list_by_owner(self, user_id: UUID) -> list[Agent]:
        return (
            self._session.query(Agent)
            .filter(
                Agent.owner_user_id == user_id,
                Agent.status != AgentStatus.DELETED.value,
            )
            .all()
        )

    def save(self, agent: Agent) -> Agent:
        self._session.flush()
        return agent

    def soft_delete(self, agent: Agent) -> None:
        agent.status = AgentStatus.DELETED.value

    def create_run(self, run: AgentRun) -> AgentRun:
        self._session.add(run)
        self._session.flush()
        return run
