"""Demo data, seed, and reset utilities for CampusAgent (P11).

This package provides:
- ``data``: centralised demo data definitions and constants.
- ``seed``: idempotent demo seed service.
- ``reset``: demo-only reset service (fail-closed in production).
- ``security``: environment guards for demo operations.
- ``routes``: internal-only FastAPI routes (development/test only).

Privacy:
- Demo data is entirely fictional. No real personal data is used.
- The demo password is a public constant — it must never be reused
  as a production default or written into ``Settings``.
- Reset only touches the demo namespace; non-demo rows are preserved.
"""

from __future__ import annotations

__all__: list[str] = ["data", "seed", "reset", "security", "routes"]
