"""
Unit tests for realtime reconnect and backfill (P5-11).

Tests:
- HTTP backfill path works (GET messages).
- Event dedup cache deduplicates event_ids.
- Dedup cache evicts FIFO at max size.
- Client can recover from disconnect via HTTP backfill.
- Duplicate event_id is skipped.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from src.realtime.connection_manager import EventDedupCache
from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestEventDedupCache:
    """Test the event deduplication cache."""

    def test_new_event_not_seen(self) -> None:
        """A new event_id is not in the cache."""
        cache = EventDedupCache()
        assert not cache.seen("evt_001")

    def test_seen_after_add(self) -> None:
        """An event_id is seen after being added."""
        cache = EventDedupCache()
        cache.add("evt_001")
        assert cache.seen("evt_001")

    def test_duplicate_skipped(self) -> None:
        """Duplicate event_ids are detected."""
        cache = EventDedupCache()
        cache.add("evt_001")
        assert cache.seen("evt_001")
        # Adding again should be a no-op
        cache.add("evt_001")
        assert cache.seen("evt_001")

    def test_fifo_eviction(self) -> None:
        """Cache evicts oldest entries when at capacity."""
        cache = EventDedupCache(max_size=3)
        cache.add("evt_1")
        cache.add("evt_2")
        cache.add("evt_3")
        assert cache.seen("evt_1")

        cache.add("evt_4")  # This should evict evt_1
        assert not cache.seen("evt_1")
        assert cache.seen("evt_4")

    def test_clear(self) -> None:
        """Clear removes all entries."""
        cache = EventDedupCache()
        cache.add("evt_1")
        cache.add("evt_2")
        cache.clear()
        assert not cache.seen("evt_1")
        assert not cache.seen("evt_2")


class TestHTTPBackfill:
    """Test HTTP-based message backfill after reconnect."""

    def test_http_backfill_returns_messages(
        self, db_client: TestClient
    ) -> None:
        """HTTP message API can be used for backfill."""
        alice = register_and_login(
            db_client, email="bf_a1@example.edu", student_no="20261001"
        )
        bob = register_and_login(
            db_client, email="bf_b1@example.edu", student_no="20261002"
        )

        # Create conversation
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Send 3 messages
        for i in range(3):
            db_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": f"backfill-{i}", "message_type": "TEXT"},
                headers=auth_headers(alice["csrf_token"]),
            )

        # Simulate reconnect: fetch all messages via HTTP
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages?page=1&page_size=50"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3
        assert len(data["messages"]) == 3

    def test_http_backfill_message_id_for_dedup(
        self, db_client: TestClient
    ) -> None:
        """HTTP backfill provides message_id for client-side dedup."""
        alice = register_and_login(
            db_client, email="bf_a2@example.edu", student_no="20261003"
        )
        bob = register_and_login(
            db_client, email="bf_b2@example.edu", student_no="20261004"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "dedup test", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        msg_id = resp.json()["data"]["id"]

        # Backfill returns the same message_id
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages"
        )
        assert resp.status_code == 200
        messages = resp.json()["data"]["messages"]
        assert any(m["id"] == msg_id for m in messages)
