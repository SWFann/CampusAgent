#!/usr/bin/env python3
"""P11-04: CLI entry to seed the demo dataset.

Usage:
    conda run -n CampusAgent python scripts/demo/seed_demo.py
    conda run -n CampusAgent python scripts/demo/seed_demo.py --json

Reads DATABASE_URL and APP_ENV from the project Settings (which in
turn reads .env / environment variables). Seeds idempotently — safe
to run repeatedly. Prints a JSON summary to stdout.

Exits non-zero if APP_ENV is production (fail-closed) or on error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the API package is importable when run as a script. Import through
# `src.*` so package-relative imports inside API modules keep working.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed CampusAgent demo data.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print only the JSON summary (no extra logging).",
    )
    args = parser.parse_args(argv)

    from src.config import settings
    from src.db.session import create_engine_from_settings, create_sessionmaker
    from src.demo.reset import reset_demo
    from src.demo.seed import seed_demo
    from src.demo.security import DemoResetForbiddenError

    try:
        engine = create_engine_from_settings(settings)
        sessionmaker = create_sessionmaker(engine)
        session = sessionmaker()
        try:
            # Reset first so seed is reproducible from a known state.
            reset_summary = reset_demo(session, settings)
            seed_summary = seed_demo(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()
    except DemoResetForbiddenError as exc:
        msg = {
            "ok": False,
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
        print(json.dumps(msg, ensure_ascii=False))
        return 2
    except Exception as exc:  # noqa: BLE001
        msg = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(msg, ensure_ascii=False))
        return 1

    summary = {
        "ok": True,
        "environment": str(settings.APP_ENV),
        "reset": reset_summary,
        "seed": seed_summary,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2 if not args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
