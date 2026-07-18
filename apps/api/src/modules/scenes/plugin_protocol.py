"""Scene Plugin Protocol — the contract every scene plugin must implement.

Privacy principles (P8 guide §4):
- Plugins receive a ``SceneServiceFacade`` to call Memory/Model/Conversation
  services. They CANNOT import repositories directly.
- Plugins never see raw P4 data from other users — only their own caller's
  raw submission and the de-identified capsules of others.
- The protocol is ``runtime_checkable`` so the registry can verify plugin
  conformance at registration time.

The protocol methods map to the scene lifecycle:

    validate_private_submission → build_private_capsule →
    generate_candidates → evaluate_candidate_privately →
    aggregate_results → build_public_result → cleanup_private_data
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from .schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
    PrivateCapsule,
)

# ---------------------------------------------------------------------------
# SceneServiceFacade — the only interface plugins may use to reach
# Memory, Model Gateway, and Conversation services.
# ---------------------------------------------------------------------------


class SceneServiceFacade(Protocol):
    """Limited service surface that plugins may call.

    Plugins MUST NOT import repositories, model providers, or other
    module internals directly. All cross-module access goes through
    this facade, which enforces privacy and authorisation boundaries.
    """

    def model_chat(
        self,
        *,
        messages: list[dict[str, str]],
        purpose: str,
        data_classification: str = "P2",
        response_schema: dict[str, Any] | None = None,
        preference_capsule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the model gateway for chat completion.

        Returns the response content dict (never raw prompt/response
        in logs).
        """
        ...

    def model_embedding(
        self,
        *,
        text: str,
        purpose: str,
        data_classification: str = "P2",
    ) -> list[float]:
        """Call the model gateway for embedding. Returns the vector."""
        ...

    def write_scene_message(
        self,
        *,
        conversation_id: UUID,
        content: str,
        message_type: str = "scene_notification",
    ) -> None:
        """Write a public scene notification to the conversation.

        Content must NOT contain private preferences or individual scores.
        """
        ...

    def log_audit(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_type: str = "scene",
        resource_id: str | None = None,
        result: str = "SUCCESS",
    ) -> None:
        """Write an audit log entry (no private content)."""
        ...


# ---------------------------------------------------------------------------
# ScenePlugin Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ScenePlugin(Protocol):
    """The contract every scene plugin implements.

    All methods are pure functions of their inputs — they do not hold
    mutable state and do not access the database directly. State is
    managed by the SceneService and passed in as arguments.
    """

    # Metadata properties (set as class attributes or instance attributes)
    scene_key: str
    version: str
    name: str
    description: str

    def validate_private_submission(
        self,
        raw_preferences: dict[str, Any],
    ) -> None:
        """Validate the user's raw preference submission.

        Raises:
            SceneSubmissionError: if the submission is invalid.
        """
        ...

    def build_private_capsule(
        self,
        raw_preferences: dict[str, Any],
    ) -> PrivateCapsule:
        """Build a de-identified capsule from raw preferences.

        The capsule contains only hard constraints, soft preferences,
        and weights — never raw free-text or identifiable data.
        """
        ...

    def generate_candidates(
        self,
        capsules: list[PrivateCapsule],
        public_context: dict[str, Any] | None,
        facade: SceneServiceFacade,
    ) -> list[CandidateInput]:
        """Generate public candidates from all participants' capsules.

        This is where the plugin calls the model gateway (via facade)
        to produce candidate options. Only public candidate data is
        returned.
        """
        ...

    def evaluate_candidate_privately(
        self,
        candidate: CandidateInput,
        capsule: PrivateCapsule,
    ) -> EvaluationResult:
        """Privately evaluate a candidate against one user's capsule.

        The result is never exposed publicly — it feeds into
        ``aggregate_results``.
        """
        ...

    def aggregate_results(
        self,
        candidate: CandidateInput,
        evaluations: list[EvaluationResult],
    ) -> AggregateResult:
        """Aggregate private evaluations into a public-safe result.

        Only aggregate scores and public reasons are returned — never
        individual scores.
        """
        ...

    def build_public_result(
        self,
        aggregates: list[AggregateResult],
        public_context: dict[str, Any] | None,
        facade: SceneServiceFacade,
    ) -> dict[str, Any]:
        """Build the final public result from aggregated candidates.

        Returns a dict with:
        - selected_candidate_key: str
        - public_summary: str
        - ranked_candidates: list[dict]
        """
        ...

    def cleanup_private_data(
        self,
        scene_instance_id: UUID,
        facade: SceneServiceFacade,
    ) -> None:
        """Plugin-specific cleanup hook.

        Called after the standard cleanup has purged encrypted payloads.
        Plugins should clean up any plugin-specific derived data.
        """
        ...
