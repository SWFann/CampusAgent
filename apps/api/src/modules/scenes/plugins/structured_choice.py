"""Privacy-safe structured choice plugins for common campus collaboration."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from ..exceptions import SceneSubmissionError
from ..plugin_protocol import SceneServiceFacade
from ..schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
    PrivateCapsule,
)


class StructuredChoicePlugin:
    """A small reusable plugin for time polls and task claiming.

    Individual selections remain encrypted. Only option-level aggregate counts
    are used to produce the public result.
    """

    version = "1.0.0"

    def __init__(self, *, scene_key: str, name: str, description: str) -> None:
        self.scene_key = scene_key
        self.name = name
        self.description = description

    def validate_private_submission(self, raw_preferences: dict[str, Any]) -> None:
        selections = raw_preferences.get("selections")
        if not isinstance(selections, list) or not selections or len(selections) > 20:
            raise SceneSubmissionError(details={"reason": "one_to_twenty_selections_required"})
        if any(not isinstance(item, str) or not item.strip() for item in selections):
            raise SceneSubmissionError(details={"reason": "selection_must_be_non_empty_text"})

    def build_private_capsule(self, raw_preferences: dict[str, Any]) -> PrivateCapsule:
        selections = [str(item).strip()[:100] for item in raw_preferences["selections"]]
        return PrivateCapsule(
            soft_preferences={"selections": selections},
            allowed_reason_codes=["member_selected"],
        )

    def generate_candidates(
        self,
        capsules: list[PrivateCapsule],
        public_context: dict[str, Any] | None,
        facade: SceneServiceFacade,
    ) -> list[CandidateInput]:
        del capsules, facade
        raw_options = (public_context or {}).get("options", [])
        options = [str(item).strip()[:100] for item in raw_options if str(item).strip()]
        return [
            CandidateInput(
                candidate_key=f"option-{index + 1}",
                display_name=option,
                public_metadata={"option": option},
            )
            for index, option in enumerate(options[:20])
        ]

    def evaluate_candidate_privately(
        self,
        candidate: CandidateInput,
        capsule: PrivateCapsule,
    ) -> EvaluationResult:
        selected = set(capsule.soft_preferences.get("selections", []))
        option = str(candidate.public_metadata.get("option", candidate.display_name))
        matched = option in selected
        return EvaluationResult(
            candidate_key=candidate.candidate_key,
            utility=1.0 if matched else 0.0,
            reason_codes=["member_selected"] if matched else [],
        )

    def aggregate_results(
        self,
        candidate: CandidateInput,
        evaluations: list[EvaluationResult],
    ) -> AggregateResult:
        votes = sum(1 for evaluation in evaluations if evaluation.utility > 0)
        total = len(evaluations)
        return AggregateResult(
            candidate_key=candidate.candidate_key,
            aggregate_score=float(votes),
            public_reason=f"{votes}/{total} 位参与者选择",
            rank=0,
        )

    def build_public_result(
        self,
        aggregates: list[AggregateResult],
        public_context: dict[str, Any] | None,
        facade: SceneServiceFacade,
    ) -> dict[str, Any]:
        del public_context, facade
        ranked = sorted(aggregates, key=lambda item: (-item.aggregate_score, item.candidate_key))
        if not ranked:
            return {
                "selected_candidate_key": None,
                "public_summary": "尚无成员提交，暂未形成协作结果。",
                "ranked_candidates": [],
            }
        winner = ranked[0]
        return {
            "selected_candidate_key": winner.candidate_key,
            "public_summary": f"当前最多成员选择了第 {winner.candidate_key.removeprefix('option-')} 项。",
            "ranked_candidates": [item.model_dump(mode="json") for item in ranked],
        }

    def cleanup_private_data(
        self,
        scene_instance_id: UUID,
        facade: SceneServiceFacade,
    ) -> None:
        del scene_instance_id, facade


def campus_structured_plugins() -> list[StructuredChoicePlugin]:
    return [
        StructuredChoicePlugin(
            scene_key="time_poll",
            name="共同时间协调",
            description="收集成员可用时间，形成可由负责人确认的候选时段。",
        ),
        StructuredChoicePlugin(
            scene_key="task_claim",
            name="任务分工认领",
            description="将群体工作拆分为任务，由成员自主认领并汇总结果。",
        ),
    ]
