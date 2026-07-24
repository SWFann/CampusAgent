"""Personal workspace chat integration tests."""

from __future__ import annotations

from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from src.modules.agents.models import Agent, WorkspaceMessage
from src.modules.model_gateway import service as gateway_service_module
from src.modules.model_gateway.mock_provider import MockProvider
from src.modules.model_gateway.service import ModelGatewayService


def _register(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "workspace@example.edu",
            "password": "SecurePass123",
            "display_name": "Workspace User",
            "student_no": "20260901",
            "organization_ids": [],
        },
    )
    assert response.status_code == 201
    return client.cookies.get("csrf_token", "")


def test_workspace_chat_uses_configured_provider(
    db_client: TestClient,
    test_engine,
    monkeypatch,
) -> None:
    csrf_token = _register(db_client)
    provider = MockProvider(
        name="stepfun",
        fixed_output="你好，这是来自个人 Agent 的回答。",
    )
    monkeypatch.setattr(
        gateway_service_module,
        "_service",
        ModelGatewayService(external=provider),
    )

    response = db_client.post(
        "/api/v1/agents/me/chat",
        headers={"X-CSRF-Token": csrf_token},
        json={"messages": [{"role": "user", "content": "帮我规划今天的安排"}]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["reply"] == "你好，这是来自个人 Agent 的回答。"
    assert data["provider"] == "stepfun"
    assert data["thread_title"] == "帮我规划今天的安排"

    listed = db_client.get("/api/v1/agents/me/workspace/threads")
    assert listed.status_code == 200
    threads = listed.json()["data"]["threads"]
    assert threads[0]["id"] == data["thread_id"]
    assert threads[0]["message_count"] == 2

    detail = db_client.get(f"/api/v1/agents/me/workspace/threads/{data['thread_id']}")
    assert detail.status_code == 200
    assert [message["content"] for message in detail.json()["data"]["messages"]] == [
        "帮我规划今天的安排",
        "你好，这是来自个人 Agent 的回答。",
    ]

    with Session(test_engine) as session:
        stored = session.query(WorkspaceMessage).all()
        assert len(stored) == 2
        assert all("帮我规划" not in message.content_encrypted for message in stored)


def test_workspace_chat_requires_authentication(db_client: TestClient) -> None:
    response = db_client.post(
        "/api/v1/agents/me/chat",
        json={"messages": [{"role": "user", "content": "你好"}]},
    )
    assert response.status_code == 401


def test_workspace_chat_requires_last_turn_from_user(
    db_client: TestClient,
) -> None:
    csrf_token = _register(db_client)
    response = db_client.post(
        "/api/v1/agents/me/chat",
        headers={"X-CSRF-Token": csrf_token},
        json={"messages": [{"role": "assistant", "content": "你好"}]},
    )
    assert response.status_code == 422


def test_personal_model_route_is_encrypted_and_key_is_never_returned(
    db_client: TestClient,
    test_engine,
) -> None:
    csrf_token = _register(db_client)

    initial = db_client.get("/api/v1/agents/me/model-route")
    assert initial.status_code == 200
    assert initial.json()["data"]["mode"] == "PLATFORM"

    saved = db_client.patch(
        "/api/v1/agents/me/model-route",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "mode": "PERSONAL",
            "name": "我的 StepFun",
            "provider": "STEPFUN",
            "base_url": "https://api.stepfun.com/v1",
            "model": "step-3.5-flash",
            "api_key": "personal-test-key-123456",
        },
    )
    assert saved.status_code == 200
    data = saved.json()["data"]
    assert data["mode"] == "PERSONAL"
    assert data["has_api_key"] is True
    assert data["active_profile_id"]
    assert data["profiles"][0]["name"] == "我的 StepFun"
    assert "api_key" not in data
    assert "personal-test-key-123456" not in saved.text

    with Session(test_engine) as session:
        agent = session.query(Agent).one()
        assert agent.model_route_encrypted is not None
        assert "personal-test-key-123456" not in agent.model_route_encrypted

    second = db_client.patch(
        "/api/v1/agents/me/model-route",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "mode": "PERSONAL",
            "name": "我的 OpenAI",
            "provider": "OPENAI",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4.1-mini",
            "api_key": "second-personal-key-123456",
        },
    )
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert len(second_data["profiles"]) == 2
    assert second_data["provider"] == "OPENAI"

    first_profile = data["profiles"][0]
    switched = db_client.patch(
        "/api/v1/agents/me/model-route",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "mode": "PERSONAL",
            "profile_id": first_profile["id"],
            "name": first_profile["name"],
            "provider": first_profile["provider"],
            "base_url": first_profile["base_url"],
            "model": first_profile["model"],
        },
    )
    assert switched.status_code == 200
    assert switched.json()["data"]["active_profile_id"] == first_profile["id"]

    second_id = second_data["active_profile_id"]
    deleted = db_client.delete(
        f"/api/v1/agents/me/model-route/profiles/{second_id}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert deleted.status_code == 200
    assert len(deleted.json()["data"]["profiles"]) == 1


def test_personal_model_route_requires_a_key(db_client: TestClient) -> None:
    csrf_token = _register(db_client)
    response = db_client.patch(
        "/api/v1/agents/me/model-route",
        headers={"X-CSRF-Token": csrf_token},
        json={"mode": "PERSONAL", "model": "step-3.5-flash"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


def test_custom_model_route_blocks_private_network_urls(db_client: TestClient) -> None:
    csrf_token = _register(db_client)
    response = db_client.patch(
        "/api/v1/agents/me/model-route",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "mode": "PERSONAL",
            "name": "Unsafe local route",
            "provider": "CUSTOM",
            "base_url": "https://127.0.0.1/v1",
            "model": "local-model",
            "api_key": "personal-test-key-123456",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "AGENT_MODEL_ROUTE_INVALID"
