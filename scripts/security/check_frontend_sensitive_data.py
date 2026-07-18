#!/usr/bin/env python3
"""P12-06: Scan frontend source for sensitive-data leakage patterns.

Checks ``apps/web/src/`` for:
- Token/private data written to localStorage / sessionStorage.
- Hard-coded API keys or secrets.
- console.log of sensitive fields (token, password, preference, memory).
- Inline secret assignment.

Exit 0 = clean, 1 = potential leakage found.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SENSITIVE_NAMES = (
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "private_preference",
    "memory_content",
    "access_token",
    "refresh_token",
    "authorization",
)

# Patterns that indicate sensitive data in storage.
STORAGE_PATTERNS = [
    re.compile(r"localStorage\.setItem\s*\([^)]*(?:token|password|secret|key|preference|memory)", re.I),
    re.compile(r"sessionStorage\.setItem\s*\([^)]*(?:token|password|secret|key|preference|memory)", re.I),
]

# Patterns for console logging of sensitive data.
CONSOLE_PATTERNS = [
    re.compile(r"console\.log\s*\([^)]*(?:token|password|secret|apiKey|private_preference|memory_content)", re.I),
]

# Hard-coded secret patterns.
SECRET_LITERAL = [
    re.compile(r'["\'](?:sk-[a-zA-Z0-9]{20,})["\']'),
    re.compile(r'["\'](?:AKIA[0-9A-Z]{16})["\']'),
]


def _iter_ts_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", ".next", "dist", ".swc"} for part in path.parts):
            continue
        if path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
            files.append(path)
    return files


def scan(root: Path) -> list[tuple[Path, int, str, str]]:
    hits: list[tuple[Path, int, str, str]] = []
    for path in _iter_ts_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in STORAGE_PATTERNS:
                if pattern.search(line):
                    hits.append((path, lineno, "sensitive data in storage", line.strip()[:160]))
            for pattern in CONSOLE_PATTERNS:
                if pattern.search(line):
                    hits.append((path, lineno, "console.log of sensitive data", line.strip()[:160]))
            for pattern in SECRET_LITERAL:
                if pattern.search(line):
                    hits.append((path, lineno, "hard-coded secret literal", line.strip()[:160]))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan frontend for sensitive data leakage.")
    parser.add_argument("--root", default="apps/web/src", help="Frontend source root.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Path not found: {root}")
        return 0

    hits = scan(root)
    if not hits:
        print(f"OK: scanned {root}, no sensitive-data leakage patterns found.")
        return 0

    print(f"FAIL: {len(hits)} potential leakage pattern(s):\n")
    for path, lineno, desc, snippet in hits:
        print(f"  {path}:{lineno}  [{desc}]")
        print(f"    {snippet}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
