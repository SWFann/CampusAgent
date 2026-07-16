"""
Unit tests for Alembic migration baseline (P2-04).

These tests verify:
- Alembic config file (alembic.ini) can be loaded.
- env.py sets target_metadata to Base.metadata.
- ``upgrade head`` succeeds on a fresh SQLite database.
- ``downgrade base`` succeeds.
- No business tables are created by the baseline migration.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_API_DIR = Path(__file__).resolve().parent.parent.parent  # apps/api
_ALEMBIC_INI = _API_DIR / "alembic.ini"
_ALEMBIC_DIR = _API_DIR / "alembic"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_alembic_config(db_url: str) -> Config:
    """Create an Alembic Config bound to a specific database URL."""
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    # env.py reads from DATABASE_URL env var, so set it.
    os.environ["DATABASE_URL"] = db_url
    return cfg


def _temp_sqlite_url(path: str) -> str:
    """Return a SQLite URL for a temp file path."""
    return f"sqlite:///{path}"


# ---------------------------------------------------------------------------
# 1. Config loading
# ---------------------------------------------------------------------------


class TestAlembicConfig:
    def test_alembic_ini_exists(self) -> None:
        assert _ALEMBIC_INI.exists(), f"{_ALEMBIC_INI} not found"

    def test_alembic_dir_exists(self) -> None:
        assert _ALEMBIC_DIR.exists(), f"{_ALEMBIC_DIR} not found"
        assert (_ALEMBIC_DIR / "env.py").exists()
        assert (_ALEMBIC_DIR / "script.py.mako").exists()

    def test_config_loads(self) -> None:
        cfg = Config(str(_ALEMBIC_INI))
        assert cfg.get_main_option("script_location") == "alembic"

    def test_versions_dir_exists(self) -> None:
        versions = _ALEMBIC_DIR / "versions"
        assert versions.exists()
        assert versions.is_dir()

    def test_baseline_migration_exists(self) -> None:
        versions = _ALEMBIC_DIR / "versions"
        py_files = list(versions.glob("*.py"))
        assert len(py_files) >= 1, "At least one migration file should exist"
        baseline = versions / "0001_baseline.py"
        assert baseline.exists(), "0001_baseline.py not found"


# ---------------------------------------------------------------------------
# 2. env.py structure and metadata
# ---------------------------------------------------------------------------


class TestEnvMetadata:
    def test_env_py_references_base_metadata(self) -> None:
        """env.py should set target_metadata to Base.metadata.

        Instead of importing env.py (which requires an Alembic context),
        we verify the source code references Base.metadata correctly.
        """
        env_path = _ALEMBIC_DIR / "env.py"
        source = env_path.read_text()
        assert "from src.db.base import Base" in source
        assert "target_metadata = Base.metadata" in source

    def test_env_py_resolves_database_url(self) -> None:
        """env.py should resolve DATABASE_URL from env var or Settings."""
        env_path = _ALEMBIC_DIR / "env.py"
        source = env_path.read_text()
        assert "DATABASE_URL" in source
        assert "_resolve_database_url" in source

    def test_env_py_does_not_hardcode_url(self) -> None:
        """env.py should NOT hardcode a database URL."""
        env_path = _ALEMBIC_DIR / "env.py"
        source = env_path.read_text()
        # Should not contain a hardcoded postgresql:// URL
        assert "postgresql://postgres:postgres@" not in source.replace(
            "# ", ""
        )


# ---------------------------------------------------------------------------
# 3. Upgrade / Downgrade on SQLite
# ---------------------------------------------------------------------------


class TestMigrationUpgradeDowngrade:
    """Test that ``upgrade head`` and ``downgrade base`` work on a temp SQLite DB."""

    @pytest.fixture(autouse=True)
    def _temp_db(self, tmp_path: Path) -> Iterator[None]:
        """Create a temp SQLite file and set up the Alembic config."""
        self.db_file = tmp_path / "test_migrations.db"
        self.db_url = _temp_sqlite_url(str(self.db_file))
        self.cfg = _make_alembic_config(self.db_url)
        yield
        # Cleanup
        if self.db_file.exists():
            self.db_file.unlink()

    def test_upgrade_head_creates_alembic_version_table(self) -> None:
        """``upgrade head`` must succeed and create the alembic_version table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "alembic_version" in inspector.get_table_names()
        engine.dispose()

    def test_downgrade_base_clears_version(self) -> None:
        """``downgrade base`` must clear the version stamp and drop business tables.

        Alembic keeps the ``alembic_version`` table after downgrade to
        base, but it should contain 0 rows.  All business tables created
        by migrations should be dropped.
        """
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "base")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            # The alembic_version table may still exist but should have no rows.
            if "alembic_version" in table_names:
                result = conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
                assert result.scalar() == 0
            # No business tables should exist after downgrade to base.
            business_tables = {
                "users",
                "student_profiles",
                "auth_sessions",
                "refresh_tokens",
                "organizations",
                "conversations",
                "messages",
                "agents",
                "memories",
                "scenes",
                "audit_logs",
            }
            assert not business_tables.intersection(set(table_names))
        engine.dispose()

    def test_business_tables_exist_after_upgrade(self) -> None:
        """After ``upgrade head``, the P3 business tables should exist."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "alembic_version" in table_names
            expected_p3_tables = {
                "users",
                "student_profiles",
                "auth_sessions",
                "refresh_tokens",
            }
            missing = expected_p3_tables - set(table_names)
            assert not missing, f"Missing P3 tables: {missing}"
        engine.dispose()

    def test_upgrade_then_downgrade_then_upgrade(self) -> None:
        """The cycle upgrade -> downgrade -> upgrade should work cleanly."""
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "base")
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "alembic_version" in table_names
            # Verify a version row exists
            result = conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
            assert result.scalar() == 1
            # Business tables should exist after re-upgrade
            assert "users" in table_names
            assert "student_profiles" in table_names
            assert "auth_sessions" in table_names
            assert "refresh_tokens" in table_names
        engine.dispose()


# ---------------------------------------------------------------------------
# 4. Offline mode (SQL generation)
# ---------------------------------------------------------------------------


class TestOfflineMode:
    def test_offline_upgrade_generates_sql(self, tmp_path: Path) -> None:
        """Offline mode should generate SQL without a live database."""
        db_file = tmp_path / "offline_test.db"
        db_url = _temp_sqlite_url(str(db_file))
        cfg = _make_alembic_config(db_url)
        # In offline mode, no actual database operations happen.
        command.upgrade(cfg, "head", sql=True)
        # If this doesn't raise, offline mode works.
