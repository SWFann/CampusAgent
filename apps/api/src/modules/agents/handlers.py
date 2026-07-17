"""Event handler for auto-creating personal agents on user registration.

P6-02: Listens for UserRegistered events and creates a personal agent.
- Idempotent: skips if agent already exists.
- Handler failures are logged but don't break registration.
"""
from __future__ import annotations

import logging

from ...events.bus import DomainEvent, default_event_bus
from ..users.events import UserRegistered

logger = logging.getLogger("campus_agent.agents")


class PersonalAgentAutoCreateHandler:
    """Event handler that auto-creates a personal agent on UserRegistered.

    Idempotent: if a personal agent already exists, the event is a no-op.
    Handler failures are caught and logged — they do NOT break the
    registration flow (the event bus already catches exceptions).
    """

    def handle(self, event: DomainEvent) -> None:
        """Handle UserRegistered event by creating a personal agent."""
        if not isinstance(event, UserRegistered):
            return

        try:
            from ...config import settings
            from ...db.session import create_engine_from_settings, create_sessionmaker
            from ..agents.service import create_personal_agent
            from ..users.repository import UserRepository

            engine = create_engine_from_settings(settings)
            session_factory = create_sessionmaker(engine)
            session = session_factory()

            try:
                user = UserRepository(session).get_by_id(event.user_id)
                if user is None:
                    logger.warning(
                        "agent.auto_create.user_not_found",
                        extra={"user_id": str(event.user_id)},
                    )
                    return

                result = create_personal_agent(user, session)
                logger.info(
                    "agent.auto_create.success",
                    extra={
                        "agent_id": result.get("id"),
                        "owner_user_id": str(event.user_id),
                    },
                )
            finally:
                session.close()
                engine.dispose()

        except Exception as exc:
            logger.error(
                "agent.auto_create.failed",
                extra={"user_id": str(event.user_id), "error": str(exc)},
            )


def register_personal_agent_handler() -> None:
    """Register the PersonalAgentAutoCreateHandler on the event bus."""
    handler = PersonalAgentAutoCreateHandler()
    default_event_bus.subscribe(UserRegistered, handler)
    logger.info("agent.auto_create.handler_registered")
