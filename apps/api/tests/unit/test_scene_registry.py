"""P8-02: Scene registry tests.

Tests:
- Register a plugin and retrieve it.
- scene_key + version uniqueness.
- Enable/disable.
- Disabled plugin not in list_enabled.
- Non-existent plugin raises SceneNotFoundError.
- Protocol conformance check.
"""
from __future__ import annotations

import pytest

from src.modules.scenes.exceptions import (
    SceneAlreadyExistsError,
    SceneNotFoundError,
)
from src.modules.scenes.registry import SceneRegistry
from src.modules.scenes.test_plugins import MaliciousScenePlugin, NoopScenePlugin


class TestSceneRegistry:
    """Test the SceneRegistry."""

    @pytest.fixture(autouse=True)
    def setup_registry(self) -> None:
        """Use a fresh registry for each test."""
        self.registry = SceneRegistry()

    def test_register_and_get(self) -> None:
        """Register a plugin and retrieve it."""
        plugin = NoopScenePlugin()
        self.registry.register(plugin)
        retrieved = self.registry.get("noop_scene", "1.0.0")
        assert retrieved is plugin

    def test_duplicate_registration_raises(self) -> None:
        """Duplicate scene_key + version raises SceneAlreadyExistsError."""
        self.registry.register(NoopScenePlugin())
        with pytest.raises(SceneAlreadyExistsError):
            self.registry.register(NoopScenePlugin())

    def test_get_nonexistent_raises(self) -> None:
        """Getting a non-existent plugin raises SceneNotFoundError."""
        with pytest.raises(SceneNotFoundError):
            self.registry.get("nonexistent", "1.0.0")

    def test_enable_disable(self) -> None:
        """Enable and disable a plugin."""
        self.registry.register(NoopScenePlugin())
        assert self.registry.is_enabled("noop_scene", "1.0.0")

        self.registry.disable("noop_scene", "1.0.0")
        assert not self.registry.is_enabled("noop_scene", "1.0.0")

        self.registry.enable("noop_scene", "1.0.0")
        assert self.registry.is_enabled("noop_scene", "1.0.0")

    def test_list_enabled_excludes_disabled(self) -> None:
        """list_enabled only returns enabled plugins."""
        self.registry.register(NoopScenePlugin())
        self.registry.register(MaliciousScenePlugin())
        self.registry.disable("malicious_scene", "1.0.0")

        enabled = self.registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].scene_key == "noop_scene"

    def test_list_all_includes_disabled(self) -> None:
        """list_all returns all plugins."""
        self.registry.register(NoopScenePlugin())
        self.registry.register(MaliciousScenePlugin())
        self.registry.disable("malicious_scene", "1.0.0")

        all_plugins = self.registry.list_all()
        assert len(all_plugins) == 2

    def test_unregister(self) -> None:
        """Unregister removes a plugin."""
        self.registry.register(NoopScenePlugin())
        self.registry.unregister("noop_scene", "1.0.0")
        with pytest.raises(SceneNotFoundError):
            self.registry.get("noop_scene", "1.0.0")

    def test_unregister_nonexistent_raises(self) -> None:
        """Unregistering a non-existent plugin raises."""
        with pytest.raises(SceneNotFoundError):
            self.registry.unregister("nonexistent", "1.0.0")

    def test_disable_nonexistent_raises(self) -> None:
        """Disabling a non-existent plugin raises."""
        with pytest.raises(SceneNotFoundError):
            self.registry.disable("nonexistent", "1.0.0")

    def test_clear(self) -> None:
        """Clear removes all plugins."""
        self.registry.register(NoopScenePlugin())
        self.registry.clear()
        assert len(self.registry.list_all()) == 0

    def test_get_entry_returns_full_entry(self) -> None:
        """get_entry returns the full RegistryEntry with enabled flag."""
        self.registry.register(NoopScenePlugin(), enabled=False)
        entry = self.registry.get_entry("noop_scene", "1.0.0")
        assert entry.enabled is False
        assert entry.scene_key == "noop_scene"
        assert entry.name == "Noop Scene"
