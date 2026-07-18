"""Regression coverage for frontend-facing route compatibility."""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import register_and_login, set_auth_cookies


def _login(client: TestClient) -> None:
    creds = register_and_login(
        client,
        email="frontend_routes@example.edu",
        student_no="20269901",
    )
    set_auth_cookies(client, creds)


def test_frontend_core_paths_are_versioned(db_client: TestClient) -> None:
    """Core pages request /api/v1/* paths; they must not 404."""
    _login(db_client)

    for path in [
        "/api/v1/agents",
        "/api/v1/agents/me",
        "/api/v1/memories",
        "/api/v1/audit/me",
    ]:
        resp = db_client.get(path)
        assert resp.status_code == 200, f"{path} returned {resp.status_code}"


def test_dorm_dinner_shortcuts_match_frontend_paths(db_client: TestClient) -> None:
    """The demo dinner pages use friendly shortcut routes without UUIDs."""
    _login(db_client)

    status_resp = db_client.get("/api/v1/scenes/dorm_dinner/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()["data"]
    assert status_data["id"]
    assert status_data["participant_count"] >= 1

    prefs_resp = db_client.get("/api/v1/scenes/dorm_dinner/preferences")
    assert prefs_resp.status_code == 200
    assert isinstance(prefs_resp.json()["data"], list)

    submit_resp = db_client.post(
        "/api/v1/scenes/dorm_dinner/preferences",
        json={
            "budget_range": "20-50",
            "dietary_restrictions": ["不吃辣"],
            "preferred_time": "18:00",
        },
    )
    assert submit_resp.status_code == 201

    candidates_resp = db_client.get("/api/v1/scenes/dorm_dinner/candidates")
    assert candidates_resp.status_code == 200
    candidates = candidates_resp.json()["data"]
    assert candidates
    assert "public_reasons" in candidates[0]

    votes_resp = db_client.get("/api/v1/scenes/dorm_dinner/votes")
    assert votes_resp.status_code == 200

    confirmation_resp = db_client.get("/api/v1/scenes/dorm_dinner/confirmation")
    assert confirmation_resp.status_code == 200
