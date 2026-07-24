"""Agent service layer — business logic for agent management.

Privacy:
- private_config_encrypted is encrypted before storage.
- Owner can read decrypted config; admin can only read metadata.
- repr and logs never include private_config.
"""

from __future__ import annotations

import ipaddress
import json
import re
import secrets
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...events.bus import default_event_bus
from ..audit.service import log_audit
from ..users.models import User
from .events import PersonalAgentCreated
from .exceptions import (
    AgentModelRouteError,
    AgentNotFoundError,
    AgentPermissionDeniedError,
    InvalidDelegationLevelError,
    WorkspaceThreadNotFoundError,
)
from .models import (
    Agent,
    AgentStatus,
    AgentType,
    DelegationLevel,
    WorkspaceMessage,
    WorkspaceMessageRole,
    WorkspaceThread,
)
from .repository import AgentRepository, WorkspaceRepository

_WORKSPACE_SYSTEM_PROMPT = """
你是 CampusAgent 中面向暨南大学学生的个人 Agent。你的目标是帮助学生更高效地理解信息、
规划校园生活、办理事务和参与协作，同时保护学生的自主权与隐私。

回答原则：
1. 默认使用自然、温和、简洁的中文，先直接回答学生的问题。
2. 不得声称已查询到未提供的实时课表、成绩、通知或办事进度；缺少校园系统数据时要如实说明。
3. 区分“建议/草稿”与“已执行”。发送消息、提交申请、更改日程或联系他人前，必须说明将会发生什么并等待学生确认。
4. 不推断、评价或向教师/管理员披露学生的私人思想、偏好、心理健康信息。
5. 遇到心理健康话题时，以支持学生主动求助和连接专业服务为目的，不做诊断、监控、评分或处分建议。
6. 重要决策始终交由相应责任人最终确认。
""".strip()

_STEPFUN_BASE_URL = "https://api.stepfun.com/v1"
_MODEL_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "OPENAI": {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini"},
    "DEEPSEEK": {"name": "DeepSeek", "base_url": "https://api.deepseek.com", "model": "deepseek-v4-flash"},
    "STEPFUN": {"name": "阶跃星辰", "base_url": _STEPFUN_BASE_URL, "model": "step-3.5-flash"},
    "CUSTOM": {"name": "自定义服务", "base_url": "", "model": ""},
}


def _generate_event_id() -> str:
    return secrets.token_hex(16)


def _validate_delegation_level(level: str) -> None:
    valid = {dl.value for dl in DelegationLevel}
    if level not in valid:
        raise InvalidDelegationLevelError(details={"field": "delegation_level", "value": level})


def _agent_to_read(agent: Agent, include_private_config: bool = False) -> dict[str, Any]:
    """Convert Agent to a safe read dict.

    Never includes private_config_encrypted unless explicitly requested
    (owner-only, after decryption).
    """
    result: dict[str, Any] = {
        "id": str(agent.id),
        "owner_user_id": str(agent.owner_user_id),
        "type": agent.type,
        "name": agent.name,
        "avatar_url": agent.avatar_url,
        "public_persona": agent.public_persona,
        "delegation_level": agent.delegation_level,
        "status": agent.status,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }
    if include_private_config:
        result["has_private_config"] = agent.private_config_encrypted is not None
    else:
        result["has_private_config"] = agent.private_config_encrypted is not None
    return result


def create_personal_agent(
    user: User,
    session: Session,
    *,
    name: str | None = None,
    public_persona: str | None = None,
    private_config_encrypted: str | None = None,
) -> dict[str, Any]:
    """Create a personal agent for a user. Idempotent — skips if exists."""
    repo = AgentRepository(session)
    existing = repo.get_personal_agent(user.id)
    if existing is not None:
        return _agent_to_read(existing)

    agent = Agent(
        owner_user_id=user.id,
        type=AgentType.PERSONAL.value,
        name=name or f"{user.display_name}的智能体",
        public_persona=public_persona,
        private_config_encrypted=private_config_encrypted,
        delegation_level=DelegationLevel.L0.value,
        status=AgentStatus.ACTIVE.value,
    )
    repo.create(agent)
    session.commit()
    session.refresh(agent)

    default_event_bus.publish(
        PersonalAgentCreated(
            event_id=_generate_event_id(),
            agent_id=agent.id,
            owner_user_id=user.id,
            occurred_at=utc_now(),
        )
    )

    return _agent_to_read(agent)


def get_my_agent(user: User, session: Session) -> dict[str, Any]:
    """Get the current user's personal agent."""
    repo = AgentRepository(session)
    agent = repo.get_personal_agent(user.id)
    if agent is None:
        return create_personal_agent(user, session)
    return _agent_to_read(agent, include_private_config=True)


def get_agent_by_id(actor: User, agent_id: UUID, session: Session) -> dict[str, Any]:
    """Get an agent by ID. Owner sees full info; others see metadata only."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)
    if agent is None or agent.status == AgentStatus.DELETED.value:
        raise AgentNotFoundError()

    is_owner = agent.owner_user_id == actor.id
    is_admin = actor.global_role in ("SYSTEM_ADMIN", "SCHOOL_ADMIN")

    if not is_owner and not is_admin:
        raise AgentPermissionDeniedError()

    # Admin can only read metadata, not private_config
    return _agent_to_read(agent, include_private_config=is_owner)


def update_agent(
    actor: User,
    agent_id: UUID,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Update an agent. Only the owner can update."""
    repo = AgentRepository(session)
    agent = repo.get_by_id(agent_id)
    if agent is None or agent.status == AgentStatus.DELETED.value:
        raise AgentNotFoundError()

    if agent.owner_user_id != actor.id:
        raise AgentPermissionDeniedError()

    if "name" in data and data["name"] is not None:
        agent.name = data["name"]
    if "avatar_url" in data:
        agent.avatar_url = data["avatar_url"]
    if "public_persona" in data:
        agent.public_persona = data["public_persona"]
    if "delegation_level" in data and data["delegation_level"] is not None:
        _validate_delegation_level(data["delegation_level"])
        agent.delegation_level = data["delegation_level"]
    if "private_config_encrypted" in data:
        agent.private_config_encrypted = data["private_config_encrypted"]

    repo.save(agent)
    session.commit()
    session.refresh(agent)

    log_audit(
        actor_id=actor.id,
        action="agent_config_update",
        resource_type="agent",
        resource_id=str(agent.id),
        result="SUCCESS",
        session=session,
    )
    return _agent_to_read(agent, include_private_config=True)


def list_my_agents(user: User, session: Session) -> dict[str, Any]:
    """List all agents owned by the current user."""
    repo = AgentRepository(session)
    agents = repo.list_by_owner(user.id)
    return {
        "agents": [_agent_to_read(a) for a in agents],
        "total": len(agents),
    }


def _load_model_route(agent: Agent) -> dict[str, Any]:
    from ..memories.encryption import get_encryption_service

    default: dict[str, Any] = {"mode": "PLATFORM", "active_profile_id": None, "profiles": []}
    if not agent.model_route_encrypted:
        return default
    try:
        decrypted = get_encryption_service().decrypt(agent.model_route_encrypted)
        stored = json.loads(decrypted)
    except (ValueError, TypeError, json.JSONDecodeError):
        raise AgentModelRouteError("个人模型路由无法解密，请重新保存") from None
    if not isinstance(stored, dict):
        raise AgentModelRouteError("个人模型路由格式无效")
    if isinstance(stored.get("profiles"), list):
        return {**default, **stored}

    # Upgrade the single-route format written by the previous release in memory.
    if stored.get("mode") == "PERSONAL" and stored.get("api_key"):
        legacy_profile = {
            "id": "legacy",
            "name": _MODEL_PROVIDER_DEFAULTS["STEPFUN"]["name"],
            "provider": "STEPFUN",
            "model": stored.get("model") or _MODEL_PROVIDER_DEFAULTS["STEPFUN"]["model"],
            "base_url": stored.get("base_url") or _STEPFUN_BASE_URL,
            "api_key": stored["api_key"],
        }
        return {"mode": "PERSONAL", "active_profile_id": "legacy", "profiles": [legacy_profile]}
    return default


def _validate_model_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.hostname:
        raise AgentModelRouteError("API 地址必须是有效的 HTTPS 地址")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise AgentModelRouteError("API 地址不能包含账号、查询参数或片段")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise AgentModelRouteError("不允许使用本机或内网 API 地址")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise AgentModelRouteError("不允许使用私有或保留 IP 地址")
    return normalized


def _active_model_profile(route: dict[str, Any]) -> dict[str, Any] | None:
    active_id = route.get("active_profile_id")
    return next((item for item in route.get("profiles", []) if item.get("id") == active_id), None)


def _save_model_route(agent: Agent, route: dict[str, Any]) -> None:
    from ..memories.encryption import get_encryption_service

    agent.model_route_encrypted = get_encryption_service().encrypt(
        json.dumps(route, ensure_ascii=False, separators=(",", ":"))
    )


def get_agent_model_route(user: User, session: Session) -> dict[str, Any]:
    from ...config import settings

    get_my_agent(user, session)
    agent = AgentRepository(session).get_personal_agent(user.id)
    if agent is None:
        raise AgentNotFoundError()
    route = _load_model_route(agent)
    active = _active_model_profile(route) if route["mode"] == "PERSONAL" else None
    profiles = [
        {
            "id": profile["id"],
            "name": profile["name"],
            "provider": profile["provider"],
            "model": profile["model"],
            "base_url": profile["base_url"],
            "has_api_key": bool(profile.get("api_key")),
        }
        for profile in route.get("profiles", [])
    ]
    return {
        "mode": "PERSONAL" if active else "PLATFORM",
        "active_profile_id": active["id"] if active else None,
        "profiles": profiles,
        "provider": active["provider"] if active else "PLATFORM",
        "model": active["model"] if active else settings.MODEL_GATEWAY_MODEL,
        "base_url": active["base_url"] if active else settings.MODEL_GATEWAY_BASE_URL,
        "has_api_key": bool(active and active.get("api_key")),
    }


def update_agent_model_route(
    user: User,
    session: Session,
    *,
    mode: str,
    profile_id: str | None,
    name: str | None,
    provider: str | None,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
) -> dict[str, Any]:
    get_my_agent(user, session)
    agent = AgentRepository(session).get_personal_agent(user.id)
    if agent is None:
        raise AgentNotFoundError()
    route = _load_model_route(agent)
    if mode == "PLATFORM":
        route["mode"] = "PLATFORM"
        route["active_profile_id"] = None
    else:
        if provider not in _MODEL_PROVIDER_DEFAULTS:
            raise AgentModelRouteError("不支持的模型服务类型")
        profiles: list[dict[str, Any]] = route.get("profiles", [])
        existing = next((item for item in profiles if item.get("id") == profile_id), None)
        if existing is None and len(profiles) >= 10:
            raise AgentModelRouteError("最多可保存 10 套模型配置")
        defaults = _MODEL_PROVIDER_DEFAULTS[provider]
        resolved_url = _validate_model_base_url(base_url or defaults["base_url"])
        resolved_key = (api_key or "").strip() or str((existing or {}).get("api_key") or "")
        if not resolved_key:
            raise AgentModelRouteError("请填写 API 密钥")
        resolved_name = (name or (existing or {}).get("name") or defaults["name"]).strip()
        if not resolved_name:
            raise AgentModelRouteError("请填写配置名称")
        saved_profile = {
            "id": existing["id"] if existing else uuid4().hex,
            "name": resolved_name[:60],
            "provider": provider,
            "model": (model or defaults["model"]).strip(),
            "base_url": resolved_url,
            "api_key": resolved_key,
        }
        if existing:
            profiles[profiles.index(existing)] = saved_profile
        else:
            profiles.append(saved_profile)
        route = {"mode": "PERSONAL", "active_profile_id": saved_profile["id"], "profiles": profiles}
    _save_model_route(agent, route)
    session.commit()
    log_audit(
        actor_id=user.id,
        action="agent_model_route_update",
        resource_type="agent",
        resource_id=str(agent.id),
        result="SUCCESS",
        session=session,
    )
    return get_agent_model_route(user, session)


def delete_agent_model_route_profile(
    user: User, session: Session, profile_id: str
) -> dict[str, Any]:
    get_my_agent(user, session)
    agent = AgentRepository(session).get_personal_agent(user.id)
    if agent is None:
        raise AgentNotFoundError()
    route = _load_model_route(agent)
    profiles = [item for item in route.get("profiles", []) if item.get("id") != profile_id]
    if len(profiles) == len(route.get("profiles", [])):
        raise AgentModelRouteError("模型配置不存在")
    if route.get("active_profile_id") == profile_id:
        route["mode"] = "PLATFORM"
        route["active_profile_id"] = None
    route["profiles"] = profiles
    _save_model_route(agent, route)
    session.commit()
    return get_agent_model_route(user, session)


def test_agent_model_route(user: User, session: Session) -> dict[str, Any]:
    from ...config import settings
    from ..model_gateway.exceptions import ModelGatewayError
    from ..model_gateway.openai_compatible import OpenAICompatibleProvider
    from ..model_gateway.schemas import (
        ChatMessage,
        ChatRequest,
        DataClassification,
        PrivacyContext,
    )

    get_my_agent(user, session)
    agent = AgentRepository(session).get_personal_agent(user.id)
    if agent is None:
        raise AgentNotFoundError()
    route = _load_model_route(agent)
    active = _active_model_profile(route) if route["mode"] == "PERSONAL" else None
    if active:
        provider = OpenAICompatibleProvider(
            base_url=active["base_url"],
            model=active["model"],
            api_key=active["api_key"],
            timeout_ms=min(settings.MODEL_GATEWAY_TIMEOUT_MS, 15000),
            is_external=True,
            name=f"personal-{active['provider'].lower()}",
        )
    else:
        provider = OpenAICompatibleProvider(
            base_url=settings.MODEL_GATEWAY_BASE_URL,
            model=settings.MODEL_GATEWAY_MODEL,
            api_key=settings.MODEL_GATEWAY_API_KEY,
            timeout_ms=min(settings.MODEL_GATEWAY_TIMEOUT_MS, 15000),
            is_external=True,
            name="stepfun",
        )
    selected_model = active["model"] if active else settings.MODEL_GATEWAY_MODEL
    try:
        response = provider.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content="请只回复 OK")],
                privacy_context=PrivacyContext(
                    data_classification=DataClassification.P0,
                    allow_external=True,
                    contains_personal_data=False,
                    purpose="model_route_test",
                ),
                purpose="model_route_test",
                temperature=0,
                max_tokens=8,
            )
        )
    except ModelGatewayError as exc:
        upstream_status = exc.details.get("status")
        upstream_code = exc.details.get("upstream_code")
        if upstream_status in {401, 403}:
            status = "API 密钥无效，或当前项目没有该模型的访问权限"
        elif upstream_status == 404 or upstream_code == "model_not_found":
            status = f"未找到模型 {selected_model}，请核对模型标识"
        elif upstream_status == 429 and upstream_code == "insufficient_quota":
            status = "OpenAI 账户额度不足，请充值或更换有额度的项目密钥"
        elif upstream_status == 429:
            status = "请求被限流或账户额度不足，请稍后重试并检查用量"
        else:
            status = "模型调用失败，请检查模型标识、API 密钥和接口地址"
        return {
            "healthy": False,
            "status": status,
            "latency_ms": None,
            "model": selected_model,
        }
    return {
        "healthy": True,
        "status": "模型调用正常",
        "latency_ms": response.metadata.latency_ms,
        "model": response.model or selected_model,
    }


def _thread_to_read(thread: WorkspaceThread, *, include_messages: bool = False) -> dict[str, Any]:
    def as_utc_iso(value: datetime) -> str:
        # SQLite returns naive values even when the column is timezone-aware.
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")

    result: dict[str, Any] = {
        "id": str(thread.id),
        "title": thread.title,
        "status": thread.status,
        "created_at": as_utc_iso(thread.created_at),
        "updated_at": as_utc_iso(thread.updated_at),
        "message_count": len(thread.messages),
    }
    if include_messages:
        from ..memories.encryption import get_encryption_service

        encryption = get_encryption_service()
        result["messages"] = [
            {
                "id": str(message.id),
                "role": message.role,
                "content": encryption.decrypt(message.content_encrypted),
                "created_at": as_utc_iso(message.created_at),
            }
            for message in thread.messages
        ]
    return result


def create_workspace_thread(
    user: User,
    session: Session,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    """Create an empty personal task owned exclusively by the current user."""
    cleaned_title = (title or "").strip() or "新的个人任务"
    thread = WorkspaceThread(owner_user_id=user.id, title=cleaned_title[:100])
    WorkspaceRepository(session).create_thread(thread)
    session.commit()
    session.refresh(thread)
    return _thread_to_read(thread)


def list_workspace_threads(user: User, session: Session) -> dict[str, Any]:
    threads = WorkspaceRepository(session).list_threads(user.id)
    return {"threads": [_thread_to_read(thread) for thread in threads], "total": len(threads)}


def get_workspace_thread(user: User, thread_id: UUID, session: Session) -> dict[str, Any]:
    thread = WorkspaceRepository(session).get_thread(thread_id, user.id)
    if thread is None:
        # Deliberately do not reveal whether another user owns this thread.
        raise WorkspaceThreadNotFoundError()
    return _thread_to_read(thread, include_messages=True)


def _title_from_message(content: str) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    if len(compact) <= 24:
        return compact
    return f"{compact[:24].rstrip()}…"


def chat_with_personal_agent(
    user: User,
    thread_id: UUID | None,
    content: str,
    session: Session,
) -> dict[str, Any]:
    """Persist one user turn, complete it, and persist the Agent reply."""
    from ...config import settings
    from ..memories.encryption import get_encryption_service
    from ..model_gateway.exceptions import ModelUnavailableError
    from ..model_gateway.openai_compatible import OpenAICompatibleProvider
    from ..model_gateway.schemas import (
        ChatMessage,
        ChatRequest,
        DataClassification,
        PrivacyContext,
    )
    from ..model_gateway.service import ModelGatewayService, get_model_gateway_service

    agent_data = get_my_agent(user, session)
    agent_id = UUID(agent_data["id"])
    agent = AgentRepository(session).get_personal_agent(user.id)
    if agent is None:
        raise AgentNotFoundError()
    model_route = _load_model_route(agent)
    repo = WorkspaceRepository(session)
    if thread_id is None:
        thread = WorkspaceThread(owner_user_id=user.id, title="新的个人任务")
        repo.create_thread(thread)
    else:
        existing_thread = repo.get_thread(thread_id, user.id)
        if existing_thread is None:
            raise WorkspaceThreadNotFoundError()
        thread = existing_thread

    encryption = get_encryption_service()
    had_messages = bool(thread.messages)
    user_message = WorkspaceMessage(
        thread=thread,
        role=WorkspaceMessageRole.USER.value,
        content_encrypted=encryption.encrypt(content),
        encryption_key_version=encryption.key_version,
    )
    repo.add_message(user_message)
    thread.updated_at = utc_now()
    if not had_messages and thread.title == "新的个人任务":
        thread.title = _title_from_message(content)
    # Save the student's input even if the upstream model is temporarily unavailable.
    session.commit()

    persisted_thread = repo.get_thread(thread.id, user.id)
    if persisted_thread is None:  # defensive: it was created or resolved above
        raise WorkspaceThreadNotFoundError()
    gateway_messages = [ChatMessage(role="system", content=_WORKSPACE_SYSTEM_PROMPT)]
    gateway_messages.extend(
        ChatMessage(role=message.role, content=encryption.decrypt(message.content_encrypted))
        for message in persisted_thread.messages[-20:]
    )
    request = ChatRequest(
        messages=gateway_messages,
        privacy_context=PrivacyContext(
            data_classification=DataClassification.P2,
            allow_external=True,
            contains_personal_data=True,
            purpose="personal_workspace_chat",
        ),
        purpose="personal_workspace_chat",
        temperature=0.5,
        max_tokens=2048,
    )
    active_profile = (
        _active_model_profile(model_route) if model_route["mode"] == "PERSONAL" else None
    )
    if active_profile:
        personal_provider = OpenAICompatibleProvider(
            base_url=active_profile["base_url"],
            model=active_profile["model"],
            api_key=active_profile["api_key"],
            timeout_ms=settings.MODEL_GATEWAY_TIMEOUT_MS,
            is_external=True,
            name=f"personal-{active_profile['provider'].lower()}",
        )
        gateway = ModelGatewayService(external=personal_provider, allow_fallback=False)
        expected_providers = {personal_provider.name}
    else:
        gateway = get_model_gateway_service()
        expected_providers = {"stepfun"}
    response = gateway.chat(
        request,
        session=session,
        agent_id=agent_id,
        actor_user_id=user.id,
    )

    # The generic gateway can fall back to deterministic local providers.
    # That behavior is useful for internal workflows but would be misleading
    # in a user-facing conversation, so fail explicitly here.
    if response.metadata.provider not in expected_providers:
        raise ModelUnavailableError(details={"reason": "external_provider_unavailable"})

    reply = response.response.content
    if not isinstance(reply, str) or not reply.strip():
        raise ModelUnavailableError(details={"reason": "empty_model_response"})

    assistant_message = WorkspaceMessage(
        thread=persisted_thread,
        role=WorkspaceMessageRole.ASSISTANT.value,
        content_encrypted=encryption.encrypt(reply.strip()),
        encryption_key_version=encryption.key_version,
    )
    repo.add_message(assistant_message)
    persisted_thread.updated_at = utc_now()
    session.commit()
    return {
        "thread_id": str(persisted_thread.id),
        "thread_title": persisted_thread.title,
        "reply": reply.strip(),
        "provider": response.metadata.provider,
        "route_source": "personal" if active_profile else "platform",
        "model": response.model,
        "request_id": response.request_id,
    }
