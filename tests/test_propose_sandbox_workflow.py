"""``propose-sandbox.yml`` - the sandbox canary's workflow - is propose.yml's hardening on a target
that is a literal, not an input, and is the only workflow that can reach the sandbox.

Hosted YAML cannot run offline, so these tests parse the file, apply the same structural checks
``test_workflow_hardening.py`` applies to ``propose.yml`` (imported, not copied: one rule, two
workflows), pin what differs on purpose, and execute the validation step under bash with hostile
inputs.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from repository_presenter.core.registry.sandbox import (
    SANDBOX_REGISTRY_RELATIVE_PATH,
    SANDBOX_REPOSITORIES,
)
from support import REPO_ROOT
from test_workflow_hardening import (
    DRY_RUN_JOB,
    EXPRESSION,
    VALIDATE_STEP,
    WORKFLOW_NAMES,
    WORKFLOWS,
    WRITE_JOB,
    _bash,
    _steps,
    token_exposure_violations,
    write_gate_violations,
)

NAME = "propose-sandbox.yml"
SANDBOX = "babar-raza/presenter-sandbox"
RECORD = "ops/proposal-authorizations/babar-raza__presenter-sandbox__0123456789ab.json"


def load() -> dict[str, Any]:
    loaded = yaml.safe_load((WORKFLOWS / NAME).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_the_workflow_is_hardened_like_propose_yml() -> None:
    workflow = load()
    assert token_exposure_violations(workflow) == []
    assert write_gate_violations(workflow) == []
    for job in workflow["jobs"].values():
        for step in _steps(job):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False
                assert step["with"]["fetch-depth"] == 0  # the record's provenance reads history


def test_the_target_is_a_literal_agreeing_with_the_code_constant_never_an_input() -> None:
    workflow = load()
    assert set(workflow[True]["workflow_dispatch"]["inputs"]) == {
        "authorization_record",
        "do_propose",
    }
    assert {SANDBOX} == SANDBOX_REPOSITORIES
    text = (WORKFLOWS / NAME).read_text(encoding="utf-8")
    owner, name = SANDBOX.split("/")
    mints = [
        step["with"]
        for job in workflow["jobs"].values()
        for step in _steps(job)
        if str(step.get("uses", "")).startswith("actions/create-github-app-token@")
    ]
    assert len(mints) == 2
    assert {(m["owner"], m["repositories"]) for m in mints} == {(owner, name)}
    for job in workflow["jobs"].values():  # every command line names the sandbox, and only it
        command = str(_steps(job)[-1]["run"])
        assert (
            f"--sandbox --repo {SANDBOX} --correction-bundle ops/sandbox-canary/bundle" in command
        )
    assert re.findall(r"--repo (\S+)", text) == [SANDBOX, SANDBOX]


def test_one_run_at_a_time_and_none_cancelled_in_flight() -> None:
    group = load()["concurrency"]
    assert group == {"group": "propose-sandbox", "cancel-in-progress": False}


def test_the_write_job_is_gated_on_a_protected_environment_and_holds_no_job_token_write() -> None:
    jobs = load()["jobs"]
    assert jobs[WRITE_JOB]["environment"] == "sandbox-canary"
    assert "environment" not in jobs[DRY_RUN_JOB]
    for job in jobs.values():
        assert job["permissions"] == {"contents": "read"}
    text = (WORKFLOWS / NAME).read_text(encoding="utf-8")
    assert text.count("REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED") >= 1
    write_env = _steps(jobs[WRITE_JOB])[-1]["env"]
    assert write_env["REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"] == "1"
    assert "vars." not in text  # the repository variable is not read: it must stay unset


def test_no_other_workflow_can_reach_the_sandbox_and_this_one_cannot_reach_a_product() -> None:
    for name in WORKFLOW_NAMES:
        if name == NAME:
            continue
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert (
            "--sandbox" not in text
            and "registry_sandbox" not in text
            and "presenter-sandbox" not in text
        )
    own = (WORKFLOWS / NAME).read_text(encoding="utf-8")
    assert "aspose" not in own.lower()  # no product is named at all
    assert (REPO_ROOT / SANDBOX_REGISTRY_RELATIVE_PATH).is_file()


def test_the_command_is_refused_when_a_step_exits_3_and_reports_it() -> None:
    for job_name in (DRY_RUN_JOB, WRITE_JOB):
        script = str(_steps(load()["jobs"][job_name])[-1]["run"])
        assert "proposal refused" in script and '"$status" -eq 3' in script
        assert ("--propose" in script.split("repository-presenter propose", 1)[1]) is (
            job_name == WRITE_JOB
        )


GOOD = {"INPUT_AUTHORIZATION_RECORD": "", "INPUT_DO_PROPOSE": "false"}


def _validate(tmp_path: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    steps = load()["jobs"][DRY_RUN_JOB]["steps"]
    script = str(next(s for s in steps if VALIDATE_STEP in str(s.get("name")))["run"])
    assert not EXPRESSION.search(script)
    env = {k: v for k, v in os.environ.items() if not k.startswith("INPUT_")}
    env.update(GOOD)
    env.update({f"INPUT_{key.upper()}": value for key, value in overrides.items()})
    env["GITHUB_OUTPUT"] = (tmp_path / "output").as_posix()
    return subprocess.run(
        [_bash(), "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_a_dry_run_and_a_fully_specified_write_dispatch_pass(tmp_path: Path) -> None:
    assert _validate(tmp_path).returncode == 0
    result = _validate(tmp_path, authorization_record=RECORD, do_propose="true")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "output").read_text(encoding="utf-8").strip().endswith(f"={RECORD}")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("do_propose", "yes"),
        ("authorization_record", "ops/../etc/passwd.json"),
        ("authorization_record", "/etc/passwd"),
        ("authorization_record", "ops/proposal-authorizations/a;touch pwned.json"),
        ("authorization_record", "ops/proposal-authorizations/sub/a.json"),
        ("authorization_record", "ops/proposal-authorizations/a.yaml"),
        ("authorization_record", "ops/proposal-authorizations/a.json\nx"),
    ],
)
def test_hostile_input_fails_closed_without_echoing_it(
    tmp_path: Path, field: str, value: str
) -> None:
    result = _validate(tmp_path, **{field: value})
    assert result.returncode != 0 and "::error::" in result.stdout
    assert not (tmp_path / "pwned").exists() and "touch pwned" not in result.stdout + result.stderr


def test_a_real_write_without_a_record_fails_closed(tmp_path: Path) -> None:
    result = _validate(tmp_path, do_propose="true")
    assert result.returncode != 0 and "authorization_record" in result.stdout
