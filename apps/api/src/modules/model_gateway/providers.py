"""Provider protocol and provider-type taxonomy.

All model providers — Mock, Rule, and OpenAI-compatible — implement the
``ModelProvider`` Protocol. Business modules must never import a concrete
provider SDK directly; they call through ``ModelGatewayService``.

Privacy:
- Providers never log prompt/response content.
- ``is_external`` is the routing gate: external providers are disabled by
  default and rejected for P3/P4 data.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from .schemas import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderHealth,
)


class ProviderType(StrEnum):
    """Provider taxonomy used by routing and metrics."""

    MOCK = "mock"
    RULE = "rule"
    OPENAI_COMPATIBLE = "openai_compatible"

    @property
    def is_local(self) -> bool:
        """Local providers never leave the process/cluster."""
        return self in (ProviderType.MOCK, ProviderType.RULE)


class ProviderCapability(StrEnum):
    """Optional capabilities a provider may advertise."""

    CHAT = "chat"
    EMBEDDING = "embedding"
    STRUCTURED_OUTPUT = "structured_output"


@runtime_checkable
class ModelProvider(Protocol):
    """Unified contract for all model providers.

    Implementations must be safe to call with sensitive privacy_context:
    they must not log, persist, or exfiltrate prompt/response content.
    """

    name: str
    provider_type: ProviderType
    is_external: bool

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Perform a chat completion."""
        ...

    def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate an embedding vector."""
        ...

    def health(self) -> ProviderHealth:
        """Return a current health snapshot."""
        ...


def is_provider_allowed_by_privacy(
    provider: ModelProvider,
    *,
    allow_external: bool,
    requires_local: bool,
) -> bool:
    """Routing gate: decide whether a provider satisfies privacy constraints.

    Rules (aligned with P7 guide §9):
    - ``requires_local=True`` → only mock/rule/openai_compatible-local allowed.
    - ``allow_external=False`` → external providers rejected.
    - External providers require ``allow_external=True``.
    """
    return not (provider.is_external and (not allow_external or requires_local))
