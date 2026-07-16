"""
Unit tests for database engine/session infrastructure.

Uses SQLite in-memory to avoid real PostgreSQL dependency.
"""

from __future__ import annotations

import contextlib
import os

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import AppEnv, Settings
from src.db.session import (
    check_database_connection,
    create_engine_from_settings,
    create_sessionmaker,
    get_db_session,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STRONG_SECRET = "x" * 48
_STRONG_ENC_KEY = "y" * 48


def _make_settings(**overrides: str) -> Settings:
    """Create Settings without reading a .env file, applying env overrides."""
    env_vars = {
        "APP_ENV": "test",
        "APP_SECRET": "test-secret-key",
        "FIELD_ENCRYPTION_KEY": "test-encryption-key",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
    }
    env_vars.update(overrides)
    old_values: dict[str, str | None] = {}
    for key, val in env_vars.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = val
    try:
        return Settings(_env_file=None)  # type: ignore[call-arg]
    finally:
        for key, old_val in old_values.items():
            if old_val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_val


# ---------------------------------------------------------------------------
# 1. Settings DB fields defaults
# ---------------------------------------------------------------------------


class TestDbSettingsDefaults:
    def test_default_pool_size(self) -> None:
        s = _make_settings()
        assert s.DB_POOL_SIZE == 5

    def test_default_max_overflow(self) -> None:
        s = _make_settings()
        assert s.DB_MAX_OVERFLOW == 10

    def test_default_pool_timeout(self) -> None:
        s = _make_settings()
        assert s.DB_POOL_TIMEOUT_SECONDS == 30

    def test_default_pool_recycle(self) -> None:
        s = _make_settings()
        assert s.DB_POOL_RECYCLE_SECONDS == 1800

    def test_default_echo_sql(self) -> None:
        s = _make_settings()
        assert s.DB_ECHO_SQL is False


# ---------------------------------------------------------------------------
# 2. Invalid pool values
# ---------------------------------------------------------------------------


class TestDbSettingsValidation:
    def test_pool_size_zero_fails(self) -> None:
        with pytest.raises(Exception, match="DB_POOL_SIZE"):
            _make_settings(DB_POOL_SIZE="0")

    def test_max_overflow_negative_fails(self) -> None:
        with pytest.raises(Exception, match="DB_MAX_OVERFLOW"):
            _make_settings(DB_MAX_OVERFLOW="-1")

    def test_pool_timeout_zero_fails(self) -> None:
        with pytest.raises(Exception, match="DB_POOL_TIMEOUT"):
            _make_settings(DB_POOL_TIMEOUT_SECONDS="0")

    def test_pool_recycle_zero_fails(self) -> None:
        with pytest.raises(Exception, match="DB_POOL_RECYCLE"):
            _make_settings(DB_POOL_RECYCLE_SECONDS="0")

    def test_production_echo_sql_true_fails(self) -> None:
        with pytest.raises(Exception, match="DB_ECHO_SQL"):
            _make_settings(
                APP_ENV="production",
                APP_SECRET=_STRONG_SECRET,
                FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
                DB_ECHO_SQL="true",
            )

    def test_production_echo_sql_false_succeeds(self) -> None:
        s = _make_settings(
            APP_ENV="production",
            APP_SECRET=_STRONG_SECRET,
            FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
            DB_ECHO_SQL="false",
        )
        assert s.DB_ECHO_SQL is False
        assert s.APP_ENV == AppEnv.PRODUCTION


# ---------------------------------------------------------------------------
# 3. Engine factory
# ---------------------------------------------------------------------------


class TestEngineFactory:
    def test_engine_not_connected_on_creation(self) -> None:
        """Engine creation should not connect to the database."""
        s = _make_settings(DATABASE_URL="sqlite:///:memory:")
        engine = create_engine_from_settings(s)
        assert engine is not None
        assert isinstance(engine, Engine)
        # Pool should exist but have no active connections.
        # StaticPool reports differently, so just verify pool object exists.
        assert engine.pool is not None

    def test_sqlite_memory_engine(self) -> None:
        s = _make_settings(DATABASE_URL="sqlite:///:memory:")
        engine = create_engine_from_settings(s)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_engine_echo_flag(self) -> None:
        s = _make_settings(DB_ECHO_SQL="true")
        engine = create_engine_from_settings(s)
        assert engine.echo is True


# ---------------------------------------------------------------------------
# 4. Sessionmaker
# ---------------------------------------------------------------------------


class TestSessionmaker:
    def test_create_sessionmaker_returns_callable(self) -> None:
        s = _make_settings()
        engine = create_engine_from_settings(s)
        sm = create_sessionmaker(engine)
        assert callable(sm)
        assert isinstance(sm, sessionmaker)

    def test_sessionmaker_creates_session(self) -> None:
        s = _make_settings()
        engine = create_engine_from_settings(s)
        sm = create_sessionmaker(engine)
        session = sm()
        assert isinstance(session, Session)
        session.close()

    def test_expire_on_commit_is_false(self) -> None:
        s = _make_settings()
        engine = create_engine_from_settings(s)
        sm = create_sessionmaker(engine)
        session = sm()
        assert session.expire_on_commit is False
        session.close()


# ---------------------------------------------------------------------------
# 5. get_db_session dependency
# ---------------------------------------------------------------------------


class TestGetDbSession:
    def test_session_is_closed_after_normal_use(self) -> None:
        s = _make_settings()
        engine = create_engine_from_settings(s)
        sm = create_sessionmaker(engine)

        gen = get_db_session(sm)
        session = next(gen)
        assert isinstance(session, Session)

        # Monkeypatch close to track it
        close_called: list[bool] = []
        original_close = session.close

        def tracked_close() -> None:
            close_called.append(True)
            original_close()

        session.close = tracked_close  # type: ignore[method-assign]

        # Complete the generator normally
        with contextlib.suppress(StopIteration):
            next(gen)

        # Verify session.close() was called
        assert close_called

    def test_session_rollback_on_exception(self) -> None:
        """When an exception occurs, the session should be rolled back."""
        s = _make_settings()
        engine = create_engine_from_settings(s)
        sm = create_sessionmaker(engine)

        gen = get_db_session(sm)
        session = next(gen)
        assert isinstance(session, Session)

        # Monkeypatch rollback and close to track them
        rollback_called: list[bool] = []
        close_called: list[bool] = []
        original_rollback = session.rollback
        original_close = session.close

        def tracked_rollback() -> None:
            rollback_called.append(True)
            original_rollback()

        def tracked_close() -> None:
            close_called.append(True)
            original_close()

        session.rollback = tracked_rollback  # type: ignore[method-assign]
        session.close = tracked_close  # type: ignore[method-assign]

        # Simulate an exception propagating through the generator.
        # get_db_session catches Exception, rolls back, and re-raises.
        try:
            gen.throw(ValueError, ValueError("test error"))  # type: ignore[attr-defined]
        except ValueError:
            pass
        except StopIteration:
            pass

        # Verify rollback and close were called
        assert rollback_called
        assert close_called

    def test_get_db_session_without_factory_raises(self) -> None:
        with pytest.raises(RuntimeError, match="sessionmaker"):
            gen = get_db_session(None)
            next(gen)


# ---------------------------------------------------------------------------
# 6. check_database_connection
# ---------------------------------------------------------------------------


class TestCheckDatabaseConnection:
    def test_check_returns_ok_for_sqlite(self) -> None:
        s = _make_settings()
        engine = create_engine_from_settings(s)
        result = check_database_connection(engine)
        assert result["status"] == "ok"

    def test_check_returns_unavailable_for_bad_url(self) -> None:
        """A bad SQLite URL should return unavailable, not raise."""
        # Use a bad SQLite URL to avoid psycopg2 dependency.
        # A non-existent file path will fail on connect.
        s = _make_settings(
            DATABASE_URL="sqlite:///nonexistent/deep/path/that/does/not/exist.db",
        )
        engine = create_engine_from_settings(s)
        result = check_database_connection(engine)
        assert result["status"] == "unavailable"
        assert "error" in result


# ---------------------------------------------------------------------------
# 7. PostgreSQL URL engine creation (no real Postgres required)
# ---------------------------------------------------------------------------


class TestPostgresqlEngineCreation:
    """Verify that a PostgreSQL URL can produce an Engine without a live server.

    These tests guard against missing DBAPI drivers (psycopg2) and ensure
    ``create_engine_from_settings`` does not eagerly connect.
    """

    def test_postgresql_engine_created_without_connect(self) -> None:
        """Engine creation must succeed for a postgresql:// URL.

        This proves the psycopg2 DBAPI is installed and the engine factory
        path does not require a running PostgreSQL instance.
        """
        s = _make_settings(
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/campus_agent",
        )
        engine = create_engine_from_settings(s)
        assert isinstance(engine, Engine)
        assert engine.url.drivername == "postgresql"

    def test_postgresql_engine_does_not_connect_on_creation(self) -> None:
        """``create_engine_from_settings`` must not call ``connect()``."""
        s = _make_settings(
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/campus_agent",
        )
        engine = create_engine_from_settings(s)
        # The pool should exist but report zero checked-out connections.
        assert engine.pool is not None
        # No connection should have been checked out.
        assert engine.pool.checkedout() == 0  # type: ignore[attr-defined]

    def test_postgresql_engine_pool_pre_ping(self) -> None:
        """PostgreSQL engines must use pool_pre_ping for stale connection detection."""
        s = _make_settings(
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/campus_agent",
        )
        engine = create_engine_from_settings(s)
        assert engine.pool._pre_ping is True  # type: ignore[attr-defined]

    def test_postgresql_engine_echo_flag(self) -> None:
        """DB_ECHO_SQL must be propagated to the PostgreSQL engine."""
        s = _make_settings(
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/campus_agent",
            DB_ECHO_SQL="true",
        )
        engine = create_engine_from_settings(s)
        assert engine.echo is True
