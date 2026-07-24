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

        user = register_and_login(db_client, email="open@example.edu", student_no="20265001")
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

        user = register_and_login(db_client, email="approval@example.edu", student_no="20265002")
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "PENDING"
        assert resp.json()["data"]["role"] == "MEMBER"

    def test_owner_can_review_pending_request(self, db_client: TestClient) -> None:
        """Owners can list and approve pending join requests."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="审核闭环", join_policy="APPROVAL")

        applicant = register_and_login(db_client, email="review@example.edu", student_no="20265012")
        set_auth_cookies(db_client, applicant)
        join_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(applicant["csrf_token"]),
        )
        assert join_resp.status_code == 201

        set_auth_cookies(db_client, owner)
        pending_resp = db_client.get(
            f"/api/v1/organizations/{org['id']}/members?status_filter=PENDING"
        )
        assert pending_resp.status_code == 200
        assert pending_resp.json()["data"]["total"] == 1

        review_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members/{applicant['user_id']}/review",
            json={"decision": "APPROVE", "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["data"]["member"]["status"] == "ACTIVE"

    def test_owner_can_reject_pending_request(self, db_client: TestClient) -> None:
        """Rejected applications leave the pending queue."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="拒绝申请", join_policy="APPROVAL")

        applicant = register_and_login(db_client, email="reject@example.edu", student_no="20265013")
        set_auth_cookies(db_client, applicant)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(applicant["csrf_token"]),
        )

        set_auth_cookies(db_client, owner)
        review_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members/{applicant['user_id']}/review",
            json={"decision": "REJECT", "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["data"]["member"] is None


class TestInvitationLifecycle:
    """Test invitation acceptance and ownership transfer flows."""

    def test_invited_user_can_accept(self, db_client: TestClient) -> None:
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="邀请加入", join_policy="INVITE_ONLY")
        invited = register_and_login(db_client, email="invited@example.edu", student_no="20265020")

        set_auth_cookies(db_client, owner)
        invite_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/invitations",
            json={"user_id": invited["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert invite_resp.status_code == 201
        assert invite_resp.json()["data"]["status"] == "INVITED"

        set_auth_cookies(db_client, invited)
        list_resp = db_client.get("/api/v1/organizations")
        listed = next(
            item for item in list_resp.json()["data"]["organizations"] if item["id"] == org["id"]
        )
        assert listed["current_membership_status"] == "INVITED"

        accept_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/invitation",
            json={"decision": "ACCEPT"},
            headers=auth_headers(invited["csrf_token"]),
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["data"]["member"]["status"] == "ACTIVE"

    def test_owner_can_transfer_ownership(self, db_client: TestClient) -> None:
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="负责人转让")
        member = register_and_login(db_client, email="new_owner@example.edu", student_no="20265021")

        set_auth_cookies(db_client, owner)
        add_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert add_resp.status_code == 201

        transfer_resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/ownership-transfer",
            json={"user_id": member["user_id"]},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert transfer_resp.status_code == 200
        assert transfer_resp.json()["data"]["role"] == "OWNER"

        members_resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        roles = {item["user_id"]: item["role"] for item in members_resp.json()["data"]["members"]}
        assert roles[owner["user_id"]] == "ADMIN"
        assert roles[member["user_id"]] == "OWNER"


class TestInviteOnlyJoinPolicy:
    """Test INVITE_ONLY join policy."""

    def test_invite_only_join_rejected(self, db_client: TestClient) -> None:
        """INVITE_ONLY join returns ORG_INVALID_JOIN_POLICY."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="仅邀请", join_policy="INVITE_ONLY")

        user = register_and_login(db_client, email="invite@example.edu", student_no="20265003")
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

        user = register_and_login(db_client, email="closed@example.edu", student_no="20265004")
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
        org = create_org(db_client, owner, name="容量已满", join_policy="OPEN", capacity=1)

        # capacity=1, owner already takes 1 slot
        user = register_and_login(db_client, email="cap@example.edu", student_no="20265005")
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
        org = create_org(db_client, owner, name="管理员加人容量满", join_policy="OPEN", capacity=1)

        target = register_and_login(db_client, email="cap_tgt@example.edu", student_no="20265006")
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
        org = create_org(db_client, owner, name="容量未满", join_policy="OPEN", capacity=10)

        user = register_and_login(db_client, email="cap_ok@example.edu", student_no="20265007")
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code == 201
