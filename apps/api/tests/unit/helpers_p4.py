"""
Shared test helpers for P4 organization and directory tests.

Provides:
- ``register_and_login``: register a user and return cookies (access_token, csrf_token).
- ``create_org``: create an organization as a given user.
- ``auth_headers``: build headers with CSRF token for write requests.
"""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient


def register_and_login(
    client: TestClient,
    *,
    email: str = "test@example.edu",
    password: str = "SecurePass123",
    display_name: str = "测试用户",
    student_no: str = "20260001",
) -> dict[str, str]:
    """Register a user and return cookies for authenticated requests.

    Returns a dict with ``user_id``, ``access_token`` and ``csrf_token``
    cookie values. Clears existing cookies first to avoid conflicts.
    """
    # Clear any existing cookies to avoid CookieConflict with httpx
    client.cookies.clear()

    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "student_no": student_no,
            "organization_ids": [],
        },
    )
    assert resp.status_code == 201, f"Register failed: {resp.json()}"
    body = resp.json()
    user_id = body["data"]["id"]
    # The TestClient stores cookies automatically; extract them.
    access_token = client.cookies.get("access_token", "")
    csrf_token = client.cookies.get("csrf_token", "")
    return {
        "user_id": user_id,
        "access_token": access_token,
        "csrf_token": csrf_token,
    }


def auth_headers(csrf_token: str) -> dict[str, str]:
    """Build headers for a write request with CSRF token."""
    return {"Content-Type": "application/json", "X-CSRF-Token": csrf_token}


def set_auth_cookies(client: TestClient, creds: dict[str, str]) -> None:
    """Set auth cookies on the test client."""
    client.cookies.set("access_token", creds["access_token"])
    client.cookies.set("csrf_token", creds["csrf_token"])


def clear_auth_cookies(client: TestClient) -> None:
    """Clear auth cookies on the test client."""
    client.cookies.clear()


def create_org(
    client: TestClient,
    creds: dict[str, str],
    *,
    name: str = "测试组织",
    org_type: str = "CLUB",
    visibility: str = "PUBLIC",
    join_policy: str = "OPEN",
    description: str | None = None,
    capacity: int | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Create an organization and return the response data.

    Assumes ``creds`` cookies are already set on the client.
    """
    payload: dict[str, Any] = {
        "name": name,
        "type": org_type,
        "visibility": visibility,
        "join_policy": join_policy,
    }
    if description is not None:
        payload["description"] = description
    if capacity is not None:
        payload["capacity"] = capacity
    if parent_id is not None:
        payload["parent_id"] = parent_id

    resp = client.post(
        "/api/v1/organizations",
        json=payload,
        headers=auth_headers(creds["csrf_token"]),
    )
    assert resp.status_code == 201, f"Create org failed: {resp.status_code} {resp.json()}"
    return resp.json()["data"]


def register_multiple_users(
    client: TestClient, count: int, prefix: str = "user"
) -> list[dict[str, str]]:
    """Register multiple users and return their credentials."""
    users = []
    for i in range(count):
        creds = register_and_login(
            client,
            email=f"{prefix}{i}@example.edu",
            display_name=f"用户{i}",
            student_no=f"2026{i:04d}",
        )
        users.append(creds)
    return users
