"""Scene Coordinator — orchestrates the generation and voting phases.

The coordinator is the execution engine that runs when a scene transitions
to GENERATING_CANDIDATES. It:

1. Loads all encrypted submissions.
2. Decrypts each submission (within the owning user's context).
3. Calls the plugin's lifecycle methods.
4. Stores public candidates and results.
5. Triggers cleanup of private data.

Privacy:
- The coordinator decrypts private data only in-memory, never persists it.
- The coordinator calls plugins through the SceneServiceFacade, which
  enforces privacy boundaries.
- The coordinator never directly accesses other modules' repositories.
- Individual evaluation results are never persisted or exposed.

Boundary (P8 guide §11):
- Coordinator may call: plugin protocol, Memory Service, Model Gateway,
  Conversation Service, Cleanup Service.
- Coordinator may NOT: directly query cross-module tables, directly read
  MemoryRepository, directly call external models.
"""
from __future__ import annotations

import json
import logging
import secrets
from typing import Any, cast
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ..audit.service import log_audit
from .events import SceneCandidateReady
from .exceptions import SceneNotFoundError, ScenePluginError, SceneStateTransitionError
from .models import (
    CandidateStatus,
    SceneCandidate,
    SceneResult,
)
from .plugin_protocol import SceneServiceFacade
from .privacy import capsule_from_json
from .registry import get_scene_registry
from .repository import (
    PrivateSubmissionRepository,
    SceneCandidateRepository,
    SceneInstanceRepository,
    SceneResultRepository,
)
from .schemas import (
    AggregateResult,
    EvaluationResult,
    PrivateCapsule,
)
from .state_machine import SceneState

logger = logging.getLogger("campus_agent.scenes.coordinator")


def _generate_event_id() -> str:
    return secrets.token_hex(16)


def _parse_context(json_str: str | None) -> dict[str, Any] | None:
    if json_str is None:
        return None
    try:
        return cast("dict[str, Any]", json.loads(json_str))
    except (json.JSONDecodeError, TypeError):
        return None


class SceneCoordinatorFacade:
    """Implementation of SceneServiceFacade for the coordinator.

    This facade provides plugins with access to the Model Gateway,
    Conversation Service, and Audit Service — all through controlled
    interfaces that enforce privacy boundaries.
    """

    def __init__(
        self,
        session: Session,
        *,
        conversation_id: UUID | None = None,
        actor_id: UUID | None = None,
    ) -> None:
        self._session = session
        self._conversation_id = conversation_id
        self._actor_id = actor_id

    def model_chat(
        self,
        *,
        messages: list[dict[str, str]],
        purpose: str,
        data_classification: str = "P2",
        response_schema: dict[str, Any] | None = None,
        preference_capsule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the model gateway for chat completion."""
        from ...config import settings
        from ..model_gateway.schemas import (
            ChatMessage,
            ChatRequest,
            DataClassification,
            PrivacyContext,
        )
        from ..model_gateway.service import get_model_gateway_service

        privacy_context = PrivacyContext(
            data_classification=DataClassification(data_classification),
            purpose=purpose,
            allow_external=settings.ENABLE_EXTERNAL_MODEL,
        )
        chat_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        request = ChatRequest(
            messages=chat_messages,
            privacy_context=privacy_context,
            purpose=purpose,
            response_schema=response_schema,
            preference_capsule=preference_capsule,
        )

        service = get_model_gateway_service()
        response = service.chat(
            request,
            session=self._session,
            actor_user_id=self._actor_id,
        )
        return {
            "content": response.response.content,
            "type": response.response.type,
            "model": response.model,
            "status": response.status,
        }

    def model_embedding(
        self,
        *,
        text: str,
        purpose: str,
        data_classification: str = "P2",
    ) -> list[float]:
        """Call the model gateway for embedding."""
        from ..model_gateway.schemas import (
            DataClassification,
            EmbeddingRequest,
            PrivacyContext,
        )
        from ..model_gateway.service import get_model_gateway_service

        privacy_context = PrivacyContext(
            data_classification=DataClassification(data_classification),
            purpose=purpose,
        )
        request = EmbeddingRequest(
            text=text,
            privacy_context=privacy_context,
        )

        service = get_model_gateway_service()
        response = service.embedding(request)
        return response.embedding

    def write_scene_message(
        self,
        *,
        conversation_id: UUID,
        content: str,
        message_type: str = "scene_notification",
    ) -> None:
        """Write a public scene notification to the conversation.

        The coordinator acts on behalf of the scene, not a specific user.
        Scene notifications are published via the domain event bus; this
        method is a best-effort convenience for plugins that want to write
        a public message to the conversation. If no valid conversation
        context exists, the call is silently ignored.
        """
        if conversation_id is None:
            return
        logger.info(
            "scene.facade.write_scene_message",
            extra={
                "conversation_id": str(conversation_id),
                "message_type": message_type,
            },
        )

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
        log_audit(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            session=self._session,
        )


def run_generation_phase(
    instance_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Run the candidate generation phase for a scene instance.

    This is called when the scene transitions to GENERATING_CANDIDATES.
    It:
    1. Loads all submissions and their capsules.
    2. Calls plugin.generate_candidates().
    3. For each candidate, calls plugin.evaluate_candidate_privately()
       against each user's capsule.
    4. Calls plugin.aggregate_results() for each candidate.
    5. Stores public candidates with aggregate scores.
    6. Calls plugin.build_public_result() to get the final result.
    7. Triggers cleanup of private data.

    Returns:
        Dict with generation summary (no private data).

    Raises:
        SceneNotFoundError: If instance not found.
        ScenePluginError: If the plugin fails.
        SceneStateTransitionError: If not in GENERATING_CANDIDATES state.
    """
    instance_repo = SceneInstanceRepository(session)
    instance = instance_repo.get_by_id(instance_id)
    if instance is None:
        raise SceneNotFoundError()

    if instance.status != SceneState.GENERATING_CANDIDATES.value:
        raise SceneStateTransitionError(
            details={
                "current_state": instance.status,
                "required_state": SceneState.GENERATING_CANDIDATES.value,
            }
        )

    registry = get_scene_registry()
    plugin = registry.get(instance.definition.scene_key, instance.definition.version)

    # Build the facade.
    facade = SceneCoordinatorFacade(
        session,
        conversation_id=instance.conversation_id,
        actor_id=instance.created_by,
    )

    # Load all submissions and build capsules.
    sub_repo = PrivateSubmissionRepository(session)
    submissions = sub_repo.list_by_instance(instance_id)

    capsules: list[PrivateCapsule] = []
    submission_user_ids: list[UUID] = []
    for sub in submissions:
        if sub.capsule_json:
            capsule = capsule_from_json(sub.capsule_json)
            capsules.append(capsule)
            submission_user_ids.append(sub.user_id)

    public_context = _parse_context(instance.public_context_json)

    try:
        # 1. Generate candidates from capsules.
        candidate_inputs = plugin.generate_candidates(capsules, public_context, facade)

        # 2. Evaluate each candidate against each capsule.
        evaluations_by_candidate: dict[str, list[EvaluationResult]] = {}
        for candidate in candidate_inputs:
            evals: list[EvaluationResult] = []
            for capsule in capsules:
                eval_result = plugin.evaluate_candidate_privately(candidate, capsule)
                evals.append(eval_result)
            evaluations_by_candidate[candidate.candidate_key] = evals

        # 3. Aggregate results for each candidate.
        aggregates: list[AggregateResult] = []
        for candidate in candidate_inputs:
            evals = evaluations_by_candidate.get(candidate.candidate_key, [])
            aggregate = plugin.aggregate_results(candidate, evals)
            aggregates.append(aggregate)

        # 4. Store public candidates.
        cand_repo = SceneCandidateRepository(session)
        orm_candidates: list[SceneCandidate] = []
        for agg in aggregates:
            # Find the original candidate input for metadata.
            ci = next(
                (c for c in candidate_inputs if c.candidate_key == agg.candidate_key),
                None,
            )
            orm_candidate = SceneCandidate(
                scene_instance_id=instance_id,
                candidate_key=agg.candidate_key,
                display_name=ci.display_name if ci else agg.candidate_key,
                public_metadata_json=json.dumps(ci.public_metadata) if ci and ci.public_metadata else None,
                aggregate_score=agg.aggregate_score,
                public_reason=agg.public_reason,
                status=CandidateStatus.ACTIVE.value if agg.hard_gate_passed else CandidateStatus.ELIMINATED.value,
                rank=agg.rank,
            )
            orm_candidates.append(orm_candidate)
        cand_repo.create_batch(orm_candidates)

        # 5. Build and store the public result.
        result_dict = plugin.build_public_result(aggregates, public_context, facade)
        selected_key = result_dict.get("selected_candidate_key")
        selected_candidate_id: UUID | None = None
        if selected_key:
            for c in orm_candidates:
                if c.candidate_key == selected_key:
                    selected_candidate_id = c.id
                    c.status = CandidateStatus.SELECTED.value
                    break

        public_summary = result_dict.get("public_summary", "")
        sub_count = sub_repo.count_by_instance(instance_id)

        result_repo = SceneResultRepository(session)
        result = SceneResult(
            scene_instance_id=instance_id,
            selected_candidate_id=selected_candidate_id,
            public_summary=public_summary,
            participant_count=len(capsules),
            submitted_count=sub_count,
        )
        result_repo.create(result)

        session.commit()

        # 6. Publish candidate-ready event.
        from ...events.bus import default_event_bus

        default_event_bus.publish(
            SceneCandidateReady(
                event_id=_generate_event_id(),
                scene_instance_id=instance_id,
                candidate_count=len(orm_candidates),
                occurred_at=utc_now(),
            )
        )

        # 7. Trigger cleanup of private data.
        from .cleanup import cleanup_private_data

        cleanup_private_data(instance_id, session, facade=facade)

        logger.info(
            "scene.coordinator.generation_complete",
            extra={
                "instance_id": str(instance_id),
                "candidates": len(orm_candidates),
                "submissions": sub_count,
            },
        )

        return {
            "instance_id": str(instance_id),
            "candidate_count": len(orm_candidates),
            "submitted_count": sub_count,
            "result_id": str(result.id),
        }

    except Exception as exc:
        logger.error(
            "scene.coordinator.generation_failed",
            extra={"instance_id": str(instance_id), "error": str(exc)},
        )
        # Transition to FAILED.
        instance_repo.update_status(
            instance_id,
            SceneState.FAILED.value,
            SceneState.FAILED.value,
        )
        instance = instance_repo.get_by_id(instance_id)
        if instance is not None:
            instance.failed_reason_code = "generation_failed"
        session.commit()

        # Still cleanup private data on failure.
        from .cleanup import cleanup_private_data

        cleanup_private_data(instance_id, session, facade=facade)

        raise ScenePluginError(
            message="场景候选生成失败",
            details={"reason": "generation_failed"},
        ) from exc


def get_facade(
    session: Session,
    *,
    conversation_id: UUID | None = None,
    actor_id: UUID | None = None,
) -> SceneServiceFacade:
    """Get a SceneServiceFacade instance for plugin use."""
    return SceneCoordinatorFacade(
        session,
        conversation_id=conversation_id,
        actor_id=actor_id,
    )
