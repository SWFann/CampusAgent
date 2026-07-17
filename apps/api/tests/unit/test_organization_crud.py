"""
Unit tests for Organization CRUD API (P4-02).

Tests verify:
- Authenticated user can create an org (201).
- Response does not contain sensitive fields.
- Creator automatically becomes OWNER.
- Anonymous create returns 401.
- Missing CSRF returns CSRF_TOKEN_MISSING.
- OWNER can update org.
- MEMBER/non-member cannot update.
- OWNER can soft-delete org.
- Deleted org not returned in list.
- Second delete returns 404.
- Non-member cannot view PRIVATE org.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    clear_auth_cookies,
    create_org,
    register_and_login,
    set_auth_cookies,
)

# ---------------------------------------------------------------------------
# 1. Create organization
# ---------------------------------------------------------------------------


class TestCreateOrganization:
    def test_create_returns_201(self, db_client: TestClient) -> None:
        """Authenticated user creates org returns 201."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        resp = db_client.post(
            "/api/v1/organizations",
            json={"name": "测试社团", "type": "CLUB"},
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "测试社团"
        assert data["type"] == "CLUB"

    def test_create_response_no_sensitive_fields(self, db_client: TestClient) -> None:
        """Response does not contain email, password_hash, token."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        resp = db_client.post(
            "/api/v1/organizations",
            json={"name": "安全测试", "type": "DORM"},
            headers=auth_headers(creds["csrf_token"]),
        )
        body = resp.text.lower()
        assert "password" not in body
        assert "email" not in body
        assert "student_no" not in body
        assert "token" not in body

    def test_creator_becomes_owner(self, db_client: TestClient) -> None:
        """Creator automatically becomes OWNER."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds)

        # Check members
        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 200
        members = resp.json()["data"]["members"]
        assert len(members) == 1
        assert members[0]["role"] == "OWNER"
        assert members[0]["status"] == "ACTIVE"
        assert members[0]["user_id"] == creds["user_id"]

    def test_anonymous_create_returns_401(self, db_client: TestClient) -> None:
        """Anonymous create returns 401."""
        resp = db_client.post(
            "/api/v1/organizations",
            json={"name": "匿名创建", "type": "CLUB"},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_missing_csrf_returns_csrf_error(self, db_client: TestClient) -> None:
        """Missing CSRF header returns CSRF_TOKEN_MISSING."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        # POST without X-CSRF-Token header
        resp = db_client.post(
            "/api/v1/organizations",
            json={"name": "无CSRF", "type": "CLUB"},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISSING"

    def test_create_with_parent(self, db_client: TestClient) -> None:
        """Create a child organization with parent_id."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        parent = create_org(db_client, creds, name="父组织", org_type="COLLEGE")

        resp = db_client.post(
            "/api/v1/organizations",
            json={
                "name": "子组织",
                "type": "CLASS",
                "parent_id": parent["id"],
            },
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["parent_id"] == parent["id"]


# ---------------------------------------------------------------------------
# 2. List organizations
# ---------------------------------------------------------------------------


class TestListOrganizations:
    def test_list_returns_public_orgs(self, db_client: TestClient) -> None:
        """List returns public orgs for any user."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        create_org(db_client, creds, name="公开社团", visibility="PUBLIC")

        resp = db_client.get("/api/v1/organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert len(orgs) >= 1
        assert any(o["name"] == "公开社团" for o in orgs)

    def test_list_anonymous_sees_only_public(self, db_client: TestClient) -> None:
        """Anonymous user only sees PUBLIC orgs."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        create_org(db_client, creds, name="公开", visibility="PUBLIC")
        create_org(db_client, creds, name="私密", visibility="PRIVATE")

        clear_auth_cookies(db_client)
        resp = db_client.get("/api/v1/organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        names = [o["name"] for o in orgs]
        assert "公开" in names
        assert "私密" not in names


# ---------------------------------------------------------------------------
# 3. Get organization
# ---------------------------------------------------------------------------


class TestGetOrganization:
    def test_get_public_org(self, db_client: TestClient) -> None:
        """Anyone can get a PUBLIC org."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="公开详情", visibility="PUBLIC")

        clear_auth_cookies(db_client)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "公开详情"

    def test_get_nonexistent_returns_404(self, db_client: TestClient) -> None:
        """Non-existent org returns ORG_NOT_FOUND."""
        import uuid

        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        resp = db_client.get(f"/api/v1/organizations/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ORG_NOT_FOUND"

    def test_non_member_cannot_view_private(self, db_client: TestClient) -> None:
        """Non-member cannot view PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="私密组织", visibility="PRIVATE")

        other = register_and_login(
            db_client, email="other@example.edu", student_no="20260002"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ORG_PERMISSION_DENIED"

    def test_member_can_view_private(self, db_client: TestClient) -> None:
        """Member can view PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="成员可见私密", visibility="PRIVATE", join_policy="OPEN"
        )

        member = register_and_login(
            db_client, email="member@example.edu", student_no="20260003"
        )
        set_auth_cookies(db_client, member)
        # Join the org
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 201

        # Now can view
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. Update organization
# ---------------------------------------------------------------------------


class TestUpdateOrganization:
    def test_owner_can_update(self, db_client: TestClient) -> None:
        """OWNER can update org."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="原名")

        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}",
            json={"name": "新名", "description": "新描述"},
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名"
        assert resp.json()["data"]["description"] == "新描述"

    def test_non_member_cannot_update(self, db_client: TestClient) -> None:
        """Non-member cannot update org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="不可改", visibility="PUBLIC")

        other = register_and_login(
            db_client, email="other@example.edu", student_no="20260004"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}",
            json={"name": "被改了"},
            headers=auth_headers(other["csrf_token"]),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ORG_PERMISSION_DENIED"

    def test_member_cannot_update(self, db_client: TestClient) -> None:
        """MEMBER (non-admin) cannot update org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="成员不可改", visibility="PUBLIC", join_policy="OPEN"
        )

        member = register_and_login(
            db_client, email="member@example.edu", student_no="20260005"
        )
        set_auth_cookies(db_client, member)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )

        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}",
            json={"name": "被改了"},
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_update_requires_csrf(self, db_client: TestClient) -> None:
        """Update requires CSRF."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="CSRF测试")

        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}",
            json={"name": "无CSRF改"},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISSING"


# ---------------------------------------------------------------------------
# 5. Delete organization
# ---------------------------------------------------------------------------


class TestDeleteOrganization:
    def test_owner_can_delete(self, db_client: TestClient) -> None:
        """OWNER can soft-delete org."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="要删除")

        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 204

    def test_deleted_org_not_in_list(self, db_client: TestClient) -> None:
        """Deleted org is not returned in list."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="已删除")

        db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(creds["csrf_token"]),
        )

        resp = db_client.get("/api/v1/organizations")
        orgs = resp.json()["data"]["organizations"]
        assert not any(o["id"] == org["id"] for o in orgs)

    def test_second_delete_returns_404(self, db_client: TestClient) -> None:
        """Second delete returns 404."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="二次删除")

        db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(creds["csrf_token"]),
        )

        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 404

    def test_non_owner_cannot_delete(self, db_client: TestClient) -> None:
        """Non-owner cannot delete org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="不可删", visibility="PUBLIC", join_policy="OPEN"
        )

        member = register_and_login(
            db_client, email="member@example.edu", student_no="20260006"
        )
        set_auth_cookies(db_client, member)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )

        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_delete_requires_csrf(self, db_client: TestClient) -> None:
        """Delete requires CSRF."""
        creds = register_and_login(db_client)
        set_auth_cookies(db_client, creds)
        org = create_org(db_client, creds, name="CSRF删除")

        resp = db_client.delete(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISSING"
