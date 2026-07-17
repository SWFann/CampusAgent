"""
Unit tests for Organization Membership lifecycle (P4-03).

Tests verify:
- OWNER can add MEMBER.
- Duplicate add returns ORG_MEMBER_ALREADY_EXISTS.
- Member list only visible to authorized users.
- OWNER can remove MEMBER.
- Removed user cannot view private org.
- User leave sets status=LEFT.
- LEFT/REMOVED user can rejoin per join policy.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


class TestAddMember:
    def test_owner_adds_member(self, db_client: TestClient) -> None:
        """OWNER adds MEMBER successfully."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="加成员测试", visibility="PRIVATE")

        member = register_and_login(
            db_client, email="member@example.edu", student_no="20260010"
        )
        set_auth_cookies(db_client, owner)  # owner adds member

        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["user_id"] == member["user_id"]
        assert data["role"] == "MEMBER"
        assert data["status"] == "ACTIVE"

    def test_duplicate_add_returns_conflict(self, db_client: TestClient) -> None:
        """Duplicate add returns ORG_MEMBER_ALREADY_EXISTS."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="重复加成员")

        member = register_and_login(
            db_client, email="dup@example.edu", student_no="20260011"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # Try again
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_MEMBER_ALREADY_EXISTS"

    def test_add_member_no_email_in_response(self, db_client: TestClient) -> None:
        """Member response does not contain email or student_no."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="安全成员")

        member = register_and_login(
            db_client, email="safe@example.edu", student_no="20260012"
        )
        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        body = resp.text.lower()
        assert "email" not in body
        assert "student_no" not in body
        assert "password" not in body


class TestListMembers:
    def test_owner_can_list_members(self, db_client: TestClient) -> None:
        """OWNER can list members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="成员列表")

        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 200
        members = resp.json()["data"]["members"]
        assert len(members) == 1  # just the owner

    def test_non_member_cannot_list_members(self, db_client: TestClient) -> None:
        """Non-member cannot list members of private org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="私密成员列表", visibility="PRIVATE")

        other = register_and_login(
            db_client, email="other@example.edu", student_no="20260013"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 403


class TestRemoveMember:
    def test_owner_removes_member(self, db_client: TestClient) -> None:
        """OWNER removes MEMBER successfully."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="移除成员", visibility="PRIVATE")

        member = register_and_login(
            db_client, email="removed@example.edu", student_no="20260014"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 204

    def test_removed_user_cannot_view_private(self, db_client: TestClient) -> None:
        """Removed user cannot view private org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="移除后不可见", visibility="PRIVATE")

        member = register_and_login(
            db_client, email="rm@example.edu", student_no="20260015"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, member)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403


class TestLeaveOrganization:
    def test_member_can_leave(self, db_client: TestClient) -> None:
        """Member can leave, status becomes LEFT."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="退出测试", join_policy="OPEN")

        member = register_and_login(
            db_client, email="leaver@example.edu", student_no="20260016"
        )
        set_auth_cookies(db_client, member)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )

        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 204

    def test_non_member_cannot_leave(self, db_client: TestClient) -> None:
        """Non-member cannot leave."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="非成员退出")

        other = register_and_login(
            db_client, email="nm@example.edu", student_no="20260017"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(other["csrf_token"]),
        )
        assert resp.status_code == 403


class TestRejoinAfterLeave:
    def test_left_user_can_rejoin_open(self, db_client: TestClient) -> None:
        """LEFT user can rejoin an OPEN org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="重新加入", join_policy="OPEN")

        member = register_and_login(
            db_client, email="rejoin@example.edu", student_no="20260018"
        )
        set_auth_cookies(db_client, member)
        # Join
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        # Leave
        db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(member["csrf_token"]),
        )
        # Rejoin
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 201


class TestUpdateMemberRole:
    def test_owner_promotes_member_to_admin(self, db_client: TestClient) -> None:
        """OWNER promotes MEMBER to ADMIN."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="升职测试")

        member = register_and_login(
            db_client, email="promote@example.edu", student_no="20260019"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "ADMIN"
