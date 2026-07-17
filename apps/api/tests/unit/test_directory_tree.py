"""
Unit tests for Directory Tree (P4-08).

Tests verify:
- No root returns PUBLIC root nodes.
- Specified root returns subtree.
- Root not found returns DIRECTORY_ORG_NOT_FOUND.
- max_depth exceeding limit returns DIRECTORY_TREE_TOO_DEEP.
- PRIVATE child nodes hidden from non-members.
- MEMBERS_ONLY child nodes visible to members.
- DELETED/ARCHIVED nodes not returned.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    clear_auth_cookies,
    create_org,
    register_and_login,
    set_auth_cookies,
)


class TestTreeValidation:
    """Test tree query validation."""

    def test_max_depth_too_deep(self, db_client: TestClient) -> None:
        """max_depth > 5 returns DIRECTORY_TREE_TOO_DEEP."""
        resp = db_client.get("/api/v1/directory/tree?max_depth=6")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DIRECTORY_TREE_TOO_DEEP"

    def test_root_not_found(self, db_client: TestClient) -> None:
        """Non-existent root returns DIRECTORY_ORG_NOT_FOUND."""
        resp = db_client.get(
            "/api/v1/directory/tree?root_organization_id=00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "DIRECTORY_ORG_NOT_FOUND"


class TestTreeStructure:
    """Test tree structure and visibility."""

    def test_no_root_returns_public_nodes(self, db_client: TestClient) -> None:
        """Without root, returns root-level PUBLIC organizations."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="根级公开", visibility="PUBLIC")

        clear_auth_cookies(db_client)
        resp = db_client.get("/api/v1/directory/tree")
        assert resp.status_code == 200
        nodes = resp.json()["data"]["nodes"]
        assert len(nodes) >= 1
        # All returned nodes should be PUBLIC (for anonymous)
        for node in nodes:
            assert node["visibility"] == "PUBLIC"

    def test_specified_root_returns_subtree(self, db_client: TestClient) -> None:
        """Specified root returns its subtree."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        parent = create_org(db_client, owner, name="父组织树", visibility="PUBLIC")

        # Create a child
        child = create_org(
            db_client,
            owner,
            name="子组织树",
            visibility="PUBLIC",
            parent_id=parent["id"],
        )

        resp = db_client.get(
            f"/api/v1/directory/tree?root_organization_id={parent['id']}"
        )
        assert resp.status_code == 200
        nodes = resp.json()["data"]["nodes"]
        assert len(nodes) == 1
        assert nodes[0]["id"] == parent["id"]
        assert len(nodes[0]["children"]) >= 1
        assert any(c["id"] == child["id"] for c in nodes[0]["children"])

    def test_private_child_hidden_from_non_member(
        self, db_client: TestClient
    ) -> None:
        """PRIVATE child node is hidden from non-members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        parent = create_org(db_client, owner, name="父公开", visibility="PUBLIC")
        create_org(
            db_client,
            owner,
            name="子私密",
            visibility="PRIVATE",
            parent_id=parent["id"],
        )

        clear_auth_cookies(db_client)
        resp = db_client.get(
            f"/api/v1/directory/tree?root_organization_id={parent['id']}"
        )
        assert resp.status_code == 200
        nodes = resp.json()["data"]["nodes"]
        # Parent is PUBLIC, visible
        assert len(nodes) == 1
        # Private child should not be in the tree for anonymous
        children = nodes[0]["children"]
        assert not any(c["name"] == "子私密" for c in children)

    def test_members_only_child_visible_to_member(
        self, db_client: TestClient
    ) -> None:
        """MEMBERS_ONLY child node is visible to members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        parent = create_org(db_client, owner, name="父公开2", visibility="PUBLIC")
        child = create_org(
            db_client,
            owner,
            name="子成员可见",
            visibility="MEMBERS_ONLY",
            parent_id=parent["id"],
        )

        # Owner is a member of the child (creator)
        resp = db_client.get(
            f"/api/v1/directory/tree?root_organization_id={parent['id']}"
        )
        assert resp.status_code == 200
        nodes = resp.json()["data"]["nodes"]
        children = nodes[0]["children"]
        assert any(c["id"] == child["id"] for c in children)

    def test_deleted_org_not_in_tree(self, db_client: TestClient) -> None:
        """DELETED organization is not in the tree."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="要删除的树节点", visibility="PUBLIC")

        # Delete the org
        db_client.delete(
            f"/api/v1/organizations/{org['id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        resp = db_client.get("/api/v1/directory/tree")
        assert resp.status_code == 200
        nodes = resp.json()["data"]["nodes"]
        assert not any(n["id"] == org["id"] for n in nodes)

    def test_private_root_not_found_for_non_member(
        self, db_client: TestClient
    ) -> None:
        """PRIVATE root returns DIRECTORY_ORG_NOT_FOUND for non-members."""
        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="私密根", visibility="PRIVATE")

        clear_auth_cookies(db_client)
        resp = db_client.get(
            f"/api/v1/directory/tree?root_organization_id={org['id']}"
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "DIRECTORY_ORG_NOT_FOUND"
