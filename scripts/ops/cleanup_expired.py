#!/usr/bin/env python3
"""P12-07: Ops script to clean up expired short-lived sensitive data.

Runs the existing cleanup functions in sequence:
1. Expire stale scene instances.
2. Clean up expired private submissions.
3. Clean up expired memories.
4. Clean up revoked consents.

Usage::

    python scripts/ops/cleanup_expired.py [--dry-run] [--limit 100]

In ``--dry-run`` mode the script reports what *would* be cleaned without
committing.  This script is safe to run from a cron job or a Celery beat
task; it never deletes users, organizations, or conversations.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the apps/api/src package is importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from sqlalchemy.orm import Session  # noqa: E402

from src.config import settings  # noqa: E402
from src.db.session import create_engine_from_settings, create_sessionmaker  # noqa: E402
from src.modules.memories.cleanup import run_cleanup as cleanup_memories  # noqa: E402
from src.modules.scenes.cleanup import cleanup_expired_submissions  # noqa: E402
from src.modules.scenes.service import expire_stale_instances  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up expired sensitive data.")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not commit.")
    parser.add_argument("--limit", type=int, default=100, help="Max rows per batch.")
    args = parser.parse_args()

    engine = create_engine_from_settings(settings)
    session_factory = create_sessionmaker(engine)
    session: Session = session_factory()

    try:
        print("=== Cleanup expired data ===")
        if args.dry_run:
            print("[dry-run] no changes will be committed.")

        # 1. Expire stale scene instances.
        expired = expire_stale_instances(session)
        print(f"Expired stale scene instances: {expired}")

        # 2. Clean up expired private submissions.
        submissions = cleanup_expired_submissions(session, limit=args.limit)
        print(f"Cleaned expired private submissions: {submissions}")

        # 3. Clean up expired memories + revoked consents.
        mem_result = cleanup_memories(session)
        print(f"Memory cleanup: {mem_result}")

        if args.dry_run:
            session.rollback()
            print("[dry-run] rolled back.")
        else:
            session.commit()
            print("Committed.")
    finally:
        session.close()
        engine.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(main())
