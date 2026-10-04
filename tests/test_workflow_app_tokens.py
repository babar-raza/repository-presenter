"""Least-privilege GitHub App installation tokens in the hosted workflows.

AGENTS.md "Security and Effects": the analysis token is repository-scoped and read-only; the write
credential exists only in a separate effect job, short-lived and target-scoped; a hosted write is
never inferred from a credential's presence. ``actions/create-github-app-token`` mints every App
token a workflow holds, and a mint step with no ``permission-*`` input inherits every permission the
App was installed with (contents, issues, pull_requests, administration write). So each mint step
must name exactly the permissions its job's steps use. Hosted YAML cannot run offline, so these
tests parse the workflow files themselves and, for the audit's exit condition, execute its report
step under bash with the GitHub expressions substituted.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from support import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
MINT_ACTION = "actions/create-github-app-token@"

# The minimum each job's steps need, read from those steps (see each workflow's header comments).
EXPECTED_MINT_PERMISSIONS: dict[str, list[dict[str, str]]] = {
    # The analysis clone (contents) and GET /repos/{owner}/{repo} plus the read client's contents,
    # trees and commits reads (metadata). No write scope anywhere in this job.
    "present.yml": [{"permission-contents": "read", "permission-metadata": "read"}],
    # The effect job: branch refs and contents writes (contents), open or refresh the presenter PR
    # (pull-requests). Nothing else: no issues, no administration.
    "propose.yml": [
        {
            "permission-contents": "write",
            "permission-metadata": "read",
            "permission-pull-requests": "write",
        }
    ],
    # One read-only GET /repos/{owner}/{repo} and nothing else.
    "verify-app-installation.yml": [{"permission-metadata": "read"}],
    "audit-app-installations.yml": [{"permission-metadata": "read"}],
    # The reachability probe is an anonymous git ls-remote. The drift leg (one per owner) mints one
    # read-only token narrowed to contents, and nothing else.
    "monitor.yml": [{"permission-contents": "read"}],
    # The scheduled upstream-issue workflow, one mint per target repository: the read-only analysis
    # (contents for the recheck reads, issues to find an existing marker, metadata); then, only in
    # the owner-gated file-and-close job, a read token of the same shape and a separate issues-write
    # token. No other write scope, no administration.
    "issues-scheduled.yml": [
        {"permission-contents": "read", "permission-issues": "read", "permission-metadata": "read"},
        {"permission-contents": "read", "permission-issues": "read", "permission-metadata": "read"},
        {"permission-issues": "write", "permission-metadata": "read"},
    ],
}

# The only workflows allowed to mint a write-scoped App token, and the write scopes each may hold.
ALLOWED_WRITE_SCOPES: dict[str, list[str]] = {
    "propose.yml": ["permission-contents", "permission-pull-requests"],
    "issues-scheduled.yml": ["permission-issues"],
}

EXPRESSION = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")


def _load(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{name} is not a YAML mapping"
    return loaded


def _mint_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith(MINT_ACTION)
    ]


def _granted(step: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in step["with"].items() if key.startswith("permission-")}


@pytest.mark.parametrize("name", sorted(EXPECTED_MINT_PERMISSIONS))
def test_every_workflow_parses_as_a_job_mapping(name: str) -> None:
    assert "jobs" in _load(name)


@pytest.mark.parametrize("name", sorted(EXPECTED_MINT_PERMISSIONS))
def test_mint_steps_request_exactly_the_permissions_their_job_uses(name: str) -> None:
    granted = [_granted(step) for step in _mint_steps(_load(name))]
    assert granted == EXPECTED_MINT_PERMISSIONS[name]


@pytest.mark.parametrize("name", [n for n, perms in EXPECTED_MINT_PERMISSIONS.items() if perms])
def test_every_mint_step_is_scoped_to_named_repositories(name: str) -> None:
    for step in _mint_steps(_load(name)):
        assert step["with"].get("repositories"), f"{name}: mint step has no repositories: scope"


def test_only_the_named_effect_jobs_hold_write_scoped_app_tokens() -> None:
    for name in EXPECTED_MINT_PERMISSIONS:
        allowed = ALLOWED_WRITE_SCOPES.get(name, [])
        for step in _mint_steps(_load(name)):
            writes = sorted(key for key, value in _granted(step).items() if value == "write")
            assert writes in ([], allowed), f"{name} mints an unexpected write scope: {writes}"


def _audit_report_script() -> str:
    steps = _load("audit-app-installations.yml")["jobs"]["check-installation"]["steps"]
    reports = [step for step in steps if "Report this organization" in str(step.get("name"))]
    assert len(reports) == 1
    return str(reports[0]["run"])


def _render(script: str, values: dict[str, str]) -> str:
    def substitute(match: re.Match[str]) -> str:
        expression = match.group(1)
        assert expression in values, f"unrendered workflow expression: {expression}"
        return values[expression]

    return EXPRESSION.sub(substitute, script)


def _posix_bash() -> str | None:
    """A POSIX shell for the audit's report step.

    On Windows a bare ``bash`` on PATH is usually the WSL launcher (``system32\\bash.EXE``), which
    runs its script inside a Linux distribution that may not exist, so it is not a POSIX shell for
    this host. Git for Windows ships the shell this project's own tooling uses; it is located from
    the ``git`` executable on PATH.
    """
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    if git is None:
        return None
    candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe"
    return str(candidate) if candidate.is_file() else None


def _run_audit_report(tmp_path: Path, outcome: str) -> subprocess.CompletedProcess[str]:
    bash = _posix_bash()
    if bash is None:
        pytest.skip("bash is not available to execute the audit's report step")
    script = _render(
        _audit_report_script(),
        {
            "steps.app-token.outcome": outcome,
            "matrix.owner": "acme-org",
            "matrix.repo": "acme-repo",
        },
    )
    env = {key: value for key, value in os.environ.items() if key != "GH_TOKEN"}
    env["GITHUB_STEP_SUMMARY"] = (tmp_path / "summary.md").as_posix()
    return subprocess.run(
        [bash, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_audit_leg_fails_and_names_the_org_when_the_app_is_not_installed(tmp_path: Path) -> None:
    result = _run_audit_report(tmp_path, outcome="failure")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "::error::acme-org" in result.stdout
    assert "NOT installed" in result.stdout
