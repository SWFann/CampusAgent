"""
Integration tests for the full organization membership lifecycle (P4-03).

Tests verify the end-to-end flow:
1. Create organization (creator becomes OWNER).
2. Add a member.
3. Member joins another org via self-service.
4. Update member role.
5. Remove member.
6. Leave organization.
7. Rejoin after leaving.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


class TestOrganizationFlow:
    """End-to-end organization lifecycle integration tests."""

    def test_full_membership_lifecycle(self, db_client: TestClient) -> None:
        """Test the complete membership lifecycle: create → add → role change → remove."""
        # 1. Owner creates a private org
        owner = register_and_login(
            db_client, email="flow_owner@example.edu", student_no="20262001"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="集成测试组织",
            visibility="PRIVATE",
            join_policy="INVITE_ONLY",
        )
        assert org["id"]

        # 2. Owner adds a member
        member = register_and_login(
            db_client, email="flow_member@example.edu", student_no="20262002"
        )
        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201

        # 3. Member can view the private org
        set_auth_cookies(db_client, member)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200

        # 4. Owner promotes member to ADMIN
        set_auth_cookies(db_client, owner)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "ADMIN"

        # 5. Owner removes the member
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 204

        # 6. Removed member can no longer view the private org
        set_auth_cookies(db_client, member)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403

    def test_join_leave_rejoin_flow(self, db_client: TestClient) -> None:
        """Test join → leave → rejoin flow on an OPEN org."""
        owner = register_and_login(
            db_client, email="jl_owner@example.edu", student_no="20262003"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="加入退出重加",
            visibility="PUBLIC",
            join_policy="OPEN",
        )

        member = register_and_login(
            db_client, email="jl_member@example.edu", student_no="20262004"
        )

        # 1. Member joins
        set_auth_cookies(db_client, member)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "ACTIVE"
        assert resp.json()["data"]["role"] == "MEMBER"

        # 2. Member leaves
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 204

        # 3. Member can no longer view member list (public org, non-member)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 403

        # 4. Member rejoins
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "ACTIVE"

    def test_user_organizations_endpoint(self, db_client: TestClient) -> None:
        """Test GET /api/v1/users/{user_id}/organizations."""
        owner = register_and_login(
            db_client, email="uo_owner@example.edu", student_no="20262005"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="用户组织列表",
            visibility="PUBLIC",
            join_policy="OPEN",
        )

        # Owner queries their own organizations
        resp = db_client.get(f"/api/v1/users/{owner['user_id']}/organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert len(orgs) == 1
        assert orgs[0]["id"] == org["id"]
        assert orgs[0]["role"] == "OWNER"

    def test_user_organizations_visibility_filter(
        self, db_client: TestClient
    ) -> None:
        """Other users cannot see private orgs in user's organization list."""
        owner = register_and_login(
            db_client, email="vf_owner@example.edu", student_no="20262006"
        )
        set_auth_cookies(db_client, owner)
        create_org(
            db_client,
            owner,
            name="私密组织",
            visibility="PRIVATE",
            join_policy="INVITE_ONLY",
        )
        create_org(
            db_client,
            owner,
            name="公开组织",
            visibility="PUBLIC",
            join_policy="OPEN",
        )

        # Another user queries owner's organizations
        other = register_and_login(
            db_client, email="vf_other@example.edu", student_no="20262007"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/users/{owner['user_id']}/organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        # Should only see PUBLIC org
        assert len(orgs) == 1
        assert orgs[0]["visibility"] == "PUBLIC"

    def test_csrf_required_on_all_write_endpoints(
        self, db_client: TestClient
    ) -> None:
        """All write endpoints require CSRF token."""
        owner = register_and_login(
            db_client, email="csrf_owner@example.edu", student_no="20262008"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="CSRF测试")

        member = register_and_login(
            db_client, email="csrf_member@example.edu", student_no="20262009"
        )

        # POST members without CSRF
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers={"Content-Type": "application/json"},  # no X-CSRF-Token
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISSING"

        # POST join without CSRF
        set_auth_cookies(db_client, member)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403

        # POST leave without CSRF
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403

        # PATCH member role without CSRF
        set_auth_cookies(db_client, owner)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "ADMIN"},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403

        # DELETE member without CSRF
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403

        # DELETE org without CSRF
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403
