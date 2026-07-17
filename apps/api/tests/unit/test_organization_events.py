"""
Unit tests for Organization domain events (P4-10).

Tests verify:
- Creating an org publishes OrganizationCreated once.
- Adding a member publishes OrganizationMemberJoined once.
- Leaving publishes OrganizationMemberLeft once.
- Role change publishes OrganizationMemberRoleChanged once.
- Events do NOT contain email/student_no/password/token.
- Handler exceptions do NOT block the main flow.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    create_org,
    register_and_login,
    set_auth_cookies,
)


class TestEventCollector:
    """Helper to collect events from the bus."""

    @staticmethod
    def subscribe() -> tuple[list, dict]:
        """Subscribe to all org events. Returns (events_list, cleanup_dict)."""
        from src.events.bus import default_event_bus
        from src.modules.organizations.events import (
            OrganizationArchived,
            OrganizationCreated,
            OrganizationMemberJoined,
            OrganizationMemberLeft,
            OrganizationMemberRoleChanged,
        )

        events: list = []

        class Collector:
            def handle(self, event):
                events.append(event)

        collector = Collector()
        event_types = [
            OrganizationCreated,
            OrganizationArchived,
            OrganizationMemberJoined,
            OrganizationMemberLeft,
            OrganizationMemberRoleChanged,
        ]
        for et in event_types:
            default_event_bus.subscribe(et, collector)

        return events, {"collector": collector}


class TestOrganizationCreatedEvent:
    """Test OrganizationCreated event."""

    def test_create_org_publishes_event(self, db_client: TestClient) -> None:
        """Creating an org publishes OrganizationCreated once."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="事件测试组织")

        from src.modules.organizations.events import OrganizationCreated

        created_events = [e for e in events if isinstance(e, OrganizationCreated)]
        assert len(created_events) == 1
        assert created_events[0].organization_type is not None

    def test_event_no_sensitive_data(self, db_client: TestClient) -> None:
        """Events do not contain email/student_no/password/token."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(
            db_client, email="evt@example.edu", student_no="20268001"
        )
        set_auth_cookies(db_client, owner)
        create_org(db_client, owner, name="安全事件测试")

        # Check all events for sensitive data
        for event in events:
            event_str = str(event).lower()
            assert "email" not in event_str
            assert "student_no" not in event_str
            assert "password" not in event_str
            assert "token" not in event_str


class TestMemberJoinedEvent:
    """Test OrganizationMemberJoined event."""

    def test_add_member_publishes_event(self, db_client: TestClient) -> None:
        """Adding a member publishes OrganizationMemberJoined once."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="成员事件测试")

        member = register_and_login(
            db_client, email="mevt@example.edu", student_no="20268002"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )

        from src.modules.organizations.events import OrganizationMemberJoined

        joined_events = [e for e in events if isinstance(e, OrganizationMemberJoined)]
        # Could be 1 (just the add) or more if create_org also triggered
        # But create_org publishes OrganizationCreated, not Joined
        assert len(joined_events) == 1
        assert joined_events[0].role == "MEMBER"
        assert joined_events[0].status == "ACTIVE"

    def test_join_publishes_event(self, db_client: TestClient) -> None:
        """Self-join publishes OrganizationMemberJoined once."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="加入事件测试", join_policy="OPEN")

        member = register_and_login(
            db_client, email="jevt@example.edu", student_no="20268003"
        )
        set_auth_cookies(db_client, member)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )

        from src.modules.organizations.events import OrganizationMemberJoined

        joined_events = [e for e in events if isinstance(e, OrganizationMemberJoined)]
        assert len(joined_events) == 1


class TestMemberLeftEvent:
    """Test OrganizationMemberLeft event."""

    def test_leave_publishes_event(self, db_client: TestClient) -> None:
        """Leaving publishes OrganizationMemberLeft once."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="退出事件测试", join_policy="OPEN")

        member = register_and_login(
            db_client, email="levt@example.edu", student_no="20268004"
        )
        set_auth_cookies(db_client, member)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/join",
            headers=auth_headers(member["csrf_token"]),
        )
        db_client.post(
            f"/api/v1/organizations/{org['id']}/leave",
            headers=auth_headers(member["csrf_token"]),
        )

        from src.modules.organizations.events import OrganizationMemberLeft

        left_events = [e for e in events if isinstance(e, OrganizationMemberLeft)]
        assert len(left_events) == 1
        assert left_events[0].action == "left"

    def test_remove_publishes_event(self, db_client: TestClient) -> None:
        """Removing a member publishes OrganizationMemberLeft once."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="移除事件测试")

        member = register_and_login(
            db_client, email="revt@example.edu", student_no="20268005"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        db_client.delete(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        from src.modules.organizations.events import OrganizationMemberLeft

        left_events = [e for e in events if isinstance(e, OrganizationMemberLeft)]
        assert len(left_events) == 1
        assert left_events[0].action == "removed"


class TestRoleChangedEvent:
    """Test OrganizationMemberRoleChanged event."""

    def test_role_change_publishes_event(self, db_client: TestClient) -> None:
        """Role change publishes OrganizationMemberRoleChanged once."""
        events, _ = TestEventCollector.subscribe()

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        org = create_org(db_client, owner, name="角色事件测试")

        member = register_and_login(
            db_client, email="rcevt@example.edu", student_no="20268006"
        )
        set_auth_cookies(db_client, owner)
        db_client.post(
            f"/api/v1/organizations/{org['id']}/members",
            json={"user_id": member["user_id"], "role": "MEMBER"},
            headers=auth_headers(owner["csrf_token"]),
        )
        db_client.patch(
            f"/api/v1/organizations/{org['id']}/members/{member['user_id']}",
            json={"role": "ADMIN"},
            headers=auth_headers(owner["csrf_token"]),
        )

        from src.modules.organizations.events import (
            OrganizationMemberRoleChanged,
        )

        changed_events = [
            e for e in events if isinstance(e, OrganizationMemberRoleChanged)
        ]
        assert len(changed_events) == 1
        assert changed_events[0].old_role == "MEMBER"
        assert changed_events[0].new_role == "ADMIN"


class TestHandlerExceptionSafety:
    """Test that handler exceptions don't block the main flow."""

    def test_failing_handler_does_not_block(self, db_client: TestClient) -> None:
        """A failing handler does not prevent the operation from succeeding."""
        from src.events.bus import default_event_bus
        from src.modules.organizations.events import OrganizationCreated

        class FailingHandler:
            def handle(self, event):
                raise RuntimeError("Handler failure")

        default_event_bus.subscribe(OrganizationCreated, FailingHandler())

        owner = register_and_login(db_client)
        set_auth_cookies(db_client, owner)
        # This should succeed despite the failing handler
        org = create_org(db_client, owner, name="异常处理器测试")
        assert org["id"]  # Operation succeeded
