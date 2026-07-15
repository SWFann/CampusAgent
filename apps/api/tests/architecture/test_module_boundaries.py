"""Keep the modular-monolith skeleton aligned with MODULE_BOUNDARIES.md."""

from __future__ import annotations

import ast
from pathlib import Path

MODULES_ROOT = Path(__file__).parents[2] / "src" / "modules"
BUSINESS_MODULES = {
    "admin",
    "agents",
    "audit",
    "auth",
    "conversations",
    "directory",
    "memories",
    "model_gateway",
    "nodes",
    "notifications",
    "organizations",
    "scenes",
    "users",
}
REQUIRED_FILES = {
    "__init__.py",
    "api.py",
    "events.py",
    "exceptions.py",
    "models.py",
    "permissions.py",
    "repository.py",
    "schemas.py",
    "service.py",
}


def test_business_modules_follow_the_frozen_template() -> None:
    for module_name in BUSINESS_MODULES:
        module_files = {path.name for path in (MODULES_ROOT / module_name).glob("*.py")}
        assert module_files >= REQUIRED_FILES, f"{module_name} is missing {REQUIRED_FILES - module_files}"


def test_modules_do_not_import_other_modules_models() -> None:
    violations: list[str] = []
    for module_name in BUSINESS_MODULES:
        for source_file in (MODULES_ROOT / module_name).glob("*.py"):
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.module is None:
                    continue
                imported = node.module.lstrip(".")
                for other_module in BUSINESS_MODULES - {module_name}:
                    if imported.endswith(f"modules.{other_module}.models"):
                        violations.append(f"{source_file}: {node.module}")

    assert not violations, "Cross-module ORM imports are forbidden:\n" + "\n".join(violations)
