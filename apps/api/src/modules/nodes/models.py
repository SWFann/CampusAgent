"""Node and Deployment ORM models.

Privacy (P7 guide §12):
- ``endpoint_encrypted`` and ``credential_encrypted`` are Fernet ciphertexts.
- ``repr`` never exposes endpoint/credential plaintext.
- ``exposure_type`` records how the node is reached (INGRESS/NODEPORT/LOCAL/MOCK).
- ``health_status`` tracks ONLINE/DEGRADED/OFFLINE.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid


class ExposureType(StrEnum):
    """How a node is exposed on the network."""

    INGRESS = "INGRESS"
    NODEPORT = "NODEPORT"
    LOCAL = "LOCAL"
    MOCK = "MOCK"


class NodeHealthStatus(StrEnum):
    """Health status for a model node."""

    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class NodeStatus(StrEnum):
    """Lifecycle status for a model node (admin-managed)."""

    REGISTERING = "registering"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    DELETED = "deleted"


class DeploymentStatus(StrEnum):
    """Status for a model deployment."""

    DEPLOYED = "deployed"
    PENDING = "pending"
    FAILED = "failed"
    RETIRED = "retired"


class ModelNode(Base):
    """Edge inference node.

    ``endpoint_encrypted`` and ``credential_encrypted`` hold Fernet
    ciphertext; plaintext is only decrypted in-memory for outbound calls
    and never appears in repr, logs, or API responses.
    """

    __tablename__ = "model_nodes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    endpoint_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    credential_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exposure_type: Mapped[str] = mapped_column(String(20), nullable=False)
    health_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NodeHealthStatus.ONLINE.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NodeStatus.REGISTERING.value
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(nullable=True)
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    models_supported_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_concurrent_requests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    deployments: Mapped[list[ModelDeployment]] = relationship(
        "ModelDeployment", back_populates="node", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        # endpoint/credential intentionally absent.
        return (
            f"<ModelNode id={self.id} name={self.name} "
            f"exposure={self.exposure_type} health={self.health_status}>"
        )


class ModelDeployment(Base):
    """Deployment record linking a model definition to a node.

    Records the deployment history and current status of a model on a
    specific node. ``priority`` controls routing order (lower = higher).
    """

    __tablename__ = "model_deployments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    model_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("model_definitions.id"), nullable=False, index=True
    )
    node_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("model_nodes.id"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeploymentStatus.DEPLOYED.value
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    node: Mapped[ModelNode] = relationship("ModelNode", back_populates="deployments")

    def __repr__(self) -> str:
        return (
            f"<ModelDeployment id={self.id} model_id={self.model_id} "
            f"node_id={self.node_id} status={self.status} priority={self.priority}>"
        )
