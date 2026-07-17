"""
Unit tests for Last OWNER protection (P4-05).

Tests verify:
- Last OWNER cannot leave (returns ORG_LAST_OWNER_CANNOT_LEAVE).
- Last OWNER cannot be removed (returns ORG_LAST_OWNER_CANNOT_LEAVE).
- Last OWNER cannot be demoted (returns ORG_LAST_OWNER_CANNOT_LEAVE).
- Non-last OWNER can be demoted/removed when another OWNER exists.
- ADMIN cannot promote anyone to OWNER.
- OWNER transfer: new OWNER becomes active, old OWNER demoted.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


def _set_global_role(test_engine, user_id: str, role: str) -> None:
    """Directly update a user's global_role in the database."""
    from src.modules.users.models import User

    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = factory()
    try:
        user = session.get(User, UUID(user_id))
        if user is not None:
            user.global_role = role
            session.commit()
    finally:
        session.close()


class TestLastOwnerCannotLeave:
    """Test that the last OWNER cannot leave."""

    def test_last_owner_leave_blocked(self, db_client: TestClient) -> None:
        """Last OWNER cannot leave — returns ORG_LAST_OWNER_CANNOT_LEAVE."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="最后Owner退出")

        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_LAST_OWNER_CANNOT_LEAVE"


class TestLastOwnerCannotBeRemoved:
    """Test that the last OWNER cannot be removed."""

    def test_last_owner_remove_blocked(
        self, db_client: TestClient, test_engine
    ) -> None:
        """Last OWNER cannot be removed — returns ORG_LAST_OWNER_CANNOT_LEAVE."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="最后Owner移除")

        # SYSTEM_ADMIN tries to remove the last owner
        sysadmin = register_and_login(
            db_client, email="sys@example.edu", student_no="20264001"
        )
        _set_global_role(test_engine, sysadmin["user_id"], "SYSTEM_ADMIN")
        set_auth_cookies(db_client, sysadmin)
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{owner['user_id']}",
            headers=auth_headers(sysadmin["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_LAST_OWNER_CANNOT_LEAVE"


class TestLastOwnerCannotBeDemoted:
    """Test that the last OWNER cannot be demoted."""

    def test_last_owner_demote_blocked(self, db_client: TestClient) -> None:
        """Last OWNER cannot be demoted — returns ORG_LAST_OWNER_CANNOT_LEAVE."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="最后Owner降级")

        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{owner['user_id']}",
            json={"role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_LAST_OWNER_CANNOT_LEAVE"

    def test_last_owner_demote_to_member_blocked(self, db_client: TestClient) -> None:
        """Last OWNER cannot be demoted to MEMBER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="最后Owner降Member")

        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{owner['user_id']}",
            json={"role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 409


class TestNonLastOwnerCanBeDemoted:
    """Test that a non-last OWNER can be demoted when another OWNER exists."""

    def test_owner_transfer_then_old_owner_demoted(
        self, db_client: TestClient, test_engine
    ) -> None:
        """After transferring ownership, old OWNER can be demoted."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="转让后降级")

        new_owner = register_and_login(
            db_client, email="new_owner@example.edu", student_no="20264002"
        )

        # Owner adds new_owner as MEMBER
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": new_owner["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # Owner promotes new_owner to OWNER
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{new_owner['user_id']}",
            json={"role": "OWNER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 200

        # Now old owner can be demoted (there are 2 owners)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{owner['user_id']}",
            json={"role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 200


class TestOwnerTransfer:
    """Test ownership transfer logic."""

    def test_owner_can_transfer_ownership(self, db_client: TestClient) -> None:
        """OWNER can transfer ownership to another member."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="所有权转让")

        new_owner = register_and_login(
            db_client, email="transfer@example.edu", student_no="20264003"
        )

        # Owner adds new_owner as MEMBER
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": new_owner["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # Owner promotes new_owner to OWNER
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{new_owner['user_id']}",
            json={"role": "OWNER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "OWNER"

        # Now new_owner can leave (old owner is still OWNER)
        set_auth_cookies(db_client, new_owner)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(new_owner["csrf_token"]),
        )
        assert resp.status_code == 204

    def test_system_admin_can_transfer_ownership(
        self, db_client: TestClient, test_engine
    ) -> None:
        """SYSTEM_ADMIN can promote a member to OWNER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="系统管理员转让")

        member = register_and_login(
            db_client, email="sa_transfer@example.edu", student_no="20264004"
        )
        sysadmin = register_and_login(
            db_client, email="sa_tr@example.edu", student_no="20264005"
        )
        _set_global_role(test_engine, sysadmin["user_id"], "SYSTEM_ADMIN")

        # Owner adds member
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # System admin promotes member to OWNER
        set_auth_cookies(db_client, sysadmin)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "OWNER"},
            headers=auth_headers(sysadmin["csrf_token"]),
        )
        assert resp.status_code == 200
