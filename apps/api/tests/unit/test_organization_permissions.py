"""
Unit tests for Organization permission matrix (P4-04).

Tests verify the RBAC policy across all actor types:
- anonymous, non-member, GUEST, MEMBER, ADMIN, OWNER
- SYSTEM_ADMIN, SCHOOL_ADMIN, ORG_ADMIN

Matrix:
| Actor        | View public | View private | Add member | Change role | Delete org |
|--------------|-------------|--------------|------------|-------------|------------|
| anonymous    | yes         | no           | no         | no          | no         |
| non-member   | yes         | no           | no         | no          | no         |
| GUEST        | yes         | limited      | no         | no          | no         |
| MEMBER       | yes         | yes          | no         | no          | no         |
| ADMIN        | yes         | yes          | yes(M/G)   | yes(M/G)    | no         |
| OWNER        | yes         | yes          | yes        | yes         | yes        |
| SYSTEM_ADMIN | yes         | yes          | yes        | yes         | yes        |
| SCHOOL_ADMIN | yes         | yes          | yes        | yes         | yes        |
| ORG_ADMIN    | no auto     | no auto      | no auto    | no auto     | no auto    |
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    clear_auth_cookies,
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


class TestViewPublicOrganization:
    """Test viewing PUBLIC organizations across roles."""

    def test_anonymous_can_view_public(self, db_client: TestClient) -> None:
        """Anonymous can view PUBLIC org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="公开组织", visibility="PUBLIC")

        clear_auth_cookies(db_client)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200

    def test_non_member_can_view_public(self, db_client: TestClient) -> None:
        """Non-member can view PUBLIC org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="公开组织2", visibility="PUBLIC")

        other = register_and_login(
            db_client, email="nm@example.edu", student_no="20263001"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200


class TestViewPrivateOrganization:
    """Test viewing PRIVATE organizations across roles."""

    def test_anonymous_cannot_view_private(
        self, db_client: TestClient, test_engine
    ) -> None:
        """Anonymous cannot view PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="私密组织", visibility="PRIVATE")

        clear_auth_cookies(db_client)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403

    def test_non_member_cannot_view_private(
        self, db_client: TestClient, test_engine
    ) -> None:
        """Non-member cannot view PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="私密组织2", visibility="PRIVATE")

        other = register_and_login(
            db_client, email="nm2@example.edu", student_no="20263002"
        )
        set_auth_cookies(db_client, other)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403

    def test_member_can_view_private(self, db_client: TestClient) -> None:
        """MEMBER can view PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="私密成员可见", visibility="PRIVATE")

        member = register_and_login(
            db_client, email="mem@example.edu", student_no="20263003"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, member)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200

    def test_guest_can_view_public_but_not_private_members(
        self, db_client: TestClient
    ) -> None:
        """GUEST can view PUBLIC org but has limited member list access."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="GUEST测试", visibility="PUBLIC")

        guest = register_and_login(
            db_client, email="guest@example.edu", student_no="20263004"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": guest["user_id"], "role": "GUEST"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # GUEST can view the org
        set_auth_cookies(db_client, guest)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200

        # GUEST can view members for PUBLIC org (limited per permissions)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}/members")
        assert resp.status_code == 200


class TestAddMemberPermissions:
    """Test add member permissions across roles."""

    def test_member_cannot_add_member(self, db_client: TestClient) -> None:
        """MEMBER cannot add members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="成员无权加人")

        member1 = register_and_login(
            db_client, email="m1@example.edu", student_no="20263005"
        )
        member2 = register_and_login(
            db_client, email="m2@example.edu", student_no="20263006"
        )

        # Owner adds member1
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member1["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # member1 tries to add member2
        set_auth_cookies(db_client, member1)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member2["user_id"], "role": "MEMBER"},
            headers=auth_headers(member1["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_admin_can_add_member_guest(self, db_client: TestClient) -> None:
        """ADMIN can add MEMBER and GUEST."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="管理员加人")

        admin = register_and_login(
            db_client, email="admin@example.edu", student_no="20263007"
        )
        target = register_and_login(
            db_client, email="target@example.edu", student_no="20263008"
        )

        # Owner promotes admin
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": admin["user_id"], "role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # Admin adds target as MEMBER
        set_auth_cookies(db_client, admin)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": target["user_id"], "role": "MEMBER"},
            headers=auth_headers(admin["csrf_token"]),
        )
        assert resp.status_code == 201

    def test_admin_cannot_add_owner(self, db_client: TestClient) -> None:
        """ADMIN cannot add OWNER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="管理员不能加OWNER")

        admin = register_and_login(
            db_client, email="adm2@example.edu", student_no="20263009"
        )
        target = register_and_login(
            db_client, email="tgt2@example.edu", student_no="20263010"
        )

        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": admin["user_id"], "role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, admin)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": target["user_id"], "role": "OWNER"},
            headers=auth_headers(admin["csrf_token"]),
        )
        assert resp.status_code == 403


class TestChangeRolePermissions:
    """Test role change permissions across roles."""

    def test_admin_can_change_member_role(self, db_client: TestClient) -> None:
        """ADMIN can change MEMBER/GUEST roles."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="管理员改角色")

        admin = register_and_login(
            db_client, email="cra@example.edu", student_no="20263011"
        )
        member = register_and_login(
            db_client, email="crm@example.edu", student_no="20263012"
        )

        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": admin["user_id"], "role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        # Admin promotes member to GUEST (or back)
        set_auth_cookies(db_client, admin)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "GUEST"},
            headers=auth_headers(admin["csrf_token"]),
        )
        assert resp.status_code == 200

    def test_admin_cannot_promote_to_owner(self, db_client: TestClient) -> None:
        """ADMIN cannot promote anyone to OWNER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="管理员不能升OWNER")

        admin = register_and_login(
            db_client, email="a2o@example.edu", student_no="20263013"
        )
        member = register_and_login(
            db_client, email="m2o@example.edu", student_no="20263014"
        )

        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": admin["user_id"], "role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, admin)
        resp = db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "OWNER"},
            headers=auth_headers(admin["csrf_token"]),
        )
        assert resp.status_code == 403


class TestDeleteOrgPermissions:
    """Test delete organization permissions across roles."""

    def test_admin_cannot_delete_org(self, db_client: TestClient) -> None:
        """ADMIN cannot delete org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="管理员不能删")

        admin = register_and_login(
            db_client, email="del_adm@example.edu", student_no="20263015"
        )

        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": admin["user_id"], "role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, admin)
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(admin["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_member_cannot_delete_org(self, db_client: TestClient) -> None:
        """MEMBER cannot delete org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="成员不能删")

        member = register_and_login(
            db_client, email="del_mem@example.edu", student_no="20263016"
        )

        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        set_auth_cookies(db_client, member)
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(member["csrf_token"]),
        )
        assert resp.status_code == 403


class TestSystemAdminPermissions:
    """Test SYSTEM_ADMIN permissions."""

    def test_system_admin_can_view_private(
        self, db_client: TestClient, test_engine
    ) -> None:
        """SYSTEM_ADMIN can view PRIVATE org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="系统管理员可见", visibility="PRIVATE")

        sysadmin = register_and_login(
            db_client, email="sysadmin@example.edu", student_no="20263017"
        )
        _set_global_role(test_engine, sysadmin["user_id"], "SYSTEM_ADMIN")

        set_auth_cookies(db_client, sysadmin)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200

    def test_system_admin_can_delete_org(
        self, db_client: TestClient, test_engine
    ) -> None:
        """SYSTEM_ADMIN can delete any org."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="系统管理员删除")

        sysadmin = register_and_login(
            db_client, email="sysadm2@example.edu", student_no="20263018"
        )
        _set_global_role(test_engine, sysadmin["user_id"], "SYSTEM_ADMIN")

        set_auth_cookies(db_client, sysadmin)
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(sysadmin["csrf_token"]),
        )
        assert resp.status_code == 204

    def test_system_admin_can_add_member(
        self, db_client: TestClient, test_engine
    ) -> None:
        """SYSTEM_ADMIN can add members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="系统管理员加人", visibility="PRIVATE")

        sysadmin = register_and_login(
            db_client, email="sysadm3@example.edu", student_no="20263019"
        )
        target = register_and_login(
            db_client, email="sysadm_tgt@example.edu", student_no="20263020"
        )
        _set_global_role(test_engine, sysadmin["user_id"], "SYSTEM_ADMIN")

        set_auth_cookies(db_client, sysadmin)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": target["user_id"], "role": "MEMBER"},
            headers=auth_headers(sysadmin["csrf_token"]),
        )
        assert resp.status_code == 201


class TestSchoolAdminPermissions:
    """Test SCHOOL_ADMIN permissions."""

    def test_school_admin_can_view_private(
        self, db_client: TestClient, test_engine
    ) -> None:
        """SCHOOL_ADMIN can view PRIVATE org (P4 MVP)."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="校管理员可见", visibility="PRIVATE")

        schooladmin = register_and_login(
            db_client, email="schladm@example.edu", student_no="20263021"
        )
        _set_global_role(test_engine, schooladmin["user_id"], "SCHOOL_ADMIN")

        set_auth_cookies(db_client, schooladmin)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 200


class TestOrgAdminNoAutoPower:
    """Test that ORG_ADMIN has no automatic organization power."""

    def test_org_admin_cannot_view_private(
        self, db_client: TestClient, test_engine
    ) -> None:
        """ORG_ADMIN does NOT automatically equal any org OWNER."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="ORG_ADMIN无权", visibility="PRIVATE")

        orgadmin = register_and_login(
            db_client, email="orgadm@example.edu", student_no="20263022"
        )
        _set_global_role(test_engine, orgadmin["user_id"], "ORG_ADMIN")

        set_auth_cookies(db_client, orgadmin)
        resp = db_client.get(f"/api/v1/organizations/{org['id']}")
        assert resp.status_code == 403

    def test_org_admin_cannot_delete_org(
        self, db_client: TestClient, test_engine
    ) -> None:
        """ORG_ADMIN cannot delete org they are not a member of."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="ORG_ADMIN不能删")

        orgadmin = register_and_login(
            db_client, email="orgadm2@example.edu", student_no="20263023"
        )
        _set_global_role(test_engine, orgadmin["user_id"], "ORG_ADMIN")

        set_auth_cookies(db_client, orgadmin)
        resp = db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(orgadmin["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_org_admin_cannot_add_member(
        self, db_client: TestClient, test_engine
    ) -> None:
        """ORG_ADMIN cannot add members to org they are not a member of."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="ORG_ADMIN不能加人")

        orgadmin = register_and_login(
            db_client, email="orgadm3@example.edu", student_no="20263024"
        )
        target = register_and_login(
            db_client, email="orgadm_tgt@example.edu", student_no="20263025"
        )
        _set_global_role(test_engine, orgadmin["user_id"], "ORG_ADMIN")

        set_auth_cookies(db_client, orgadmin)
        resp = db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": target["user_id"], "role": "MEMBER"},
            headers=auth_headers(orgadmin["csrf_token"]),
        )
        assert resp.status_code == 403
