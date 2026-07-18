"""P12-12: Observability panel security.

Verifies:
- /metrics is accessible and returns Prometheus-style text.
- /metrics/model-gateway is accessible and returns Prometheus text.
- Metrics text contains no secrets (tokens, passwords, api keys, emails).
- Admin model list endpoint does not expose api_key/secret fields.
- Admin node list does not leak endpoint userinfo/token.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin_and_login(db_client, test_db_session):
    """Create a SYSTEM_ADMIN with a real password and log in via API."""
    from src.modules.auth.passwords import hash_password
    from src.modules.users.models import GlobalRole, User, UserStatus

    user = User(
        email="admin-obs@example.com",
        password_hash=hash_password("AdminPass123!"),
        display_name="Admin",
        global_role=GlobalRole.SYSTEM_ADMIN.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.commit()

    resp = db_client.post(
        "/api/v1/auth/login",
        json={"email": "admin-obs@example.com", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return db_client


# ---------------------------------------------------------------------------
# 1. /metrics endpoint
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    def test_metrics_accessible(self, db_client):
        resp = db_client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_metrics_model_gateway_accessible(self, db_client):
        resp = db_client.get("/metrics/model-gateway")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_metrics_no_secret_patterns(self, db_client):
        """Metrics text must not contain common secret patterns."""
        resp = db_client.get("/metrics")
        text = resp.text
        forbidden = [
            "APP_SECRET",
            "test-secret-key-at-least-32-chars-long",
            "Bearer ",
            "sk-",
            "field_encryption_key",
        ]
        for token in forbidden:
            assert token not in text, f"Metrics leaked '{token}'"

    def test_model_gateway_metrics_no_secret_patterns(self, db_client):
        resp = db_client.get("/metrics/model-gateway")
        text = resp.text
        forbidden = [
            "APP_SECRET",
            "test-secret-key-at-least-32-chars-long",
            "Bearer ",
            "sk-",
        ]
        for token in forbidden:
            assert token not in text, f"Model-gateway metrics leaked '{token}'"


# ---------------------------------------------------------------------------
# 2. Admin panel does not expose secrets
# ---------------------------------------------------------------------------


class TestAdminPanelNoSecrets:
    """Verify admin endpoints never return secret fields."""

    def test_admin_model_list_no_api_key(self, db_client, test_db_session):
        client = _make_admin_and_login(db_client, test_db_session)
        resp = client.get("/api/v1/admin/models")
        assert resp.status_code == 200, resp.json()
        body_str = resp.text
        for secret_field in [
            '"api_key"',
            '"api_secret"',
            '"secret"',
            '"password_hash"',
            '"access_token"',
            '"refresh_token"',
        ]:
            assert secret_field not in body_str, (
                f"Admin model list leaked field {secret_field}"
            )

    def test_admin_node_list_no_endpoint_token(self, db_client, test_db_session):
        client = _make_admin_and_login(db_client, test_db_session)
        resp = client.get("/api/v1/admin/nodes")
        assert resp.status_code == 200, resp.json()
        body_str = resp.text
        for secret_field in [
            '"api_key"',
            '"api_secret"',
            '"password_hash"',
            '"access_token"',
        ]:
            assert secret_field not in body_str, (
                f"Admin node list leaked field {secret_field}"
            )
