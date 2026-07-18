"""P13-05/P13-06: Unit tests for release candidate scripts.

Tests the command runner in ``collect_evidence.py`` and the check
functions in ``check_release_candidate.py``. Covers success, failure,
command-missing, secret-pattern-hit, and normal-path-return-0 scenarios
as required by the P13 implementation guide.

The scripts live in ``scripts/release/`` outside the ``apps/api`` package,
so we load them dynamically via ``importlib``.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Dynamic module loading
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_RELEASE = _REPO_ROOT / "scripts" / "release"


def _load_module(module_name: str, file_path: Path):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_collect_evidence = _load_module(
    "collect_evidence", _SCRIPTS_RELEASE / "collect_evidence.py"
)
_check_rc = _load_module(
    "check_release_candidate", _SCRIPTS_RELEASE / "check_release_candidate.py"
)

CommandResult = _collect_evidence.CommandResult
run_command = _collect_evidence.run_command
check_tool_available = _collect_evidence.check_tool_available

CheckResult = _check_rc.CheckResult
check_required_docs = _check_rc.check_required_docs
check_frozen_contracts = _check_rc.check_frozen_contracts
check_no_real_secrets = _check_rc.check_no_real_secrets
check_env_example = _check_rc.check_env_example
check_dev_plan = _check_rc.check_dev_plan
check_no_large_untracked = _check_rc.check_no_large_untracked
run_all_checks = _check_rc.run_all_checks


# ===========================================================================
# collect_evidence.py — CommandResult tests
# ===========================================================================


class TestCommandResult:
    """Test the CommandResult data class."""

    def test_success(self) -> None:
        r = CommandResult("test", "echo hello", 0, "hello\n", "", 0.1)
        assert r.ok is True
        assert r.skipped is False
        assert r.name == "test"
        assert r.returncode == 0

    def test_failure(self) -> None:
        r = CommandResult("test", "false", 1, "", "error\n", 0.1)
        assert r.ok is False
        assert r.skipped is False
        assert r.returncode == 1

    def test_mark_skipped(self) -> None:
        r = CommandResult("test", "missing-cmd", 0, "", "", 0.0)
        r.mark_skipped("executable not found")
        assert r.skipped is True
        assert r.skip_reason == "executable not found"
        assert r.ok is False
        assert r.returncode == -1

    def test_summary_from_stdout(self) -> None:
        r = CommandResult("test", "cmd", 0, "line1\nline2\nline3\n", "", 0.1)
        summary = r.summary(max_lines=2)
        assert "line2" in summary
        assert "line3" in summary
        assert "line1" not in summary

    def test_summary_from_stderr_when_stdout_empty(self) -> None:
        r = CommandResult("test", "cmd", 1, "", "error details\n", 0.1)
        summary = r.summary()
        assert "error details" in summary

    def test_summary_no_output(self) -> None:
        r = CommandResult("test", "cmd", 0, "", "", 0.1)
        summary = r.summary()
        assert "no output" in summary
        assert "0" in summary  # exit code

    def test_summary_skipped(self) -> None:
        r = CommandResult("test", "cmd", 0, "", "", 0.0)
        r.mark_skipped("not available")
        summary = r.summary()
        assert "SKIPPED" in summary
        assert "not available" in summary

    def test_to_dict(self) -> None:
        r = CommandResult("test", "echo hi", 0, "hi\n", "", 0.5)
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["command"] == "echo hi"
        assert d["returncode"] == 0
        assert d["ok"] is True
        assert d["skipped"] is False
        assert d["duration_s"] == 0.5


# ===========================================================================
# collect_evidence.py — run_command tests
# ===========================================================================


class TestRunCommand:
    """Test the run_command function."""

    def test_success(self, tmp_path: Path) -> None:
        r = run_command("echo_test", ["echo", "hello"], cwd=tmp_path, timeout=10)
        assert r.ok is True
        assert r.returncode == 0
        assert "hello" in r.stdout

    def test_failure(self, tmp_path: Path) -> None:
        r = run_command(
            "false_test", ["false"], cwd=tmp_path, timeout=10
        )
        assert r.ok is False
        assert r.returncode != 0

    def test_command_not_found(self, tmp_path: Path) -> None:
        r = run_command(
            "missing_cmd",
            ["this-command-does-not-exist-12345"],
            cwd=tmp_path,
            timeout=10,
        )
        assert r.skipped is True
        assert "not found" in r.skip_reason.lower()
        assert r.ok is False

    def test_timeout(self, tmp_path: Path) -> None:
        # Use Python to sleep longer than the timeout.
        r = run_command(
            "sleep_test",
            ["python3", "-c", "import time; time.sleep(10)"],
            cwd=tmp_path,
            timeout=1,
        )
        assert r.ok is False
        assert "timeout" in r.stderr.lower()

    def test_env_override(self, tmp_path: Path) -> None:
        r = run_command(
            "env_test",
            ["python3", "-c", "import os; print(os.environ.get('MY_TEST_VAR', 'unset'))"],
            cwd=tmp_path,
            timeout=10,
            env={"MY_TEST_VAR": "set-value"},
        )
        assert r.ok is True
        assert "set-value" in r.stdout


# ===========================================================================
# collect_evidence.py — check_tool_available tests
# ===========================================================================


class TestCheckToolAvailable:
    """Test the check_tool_available function."""

    def test_existing_tool(self) -> None:
        # 'python3' should always be available.
        assert check_tool_available("python3") is True

    def test_nonexistent_tool(self) -> None:
        assert check_tool_available("this-tool-does-not-exist-xyz") is False


# ===========================================================================
# check_release_candidate.py — CheckResult tests
# ===========================================================================


class TestCheckResultFormat:
    """Test the CheckResult NamedTuple."""

    def test_pass_format(self) -> None:
        r = CheckResult("test", True, "all good")
        formatted = r.format()
        assert "[PASS]" in formatted
        assert "test" in formatted
        assert "all good" in formatted

    def test_fail_format(self) -> None:
        r = CheckResult("test", False, "something wrong")
        formatted = r.format()
        assert "[FAIL]" in formatted
        assert "something wrong" in formatted


# ===========================================================================
# check_release_candidate.py — check_required_docs tests
# ===========================================================================


class TestCheckRequiredDocs:
    """Test check_required_docs with temporary directories."""

    def test_all_present(self, tmp_path: Path) -> None:
        for rel in _check_rc.REQUIRED_DOCS:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# placeholder\n", encoding="utf-8")
        results = check_required_docs(tmp_path)
        assert len(results) == 1
        assert results[0].ok is True
        assert "all" in results[0].detail

    def test_missing_files(self, tmp_path: Path) -> None:
        # Don't create any files — all should be missing.
        results = check_required_docs(tmp_path)
        assert len(results) == 1
        assert results[0].ok is False
        assert "missing" in results[0].detail.lower()

    def test_partial_missing(self, tmp_path: Path) -> None:
        # Create only the first required doc.
        first = _check_rc.REQUIRED_DOCS[0]
        path = tmp_path / first
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# placeholder\n", encoding="utf-8")
        results = check_required_docs(tmp_path)
        assert results[0].ok is False
        assert "missing" in results[0].detail.lower()


# ===========================================================================
# check_release_candidate.py — check_frozen_contracts tests
# ===========================================================================


class TestCheckFrozenContracts:
    """Test check_frozen_contracts."""

    def test_present(self, tmp_path: Path) -> None:
        for rel in _check_rc.FROZEN_CONTRACTS:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# contract\n", encoding="utf-8")
        results = check_frozen_contracts(tmp_path)
        assert len(results) == 1
        assert results[0].ok is True

    def test_missing(self, tmp_path: Path) -> None:
        results = check_frozen_contracts(tmp_path)
        assert len(results) == 1
        assert results[0].ok is False
        assert "missing" in results[0].detail.lower()


# ===========================================================================
# check_release_candidate.py — check_no_real_secrets tests
# ===========================================================================


class TestCheckNoRealSecrets:
    """Test check_no_real_secrets detects real credential patterns."""

    def test_clean_repo(self, tmp_path: Path) -> None:
        # Create a clean .py file.
        (tmp_path / "code.py").write_text(
            "x = 'some-api-key'\n", encoding="utf-8"
        )
        results = check_no_real_secrets(tmp_path)
        assert len(results) == 1
        assert results[0].ok is True

    def test_detects_kuboard_url(self, tmp_path: Path) -> None:
        # Construct at runtime to avoid static secret scanners.
        url = "https://" + "kuboard" + ".example.com:8080"
        (tmp_path / "config.py").write_text(
            f'url = "{url}"\n',
            encoding="utf-8",
        )
        results = check_no_real_secrets(tmp_path)
        assert results[0].ok is False
        assert "Kuboard" in results[0].detail

    def test_detects_feishu_token(self, tmp_path: Path) -> None:
        # Construct at runtime to avoid static secret scanners.
        token = "t-g" + ("A" * 25)
        (tmp_path / "config.py").write_text(
            f'token = "{token}"\n',
            encoding="utf-8",
        )
        results = check_no_real_secrets(tmp_path)
        assert results[0].ok is False
        assert "Feishu" in results[0].detail

    def test_detects_private_key(self, tmp_path: Path) -> None:
        # Construct at runtime to avoid static secret scanners.
        pem_header = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
        pem_footer = "-----END " + "RSA " + "PRIVATE KEY-----"
        (tmp_path / "keys.py").write_text(
            f"{pem_header}\nfake\n{pem_footer}\n",
            encoding="utf-8",
        )
        results = check_no_real_secrets(tmp_path)
        assert results[0].ok is False
        assert "private key" in results[0].detail.lower()

    def test_detects_private_ip_with_port(self, tmp_path: Path) -> None:
        # Construct at runtime to avoid static secret scanners.
        ip = "10." + "0.1.5:8080"
        (tmp_path / "config.py").write_text(
            f'endpoint = "{ip}"\n',
            encoding="utf-8",
        )
        results = check_no_real_secrets(tmp_path)
        assert results[0].ok is False
        assert "private ip" in results[0].detail.lower()

    def test_allowlist_not_flagged(self, tmp_path: Path) -> None:
        """Values containing allowlist keywords should not be flagged."""
        (tmp_path / "code.py").write_text(
            'key = "test-api-key-1234567890"\n',
            encoding="utf-8",
        )
        results = check_no_real_secrets(tmp_path)
        assert results[0].ok is True

    def test_skips_directories(self, tmp_path: Path) -> None:
        """Files in skip directories should not be scanned."""
        skip_dir = tmp_path / ".git"
        skip_dir.mkdir()
        # Construct at runtime to avoid static secret scanners.
        url = "https://" + "kuboard" + ".evil.com:8080"
        (skip_dir / "config.py").write_text(
            f'url = "{url}"\n',
            encoding="utf-8",
        )
        results = check_no_real_secrets(tmp_path)
        assert results[0].ok is True


# ===========================================================================
# check_release_candidate.py — check_env_example tests
# ===========================================================================


class TestCheckEnvExample:
    """Test check_env_example."""

    def test_clean_env(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text(
            textwrap.dedent("""\
                APP_SECRET=dev-secret-key-change-in-production
                MODEL_GATEWAY_API_KEY=
                ENABLE_EXTERNAL_MODEL=false
            """),
            encoding="utf-8",
        )
        results = check_env_example(tmp_path)
        assert len(results) == 1
        assert results[0].ok is True

    def test_missing_env_file(self, tmp_path: Path) -> None:
        results = check_env_example(tmp_path)
        assert len(results) == 1
        assert results[0].ok is False
        assert "not found" in results[0].detail.lower()

    def test_real_api_key(self, tmp_path: Path) -> None:
        fake_key = "sk-" + "real-key-1234567890abcdef"
        (tmp_path / ".env.example").write_text(
            f"MODEL_GATEWAY_API_KEY={fake_key}\n",
            encoding="utf-8",
        )
        results = check_env_example(tmp_path)
        assert results[0].ok is False
        assert "MODEL_GATEWAY_API_KEY" in results[0].detail

    def test_placeholder_api_key(self, tmp_path: Path) -> None:
        (tmp_path / ".env.example").write_text(
            "MODEL_GATEWAY_API_KEY=<your-key-here>\n",
            encoding="utf-8",
        )
        results = check_env_example(tmp_path)
        assert results[0].ok is True

    def test_commented_api_key(self, tmp_path: Path) -> None:
        fake_key = "sk-" + "real-key-1234567890abcdef"
        (tmp_path / ".env.example").write_text(
            f"# MODEL_GATEWAY_API_KEY={fake_key}\n",
            encoding="utf-8",
        )
        results = check_env_example(tmp_path)
        assert results[0].ok is True


# ===========================================================================
# check_release_candidate.py — check_dev_plan tests
# ===========================================================================


class TestCheckDevPlan:
    """Test check_dev_plan."""

    def test_missing_file(self, tmp_path: Path) -> None:
        results = check_dev_plan(tmp_path)
        assert len(results) == 1
        assert results[0].ok is False
        assert "not found" in results[0].detail.lower()

    def test_correct_p13_progress(self, tmp_path: Path) -> None:
        plan_dir = tmp_path / "docs" / "development"
        plan_dir.mkdir(parents=True)
        (plan_dir / "DEVELOPMENT_PLAN.md").write_text(
            textwrap.dedent("""\
                ## P13: Release Candidate

                | [x] | P13-01 | Task 1 |
                | [x] | P13-02 | Task 2 |
                | [x] | P13-03 | Task 3 |
                | [x] | P13-04 | Task 4 |
                | [x] | P13-05 | Task 5 |
                | [x] | P13-06 | Task 6 |
            """),
            encoding="utf-8",
        )
        results = check_dev_plan(tmp_path)
        assert results[0].ok is True

    def test_insufficient_progress(self, tmp_path: Path) -> None:
        plan_dir = tmp_path / "docs" / "development"
        plan_dir.mkdir(parents=True)
        (plan_dir / "DEVELOPMENT_PLAN.md").write_text(
            textwrap.dedent("""\
                ## P13: Release Candidate

                | [x] | P13-01 | Task 1 |
                | [ ] | P13-02 | Task 2 |
                | [ ] | P13-03 | Task 3 |
            """),
            encoding="utf-8",
        )
        results = check_dev_plan(tmp_path)
        assert results[0].ok is False
        assert "only" in results[0].detail.lower()


# ===========================================================================
# check_release_candidate.py — check_no_large_untracked tests
# ===========================================================================


class TestCheckNoLargeUntracked:
    """Test check_no_large_untracked."""

    def test_no_large_files(self, tmp_path: Path) -> None:
        """With no git repo, should return ok (git not available or no files)."""
        results = check_no_large_untracked(tmp_path)
        # In a non-git directory, git status will fail — the function
        # catches the exception and returns ok=True with "skipped".
        assert len(results) == 1

    @patch("subprocess.run")
    def test_large_file_detected(
        self, mock_run, tmp_path: Path
    ) -> None:
        """Simulate a large untracked file."""
        large_file = tmp_path / "big.bin"
        large_file.write_bytes(b"\x00" * (2 * 1024 * 1024))  # 2 MB

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "?? big.bin\n"

        results = check_no_large_untracked(tmp_path)
        assert results[0].ok is False
        assert "large" in results[0].detail.lower()

    @patch("subprocess.run")
    def test_no_large_untracked_files(
        self, mock_run, tmp_path: Path
    ) -> None:
        """Simulate no large untracked files."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""

        results = check_no_large_untracked(tmp_path)
        assert results[0].ok is True


# ===========================================================================
# check_release_candidate.py — run_all_checks integration test
# ===========================================================================


class TestRunAllChecks:
    """Integration test for run_all_checks."""

    def test_returns_list_of_results(self, tmp_path: Path) -> None:
        results = run_all_checks(tmp_path)
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, CheckResult)
            assert hasattr(r, "name")
            assert hasattr(r, "ok")
            assert hasattr(r, "detail")
