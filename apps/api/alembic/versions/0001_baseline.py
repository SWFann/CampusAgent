"""baseline migration — establishes alembic version table.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-16 19:00:00

This is the initial baseline migration for CampusAgent. It intentionally
creates NO business tables. The ``alembic_version`` table is created
automatically by Alembic's bookkeeping when ``upgrade head`` is executed.

Design decision: an empty baseline is preferred over embedding table
definitions here. All future schema changes will be added as subsequent
migration files in ``alembic/versions/``.

Downgrade strategy: ``downgrade base`` removes the ``alembic_version``
table, returning the database to a pristine state. This is safe because
no business tables are created by this migration.
"""
from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op baseline migration.

    Alembic automatically creates the ``alembic_version`` table when the
    first migration runs. This migration deliberately creates no business
    tables or schema objects.
    """
    pass


def downgrade() -> None:
    """Downgrade to base (pristine database).

    Alembic automatically drops the ``alembic_version`` table when
    downgrading past the first migration. No business objects exist to
    remove.
    """
    pass
