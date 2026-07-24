"""Agent repository for database access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from .models import (
    Agent,
    AgentRun,
    AgentStatus,
    WorkspaceMessage,
    WorkspaceThread,
    WorkspaceThreadStatus,
)


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


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_thread(self, thread: WorkspaceThread) -> WorkspaceThread:
        self._session.add(thread)
        self._session.flush()
        return thread

    def list_threads(self, owner_user_id: UUID) -> list[WorkspaceThread]:
        return (
            self._session.query(WorkspaceThread)
            .filter(
                WorkspaceThread.owner_user_id == owner_user_id,
                WorkspaceThread.status != WorkspaceThreadStatus.DELETED.value,
            )
            .order_by(WorkspaceThread.updated_at.desc())
            .all()
        )

    def get_thread(self, thread_id: UUID, owner_user_id: UUID) -> WorkspaceThread | None:
        return (
            self._session.query(WorkspaceThread)
            .options(selectinload(WorkspaceThread.messages))
            .filter(
                WorkspaceThread.id == thread_id,
                WorkspaceThread.owner_user_id == owner_user_id,
                WorkspaceThread.status != WorkspaceThreadStatus.DELETED.value,
            )
            .first()
        )

    def add_message(self, message: WorkspaceMessage) -> WorkspaceMessage:
        self._session.add(message)
        self._session.flush()
        return message
