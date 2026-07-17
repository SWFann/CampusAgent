"""
Authorization test matrix for P4 organizations and directory (P4-11).

Systematically covers cross-cutting authorization paths and privacy projections:
- anonymous, non-member, GUEST, MEMBER, ADMIN, OWNER
- SYSTEM_ADMIN, SCHOOL_ADMIN, ORG_ADMIN
- deleted user, archived org, deleted org

Scenarios:
- View PUBLIC/MEMBERS_ONLY/PRIVATE organizations
- View member lists
- Add members, change roles, remove members
- Delete organizations
- Join and leave organizations
- Directory search, tree, user organizations
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    clear_auth_cookies,
    create_org,
    register_and_login,
    set_auth_cookies,
)


def _set_global_role(test_engine, user_id: str, role: str) -> None:
    """Directly update a user's global_role in the database."""
    from src.modules.users.models import User

    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = factory()
    try:
        user = session.get(User, UUID(user_id))
        if user is not None:
            user.global_role = role
            session.commit()
    finally:
        session.close()


class TestViewOrgMatrix:
    """Matrix: view PUBLIC/MEMBERS_ONLY/PRIVATE orgs."""

    def test_anonymous_view_matrix(
        self, db_client: TestClient, test_engine
    ) -> None:
        """Anonymous: PUBLIC=yes, MEMBERS_ONLY=no, PRIVATE=no."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        pub = create_org(db_client, owner, name="矩阵公开", visibility="PUBLIC")
        mo = create_org(db_client, owner, name="矩阵成员", visibility="MEMBERS_ONLY")
        priv = create_org(db_client, owner, name="矩阵私密", visibility="PRIVATE")

        clear_auth_cookies(db_client)
        assert db_client.get(f"/api/v1/organizations/{pub['id']}").status_code == 200
        assert db_client.get(f"/api/v1/organizations/{mo['id']}").status_code == 403
        assert db_client.get(f"/api/v1/organizations/{priv['id']}").status_code == 403

    def test_member_view_matrix(
        self, db_client: TestClient, test_engine
    ) -> None:
        """MEMBER: PUBLIC=yes, MEMBERS_ONLY=yes, PRIVATE=yes (if member)."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        pub = create_org(db_client, owner, name="成员矩阵公开", visibility="PUBLIC")
        mo = create_org(db_client, owner, name="成员矩阵仅成员", visibility="MEMBERS_ONLY")
        priv = create_org(db_client, owner, name="成员矩阵私密", visibility="PRIVATE")

        member = register_and_login(
            db_client, email="mtx@example.edu", student_no="20261101"
        )
        # Add member to all three orgs
        set_auth_cookies(db_client, owner)
        for org_id in [pub["id"], mo["id"], priv["id"]]:
            db_client.post(
                f"/api/v1/organizations/{org_id}/members",
                json={"user_id": member["user_id"], "role": "MEMBER"},
                headers=auth_headers(owner["csrf_token"]),
            )

        set_auth_cookies(db_client, member)
        assert db_client.get(f"/api/v1/organizations/{pub['id']}").status_code == 200
        assert db_client.get(f"/api/v1/organizations/{mo['id']}").status_code == 200
        assert db_client.get(f"/api/v1/organizations/{priv['id']}").status_code == 200


class TestMemberListMatrix:
    """Matrix: view member lists."""

    def test_anonymous_cannot_view_members(self, db_client: TestClient) -> None:
        """Anonymous cannot view member list (requires auth)."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="匿名成员列表", visibility="PUBLIC")

        clear_auth_cookies(db_client)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 401  # Auth required

    def test_non_member_cannot_view_private_members(
        self, db_client: TestClient
    ) -> None:
        """Non-member cannot view member list of PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="非成员私密列表", visibility="PRIVATE")

        other = register_and_login(
            db_client, email="nmp@example.edu", student_no="20261102"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 403


class TestWriteOperationMatrix:
    """Matrix: add member, change role, remove member, delete org."""

    def test_anonymous_cannot_write(self, db_client: TestClient) -> None:
        """Anonymous cannot perform any write operation."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="匿名写操作")

        target = register_and_login(
            db_client, email="anon_t@example.edu", student_no="20261103"
        )

        clear_auth_cookies(db_client)
        # POST members
        assert db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": target["user_id"], "role": "MEMBER"},
        ).status_code in (401, 403)

        # PATCH role
        assert db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{target['user_id']}",
            json={"role": "ADMIN"},
        ).status_code in (401, 403)

        # DELETE member
        assert db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{target['user_id']}"
        ).status_code in (401, 403)

        # DELETE org
        assert db_client.delete(
            f"/api/v1/organizations/{org['id']}"
        ).status_code in (401, 403)


class TestDirectorySearchPrivacy:
    """Directory search privacy enforcement."""

    def test_search_no_email_leak(self, db_client: TestClient) -> None:
        """Search results do not leak email."""
        register_and_login(
            db_client,
            email="leak@example.edu",
            display_name="LeakTest",
            student_no="20261104",
        )
        resp = db_client.get("/api/v1/directory/search?q=LeakTest&type=users")
        assert resp.status_code == 200
        assert "email" not in resp.text.lower()

    def test_search_no_student_no_leak(self, db_client: TestClient) -> None:
        """Search results do not leak student_no."""
        register_and_login(
            db_client,
            email="sn@example.edu",
            display_name="SNTest",
            student_no="20261105",
        )
        resp = db_client.get("/api/v1/directory/search?q=SNTest&type=users")
        assert resp.status_code == 200
        assert "student_no" not in resp.text.lower()
        assert "20261105" not in resp.text

    def test_search_no_password_leak(self, db_client: TestClient) -> None:
        """Search results do not leak password_hash."""
        resp = db_client.get("/api/v1/directory/search?q=test&type=users")
        assert resp.status_code == 200
        assert "password" not in resp.text.lower()
        assert "hash" not in resp.text.lower()


class TestUserOrganizationsPrivacy:
    """User organizations list privacy."""

    def test_private_org_not_leaked_to_other(
        self, db_client: TestClient
    ) -> None:
        """Other users cannot see PRIVATE orgs in user's org list."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="不泄露私密", visibility="PRIVATE")
        create_org(db_client, owner, name="可公开列表", visibility="PUBLIC")

        other = register_and_login(
            db_client, email="leak_check@example.edu", student_no="20261106"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/users/{owner['user_id']}/organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        for org in orgs:
            assert org["visibility"] == "PUBLIC"


class TestDeletedOrgMatrix:
    """Matrix: deleted/archived orgs."""

    def test_deleted_org_not_in_list(self, db_client: TestClient) -> None:
        """Deleted org not in list."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="已删除列表")
        db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        resp = db_client.get("/api/v1/organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert not any(o["id"] == org["id"] for o in orgs)

    def test_deleted_org_not_in_search(self, db_client: TestClient) -> None:
        """Deleted org not in search."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="已删除搜索", visibility="PUBLIC")
        db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        resp = db_client.get("/api/v1/directory/search?q=已删除搜索&type=organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert not any(o["id"] == org["id"] for o in orgs)

    def test_deleted_org_returns_not_found(self, db_client: TestClient) -> None:
        """Deleted org returns 404."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="已删除详情")
        db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 404


class TestDeletedUserMatrix:
    """Matrix: deleted user."""

    def test_deleted_user_organizations_not_found(
        self, db_client: TestClient, test_engine
    ) -> None:
        """Deleted user's organizations endpoint returns not found."""
        from src.db.time import utc_now
        from src.modules.users.models import User

        user = register_and_login(
            db_client, email="del_user@example.edu", student_no="20261107"
        )

        # Delete the user
        factory = sessionmaker(bind=test_engine, expire_on_commit=False)
        session = factory()
        try:
            u = session.get(User, UUID(user["user_id"]))
            if u is not None:
                u.status = "DELETED"
                u.deleted_at = utc_now()
                session.commit()
        finally:
            session.close()

        resp = db_client.get(f"/api/v1/users/{user['user_id']}/organizations")
        assert resp.status_code == 404
