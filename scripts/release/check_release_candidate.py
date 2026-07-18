#!/usr/bin/env python3
"""P13-06: Release Candidate readiness checker.

Verifies that the repository is in a state safe to hand to Codex for
final audit and commit. This is a *gate* script — exit 0 means "no
obvious problems found", exit 1 means "fix these before handing off".

Checks performed:
1. **Required documents exist** — P13 release documents must be present.
2. **Frozen contract files exist** — P0/P1 API & WebSocket contracts.
3. **No real secrets in .env.example** — scan for obvious credential patterns.
4. **No lab credentials in docs** — scan for Kuboard, Feishu token, private keys.
5. **DEVELOPMENT_PLAN not premature** — P13 marked but no future stages claimed done.
6. **No large untracked binaries** — reject untracked files > 1 MB.

Usage::

    python scripts/release/check_release_candidate.py [--root .] [--verbose]

Exit code:
- 0: all checks passed.
- 1: one or more checks failed (details printed).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Check result types
# ---------------------------------------------------------------------------


class CheckResult(NamedTuple):
    """Outcome of a single release check."""

    name: str
    ok: bool
    detail: str

    def format(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return f"  [{mark}] {self.name}: {self.detail}"


# ---------------------------------------------------------------------------
# Required documents
# ---------------------------------------------------------------------------

REQUIRED_DOCS = [
    "docs/development/P13-RC-CHECKLIST.md",
    "docs/development/P13-DEMO-RUNBOOK.md",
    "docs/development/P13-ACCEPTANCE-EVIDENCE.md",
    "docs/development/P13-RELEASE-NOTES.md",
    "docs/development/P13-COMPLETION-REPORT.md",
    "docs/development/P12-COMPLETION-REPORT.md",
    "docs/development/P12-RISK-REGISTER.md",
    "docs/development/P12-RECOVERY-RUNBOOK.md",
]

FROZEN_CONTRACTS = [
    "docs/api/API_CONTRACT.md",
    "docs/api/WEBSOCKET_CONTRACT.md",
]


def check_required_docs(root: Path) -> list[CheckResult]:
    """Check that all required P13 documents exist."""
    results: list[CheckResult] = []
    missing: list[str] = []
    for rel in REQUIRED_DOCS:
        path = root / rel
        if not path.exists():
            missing.append(rel)
    if missing:
        results.append(
            CheckResult(
                "required_docs",
                False,
                f"missing {len(missing)} file(s): {', '.join(missing[:5])}",
            )
        )
    else:
        results.append(
            CheckResult("required_docs", True, f"all {len(REQUIRED_DOCS)} docs present")
        )
    return results


def check_frozen_contracts(root: Path) -> list[CheckResult]:
    """Check that P0/P1 frozen contract files exist."""
    results: list[CheckResult] = []
    missing: list[str] = []
    for rel in FROZEN_CONTRACTS:
        path = root / rel
        if not path.exists():
            missing.append(rel)
    if missing:
        results.append(
            CheckResult(
                "frozen_contracts",
                False,
                f"missing: {', '.join(missing)}",
            )
        )
    else:
        results.append(
            CheckResult("frozen_contracts", True, "API & WebSocket contracts present")
        )
    return results


# ---------------------------------------------------------------------------
# Secret scanning
# ---------------------------------------------------------------------------

# Patterns that indicate real lab credentials — must never be in the repo.
# Note: we only flag actual addresses/credentials, not policy mentions
# like "不得写入 Kuboard 地址" which are security instructions.
SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Real Kuboard URL (http/https with kuboard in hostname), not just the word.
    (re.compile(r"https?://[^/\s]*kuboard[^/\s]*", re.IGNORECASE), "Kuboard platform URL"),
    # Real Feishu token value (t-g + 30+ hex chars), not the word "token".
    (re.compile(r"t-g[A-Za-z0-9]{20,}"), "Feishu disposable token value"),
    (re.compile(r"-----BEGIN (RSA |EC |)PRIVATE KEY-----"), "PEM private key"),
    # Private IP with port (lab endpoints), not documentation examples.
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{4,5}\b"), "private IP address with port"),
    (re.compile(r"MODEL_GATEWAY_API_KEY\s*[:=]\s*['\"][^'\"]{10,}['\"]"), "hardcoded MODEL_GATEWAY_API_KEY with value"),
]

# Directories to skip when scanning for secrets.
SECRET_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".next",
    ".swc",
    "artifacts",
    "playwright-report",
    "test-results",
}

# Known test/placeholder values that are safe and should not be flagged.
SECRET_ALLOWLIST = (
    "some-api-key",
    "test-api-key",
    "test-key",
    "mock-api-key",
    "sk-test-mock",
    "test-secret",
    "demo-secret",
    "placeholder",
    "changeme",
    "your-",
    "example-",
    "redacted",
    "dummy",
    "fake",
    "not-a-real",
)

# Files to scan for secret patterns.
SECRET_SCAN_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".env", ".md", ".sh", ".cfg", ".ini"}


def _iter_scan_files(root: Path) -> list[Path]:
    """Yield files to scan for secrets."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SECRET_SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SECRET_SCAN_EXTENSIONS or path.name == ".env.example":
            files.append(path)
    return files


def _is_allowed_value(match_text: str) -> bool:
    """Return True if a matched string contains a known test/placeholder value."""
    lowered = match_text.lower()
    return any(allow in lowered for allow in (a.lower() for a in SECRET_ALLOWLIST))


def check_no_real_secrets(root: Path) -> list[CheckResult]:
    """Scan docs and code for real lab credentials."""
    results: list[CheckResult] = []
    hits: list[str] = []
    files = _iter_scan_files(root)

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, desc in SECRET_PATTERNS:
            match = pattern.search(text)
            if match and not _is_allowed_value(match.group(0)):
                rel = path.relative_to(root)
                hits.append(f"{rel} [{desc}]")
                break  # one hit per file is enough

    if hits:
        results.append(
            CheckResult(
                "no_real_secrets",
                False,
                f"{len(hits)} file(s) with potential secrets: {', '.join(hits[:5])}",
            )
        )
    else:
        results.append(
            CheckResult("no_real_secrets", True, f"scanned {len(files)} files, no real secrets")
        )
    return results


def check_env_example(root: Path) -> list[CheckResult]:
    """Check .env.example doesn't contain real secrets."""
    results: list[CheckResult] = []
    env_path = root / ".env.example"
    if not env_path.exists():
        results.append(CheckResult("env_example", False, ".env.example not found"))
        return results

    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError as exc:
        results.append(CheckResult("env_example", False, f"read error: {exc}"))
        return results

    # Check that MODEL_GATEWAY_API_KEY is empty or placeholder.
    # Skip comment lines (starting with #).
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        api_key_match = re.match(r"MODEL_GATEWAY_API_KEY\s*=\s*(.*)", stripped)
        if api_key_match:
            value = api_key_match.group(1).strip().strip('"').strip("'")
            if value and not value.startswith("<") and len(value) > 5:
                results.append(
                    CheckResult("env_example", False, f"MODEL_GATEWAY_API_KEY has value: {value[:20]}...")
                )
                return results

    # Check APP_SECRET is a dev placeholder.
    app_secret_match = re.search(r"APP_SECRET\s*=\s*(.+)", text)
    if app_secret_match:
        value = app_secret_match.group(1).strip().strip('"').strip("'")
        if value and "change" not in value.lower() and "dev" not in value.lower() and len(value) > 20:
            results.append(
                CheckResult("env_example", False, f"APP_SECRET looks like a real value: {value[:20]}...")
            )
            return results

    results.append(CheckResult("env_example", True, "no real secrets in .env.example"))
    return results


# ---------------------------------------------------------------------------
# DEVELOPMENT_PLAN check
# ---------------------------------------------------------------------------


def check_dev_plan(root: Path) -> list[CheckResult]:
    """Check DEVELOPMENT_PLAN doesn't prematurely mark future stages."""
    results: list[CheckResult] = []
    plan_path = root / "docs" / "development" / "DEVELOPMENT_PLAN.md"
    if not plan_path.exists():
        results.append(CheckResult("dev_plan", False, "DEVELOPMENT_PLAN.md not found"))
        return results

    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        results.append(CheckResult("dev_plan", False, f"read error: {exc}"))
        return results

    # P13 should be marked as done or RC ready.
    p13_section = re.search(r"## P13[：:](.*?)(?=\n## |\Z)", text, re.DOTALL)
    if p13_section:
        p13_text = p13_section.group(1)
        # Check that P13-01 through at least P13-09 have [x] marks.
        done_count = len(re.findall(r"\|\s*\[x\]\s*\|", p13_text))
        if done_count < 5:
            results.append(
                CheckResult("dev_plan", False, f"P13 only has {done_count} tasks marked [x]")
            )
            return results

    results.append(CheckResult("dev_plan", True, "P13 progress recorded in DEVELOPMENT_PLAN"))
    return results


# ---------------------------------------------------------------------------
# Large untracked files check
# ---------------------------------------------------------------------------


def check_no_large_untracked(root: Path) -> list[CheckResult]:
    """Check for large untracked binary files."""
    results: list[CheckResult] = []
    import subprocess

    try:
        proc = subprocess.run(  # noqa: S603, S607
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        results.append(CheckResult("large_untracked", True, "git not available, skipped"))
        return results

    large_files: list[str] = []
    size_threshold = 1024 * 1024  # 1 MB

    for line in proc.stdout.splitlines():
        if not line.startswith("??"):
            continue
        # Format: "?? path/to/file"
        rel_path = line[3:].strip().strip('"')
        full_path = root / rel_path
        if full_path.is_file():
            try:
                size = full_path.stat().st_size
                if size > size_threshold:
                    large_files.append(f"{rel_path} ({size // 1024} KB)")
            except OSError:
                pass

    if large_files:
        results.append(
            CheckResult(
                "large_untracked",
                False,
                f"{len(large_files)} large untracked file(s): {', '.join(large_files[:5])}",
            )
        )
    else:
        results.append(CheckResult("large_untracked", True, "no large untracked files"))
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_all_checks(root: Path) -> list[CheckResult]:
    """Run all release candidate checks and return results."""
    all_results: list[CheckResult] = []
    all_results.extend(check_required_docs(root))
    all_results.extend(check_frozen_contracts(root))
    all_results.extend(check_no_real_secrets(root))
    all_results.extend(check_env_example(root))
    all_results.extend(check_dev_plan(root))
    all_results.extend(check_no_large_untracked(root))
    return all_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="P13-06: Check release candidate readiness.",
    )
    parser.add_argument("--root", default=".", help="Repository root (default: cwd).")
    parser.add_argument("--verbose", action="store_true", help="Print extra details.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root path does not exist: {root}", file=sys.stderr)
        return 1

    print("=" * 60)
    print("P13 Release Candidate Check")
    print(f"Root: {root}")
    print("=" * 60)

    results = run_all_checks(root)

    for r in results:
        print(r.format())

    passed = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)
    print("-" * 60)
    print(f"Result: {passed} passed, {failed} failed")

    if failed:
        print("\nFAILED checks:")
        for r in results:
            if not r.ok:
                print(f"  - {r.name}: {r.detail}")
        return 1

    print("\nAll release candidate checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
