"""
Unit tests for group conversation creation (P5-03).

Tests:
- Four-person group chat creation → success.
- Creator is OWNER.
- Initial members are deduplicated.
- Non-OWNER cannot add members.
- OWNER can remove MEMBER.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestGroupConversation:
    """Test group conversation creation and participant management."""

    def test_create_group_conversation(self, db_client: TestClient) -> None:
        """Four-person group chat creation → success."""
        owner = register_and_login(
            db_client, email="grp_owner@example.edu", student_no="20264001"
        )
        m1 = register_and_login(
            db_client, email="grp_m1@example.edu", student_no="20264002"
        )
        m2 = register_and_login(
            db_client, email="grp_m2@example.edu", student_no="20264003"
        )
        m3 = register_and_login(
            db_client, email="grp_m3@example.edu", student_no="20264004"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "测试群聊",
                "participant_user_ids": [
                    m1["user_id"],
                    m2["user_id"],
                    m3["user_id"],
                ],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["type"] == "GROUP"
        assert data["title"] == "测试群聊"
        assert data["id"]

    def test_creator_is_owner(self, db_client: TestClient) -> None:
        """Creator should have OWNER role."""
        owner = register_and_login(
            db_client, email="grp_own2@example.edu", student_no="20264005"
        )
        m1 = register_and_login(
            db_client, email="grp_m4@example.edu", student_no="20264006"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Owner Test",
                "participant_user_ids": [m1["user_id"]],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # List participants and check owner role
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/participants",
        )
        assert resp.status_code == 200
        participants = resp.json()["data"]["participants"]
        owner_part = [p for p in participants if p["participant_user_id"] == owner["user_id"]]
        assert len(owner_part) == 1
        assert owner_part[0]["role"] == "OWNER"

    def test_duplicate_members_deduplicated(
        self, db_client: TestClient
    ) -> None:
        """Duplicate user IDs should be deduplicated."""
        owner = register_and_login(
            db_client, email="grp_dup@example.edu", student_no="20264007"
        )
        m1 = register_and_login(
            db_client, email="grp_dupm@example.edu", student_no="20264008"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Dedup Test",
                "participant_user_ids": [
                    m1["user_id"],
                    m1["user_id"],
                    m1["user_id"],
                ],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/participants",
        )
        assert resp.status_code == 200
        participants = resp.json()["data"]["participants"]
        # Owner + 1 unique member = 2
        assert len(participants) == 2

    def test_non_owner_cannot_add_member(
        self, db_client: TestClient
    ) -> None:
        """Non-OWNER cannot add members."""
        owner = register_and_login(
            db_client, email="grp_no@example.edu", student_no="20264009"
        )
        m1 = register_and_login(
            db_client, email="grp_nom@example.edu", student_no="20264010"
        )
        outsider = register_and_login(
            db_client, email="grp_out@example.edu", student_no="20264011"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Perm Test",
                "participant_user_ids": [m1["user_id"]],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Outsider (non-participant) tries to add a member
        set_auth_cookies(db_client, outsider)
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/participants",
            json={"user_id": owner["user_id"], "role": "MEMBER"},
            headers=auth_headers(outsider["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_owner_can_remove_member(
        self, db_client: TestClient
    ) -> None:
        """OWNER can remove a MEMBER."""
        owner = register_and_login(
            db_client, email="grp_rm@example.edu", student_no="20264012"
        )
        m1 = register_and_login(
            db_client, email="grp_rmm@example.edu", student_no="20264013"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Remove Test",
                "participant_user_ids": [m1["user_id"]],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Owner removes m1
        resp = db_client.delete(
            f"/api/v1/conversations/{conv_id}/participants/{m1['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 204

        # Verify m1 is no longer an active participant
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/participants",
        )
        assert resp.status_code == 200
        participants = resp.json()["data"]["participants"]
        active = [p for p in participants if p["status"] == "ACTIVE"]
        assert len(active) == 1  # Only owner remains
