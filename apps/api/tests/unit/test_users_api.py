"""
Unit tests for Users API (P3-07) and UserRegistered event (P3-08).

Tests verify:
- GET /users/{id} returns public profile.
- GET /users/{id} for non-existent returns 404.
- PATCH /users/{id} as self updates profile.
- PATCH /users/{id} as other user fails with PERMISSION_DENIED.
- PATCH /users/{id} requires CSRF.
- UserRegistered event is published on register.
- UserRegistered event has correct fields.
"""

from __future__ import annotations

from typing import TypedDict

from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class RegisteredUserResult(TypedDict):
    cookies: dict[str, str]
    user_id: str


def _register_user(
    client: TestClient,
    email: str = "userapi@example.edu",
    student_no: str = "20260400",
) -> RegisteredUserResult:
    """Register a user and return cookies."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "display_name": "User API",
            "student_no": student_no,
            "organization_ids": [],
        },
    )
    assert resp.status_code == 201
    cookies: dict[str, str] = {}
    for header in resp.headers.get_list("set-cookie"):
        name_value = header.split(";")[0]
        name, value = name_value.split("=", 1)
        cookies[name.strip()] = value.strip()
    body = resp.json()
    user_id = body["data"]["id"]
    return {"cookies": cookies, "user_id": user_id}


def _make_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ---------------------------------------------------------------------------
# 1. GET /users/{id}
# ---------------------------------------------------------------------------


class TestGetUser:
    def test_get_user_returns_public_profile(self, db_client: TestClient):
        """GET /users/{id} returns public profile."""
        result = _register_user(db_client)
        user_id = result["user_id"]
        resp = db_client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["display_name"] == "User API"
        # Must NOT include email or student_no
        assert "email" not in data
        assert "student_no" not in data

    def test_get_nonexistent_user_returns_404(self, db_client: TestClient):
        """GET /users/{nonexistent} returns 404."""
        from uuid import uuid4

        resp = db_client.get(f"/api/v1/users/{uuid4()}")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# 2. PATCH /users/{id}
# ---------------------------------------------------------------------------


class TestPatchUser:
    def test_patch_self_updates_profile(self, db_client: TestClient):
        """PATCH as self updates profile."""
        result = _register_user(db_client)
        cookies = result["cookies"]
        user_id = result["user_id"]
        csrf = cookies.get("csrf_token", "")

        resp = db_client.patch(
            f"/api/v1/users/{user_id}",
            json={"display_name": "Updated Name", "bio": "New bio"},
            headers={
                "Cookie": _make_cookie_header(cookies),
                "X-CSRF-Token": csrf,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["display_name"] == "Updated Name"

    def test_patch_other_user_denied(self, db_client: TestClient):
        """PATCH as a different user returns PERMISSION_DENIED."""
        result1 = _register_user(db_client, email="user1@example.edu", student_no="20260401")
        result2 = _register_user(db_client, email="user2@example.edu", student_no="20260402")

        cookies2 = result2["cookies"]
        csrf2 = cookies2.get("csrf_token", "")
        user_id1 = result1["user_id"]

        resp = db_client.patch(
            f"/api/v1/users/{user_id1}",
            json={"display_name": "Hacked"},
            headers={
                "Cookie": _make_cookie_header(cookies2),
                "X-CSRF-Token": csrf2,
            },
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "PERMISSION_DENIED"

    def test_patch_requires_csrf(self, db_client: TestClient):
        """PATCH without CSRF returns CSRF_TOKEN_MISSING."""
        result = _register_user(db_client)
        cookies = result["cookies"]
        user_id = result["user_id"]

        resp = db_client.patch(
            f"/api/v1/users/{user_id}",
            json={"display_name": "Updated"},
            headers={"Cookie": _make_cookie_header(cookies)},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "CSRF_TOKEN_MISSING"


# ---------------------------------------------------------------------------
# 3. UserRegistered event (P3-08)
# ---------------------------------------------------------------------------


class TestUserRegisteredEvent:
    def test_register_publishes_user_registered_event(self, db_client: TestClient):
        """Registration publishes UserRegistered on the shared event bus."""
        from src.events.bus import default_event_bus
        from src.modules.users.events import UserRegistered

        class Recorder:
            def __init__(self) -> None:
                self.events: list[UserRegistered] = []

            def handle(self, event):
                self.events.append(event)

        recorder = Recorder()
        default_event_bus.subscribe(UserRegistered, recorder)

        result = _register_user(
            db_client,
            email="event-published@example.edu",
            student_no="20260499",
        )

        assert len(recorder.events) == 1
        assert str(recorder.events[0].user_id) == result["user_id"]

    def test_event_has_correct_fields(self):
        """UserRegistered event has all required fields."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.modules.users.events import UserRegistered, create_user_registered_event

        user_id = uuid4()
        email = "test@example.edu"
        now = datetime.now(UTC)

        event = create_user_registered_event(user_id, email, now)

        assert isinstance(event, UserRegistered)
        assert event.user_id == user_id
        assert len(event.email_hash) == 64  # SHA-256 hex
        assert event.occurred_at == now
        assert len(event.event_id) > 0  # non-empty UUID string

    def test_event_id_is_unique(self):
        """Each call produces a unique event_id."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.modules.users.events import create_user_registered_event

        now = datetime.now(UTC)
        user_id = uuid4()

        event1 = create_user_registered_event(user_id, "a@b.edu", now)
        event2 = create_user_registered_event(user_id, "a@b.edu", now)

        assert event1.event_id != event2.event_id

    def test_email_not_in_event(self):
        """The event must not contain the plaintext email."""
        from dataclasses import asdict
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.modules.users.events import create_user_registered_event

        email = "plaintext@example.edu"
        event = create_user_registered_event(uuid4(), email, datetime.now(UTC))

        # The event dict must not contain the raw email
        event_dict = asdict(event)
        assert email not in str(event_dict)
        assert "email" not in event_dict  # only email_hash
