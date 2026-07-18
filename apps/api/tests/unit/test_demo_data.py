"""P11-01: Unit tests for demo data schema and constants.

Verifies:
- Demo emails are unique.
- At least 5 demo users, at least 1 admin.
- At least 3 dinner participants.
- Private preference samples are non-empty.
- is_demo_email / is_demo_org_slug helpers work correctly.
- DEMO_PRIVATE_PHRASE appears in private preference notes.
"""

from __future__ import annotations

from src.demo.data import (
    DEMO_ADMIN,
    DEMO_ALICE,
    DEMO_BOB,
    DEMO_CAROL,
    DEMO_DELETED,
    DEMO_ORG_SLUG_SUFFIX,
    DEMO_ORGANIZATIONS,
    DEMO_PASSWORD,
    DEMO_PREFERENCES_BY_PARTICIPANT,
    DEMO_PRIVATE_PHRASE,
    DEMO_SCENE_IDEMPOTENCY_KEY,
    DEMO_SCENE_PARTICIPANT_KEYS,
    DEMO_USERS,
    DEMO_VOTES,
    demo_emails,
    is_demo_email,
    is_demo_org_slug,
)


class TestDemoUsers:
    """Demo user data integrity."""

    def test_at_least_five_users(self) -> None:
        assert len(DEMO_USERS) >= 5

    def test_at_least_one_admin(self) -> None:
        admins = [u for u in DEMO_USERS if u.is_admin]
        assert len(admins) >= 1

    def test_emails_unique(self) -> None:
        emails = [u.email for u in DEMO_USERS]
        assert len(emails) == len(set(emails))

    def test_emails_lowercase_demo_prefix(self) -> None:
        for u in DEMO_USERS:
            assert u.email.startswith("demo_"), f"{u.email} missing demo_ prefix"
            assert u.email == u.email.lower(), f"{u.email} not lowercase"

    def test_deleted_user_is_soft_deleted(self) -> None:
        assert DEMO_DELETED.soft_deleted is True
        assert DEMO_DELETED.status == "DELETED"

    def test_active_users_are_not_soft_deleted(self) -> None:
        for u in DEMO_USERS:
            if u is DEMO_DELETED:
                continue
            assert not u.soft_deleted
            assert u.status == "ACTIVE"

    def test_all_users_have_student_no(self) -> None:
        for u in DEMO_USERS:
            assert u.student_no, f"{u.key} missing student_no"

    def test_admin_is_system_admin(self) -> None:
        assert DEMO_ADMIN.is_admin
        assert DEMO_ADMIN.global_role == "SYSTEM_ADMIN"

    def test_students_have_student_role(self) -> None:
        for u in [DEMO_ALICE, DEMO_BOB, DEMO_CAROL]:
            assert u.global_role == "STUDENT"


class TestDemoEmailsHelpers:
    """is_demo_email and demo_emails helpers."""

    def test_demo_emails_returns_all(self) -> None:
        emails = demo_emails()
        assert len(emails) == len(DEMO_USERS)

    def test_is_demo_email_positive(self) -> None:
        assert is_demo_email("demo_alice@example.com")

    def test_is_demo_email_negative_non_demo(self) -> None:
        assert not is_demo_email("alice@example.com")

    def test_is_demo_email_negative_other_domain(self) -> None:
        assert not is_demo_email("demo_alice@other.com")

    def test_is_demo_email_empty(self) -> None:
        assert not is_demo_email("")

    def test_is_demo_org_slug_positive(self) -> None:
        assert is_demo_org_slug(f"test{DEMO_ORG_SLUG_SUFFIX}")

    def test_is_demo_org_slug_negative(self) -> None:
        assert not is_demo_org_slug("regular-slug")
        assert not is_demo_org_slug("")


class TestDemoOrganizations:
    """Demo organization data integrity."""

    def test_at_least_one_org(self) -> None:
        assert len(DEMO_ORGANIZATIONS) >= 1

    def test_all_org_slugs_have_demo_suffix(self) -> None:
        for org in DEMO_ORGANIZATIONS:
            assert org.slug.endswith(DEMO_ORG_SLUG_SUFFIX), (
                f"{org.slug} missing demo suffix"
            )

    def test_parent_child_relationship(self) -> None:
        keys = {o.key: o for o in DEMO_ORGANIZATIONS}
        for org in DEMO_ORGANIZATIONS:
            if org.parent_key is not None:
                assert org.parent_key in keys, f"{org.key} parent not found"
                assert keys[org.parent_key].type == "SCHOOL"


class TestDemoSceneParticipants:
    """Dinner scene participant integrity."""

    def test_at_least_three_participants(self) -> None:
        assert len(DEMO_SCENE_PARTICIPANT_KEYS) >= 3

    def test_participant_keys_exist_in_users(self) -> None:
        user_keys = {u.key for u in DEMO_USERS}
        for key in DEMO_SCENE_PARTICIPANT_KEYS:
            assert key in user_keys, f"participant {key} not in DEMO_USERS"

    def test_preferences_non_empty(self) -> None:
        for key in DEMO_SCENE_PARTICIPANT_KEYS:
            prefs = DEMO_PREFERENCES_BY_PARTICIPANT.get(key)
            assert prefs is not None, f"no preferences for {key}"
            assert "cuisine_preferences" in prefs
            assert len(prefs["cuisine_preferences"]) > 0
            assert "dietary_restrictions" in prefs

    def test_private_phrase_in_preferences_notes(self) -> None:
        """Each private preference note carries the DEMO_PRIVATE_PHRASE marker."""
        for key in DEMO_SCENE_PARTICIPANT_KEYS:
            prefs = DEMO_PREFERENCES_BY_PARTICIPANT[key]
            notes = prefs.get("notes", "")
            assert DEMO_PRIVATE_PHRASE in notes, (
                f"{key} notes missing DEMO_PRIVATE_PHRASE"
            )


class TestDemoVotes:
    """Demo vote data integrity."""

    def test_at_least_two_votes(self) -> None:
        assert len(DEMO_VOTES) >= 2

    def test_voter_keys_are_participants(self) -> None:
        for vote in DEMO_VOTES:
            assert vote["voter_key"] in DEMO_SCENE_PARTICIPANT_KEYS

    def test_vote_values_are_approve(self) -> None:
        for vote in DEMO_VOTES:
            assert vote["vote_value"] == "APPROVE"


class TestDemoConstants:
    """Static constants are stable and well-formed."""

    def test_password_is_non_empty(self) -> None:
        assert len(DEMO_PASSWORD) >= 12

    def test_private_phrase_is_marker(self) -> None:
        assert DEMO_PRIVATE_PHRASE == "DEMO_PRIVATE_PHRASE_DO_NOT_RENDER"

    def test_scene_idempotency_key_is_non_empty(self) -> None:
        assert DEMO_SCENE_IDEMPOTENCY_KEY
        assert len(DEMO_SCENE_IDEMPOTENCY_KEY) > 10
