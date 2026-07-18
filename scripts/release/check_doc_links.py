#!/usr/bin/env python3
"""P13-09: Check internal document links.

Scans README.md, docs/**/*.md, and development-logs/**/*.md for broken
internal (relative path) links. External links and pure anchors are
skipped. Exit 0 if no broken links, exit 1 if any are found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCAN_GLOBS = ["README.md", "docs/**/*.md", "development-logs/**/*.md"]
SKIP_DIRS = {
    ".git", "node_modules", ".next", ".mypy_cache",
    ".ruff_cache", "__pycache__",
}


def main() -> int:
    md_files: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for f in ROOT.glob(pattern):
            if f.is_file() and not any(s in f.parts for s in SKIP_DIRS):
                md_files.add(f)

    md_files_sorted = sorted(md_files)
    print(f"Scanning {len(md_files_sorted)} Markdown files...")

    stats = {"total": 0, "valid": 0, "broken": 0, "external": 0, "anchor": 0}
    broken: list[dict[str, str]] = []

    for md_file in md_files_sorted:
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as e:
            print(f"  WARN: cannot read {md_file}: {e}")
            continue

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        for text, url in links:
            stats["total"] += 1

            if url.startswith(("http://", "https://", "mailto:")):
                stats["external"] += 1
                continue

            if url.startswith("#"):
                stats["anchor"] += 1
                stats["valid"] += 1
                continue

            path_part = url.split("#")[0]
            if not path_part:
                stats["anchor"] += 1
                stats["valid"] += 1
                continue

            if path_part.startswith("/"):
                target = ROOT / path_part.lstrip("/")
            else:
                target = (md_file.parent / path_part).resolve()

            if target.exists():
                stats["valid"] += 1
            else:
                stats["broken"] += 1
                broken.append({
                    "source": str(md_file.relative_to(ROOT)),
                    "text": text[:50],
                    "url": url[:80],
                    "target": str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target)[:80],
                })

    print()
    print("=" * 70)
    print("Document Link Check Report")
    print("=" * 70)
    print(f"Total links:    {stats['total']}")
    print(f"Valid links:    {stats['valid']}")
    print(f"Broken links:   {stats['broken']}")
    print(f"External links: {stats['external']} (skipped)")
    print(f"Anchor links:   {stats['anchor']}")
    print()

    if broken:
        print(f"BROKEN LINKS ({len(broken)}):")
        for i, link in enumerate(broken, 1):
            print(f"  {i}. [{link['source']}] -> [{link['text']}]({link['url']})")
            print(f"     target: {link['target']}")
        return 1
    else:
        print("All internal links are valid!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
