"""P11-02: Idempotent demo seed service.

Creates or updates the fixed demo dataset so that repeated runs produce
the same end state without duplicating rows.

Privacy:
- Passwords are bcrypt-hashed via the P3 password module; plaintext is
  never persisted.
- Private preference bodies are encrypted by the scene service before
  storage (see scenes.privacy.encrypt_payload).
- No real personal data is used — every record is fictional.

Idempotency:
- Users: lookup by email (lowercase); create if missing, update fields
  and password_hash if present.
- Organisations: lookup by slug; create if missing, update if present.
- Memberships: lookup by (org_id, user_id); create if missing.
- Conversation: lookup by title + created_by; create with messages if
  missing, otherwise leave untouched.
- Scene instance: lookup by DEMO_SCENE_IDEMPOTENCY_KEY; if present the
  full lifecycle is skipped, otherwise the scene is run to COMPLETED.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.time import utc_now
from ..modules.auth.passwords import hash_password
from ..modules.conversations.models import (
    Conversation,
    ConversationParticipant,
    ConversationRole,
    ConversationStatus,
    Message,
    ParticipantStatus,
    ParticipantType,
    SenderType,
)
from ..modules.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from ..modules.scenes.coordinator import run_generation_phase
from ..modules.scenes.registry import get_scene_registry
from ..modules.scenes.service import (
    accept_invitation,
    cast_vote,
    create_scene_instance,
    submit_private_preferences,
    transition_state,
)
from ..modules.users.models import StudentProfile, User, UserStatus
from .data import (
    DEMO_CONVERSATION,
    DEMO_MEMBERSHIPS,
    DEMO_MESSAGES,
    DEMO_ORGANIZATIONS,
    DEMO_PASSWORD,
    DEMO_PREFERENCES_BY_PARTICIPANT,
    DEMO_SCENE_IDEMPOTENCY_KEY,
    DEMO_SCENE_PARTICIPANT_KEYS,
    DEMO_USERS,
    DEMO_VOTES,
)

logger = logging.getLogger("campus_agent.demo.seed")


def _ensure_plugin_registered() -> None:
    """Register the dorm dinner plugin if not already registered."""
    from ..modules.scenes.plugins import DormDinnerPlugin

    registry = get_scene_registry()
    with suppress(Exception):
        registry.register(DormDinnerPlugin())


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def _seed_users(session: Session) -> tuple[dict[str, User], dict[str, int]]:
    """Create or update demo users. Returns (key->User, counters)."""
    users: dict[str, User] = {}
    created = 0
    updated = 0
    password_hash = hash_password(DEMO_PASSWORD)

    for demo_user in DEMO_USERS:
        email = demo_user.email.lower()
        stmt = select(User).where(User.email == email)
        user = session.execute(stmt).scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=password_hash,
                display_name=demo_user.display_name,
                global_role=demo_user.global_role,
                status=demo_user.status,
                deleted_at=utc_now() if demo_user.soft_deleted else None,
            )
            session.add(user)
            session.flush()
            profile = StudentProfile(
                user_id=user.id,
                student_no=demo_user.student_no,
                enrollment_year=demo_user.enrollment_year,
                major_name=demo_user.major_name,
                bio=demo_user.bio,
            )
            session.add(profile)
            created += 1
        else:
            user.display_name = demo_user.display_name
            user.global_role = demo_user.global_role
            user.password_hash = password_hash
            if demo_user.soft_deleted:
                user.status = UserStatus.DELETED.value
                user.deleted_at = user.deleted_at or utc_now()
            else:
                user.status = UserStatus.ACTIVE.value
                user.deleted_at = None
            updated += 1

            stmt_p = select(StudentProfile).where(StudentProfile.user_id == user.id)
            existing_profile = session.execute(stmt_p).scalar_one_or_none()
            if existing_profile is None:
                existing_profile = StudentProfile(
                    user_id=user.id,
                    student_no=demo_user.student_no,
                    enrollment_year=demo_user.enrollment_year,
                    major_name=demo_user.major_name,
                    bio=demo_user.bio,
                )
                session.add(existing_profile)
            else:
                existing_profile.student_no = demo_user.student_no
                existing_profile.major_name = demo_user.major_name
                existing_profile.bio = demo_user.bio

        users[demo_user.key] = user

    session.flush()
    return users, {"users_created": created, "users_updated": updated}


# ---------------------------------------------------------------------------
# Organisations
# ---------------------------------------------------------------------------


def _seed_organizations(
    session: Session,
    users: dict[str, User],
) -> tuple[dict[str, Organization], dict[str, int]]:
    """Create or update demo organisations. Returns (key->Org, counters)."""
    orgs: dict[str, Organization] = {}
    created = 0

    admin_user = users["admin"]
    legacy_names = {"project": "2312", "lab": "wnds"}
    for demo_org in DEMO_ORGANIZATIONS:
        stmt = select(Organization).where(Organization.slug == demo_org.slug)
        org = session.execute(stmt).scalar_one_or_none()
        if org is None and demo_org.key in legacy_names:
            org = session.execute(
                select(Organization).where(Organization.name == legacy_names[demo_org.key])
            ).scalar_one_or_none()
            if org is not None:
                org.slug = demo_org.slug

        parent_id = None
        if demo_org.parent_key is not None:
            parent = orgs.get(demo_org.parent_key)
            parent_id = parent.id if parent else None

        if org is None:
            org = Organization(
                name=demo_org.name,
                slug=demo_org.slug,
                type=demo_org.type,
                parent_id=parent_id,
                description=demo_org.description,
                visibility=demo_org.visibility,
                join_policy=demo_org.join_policy,
                status=OrganizationStatus.ACTIVE.value,
                created_by=admin_user.id,
            )
            session.add(org)
            session.flush()
            created += 1
        else:
            org.name = demo_org.name
            org.type = demo_org.type
            org.parent_id = parent_id
            org.description = demo_org.description
            org.visibility = demo_org.visibility
            org.join_policy = demo_org.join_policy

        orgs[demo_org.key] = org

    session.flush()
    return orgs, {"organizations_created": created}


# ---------------------------------------------------------------------------
# Memberships
# ---------------------------------------------------------------------------


def _seed_memberships(
    session: Session,
    users: dict[str, User],
    orgs: dict[str, Organization],
) -> dict[str, int]:
    """Create demo memberships idempotently."""
    created = 0
    for m in DEMO_MEMBERSHIPS:
        user = users.get(m.user_key)
        org = orgs.get(m.org_key)
        if user is None or org is None:
            continue

        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == user.id,
        )
        existing = session.execute(stmt).scalar_one_or_none()
        if existing is None:
            membership = OrganizationMembership(
                organization_id=org.id,
                user_id=user.id,
                role=m.role,
                status=m.status,
                joined_at=utc_now(),
            )
            session.add(membership)
            created += 1
        else:
            existing.role = m.role
            existing.status = m.status

    session.flush()
    return {"memberships_created": created}


# ---------------------------------------------------------------------------
# Conversation and messages
# ---------------------------------------------------------------------------


def _seed_conversation(
    session: Session,
    users: dict[str, User],
) -> tuple[Conversation | None, dict[str, int]]:
    """Create the demo group conversation with seed messages."""
    creator = users.get(DEMO_CONVERSATION.participant_keys[0])
    if creator is None:
        return None, {"conversations_created": 0, "messages_created": 0}

    stmt = select(Conversation).where(
        Conversation.title == DEMO_CONVERSATION.title,
        Conversation.created_by == creator.id,
        Conversation.type == DEMO_CONVERSATION.type,
    )
    conversation = session.execute(stmt).scalar_one_or_none()

    messages_created = 0
    if conversation is None:
        conversation = Conversation(
            type=DEMO_CONVERSATION.type,
            title=DEMO_CONVERSATION.title,
            created_by=creator.id,
            status=ConversationStatus.ACTIVE.value,
        )
        session.add(conversation)
        session.flush()

        for key in DEMO_CONVERSATION.participant_keys:
            participant = users.get(key)
            if participant is None:
                continue
            role = (
                ConversationRole.OWNER.value
                if key == DEMO_CONVERSATION.participant_keys[0]
                else ConversationRole.MEMBER.value
            )
            cp = ConversationParticipant(
                conversation_id=conversation.id,
                participant_type=ParticipantType.USER.value,
                participant_user_id=participant.id,
                role=role,
                status=ParticipantStatus.ACTIVE.value,
            )
            session.add(cp)

        for seq, msg in enumerate(DEMO_MESSAGES, start=1):
            sender = users.get(msg["sender_key"])
            if sender is None:
                continue
            message = Message(
                conversation_id=conversation.id,
                sender_type=SenderType.USER.value,
                sender_user_id=sender.id,
                message_type=msg["message_type"],
                content=msg["content"],
                sequence=seq,
                status="ACTIVE",
            )
            session.add(message)
            messages_created += 1

        session.flush()
        return conversation, {
            "conversations_created": 1,
            "messages_created": messages_created,
        }

    return conversation, {"conversations_created": 0, "messages_created": 0}


# ---------------------------------------------------------------------------
# Dorm dinner scene
# ---------------------------------------------------------------------------


def _seed_dinner_scene(
    session: Session,
    users: dict[str, User],
    conversation: Conversation | None,
    organizations: dict[str, Organization],
) -> dict[str, int]:
    """Run the demo dorm-dinner scene to COMPLETED idempotently."""
    from ..modules.scenes.repository import SceneInstanceRepository

    instance_repo = SceneInstanceRepository(session)
    existing = instance_repo.get_by_idempotency_key(DEMO_SCENE_IDEMPOTENCY_KEY)
    if existing is not None:
        return {"scenes_created": 0, "votes_created": 0, "preferences_created": 0}

    _ensure_plugin_registered()

    creator_key = DEMO_SCENE_PARTICIPANT_KEYS[0]
    creator = users[creator_key]
    participant_ids = [users[key].id for key in DEMO_SCENE_PARTICIPANT_KEYS if key in users]

    data: dict[str, Any] = {
        "scene_key": "dorm_dinner",
        "participant_user_ids": participant_ids,
        "idempotency_key": DEMO_SCENE_IDEMPOTENCY_KEY,
    }
    dorm = organizations.get("dorm")
    if dorm is not None:
        data["organization_id"] = dorm.id
    if conversation is not None:
        data["conversation_id"] = conversation.id

    result = create_scene_instance(creator, data, session)
    instance_id = UUID(result["id"])

    transition_state(creator, instance_id, "publish", session)
    transition_state(creator, instance_id, "start_collecting", session)

    for key in DEMO_SCENE_PARTICIPANT_KEYS:
        if key == creator_key:
            continue
        participant = users.get(key)
        if participant is not None:
            accept_invitation(participant, instance_id, session)

    preferences_created = 0
    for key in DEMO_SCENE_PARTICIPANT_KEYS:
        participant = users.get(key)
        prefs = DEMO_PREFERENCES_BY_PARTICIPANT.get(key)
        if participant is not None and prefs is not None:
            submit_private_preferences(participant, instance_id, prefs, session)
            preferences_created += 1

    transition_state(creator, instance_id, "start_processing", session)
    run_generation_phase(instance_id, session)
    transition_state(creator, instance_id, "candidates_ready", session)

    votes_created = 0
    from ..modules.scenes.models import CandidateStatus, SceneCandidate

    # Query for voteable candidates: ACTIVE or SELECTED (the top-ranked
    # candidate may have been marked SELECTED by the generation phase).
    voteable_statuses = [
        CandidateStatus.ACTIVE.value,
        CandidateStatus.SELECTED.value,
    ]
    for vote in DEMO_VOTES:
        voter = users.get(vote["voter_key"])
        if voter is None:
            continue

        stmt = (
            select(SceneCandidate)
            .where(
                SceneCandidate.scene_instance_id == instance_id,
                SceneCandidate.status.in_(voteable_statuses),
            )
            .order_by(SceneCandidate.rank.asc())
            .limit(1)
        )
        top_candidate = session.execute(stmt).scalar_one_or_none()
        if top_candidate is None:
            break
        cast_vote(
            voter,
            instance_id,
            top_candidate.id,
            vote["vote_value"],
            session,
            idempotency_key=f"demo-vote-{vote['voter_key']}",
        )
        votes_created += 1

    transition_state(creator, instance_id, "voting_complete", session)
    transition_state(creator, instance_id, "confirm", session)

    return {
        "scenes_created": 1,
        "votes_created": votes_created,
        "preferences_created": preferences_created,
    }


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def seed_demo(session: Session) -> dict[str, Any]:
    """Seed the complete demo dataset idempotently.

    Args:
        session: A SQLAlchemy Session. The caller is responsible for
            committing or rolling back.

    Returns:
        A summary dict with stable keys:
        - users_created, users_updated
        - organizations_created
        - memberships_created
        - conversations_created, messages_created
        - scenes_created, votes_created, preferences_created
    """
    users, user_counts = _seed_users(session)
    orgs, org_counts = _seed_organizations(session, users)
    member_counts = _seed_memberships(session, users, orgs)
    conversation, conv_counts = _seed_conversation(session, users)
    scene_counts = _seed_dinner_scene(session, users, conversation, orgs)

    summary: dict[str, Any] = {
        "users_created": user_counts["users_created"],
        "users_updated": user_counts["users_updated"],
        "organizations_created": org_counts["organizations_created"],
        "memberships_created": member_counts["memberships_created"],
        "conversations_created": conv_counts["conversations_created"],
        "messages_created": conv_counts["messages_created"],
        "scenes_created": scene_counts["scenes_created"],
        "votes_created": scene_counts["votes_created"],
        "preferences_created": scene_counts["preferences_created"],
    }
    logger.info("demo.seed.complete", extra=summary)
    return summary
