"""P6-11+12: Audit log model and service tests.

Tests:
- AuditLog model has no content/prompt/plaintext fields.
- log_audit writes entries without content.
- list_my_audit_logs returns only the user's own logs.
- Audit log repr does not contain content.
- memory_read, memory_write, memory_delete are audited.
- consent_grant, consent_revoke are audited.
- agent_config_update is audited.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from src.modules.audit.models import AuditAction, AuditLog, AuditResult
from src.modules.audit.repository import AuditRepository
from src.modules.audit.service import list_my_audit_logs, log_audit
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="audit@example.com",
        password_hash="fake",
        display_name="Audit User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def other_user(test_db_session: Session) -> User:
    user = User(
        email="audit-other@example.com",
        password_hash="fake",
        display_name="Audit Other",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


class TestAuditLogModel:
    """Test AuditLog ORM model."""

    def test_no_content_fields(self) -> None:
        """AuditLog must not have content/prompt/plaintext columns."""
        col_names = {c.name for c in AuditLog.__table__.columns}
        forbidden = {"content", "prompt", "plaintext", "memory_plaintext", "encrypted_content"}
        assert not forbidden.intersection(col_names), (
            f"Forbidden columns found: {forbidden.intersection(col_names)}"
        )

    def test_has_required_fields(self) -> None:
        """AuditLog has all required fields."""
        col_names = {c.name for c in AuditLog.__table__.columns}
        required = {
            "id", "actor_user_id", "action", "resource_type", "resource_id",
            "purpose", "result", "request_id", "metadata_json", "created_at",
        }
        assert required.issubset(col_names), f"Missing: {required - col_names}"

    def test_repr_no_content(self, test_db_session: Session, test_user: User) -> None:
        """repr must not contain metadata content."""
        log = AuditLog(
            actor_user_id=test_user.id,
            action="memory_read",
            resource_type="memory",
            resource_id="abc-123",
            purpose="chat_reply",
            result="SUCCESS",
            metadata_json=json.dumps({"secret": "should-not-appear"}),
        )
        repr_str = repr(log)
        assert "should-not-appear" not in repr_str
        assert "metadata_json" not in repr_str

    def test_audit_action_enum(self) -> None:
        assert AuditAction.MEMORY_READ == "memory_read"
        assert AuditAction.MEMORY_WRITE == "memory_write"
        assert AuditAction.MEMORY_DELETE == "memory_delete"
        assert AuditAction.CONSENT_GRANT == "consent_grant"
        assert AuditAction.CONSENT_REVOKE == "consent_revoke"
        assert AuditAction.AGENT_CONFIG_UPDATE == "agent_config_update"
        assert AuditAction.AGENT_RUN == "agent_run"

    def test_audit_result_enum(self) -> None:
        assert AuditResult.SUCCESS == "SUCCESS"
        assert AuditResult.DENIED == "DENIED"
        assert AuditResult.ERROR == "ERROR"


class TestAuditService:
    """Test audit service."""

    def test_log_audit_creates_entry(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """log_audit creates an audit log entry."""
        log_audit(
            actor_id=test_user.id,
            action="memory_read",
            resource_type="memory",
            resource_id="mem-001",
            purpose="chat_reply",
            result="SUCCESS",
            session=test_db_session,
        )
        test_db_session.flush()

        repo = AuditRepository(test_db_session)
        logs = repo.list_by_actor(test_user.id)
        assert len(logs) == 1
        assert logs[0].action == "memory_read"
        assert logs[0].result == "SUCCESS"

    def test_log_audit_no_content(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Audit log entry does not store content/plaintext."""
        log_audit(
            actor_id=test_user.id,
            action="memory_read",
            resource_type="memory",
            resource_id="mem-001",
            purpose="self",
            result="SUCCESS",
            metadata={"key": "value"},
            session=test_db_session,
        )
        test_db_session.flush()

        repo = AuditRepository(test_db_session)
        logs = repo.list_by_actor(test_user.id)
        assert len(logs) == 1
        # metadata_json should only contain the provided metadata
        meta = json.loads(logs[0].metadata_json) if logs[0].metadata_json else {}
        assert meta == {"key": "value"}
        # No content/plaintext fields on the model
        assert not hasattr(logs[0], "content")
        assert not hasattr(logs[0], "plaintext")

    def test_list_my_audit_logs_only_own(
        self, test_db_session: Session, test_user: User, other_user: User
    ) -> None:
        """list_my_audit_logs returns only the user's own logs."""
        log_audit(
            actor_id=test_user.id,
            action="memory_read",
            resource_type="memory",
            resource_id="mem-001",
            session=test_db_session,
        )
        log_audit(
            actor_id=other_user.id,
            action="memory_read",
            resource_type="memory",
            resource_id="mem-002",
            session=test_db_session,
        )
        test_db_session.flush()

        result = list_my_audit_logs(test_user, test_db_session)
        assert result["total"] == 1
        assert result["audit_logs"][0]["resource_id"] == "mem-001"

    def test_list_my_audit_logs_metadata_no_content(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Audit log response does not include content/plaintext."""
        log_audit(
            actor_id=test_user.id,
            action="memory_write",
            resource_type="memory",
            resource_id="mem-003",
            metadata={"agent_id": "agent-001"},
            session=test_db_session,
        )
        test_db_session.flush()

        result = list_my_audit_logs(test_user, test_db_session)
        log = result["audit_logs"][0]
        # Should not have content or plaintext keys
        assert "content" not in log
        assert "plaintext" not in log
        assert "prompt" not in log

    def test_audit_with_request_id(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Audit log can store request_id."""
        log_audit(
            actor_id=test_user.id,
            action="consent_grant",
            resource_type="consent",
            resource_id="consent-001",
            request_id="req-12345",
            session=test_db_session,
        )
        test_db_session.flush()

        result = list_my_audit_logs(test_user, test_db_session)
        assert result["audit_logs"][0]["request_id"] == "req-12345"


class TestAuditIntegration:
    """Test that audit logs are created by other services."""

    def test_memory_create_audited(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Memory creation is audited."""
        from src.modules.memories.encryption import reset_encryption_service
        from src.modules.memories.service import create_memory

        reset_encryption_service()
        create_memory(
            test_user,
            {"content": "test", "category": "PREFERENCE"},
            test_db_session,
        )

        result = list_my_audit_logs(test_user, test_db_session)
        actions = [log["action"] for log in result["audit_logs"]]
        assert "memory_write" in actions

    def test_consent_grant_audited(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Consent grant is audited."""
        from src.modules.agents.models import Agent, AgentType, DelegationLevel
        from src.modules.memories.consent import grant_consent

        agent = Agent(
            owner_user_id=test_user.id,
            type=AgentType.PERSONAL.value,
            name="Test",
            delegation_level=DelegationLevel.L0.value,
            status="ACTIVE",
        )
        test_db_session.add(agent)
        test_db_session.flush()

        grant_consent(test_user.id, agent.id, "chat_reply", test_db_session)

        result = list_my_audit_logs(test_user, test_db_session)
        actions = [log["action"] for log in result["audit_logs"]]
        assert "consent_grant" in actions

    def test_agent_config_update_audited(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Agent config update is audited."""
        from src.modules.agents.service import create_personal_agent, update_agent

        create_personal_agent(test_user, test_db_session)
        from src.modules.agents.repository import AgentRepository

        repo = AgentRepository(test_db_session)
        agent = repo.get_personal_agent(test_user.id)
        assert agent is not None

        update_agent(test_user, agent.id, {"name": "Updated"}, test_db_session)

        result = list_my_audit_logs(test_user, test_db_session)
        actions = [log["action"] for log in result["audit_logs"]]
        assert "agent_config_update" in actions
