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


def test_only_the_write_job_is_granted_a_write_permission() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    assert workflow["jobs"]["plan"].get("permissions", {}).get("contents") != "write"
    write_permissions = workflow["jobs"]["write"]["permissions"]
    assert write_permissions["contents"] == "write"
    assert write_permissions["pull-requests"] == "write"


def test_the_write_job_needs_the_plan_job_and_is_gated_on_do_publish_and_ready() -> None:
    workflow = _load(CANDIDATES_PUBLISH)
    write_job = workflow["jobs"]["write"]
    assert write_job["needs"] == "plan"
    condition = write_job["if"]
    assert "inputs.do_publish" in condition
    assert "needs.plan.outputs.ready" in condition
    assert "needs.plan.result" in condition


def test_no_job_mints_a_github_app_installation_token() -> None:
    """G7-W14's own simplification: the write target is this control repository itself, so no
    App installation token is minted anywhere in this file - only the job's own ambient
    GITHUB_TOKEN, under a distinct name, in the one gated step."""
    workflow = _load(CANDIDATES_PUBLISH)
    for job in workflow["jobs"].values():
        for step in _steps(job):
            assert not str(step.get("uses", "")).startswith("actions/create-github-app-token")


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
    assert job["permissions"]["contents"] == "write"
    assert job["permissions"]["pull-requests"] == "write"


def test_sealing_scheduled_publishes_every_planned_repository_not_only_full_mode() -> None:
    """Unlike `propose` (registry mode "full" only), candidates/ bookkeeping applies to every
    planned repository, dry_run included - the whole point of G7-W14."""
    workflow = _load(SEALING_SCHEDULED)
    job = workflow["jobs"]["publish-candidates"]
    assert job["strategy"]["matrix"]["target"] == "${{ fromJSON(needs.plan.outputs.repositories) }}"
