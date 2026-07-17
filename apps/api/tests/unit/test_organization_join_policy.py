"""
Unit tests for Join Policy and Capacity (P4-06).

Tests verify:
- OPEN join -> ACTIVE MEMBER.
- APPROVAL join -> PENDING MEMBER.
- INVITE_ONLY join -> ORG_INVALID_JOIN_POLICY.
- CLOSED join -> ORG_INVALID_JOIN_POLICY.
- Already member join -> ORG_MEMBER_ALREADY_EXISTS.
- Capacity full join -> ORG_CAPACITY_EXCEEDED.
- Admin add member also respects capacity.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


class TestOpenJoinPolicy:
    """Test OPEN join policy."""

    def test_open_join_active_member(self, db_client: TestClient) -> None:
        """OPEN join creates ACTIVE MEMBER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="开放加入", join_policy="OPEN")

        user = register_and_login(
            db_client, email="open@example.edu", student_no="20265001"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "ACTIVE"
        assert resp.json()["data"]["role"] == "MEMBER"


class TestApprovalJoinPolicy:
    """Test APPROVAL join policy."""

    def test_approval_join_pending(self, db_client: TestClient) -> None:
        """APPROVAL join creates PENDING MEMBER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="审批加入", join_policy="APPROVAL")

        user = register_and_login(
            db_client, email="approval@example.edu", student_no="20265002"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "PENDING"
        assert resp.json()["data"]["role"] == "MEMBER"


class TestInviteOnlyJoinPolicy:
    """Test INVITE_ONLY join policy."""

    def test_invite_only_join_rejected(self, db_client: TestClient) -> None:
        """INVITE_ONLY join returns ORG_INVALID_JOIN_POLICY."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="仅邀请", join_policy="INVITE_ONLY")

        user = register_and_login(
            db_client, email="invite@example.edu", student_no="20265003"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORG_INVALID_JOIN_POLICY"


class TestClosedJoinPolicy:
    """Test CLOSED join policy."""

    def test_closed_join_rejected(self, db_client: TestClient) -> None:
        """CLOSED join returns ORG_INVALID_JOIN_POLICY."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="已关闭", join_policy="CLOSED")

        user = register_and_login(
            db_client, email="closed@example.edu", student_no="20265004"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "ORG_INVALID_JOIN_POLICY"


class TestAlreadyMemberJoin:
    """Test that existing members cannot join again."""

    def test_active_member_join_conflict(self, db_client: TestClient) -> None:
        """Active member joining returns ORG_MEMBER_ALREADY_EXISTS."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="重复加入", join_policy="OPEN")

        # Owner is already a member
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_MEMBER_ALREADY_EXISTS"


class TestCapacityExceeded:
    """Test capacity limits."""

    def test_capacity_exceeded_on_join(self, db_client: TestClient) -> None:
        """Joining a full org returns ORG_CAPACITY_EXCEEDED."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="容量已满", join_policy="OPEN", capacity=1
        )

        # capacity=1, owner already takes 1 slot
        user = register_and_login(
            db_client, email="cap@example.edu", student_no="20265005"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_CAPACITY_EXCEEDED"

    def test_capacity_exceeded_on_admin_add(self, db_client: TestClient) -> None:
        """Admin adding a member to a full org returns ORG_CAPACITY_EXCEEDED."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="管理员加人容量满", join_policy="OPEN", capacity=1
        )

        target = register_and_login(
            db_client, email="cap_tgt@example.edu", student_no="20265006"
        )
        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": target["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_CAPACITY_EXCEEDED"

    def test_capacity_not_exceeded_when_not_full(self, db_client: TestClient) -> None:
        """Joining an org that still has capacity succeeds."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="容量未满", join_policy="OPEN", capacity=10
        )

        user = register_and_login(
            db_client, email="cap_ok@example.edu", student_no="20265007"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 201
