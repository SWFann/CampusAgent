"""
Unit tests for Directory Search (P4-07).

Tests verify:
- Query too short returns DIRECTORY_QUERY_TOO_SHORT.
- Invalid type returns DIRECTORY_INVALID_TYPE.
- User search does NOT return email/student_no/password_hash.
- Disabled/deleted users not returned.
- PUBLIC org can be searched.
- MEMBERS_ONLY/PRIVATE orgs hidden from non-members.
- Members can search their MEMBERS_ONLY/PRIVATE orgs.
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


class TestSearchValidation:
    """Test search input validation."""

    def test_query_too_short(self, db_client: TestClient) -> None:
        """Query shorter than 2 chars returns DIRECTORY_QUERY_TOO_SHORT."""
        resp = db_client.get("/api/v1/directory/search?q=a")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DIRECTORY_QUERY_TOO_SHORT"

    def test_empty_query_too_short(self, db_client: TestClient) -> None:
        """Empty query returns DIRECTORY_QUERY_TOO_SHORT."""
        resp = db_client.get("/api/v1/directory/search?q=")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DIRECTORY_QUERY_TOO_SHORT"

    def test_invalid_type(self, db_client: TestClient) -> None:
        """Invalid type returns DIRECTORY_INVALID_TYPE."""
        resp = db_client.get("/api/v1/directory/search?q=ab&type=invalid")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DIRECTORY_INVALID_TYPE"


class TestUserSearch:
    """Test user search privacy."""

    def test_user_search_no_email(self, db_client: TestClient) -> None:
        """User search does not return email or student_no."""
        register_and_login(
            db_client,
            email="searchable@example.edu",
            display_name="Searchable User",
            student_no="20267001",
        )

        resp = db_client.get("/api/v1/directory/search?q=Searchable&type=users")
        assert resp.status_code == 200
        body = resp.text.lower()
        assert "email" not in body
        assert "student_no" not in body
        assert "password" not in body

    def test_user_search_returns_display_name(self, db_client: TestClient) -> None:
        """User search returns display_name."""
        register_and_login(
            db_client,
            email="visible@example.edu",
            display_name="Visible Person",
            student_no="20267002",
        )

        resp = db_client.get("/api/v1/directory/search?q=Visible&type=users")
        assert resp.status_code == 200
        users = resp.json()["data"]["users"]
        assert len(users) >= 1
        assert any(u["display_name"] == "Visible Person" for u in users)

    def test_deleted_user_not_returned(
        self, db_client: TestClient, test_engine
    ) -> None:
        """Deleted users are not returned in search."""
        from uuid import UUID

        from sqlalchemy.orm import sessionmaker

        from src.db.time import utc_now
        from src.modules.users.models import User

        user_creds = register_and_login(
            db_client,
            email="deleted@example.edu",
            display_name="DeletedUser",
            student_no="20267003",
        )

        # Mark user as deleted
        factory = sessionmaker(bind=test_engine, expire_on_commit=False)
        session = factory()
        try:
            user = session.get(User, UUID(user_creds["user_id"]))
            if user is not None:
                user.status = "DELETED"
                user.deleted_at = utc_now()
                session.commit()
        finally:
            session.close()

        resp = db_client.get("/api/v1/directory/search?q=DeletedUser&type=users")
        assert resp.status_code == 200
        users = resp.json()["data"]["users"]
        assert not any(u["display_name"] == "DeletedUser" for u in users)


class TestOrganizationSearch:
    """Test organization search with visibility filtering."""

    def test_public_org_searchable(self, db_client: TestClient) -> None:
        """PUBLIC org can be searched by anyone."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="公开搜索组织", visibility="PUBLIC")

        clear_auth_cookies(db_client)
        resp = db_client.get("/api/v1/directory/search?q=公开搜索&type=organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert any(o["name"] == "公开搜索组织" for o in orgs)

    def test_private_org_hidden_from_non_member(
        self, db_client: TestClient
    ) -> None:
        """PRIVATE org is not visible to non-members in search."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="私密搜索组织", visibility="PRIVATE")

        # Another user searches
        other = register_and_login(
            db_client, email="other_s@example.edu", student_no="20267004"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get("/api/v1/directory/search?q=私密搜索&type=organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert not any(o["name"] == "私密搜索组织" for o in orgs)

    def test_members_only_org_visible_to_member(
        self, db_client: TestClient
    ) -> None:
        """MEMBERS_ONLY org is visible to members in search."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client, owner, name="成员可见搜索", visibility="MEMBERS_ONLY"
        )

        member = register_and_login(
            db_client, email="mo_member@example.edu", student_no="20267005"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, member)
        resp = db_client.get("/api/v1/directory/search?q=成员可见&type=organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert any(o["name"] == "成员可见搜索" for o in orgs)

    def test_members_only_org_hidden_from_non_member(
        self, db_client: TestClient
    ) -> None:
        """MEMBERS_ONLY org is hidden from non-members in search."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(
            db_client, owner, name="仅成员搜索", visibility="MEMBERS_ONLY"
        )

        other = register_and_login(
            db_client, email="mo_other@example.edu", student_no="20267006"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get("/api/v1/directory/search?q=仅成员&type=organizations")
        assert resp.status_code == 200
        orgs = resp.json()["data"]["organizations"]
        assert not any(o["name"] == "仅成员搜索" for o in orgs)


class TestSearchAll:
    """Test searching both users and organizations."""

    def test_search_all_returns_both(self, db_client: TestClient) -> None:
        """Search type=all returns both users and organizations."""
        owner = register_and_login(
            db_client,
            email="all@example.edu",
            display_name="AllTest User",
            student_no="20267007",
        )
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="AllTest组织", visibility="PUBLIC")

        resp = db_client.get("/api/v1/directory/search?q=AllTest&type=all")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["users"]) >= 1
        assert len(data["organizations"]) >= 1
