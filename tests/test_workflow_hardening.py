"""Shell-injection and token-exposure hardening of the hosted workflows.

``propose.yml`` is the one write-capable workflow, and it used to interpolate the dispatcher's
``${{ inputs.* }}`` straight into ``run:`` bash text (a dispatcher could inject shell) and to mint
the write token in the same job that ran the dry run. AGENTS.md "Security and Effects": write
credentials exist only in a separate effect job, short-lived and target-scoped. Hosted YAML cannot
run offline, so these tests parse the workflow files, apply structural checks (each with a negative
control: the check must reject a deliberately broken copy), and execute the validation step under
bash with hostile inputs.

The structural rules, for every workflow: no attacker-influenced expression is interpolated into a
``run:`` script (it goes through ``env:``). For ``propose.yml`` additionally: the write token and
the App secrets exist only in the ``write`` job and only the final step sees the token; ``write``
needs the ``dry-run`` job and is gated on ``do_propose``; one run per target repository at a time.
"""

from __future__ import annotations

import copy
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
PROPOSE = "propose.yml"
WRITE_JOB = "write"
DRY_RUN_JOB = "dry-run"
VALIDATE_STEP = "Validate every dispatch input"
MINT_ACTION = "actions/create-github-app-token@"
EXPRESSION = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")

# The only expressions that may appear inside a ``run:`` script: values GitHub itself assigns (the
# trigger's event name, the numeric run id) and a prior step's or job's own status. Everything else
# (inputs, event payload, matrix values, step and job outputs) is influenced by a dispatcher or by
# data a step computed, and reaches a script through ``env:``.
SAFE_RUN_EXPRESSIONS = (
    re.compile(r"^github\.event_name$"),
    re.compile(r"^github\.run_id$"),
    re.compile(r"^steps\.[A-Za-z0-9_-]+\.(outcome|conclusion)$"),
    re.compile(r"^needs\.[A-Za-z0-9_-]+\.result$"),
)

WORKFLOW_NAMES = sorted(path.name for path in WORKFLOWS.glob("*.yml"))


def _load(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{name} is not a YAML mapping"
    return loaded


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


# --- the structural checks: each returns the list of violations, empty when the rule holds --------


def untrusted_run_expressions(workflow: dict[str, Any]) -> list[str]:
    """Every expression interpolated into a ``run:`` (or github-script ``script:``) body."""
    found: list[str] = []
    for job_name, job in workflow["jobs"].items():
        for step in _steps(job):
            bodies = [str(step["run"])] if "run" in step else []
            if str(step.get("uses", "")).startswith("actions/github-script@"):
                bodies.append(str(step.get("with", {}).get("script", "")))
            for body in bodies:
                for expression in EXPRESSION.findall(body):
                    if not any(safe.match(expression) for safe in SAFE_RUN_EXPRESSIONS):
                        found.append(
                            f"{job_name}: {step.get('name', step.get('id'))}: {expression}"
                        )
    return found


def run_blocks_with_input_expressions(workflow: dict[str, Any]) -> list[str]:
    """The literal rule from the hardening brief, independent of the allow-list above."""
    return [
        f"{job_name}: {step.get('name')}"
        for job_name, job in workflow["jobs"].items()
        for step in _steps(job)
        if "${{ inputs." in str(step.get("run", ""))
        or "${{ github.event.inputs." in str(step.get("run", ""))
    ]


def _mint_steps(job: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    return [
        (i, s) for i, s in enumerate(_steps(job)) if str(s.get("uses", "")).startswith(MINT_ACTION)
    ]


def token_exposure_violations(workflow: dict[str, Any]) -> list[str]:
    """Write-capable material lives in the ``write`` job alone; tokens reach one final step only.

    The ``dry-run`` job may mint a read-only token (its dry run reads the target), but never a write
    scope, the write token, or the write gate, and that read token is seen by its final step only.
    """
    violations: list[str] = []
    for job_name, job in workflow["jobs"].items():
        steps = _steps(job)
        mints = _mint_steps(job)
        is_write = job_name == WRITE_JOB
        text = yaml.safe_dump(job)
        if not is_write:
            for marker in (
                "GH_PROPOSAL_WRITE_TOKEN",
                "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED",
                "steps.app-token",
            ):
                if marker in text:
                    violations.append(f"{job_name} references {marker}")
            for _, mint in mints:
                grants = {
                    k: v for k, v in mint.get("with", {}).items() if k.startswith("permission-")
                }
                if not grants or any(str(v) != "read" for v in grants.values()):
                    violations.append(f"{job_name} mints a non-read-only token")
        if len(mints) != 1:
            violations.append(f"{job_name} must mint exactly one token")
            continue
        token_id = str(mints[0][1].get("id"))
        reference = f"steps.{token_id}.outputs"
        if "env" in job and reference in yaml.safe_dump(job["env"]):
            violations.append(f"{job_name}: the token is exposed at job level")
        for index, step in enumerate(steps):
            sees_token = reference in yaml.safe_dump(step.get("env", {})) or reference in str(
                step.get("run", "")
            )
            if sees_token and index != len(steps) - 1:
                violations.append(f"{job_name} step {index} sees the token but is not the final")
            if index < mints[0][0] and sees_token:
                violations.append(f"{job_name} step {index} uses the token before it is minted")
        final = steps[-1]
        if is_write:
            if "GH_PROPOSAL_WRITE_TOKEN" not in final.get("env", {}):
                violations.append("the final write step does not receive the token")
            if "--propose" not in str(final.get("run", "")):
                violations.append("the final write step is not the propose step")
        elif "GH_TOKEN" not in final.get("env", {}):
            violations.append("the final dry-run step does not receive the read token")
    return violations


def write_gate_violations(workflow: dict[str, Any]) -> list[str]:
    jobs = workflow["jobs"]
    violations: list[str] = []
    if WRITE_JOB not in jobs or DRY_RUN_JOB not in jobs:
        return ["propose.yml needs both a dry-run and a write job"]
    needs = jobs[WRITE_JOB].get("needs")
    needs = [needs] if isinstance(needs, str) else list(needs or [])
    if DRY_RUN_JOB not in needs:
        violations.append("the write job does not need the dry-run job")
    condition = str(jobs[WRITE_JOB].get("if", ""))
    if "inputs.do_propose" not in condition:
        violations.append("the write job is not gated on do_propose")
    if f"needs.{DRY_RUN_JOB}.result == 'success'" not in condition:
        violations.append("the write job is not gated on the dry run having succeeded")
    for job_name, job in jobs.items():
        for scope, level in (job.get("permissions") or {}).items():
            if level == "write":
                violations.append(f"{job_name} holds GITHUB_TOKEN write permission {scope}")
    return violations


def concurrency_violations(workflow: dict[str, Any]) -> list[str]:
    group = workflow.get("concurrency")
    if not isinstance(group, dict) or not group.get("group"):
        return ["no concurrency group"]
    violations: list[str] = []
    if "inputs.repo" not in str(group["group"]):
        violations.append("the concurrency group is not keyed to the target repository")
    if group.get("cancel-in-progress") is not False:
        violations.append("cancel-in-progress must be false")
    return violations


# --- the real workflows satisfy the rules -------------------------------------------------------


@pytest.mark.parametrize("name", WORKFLOW_NAMES)
def test_no_workflow_interpolates_an_untrusted_expression_into_a_run_script(name: str) -> None:
    workflow = _load(name)
    assert untrusted_run_expressions(workflow) == []
    assert run_blocks_with_input_expressions(workflow) == []


def test_the_write_token_exists_only_in_the_write_job_and_only_its_final_step() -> None:
    assert token_exposure_violations(_load(PROPOSE)) == []


def test_the_write_job_needs_the_dry_run_and_the_explicit_do_propose_input() -> None:
    assert write_gate_violations(_load(PROPOSE)) == []


def test_one_proposal_per_target_repository_at_a_time() -> None:
    assert concurrency_violations(_load(PROPOSE)) == []


def test_the_dry_run_job_holds_only_a_read_token_and_read_permission() -> None:
    job = _load(PROPOSE)["jobs"][DRY_RUN_JOB]
    assert job["permissions"] == {"contents": "read"}
    ((_, mint),) = _mint_steps(job)
    assert {k: v for k, v in mint["with"].items() if k.startswith("permission-")} == {
        "permission-contents": "read",
        "permission-metadata": "read",
    }
    # The secrets appear only on that mint step.
    others = [s for s in _steps(job) if s is not mint]
    assert "secrets." not in yaml.safe_dump(others)


def test_checkouts_do_not_persist_the_job_token() -> None:
    for job in _load(PROPOSE)["jobs"].values():
        for step in _steps(job):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False


def test_the_checkouts_are_full_depth_for_the_record_provenance() -> None:
    for job in _load(PROPOSE)["jobs"].values():
        checkouts = [
            s for s in _steps(job) if str(s.get("uses", "")).startswith("actions/checkout@")
        ]
        assert checkouts
        for step in checkouts:
            assert step["with"]["fetch-depth"] == 0


def test_the_record_and_trigger_sha_reach_the_command_through_env() -> None:
    jobs = _load(PROPOSE)["jobs"]
    for job_name in (DRY_RUN_JOB, WRITE_JOB):
        final = _steps(jobs[job_name])[-1]
        assert "AUTHORIZATION_RECORD" in final["env"]
        assert final["env"]["TRIGGER_SHA"] == "${{ github.sha }}"
        assert '--authorization-record "$AUTHORIZATION_RECORD"' in final["run"]
        assert '--trigger-sha "$TRIGGER_SHA"' in final["run"]


def test_the_removed_cli_flags_and_inputs_are_gone() -> None:
    text = (WORKFLOWS / PROPOSE).read_text(encoding="utf-8")
    for removed in ("--readme-file", "--expires-in-minutes", "--source-revision"):
        assert removed not in text
    inputs = _load(PROPOSE)[True]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"repo", "base_branch", "authorization_record", "do_propose"}


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
@pytest.mark.parametrize(("exit_code", "refused"), [(0, False), (1, False), (2, False), (3, True)])
def test_exit_code_3_is_reported_as_a_refused_proposal(
    tmp_path: Path, job_name: str, exit_code: int, refused: bool
) -> None:
    script = str(_steps(_load(PROPOSE)["jobs"][job_name])[-1]["run"])
    fake = tmp_path / "bin"
    fake.mkdir()
    command = fake / "repository-presenter"
    command.write_text(f'#!/usr/bin/env bash\necho "args: $*"\nexit {exit_code}\n', newline="\n")
    command.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{fake.as_posix()}{os.pathsep}{env['PATH']}"
    env.update(
        REPO="acme/x",
        BASE_BRANCH="",
        AUTHORIZATION_RECORD="ops/proposal-authorizations/a.json",
        TRIGGER_SHA="a" * 40,
    )
    result = subprocess.run(
        [_bash(), "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert ("proposal refused" in result.stdout) is refused
    assert "--authorization-record ops/proposal-authorizations/a.json" in result.stdout
    assert f"--trigger-sha {'a' * 40}" in result.stdout
    assert ("--propose" in result.stdout.split("args:", 1)[1]) is (job_name == WRITE_JOB)


# --- negative controls: each check rejects a deliberately broken workflow -----------------------


def _broken(mutate: Any) -> dict[str, Any]:
    workflow = copy.deepcopy(_load(PROPOSE))
    mutate(workflow)
    return workflow


def _step(workflow: dict[str, Any], job: str, fragment: str) -> dict[str, Any]:
    matches = [s for s in _steps(workflow["jobs"][job]) if fragment in str(s.get("name"))]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize(
    "expression", ["inputs.repo", "github.event.inputs.repo", "github.event.client_payload.x"]
)
def test_an_input_expression_in_a_run_block_is_rejected(expression: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        _step(workflow, DRY_RUN_JOB, "Dry run")["run"] += f'\necho "${{{{ {expression} }}}}"\n'

    broken = _broken(mutate)
    assert untrusted_run_expressions(broken)
    if "inputs." in expression:
        assert run_blocks_with_input_expressions(broken)


def test_step_and_matrix_outputs_in_a_run_block_are_rejected_too() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        step = _step(workflow, DRY_RUN_JOB, "Dry run")
        step["run"] += '\necho "${{ steps.validate.outputs.repo }} ${{ matrix.owner }}"\n'

    assert len(untrusted_run_expressions(_broken(mutate))) == 2


def test_the_write_token_in_the_dry_run_job_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        step = _step(workflow, DRY_RUN_JOB, "Dry run")
        step["env"]["GH_PROPOSAL_WRITE_TOKEN"] = "${{ steps.app-token.outputs.token }}"

    assert token_exposure_violations(_broken(mutate))


def test_a_mint_step_in_the_dry_run_job_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        mint = _step(workflow, WRITE_JOB, "Mint")
        workflow["jobs"][DRY_RUN_JOB]["steps"].insert(0, copy.deepcopy(mint))

    assert token_exposure_violations(_broken(mutate))


def test_a_non_read_only_mint_in_the_dry_run_job_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        mint = _step(workflow, DRY_RUN_JOB, "Mint")
        mint["with"]["permission-pull-requests"] = "write"

    assert token_exposure_violations(_broken(mutate))


def test_a_mint_without_permission_inputs_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        mint = _step(workflow, DRY_RUN_JOB, "Mint")
        mint["with"] = {k: v for k, v in mint["with"].items() if not k.startswith("permission-")}

    assert token_exposure_violations(_broken(mutate))


def test_the_read_token_in_a_non_final_dry_run_step_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        steps = workflow["jobs"][DRY_RUN_JOB]["steps"]
        steps.insert(
            len(steps) - 1,
            {"name": "Extra", "env": {"T": "${{ steps.read-token.outputs.token }}"}, "run": "true"},
        )

    assert token_exposure_violations(_broken(mutate))


def test_the_write_token_at_write_job_level_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        workflow["jobs"][WRITE_JOB]["env"] = {"T": "${{ steps.app-token.outputs.token }}"}

    assert token_exposure_violations(_broken(mutate))


def test_the_write_token_in_a_non_final_write_step_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        steps = workflow["jobs"][WRITE_JOB]["steps"]
        steps[-2:] = [
            {"name": "Extra", "env": {"T": "${{ steps.app-token.outputs.token }}"}, "run": "true"},
            steps[-1],
        ]

    assert token_exposure_violations(_broken(mutate))


def test_a_write_job_without_needs_on_the_dry_run_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        del workflow["jobs"][WRITE_JOB]["needs"]

    assert write_gate_violations(_broken(mutate))


def test_a_write_job_not_gated_on_do_propose_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        workflow["jobs"][WRITE_JOB]["if"] = "${{ needs.dry-run.result == 'success' }}"

    assert write_gate_violations(_broken(mutate))


def test_a_write_job_not_gated_on_the_dry_run_result_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        workflow["jobs"][WRITE_JOB]["if"] = "${{ inputs.do_propose }}"

    assert write_gate_violations(_broken(mutate))


def test_github_token_write_permission_on_any_job_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        workflow["jobs"][DRY_RUN_JOB]["permissions"] = {"contents": "write"}

    assert write_gate_violations(_broken(mutate))


def test_a_missing_concurrency_group_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        del workflow["concurrency"]

    assert concurrency_violations(_broken(mutate))


def test_a_concurrency_group_not_keyed_to_the_repository_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        workflow["concurrency"]["group"] = "propose"

    assert concurrency_violations(_broken(mutate))


def test_cancel_in_progress_is_rejected() -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        workflow["concurrency"]["cancel-in-progress"] = True

    assert concurrency_violations(_broken(mutate))


# --- the validation step, executed under bash with hostile inputs --------------------------------

GOOD = {
    "INPUT_REPO": "acme-org/disposable-target",
    "INPUT_BASE_BRANCH": "",
    "INPUT_AUTHORIZATION_RECORD": "",
    "INPUT_DO_PROPOSE": "false",
    "INPUT_CANDIDATE_ARTIFACT": "",
}
RECORD = "ops/proposal-authorizations/2026-10-05-acme-readme.json"


def _bash() -> str:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available to execute the validation step")
    probe = subprocess.run([bash, "-c", "echo ok"], capture_output=True, text=True, check=False)
    if probe.stdout.strip() != "ok":
        pytest.skip("bash on PATH is not a working POSIX shell (a WSL launcher?)")
    return bash


def _validate(tmp_path: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    steps = _load(PROPOSE)["jobs"][DRY_RUN_JOB]["steps"]
    script = str(next(s for s in steps if VALIDATE_STEP in str(s.get("name")))["run"])
    assert not EXPRESSION.search(script), "the validation script interpolates a workflow expression"
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


def _outputs(tmp_path: Path) -> dict[str, str]:
    lines = (tmp_path / "output").read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_a_valid_dry_run_dispatch_passes_and_publishes_the_split_target(tmp_path: Path) -> None:
    result = _validate(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _outputs(tmp_path) == {
        "owner": "acme-org",
        "name": "disposable-target",
        "repo": "acme-org/disposable-target",
        "base_branch": "",
        "authorization_record": "",
        "candidate_artifact": "",
    }


def test_a_fully_specified_write_dispatch_passes(tmp_path: Path) -> None:
    result = _validate(
        tmp_path, base_branch="release/1.x", authorization_record=RECORD, do_propose="true"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = _outputs(tmp_path)
    assert outputs["authorization_record"] == RECORD
    assert outputs["base_branch"] == "release/1.x"


HOSTILE = [
    ("repo", "acme/x;touch pwned"),
    ("repo", "acme/x$(touch pwned)"),
    ("repo", "acme/x`touch pwned`"),
    ("repo", "acme/x\n::set-env name=A::B"),
    ("repo", "acme/x y"),
    ("repo", "no-slash"),
    ("repo", "-acme/x"),
    ("repo", "acme/-x"),
    ("repo", "acme/.."),
    ("repo", "acme/a/b"),
    ("repo", ""),
    ("base_branch", "main;touch pwned"),
    ("base_branch", "main$(touch pwned)"),
    ("base_branch", "a..b"),
    ("base_branch", "-main"),
    ("base_branch", "release/"),
    ("base_branch", "x.lock"),
    ("base_branch", "main\nx"),
    ("do_propose", "yes"),
    ("authorization_record", "ops/../etc/passwd.json"),
    ("authorization_record", "/etc/passwd"),
    ("authorization_record", "ops/a b"),
    ("authorization_record", "ops/a;touch pwned"),
    ("authorization_record", "docs/record.json"),
    ("authorization_record", "ops/"),
    ("authorization_record", "ops/proposal-authorizations/"),
    ("authorization_record", "ops/proposal-authorizations/a.yaml"),
    ("authorization_record", "ops/proposal-authorizations/sub/a.json"),
    ("authorization_record", "ops/proposal-authorizations/../a.json"),
    ("authorization_record", "ops/proposal-authorizations/a.json\nx"),
]


@pytest.mark.parametrize(("field", "value"), HOSTILE)
def test_hostile_or_malformed_input_fails_closed(tmp_path: Path, field: str, value: str) -> None:
    result = _validate(tmp_path, **{field: value})
    assert result.returncode != 0, f"{field}={value!r} was accepted"
    assert "::error::" in result.stdout
    assert not (tmp_path / "pwned").exists(), "injected shell ran"
    assert "touch pwned" not in result.stdout + result.stderr, (
        "the rejection message must name the input, never echo its value"
    )
    assert not (tmp_path / "output").exists() or not (tmp_path / "output").read_text()


def test_a_real_write_without_an_authorization_record_fails_closed(tmp_path: Path) -> None:
    result = _validate(tmp_path, do_propose="true")
    assert result.returncode != 0
    assert "authorization_record" in result.stdout


def test_a_scheduled_write_may_omit_the_record_because_it_is_located_for_the_sealed_candidate(
    tmp_path: Path,
) -> None:
    result = _validate(
        tmp_path,
        do_propose="true",
        candidate_artifact="sealed-acme-org__disposable-target",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = (tmp_path / "output").read_text(encoding="utf-8")
    assert "candidate_artifact=sealed-acme-org__disposable-target" in output


@pytest.mark.parametrize(
    "artifact",
    [
        "sealed-other-org__other-repo",
        "sealed-acme-org__disposable-target; echo pwned",
        "../sealed-acme-org__disposable-target",
        "sealed-acme-org__disposable-target\n::set-output name=x::y",
        "$(id)",
    ],
)
def test_a_candidate_artifact_naming_anything_but_the_targets_own_sealed_bundle_is_rejected(
    tmp_path: Path, artifact: str
) -> None:
    result = _validate(tmp_path, candidate_artifact=artifact)
    assert result.returncode != 0
    assert "candidate_artifact" in result.stdout
    assert artifact not in result.stdout


# --- present.yml: the resolved target is validated before anything reaches $GITHUB_OUTPUT --------

RESOLVE_STEP = "Resolve the target repository from this trigger"

# The pre-hardening script (interpolated expressions), kept only as a negative control: it must be
# shown to emit an extra output line for a hostile value, so the new test proves a real difference.
OLD_RESOLVE_SCRIPT = """
repository="${{ inputs.repository }}"
owner="${repository%%/*}"
name="${repository#*/}"
echo "repository=$repository" >> "$GITHUB_OUTPUT"
echo "owner=$owner" >> "$GITHUB_OUTPUT"
echo "name=$name" >> "$GITHUB_OUTPUT"
"""

HOSTILE_TARGETS = [
    "acme/x\ninjected=1",
    "acme/x\r\ninjected=1",
    "acme/x\rinjected=1",
    "acme/x\n::set-output name=injected::1",
    "acme/x::error::boom",
    "acme/x=y",
    "acme=evil/x",
    "acme/x\n",
    "acme/x\nowner=evil\nname=evil",
    "acme/x;touch pwned",
    "acme/$(touch pwned)",
    "no-slash",
    "/x",
    "acme/",
    "acme/..",
]


def _resolve(tmp_path: Path, event: str, value: str) -> subprocess.CompletedProcess[str]:
    steps = _load("present.yml")["jobs"]["present"]["steps"]
    script = str(next(s for s in steps if RESOLVE_STEP in str(s.get("name")))["run"])
    assert not EXPRESSION.search(script)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DISPATCH_", "PAYLOAD_"))}
    env["EVENT_NAME"] = event
    env["DISPATCH_REPOSITORY"] = value if event == "workflow_dispatch" else ""
    env["PAYLOAD_REPOSITORY"] = value if event == "repository_dispatch" else ""
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


@pytest.mark.parametrize("event", ["workflow_dispatch", "repository_dispatch"])
def test_a_valid_target_yields_exactly_three_outputs(tmp_path: Path, event: str) -> None:
    result = _resolve(tmp_path, event, "aspose-slides-foss/Aspose.Slides-FOSS-for-Java")
    assert result.returncode == 0, result.stdout + result.stderr
    lines = (tmp_path / "output").read_text(encoding="utf-8").splitlines()
    assert lines == [
        "repository=aspose-slides-foss/Aspose.Slides-FOSS-for-Java",
        "owner=aspose-slides-foss",
        "name=Aspose.Slides-FOSS-for-Java",
    ]


@pytest.mark.parametrize("event", ["workflow_dispatch", "repository_dispatch"])
@pytest.mark.parametrize("value", HOSTILE_TARGETS)
def test_a_hostile_target_fails_closed_before_any_output(
    tmp_path: Path, event: str, value: str
) -> None:
    result = _resolve(tmp_path, event, value)
    assert result.returncode != 0, f"{value!r} was accepted"
    assert "::error::" in result.stdout
    assert not (tmp_path / "output").exists() or (tmp_path / "output").read_text() == ""
    assert not (tmp_path / "pwned").exists()
    # The raw value is never echoed, so it cannot smuggle a workflow command into the log.
    assert "injected" not in result.stdout + result.stderr
    assert "boom" not in result.stdout + result.stderr


def test_negative_control_the_old_script_emitted_an_injected_output(tmp_path: Path) -> None:
    script = _render_old(OLD_RESOLVE_SCRIPT, "acme/x\ninjected=1")
    env = {**os.environ, "GITHUB_OUTPUT": (tmp_path / "output").as_posix()}
    subprocess.run(
        [_bash(), "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=True
    )
    lines = (tmp_path / "output").read_text(encoding="utf-8").splitlines()
    assert "injected=1" in lines, lines


def _render_old(script: str, value: str) -> str:
    return EXPRESSION.sub(lambda _match: value, script)
