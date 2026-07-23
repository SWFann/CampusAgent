"""Scene plugins package.

This package contains all scene plugin implementations. Each plugin
implements the ScenePlugin protocol defined in plugin_protocol.py.

Available plugins:
- ``dorm_dinner``: The dormitory dinner planning scenario (P9).
"""

from __future__ import annotations

from .dorm_dinner import DormDinnerPlugin
from .structured_choice import StructuredChoicePlugin, campus_structured_plugins

__all__ = ["DormDinnerPlugin", "StructuredChoicePlugin", "campus_structured_plugins"]
