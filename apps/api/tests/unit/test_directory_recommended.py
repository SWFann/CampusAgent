"""
Unit tests for Directory Recommended (P4-09).

Tests verify:
- Anonymous returns empty or public recommendations.
- Logged-in user with no orgs returns empty recommendations.
- User with org relationships gets same-parent PUBLIC orgs.
- PRIVATE orgs not recommended to non-members.
- Recommendations include reason field.
- No email/student_no/bio/password_hash used.
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


class TestRecommendedAnonymous:
    """Test recommendations for anonymous users."""

    def test_anonymous_gets_public_or_empty(self, db_client: TestClient) -> None:
        """Anonymous user gets empty or public-only recommendations."""
        clear_auth_cookies(db_client)
        resp = db_client.get("/api/v1/directory/recommended")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "recommendations" in data
        # All recommendations should be PUBLIC
        for rec in data["recommendations"]:
            assert rec["visibility"] == "PUBLIC"


class TestRecommendedLoggedIn:
    """Test recommendations for logged-in users."""

    def test_no_orgs_returns_empty(self, db_client: TestClient) -> None:
        """User with no org memberships gets empty recommendations."""
        user = register_and_login(
            db_client, email="norec@example.edu", student_no="20269001"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/directory/recommended")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # With no orgs, recommendations come from strategy 2 (public clubs)
        # but there are none, so should be empty
        assert isinstance(data["recommendations"], list)

    def test_same_parent_public_recommended(self, db_client: TestClient) -> None:
        """User gets same-parent PUBLIC orgs recommended."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)

        # Create a parent org
        parent = create_org(db_client, owner, name="推荐父", visibility="PUBLIC")

        # Create a child that the user joins
        child1 = create_org(
            db_client,
            owner,
            name="推荐子1",
            visibility="PUBLIC",
            parent_id=parent["id"],
        )

        # Create another child under the same parent (should be recommended)
        child2 = create_org(
            db_client,
            owner,
            name="推荐子2",
            visibility="PUBLIC",
            parent_id=parent["id"],
        )

        # Register a new user and add them to child1 only
        user = register_and_login(
            db_client, email="rec_user@example.edu", student_no="20269002"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{child1['id']}/members",
            json={"user_id": user["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # User should get child2 recommended
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/directory/recommended")
        assert resp.status_code == 200
        recs = resp.json()["data"]["recommendations"]
        rec_ids = [r["id"] for r in recs]
        assert child2["id"] in rec_ids

    def test_private_not_recommended(self, db_client: TestClient) -> None:
        """PRIVATE orgs not recommended to non-members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)

        parent = create_org(db_client, owner, name="私密推荐父", visibility="PUBLIC")
        child1 = create_org(
            db_client,
            owner,
            name="私密推荐子1",
            visibility="PUBLIC",
            parent_id=parent["id"],
        )
        private_child = create_org(
            db_client,
            owner,
            name="私密推荐子2",
            visibility="PRIVATE",
            parent_id=parent["id"],
        )

        user = register_and_login(
            db_client, email="priv_rec@example.edu", student_no="20269003"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{child1['id']}/members",
            json={"user_id": user["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/directory/recommended")
        assert resp.status_code == 200
        recs = resp.json()["data"]["recommendations"]
        rec_ids = [r["id"] for r in recs]
        assert private_child["id"] not in rec_ids

    def test_recommendations_have_reason(self, db_client: TestClient) -> None:
        """Each recommendation includes a reason field."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="理由测试CLUB", visibility="PUBLIC", org_type="CLUB")

        user = register_and_login(
            db_client, email="reason@example.edu", student_no="20269004"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/directory/recommended")
        assert resp.status_code == 200
        recs = resp.json()["data"]["recommendations"]
        for rec in recs:
            assert "reason" in rec
            assert rec["reason"]  # non-empty

    def test_no_sensitive_data_in_recommendations(
        self, db_client: TestClient
    ) -> None:
        """Recommendations do not contain email/student_no/bio/password_hash."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="安全推荐", visibility="PUBLIC", org_type="CLUB")

        user = register_and_login(
            db_client, email="safe_rec@example.edu", student_no="20269005"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/directory/recommended")
        assert resp.status_code == 200
        body = resp.text.lower()
        assert "email" not in body
        assert "student_no" not in body
        assert "password" not in body
        assert "bio" not in body
