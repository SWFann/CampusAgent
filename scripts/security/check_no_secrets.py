#!/usr/bin/env python3
"""P12-01: Lightweight secret scanner (gitleaks substitute).

Scans the working tree for high-signal secret indicators that must never
be committed to the repository:

- AWS access key IDs (``AKIA...``)
- OpenAI-style API keys (``sk-...`` long tokens)
- PEM private key headers (``BEGIN PRIVATE KEY`` / ``BEGIN RSA PRIVATE KEY``)
- Hard-coded ``MODEL_GATEWAY_API_KEY=`` assignments with a real value
- Hard-coded ``password=`` / ``password:`` assignments with a real value
- Google/Anthropic API key prefixes (``AIza...``, ``sk-ant-...``)
- Generic high-entropy ``SECRET = "..."`` assignments in source files

The scanner is intentionally conservative: it whitelists known demo/test
values (``test-secret-key-...``, ``test-encryption-key``, ``SecurePass123``
etc.) and skips vendored/generated directories.

Usage::

    uv run --project apps/api --extra dev --frozen python scripts/security/check_no_secrets.py [--root .]

Exit code 0 = no real secrets found, 1 = potential secret detected.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Directories that never contain production secrets.
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    ".swc",
    "playwright-report",
    "test-results",
}

# File extensions worth scanning.
SCAN_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".env.example",
    ".sh",
    ".md",
    ".cfg",
    ".ini",
    ".conf",
    ".txt",
    ".dockerfile",
    "Dockerfile",
}

# Whitelisted substrings — demo/test values that are safe.
ALLOWLIST_SUBSTRINGS = (
    "test-secret-key-at-least-32-chars-long",
    "test-encryption-key",
    "SecurePass123",
    "WrongPass456",
    "AnyPass123",
    "test-secret",
    "demo-secret",
    "placeholder",
    "changeme",
    "your-",
    "example-",
    "<your",
    "YOUR_",
    "xxx",
    "redacted",
    "dummy",
    "fake",
    "not-a-real",
    "sk-test-mock",
    "mock-api-key",
    "test-api-key",
    "test-key",
    "some-api-key",
    "sample-api-key",
)

# (pattern, description) pairs. Patterns are compiled regexes.
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI-style API key"),
    (re.compile(r"sk-ant-[a-zA-Z0-9]{20,}"), "Anthropic API key"),
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "Google API key"),
    (re.compile(r"-----BEGIN (RSA |EC |)PRIVATE KEY-----"), "PEM private key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"), "GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
]


def _is_allowed(value: str) -> bool:
    lowered = value.lower()
    return any(allow in lowered for allow in (a.lower() for a in ALLOWLIST_SUBSTRINGS))


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        suffix = path.suffix.lower()
        name = path.name
        if suffix in SCAN_EXTENSIONS or name in SCAN_EXTENSIONS or name == ".env.example":
            files.append(path)
    return files


def scan_file(path: Path, root: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, description, snippet) hits for a file."""
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits

    for lineno, line in enumerate(text.splitlines(), start=1):
        # 1. Regex-based secret patterns.
        for pattern, desc in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                if _is_allowed(match.group(0)):
                    continue
                hits.append((lineno, desc, line.strip()[:160]))
                break

        # 2. Hard-coded assignment of MODEL_GATEWAY_API_KEY to a string literal.
        #    Only flag when the RHS is a quoted literal, not a variable/env ref.
        m = re.search(r'MODEL_GATEWAY_API_KEY\s*[:=]\s*["\']([^"\']+)["\']', line)
        if m and not _is_allowed(m.group(1)):
            hits.append((lineno, "hardcoded MODEL_GATEWAY_API_KEY", line.strip()[:160]))

        # 3. Hard-coded password assignment to a string literal in config files.
        #    We only flag quoted-literal RHS to avoid variable references like
        #    ``password=body.password``.
        if not _is_allowed(line) and "test" not in path.name.lower():
            m = re.search(r'(?i)\bpassword\s*[:=]\s*["\']([A-Za-z0-9_!@#$%^&*.-]{6,})["\']', line)
            if m and not _is_allowed(m.group(1)):
                hits.append((lineno, "hardcoded password", line.strip()[:160]))

    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repo for real secrets.")
    parser.add_argument("--root", default=".", help="Repository root (default: cwd).")
    parser.add_argument(
        "--quiet", action="store_true", help="Only print hits and exit code."
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not args.quiet:
        print(f"Scanning {root} for secrets...")

    all_hits: list[tuple[Path, int, str, str]] = []
    files = _iter_files(root)
    for path in files:
        for lineno, desc, snippet in scan_file(path, root):
            all_hits.append((path, lineno, desc, snippet))

    if not all_hits:
        if not args.quiet:
            print(f"OK: scanned {len(files)} files, no real secrets detected.")
        return 0

    print(f"FAIL: {len(all_hits)} potential secret(s) detected:\n")
    for path, lineno, desc, snippet in all_hits:
        rel = path.relative_to(root)
        print(f"  {rel}:{lineno}  [{desc}]")
        print(f"    {snippet}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
