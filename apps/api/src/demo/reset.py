"""P11-03: Demo-only reset service.

Deletes only demo-namespace data so that non-demo rows are preserved.
After reset, ``seed_demo`` can be called again to restore the fixed
dataset.

Safety:
- ``reset_demo`` calls ``assert_demo_env`` first; production fails-closed.
- Demo rows are identified by demo emails and demo org slug suffix —
  never by deleting all rows in a table.
- Hard-deletes demo rows (they are fictional) so the DB returns to a
  clean state suitable for a fresh seed.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from ..config import Settings
from ..modules.agents.models import Agent, AgentRun
from ..modules.audit.models import AuditLog
from ..modules.auth.models import AuthSession, RefreshToken
from ..modules.contacts.models import ContactRelationship
from ..modules.conversations.models import (
    Conversation,
    ConversationParticipant,
    Message,
)
from ..modules.organizations.models import Organization, OrganizationMembership
from ..modules.scenes.models import (
    PrivateSubmission,
    SceneCandidate,
    SceneInstance,
    SceneParticipant,
    SceneResult,
    SceneVote,
)
from ..modules.users.models import StudentProfile, User
from .data import (
    DEMO_ORG_SLUG_SUFFIX,
    DEMO_SCENE_IDEMPOTENCY_KEY,
    demo_emails,
    is_demo_email,
    is_demo_org_slug,
)
from .security import assert_demo_env

logger = logging.getLogger("campus_agent.demo.reset")


def _delete_count(session: Session, stmt: Any) -> int:
    """Execute a DELETE statement and return the affected row count.

    SQLAlchemy's type stubs annotate ``Session.execute(delete(...))`` as
    returning ``Result[Any]``, which lacks ``rowcount``. At runtime the
    result is a ``CursorResult`` that does expose ``rowcount``. This
    helper centralises the cast so call sites stay readable.
    """
    result = session.execute(stmt)
    return cast(CursorResult[Any], result).rowcount


def _collect_demo_user_ids(session: Session) -> list[Any]:
    emails = demo_emails()
    if not emails:
        return []
    stmt = select(User.id).where(User.email.in_(emails))
    return list(session.execute(stmt).scalars().all())


def _collect_demo_org_ids(session: Session) -> list[Any]:
    stmt = select(Organization.id).where(
        Organization.slug.like(f"%{DEMO_ORG_SLUG_SUFFIX}")
    )
    return list(session.execute(stmt).scalars().all())


def _collect_demo_scene_ids(session: Session) -> list[Any]:
    stmt = select(SceneInstance.id).where(
        SceneInstance.idempotency_key == DEMO_SCENE_IDEMPOTENCY_KEY
    )
    return list(session.execute(stmt).scalars().all())


def _collect_demo_conversation_ids(
    session: Session,
    demo_user_ids: list[Any],
) -> list[Any]:
    if not demo_user_ids:
        return []
    created_stmt = select(Conversation.id).where(
        Conversation.created_by.in_(demo_user_ids)
    )
    participated_stmt = select(ConversationParticipant.conversation_id).where(
        ConversationParticipant.participant_user_id.in_(demo_user_ids)
    )
    conversation_ids = set(session.execute(created_stmt).scalars().all())
    conversation_ids.update(session.execute(participated_stmt).scalars().all())
    return list(conversation_ids)


def _delete_scene_graph(session: Session, scene_ids: list[Any]) -> tuple[int, int]:
    """Delete scene child rows before deleting SceneInstance rows.

    Returns:
        ``(deleted_preferences, deleted_scenes)``.
    """
    if not scene_ids:
        return 0, 0

    deleted_preferences = _delete_count(
        session,
        delete(PrivateSubmission).where(
            PrivateSubmission.scene_instance_id.in_(scene_ids)
        ),
    )
    session.execute(
        delete(SceneVote).where(
            SceneVote.scene_instance_id.in_(scene_ids)
        )
    )
    session.execute(
        delete(SceneResult).where(
            SceneResult.scene_instance_id.in_(scene_ids)
        )
    )
    session.execute(
        delete(SceneCandidate).where(
            SceneCandidate.scene_instance_id.in_(scene_ids)
        )
    )
    session.execute(
        delete(SceneParticipant).where(
            SceneParticipant.scene_instance_id.in_(scene_ids)
        )
    )
    deleted_scenes = _delete_count(
        session,
        delete(SceneInstance).where(
            SceneInstance.id.in_(scene_ids)
        ),
    )
    return deleted_preferences, deleted_scenes


def reset_demo(session: Session, settings: Settings) -> dict[str, Any]:
    """Delete all demo-namespace data; preserve non-demo rows.

    Args:
        session: A SQLAlchemy Session. Caller commits/rolls back.
        settings: Application settings — used for the env guard.

    Returns:
        Summary dict: deleted_users, deleted_organizations,
        deleted_sessions, deleted_messages, deleted_scenes,
        deleted_preferences.

    Raises:
        DemoResetForbiddenError: if APP_ENV is not development/test.
    """
    assert_demo_env(settings)

    demo_user_ids = _collect_demo_user_ids(session)
    demo_org_ids = _collect_demo_org_ids(session)
    demo_scene_ids = _collect_demo_scene_ids(session)
    demo_conv_ids = _collect_demo_conversation_ids(session, demo_user_ids)

    deleted_preferences = 0
    deleted_scenes = 0
    deleted_messages = 0
    deleted_sessions = 0

    # 1. Scene data (votes, submissions, candidates, results, participants,
    #    instances) for the demo scene.
    if demo_scene_ids:
        preferences_count, scenes_count = _delete_scene_graph(
            session,
            demo_scene_ids,
        )
        deleted_preferences += preferences_count
        deleted_scenes += scenes_count

    # 2. Conversation data for the demo conversation.
    if demo_conv_ids:
        # Defensive: also delete any SceneInstance that references these
        # conversations, in case they weren't caught by demo_scene_ids above
        # (e.g. missing idempotency_key on prior seed runs).
        extra_scene_ids = list(
            session.execute(
                select(SceneInstance.id).where(
                    SceneInstance.conversation_id.in_(demo_conv_ids)
                )
            ).scalars().all()
        )
        preferences_count, scenes_count = _delete_scene_graph(
            session,
            extra_scene_ids,
        )
        deleted_preferences += preferences_count
        deleted_scenes += scenes_count
        deleted_messages += _delete_count(
            session,
            delete(Message).where(Message.conversation_id.in_(demo_conv_ids)),
        )
        session.execute(
            delete(ConversationParticipant).where(
                ConversationParticipant.conversation_id.in_(demo_conv_ids)
            )
        )
        session.execute(
            delete(Conversation).where(Conversation.id.in_(demo_conv_ids))
        )

    # 3. Memberships for demo orgs or demo users.
    if demo_org_ids:
        session.execute(
            delete(OrganizationMembership).where(
                OrganizationMembership.organization_id.in_(demo_org_ids)
            )
        )
    if demo_user_ids:
        session.execute(
            delete(OrganizationMembership).where(
                OrganizationMembership.user_id.in_(demo_user_ids)
            )
        )

    # 4. Demo organisations.
    deleted_organizations = 0
    if demo_org_ids:
        deleted_organizations = _delete_count(
            session,
            delete(Organization).where(Organization.id.in_(demo_org_ids)),
        )
    else:
        # Still delete any stray org with the demo slug suffix.
        deleted_organizations = _delete_count(
            session,
            delete(Organization).where(
                Organization.slug.like(f"%{DEMO_ORG_SLUG_SUFFIX}")
            ),
        )

    # 5. Agent runs and agents owned by demo users.
    if demo_user_ids:
        session.execute(
            delete(AgentRun).where(AgentRun.actor_user_id.in_(demo_user_ids))
        )
        session.execute(
            delete(Agent).where(Agent.owner_user_id.in_(demo_user_ids))
        )

    # 6. Audit logs authored by demo users (metadata only, safe to clear).
    if demo_user_ids:
        session.execute(
            delete(AuditLog).where(AuditLog.actor_user_id.in_(demo_user_ids))
        )

    # 7. Refresh tokens and auth sessions for demo users.
    if demo_user_ids:
        session.execute(
            delete(ContactRelationship).where(
                (ContactRelationship.requester_id.in_(demo_user_ids))
                | (ContactRelationship.addressee_id.in_(demo_user_ids))
            )
        )
        deleted_sessions += _delete_count(
            session,
            delete(RefreshToken).where(
                RefreshToken.user_id.in_(demo_user_ids)
            ),
        )
        deleted_sessions += _delete_count(
            session,
            delete(AuthSession).where(AuthSession.user_id.in_(demo_user_ids)),
        )

    # 8. Student profiles and users.
    deleted_users = 0
    if demo_user_ids:
        session.execute(
            delete(StudentProfile).where(
                StudentProfile.user_id.in_(demo_user_ids)
            )
        )
        deleted_users = _delete_count(
            session,
            delete(User).where(User.id.in_(demo_user_ids)),
        )

    session.flush()
    summary: dict[str, Any] = {
        "deleted_users": deleted_users,
        "deleted_organizations": deleted_organizations,
        "deleted_sessions": deleted_sessions,
        "deleted_messages": deleted_messages,
        "deleted_scenes": deleted_scenes,
        "deleted_preferences": deleted_preferences,
    }
    logger.info("demo.reset.complete", extra=summary)
    return summary


def get_demo_status(session: Session) -> dict[str, Any]:
    """Return a non-sensitive status snapshot of the demo dataset.

    Used by the internal status endpoint and CLI. Counts only — no
    private content, emails, or tokens are returned.
    """
    emails = demo_emails()
    user_count = 0
    if emails:
        user_rows = session.execute(
            select(User).where(User.email.in_(emails))
        ).scalars().all()
        user_count = len(user_rows)

    org_rows = session.execute(
        select(Organization).where(
            Organization.slug.like(f"%{DEMO_ORG_SLUG_SUFFIX}")
        )
    ).scalars().all()
    org_count = len(org_rows)

    scene_rows = session.execute(
        select(SceneInstance).where(
            SceneInstance.idempotency_key == DEMO_SCENE_IDEMPOTENCY_KEY
        )
    ).scalars().all()
    scene_count = len(scene_rows)

    return {
        "namespace": "demo",
        "users_present": user_count,
        "organizations_present": org_count,
        "scenes_present": scene_count,
        "is_demo_email_check": is_demo_email("demo_alice@example.com"),
        "is_demo_org_slug_check": is_demo_org_slug("x-demo-lab"),
    }
