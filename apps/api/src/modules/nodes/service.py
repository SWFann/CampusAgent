"""Node and Deployment service — admin business logic.

Privacy:
- Endpoint and credential are encrypted before storage.
- List responses redact endpoint entirely.
- Detail responses include only the host (no userinfo/query/token).
- repr and logs never include endpoint/credential plaintext.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ..audit.service import log_audit
from ..memories.encryption import get_encryption_service
from ..model_gateway.models import ModelDefinition
from ..users.models import GlobalRole, User
from .exceptions import (
    AdminPermissionDeniedError,
    ModelNotFoundError,
    NodeInUseError,
    NodeNotFoundError,
)
from .health import NodeHealthChecker, get_node_health_checker
from .models import (
    ModelDeployment,
    ModelNode,
    NodeHealthStatus,
    NodeStatus,
)
from .repository import DeploymentRepository, NodeRepository
from .schemas import (
    DeploymentCreate,
    ModelDefinitionCreate,
    NodeCreate,
    NodeUpdate,
)

# ---------------------------------------------------------------------------
# RBAC helpers
# ---------------------------------------------------------------------------


def _require_system_admin(user: User) -> None:
    if user.global_role != GlobalRole.SYSTEM_ADMIN.value:
        raise AdminPermissionDeniedError()


def _require_admin(user: User) -> None:
    """Require SCHOOL_ADMIN or SYSTEM_ADMIN."""
    if user.global_role not in (
        GlobalRole.SYSTEM_ADMIN.value,
        GlobalRole.SCHOOL_ADMIN.value,
    ):
        raise AdminPermissionDeniedError()


# ---------------------------------------------------------------------------
# Endpoint safety
# ---------------------------------------------------------------------------


def _safe_endpoint_host(endpoint: str) -> str:
    """Return only the host:port (no userinfo, query, or fragment)."""
    parsed = urlparse(endpoint)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    scheme = parsed.scheme or "https"
    return f"{scheme}://{host}{port}"


def _validate_endpoint(endpoint: str) -> None:
    """Basic endpoint validation (R1-28 rules, simplified for MVP).

    - Must have a scheme (http/https).
    - Must not contain userinfo.
    - Must not contain query or fragment.
    """
    from ...utils.errors import AppError

    parsed = urlparse(endpoint)
    if parsed.scheme not in ("http", "https"):
        raise AppError(
            code="INVALID_ENDPOINT",
            message="端点格式无效：协议必须为 http 或 https",
            status_code=400,
        )
    if parsed.username or parsed.password:
        raise AppError(
            code="INVALID_ENDPOINT",
            message="端点格式无效：不得包含用户名密码",
            status_code=400,
        )
    if parsed.query or parsed.fragment:
        raise AppError(
            code="INVALID_ENDPOINT",
            message="端点格式无效：不得包含 query 或 fragment",
            status_code=400,
        )
    if not parsed.hostname:
        raise AppError(
            code="INVALID_ENDPOINT",
            message="端点格式无效：缺少主机名",
            status_code=400,
        )


# ---------------------------------------------------------------------------
# Node service
# ---------------------------------------------------------------------------


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _node_to_read(node: ModelNode, *, include_endpoint: bool = False) -> dict[str, Any]:
    """Convert ModelNode to a safe read dict.

    ``include_endpoint`` is True only for detail view, and even then only
    the host:port is included (never userinfo/query/token).
    """
    result: dict[str, Any] = {
        "node_id": str(node.id),
        "name": node.name,
        "status": node.status,
        "health_status": node.health_status,
        "exposure_type": node.exposure_type,
        "namespace": node.namespace,
        "capabilities": _json_loads(node.capabilities_json),
        "models_supported": _json_loads(node.models_supported_json),
        "max_concurrent_requests": node.max_concurrent_requests,
        "current_requests": node.current_requests,
        "uptime_seconds": node.uptime_seconds,
        "last_heartbeat": node.last_heartbeat_at.isoformat() if node.last_heartbeat_at else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
        "metadata": _json_loads(node.metadata_json),
    }
    if include_endpoint:
        # Decrypt to extract host only, then discard plaintext.
        enc = get_encryption_service()
        try:
            plaintext = enc.decrypt(node.endpoint_encrypted)
            result["endpoint"] = _safe_endpoint_host(plaintext)
        except Exception:
            result["endpoint"] = None
    return result


def _node_to_list_read(node: ModelNode) -> dict[str, Any]:
    """Convert ModelNode to a list-item dict (endpoint fully redacted)."""
    return {
        "node_id": str(node.id),
        "name": node.name,
        "status": node.status,
        "health_status": node.health_status,
        "capabilities": _json_loads(node.capabilities_json),
        "last_heartbeat": node.last_heartbeat_at.isoformat() if node.last_heartbeat_at else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }


def create_node(
    actor: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Register a new edge node. SYSTEM_ADMIN only."""
    _require_system_admin(actor)
    parsed = NodeCreate(**data)
    _validate_endpoint(parsed.endpoint)

    enc = get_encryption_service()
    node = ModelNode(
        name=parsed.name,
        endpoint_encrypted=enc.encrypt(parsed.endpoint),
        credential_encrypted=enc.encrypt(parsed.credential) if parsed.credential else None,
        namespace=parsed.namespace,
        exposure_type=parsed.exposure_type,
        status=NodeStatus.REGISTERING.value,
        health_status=NodeHealthStatus.ONLINE.value,
        capabilities_json=_json_dumps(parsed.capabilities),
        models_supported_json=_json_dumps(parsed.models_supported),
        max_concurrent_requests=parsed.max_concurrent_requests,
        metadata_json=_json_dumps(parsed.metadata),
    )
    repo = NodeRepository(session)
    existing = repo.get_by_name(parsed.name)
    if existing is not None:
        from ...utils.errors import AppError
        raise AppError(code="NODE_ALREADY_EXISTS", message="节点已存在", status_code=409)
    repo.create(node)
    session.commit()
    session.refresh(node)

    log_audit(
        actor_id=actor.id,
        action="admin_node_create",
        resource_type="node",
        resource_id=str(node.id),
        result="SUCCESS",
        session=session,
    )
    return _node_to_read(node, include_endpoint=False)


def list_nodes(
    actor: User,
    session: Session,
    *,
    status: str | None = None,
    capability: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List all nodes. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    _require_admin(actor)
    if page < 1 or limit < 1 or limit > 100:
        from ...utils.errors import AppError
        raise AppError(code="INVALID_PAGINATION", message="分页参数无效", status_code=400)
    repo = NodeRepository(session)
    nodes, total = repo.list_all(
        status=status, capability=capability, limit=limit, offset=(page - 1) * limit
    )
    return {
        "nodes": [_node_to_list_read(n) for n in nodes],
        "pagination": {"total": total, "page": page, "limit": limit},
    }


def get_node(actor: User, node_id: UUID, session: Session) -> dict[str, Any]:
    """Get a single node detail. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    _require_admin(actor)
    repo = NodeRepository(session)
    node = repo.get_by_id(node_id)
    if node is None or node.deleted_at is not None:
        raise NodeNotFoundError()
    return _node_to_read(node, include_endpoint=True)


def update_node(
    actor: User,
    node_id: UUID,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Update node config. SYSTEM_ADMIN only."""
    _require_system_admin(actor)
    parsed = NodeUpdate(**data)
    repo = NodeRepository(session)
    node = repo.get_by_id(node_id)
    if node is None or node.deleted_at is not None:
        raise NodeNotFoundError()
    if parsed.status is not None:
        node.status = parsed.status
    if parsed.max_concurrent_requests is not None:
        node.max_concurrent_requests = parsed.max_concurrent_requests
    if parsed.metadata is not None:
        node.metadata_json = _json_dumps(parsed.metadata)
    repo.save(node)
    session.commit()
    session.refresh(node)

    log_audit(
        actor_id=actor.id,
        action="admin_node_update",
        resource_type="node",
        resource_id=str(node.id),
        result="SUCCESS",
        session=session,
    )
    return _node_to_read(node, include_endpoint=False)


def delete_node(
    actor: User,
    node_id: UUID,
    session: Session,
) -> None:
    """Soft-delete a node. SYSTEM_ADMIN only."""
    _require_system_admin(actor)
    repo = NodeRepository(session)
    node = repo.get_by_id(node_id)
    if node is None or node.deleted_at is not None:
        raise NodeNotFoundError()
    if node.current_requests > 0:
        raise NodeInUseError()
    repo.soft_delete(node)
    session.commit()

    log_audit(
        actor_id=actor.id,
        action="admin_node_delete",
        resource_type="node",
        resource_id=str(node.id),
        result="SUCCESS",
        session=session,
    )


def trigger_health_check(
    actor: User,
    node_id: UUID,
    session: Session,
    *,
    checker: NodeHealthChecker | None = None,
) -> dict[str, Any]:
    """Manually trigger a node health check. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    _require_admin(actor)
    repo = NodeRepository(session)
    node = repo.get_by_id(node_id)
    if node is None or node.deleted_at is not None:
        raise NodeNotFoundError()

    checker = checker or get_node_health_checker()
    enc = get_encryption_service()
    try:
        endpoint = enc.decrypt(node.endpoint_encrypted)
    except Exception:
        endpoint = ""

    result = checker.check(node, decrypted_endpoint=endpoint)
    # Persist health status + heartbeat.
    repo.update_health(
        node,
        health_status=result["status"],
        last_heartbeat=utc_now(),
    )
    # Map health_status to admin status if appropriate.
    if result["status"] == NodeHealthStatus.ONLINE.value:
        node.status = NodeStatus.HEALTHY.value
    elif result["status"] == NodeHealthStatus.DEGRADED.value:
        node.status = NodeStatus.DEGRADED.value
    elif result["status"] == NodeHealthStatus.OFFLINE.value:
        node.status = NodeStatus.OFFLINE.value
    repo.save(node)
    session.commit()

    return {
        "node_id": str(node.id),
        "status": result["status"],
        "checks": result["checks"],
        "latency_ms": result["latency_ms"],
        "checked_at": result["checked_at"],
    }


def get_node_metrics(
    actor: User,
    node_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Return simulated node resource metrics (P7-11).

    SCHOOL_ADMIN or SYSTEM_ADMIN. Returns simulated cpu/gpu values — no
    sensitive labels (no user id, no prompt, no endpoint with token).
    """
    _require_admin(actor)
    repo = NodeRepository(session)
    node = repo.get_by_id(node_id)
    if node is None or node.deleted_at is not None:
        raise NodeNotFoundError()
    # Simulated metrics — deterministic from node id hash for stability.
    import hashlib
    digest = hashlib.sha256(str(node.id).encode()).hexdigest()
    cpu = int(digest[:2], 16) % 100
    memory = int(digest[2:4], 16) % 100
    gpu = int(digest[4:6], 16) % 100
    return {
        "node_id": str(node.id),
        "interval": "5m",
        "metrics": [
            {
                "timestamp": utc_now().isoformat(),
                "cpu_usage": float(cpu),
                "memory_usage": float(memory),
                "gpu_usage": float(gpu),
                "active_requests": node.current_requests,
                "request_latency_p50": 250.0,
                "request_latency_p95": 850.0,
                "error_rate": 0.0,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Model definition service
# ---------------------------------------------------------------------------


def _model_to_read(model: ModelDefinition) -> dict[str, Any]:
    return {
        "model_id": str(model.id),
        "name": model.name,
        "version": model.version,
        "provider": model.provider,
        "model_type": model.model_type,
        "enabled": model.enabled,
        "capabilities": _json_loads(model.capabilities_json),
        "max_tokens": model.max_tokens,
        "default_temperature": model.default_temperature,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "metadata": _json_loads(model.metadata_json),
    }


def create_model(
    actor: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Register a new model definition. SYSTEM_ADMIN only."""
    _require_system_admin(actor)
    parsed = ModelDefinitionCreate(**data)
    model = ModelDefinition(
        name=parsed.name,
        version=parsed.version,
        provider=parsed.provider,
        model_type=parsed.model_type,
        capabilities_json=_json_dumps(parsed.capabilities),
        max_tokens=parsed.max_tokens,
        default_temperature=parsed.default_temperature,
        enabled=parsed.enabled,
        metadata_json=_json_dumps(parsed.metadata),
    )
    session.add(model)
    session.commit()
    session.refresh(model)

    log_audit(
        actor_id=actor.id,
        action="admin_model_create",
        resource_type="model",
        resource_id=str(model.id),
        result="SUCCESS",
        session=session,
    )
    return _model_to_read(model)


def list_models(
    actor: User,
    session: Session,
    *,
    provider: str | None = None,
    enabled: bool | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List model definitions. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    _require_admin(actor)
    if page < 1 or limit < 1 or limit > 100:
        from ...utils.errors import AppError
        raise AppError(code="INVALID_PAGINATION", message="分页参数无效", status_code=400)
    from sqlalchemy import select
    stmt = select(ModelDefinition)
    if provider:
        stmt = stmt.where(ModelDefinition.provider == provider)
    if enabled is not None:
        stmt = stmt.where(ModelDefinition.enabled == enabled)
    all_models = list(session.execute(stmt).scalars().all())
    total = len(all_models)
    page_models = all_models[(page - 1) * limit : (page - 1) * limit + limit]
    return {
        "models": [_model_to_read(m) for m in page_models],
        "pagination": {"total": total, "page": page, "limit": limit},
    }


# ---------------------------------------------------------------------------
# Deployment service
# ---------------------------------------------------------------------------


def _deployment_to_read(dep: ModelDeployment) -> dict[str, Any]:
    return {
        "deployment_id": str(dep.id),
        "model_id": str(dep.model_id),
        "node_id": str(dep.node_id),
        "version": dep.version,
        "status": dep.status,
        "priority": dep.priority,
        "capabilities": _json_loads(dep.capabilities_json),
        "deployed_at": dep.deployed_at.isoformat() if dep.deployed_at else None,
        "created_at": dep.created_at.isoformat() if dep.created_at else None,
    }


def create_deployment(
    actor: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Create a deployment record. SYSTEM_ADMIN only."""
    _require_system_admin(actor)
    parsed = DeploymentCreate(**data)

    # Validate model and node exist.
    model = session.get(ModelDefinition, parsed.model_id)
    if model is None:
        raise ModelNotFoundError()
    node_repo = NodeRepository(session)
    node = node_repo.get_by_id(parsed.node_id)
    if node is None or node.deleted_at is not None:
        raise NodeNotFoundError()

    dep = ModelDeployment(
        model_id=parsed.model_id,
        node_id=parsed.node_id,
        version=parsed.version,
        status=parsed.status,
        priority=parsed.priority,
        capabilities_json=_json_dumps(parsed.capabilities),
        metadata_json=_json_dumps(parsed.metadata),
    )
    dep_repo = DeploymentRepository(session)
    dep_repo.create(dep)
    session.commit()
    session.refresh(dep)

    log_audit(
        actor_id=actor.id,
        action="admin_deployment_create",
        resource_type="deployment",
        resource_id=str(dep.id),
        result="SUCCESS",
        session=session,
    )
    return _deployment_to_read(dep)


def list_deployments(
    actor: User,
    session: Session,
    *,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """List deployments. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    _require_admin(actor)
    if page < 1 or limit < 1 or limit > 100:
        from ...utils.errors import AppError
        raise AppError(code="INVALID_PAGINATION", message="分页参数无效", status_code=400)
    dep_repo = DeploymentRepository(session)
    deps, total = dep_repo.list_all(
        status=status, limit=limit, offset=(page - 1) * limit
    )
    return {
        "deployments": [_deployment_to_read(d) for d in deps],
        "pagination": {"total": total, "page": page, "limit": limit},
    }

