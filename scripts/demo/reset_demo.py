#!/usr/bin/env python3
"""P11-04: CLI entry to reset the demo dataset.

Usage:
    uv run --project apps/api --extra dev --frozen python scripts/demo/reset_demo.py
    uv run --project apps/api --extra dev --frozen python scripts/demo/reset_demo.py --json

Resets only demo-namespace data; non-demo rows are preserved. Prints
a JSON summary to stdout. Exits non-zero if APP_ENV is production.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset CampusAgent demo data.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print only the JSON summary (no extra logging).",
    )
    args = parser.parse_args(argv)

    from src.config import settings
    from src.db.session import create_engine_from_settings, create_sessionmaker
    from src.demo.reset import reset_demo
    from src.demo.security import DemoResetForbiddenError

    try:
        engine = create_engine_from_settings(settings)
        sessionmaker = create_sessionmaker(engine)
        session = sessionmaker()
        try:
            summary = reset_demo(session, settings)
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

    summary_out = {
        "ok": True,
        "environment": str(settings.APP_ENV),
        "reset": summary,
    }
    print(json.dumps(summary_out, ensure_ascii=False, indent=2 if not args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
