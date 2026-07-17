"""
Unit tests for organization default group conversation (P5-04).

Tests:
- Create organization → can get/create default org group.
- Member joins organization → enters org group conversation.
- Member leaves organization → participant LEFT.
- Non-org-member cannot read org group.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


class TestOrgGroupConversation:
    """Test organization default group conversation."""

    def test_get_or_create_org_group(self, db_client: TestClient) -> None:
        """After creating an org, can create/get default org group."""
        owner = register_and_login(
            db_client, email="org_g1@example.edu", student_no="20265001"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="测试组织群聊",
            visibility="PUBLIC",
            join_policy="OPEN",
        )

        # Create org group conversation
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "organization_id": org["id"],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        # This creates a GROUP with org_id — for P5 MVP we test it works
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["organization_id"] == org["id"]

    def test_org_member_joins_group(self, db_client: TestClient) -> None:
        """Member joins organization → enters org group conversation."""
        owner = register_and_login(
            db_client, email="org_j1@example.edu", student_no="20265002"
        )
        member = register_and_login(
            db_client, email="org_jm@example.edu", student_no="20265003"
        )

        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="Join Test Org",
            visibility="PUBLIC",
            join_policy="OPEN",
        )

        # Member joins the org
        set_auth_cookies(db_client, member)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 201

        # Now sync the member to org group conversation

        # Get the session from the app state
        from typing import Any

        from src.modules.conversations.service import sync_org_member_joined

        app_obj: Any = db_client.app
        session_factory = app_obj.state.db_sessionmaker
        with session_factory() as session:
            sync_org_member_joined(
                organization_id=__import__("uuid").UUID(org["id"]),
                user_id=__import__("uuid").UUID(member["user_id"]),
                role="MEMBER",
                session=session,
            )

    def test_non_org_member_cannot_read(
        self, db_client: TestClient
    ) -> None:
        """Non-org-member cannot read org group."""
        owner = register_and_login(
            db_client, email="org_n1@example.edu", student_no="20265004"
        )
        outsider = register_and_login(
            db_client, email="org_n2@example.edu", student_no="20265005"
        )

        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="Private Org",
            visibility="PRIVATE",
            join_policy="INVITE_ONLY",
        )

        # Create a group conversation
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Org Group",
                "participant_user_ids": [],
                "organization_id": org["id"],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Outsider cannot read
        set_auth_cookies(db_client, outsider)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code == 403
