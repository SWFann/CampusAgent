"""P6-10: Architecture test — no module may bypass Memory Service.

This test verifies that no module outside ``modules/memories/`` directly
imports ``MemoryRepository`` or ``ConsentRepository``. Only
``modules/memories/service.py`` and ``modules/memories/consent.py`` and
``modules/memories/cleanup.py`` are allowed to use the repositories.

Tests are allowed to import the repositories for setup.
"""
from __future__ import annotations

import ast
from pathlib import Path

# Root of the API source tree
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"

# Modules that ARE allowed to import MemoryRepository / ConsentRepository
_ALLOWED_IMPORTERS = {
    "modules/memories/service.py",
    "modules/memories/consent.py",
    "modules/memories/cleanup.py",
    "modules/memories/repository.py",  # defines them
}

# Modules that must NEVER import MemoryRepository / ConsentRepository
_FORBIDDEN_PATTERNS = {"MemoryRepository", "ConsentRepository"}


def _find_python_files(root: Path) -> list[Path]:
    """Find all .py files under root, excluding __pycache__."""
    return [
        p
        for p in root.rglob("*.py")
        if "__pycache__" not in str(p) and p.stat().st_size > 0
    ]


def _check_imports(file_path: Path) -> set[str]:
    """Return the set of forbidden symbols imported in this file."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return set()

    forbidden_found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            for alias in node.names:
                if alias.name in _FORBIDDEN_PATTERNS:
                    forbidden_found.add(alias.name)
    return forbidden_found


class TestMemoryServiceBoundary:
    """Verify no module bypasses Memory Service by importing repositories directly."""

    def test_no_direct_repository_import_outside_memories(self) -> None:
        """No module outside modules/memories/ imports MemoryRepository or ConsentRepository."""
        violators: list[str] = []

        for py_file in _find_python_files(_SRC_ROOT):
            rel = py_file.relative_to(_SRC_ROOT)
            rel_str = str(rel).replace("\\", "/")

            # Skip allowed importers
            if rel_str in _ALLOWED_IMPORTERS:
                continue

            # Skip test files (they're not in src/)
            # Skip __init__.py files
            if rel_str.endswith("__init__.py"):
                continue

            forbidden = _check_imports(py_file)
            if forbidden:
                violators.append(
                    f"{rel_str}: imports {', '.join(sorted(forbidden))}"
                )

        assert not violators, (
            "Modules bypassing Memory Service detected:\n" + "\n".join(violators)
        )

    def test_memory_service_uses_repository(self) -> None:
        """Verify that memory service.py does import MemoryRepository (sanity check)."""
        service_path = _SRC_ROOT / "modules/memories/service.py"
        forbidden = _check_imports(service_path)
        assert "MemoryRepository" in forbidden

    def test_consent_service_uses_repository(self) -> None:
        """Verify that consent.py does import ConsentRepository (sanity check)."""
        consent_path = _SRC_ROOT / "modules/memories/consent.py"
        forbidden = _check_imports(consent_path)
        assert "ConsentRepository" in forbidden

    def test_audit_service_does_not_import_memory_repo(self) -> None:
        """Audit service must not import MemoryRepository."""
        audit_path = _SRC_ROOT / "modules/audit/service.py"
        forbidden = _check_imports(audit_path)
        assert "MemoryRepository" not in forbidden
        assert "ConsentRepository" not in forbidden

    def test_agents_service_does_not_import_memory_repo(self) -> None:
        """Agents service must not import MemoryRepository."""
        agents_path = _SRC_ROOT / "modules/agents/service.py"
        forbidden = _check_imports(agents_path)
        assert "MemoryRepository" not in forbidden
        assert "ConsentRepository" not in forbidden

    def test_conversations_service_does_not_import_memory_repo(self) -> None:
        """Conversations service must not import MemoryRepository."""
        conv_path = _SRC_ROOT / "modules/conversations/service.py"
        forbidden = _check_imports(conv_path)
        assert "MemoryRepository" not in forbidden
        assert "ConsentRepository" not in forbidden
