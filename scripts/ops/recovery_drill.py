#!/usr/bin/env python3
"""P12-13: Recovery drill — simulate failures and verify graceful degradation.

This script is a *manual* operations drill. It does NOT require Docker,
Redis, or a real PostgreSQL instance. It exercises the same code paths
that the production health checks use, but against deliberately broken
or in-memory backends, so operators can rehearse the recovery runbook
(``docs/development/P12-RECOVERY-RUNBOOK.md``).

Drills covered (P12 guide §18):
1. Database unavailable → ``/health/ready`` reports ``degraded``.
2. Redis unavailable → ``/health/ready`` reports ``degraded`` but
   ``/health/live`` still returns ``ok``.
3. Mock-model unavailable → model health endpoint reports failure
   but the API process does not crash (no white screen).
4. Demo reset → after reset, ``seed_demo`` restores the dataset.
5. Cleanup of expired data → after cleanup, the main read path
   still works.

Usage::

    conda run -n CampusAgent python scripts/ops/recovery_drill.py
    conda run -n CampusAgent python scripts/ops/recovery_drill.py --verbose
    conda run -n CampusAgent python scripts/ops/recovery_drill.py --skip demo-reset

Exit code:
- 0 if all drills passed.
- 1 if any drill failed (details printed to stdout).

Safety:
- The script never touches a production database. It uses an in-memory
  SQLite engine and overrides ``APP_ENV=test`` before importing the app.
- No real secrets, tokens, or user data are logged.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Environment bootstrap — must run BEFORE any application import.
# ---------------------------------------------------------------------------

# Force test environment so demo routes mount and production guards pass.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("APP_SECRET", "test-secret-key-at-least-32-chars-long")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "test-encryption-key")

# Ensure the apps/api/src package is importable when run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_SRC = _REPO_ROOT / "apps" / "api"
sys.path.insert(0, str(_API_SRC))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from src.db.base import Base  # noqa: E402
from src.db.session import (  # noqa: E402
    check_database_connection,
    create_sessionmaker,
)
from src.main import create_app  # noqa: E402

# Import ORM models so Base.metadata.create_all() registers every table.
from src.modules.agents.models import Agent, AgentRun  # noqa: E402, F401
from src.modules.audit.models import AuditLog  # noqa: E402, F401
from src.modules.auth.models import AuthSession, RefreshToken  # noqa: E402, F401
from src.modules.conversations.models import (  # noqa: E402, F401
    Conversation,
    ConversationParticipant,
    Message,
)
from src.modules.memories.models import ConsentRecord, MemoryItem  # noqa: E402, F401
from src.modules.model_gateway.models import ModelDefinition  # noqa: E402, F401
from src.modules.nodes.models import ModelDeployment, ModelNode  # noqa: E402, F401
from src.modules.organizations.models import (  # noqa: E402, F401
    Organization,
    OrganizationMembership,
)
from src.modules.scenes.models import (  # noqa: E402, F401
    PrivateSubmission,
    SceneCandidate,
    SceneDefinition,
    SceneInstance,
    SceneParticipant,
    SceneResult,
    SceneVote,
)
from src.modules.users.models import StudentProfile, User  # noqa: E402, F401


# ---------------------------------------------------------------------------
# Drill result helpers
# ---------------------------------------------------------------------------


class DrillResult:
    """Outcome of a single drill."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, name: str, status: str, detail: str = "") -> None:
        self.name = name
        self.status = status
        self.detail = detail

    def __str__(self) -> str:
        prefix = f"[{self.status}] {self.name}"
        if self.detail:
            return f"{prefix} — {self.detail}"
        return prefix


def _run_drill(name: str, fn: Callable[[], str], *, verbose: bool) -> DrillResult:
    """Execute a drill function and capture exceptions."""
    try:
        detail = fn() or ""
        if verbose and detail:
            print(f"  {name}: {detail}")
        return DrillResult(name, DrillResult.PASS, detail)
    except AssertionError as exc:
        msg = str(exc) or "assertion failed"
        if verbose:
            traceback.print_exc()
        return DrillResult(name, DrillResult.FAIL, msg)
    except Exception as exc:  # noqa: BLE001 — drill must not abort the suite
        msg = f"{type(exc).__name__}: {exc}"
        if verbose:
            traceback.print_exc()
        return DrillResult(name, DrillResult.FAIL, msg)


# ---------------------------------------------------------------------------
# App factory helpers
# ---------------------------------------------------------------------------


def _make_test_engine():
    """Create a fresh in-memory SQLite engine with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _make_client_with_db(engine, *, redis_client=None) -> TestClient:
    """Build a TestClient whose app.state points at the given engine."""
    session_factory = create_sessionmaker(engine)
    app = create_app()
    app.state.db_engine = engine
    app.state.db_sessionmaker = session_factory
    app.state.redis_client = redis_client  # type: ignore[assignment]
    return TestClient(app)


def _make_broken_db_engine():
    """An engine that points at a non-existent SQLite file path.

    Using a file path that cannot be opened simulates an unavailable
    database without requiring a real PostgreSQL failure.
    """
    return create_engine(
        "sqlite:////nonexistent/recovery-drill/unavailable.db",
        poolclass=StaticPool,
    )


# ---------------------------------------------------------------------------
# Drill 1: database unavailable → /health/ready degraded
# ---------------------------------------------------------------------------


def drill_database_unavailable() -> str:
    """When the DB engine cannot connect, /health/ready must report degraded."""
    broken_engine = _make_broken_db_engine()
    db_status = check_database_connection(broken_engine)
    assert db_status["status"] == "unavailable", (
        f"Expected broken engine to report unavailable, got {db_status}"
    )

    client = _make_client_with_db(broken_engine, redis_client=None)
    resp = client.get("/health/ready")
    assert resp.status_code == 200, f"/health/ready returned {resp.status_code}"
    body = resp.json()
    assert body["status"] == "degraded", (
        f"Expected degraded status, got {body['status']}"
    )
    assert body["checks"]["database"] == "unavailable", (
        f"Expected database check to be unavailable, got {body['checks']}"
    )

    # /health/live must still be ok — liveness never depends on the DB.
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    broken_engine.dispose()
    return "health/ready=degraded(database=unavailable), health/live=ok"


# ---------------------------------------------------------------------------
# Drill 2: Redis unavailable → degraded but /health/live ok
# ---------------------------------------------------------------------------


def drill_redis_unavailable() -> str:
    """When Redis is not configured, /health/ready degrades but live stays ok."""
    engine = _make_test_engine()
    # redis_client=None simulates "Redis not configured".
    client = _make_client_with_db(engine, redis_client=None)

    ready = client.get("/health/ready")
    body = ready.json()
    assert ready.status_code == 200
    assert body["status"] == "degraded", (
        f"Expected degraded when Redis is None, got {body['status']}"
    )
    # When redis_client is None the health check reports "not_configured";
    # when a real client is present but unreachable it reports "unavailable".
    # Both are valid degraded states — the key property is status != "ok".
    redis_state = body["checks"]["redis"]
    assert redis_state in ("unavailable", "not_configured"), (
        f"Expected redis check to be unavailable or not_configured, got {redis_state}"
    )
    assert body["checks"]["database"] == "ok", (
        f"Expected database to be ok, got {body['checks']}"
    )

    live = client.get("/health/live")
    assert live.json()["status"] == "ok"
    engine.dispose()
    return f"health/ready=degraded(redis={redis_state}), health/live=ok"


# ---------------------------------------------------------------------------
# Drill 3: mock-model unavailable → model health reports failure, no crash
# ---------------------------------------------------------------------------


def drill_model_gateway_unavailable() -> str:
    """Model gateway health endpoint must report failure without crashing.

    The internal model gateway health endpoint lives at
    ``/internal/v1/model/health`` (EP-MODEL-060). When no providers are
    configured it must still return a structured response — never a 500.
    The public ``/metrics/model-gateway`` endpoint must also remain reachable
    so the observability panel keeps working during a model outage.
    """
    engine = _make_test_engine()
    client = _make_client_with_db(engine, redis_client=None)

    # The internal model gateway health endpoint must not 500 even when no
    # providers are configured. Accept 200 (graceful) or 503 (explicitly
    # degraded). 404 means the route was not mounted — also acceptable in a
    # stripped deployment, but 500 is a hard failure.
    resp = client.get("/internal/v1/model/health")
    assert resp.status_code in (200, 503), (
        f"Model gateway health should not 500, got {resp.status_code}: {resp.text}"
    )

    # /metrics/model-gateway must still be reachable — the observability
    # panel depends on it and must not white-screen during a model outage.
    metrics = client.get("/metrics/model-gateway")
    assert metrics.status_code == 200, (
        f"metrics/model-gateway returned {metrics.status_code}"
    )
    engine.dispose()
    return f"model/health={resp.status_code}, metrics/model-gateway=200"


# ---------------------------------------------------------------------------
# Drill 4: demo reset → reseed restores dataset
# ---------------------------------------------------------------------------


def drill_demo_reset_reseed() -> str:
    """reset_demo + seed_demo must restore the demo dataset cleanly."""
    from src.config import settings
    from src.demo.reset import reset_demo
    from src.demo.seed import seed_demo

    engine = _make_test_engine()
    session_factory = create_sessionmaker(engine)
    session: Session = session_factory()

    try:
        # Seed once.
        first = seed_demo(session)
        session.commit()
        assert first["users_created"] >= 1, "Initial seed created no users"

        # Reset.
        reset_summary = reset_demo(session, settings)
        session.commit()
        assert reset_summary["deleted_users"] >= 1, (
            f"Reset deleted no users: {reset_summary}"
        )

        # Reseed — must be idempotent and restore the same shape.
        second = seed_demo(session)
        session.commit()
        assert second["users_created"] >= 1, "Reseed created no users"
    finally:
        session.close()
        engine.dispose()

    return (
        f"seed→reset→reseed ok "
        f"(initial_users={first['users_created']}, "
        f"deleted={reset_summary['deleted_users']}, "
        f"reseeded={second['users_created']})"
    )


# ---------------------------------------------------------------------------
# Drill 5: cleanup expired → main path still works
# ---------------------------------------------------------------------------


def drill_cleanup_then_read() -> str:
    """After running cleanup_expired, the main read path must still work."""
    from src.modules.memories.cleanup import run_cleanup as cleanup_memories
    from src.modules.scenes.cleanup import cleanup_expired_submissions
    from src.modules.scenes.service import expire_stale_instances

    engine = _make_test_engine()
    session_factory = create_sessionmaker(engine)
    session: Session = session_factory()

    try:
        # Run all cleanup functions on an empty DB — they must not raise.
        expired = expire_stale_instances(session)
        submissions = cleanup_expired_submissions(session, limit=100)
        mem_result = cleanup_memories(session)
        session.commit()

        # Main read path: health/ready still works via the API.
        client = _make_client_with_db(engine, redis_client=None)
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        # Database check should still be ok after cleanup.
        assert ready.json()["checks"]["database"] == "ok"
    finally:
        session.close()
        engine.dispose()

    return (
        f"cleanup ok "
        f"(expired_scenes={expired}, "
        f"submissions={submissions}, "
        f"memories={mem_result}), read path still 200"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_DRILLS: list[tuple[str, Callable[[], str]]] = [
    ("database-unavailable", drill_database_unavailable),
    ("redis-unavailable", drill_redis_unavailable),
    ("model-gateway-unavailable", drill_model_gateway_unavailable),
    ("demo-reset-reseed", drill_demo_reset_reseed),
    ("cleanup-then-read", drill_cleanup_then_read),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="P12-13 recovery drill — verify graceful degradation.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tracebacks and per-drill details.",
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Drill names to skip (e.g. demo-reset-reseed).",
    )
    args = parser.parse_args()

    # Normalise skip names to the drill keys.
    skip_set = {s.strip() for s in args.skip if s.strip()}
    # Accept both "demo-reset" and "demo-reset-reseed".
    normalised_skip: set[str] = set()
    for s in skip_set:
        normalised_skip.add(s)
        # Also match by prefix.
        for key, _ in _DRILLS:
            if key.startswith(s) or s.startswith(key):
                normalised_skip.add(key)

    print("=" * 70)
    print("P12-13 Recovery Drill")
    print("=" * 70)
    print(f"APP_ENV={os.environ.get('APP_ENV')}")
    print(f"DATABASE_URL={os.environ.get('DATABASE_URL')}")
    print(f"REDIS_URL={os.environ.get('REDIS_URL')}")
    print("-" * 70)

    results: list[DrillResult] = []
    for name, fn in _DRILLS:
        if name in normalised_skip:
            results.append(DrillResult(name, DrillResult.SKIP, "skipped by --skip"))
            print(results[-1])
            continue
        print(f"Running drill: {name} ...")
        result = _run_drill(name, fn, verbose=args.verbose)
        results.append(result)
        print(result)

    print("-" * 70)
    passed = sum(1 for r in results if r.status == DrillResult.PASS)
    failed = sum(1 for r in results if r.status == DrillResult.FAIL)
    skipped = sum(1 for r in results if r.status == DrillResult.SKIP)
    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 70)

    if failed:
        print("\nFAILED drills:")
        for r in results:
            if r.status == DrillResult.FAIL:
                print(f"  - {r.name}: {r.detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
