#!/usr/bin/env python3
"""P13-05: Release evidence collector.

Collects machine-checkable evidence that can be pasted into a Codex audit
review. Each command is executed in a subprocess, its exit code and a
short summary are recorded. The script never swallows failures — every
command's real outcome is captured.

Evidence collected:
- ``git status --short --branch``  (working tree state)
- ``git log -1 --oneline``         (baseline commit)
- ``git diff HEAD --check``        (whitespace/conflict markers)
- ``pip check``                    (dependency conflicts)
- ``ruff check``                   (lint)
- ``mypy``                         (type check)
- ``pytest`` summary               (test count)
- ``pnpm lint/typecheck/test/build`` summaries (frontend quality)
- Docker / gitleaks availability
- P12 risk register summary

Usage::

    conda run -n CampusAgent python scripts/release/collect_evidence.py [--root .] [--json] [--output artifacts/release-evidence/]

Exit code:
- 0 if all commands ran (regardless of individual pass/fail).
- 1 only if the script itself failed to run (e.g. bad root path).

The script writes a Markdown report and an optional JSON file. Individual
command failures are recorded in the report, not masked.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


class CommandResult:
    """Outcome of a single evidence command."""

    def __init__(
        self,
        name: str,
        command: str,
        returncode: int,
        stdout: str,
        stderr: str,
        duration_s: float,
    ) -> None:
        self.name = name
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_s = duration_s
        self.skipped = False
        self.skip_reason = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def mark_skipped(self, reason: str) -> None:
        self.skipped = True
        self.skip_reason = reason
        self.returncode = -1

    def summary(self, max_lines: int = 5) -> str:
        """Return a short human-readable summary of the output."""
        if self.skipped:
            return f"SKIPPED: {self.skip_reason}"
        source = self.stdout if self.stdout else self.stderr
        lines = [ln for ln in source.strip().splitlines() if ln.strip()]
        if not lines:
            return f"(no output, exit={self.returncode})"
        tail = lines[-max_lines:]
        return "\n".join(tail)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "returncode": self.returncode,
            "ok": self.ok,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "duration_s": round(self.duration_s, 2),
            "stdout_tail": self.summary(),
        }


def run_command(
    name: str,
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a subprocess and capture its result. Never raises."""
    import time

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    start = time.monotonic()
    try:
        proc = subprocess.run(  # noqa: S603 — args is controlled by this script
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
        )
        duration = time.monotonic() - start
        return CommandResult(
            name=name,
            command=" ".join(args),
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_s=duration,
        )
    except FileNotFoundError:
        duration = time.monotonic() - start
        result = CommandResult(name, " ".join(args), 127, "", "command not found", duration)
        result.mark_skipped("executable not found")
        return result
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        result = CommandResult(
            name,
            " ".join(args),
            124,
            exc.stdout or "",
            f"timeout after {timeout}s",
            duration,
        )
        return result


def check_tool_available(tool: str) -> bool:
    """Return True if a CLI tool is on PATH."""
    return shutil.which(tool) is not None


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------


def collect_git_evidence(root: Path) -> list[CommandResult]:
    """Collect git-related evidence."""
    results: list[CommandResult] = []

    results.append(
        run_command("git_status", ["git", "status", "--short", "--branch"], cwd=root, timeout=30)
    )
    results.append(
        run_command("git_log", ["git", "log", "-1", "--oneline"], cwd=root, timeout=30)
    )
    results.append(
        run_command("git_diff_check", ["git", "diff", "HEAD", "--check"], cwd=root, timeout=60)
    )
    return results


def collect_python_evidence(root: Path) -> list[CommandResult]:
    """Collect Python/backend evidence via conda run."""
    conda = shutil.which("conda")
    if not conda:
        result = CommandResult("pip_check", "conda", 127, "", "conda not found", 0.0)
        result.mark_skipped("conda not found")
        return [result]

    api_dir = root / "apps" / "api"
    results: list[CommandResult] = []

    results.append(
        run_command(
            "pip_check",
            ["conda", "run", "-n", "CampusAgent", "pip", "check"],
            cwd=root,
            timeout=120,
        )
    )
    results.append(
        run_command(
            "ruff_check",
            ["conda", "run", "-n", "CampusAgent", "ruff", "check", "apps/api", "--no-cache"],
            cwd=root,
            timeout=120,
        )
    )
    results.append(
        run_command(
            "mypy",
            [
                "conda",
                "run",
                "-n",
                "CampusAgent",
                "mypy",
                "apps/api/src",
                "apps/api/tests",
                "--no-incremental",
            ],
            cwd=root,
            timeout=300,
        )
    )
    results.append(
        run_command(
            "pytest",
            [
                "conda",
                "run",
                "-n",
                "CampusAgent",
                "python",
                "-m",
                "pytest",
                "apps/api/tests",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            cwd=root,
            timeout=600,
        )
    )
    return results


def collect_frontend_evidence(root: Path) -> list[CommandResult]:
    """Collect frontend evidence via corepack pnpm."""
    corepack = shutil.which("corepack")
    if not corepack:
        result = CommandResult("pnpm_lint", "corepack", 127, "", "corepack not found", 0.0)
        result.mark_skipped("corepack not found")
        return [result]

    results: list[CommandResult] = []
    for name, subcmd in [
        ("pnpm_lint", ["lint"]),
        ("pnpm_typecheck", ["typecheck"]),
        ("pnpm_test", ["test"]),
    ]:
        results.append(
            run_command(
                name,
                ["corepack", "pnpm", *subcmd],
                cwd=root,
                timeout=300,
            )
        )
    results.append(
        run_command(
            "pnpm_build",
            ["corepack", "pnpm", "--filter", "@campus-agent/web", "build"],
            cwd=root,
            timeout=300,
        )
    )
    return results


def collect_tooling_evidence(root: Path) -> list[CommandResult]:
    """Check availability of Docker and gitleaks."""
    results: list[CommandResult] = []

    if check_tool_available("docker"):
        results.append(
            run_command("docker_config", ["docker", "compose", "config"], cwd=root, timeout=60)
        )
    else:
        r = CommandResult("docker_config", "docker compose config", 127, "", "", 0.0)
        r.mark_skipped("docker not available")
        results.append(r)

    if check_tool_available("gitleaks"):
        results.append(
            run_command(
                "gitleaks",
                [
                    "gitleaks",
                    "detect",
                    "--source",
                    ".",
                    "--redact",
                    "--verbose",
                    "--no-banner",
                ],
                cwd=root,
                timeout=120,
            )
        )
    else:
        r = CommandResult("gitleaks", "gitleaks detect", 127, "", "", 0.0)
        r.mark_skipped("gitleaks not available")
        results.append(r)

    return results


def collect_demo_evidence(root: Path) -> list[CommandResult]:
    """Run the demo smoke test."""
    conda = shutil.which("conda")
    if not conda:
        r = CommandResult("demo_smoke", "conda", 127, "", "conda not found", 0.0)
        r.mark_skipped("conda not found")
        return [r]

    return [
        run_command(
            "demo_smoke",
            ["conda", "run", "-n", "CampusAgent", "python", "scripts/demo/run_demo_smoke.py"],
            cwd=root,
            timeout=120,
        )
    ]


def collect_risk_register_summary(root: Path) -> CommandResult:
    """Extract a brief summary from the P12 risk register."""
    risk_file = root / "docs" / "development" / "P12-RISK-REGISTER.md"
    if not risk_file.exists():
        r = CommandResult("risk_register", str(risk_file), 1, "", "file not found", 0.0)
        r.mark_skipped("P12-RISK-REGISTER.md not found")
        return r

    try:
        text = risk_file.read_text(encoding="utf-8")
    except OSError as exc:
        r = CommandResult("risk_register", str(risk_file), 1, "", str(exc), 0.0)
        return r

    # Extract the statistics line.
    stats_match = re.search(r"\*\*统计\*\*[：:]\s*(.+)", text)
    blocker_match = re.search(r"\*\*阻塞项\*\*[：:]\s*(.+)", text)
    stats = stats_match.group(1).strip() if stats_match else "(not found)"
    blocker = blocker_match.group(1).strip() if blocker_match else "(not found)"
    summary = f"stats: {stats} | blocker: {blocker}"
    return CommandResult("risk_register", str(risk_file), 0, summary, "", 0.0)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_markdown_report(
    all_results: list[CommandResult],
    root: Path,
) -> str:
    """Generate a Markdown evidence report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = []
    lines.append("# P13 Release Evidence Report")
    lines.append("")
    lines.append(f"- **Generated**: {now}")
    lines.append(f"- **Root**: `{root}`")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Command | Status | Exit | Duration (s) |")
    lines.append("|---|---|---|---|")
    for r in all_results:
        if r.skipped:
            status = "SKIPPED"
        elif r.ok:
            status = "PASS"
        else:
            status = "FAIL"
        lines.append(f"| {r.name} | {status} | {r.returncode} | {r.duration_s:.1f} |")
    lines.append("")

    # Pass/fail counts
    passed = sum(1 for r in all_results if r.ok)
    failed = sum(1 for r in all_results if not r.ok and not r.skipped)
    skipped = sum(1 for r in all_results if r.skipped)
    lines.append(f"**Totals**: {passed} passed, {failed} failed, {skipped} skipped")
    lines.append("")

    # Detailed output
    lines.append("## Detailed Output")
    lines.append("")
    for r in all_results:
        lines.append(f"### {r.name}")
        lines.append("")
        if r.skipped:
            lines.append(f"- **Status**: SKIPPED — {r.skip_reason}")
        else:
            lines.append(f"- **Command**: `{r.command}`")
            lines.append(f"- **Exit code**: {r.returncode}")
            lines.append(f"- **Status**: {'PASS' if r.ok else 'FAIL'}")
            lines.append(f"- **Duration**: {r.duration_s:.2f}s")
        lines.append("")
        summary = r.summary()
        if summary:
            lines.append("```")
            lines.append(summary)
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def generate_json_report(all_results: list[CommandResult], root: Path) -> dict[str, Any]:
    """Generate a JSON evidence report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    passed = sum(1 for r in all_results if r.ok)
    failed = sum(1 for r in all_results if not r.ok and not r.skipped)
    skipped = sum(1 for r in all_results if r.skipped)
    return {
        "generated_at": now,
        "root": str(root),
        "summary": {
            "total": len(all_results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "results": [r.to_dict() for r in all_results],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="P13-05: Collect release evidence for Codex audit.",
    )
    parser.add_argument("--root", default=".", help="Repository root (default: cwd).")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument(
        "--output",
        default="artifacts/release-evidence",
        help="Output directory for report files (default: artifacts/release-evidence).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: root path does not exist: {root}", file=sys.stderr)
        return 1

    print(f"Collecting release evidence from {root} ...", file=sys.stderr)

    all_results: list[CommandResult] = []
    all_results.extend(collect_git_evidence(root))
    all_results.extend(collect_python_evidence(root))
    all_results.extend(collect_frontend_evidence(root))
    all_results.extend(collect_tooling_evidence(root))
    all_results.extend(collect_demo_evidence(root))
    all_results.append(collect_risk_register_summary(root))

    # Print to stdout.
    if args.json:
        report = generate_json_report(all_results, root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(generate_markdown_report(all_results, root))

    # Also write files to the output directory.
    out_dir = root / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "evidence.md"
    json_path = out_dir / "evidence.json"
    md_path.write_text(generate_markdown_report(all_results, root), encoding="utf-8")
    json_path.write_text(
        json.dumps(generate_json_report(all_results, root), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nEvidence written to {md_path} and {json_path}", file=sys.stderr)

    # Exit 0 as long as the script ran — individual command failures are in the report.
    return 0


if __name__ == "__main__":
    sys.exit(main())
