"""P12-12: Performance budget tests.

Establishes minimum performance baselines for the MVP using the in-memory
SQLite test client.  Thresholds are p95 latency budgets:

- /health/live       < 50ms
- /health/ready      < 200ms  (mock deps)
- login              < 300ms
- organization list  < 300ms
- conversation list  < 300ms
- dinner result read < 500ms
- /metrics           < 200ms

In the test environment latencies are dominated by bcrypt hashing (login)
and SQLite.  Thresholds are intentionally generous to avoid flakiness while
still catching gross regressions.
"""

from __future__ import annotations

import time

import pytest
from starlette.testclient import TestClient

from tests.unit.helpers_p4 import register_and_login, set_auth_cookies

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _measure(client: TestClient, method: str, path: str, **kwargs) -> float:
    """Measure a single request latency in milliseconds."""
    start = time.perf_counter()
    if method == "GET":
        client.get(path, **kwargs)
    elif method == "POST":
        client.post(path, **kwargs)
    return (time.perf_counter() - start) * 1000


def _p95(samples: list[float]) -> float:
    """Compute the 95th percentile of a list of latencies."""
    sorted_samples = sorted(samples)
    idx = int(len(sorted_samples) * 0.95)
    idx = min(idx, len(sorted_samples) - 1)
    return sorted_samples[idx]


SAMPLES = 15  # small sample to keep test suite fast


# ---------------------------------------------------------------------------
# 1. Health endpoints
# ---------------------------------------------------------------------------


class TestHealthPerformance:
    def test_health_live_p95_under_50ms(self, db_client: TestClient):
        latencies = [_measure(db_client, "GET", "/health/live") for _ in range(SAMPLES)]
        p95 = _p95(latencies)
        assert p95 < 50, f"/health/live p95 {p95:.1f}ms exceeds 50ms"

    def test_health_ready_p95_under_200ms(self, db_client: TestClient):
        latencies = [_measure(db_client, "GET", "/health/ready") for _ in range(SAMPLES)]
        p95 = _p95(latencies)
        assert p95 < 200, f"/health/ready p95 {p95:.1f}ms exceeds 200ms"


# ---------------------------------------------------------------------------
# 2. Login
# ---------------------------------------------------------------------------


class TestLoginPerformance:
    def test_login_p95_under_300ms(self, db_client: TestClient):
        # Register once
        db_client.cookies.clear()
        db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12perf-login@example.edu",
                "password": "SecurePass123",
                "display_name": "Perf",
                "student_no": "20269001",
                "organization_ids": [],
            },
        )
        latencies = []
        for _ in range(SAMPLES):
            db_client.cookies.clear()
            start = time.perf_counter()
            db_client.post(
                "/api/v1/auth/login",
                json={
                    "email": "p12perf-login@example.edu",
                    "password": "SecurePass123",
                },
            )
            latencies.append((time.perf_counter() - start) * 1000)
        p95 = _p95(latencies)
        assert p95 < 300, f"login p95 {p95:.1f}ms exceeds 300ms"


# ---------------------------------------------------------------------------
# 3. Authenticated list endpoints
# ---------------------------------------------------------------------------


class TestListPerformance:
    @pytest.fixture()
    def authed(self, db_client: TestClient) -> dict[str, str]:
        creds = register_and_login(
            db_client, email="p12perf-list@example.edu", student_no="20269010"
        )
        set_auth_cookies(db_client, creds)
        return creds

    def test_organization_list_p95_under_300ms(
        self, db_client: TestClient, authed: dict[str, str]
    ):
        latencies = [
            _measure(db_client, "GET", "/api/v1/organizations") for _ in range(SAMPLES)
        ]
        p95 = _p95(latencies)
        assert p95 < 300, f"org list p95 {p95:.1f}ms exceeds 300ms"

    def test_conversation_list_p95_under_300ms(
        self, db_client: TestClient, authed: dict[str, str]
    ):
        latencies = [
            _measure(db_client, "GET", "/api/v1/conversations") for _ in range(SAMPLES)
        ]
        p95 = _p95(latencies)
        assert p95 < 300, f"conv list p95 {p95:.1f}ms exceeds 300ms"


# ---------------------------------------------------------------------------
# 4. Metrics endpoint
# ---------------------------------------------------------------------------


class TestMetricsPerformance:
    def test_metrics_p95_under_200ms(self, db_client: TestClient):
        latencies = [_measure(db_client, "GET", "/metrics") for _ in range(SAMPLES)]
        p95 = _p95(latencies)
        assert p95 < 200, f"/metrics p95 {p95:.1f}ms exceeds 200ms"


# ---------------------------------------------------------------------------
# 5. Dinner result read (non-existent → 404 fast)
# ---------------------------------------------------------------------------


class TestDinnerResultPerformance:
    def test_dinner_result_404_p95_under_500ms(self, db_client: TestClient):
        creds = register_and_login(
            db_client, email="p12perf-dinner@example.edu", student_no="20269020"
        )
        set_auth_cookies(db_client, creds)
        fake_id = "00000000-0000-0000-0000-000000000000"
        latencies = [
            _measure(db_client, "GET", f"/api/v1/scenes/{fake_id}/result")
            for _ in range(SAMPLES)
        ]
        p95 = _p95(latencies)
        assert p95 < 500, f"dinner result p95 {p95:.1f}ms exceeds 500ms"
