"""Structural checks on ``candidates-publish.yml`` and the new ``publish-candidates`` job in
``sealing-scheduled.yml`` (G7-W14), mirroring ``tests/test_workflow_hardening.py``'s own
discipline for ``propose.yml`` (hosted YAML cannot run offline, so these parse the files and check
properties directly) without reusing that file's PROPOSE-specific mutation framework, since this
is a second, independently-shaped write-capable workflow, not a variant of the first.
"""

from __future__ import annotations

from typing import Any

import yaml

from support import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CANDIDATES_PUBLISH = "candidates-publish.yml"
SEALING_SCHEDULED = "sealing-scheduled.yml"
WRITE_TOKEN = "GH_CANDIDATES_WRITE_TOKEN"
AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED"


def _load(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{name} is not a YAML mapping"
    return loaded


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


def test_candidates_publish_has_exactly_a_plan_and_a_write_job() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    assert set(workflow["jobs"]) == {"plan", "write"}


def test_the_write_token_and_the_owner_switch_appear_only_in_the_writes_final_step() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    write_steps = _steps(workflow["jobs"]["write"])
    for step in write_steps[:-1]:
        env = step.get("env", {})
        assert WRITE_TOKEN not in env
        assert AUTHORIZATION_VARIABLE not in env
    final_env = write_steps[-1].get("env", {})
    assert WRITE_TOKEN in final_env
    assert final_env.get(AUTHORIZATION_VARIABLE) == "1"
    # And never anywhere in the plan job, which holds no write credential at all.
    for step in _steps(workflow["jobs"]["plan"]):
        env = step.get("env", {})
        assert WRITE_TOKEN not in env
        assert AUTHORIZATION_VARIABLE not in env


def test_no_job_token_grants_a_write_permission_anywhere() -> None:
    """The write capability is the minted App installation token, never the job's own
    GITHUB_TOKEN: that token cannot open the PR on this repository and starts no required CI
    checks on it (docs/DECISION_LOG.md 2026-10-10), so it is read-only in every job and in the
    workflow default - and in the caller's `publish-candidates` job too (a reusable workflow's
    token permissions can never exceed its caller's grant)."""
    workflow = _load(CANDIDATES_PUBLISH)
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert job["permissions"] == {"contents": "read"}
    caller = _load(SEALING_SCHEDULED)["jobs"]["publish-candidates"]
    assert caller["permissions"] == {"contents": "read"}


def test_the_write_job_needs_the_plan_job_and_is_gated_on_do_publish_and_ready() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    write_job = workflow["jobs"]["write"]
    assert write_job["needs"] == "plan"
    condition = write_job["if"]
    assert "inputs.do_publish" in condition
    assert "needs.plan.outputs.ready" in condition
    assert "needs.plan.result" in condition


def _app_token_steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        step
        for step in _steps(job)
        if str(step.get("uses", "")).startswith("actions/create-github-app-token@")
    ]


def test_only_the_write_job_mints_an_app_token_with_the_minimum_scope() -> None:
    """The plan job holds no credential at all. The write job mints exactly one installation
    token: contents+pull-requests write (metadata read is mandatory), and no `owner` or
    `repositories` input - the action's documented default of "only the current repository"; an
    `owner` alone would widen it to every repository in the installation."""
    workflow = _load(CANDIDATES_PUBLISH)
    assert _app_token_steps(workflow["jobs"]["plan"]) == []
    minted = _app_token_steps(workflow["jobs"]["write"])
    assert len(minted) == 1
    inputs = minted[0]["with"]
    assert {key for key in inputs if key.startswith("permission-")} == {
        "permission-contents",
        "permission-metadata",
        "permission-pull-requests",
    }
    assert inputs["permission-contents"] == "write"
    assert inputs["permission-pull-requests"] == "write"
    assert inputs["permission-metadata"] == "read"
    assert "owner" not in inputs
    assert "repositories" not in inputs
    assert set(inputs) == {"app-id", "private-key"} | {
        key for key in inputs if "permission-" in key
    }


def test_the_write_token_is_the_minted_app_token_never_the_ambient_github_token() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    write_steps = _steps(workflow["jobs"]["write"])
    mint = _app_token_steps(workflow["jobs"]["write"])[0]
    assert write_steps.index(mint) < len(write_steps) - 1  # minted before the final step
    final_env = write_steps[-1]["env"]
    assert final_env[WRITE_TOKEN] == f"${{{{ steps.{mint['id']}.outputs.token }}}}"
    for job in workflow["jobs"].values():
        for step in _steps(job):
            for value in (step.get("env") or {}).values():
                assert "secrets.GITHUB_TOKEN" not in str(value)
            assert "secrets.GITHUB_TOKEN" not in str(step.get("with", {}))


def test_the_app_secrets_are_read_only_by_the_mint_step_and_only_in_the_write_job() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    for job_name, job in workflow["jobs"].items():
        for step in _steps(job):
            text = str(step)
            if "GH_APP_" in text:
                assert job_name == "write"
                assert str(step.get("uses", "")).startswith("actions/create-github-app-token@")


def test_checkouts_do_not_persist_the_job_token() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    for job in workflow["jobs"].values():
        for step in _steps(job):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False


def test_one_publish_per_target_repository_at_a_time() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    concurrency = workflow["concurrency"]
    assert "inputs.repo" in concurrency["group"]
    assert concurrency["cancel-in-progress"] is False


def test_no_run_script_interpolates_github_ref_name_directly() -> None:
    """github.ref_name is a trigger-time value, not an attacker-influenced one, but this project's
    own rule (tests/test_workflow_hardening.py) is that nothing besides a short fixed allow-list
    is ever interpolated straight into run: text - everything else goes through env:, including
    this one, so a reviewer never has to re-derive which expressions are "safe enough" ad hoc."""
    workflow = _load(CANDIDATES_PUBLISH)
    for job in workflow["jobs"].values():
        for step in _steps(job):
            assert "${{ github.ref_name }}" not in str(step.get("run", ""))


def test_sealing_scheduled_gates_candidates_publish_on_its_own_owner_variable() -> None:
    workflow = _load(SEALING_SCHEDULED)
    job = workflow["jobs"]["publish-candidates"]
    condition = job["if"]
    assert "vars.REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED" in condition
    assert job["needs"] == ["plan", "seal"]
    assert job["uses"] == "./.github/workflows/candidates-publish.yml"
    assert job["secrets"] == "inherit"  # the called write job reads GH_APP_ID/GH_APP_PRIVATE_KEY


def test_sealing_scheduled_publishes_every_planned_repository_not_only_full_mode() -> None:
    """Unlike `propose` (registry mode "full" only), candidates/ bookkeeping applies to every
    planned repository, dry_run included - the whole point of G7-W14."""
    workflow = _load(SEALING_SCHEDULED)
    job = workflow["jobs"]["publish-candidates"]
    assert job["strategy"]["matrix"]["target"] == "${{ fromJSON(needs.plan.outputs.repositories) }}"


def test_ci_runs_on_every_pull_request_so_the_required_checks_report_on_a_candidates_pr() -> None:
    """The candidates-update PR is opened with an App installation token precisely so ci.yml's own
    ordinary `pull_request` trigger fires for it. That only works while ci.yml has no branch or
    path filter that would exclude a `candidates/`-only change from the required checks (the
    branch-protection contexts `Python 3.11`/`3.12`/`3.13` come from its matrix job name)."""
    ci = _load("ci.yml")
    triggers = ci.get("on", ci.get(True))  # PyYAML 1.1 reads a bare `on` key as boolean True
    assert "pull_request" in triggers
    pull_request = triggers["pull_request"] or {}
    for narrowing in ("paths", "paths-ignore", "branches", "branches-ignore", "types"):
        assert narrowing not in pull_request
    job = ci["jobs"]["checks"]
    assert job["name"] == "Python ${{ matrix.python-version }}"
    assert job["strategy"]["matrix"]["python-version"] == ["3.11", "3.12", "3.13"]
