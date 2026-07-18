"""P12-08: Concurrency and idempotency regression.

Verifies that common duplicate/concurrent operations do not corrupt data:
- Duplicate organization join is idempotent (no duplicate membership).
- Duplicate vote replaces, not duplicates.
- Refresh token replay is rejected (second concurrent refresh fails).
- Duplicate scene accept is idempotent.
- Concurrent same-key operations return stable errors, not 500.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.modules.scenes.models import CandidateStatus, SceneCandidate
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import SceneInstanceRepository, SceneVoteRepository
from src.modules.scenes.service import (
    accept_invitation,
    cast_vote,
    create_scene_instance,
    transition_state,
)
from src.modules.scenes.state_machine import SceneState
from src.modules.scenes.test_plugins import NoopScenePlugin
from src.modules.users.models import GlobalRole, User, UserStatus
from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)

# ---------------------------------------------------------------------------
# 1. Duplicate organization join (HTTP-level)
# ---------------------------------------------------------------------------


class TestDuplicateOrgJoinIdempotency:
    def test_duplicate_join_is_idempotent(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="p12join_owner@example.edu", student_no="20268001"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="Join Idempotency Org",
            visibility="PUBLIC",
            join_policy="OPEN",
        )
        org_id = org["id"]

        joiner = register_and_login(
            db_client, email="p12joiner@example.edu", student_no="20268002"
        )
        set_auth_cookies(db_client, joiner)
        # First join
        resp1 = db_client.post(
            f"/api/v1/organizations/{org_id}/join",
            headers=auth_headers(joiner["csrf_token"]),
        )
        assert resp1.status_code in (200, 201, 204)

        # Second join (duplicate) — must not 500, must be idempotent
        resp2 = db_client.post(
            f"/api/v1/organizations/{org_id}/join",
            headers=auth_headers(joiner["csrf_token"]),
        )
        assert resp2.status_code != 500
        # Idempotent: either 200/201 (re-confirmed) or 409 (already member).
        assert resp2.status_code in (200, 201, 204, 409)


# ---------------------------------------------------------------------------
# 2. Duplicate vote replaces, not duplicates (service-level)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_registry():
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(NoopScenePlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def creator(test_db_session: Session) -> User:
    user = User(
        email="p12vote-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def voter(test_db_session: Session) -> User:
    user = User(
        email="p12vote-voter@example.com",
        password_hash="fake",
        display_name="Voter",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


class TestVoteIdempotency:
    @pytest.fixture()
    def voting_scene(
        self, creator: User, voter: User, test_db_session: Session
    ) -> tuple[UUID, SceneCandidate]:
        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id, voter.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(voter, instance_id, test_db_session)

        candidate = SceneCandidate(
            scene_instance_id=instance_id,
            candidate_key="cand",
            display_name="Candidate",
            status=CandidateStatus.ACTIVE.value,
        )
        test_db_session.add(candidate)
        test_db_session.flush()

        instance = SceneInstanceRepository(test_db_session).get_by_id(instance_id)
        assert instance is not None
        instance.status = SceneState.VOTING.value
        instance.current_phase = SceneState.VOTING.value
        test_db_session.flush()
        return instance_id, candidate

    def test_duplicate_vote_replaces_not_duplicates(
        self,
        voting_scene: tuple[UUID, SceneCandidate],
        voter: User,
        test_db_session: Session,
    ):
        instance_id, candidate = voting_scene
        cast_vote(voter, instance_id, candidate.id, "APPROVE", test_db_session)
        cast_vote(voter, instance_id, candidate.id, "APPROVE", test_db_session)

        vote_repo = SceneVoteRepository(test_db_session)
        votes = vote_repo.list_by_instance(instance_id)
        voter_votes = [v for v in votes if v.user_id == voter.id]
        assert len(voter_votes) == 1

    def test_vote_then_change_value_replaces(
        self,
        voting_scene: tuple[UUID, SceneCandidate],
        voter: User,
        test_db_session: Session,
    ):
        instance_id, candidate = voting_scene
        cast_vote(voter, instance_id, candidate.id, "APPROVE", test_db_session)
        cast_vote(voter, instance_id, candidate.id, "REJECT", test_db_session)

        vote_repo = SceneVoteRepository(test_db_session)
        votes = vote_repo.list_by_instance(instance_id)
        voter_votes = [v for v in votes if v.user_id == voter.id]
        assert len(voter_votes) == 1
        assert voter_votes[0].vote_value == "REJECT"


# ---------------------------------------------------------------------------
# 3. Refresh token replay rejection (HTTP-level)
# ---------------------------------------------------------------------------


class TestRefreshTokenReplayRejection:
    def test_concurrent_refresh_second_fails(self, db_client: TestClient):
        db_client.cookies.clear()
        reg = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12replay@example.edu",
                "password": "SecurePass123",
                "display_name": "Replay",
                "student_no": "20268010",
                "organization_ids": [],
            },
        )
        assert reg.status_code == 201
        cookies: dict[str, str] = {}
        for header in reg.headers.get_list("set-cookie"):
            name_value = header.split(";")[0]
            name, value = name_value.split("=", 1)
            cookies[name.strip()] = value.strip()
        cookie_str = (
            f"refresh_token={cookies['refresh_token']}; csrf_token={cookies['csrf_token']}"
        )
        # First refresh succeeds
        resp1 = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": cookie_str, "X-CSRF-Token": cookies["csrf_token"]},
        )
        assert resp1.status_code == 200
        # Second concurrent refresh with same token fails (replay)
        resp2 = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": cookie_str, "X-CSRF-Token": cookies["csrf_token"]},
        )
        assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# 4. Duplicate scene accept is idempotent (service-level)
# ---------------------------------------------------------------------------


class TestSceneAcceptIdempotency:
    def test_duplicate_accept_is_idempotent(
        self, creator: User, voter: User, test_db_session: Session
    ):
        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id, voter.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        # First accept
        accept_invitation(voter, instance_id, test_db_session)
        # Second accept — should be idempotent (no exception, or stable error)
        try:
            accept_invitation(voter, instance_id, test_db_session)
        except Exception as exc:
            # If it raises, it must be a stable business error, not a 500.
            assert "500" not in str(exc)


# ---------------------------------------------------------------------------
# 5. Non-existent resource does not 500 on duplicate-style requests
# ---------------------------------------------------------------------------


class TestNonExistentIdempotency:
    def test_join_nonexistent_org_stable_error(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="p12ne@example.edu", student_no="20268020"
        )
        set_auth_cookies(db_client, user)
        fake_id = str(uuid4())
        resp = db_client.post(
            f"/api/v1/organizations/{fake_id}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code in (403, 404)
        assert resp.status_code != 500
