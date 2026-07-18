"""Routing policy — select a provider that satisfies privacy constraints.

Rules (P7 guide §9, aligned with API_CONTRACT EP-MODEL-058):
1. P4 requests default to local-only (requires_local forced by PrivacyContext).
2. requires_local=True → only mock / rule / local openai_compatible providers.
3. External providers are disabled by default (allow_external=False).
4. Unhealthy providers are skipped.
5. Timeout / failure → degrade to the next provider in priority order.
6. No eligible provider → MODEL_ROUTING_FAILED.
7. Sensitive data routed externally → PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED.

Degradation order (privacy-preserving only):
    configured-local → mock → rule
External is only attempted when allow_external=True AND data is P0/P1/P2.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .exceptions import (
    ModelRoutingFailedError,
    PrivacyContextSensitiveExternalBlockedError,
)
from .providers import ModelProvider
from .schemas import ChatRequest, PrivacyContext, RoutingDecision

logger = logging.getLogger("campus_agent.model_gateway.router")


@dataclass
class ProviderCandidate:
    """A provider plus its routing priority (lower = higher priority)."""

    provider: ModelProvider
    priority: int = 100
    # Whether this candidate represents a local lab node (is_external=False).
    # Cached for routing decisions without re-reading the provider.
    _healthy: bool | None = field(default=None, repr=False)

    @property
    def healthy(self) -> bool:
        if self._healthy is None:
            self._healthy = self.provider.health().healthy
        return self._healthy

    def reset_health_cache(self) -> None:
        self._healthy = None


class RoutingPolicy:
    """Selects an eligible, healthy provider for a given privacy context.

    The policy is stateless aside from the candidate list; health is probed
    on demand and cached per-selection.
    """

    def __init__(self, candidates: list[ProviderCandidate] | None = None) -> None:
        self._candidates: list[ProviderCandidate] = list(candidates or [])

    # ------------------------------------------------------------------
    # Candidate management
    # ------------------------------------------------------------------

    def add_candidate(self, candidate: ProviderCandidate) -> None:
        self._candidates.append(candidate)

    def set_candidates(self, candidates: list[ProviderCandidate]) -> None:
        self._candidates = list(candidates)

    @property
    def candidates(self) -> list[ProviderCandidate]:
        return list(self._candidates)

    # ------------------------------------------------------------------
    # Privacy gate
    # ------------------------------------------------------------------

    @staticmethod
    def _privacy_allows(
        provider: ModelProvider,
        ctx: PrivacyContext,
    ) -> bool:
        """Return True if the provider satisfies the privacy context."""
        # External providers are blocked when context forbids external;
        # requires_local also blocks external providers.
        return not (
            provider.is_external
            and (ctx.is_external_blocked or ctx.requires_local)
        )

    @staticmethod
    def _would_block_sensitive_external(
        provider: ModelProvider,
        ctx: PrivacyContext,
    ) -> bool:
        """True if selecting this provider would violate sensitive-external."""
        return provider.is_external and ctx.is_external_blocked

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select(
        self,
        request: ChatRequest,
    ) -> tuple[ModelProvider, RoutingDecision]:
        """Select the best eligible, healthy provider.

        Returns:
            (provider, routing_decision)

        Raises:
            PrivacyContextSensitiveExternalBlockedError: when the only
                available providers are external but data is sensitive.
            ModelRoutingFailedError: when no provider is eligible/healthy.
        """
        ctx = request.privacy_context

        # Partition candidates by privacy eligibility.
        eligible: list[ProviderCandidate] = []
        blocked_external = False
        for cand in sorted(self._candidates, key=lambda c: c.priority):
            if self._privacy_allows(cand.provider, ctx):
                eligible.append(cand)
            elif self._would_block_sensitive_external(cand.provider, ctx):
                blocked_external = True

        if not eligible:
            if blocked_external:
                raise PrivacyContextSensitiveExternalBlockedError(
                    details={"data_classification": ctx.data_classification.value}
                )
            raise ModelRoutingFailedError(
                details={"reason": "no_eligible_provider"}
            )

        # Among eligible candidates, pick the first healthy one (priority order).
        for cand in eligible:
            if cand.healthy:
                decision = RoutingDecision(
                    provider_type=cand.provider.provider_type.value,
                    provider_name=cand.provider.name,
                    reason="selected",
                    privacy_blocked_external=blocked_external,
                )
                logger.debug(
                    "router.selected",
                    extra={
                        "provider_type": decision.provider_type,
                        "provider_name": decision.provider_name,
                    },
                )
                return cand.provider, decision

        # All eligible providers are unhealthy. If mock/rule exist, they are
        # always healthy (pure compute), so reaching here means only external
        # or local-node providers were eligible and all are down.
        # As a last resort, prefer mock/rule if they were eligible but
        # somehow reported unhealthy — but mock/rule are always healthy.
        raise ModelRoutingFailedError(
            details={"reason": "all_eligible_unhealthy"}
        )

    def select_for_fallback(
        self,
        request: ChatRequest,
        exclude: set[str] | None = None,
    ) -> ModelProvider | None:
        """Select a fallback provider (mock or rule) excluding failed ones.

        Used by the service layer when the primary provider times out or
        errors. Only privacy-safe local providers are considered — never
        degrades to external.
        """
        ctx = request.privacy_context
        exclude = exclude or set()
        for cand in sorted(self._candidates, key=lambda c: c.priority):
            if cand.provider.name in exclude:
                continue
            # Fallback is restricted to local providers only.
            if cand.provider.is_external:
                continue
            if not self._privacy_allows(cand.provider, ctx):
                continue
            if cand.provider.health().healthy:
                return cand.provider
        return None


def build_default_candidates(
    mock: ModelProvider,
    rule: ModelProvider,
    *,
    local_node: ModelProvider | None = None,
    external: ModelProvider | None = None,
) -> list[ProviderCandidate]:
    """Build the standard candidate list with sensible priorities.

    Priority order (lower = tried first):
      1. local node (if configured) — priority 10
      2. external (if configured and allowed) — priority 50
      3. rule — priority 80
      4. mock — priority 90

    Mock and rule are always last-resort to preserve real-model usage when
    available, while still guaranteeing a privacy-safe fallback.
    """
    candidates: list[ProviderCandidate] = []
    if local_node is not None:
        candidates.append(ProviderCandidate(provider=local_node, priority=10))
    if external is not None:
        candidates.append(ProviderCandidate(provider=external, priority=50))
    candidates.append(ProviderCandidate(provider=rule, priority=80))
    candidates.append(ProviderCandidate(provider=mock, priority=90))
    return candidates
