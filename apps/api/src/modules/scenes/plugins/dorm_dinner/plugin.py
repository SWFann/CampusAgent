"""P9-12: DormDinnerPlugin — the main scene plugin implementation.

This plugin implements the full ScenePlugin protocol for the dorm
dinner planning scenario. It delegates to the schema, capsule,
algorithm, reasons, and model_enhancement modules.

Lifecycle:
    validate_private_submission → build_private_capsule →
    generate_candidates → evaluate_candidate_privately →
    aggregate_results → build_public_result → cleanup_private_data

Privacy guarantees:
- Raw preferences (including notes) never leave the private domain.
- Only de-identified capsules are used for candidate generation.
- Public results contain only aggregate scores and allowlisted reasons.
- The model gateway only sees non-sensitive structured data.
- When the model is unavailable, the rule-based path completes the scenario.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from ...plugin_protocol import SceneServiceFacade
from ...schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
    PrivateCapsule,
)
from .algorithm import (
    aggregate_evaluations,
    build_ranked_result,
    evaluate_candidate,
    generate_candidates,
)
from .capsule import build_capsule
from .model_enhancement import enhance_public_summary
from .schema import validate_raw_preferences

logger = logging.getLogger("campus_agent.scenes.dorm_dinner.plugin")


class DormDinnerPlugin:
    """Scene plugin for the dormitory dinner planning scenario.

    This is the competition's main demo scenario. Four dorm-mates
    negotiate where to eat dinner together, with strict privacy
    boundaries enforced by the P8 Scene Core framework.
    """

    # ScenePlugin metadata
    scene_key: str = "dorm_dinner"
    version: str = "1.0.0"
    name: str = "宿舍聚餐协商"
    description: str = (
        "宿舍四人聚餐协商场景：私有偏好提交、候选生成、"
        "确定性聚合、投票确认。支持离线运行和规则备用路径。"
    )

    # ------------------------------------------------------------------
    # P9-01 / P9-03: Input validation
    # ------------------------------------------------------------------

    def validate_private_submission(
        self,
        raw_preferences: dict[str, Any],
    ) -> None:
        """Validate the user's raw preference submission.

        Raises:
            ValueError: If the submission fails validation (range,
                enum, or length constraints).
        """
        validate_raw_preferences(raw_preferences)

    # ------------------------------------------------------------------
    # P9-04 / P9-05: Capsule building
    # ------------------------------------------------------------------

    def build_private_capsule(
        self,
        raw_preferences: dict[str, Any],
    ) -> PrivateCapsule:
        """Build a de-identified capsule from raw preferences.

        The capsule contains only hard constraints, soft preferences,
        and weights — never raw free-text or identifiable data.
        """
        return build_capsule(raw_preferences)

    # ------------------------------------------------------------------
    # P9-07: Candidate generation
    # ------------------------------------------------------------------

    def generate_candidates(
        self,
        capsules: list[PrivateCapsule],
        public_context: dict[str, Any] | None,
        facade: SceneServiceFacade,
    ) -> list[CandidateInput]:
        """Generate public candidates from all participants' capsules.

        Uses only the de-identified capsules and public context —
        never raw private input.
        """
        return generate_candidates(capsules, public_context)

    # ------------------------------------------------------------------
    # P9-08: Private candidate evaluation
    # ------------------------------------------------------------------

    def evaluate_candidate_privately(
        self,
        candidate: CandidateInput,
        capsule: PrivateCapsule,
    ) -> EvaluationResult:
        """Privately evaluate a candidate against one user's capsule.

        The result is never exposed publicly — it feeds into
        ``aggregate_results``.
        """
        return evaluate_candidate(candidate, capsule)

    # ------------------------------------------------------------------
    # P9-09: Deterministic aggregation
    # ------------------------------------------------------------------

    def aggregate_results(
        self,
        candidate: CandidateInput,
        evaluations: list[EvaluationResult],
    ) -> AggregateResult:
        """Aggregate private evaluations into a public-safe result.

        Uses a deterministic algorithm: hard gate, mean utility,
        fairness penalty, distance/budget bonuses, stable sort.
        """
        return aggregate_evaluations(candidate, evaluations)

    # ------------------------------------------------------------------
    # P9-10 / P9-11: Build public result with model enhancement
    # ------------------------------------------------------------------

    def build_public_result(
        self,
        aggregates: list[AggregateResult],
        public_context: dict[str, Any] | None,
        facade: SceneServiceFacade,
    ) -> dict[str, Any]:
        """Build the final public result from aggregated candidates.

        This method:
        1. Ranks candidates using the deterministic algorithm.
        2. Optionally enhances the public summary using the model
           gateway (P9-11). If the model fails, the rule-based text
           is used.
        3. Returns a dict with selected_candidate_key, public_summary,
           and ranked_candidates.

        Privacy:
        - Only restaurant names, scores, and allowlisted reason codes
          are sent to the model.
        - No raw preferences, capsules, evaluations, or notes are
          included in the model prompt.
        """
        # Rank candidates deterministically.
        ranked_result = build_ranked_result(aggregates)

        # Enhance the public summary using the model (best-effort).
        enhanced_summary = enhance_public_summary(ranked_result, facade)
        ranked_result["public_summary"] = enhanced_summary

        return ranked_result

    # ------------------------------------------------------------------
    # P9-15: Cleanup
    # ------------------------------------------------------------------

    def cleanup_private_data(
        self,
        scene_instance_id: UUID,
        facade: SceneServiceFacade,
    ) -> None:
        """Plugin-specific cleanup hook.

        The standard cleanup (in cleanup.py) purges encrypted payloads
        and capsule JSON. This method handles any plugin-specific
        derived data. For the dorm dinner scenario, there is no
        additional plugin-specific data to clean up — all derived data
        (candidates, results) is already public-safe.
        """
        logger.info(
            "dorm_dinner.cleanup",
            extra={"scene_instance_id": str(scene_instance_id)},
        )
