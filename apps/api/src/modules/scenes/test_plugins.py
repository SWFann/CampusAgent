"""Test plugins for the scene framework.

Contains:
- ``NoopScenePlugin``: a minimal, correct plugin that implements the full
  ScenePlugin protocol. Used for framework testing and as a reference
  implementation.
- ``MaliciousScenePlugin``: a plugin that attempts boundary violations.
  Used by boundary tests to verify the framework rejects malicious
  behavior.

Privacy:
- NoopScenePlugin never returns sensitive data in capsules or results.
- MaliciousScenePlugin attempts to leak data, but the framework's
  privacy validation (validate_capsule, sanitise_log_dict) should
  reject it.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
    PrivateCapsule,
)

# ---------------------------------------------------------------------------
# NoopScenePlugin — a correct, minimal reference implementation
# ---------------------------------------------------------------------------


class NoopScenePlugin:
    """A minimal scene plugin for framework testing.

    Implements the full ScenePlugin protocol with deterministic,
    non-sensitive outputs. No model gateway calls — all logic is
    local and deterministic.
    """

    scene_key: str = "noop_scene"
    version: str = "1.0.0"
    name: str = "Noop Scene"
    description: str = "A minimal scene plugin for framework testing."

    def validate_private_submission(
        self,
        raw_preferences: dict[str, Any],
    ) -> None:
        """Validate that the submission has at least one key."""
        if not raw_preferences:
            from .exceptions import SceneSubmissionError

            raise SceneSubmissionError(
                message="提交内容不能为空",
            )

    def build_private_capsule(
        self,
        raw_preferences: dict[str, Any],
    ) -> PrivateCapsule:
        """Build a minimal capsule from raw preferences.

        Extracts hard constraints and soft preferences from the raw input
        without carrying free-text or identifiable data.
        """
        hard_constraints: dict[str, Any] = {}
        soft_preferences: dict[str, Any] = {}

        for key, value in raw_preferences.items():
            if key.startswith("require_"):
                hard_constraints[key] = value
            elif key.startswith("prefer_"):
                soft_preferences[key] = value
            else:
                soft_preferences[key] = value

        return PrivateCapsule(
            hard_constraints=hard_constraints,
            soft_preferences=soft_preferences,
            weights={},
            allowed_reason_codes=[],
        )

    def generate_candidates(
        self,
        capsules: list[PrivateCapsule],
        public_context: dict[str, Any] | None,
        facade: Any,
    ) -> list[CandidateInput]:
        """Generate deterministic candidates from capsules."""
        candidates: list[CandidateInput] = []
        for i in range(min(3, max(1, len(capsules)))):
            candidates.append(
                CandidateInput(
                    candidate_key=f"candidate_{i}",
                    display_name=f"Candidate {i + 1}",
                    public_metadata={"index": i},
                )
            )
        return candidates

    def evaluate_candidate_privately(
        self,
        candidate: CandidateInput,
        capsule: PrivateCapsule,
    ) -> EvaluationResult:
        """Deterministic evaluation — pass all hard constraints.

        Utility is derived from the candidate's public metadata ``index``
        if present, otherwise falls back to a hash-based value in [0, 1).
        This keeps the evaluation deterministic without assuming a
        specific candidate_key format.
        """
        index = candidate.public_metadata.get("index") if candidate.public_metadata else None
        if isinstance(index, int) and index >= 0:
            utility = 1.0 / (index + 1)
        else:
            # Deterministic hash-based utility in [0, 1).
            hash_val = hash(candidate.candidate_key) & 0xFFFF
            utility = (hash_val % 1000) / 1000.0
        return EvaluationResult(
            candidate_key=candidate.candidate_key,
            hard_pass=True,
            utility=utility,
            objection=False,
            reason_codes=[],
        )

    def aggregate_results(
        self,
        candidate: CandidateInput,
        evaluations: list[EvaluationResult],
    ) -> AggregateResult:
        """Aggregate evaluations into a public-safe result."""
        avg_utility = sum(e.utility for e in evaluations) / len(evaluations) if evaluations else 0.0
        return AggregateResult(
            candidate_key=candidate.candidate_key,
            aggregate_score=round(avg_utility, 4),
            public_reason=f"Average utility: {avg_utility:.2f}",
            rank=0,
            hard_gate_passed=all(e.hard_pass for e in evaluations),
        )

    def build_public_result(
        self,
        aggregates: list[AggregateResult],
        public_context: dict[str, Any] | None,
        facade: Any,
    ) -> dict[str, Any]:
        """Build the final public result."""
        # Sort by aggregate score descending.
        sorted_aggs = sorted(aggregates, key=lambda a: a.aggregate_score, reverse=True)
        for i, agg in enumerate(sorted_aggs):
            agg.rank = i + 1

        selected = sorted_aggs[0] if sorted_aggs else None
        return {
            "selected_candidate_key": selected.candidate_key if selected else None,
            "public_summary": f"Selected: {selected.candidate_key}" if selected else "No selection",
            "ranked_candidates": [
                {
                    "candidate_key": a.candidate_key,
                    "score": a.aggregate_score,
                    "rank": a.rank,
                }
                for a in sorted_aggs
            ],
        }

    def cleanup_private_data(
        self,
        scene_instance_id: UUID,
        facade: Any,
    ) -> None:
        """No plugin-specific data to clean up."""
        pass


# ---------------------------------------------------------------------------
# MaliciousScenePlugin — attempts boundary violations (for testing)
# ---------------------------------------------------------------------------


class MaliciousScenePlugin:
    """A plugin that attempts to violate privacy and security boundaries.

    The framework must reject ALL of these attempts:
    - Returning forbidden keys in capsules.
    - Attempting to access repositories directly (static check).
    - Attempting to call external models directly (static check).

    This plugin is used by test_scene_boundary_plugin.py to verify
    that the framework enforces its boundaries.
    """

    scene_key: str = "malicious_scene"
    version: str = "1.0.0"
    name: str = "Malicious Scene"
    description: str = "A plugin that attempts boundary violations (for testing)."

    def validate_private_submission(
        self,
        raw_preferences: dict[str, Any],
    ) -> None:
        """Always passes — the malice is in the capsule."""
        pass

    def build_private_capsule(
        self,
        raw_preferences: dict[str, Any],
    ) -> PrivateCapsule:
        """Attempt to include raw_text in the capsule (should be rejected)."""
        return PrivateCapsule(
            hard_constraints={"raw_text": "sensitive data that should be rejected"},
            soft_preferences={},
            weights={},
            allowed_reason_codes=[],
        )

    def generate_candidates(
        self,
        capsules: list[PrivateCapsule],
        public_context: dict[str, Any] | None,
        facade: Any,
    ) -> list[CandidateInput]:
        """Return a candidate with an email field (sensitive)."""
        return [
            CandidateInput(
                candidate_key="malicious_1",
                display_name="Malicious Candidate",
                public_metadata={"email": "user@example.com"},
            )
        ]

    def evaluate_candidate_privately(
        self,
        candidate: CandidateInput,
        capsule: PrivateCapsule,
    ) -> EvaluationResult:
        """Attempt to return individual score with PII."""
        return EvaluationResult(
            candidate_key=candidate.candidate_key,
            hard_pass=True,
            utility=0.5,
            objection=False,
            reason_codes=["leaked_email"],
        )

    def aggregate_results(
        self,
        candidate: CandidateInput,
        evaluations: list[EvaluationResult],
    ) -> AggregateResult:
        """Attempt to include individual scores in public reason."""
        individual_scores = [str(e.utility) for e in evaluations]
        return AggregateResult(
            candidate_key=candidate.candidate_key,
            aggregate_score=0.5,
            public_reason=f"Individual scores: {individual_scores}",
            rank=0,
            hard_gate_passed=True,
        )

    def build_public_result(
        self,
        aggregates: list[AggregateResult],
        public_context: dict[str, Any] | None,
        facade: Any,
    ) -> dict[str, Any]:
        """Attempt to include raw preferences in the result."""
        return {
            "selected_candidate_key": aggregates[0].candidate_key if aggregates else None,
            "public_summary": "Result with leaked data",
            "raw_preferences": {"this": "should not be here"},
        }

    def cleanup_private_data(
        self,
        scene_instance_id: UUID,
        facade: Any,
    ) -> None:
        """Attempt to call repository directly (should fail at import)."""
        # This method intentionally does nothing harmful — the boundary
        # test verifies that plugins cannot import repositories.
        pass


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_test_plugins() -> None:
    """Register the noop test plugin in the scene registry.

    This is called during test setup or application startup for the
    framework test environment.
    """
    from .registry import get_scene_registry

    registry = get_scene_registry()
    registry.clear()
    registry.register(NoopScenePlugin())
