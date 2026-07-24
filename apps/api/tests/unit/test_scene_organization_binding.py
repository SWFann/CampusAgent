"""Organization-bound collaboration lifecycle tests."""

from __future__ import annotations

from starlette.testclient import TestClient

from src.modules.scenes.plugins import campus_structured_plugins
from src.modules.scenes.registry import get_scene_registry
from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


def test_group_scene_invites_active_members_and_appears_in_their_library(
    db_client: TestClient,
) -> None:
    registry = get_scene_registry()
    if not registry.is_enabled("time_poll"):
        registry.register(campus_structured_plugins()[0])

    owner = register_and_login(db_client)
    set_auth_cookies(db_client, owner)
    organization = create_org(db_client, owner, name="协作绑定测试")
    member = register_and_login(
        db_client,
        email="scene-member@example.edu",
        student_no="20265110",
    )

    set_auth_cookies(db_client, owner)
    add_member = db_client.post(
        f"/api/v1/organizations/{organization['id']}/members",
        json={"user_id": member["user_id"], "role": "MEMBER"},
        headers=auth_headers(owner["csrf_token"]),
    )
    assert add_member.status_code == 201

    created = db_client.post(
        "/api/v1/scenes",
        json={
            "scene_key": "time_poll",
            "organization_id": organization["id"],
            "participant_user_ids": [owner["user_id"]],
            "public_context": {
                "title": "班会时间协调",
                "options": ["周四 19:00", "周五 16:00"],
            },
        },
    )
    assert created.status_code == 201
    scene = created.json()["data"]
    assert scene["organization_id"] == organization["id"]
    assert scene["participant_status"] == "ACCEPTED"

    set_auth_cookies(db_client, member)
    mine = db_client.get("/api/v1/scenes/mine")
    assert mine.status_code == 200
    member_scene = next(item for item in mine.json()["data"]["scenes"] if item["id"] == scene["id"])
    assert member_scene["organization_id"] == organization["id"]
    assert member_scene["participant_status"] == "INVITED"

    accepted = db_client.post(
        f"/api/v1/scenes/{scene['id']}/accept",
        headers=auth_headers(member["csrf_token"]),
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["status"] == "ACCEPTED"
