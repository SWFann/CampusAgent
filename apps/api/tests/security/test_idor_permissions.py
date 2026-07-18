"""P12-03: IDOR and authorization boundary regression.

Verifies that a user cannot access another user's resources across:
- organizations (private org read by non-member)
- conversations (read another user's conversation)
- memories (read/patch/delete another user's memory)
- admin endpoints (non-admin denied)

Design: cross-user access must return 403 or 404 — never 200 with
another user's private data. We do not assert the exact status code
(403 vs 404) because returning 404 to hide existence is also acceptable.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)

# ---------------------------------------------------------------------------
# 1. Cross-organization IDOR
# ---------------------------------------------------------------------------


class TestCrossOrganizationIdor:
    def test_non_member_cannot_read_private_org(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_org_owner@example.edu", student_no="20263001"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="IDOR 私有组织",
            visibility="PRIVATE",
            join_policy="INVITE_ONLY",
        )
        org_id = org["id"]

        intruder = register_and_login(
            db_client, email="idor_intruder@example.edu", student_no="20263002"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.get(f"/api/v1/organizations/{org_id}")
        assert resp.status_code in (403, 404)

    def test_non_member_cannot_patch_org(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_patch_owner@example.edu", student_no="20263003"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="IDOR Patch Org",
            visibility="PRIVATE",
            join_policy="INVITE_ONLY",
        )
        org_id = org["id"]

        intruder = register_and_login(
            db_client, email="idor_patch_intruder@example.edu", student_no="20263004"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.patch(
            f"/api/v1/organizations/{org_id}",
            json={"description": "hijacked"},
            headers=auth_headers(intruder["csrf_token"]),
        )
        assert resp.status_code in (403, 404)

    def test_non_member_cannot_delete_org(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_del_owner@example.edu", student_no="20263005"
        )
        set_auth_cookies(db_client, owner)
        org = create_org(
            db_client,
            owner,
            name="IDOR Del Org",
            visibility="PRIVATE",
            join_policy="INVITE_ONLY",
        )
        org_id = org["id"]

        intruder = register_and_login(
            db_client, email="idor_del_intruder@example.edu", student_no="20263006"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.delete(
            f"/api/v1/organizations/{org_id}",
            headers=auth_headers(intruder["csrf_token"]),
        )
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# 2. Cross-conversation IDOR
# ---------------------------------------------------------------------------


class TestCrossConversationIdor:
    def test_non_participant_cannot_read_conversation(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_conv_owner@example.edu", student_no="20263010"
        )
        set_auth_cookies(db_client, owner)
        # Create a group conversation
        resp = db_client.post(
            "/api/v1/conversations",
            json={"title": "IDOR Conv", "organization_id": None},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        intruder = register_and_login(
            db_client, email="idor_conv_intruder@example.edu", student_no="20263011"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# 3. Cross-memory IDOR
# ---------------------------------------------------------------------------


class TestCrossMemoryIdor:
    def _create_memory(self, client: TestClient, creds: dict[str, str]) -> str:
        set_auth_cookies(client, creds)
        resp = client.post(
            "/memories",
            json={
                "category": "PREFERENCE",
                "content": "private content for idor",
                "sensitivity_level": "INTERNAL",
            },
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code in (200, 201), f"create memory failed: {resp.json()}"
        return resp.json()["data"]["id"]

    def test_non_owner_cannot_read_memory(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_mem_owner@example.edu", student_no="20263020"
        )
        mem_id = self._create_memory(db_client, owner)

        intruder = register_and_login(
            db_client, email="idor_mem_intruder@example.edu", student_no="20263021"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.get(f"/memories/{mem_id}")
        assert resp.status_code in (403, 404)

    def test_non_owner_cannot_patch_memory(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_mem_p_owner@example.edu", student_no="20263022"
        )
        mem_id = self._create_memory(db_client, owner)

        intruder = register_and_login(
            db_client, email="idor_mem_p_intruder@example.edu", student_no="20263023"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.patch(
            f"/memories/{mem_id}",
            json={"content": "hijacked"},
            headers=auth_headers(intruder["csrf_token"]),
        )
        assert resp.status_code in (403, 404)

    def test_non_owner_cannot_delete_memory(self, db_client: TestClient):
        owner = register_and_login(
            db_client, email="idor_mem_d_owner@example.edu", student_no="20263024"
        )
        mem_id = self._create_memory(db_client, owner)

        intruder = register_and_login(
            db_client, email="idor_mem_d_intruder@example.edu", student_no="20263025"
        )
        set_auth_cookies(db_client, intruder)
        resp = db_client.delete(
            f"/memories/{mem_id}",
            headers=auth_headers(intruder["csrf_token"]),
        )
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# 4. Admin endpoint access control
# ---------------------------------------------------------------------------


class TestAdminAccessControl:
    def test_regular_user_cannot_list_admin_nodes(self, db_client: TestClient):
        student = register_and_login(
            db_client, email="idor_admin_student@example.edu", student_no="20263030"
        )
        set_auth_cookies(db_client, student)
        resp = db_client.get("/api/v1/admin/nodes")
        assert resp.status_code in (403, 404)

    def test_regular_user_cannot_create_admin_node(self, db_client: TestClient):
        student = register_and_login(
            db_client, email="idor_admin_c_student@example.edu", student_no="20263031"
        )
        set_auth_cookies(db_client, student)
        resp = db_client.post(
            "/api/v1/admin/nodes",
            json={"name": "evil-node", "endpoint": "http://evil:8080"},
            headers=auth_headers(student["csrf_token"]),
        )
        assert resp.status_code in (403, 404)

    def test_regular_user_cannot_list_admin_models(self, db_client: TestClient):
        student = register_and_login(
            db_client, email="idor_admin_m_student@example.edu", student_no="20263032"
        )
        set_auth_cookies(db_client, student)
        resp = db_client.get("/api/v1/admin/models")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# 5. Non-existent resource returns 404, not 500
# ---------------------------------------------------------------------------


class TestNonExistentResourceHandling:
    def test_nonexistent_org_returns_404_not_500(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="idor_404@example.edu", student_no="20263040"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (403, 404)
        assert resp.status_code != 500

    def test_nonexistent_conversation_returns_404_not_500(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="idor_404c@example.edu", student_no="20263041"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (403, 404)
        assert resp.status_code != 500
