"""P8-01: Scene plugin protocol tests.

Tests:
- NoopScenePlugin implements all required methods.
- SceneServiceFacade protocol has the correct interface.
- Protocol is runtime_checkable.
- Plugin lifecycle methods produce correct types.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.scenes.plugin_protocol import ScenePlugin
from src.modules.scenes.schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
    PrivateCapsule,
)
from src.modules.scenes.test_plugins import NoopScenePlugin


class TestPluginProtocol:
    """Test the ScenePlugin protocol conformance."""

    def test_noop_plugin_is_scene_plugin(self) -> None:
        """NoopScenePlugin should be recognized as a ScenePlugin."""
        assert isinstance(NoopScenePlugin(), ScenePlugin)

    def test_protocol_is_runtime_checkable(self) -> None:
        """The ScenePlugin protocol should be runtime_checkable."""
        # isinstance() check on a Protocol requires runtime_checkable.
        assert isinstance(NoopScenePlugin(), ScenePlugin)

    def test_noop_plugin_has_required_attributes(self) -> None:
        """Plugin must have scene_key, version, name, description."""
        plugin = NoopScenePlugin()
        assert hasattr(plugin, "scene_key")
        assert hasattr(plugin, "version")
        assert hasattr(plugin, "name")
        assert hasattr(plugin, "description")
        assert plugin.scene_key == "noop_scene"
        assert plugin.version == "1.0.0"

    def test_validate_private_submission(self) -> None:
        """validate_private_submission should accept valid input."""
        plugin = NoopScenePlugin()
        plugin.validate_private_submission({"key": "value"})  # should not raise

    def test_validate_private_submission_rejects_empty(self) -> None:
        """validate_private_submission should reject empty input."""
        plugin = NoopScenePlugin()
        from src.modules.scenes.exceptions import SceneSubmissionError

        with pytest.raises(SceneSubmissionError):
            plugin.validate_private_submission({})

    def test_build_private_capsule_returns_correct_type(self) -> None:
        """build_private_capsule should return a PrivateCapsule."""
        plugin = NoopScenePlugin()
        capsule = plugin.build_private_capsule({"require_a": True, "prefer_b": 2})
        assert isinstance(capsule, PrivateCapsule)
        assert "require_a" in capsule.hard_constraints
        assert "prefer_b" in capsule.soft_preferences

    def test_generate_candidates_returns_list(self) -> None:
        """generate_candidates should return a list of CandidateInput."""
        plugin = NoopScenePlugin()
        capsule = plugin.build_private_capsule({"require_a": True})
        candidates = plugin.generate_candidates([capsule], None, None)
        assert isinstance(candidates, list)
        for c in candidates:
            assert isinstance(c, CandidateInput)

    def test_evaluate_candidate_returns_evaluation_result(self) -> None:
        """evaluate_candidate_privately should return EvaluationResult."""
        plugin = NoopScenePlugin()
        capsule = plugin.build_private_capsule({"require_a": True})
        candidate = CandidateInput(candidate_key="c1", display_name="C1")
        result = plugin.evaluate_candidate_privately(candidate, capsule)
        assert isinstance(result, EvaluationResult)
        assert result.candidate_key == "c1"

    def test_aggregate_results_returns_aggregate_result(self) -> None:
        """aggregate_results should return AggregateResult."""
        plugin = NoopScenePlugin()
        candidate = CandidateInput(candidate_key="c1", display_name="C1")
        evals = [EvaluationResult(candidate_key="c1", utility=0.5)]
        result = plugin.aggregate_results(candidate, evals)
        assert isinstance(result, AggregateResult)
        assert result.candidate_key == "c1"

    def test_build_public_result_returns_dict(self) -> None:
        """build_public_result should return a dict with required keys."""
        plugin = NoopScenePlugin()
        capsule = plugin.build_private_capsule({"require_a": True})
        candidates = plugin.generate_candidates([capsule], None, None)
        candidate = candidates[0]
        evals = [EvaluationResult(candidate_key=candidate.candidate_key, utility=0.5)]
        aggregate = plugin.aggregate_results(candidate, evals)
        result = plugin.build_public_result([aggregate], None, None)

        assert isinstance(result, dict)
        assert "selected_candidate_key" in result
        assert "public_summary" in result

    def test_cleanup_private_data(self) -> None:
        """cleanup_private_data should not raise."""
        plugin = NoopScenePlugin()
        plugin.cleanup_private_data(uuid4(), None)  # should not raise


class TestSceneServiceFacade:
    """Test the SceneServiceFacade protocol interface."""

    def test_facade_is_a_protocol(self) -> None:
        """SceneServiceFacade should be a Protocol."""
        # We can't instantiate a Protocol directly, but we can check
        # that the coordinator's facade implementation satisfies it.
        from src.modules.scenes.coordinator import SceneCoordinatorFacade

        # SceneCoordinatorFacade implements the SceneServiceFacade protocol.
        # We can verify it has the required methods.
        assert hasattr(SceneCoordinatorFacade, "model_chat")
        assert hasattr(SceneCoordinatorFacade, "model_embedding")
        assert hasattr(SceneCoordinatorFacade, "write_scene_message")
        assert hasattr(SceneCoordinatorFacade, "log_audit")
