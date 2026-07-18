"""P7-10: Admin Model/Node/Deployment API tests.

Verifies:
- Non-admin is denied.
- Admin can create a node.
- Node credential is encrypted.
- List nodes redacts credential.
- Create/update deployment.
"""
from __future__ import annotations

from src.modules.nodes.models import ModelNode
from src.modules.users.models import User

from .helpers_p4 import auth_headers, register_and_login, set_auth_cookies


def _promote_to_admin(client, db_session_via_app, email):
    """Promote a registered user to SYSTEM_ADMIN via direct DB update."""
    # The db_client fixture shares the test engine; we need the sessionmaker.
    pass


def _make_system_admin(client, db_engine):
    """Register a user and promote to SYSTEM_ADMIN."""
    creds = register_and_login(
        client,
        email="admin@example.edu",
        display_name="Admin",
        student_no="20269999",
    )
    # Promote via direct DB access.
    from sqlalchemy.orm import sessionmaker
    session_local = sessionmaker(bind=db_engine, expire_on_commit=False)
    with session_local() as s:
        user = s.query(User).filter(User.email == "admin@example.edu").first()
        if user:
            user.global_role = "SYSTEM_ADMIN"
            s.commit()
    set_auth_cookies(client, creds)
    return creds


def _make_school_admin(client, db_engine):
    """Register a user and promote to SCHOOL_ADMIN."""
    creds = register_and_login(
        client,
        email="schooladmin@example.edu",
        display_name="SchoolAdmin",
        student_no="20268888",
    )
    from sqlalchemy.orm import sessionmaker
    session_local = sessionmaker(bind=db_engine, expire_on_commit=False)
    with session_local() as s:
        user = s.query(User).filter(User.email == "schooladmin@example.edu").first()
        if user:
            user.global_role = "SCHOOL_ADMIN"
            s.commit()
    set_auth_cookies(client, creds)
    return creds


class TestNodeAdminAPI:
    def test_non_admin_denied(self, db_client, test_engine):
        creds = register_and_login(db_client, email="student@example.edu", student_no="20260001")
        set_auth_cookies(db_client, creds)
        resp = db_client.get("/api/v1/admin/nodes")
        assert resp.status_code == 403

    def test_admin_create_node(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        resp = db_client.post(
            "/api/v1/admin/nodes",
            json={
                "name": "edge-node-01",
                "endpoint": "http://edge-node.example.edu:8080/v1",
                "exposure_type": "LOCAL",
                "capabilities": ["model_inference"],
            },
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()["data"]
        assert data["name"] == "edge-node-01"
        # Endpoint must NOT be in the create response.
        assert "endpoint" not in data or data.get("endpoint") is None

    def test_node_credential_encrypted_in_db(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        db_client.post(
            "/api/v1/admin/nodes",
            json={
                "name": "cred-node",
                "endpoint": "http://node.example.edu/v1",
                "credential": "super-secret-credential",
                "exposure_type": "INGRESS",
            },
            headers=auth_headers(creds["csrf_token"]),
        )
        # Verify the DB stores ciphertext.
        from sqlalchemy.orm import sessionmaker
        session_local = sessionmaker(bind=test_engine, expire_on_commit=False)
        with session_local() as s:
            node = s.query(ModelNode).filter(ModelNode.name == "cred-node").first()
            assert node is not None
            assert "super-secret-credential" not in node.credential_encrypted
            assert node.credential_encrypted != "super-secret-credential"

    def test_list_nodes_redacts_credential(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        db_client.post(
            "/api/v1/admin/nodes",
            json={
                "name": "list-node",
                "endpoint": "http://node.example.edu/v1",
                "credential": "do-not-leak",
                "exposure_type": "LOCAL",
            },
            headers=auth_headers(creds["csrf_token"]),
        )
        resp = db_client.get("/api/v1/admin/nodes")
        assert resp.status_code == 200
        body = resp.json()["data"]
        # List response must not contain credential or endpoint.
        for node in body["nodes"]:
            assert "credential" not in node
            assert "endpoint" not in node

    def test_school_admin_can_list_not_create(self, db_client, test_engine):
        creds = _make_school_admin(db_client, test_engine)
        # Can list.
        resp = db_client.get("/api/v1/admin/nodes")
        assert resp.status_code == 200
        # Cannot create.
        resp = db_client.post(
            "/api/v1/admin/nodes",
            json={"name": "x", "endpoint": "http://x/v1", "exposure_type": "LOCAL"},
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 403


class TestModelAdminAPI:
    def test_admin_create_model(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        resp = db_client.post(
            "/api/v1/admin/models",
            json={
                "name": "local-llama-7b",
                "provider": "local",
                "model_type": "chat",
            },
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()["data"]
        assert data["name"] == "local-llama-7b"

    def test_list_models(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        db_client.post(
            "/api/v1/admin/models",
            json={"name": "m1", "provider": "mock", "model_type": "chat"},
            headers=auth_headers(creds["csrf_token"]),
        )
        resp = db_client.get("/api/v1/admin/models")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["models"]) >= 1


class TestDeploymentAPI:
    def test_create_deployment(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        # Create node.
        node_resp = db_client.post(
            "/api/v1/admin/nodes",
            json={"name": "dep-node", "endpoint": "http://n/v1", "exposure_type": "LOCAL"},
            headers=auth_headers(creds["csrf_token"]),
        )
        node_id = node_resp.json()["data"]["node_id"]
        # Create model.
        model_resp = db_client.post(
            "/api/v1/admin/models",
            json={"name": "dep-model", "provider": "local", "model_type": "chat"},
            headers=auth_headers(creds["csrf_token"]),
        )
        model_id = model_resp.json()["data"]["model_id"]
        # Create deployment.
        resp = db_client.post(
            "/api/v1/admin/deployments",
            json={"model_id": model_id, "node_id": node_id},
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 201, resp.json()

    def test_deployment_missing_model(self, db_client, test_engine):
        creds = _make_system_admin(db_client, test_engine)
        node_resp = db_client.post(
            "/api/v1/admin/nodes",
            json={"name": "dep-node-2", "endpoint": "http://n/v1", "exposure_type": "LOCAL"},
            headers=auth_headers(creds["csrf_token"]),
        )
        node_id = node_resp.json()["data"]["node_id"]
        import uuid
        resp = db_client.post(
            "/api/v1/admin/deployments",
            json={"model_id": str(uuid.uuid4()), "node_id": node_id},
            headers=auth_headers(creds["csrf_token"]),
        )
        assert resp.status_code == 404
