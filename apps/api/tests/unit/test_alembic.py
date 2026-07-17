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
                "organization_memberships",
                "agents",
                "agent_runs",
                "memory_items",
                "consent_records",
                "audit_logs",
                "conversations",
                "conversation_participants",
                "messages",
            }
            assert not business_tables.intersection(set(table_names))
        engine.dispose()

    def test_business_tables_exist_after_upgrade(self) -> None:
        """After ``upgrade head``, the P3+P4 business tables should exist."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "alembic_version" in table_names
            expected_tables = {
                "users",
                "student_profiles",
                "auth_sessions",
                "refresh_tokens",
                "organizations",
                "organization_memberships",
                "agents",
                "agent_runs",
                "memory_items",
                "consent_records",
                "audit_logs",
                "conversations",
                "conversation_participants",
                "messages",
            }
            missing = expected_tables - set(table_names)
            assert not missing, f"Missing tables: {missing}"
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
            assert "organizations" in table_names
            assert "organization_memberships" in table_names
            # After re-upgrade, P6 tables should also exist
            assert "agents" in table_names
            assert "agent_runs" in table_names
            assert "memory_items" in table_names
            assert "consent_records" in table_names
            assert "audit_logs" in table_names
            assert "conversations" in table_names
            assert "conversation_participants" in table_names
            assert "messages" in table_names
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


# ---------------------------------------------------------------------------
# 5. P4 organization table structure
# ---------------------------------------------------------------------------


class TestP4OrganizationTables:
    """Test that the 0003 migration creates the P4 tables correctly."""

    @pytest.fixture(autouse=True)
    def _temp_db(self, tmp_path: Path) -> Iterator[None]:
        self.db_file = tmp_path / "test_p4_migrations.db"
        self.db_url = _temp_sqlite_url(str(self.db_file))
        self.cfg = _make_alembic_config(self.db_url)
        yield
        if self.db_file.exists():
            self.db_file.unlink()

    def test_upgrade_creates_organizations_table(self) -> None:
        """upgrade head must create the organizations table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "organizations" in inspector.get_table_names()
            # Check key columns
            org_columns = {c["name"] for c in inspector.get_columns("organizations")}
            expected = {
                "id", "name", "slug", "type", "parent_id",
                "description", "visibility", "join_policy", "status",
                "capacity", "created_by", "created_at", "updated_at",
                "archived_at", "deleted_at",
            }
            assert expected.issubset(org_columns), f"Missing columns: {expected - org_columns}"
            # Check indexes
            org_indexes = {i["name"] for i in inspector.get_indexes("organizations")}
            assert "ix_organizations_parent_id" in org_indexes
            assert "ix_organizations_type" in org_indexes
            assert "ix_organizations_status" in org_indexes
        engine.dispose()

    def test_upgrade_creates_memberships_table(self) -> None:
        """upgrade head must create the organization_memberships table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "organization_memberships" in inspector.get_table_names()
            # Check key columns
            mem_columns = {c["name"] for c in inspector.get_columns("organization_memberships")}
            expected = {
                "id", "organization_id", "user_id", "role", "status",
                "invited_by", "joined_at", "left_at",
                "created_at", "updated_at",
            }
            assert expected.issubset(mem_columns), f"Missing columns: {expected - mem_columns}"
            # Check indexes
            mem_indexes = {i["name"] for i in inspector.get_indexes("organization_memberships")}
            assert "ix_organization_memberships_organization_id" in mem_indexes
            assert "ix_organization_memberships_user_id" in mem_indexes
            assert "ix_organization_memberships_role" in mem_indexes
            assert "ix_organization_memberships_status" in mem_indexes
            # Check unique constraint
            uniques = inspector.get_unique_constraints("organization_memberships")
            uq_names = {u["name"] for u in uniques}
            assert "uq_organization_memberships_org_user" in uq_names
        engine.dispose()

    def test_downgrade_removes_p4_tables(self) -> None:
        """downgrade to 0002 must remove P4 tables but keep P3 tables."""
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "0002_user_auth")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "organizations" not in table_names
            assert "organization_memberships" not in table_names
            # P3 tables should still exist
            assert "users" in table_names
            assert "auth_sessions" in table_names
        engine.dispose()


# ---------------------------------------------------------------------------
# 6. P5 conversation/message table structure
# ---------------------------------------------------------------------------


class TestP5ConversationTables:
    """Test that the 0004 migration creates the P5 tables correctly."""

    @pytest.fixture(autouse=True)
    def _temp_db(self, tmp_path: Path) -> Iterator[None]:
        self.db_file = tmp_path / "test_p5_migrations.db"
        self.db_url = _temp_sqlite_url(str(self.db_file))
        self.cfg = _make_alembic_config(self.db_url)
        yield
        if self.db_file.exists():
            self.db_file.unlink()

    def test_upgrade_creates_conversations_table(self) -> None:
        """upgrade head must create the conversations table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "conversations" in inspector.get_table_names()
            conv_columns = {c["name"] for c in inspector.get_columns("conversations")}
            expected = {
                "id", "type", "title", "organization_id", "created_by",
                "status", "created_at", "updated_at", "deleted_at",
            }
            assert expected.issubset(conv_columns), f"Missing columns: {expected - conv_columns}"
            conv_indexes = {i["name"] for i in inspector.get_indexes("conversations")}
            assert "ix_conversations_type" in conv_indexes
            assert "ix_conversations_status" in conv_indexes
            assert "ix_conversations_organization_id" in conv_indexes
        engine.dispose()

    def test_upgrade_creates_participants_table(self) -> None:
        """upgrade head must create the conversation_participants table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "conversation_participants" in inspector.get_table_names()
            part_columns = {c["name"] for c in inspector.get_columns("conversation_participants")}
            expected = {
                "id", "conversation_id", "participant_type",
                "participant_user_id", "participant_agent_id",
                "role", "status", "joined_at", "left_at",
                "created_at", "updated_at",
            }
            assert expected.issubset(part_columns), f"Missing columns: {expected - part_columns}"
            part_indexes = {i["name"] for i in inspector.get_indexes("conversation_participants")}
            assert "ix_conversation_participants_conversation_id" in part_indexes
            assert "ix_conversation_participants_participant_user_id" in part_indexes
            assert "ix_conversation_participants_status" in part_indexes
            uniques = inspector.get_unique_constraints("conversation_participants")
            uq_names = {u["name"] for u in uniques}
            assert "uq_conversation_participants_unique" in uq_names
        engine.dispose()

    def test_upgrade_creates_messages_table(self) -> None:
        """upgrade head must create the messages table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "messages" in inspector.get_table_names()
            msg_columns = {c["name"] for c in inspector.get_columns("messages")}
            expected = {
                "id", "conversation_id", "sender_type", "sender_user_id",
                "sender_agent_id", "message_type", "content", "payload_json",
                "idempotency_key", "status", "sequence",
                "created_at", "deleted_at",
            }
            assert expected.issubset(msg_columns), f"Missing columns: {expected - msg_columns}"
            msg_indexes = {i["name"] for i in inspector.get_indexes("messages")}
            assert "ix_messages_conversation_id" in msg_indexes
            assert "ix_messages_created_at" in msg_indexes
            assert "ix_messages_idempotency_key" in msg_indexes
            assert "ix_messages_status" in msg_indexes
            assert "ix_messages_conversation_created" in msg_indexes
        engine.dispose()

    def test_downgrade_removes_p5_tables(self) -> None:
        """downgrade to 0003 must remove P5 tables but keep P4 tables."""
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "0003_org_member")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "conversations" not in table_names
            assert "conversation_participants" not in table_names
            assert "messages" not in table_names
            assert "organization_memberships" in table_names
            # P5 and P6 tables should also be removed after downgrade to 0003
            assert "agents" not in table_names
            assert "agent_runs" not in table_names
            assert "memory_items" not in table_names
            assert "consent_records" not in table_names
            assert "audit_logs" not in table_names
        engine.dispose()


# ---------------------------------------------------------------------------
# 7. P6 agent/memory/consent/audit table structure
# ---------------------------------------------------------------------------


class TestP6AgentMemoryTables:
    """Test that the 0005 migration creates the P6 tables correctly."""

    @pytest.fixture(autouse=True)
    def _temp_db(self, tmp_path: Path) -> Iterator[None]:
        self.db_file = tmp_path / "test_p6_migrations.db"
        self.db_url = _temp_sqlite_url(str(self.db_file))
        self.cfg = _make_alembic_config(self.db_url)
        yield
        if self.db_file.exists():
            self.db_file.unlink()

    def test_upgrade_creates_agents_table(self) -> None:
        """upgrade head must create the agents table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "agents" in inspector.get_table_names()
            cols = {c["name"] for c in inspector.get_columns("agents")}
            expected = {
                "id", "owner_user_id", "type", "name", "avatar_url",
                "public_persona", "private_config_encrypted",
                "delegation_level", "status",
                "created_at", "updated_at", "deleted_at",
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"
            indexes = {i["name"] for i in inspector.get_indexes("agents")}
            assert "ix_agents_owner_user_id" in indexes
        engine.dispose()

    def test_upgrade_creates_agent_runs_table(self) -> None:
        """upgrade head must create the agent_runs table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "agent_runs" in inspector.get_table_names()
            cols = {c["name"] for c in inspector.get_columns("agent_runs")}
            expected = {
                "id", "agent_id", "actor_user_id", "purpose",
                "input_hash", "output_hash", "model_name",
                "token_count", "latency_ms", "status", "created_at",
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"
        engine.dispose()

    def test_upgrade_creates_memory_items_table(self) -> None:
        """upgrade head must create the memory_items table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "memory_items" in inspector.get_table_names()
            cols = {c["name"] for c in inspector.get_columns("memory_items")}
            expected = {
                "id", "owner_user_id", "agent_id", "category",
                "sensitivity_level", "source", "content_encrypted",
                "content_hash", "encryption_key_version",
                "expires_at", "deleted_at", "created_at", "updated_at",
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"
            indexes = {i["name"] for i in inspector.get_indexes("memory_items")}
            assert "ix_memory_items_owner_user_id" in indexes
            assert "ix_memory_items_agent_id" in indexes
            assert "ix_memory_items_category" in indexes
        engine.dispose()

    def test_upgrade_creates_consent_records_table(self) -> None:
        """upgrade head must create the consent_records table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "consent_records" in inspector.get_table_names()
            cols = {c["name"] for c in inspector.get_columns("consent_records")}
            expected = {
                "id", "grantor_user_id", "grantee_agent_id", "purpose",
                "scope_json", "status", "granted_at", "expires_at",
                "revoked_at", "created_at", "updated_at", "memory_id",
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"
        engine.dispose()

    def test_upgrade_creates_audit_logs_table(self) -> None:
        """upgrade head must create the audit_logs table."""
        command.upgrade(self.cfg, "head")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            assert "audit_logs" in inspector.get_table_names()
            cols = {c["name"] for c in inspector.get_columns("audit_logs")}
            expected = {
                "id", "actor_user_id", "action", "resource_type",
                "resource_id", "purpose", "result", "request_id",
                "metadata_json", "created_at",
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"
            indexes = {i["name"] for i in inspector.get_indexes("audit_logs")}
            assert "ix_audit_logs_actor_user_id" in indexes
            assert "ix_audit_logs_action" in indexes
        engine.dispose()

    def test_downgrade_removes_p6_tables(self) -> None:
        """downgrade to 0004 must remove P6 tables but keep P5 tables."""
        command.upgrade(self.cfg, "head")
        command.downgrade(self.cfg, "0004_convo_msg")

        from sqlalchemy import create_engine

        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()
            assert "agents" not in table_names
            assert "agent_runs" not in table_names
            assert "memory_items" not in table_names
            assert "consent_records" not in table_names
            assert "audit_logs" not in table_names
            # P5 tables should still exist
            assert "conversations" in table_names
            assert "messages" in table_names
        engine.dispose()
