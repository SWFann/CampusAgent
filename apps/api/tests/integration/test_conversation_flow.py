"""
Integration tests for the full conversation flow (P5-13).

Tests verify the complete end-to-end user journeys:
- Private chat: create → send message → list messages → delete message
- Group chat: create → add participant → remove participant → send messages
- Non-member cannot read messages or list participants
- Message pagination across multiple pages
- Idempotent message write
- Deleted message hides content
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestPrivateChatFlow:
    """End-to-end private chat flow."""

    def test_full_private_chat_flow(self, db_client: TestClient) -> None:
        """Alice creates a private chat with Bob, sends a message, lists it, deletes it."""
        alice = register_and_login(
            db_client, email="flow_pv_a@example.edu", student_no="20267001"
        )
        bob = register_and_login(
            db_client, email="flow_pv_b@example.edu", student_no="20267002"
        )

        # 1. Alice creates a private conversation with Bob
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv = resp.json()["data"]
        conv_id = conv["id"]
        assert conv["type"] == "PRIVATE"
        assert conv["status"] == "ACTIVE"

        # 2. Alice sends a message
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Hello Bob!", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        msg = resp.json()["data"]
        assert msg["content"] == "Hello Bob!"
        assert msg["sender_user_id"] == alice["user_id"]
        assert msg["status"] == "ACTIVE"
        msg_id = msg["id"]

        # 3. Bob can list messages
        set_auth_cookies(db_client, bob)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["messages"][0]["content"] == "Hello Bob!"

        # 4. Alice deletes the message
        set_auth_cookies(db_client, alice)
        resp = db_client.delete(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}",
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 204

        # 5. List messages — deleted message hides content
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        messages = resp.json()["data"]["messages"]
        assert len(messages) == 1
        assert messages[0]["status"] == "DELETED"
        assert messages[0]["content"] is None

    def test_private_chat_idempotent_reuse(self, db_client: TestClient) -> None:
        """Creating the same private chat twice returns the same conversation."""
        alice = register_and_login(
            db_client, email="flow_pv_c@example.edu", student_no="20267003"
        )
        bob = register_and_login(
            db_client, email="flow_pv_d@example.edu", student_no="20267004"
        )

        # Alice creates a private conversation with Bob
        set_auth_cookies(db_client, alice)
        resp1 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp1.status_code == 201
        conv1_id = resp1.json()["data"]["id"]

        # Alice creates again — should return the same conversation
        resp2 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp2.status_code == 201
        conv2_id = resp2.json()["data"]["id"]
        assert conv1_id == conv2_id

        # Bob creates from his side — also returns the same conversation
        set_auth_cookies(db_client, bob)
        resp3 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": alice["user_id"]},
            headers=auth_headers(bob["csrf_token"]),
        )
        assert resp3.status_code == 201
        conv3_id = resp3.json()["data"]["id"]
        assert conv1_id == conv3_id

    def test_non_member_cannot_read_private_chat(
        self, db_client: TestClient
    ) -> None:
        """A non-member cannot read a private conversation's messages."""
        alice = register_and_login(
            db_client, email="flow_pv_e@example.edu", student_no="20267005"
        )
        bob = register_and_login(
            db_client, email="flow_pv_f@example.edu", student_no="20267006"
        )
        carol = register_and_login(
            db_client, email="flow_pv_g@example.edu", student_no="20267007"
        )

        # Alice creates a private conversation with Bob
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Alice sends a message
        db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "secret message"},
            headers=auth_headers(alice["csrf_token"]),
        )

        # Carol (non-member) tries to get the conversation
        set_auth_cookies(db_client, carol)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code == 403

        # Carol tries to list messages
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 403

        # Carol tries to list participants
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/participants")
        assert resp.status_code == 403


class TestGroupChatFlow:
    """End-to-end group chat flow."""

    def test_full_group_chat_flow(self, db_client: TestClient) -> None:
        """Create a group, add/remove participants, send messages."""
        owner = register_and_login(
            db_client, email="flow_gp_o@example.edu", student_no="20267010"
        )
        m1 = register_and_login(
            db_client, email="flow_gp_1@example.edu", student_no="20267011"
        )
        m2 = register_and_login(
            db_client, email="flow_gp_2@example.edu", student_no="20267012"
        )
        m3 = register_and_login(
            db_client, email="flow_gp_3@example.edu", student_no="20267013"
        )
        outsider = register_and_login(
            db_client, email="flow_gp_x@example.edu", student_no="20267014"
        )

        # 1. Owner creates a group with 3 initial members
        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Group Chat Flow",
                "participant_user_ids": [m1["user_id"], m2["user_id"]],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv = resp.json()["data"]
        conv_id = conv["id"]
        assert conv["type"] == "GROUP"
        assert conv["title"] == "Group Chat Flow"

        # 2. List participants — owner + 2 members = 3
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/participants")
        assert resp.status_code == 200
        participants = resp.json()["data"]["participants"]
        assert len(participants) == 3

        # Verify owner role
        owner_part = [p for p in participants if p["participant_user_id"] == owner["user_id"]]
        assert len(owner_part) == 1
        assert owner_part[0]["role"] == "OWNER"

        # 3. Owner adds m3
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/participants",
            json={"user_id": m3["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201

        # 4. List participants — now 4
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/participants")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 4

        # 5. m1 sends a message
        set_auth_cookies(db_client, m1)
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Hi group!", "message_type": "TEXT"},
            headers=auth_headers(m1["csrf_token"]),
        )
        assert resp.status_code == 201

        # 6. m2 can read the message
        set_auth_cookies(db_client, m2)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 1

        # 7. Outsider cannot read messages
        set_auth_cookies(db_client, outsider)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 403

        # 8. Outsider cannot send messages
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "intrusion"},
            headers=auth_headers(outsider["csrf_token"]),
        )
        assert resp.status_code == 403

        # 9. Owner removes m1
        set_auth_cookies(db_client, owner)
        resp = db_client.delete(
            f"/api/v1/conversations/{conv_id}/participants/{m1['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 204

        # 10. m1 (now removed) cannot send messages
        set_auth_cookies(db_client, m1)
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "after removal"},
            headers=auth_headers(m1["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_non_owner_cannot_add_participant(
        self, db_client: TestClient
    ) -> None:
        """A non-owner member cannot add participants."""
        owner = register_and_login(
            db_client, email="flow_gp_a@example.edu", student_no="20267020"
        )
        member = register_and_login(
            db_client, email="flow_gp_b@example.edu", student_no="20267021"
        )
        target = register_and_login(
            db_client, email="flow_gp_c@example.edu", student_no="20267022"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={"title": "Perm Test", "participant_user_ids": [member["user_id"]]},
            headers=auth_headers(owner["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Member (not owner) tries to add target
        set_auth_cookies(db_client, member)
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/participants",
            json={"user_id": target["user_id"], "role": "MEMBER"},
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 403


class TestMessagePaginationFlow:
    """Test message pagination in an integration context."""

    def test_message_pagination_multi_page(
        self, db_client: TestClient
    ) -> None:
        """Messages span multiple pages correctly."""
        alice = register_and_login(
            db_client, email="flow_pg_a@example.edu", student_no="20267030"
        )
        bob = register_and_login(
            db_client, email="flow_pg_b@example.edu", student_no="20267031"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Send 55 messages (page_size=50 by default)
        for i in range(55):
            db_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": f"message-{i}", "message_type": "TEXT"},
                headers=auth_headers(alice["csrf_token"]),
            )

        # Page 1 — 50 messages, total=55
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages?page=1&page_size=50"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 55
        assert len(data["messages"]) == 50
        assert data["page"] == 1
        assert data["page_size"] == 50

        # Page 2 — 5 messages
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages?page=2&page_size=50"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 55
        assert len(data["messages"]) == 5
        assert data["page"] == 2

    def test_conversation_list_pagination(
        self, db_client: TestClient
    ) -> None:
        """Conversation list supports pagination."""
        alice = register_and_login(
            db_client, email="flow_pl_a@example.edu", student_no="20267049"
        )

        set_auth_cookies(db_client, alice)

        # Create 5 private conversations with 5 different users
        for i in range(5):
            other = register_and_login(
                db_client,
                email=f"flow_pl_b{i}@example.edu",
                student_no=f"2026705{i}",
            )
            set_auth_cookies(db_client, alice)
            db_client.post(
                "/api/v1/conversations/private",
                json={"target_user_id": other["user_id"]},
                headers=auth_headers(alice["csrf_token"]),
            )

        # Page 1 — 5 conversations
        resp = db_client.get(
            "/api/v1/conversations?page=1&page_size=10"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["conversations"]) == 5

        # Each conversation has participant_count
        for conv in data["conversations"]:
            assert conv["participant_count"] == 2
            assert conv["type"] == "PRIVATE"
