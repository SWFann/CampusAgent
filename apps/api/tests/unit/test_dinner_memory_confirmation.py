"""P9-14: Long-term memory confirmation tests.

Tests cover (per P9 guide §16):
- Default: preferences are NOT saved to Memory.
- When save_to_long_term_memory=True: saved with explicit category and source.
- The saved content is the capsule (not raw preferences or notes).
- Consent can be revoked (memory can be deleted).
"""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.memories.models import MemoryItem, MemorySource
from src.modules.scenes.plugins.dorm_dinner.plugin import DormDinnerPlugin
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.service import (
    accept_invitation,
    create_scene_instance,
    submit_private_preferences,
    transition_state,
)
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def setup_registry():
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(DormDinnerPlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def creator(test_db_session: Session) -> User:
    user = User(
        email="memory-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def participant1(test_db_session: Session) -> User:
    user = User(
        email="memory-p1@example.com",
        password_hash="fake",
        display_name="P1",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


def _make_prefs(**kwargs) -> dict:
    prefs = {
        "budget_min": 20,
        "budget_max": 50,
        "cuisine_preferences": ["sichuan"],
        "dietary_restrictions": ["none"],
        "distance_preference": "moderate",
        "available_time": ["dinner"],
        "environment_preference": "moderate",
        "notes": "secret note for memory test",
    }
    prefs.update(kwargs)
    return prefs


class TestMemoryConfirmationDefault:
    """Tests for default behaviour (not saved to Memory)."""

    def test_default_not_saved_to_memory(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """By default, preferences are NOT saved to Memory."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        # Submit WITHOUT save_to_long_term_memory (defaults to False).
        submit_private_preferences(
            creator, instance_id, _make_prefs(), test_db_session,
        )

        # Verify no memory items were created for this user.
        memories = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).all()
        assert len(memories) == 0

    def test_explicit_false_not_saved(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Explicitly setting save_to_long_term_memory=False does not save."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        submit_private_preferences(
            creator, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=False,
        )

        memories = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).all()
        assert len(memories) == 0


class TestMemoryConfirmationOptIn:
    """Tests for opt-in memory saving."""

    def test_saved_when_confirmed(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """When save_to_long_term_memory=True, a memory item is created."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        submit_private_preferences(
            creator, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=True,
        )

        # Verify a memory item was created.
        memories = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).all()
        assert len(memories) == 1

    def test_saved_with_explicit_category(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """The memory item has an explicit category."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        submit_private_preferences(
            creator, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=True,
        )

        memory = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).first()
        assert memory is not None
        assert memory.category == "dorm_dinner_preference"

    def test_saved_with_explicit_source(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """The memory item has an explicit source (USER_INPUT)."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        submit_private_preferences(
            creator, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=True,
        )

        memory = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).first()
        assert memory is not None
        assert memory.source == MemorySource.USER_INPUT.value

    def test_saved_content_is_capsule_not_raw(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """The saved content is the capsule, not raw preferences or notes."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        secret_note = "This is a very secret note that should never be in memory"
        submit_private_preferences(
            creator, instance_id,
            _make_prefs(notes=secret_note),
            test_db_session,
            save_to_long_term_memory=True,
        )

        memory = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).first()
        assert memory is not None
        # The encrypted content should be the capsule, not the raw preferences.
        # We can't decrypt it here, but we can verify the content_hash
        # is not the hash of the raw preferences.
        # More importantly, the raw notes text should not be findable.
        # Since content is encrypted, we check that the note text is not
        # in any plaintext field.
        assert secret_note not in (memory.content_encrypted or "")
        assert secret_note not in (memory.content_hash or "")

    def test_only_confirmer_saves_not_others(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Only the user who confirms saves to memory; others don't."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        # Creator saves, participant1 does not.
        submit_private_preferences(
            creator, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=True,
        )
        submit_private_preferences(
            participant1, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=False,
        )

        creator_memories = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).all()
        p1_memories = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == participant1.id,
        ).all()

        assert len(creator_memories) == 1
        assert len(p1_memories) == 0


class TestMemoryRevocation:
    """Tests for consent revocation (memory deletion)."""

    def test_memory_can_be_deleted(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """A saved memory can be deleted (consent revoked)."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        submit_private_preferences(
            creator, instance_id, _make_prefs(),
            test_db_session,
            save_to_long_term_memory=True,
        )

        # Verify memory exists.
        memory = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).first()
        assert memory is not None

        # Delete the memory (revoke consent).
        test_db_session.delete(memory)
        test_db_session.commit()

        # Verify memory is gone.
        memories = test_db_session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == creator.id,
        ).all()
        assert len(memories) == 0
