"""The unattended upstream-issue workflow (``.github/workflows/issues-scheduled.yml``).

Hosted YAML cannot run offline, so these tests parse the file and pin the properties AGENTS.md
"Security and Effects" makes non-negotiable for it: a read-only analysis path that never holds the
write credential; a write path that runs only when the owner's repository variable is set to
``1``; a write token minted per target repository with the issues permission alone; and no
ambient write credential anywhere else.
"""

from __future__ import annotations

from typing import Any

import yaml

from support import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "issues-scheduled.yml"
GATE_VARIABLE = "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED"
WRITE_TOKEN = "GH_ISSUES_WRITE_TOKEN"
MINT = "actions/create-github-app-token@"


def _workflow() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _jobs() -> dict[str, dict[str, Any]]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    return steps


def _text(value: object) -> str:
    return yaml.safe_dump(value, sort_keys=True)


def test_the_workflow_is_scheduled_and_manually_dispatchable() -> None:
    # PyYAML (YAML 1.1) parses the bare `on:` key as the boolean True.
    loaded = _workflow()
    triggers = loaded["on"] if "on" in loaded else loaded[True]
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers


def test_the_top_level_grant_is_read_only() -> None:
    assert _workflow()["permissions"] == {"contents": "read"}


def test_no_job_widens_the_top_level_grant() -> None:
    for name, job in _jobs().items():
        assert "permissions" not in job or job["permissions"] == {"contents": "read"}, name


def test_the_write_path_is_gated_on_the_owner_repository_variable() -> None:
    write_jobs = [
        name for name, job in _jobs().items() if WRITE_TOKEN in _text(job.get("steps", []))
    ]
    assert write_jobs, "the workflow must contain a write job"
    for name in write_jobs:
        condition = str(_jobs()[name].get("if", ""))
        assert "vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED == '1'" in condition, name


def test_the_write_token_appears_in_no_read_only_job() -> None:
    for name, job in _jobs().items():
        if "vars.REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED" in str(job.get("if", "")):
            continue
        text = _text(job)
        assert WRITE_TOKEN not in text, name
        assert GATE_VARIABLE not in text, name


def test_the_gate_is_set_as_a_literal_only_on_the_step_that_writes() -> None:
    for name, job in _jobs().items():
        for step in _steps(job):
            env = step.get("env") or {}
            if GATE_VARIABLE in env:
                assert env[GATE_VARIABLE] == "1", f"{name}: gate must be the literal 1"
                assert WRITE_TOKEN in env, f"{name}: the gate and the write token share one step"


def test_every_mint_step_is_scoped_to_its_one_target_repository() -> None:
    for name, job in _jobs().items():
        for step in _steps(job):
            if str(step.get("uses", "")).startswith(MINT):
                assert step["with"]["repositories"] == "${{ matrix.target.name }}", name
                assert step["with"]["owner"] == "${{ matrix.target.owner }}", name


def test_the_write_token_requests_issues_write_and_no_other_write_scope() -> None:
    mints = [
        step["with"]
        for step in _steps(_jobs()["file-and-close"])
        if str(step.get("uses", "")).startswith(MINT)
    ]
    write_grants = [{k: v for k, v in grant.items() if str(v) == "write"} for grant in mints]
    assert {"permission-issues": "write"} in write_grants
    assert [w for w in write_grants if w] == [{"permission-issues": "write"}]


def test_the_analysis_path_never_requests_write_scope() -> None:
    for step in _steps(_jobs()["analyse"]):
        if str(step.get("uses", "")).startswith(MINT):
            assert "write" not in {str(v) for v in step["with"].values()}


def test_the_write_job_does_not_wait_on_analysis_so_one_failure_cannot_stop_the_others() -> None:
    needs = _jobs()["file-and-close"]["needs"]
    needs_list = [needs] if isinstance(needs, str) else list(needs)
    assert "analyse" not in needs_list


def test_the_fan_out_is_a_matrix_over_targets_computed_by_the_official_entry_point() -> None:
    targets_text = _text(_jobs()["targets"])
    assert "repository-presenter issue-targets" in targets_text
    for name in ("analyse", "file-and-close"):
        assert _jobs()[name]["strategy"]["fail-fast"] is False, name
        assert "fromJSON(needs.targets.outputs.matrix)" in str(
            _jobs()[name]["strategy"]["matrix"]["target"]
        ), name


def test_the_write_steps_run_the_gated_official_entry_point() -> None:
    commands = [str(step.get("run", "")) for step in _steps(_jobs()["file-and-close"])]
    assert any("file-upstream-defects" in c and "--file" in c for c in commands)
    assert any("redetect-upstream-defects" in c and "--close" in c for c in commands)


def test_the_analysis_path_runs_only_dry_run_forms_of_the_entry_point() -> None:
    commands = [str(step.get("run", "")) for step in _steps(_jobs()["analyse"])]
    assert any("file-upstream-defects" in c for c in commands)
    assert all("--file" not in c and "--close" not in c and "--apply" not in c for c in commands)
