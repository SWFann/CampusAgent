"""Scene Registry — registers and manages scene plugin definitions.

The registry is the single source of truth for which scene plugins are
available. It enforces:
- scene_key + version uniqueness.
- Plugin conformance to the ScenePlugin protocol.
- Enable/disable at runtime.

Privacy: the registry never stores private data — only plugin metadata.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from .exceptions import SceneAlreadyExistsError, SceneNotFoundError, ScenePluginError
from .plugin_protocol import ScenePlugin

logger = logging.getLogger("campus_agent.scenes.registry")


@dataclass
class RegistryEntry:
    """A registered scene plugin entry."""

    plugin: ScenePlugin
    enabled: bool = True
    capabilities: dict[str, Any] = field(default_factory=dict)

    @property
    def scene_key(self) -> str:
        return self.plugin.scene_key

    @property
    def version(self) -> str:
        return self.plugin.version

    @property
    def name(self) -> str:
        return self.plugin.name

    @property
    def description(self) -> str:
        return self.plugin.description


class SceneRegistry:
    """Thread-safe registry of scene plugins.

    Usage:
        registry = get_scene_registry()
        registry.register(my_plugin)
        plugin = registry.get("meal_planning", "1.0.0")
        plugins = registry.list_enabled()
    """

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._lock = threading.Lock()

    def _make_key(self, scene_key: str, version: str) -> str:
        """Build the internal lookup key."""
        return f"{scene_key}:{version}"

    def register(
        self,
        plugin: ScenePlugin,
        *,
        enabled: bool = True,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        """Register a scene plugin.

        Args:
            plugin: An object implementing the ScenePlugin protocol.
            enabled: Whether the plugin is enabled on registration.
            capabilities: Optional capability metadata.

        Raises:
            SceneAlreadyExistsError: If scene_key + version is already
                registered.
            ScenePluginError: If the plugin does not conform to the
                ScenePlugin protocol.
        """
        # Validate protocol conformance (runtime_checkable).
        if not isinstance(plugin, ScenePlugin):
            raise ScenePluginError(
                message="插件不符合 ScenePlugin 协议",
                details={"type": type(plugin).__name__},
            )

        # Validate required attributes.
        if not hasattr(plugin, "scene_key") or not plugin.scene_key:
            raise ScenePluginError(
                message="插件缺少 scene_key 属性",
                details={"type": type(plugin).__name__},
            )
        if not hasattr(plugin, "version") or not plugin.version:
            raise ScenePluginError(
                message="插件缺少 version 属性",
                details={"type": type(plugin).__name__},
            )

        key = self._make_key(plugin.scene_key, plugin.version)

        with self._lock:
            if key in self._entries:
                raise SceneAlreadyExistsError(
                    details={"scene_key": plugin.scene_key, "version": plugin.version}
                )
            self._entries[key] = RegistryEntry(
                plugin=plugin,
                enabled=enabled,
                capabilities=capabilities or {},
            )
            logger.info(
                "scene.registry.register",
                extra={"scene_key": plugin.scene_key, "version": plugin.version},
            )

    def unregister(self, scene_key: str, version: str) -> None:
        """Remove a plugin from the registry."""
        key = self._make_key(scene_key, version)
        with self._lock:
            if key not in self._entries:
                raise SceneNotFoundError(
                    details={"scene_key": scene_key, "version": version}
                )
            del self._entries[key]
            logger.info(
                "scene.registry.unregister",
                extra={"scene_key": scene_key, "version": version},
            )

    def get(self, scene_key: str, version: str = "1.0.0") -> ScenePlugin:
        """Get a plugin by scene_key + version.

        Raises:
            SceneNotFoundError: If not registered.
        """
        key = self._make_key(scene_key, version)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                raise SceneNotFoundError(
                    details={"scene_key": scene_key, "version": version}
                )
            return entry.plugin

    def get_entry(self, scene_key: str, version: str = "1.0.0") -> RegistryEntry:
        """Get the full registry entry (includes enabled flag)."""
        key = self._make_key(scene_key, version)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                raise SceneNotFoundError(
                    details={"scene_key": scene_key, "version": version}
                )
            return entry

    def enable(self, scene_key: str, version: str = "1.0.0") -> None:
        """Enable a registered plugin."""
        key = self._make_key(scene_key, version)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                raise SceneNotFoundError(
                    details={"scene_key": scene_key, "version": version}
                )
            entry.enabled = True

    def disable(self, scene_key: str, version: str = "1.0.0") -> None:
        """Disable a registered plugin."""
        key = self._make_key(scene_key, version)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                raise SceneNotFoundError(
                    details={"scene_key": scene_key, "version": version}
                )
            entry.enabled = False

    def is_enabled(self, scene_key: str, version: str = "1.0.0") -> bool:
        """Check if a plugin is registered and enabled."""
        key = self._make_key(scene_key, version)
        with self._lock:
            entry = self._entries.get(key)
            return entry is not None and entry.enabled

    def list_all(self) -> list[RegistryEntry]:
        """List all registered plugins (enabled and disabled)."""
        with self._lock:
            return list(self._entries.values())

    def list_enabled(self) -> list[RegistryEntry]:
        """List only enabled plugins."""
        with self._lock:
            return [e for e in self._entries.values() if e.enabled]

    def clear(self) -> None:
        """Remove all registered plugins (for testing)."""
        with self._lock:
            self._entries.clear()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_registry: SceneRegistry | None = None


def get_scene_registry() -> SceneRegistry:
    """Get the singleton SceneRegistry instance."""
    global _registry
    if _registry is None:
        _registry = SceneRegistry()
    return _registry


def reset_scene_registry() -> None:
    """Reset the singleton (for testing)."""
    global _registry
    _registry = None
