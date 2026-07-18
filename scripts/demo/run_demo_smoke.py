#!/usr/bin/env python3
"""P11-06: Demo main-path smoke test script.

Runs the full product main path in-process (no Docker, no running
server required) so a demo operator can verify the system is healthy
before a live demo:

    python scripts/demo/run_demo_smoke.py

Main path exercised:
  1. reset + seed demo data (service layer, like the CLI)
  2. demo_admin login
  3. browse organization directory
  4. list conversations
  5. list scenes / scene definitions
  6. check demo status (internal API)
  7. privacy check — DEMO_PRIVATE_PHRASE must not leak
  8. soft-deleted user cannot login
  9. non-admin cannot access demo reset
 10. logout

Each step prints PASS/FAIL with a short reason. The script exits 0
only if every step passed. Output is human-readable; pass --json for
a machine-readable summary.

Environment:
- Forces APP_ENV=test and an in-memory SQLite database so it never
  touches real data and never requires Docker or Postgres.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure the API package is importable when run as a script.
# We add apps/api (not apps/api/src) so that `src` is importable as a
# package — this matches how pytest imports the app and lets main.py's
# relative imports resolve correctly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


def _setup_test_env() -> None:
    """Force a safe, isolated test environment before app imports."""
    os.environ["APP_ENV"] = "test"
    os.environ["APP_DEBUG"] = "false"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["APP_SECRET"] = "test-secret-key-at-least-32-chars-long"
    os.environ["FIELD_ENCRYPTION_KEY"] = "test-encryption-key-32-chars!!"


class SmokeResult:
    """Collects pass/fail outcomes for each smoke step."""

    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []

    def pass_step(self, name: str, detail: str = "") -> None:
        self.steps.append({"name": name, "ok": True, "detail": detail})

    def fail_step(self, name: str, detail: str) -> None:
        self.steps.append({"name": name, "ok": False, "detail": detail})

    @property
    def all_passed(self) -> bool:
        return all(s["ok"] for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.all_passed,
            "passed": sum(1 for s in self.steps if s["ok"]),
            "failed": sum(1 for s in self.steps if not s["ok"]),
            "steps": self.steps,
        }


def _get_csrf(client: Any) -> str:
    return client.cookies.get("csrf_token", "")


def _login(client: Any, email: str, password: str) -> Any:
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def run_smoke() -> SmokeResult:
    """Run the full demo smoke path in-process."""
    result = SmokeResult()

    # Import after env is set up.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from src.db.base import Base
    # Import all models so create_all registers every table.
    from src.modules.agents.models import Agent, AgentRun  # noqa: F401
    from src.modules.audit.models import AuditLog  # noqa: F401
    from src.modules.auth.models import AuthSession, RefreshToken  # noqa: F401
    from src.modules.conversations.models import (  # noqa: F401
        Conversation,
        ConversationParticipant,
        Message,
    )
    from src.modules.memories.models import ConsentRecord, MemoryItem  # noqa: F401
    from src.modules.model_gateway.models import ModelDefinition  # noqa: F401
    from src.modules.nodes.models import ModelDeployment, ModelNode  # noqa: F401
    from src.modules.organizations.models import (  # noqa: F401
        Organization,
        OrganizationMembership,
    )
    from src.modules.scenes.models import (  # noqa: F401
        PrivateSubmission,
        SceneCandidate,
        SceneDefinition,
        SceneInstance,
        SceneParticipant,
        SceneResult,
        SceneVote,
    )
    from src.modules.users.models import StudentProfile, User  # noqa: F401

    from starlette.testclient import TestClient

    from src.config import Settings
    from src.db.session import create_sessionmaker
    from src.demo.data import (
        DEMO_ADMIN,
        DEMO_ALICE,
        DEMO_DELETED,
        DEMO_PASSWORD,
        DEMO_PRIVATE_PHRASE,
    )
    from src.demo.reset import reset_demo
    from src.demo.seed import seed_demo
    from src.main import create_app
    from src.modules.scenes.plugins import DormDinnerPlugin
    from src.modules.scenes.registry import (
        get_scene_registry,
        reset_scene_registry,
    )

    # 1. Build an in-memory SQLite database + app.
    try:
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = create_sessionmaker(engine)

        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        app = create_app(settings)
        app.state.db_engine = engine
        app.state.db_sessionmaker = session_factory
        app.state.redis_client = None  # type: ignore[assignment]
        client = TestClient(app)
        result.pass_step("build_app", "in-memory SQLite + FastAPI app created")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("build_app", f"{type(exc).__name__}: {exc}")
        return result

    # Register the dorm dinner scene plugin.
    reset_scene_registry()
    registry = get_scene_registry()
    try:
        registry.register(DormDinnerPlugin())
    except Exception:  # noqa: BLE001
        pass  # may already be registered

    # 2. Reset + seed demo data at the service layer.
    try:
        session = session_factory()
        try:
            reset_demo(session, settings)
            summary = seed_demo(session)
            session.commit()
        finally:
            session.close()
        if summary["users_created"] >= 5 and summary["scenes_created"] == 1:
            result.pass_step(
                "seed_demo",
                f"users_created={summary['users_created']}, scenes_created={summary['scenes_created']}",
            )
        else:
            result.fail_step("seed_demo", f"unexpected summary: {summary}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("seed_demo", f"{type(exc).__name__}: {exc}")

    # 3. demo_admin login.
    try:
        resp = _login(client, DEMO_ADMIN.email, DEMO_PASSWORD)
        if resp.status_code == 200 and resp.json().get("success"):
            result.pass_step("admin_login", f"status={resp.status_code}")
        else:
            result.fail_step(
                "admin_login",
                f"status={resp.status_code}, body={resp.text[:200]}",
            )
    except Exception as exc:  # noqa: BLE001
        result.fail_step("admin_login", f"{type(exc).__name__}: {exc}")

    csrf = _get_csrf(client)

    # 4. Browse organization directory.
    try:
        resp = client.get("/api/v1/directory/tree")
        if resp.status_code == 200:
            result.pass_step("directory_tree", f"status={resp.status_code}")
        else:
            result.fail_step("directory_tree", f"status={resp.status_code}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("directory_tree", f"{type(exc).__name__}: {exc}")

    # 5. List conversations.
    try:
        resp = client.get("/api/v1/conversations")
        if resp.status_code == 200:
            result.pass_step("list_conversations", f"status={resp.status_code}")
        else:
            result.fail_step("list_conversations", f"status={resp.status_code}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("list_conversations", f"{type(exc).__name__}: {exc}")

    # 6. List scenes / scene definitions.
    try:
        resp = client.get("/api/v1/scenes")
        if resp.status_code == 200:
            result.pass_step("list_scenes", f"status={resp.status_code}")
        else:
            result.fail_step("list_scenes", f"status={resp.status_code}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("list_scenes", f"{type(exc).__name__}: {exc}")

    # 7. Check demo status (internal API).
    try:
        resp = client.get(
            "/api/v1/internal/demo/status",
            headers={"X-CSRF-Token": csrf},
        )
        if resp.status_code == 200:
            data = resp.json()["data"]
            result.pass_step(
                "demo_status",
                f"users_present={data['users_present']}, scenes_present={data['scenes_present']}",
            )
        else:
            result.fail_step("demo_status", f"status={resp.status_code}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("demo_status", f"{type(exc).__name__}: {exc}")

    # 8. Privacy check — DEMO_PRIVATE_PHRASE must not leak in any read response.
    try:
        leaked_in: list[str] = []
        for name, path in [
            ("scenes", "/api/v1/scenes"),
            ("directory", "/api/v1/directory/tree"),
            ("auth_me", "/api/v1/auth/me"),
            ("conversations", "/api/v1/conversations"),
        ]:
            r = client.get(path)
            if r.status_code == 200 and DEMO_PRIVATE_PHRASE in r.text:
                leaked_in.append(name)
        if not leaked_in:
            result.pass_step("privacy_no_leak", "DEMO_PRIVATE_PHRASE not found in responses")
        else:
            result.fail_step("privacy_no_leak", f"leaked in: {leaked_in}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("privacy_no_leak", f"{type(exc).__name__}: {exc}")

    # 9. Soft-deleted user cannot login.
    try:
        resp = _login(client, DEMO_DELETED.email, DEMO_PASSWORD)
        if resp.status_code in (401, 403):
            result.pass_step("deleted_user_blocked", f"status={resp.status_code}")
        else:
            result.fail_step(
                "deleted_user_blocked",
                f"expected 401/403, got {resp.status_code}",
            )
    except Exception as exc:  # noqa: BLE001
        result.fail_step("deleted_user_blocked", f"{type(exc).__name__}: {exc}")

    # 10. Non-admin (alice) cannot access demo reset.
    try:
        # Switch to alice by logging in (overwrites cookies).
        resp = _login(client, DEMO_ALICE.email, DEMO_PASSWORD)
        if resp.status_code != 200:
            result.fail_step("non_admin_blocked", f"alice login failed: {resp.status_code}")
        else:
            alice_csrf = _get_csrf(client)
            resp = client.post(
                "/api/v1/internal/demo/reset",
                headers={"X-CSRF-Token": alice_csrf},
            )
            if resp.status_code in (401, 403):
                result.pass_step("non_admin_blocked", f"status={resp.status_code}")
            else:
                result.fail_step(
                    "non_admin_blocked",
                    f"expected 401/403, got {resp.status_code}",
                )
    except Exception as exc:  # noqa: BLE001
        result.fail_step("non_admin_blocked", f"{type(exc).__name__}: {exc}")

    # 11. Logout.
    try:
        # Log back in as admin to test logout cleanly.
        _login(client, DEMO_ADMIN.email, DEMO_PASSWORD)
        admin_csrf = _get_csrf(client)
        resp = client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": admin_csrf},
        )
        if resp.status_code in (200, 204):
            result.pass_step("logout", f"status={resp.status_code}")
        else:
            result.fail_step("logout", f"status={resp.status_code}")
    except Exception as exc:  # noqa: BLE001
        result.fail_step("logout", f"{type(exc).__name__}: {exc}")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the CampusAgent demo smoke test.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print only the JSON summary.",
    )
    args = parser.parse_args(argv)

    _setup_test_env()
    result = run_smoke()

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("CampusAgent Demo Smoke Test")
        print("=" * 60)
        for step in result.steps:
            mark = "PASS" if step["ok"] else "FAIL"
            detail = f" — {step['detail']}" if step["detail"] else ""
            print(f"  [{mark}] {step['name']}{detail}")
        print("-" * 60)
        summary = result.to_dict()
        print(
            f"Result: {summary['passed']} passed, {summary['failed']} failed "
            f"-> {'ALL PASSED' if result.all_passed else 'FAILURES'}"
        )

    return 0 if result.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
