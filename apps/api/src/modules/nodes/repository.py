"""Repository for ModelNode and ModelDeployment data access."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.time import utc_now
from .models import ModelDeployment, ModelNode, NodeStatus


class NodeRepository:
    """Data access for ModelNode records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, node: ModelNode) -> ModelNode:
        self._session.add(node)
        self._session.flush()
        return node

    def get_by_id(self, node_id: UUID) -> ModelNode | None:
        return self._session.get(ModelNode, node_id)

    def get_by_name(self, name: str) -> ModelNode | None:
        stmt = select(ModelNode).where(
            ModelNode.name == name,
            ModelNode.deleted_at.is_(None),
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_all(
        self,
        *,
        status: str | None = None,
        capability: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ModelNode], int]:
        stmt = select(ModelNode).where(ModelNode.deleted_at.is_(None))
        if status:
            stmt = stmt.where(ModelNode.status == status)
        # capability filtering requires JSON inspection; we filter in Python
        # for simplicity (small admin dataset).
        count_stmt = select(ModelNode).where(ModelNode.deleted_at.is_(None))
        if status:
            count_stmt = count_stmt.where(ModelNode.status == status)
        all_nodes = list(self._session.execute(stmt).scalars().all())
        if capability:
            import json

            filtered = []
            for n in all_nodes:
                caps = json.loads(n.capabilities_json) if n.capabilities_json else []
                if capability in caps:
                    filtered.append(n)
            all_nodes = filtered
        total = len(all_nodes)
        page = all_nodes[offset : offset + limit]
        return page, total

    def save(self, node: ModelNode) -> ModelNode:
        self._session.flush()
        return node

    def soft_delete(self, node: ModelNode) -> None:
        node.deleted_at = utc_now()
        node.status = NodeStatus.DELETED.value

    def update_health(
        self,
        node: ModelNode,
        *,
        health_status: str,
        last_heartbeat: datetime | None = None,
    ) -> None:
        node.health_status = health_status
        if last_heartbeat is not None:
            node.last_heartbeat_at = last_heartbeat
        self._session.flush()


class DeploymentRepository:
    """Data access for ModelDeployment records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, deployment: ModelDeployment) -> ModelDeployment:
        self._session.add(deployment)
        self._session.flush()
        return deployment

    def get_by_id(self, deployment_id: UUID) -> ModelDeployment | None:
        return self._session.get(ModelDeployment, deployment_id)

    def list_all(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ModelDeployment], int]:
        stmt = select(ModelDeployment)
        if status:
            stmt = stmt.where(ModelDeployment.status == status)
        all_deployments = list(self._session.execute(stmt).scalars().all())
        total = len(all_deployments)
        page = all_deployments[offset : offset + limit]
        return page, total

    def save(self, deployment: ModelDeployment) -> ModelDeployment:
        self._session.flush()
        return deployment
