"""P8-13: Scene boundary plugin tests.

Tests that the framework rejects malicious plugin behavior:
- Capsule with forbidden keys (raw_text) is rejected by validate_capsule.
- Plugin protocol conformance is checked at registration.
- Malicious plugin's capsule validation fails.
- NoopScenePlugin passes all validations.
"""
from __future__ import annotations

import pytest

from src.modules.scenes.privacy import validate_capsule
from src.modules.scenes.registry import SceneRegistry
from src.modules.scenes.schemas import PrivateCapsule
from src.modules.scenes.test_plugins import MaliciousScenePlugin, NoopScenePlugin


class TestBoundaryPlugin:
    """Test that the framework enforces its boundaries."""

    def test_noop_plugin_passes_capsule_validation(self) -> None:
        """The noop plugin's capsule should pass validation."""
        plugin = NoopScenePlugin()
        capsule = plugin.build_private_capsule(
            {"require_vegetarian": True, "prefer_spicy": 3}
        )
        validate_capsule(capsule)  # should not raise

    def test_malicious_plugin_capsule_rejected(self) -> None:
        """The malicious plugin's capsule with raw_text should be rejected."""
        plugin = MaliciousScenePlugin()
        capsule = plugin.build_private_capsule({"key": "value"})
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_noop_plugin_protocol_conformance(self) -> None:
        """NoopScenePlugin should pass the ScenePlugin protocol check."""
        from src.modules.scenes.plugin_protocol import ScenePlugin

        assert isinstance(NoopScenePlugin(), ScenePlugin)

    def test_malicious_plugin_protocol_conformance(self) -> None:
        """MaliciousScenePlugin should also pass the protocol check
        (it implements the methods), but its output is rejected by
        the privacy validation layer."""
        from src.modules.scenes.plugin_protocol import ScenePlugin

        assert isinstance(MaliciousScenePlugin(), ScenePlugin)

    def test_registry_rejects_non_protocol_objects(self) -> None:
        """Registry should reject objects that don't implement the protocol."""
        registry = SceneRegistry()

        class NotAPlugin:
            pass

        from src.modules.scenes.exceptions import ScenePluginError

        with pytest.raises(ScenePluginError):
            registry.register(NotAPlugin())  # type: ignore[arg-type]

    def test_registry_rejects_missing_scene_key(self) -> None:
        """Registry should reject plugins without scene_key."""
        registry = SceneRegistry()

        class MissingKeyPlugin:
            version: str = "1.0.0"
            name: str = "Missing Key"
            description: str = "No scene_key"

            def validate_private_submission(self, raw): pass
            def build_private_capsule(self, raw): pass
            def generate_candidates(self, capsules, ctx, facade): pass
            def evaluate_candidate_privately(self, c, cap): pass
            def aggregate_results(self, c, evals): pass
            def build_public_result(self, aggs, ctx, facade): pass
            def cleanup_private_data(self, sid, facade): pass

        from src.modules.scenes.exceptions import ScenePluginError

        with pytest.raises(ScenePluginError):
            registry.register(MissingKeyPlugin())  # type: ignore[arg-type]

    def test_capsule_with_email_in_nested_dict_rejected(self) -> None:
        """A capsule with 'email' nested inside hard_constraints is rejected."""
        capsule = PrivateCapsule(
            hard_constraints={"contact": {"email": "user@example.com"}},
        )
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_capsule_with_phone_rejected(self) -> None:
        """A capsule with 'phone' key is rejected."""
        capsule = PrivateCapsule(
            soft_preferences={"phone": "1234567890"},
        )
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_capsule_with_name_rejected(self) -> None:
        """A capsule with 'name' key is rejected."""
        capsule = PrivateCapsule(
            hard_constraints={"name": "John Doe"},
        )
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_noop_plugin_generate_candidates_returns_public_data(self) -> None:
        """NoopScenePlugin.generate_candidates returns only public data."""
        plugin = NoopScenePlugin()
        capsule = plugin.build_private_capsule({"require_a": True})
        candidates = plugin.generate_candidates([capsule], None, None)

        for c in candidates:
            assert c.candidate_key is not None
            assert c.display_name is not None
            # public_metadata should not contain private fields
            if c.public_metadata:
                for key in c.public_metadata:
                    assert key.lower() not in ("email", "phone", "name", "raw_text")

    def test_noop_plugin_aggregate_results_no_individual_scores(self) -> None:
        """NoopScenePlugin.aggregate_results should not expose individual scores."""
        plugin = NoopScenePlugin()
        from src.modules.scenes.schemas import CandidateInput, EvaluationResult

        candidate = CandidateInput(candidate_key="c1", display_name="C1")
        evals = [
            EvaluationResult(candidate_key="c1", utility=0.8),
            EvaluationResult(candidate_key="c1", utility=0.6),
        ]
        result = plugin.aggregate_results(candidate, evals)

        # The public_reason should not contain individual scores.
        assert "0.8" not in result.public_reason or "0.7" in result.public_reason  # avg is ok
        # The aggregate score is the average, not individual.
        assert result.aggregate_score == pytest.approx(0.7, abs=0.01)
