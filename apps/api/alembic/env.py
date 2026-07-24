"""
Alembic migration environment for CampusAgent API.

This module configures Alembic to:
- Use ``Base.metadata`` from ``src.db.base`` as the target metadata.
- Read the database URL from ``Settings.DATABASE_URL`` at runtime.
- NOT hardcode any database URL in ``alembic.ini``.
- Support both offline (``--sql``) and online (engine) migration modes.
- NOT connect to a production database during import.

The database URL is resolved in the following order:
1. The ``--x database-url`` Alembic CLI option (if provided).
2. The ``DATABASE_URL`` environment variable.
3. The ``Settings.DATABASE_URL`` default.

This ensures that ``alembic upgrade head`` uses the same configuration
source as the application itself.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure the ``src`` package is importable when Alembic runs from the
# ``apps/api`` directory (the standard invocation location).
# We add the parent of ``alembic/`` (i.e. ``apps/api/``) to sys.path so
# that ``from src.config import Settings`` resolves correctly.
_this_dir = os.path.dirname(os.path.abspath(__file__))
_api_dir = os.path.normpath(os.path.join(_this_dir, ".."))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from src.config import Settings  # noqa: E402  (import after sys.path fix)
from src.db.base import Base  # noqa: E402

# -----------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini.
# -----------------------------------------------------------------------
config = context.config

# Configure Python logging from alembic.ini if the config file has a
# ``[loggers]`` section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The target metadata for autogenerate support.
target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """Resolve the database URL for Alembic operations.

    Resolution order:
    1. ``--x database-url`` Alembic CLI option.
    2. ``DATABASE_URL`` environment variable.
    3. ``Settings.DATABASE_URL`` default.

    This function does NOT connect to the database.
    """
    # 1. Check for the Alembic ``-x database-url=...`` option.
    x_args = context.get_x_argument(as_dictionary=True)
    if isinstance(x_args, dict):
        db_url = x_args.get("database-url")
        if db_url:
            return str(db_url)

    # 2. Check the DATABASE_URL environment variable.
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # 3. Fall back to Settings default.
    return Settings(_env_file=None).DATABASE_URL  # type: ignore[call-arg]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout).

    This does NOT require a live database connection.
    """
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (use a live database connection).

    A new ``Engine`` is created from the resolved database URL.
    The engine is disposed after migrations complete.
    """
    url = _resolve_database_url()

    # If the URL starts with sqlite:///:memory:, use a StaticPool so the
    # in-memory database is shared across all connections.
    connectable_kwargs: dict[str, object] = {"poolclass": pool.NullPool}

    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        connectable_kwargs = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }

    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        **connectable_kwargs,  # type: ignore[arg-type]
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# Alembic imports this module only with a configured migration context.
# Do not swallow migration errors: a failed schema change must fail the
# command instead of leaving a partially upgraded database behind.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
