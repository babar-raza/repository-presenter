"""``propose.yml``'s correction mode: the structure that keeps it as safe as the sealed path.

A dispatch that names ``correction_run`` proposes ``corrections/<run>/<owner>__<name>/`` instead
of a sealed candidate (docs/OPERATIONS_RUNBOOK.md section 12). Hosted YAML cannot run offline, so
these tests parse the file, apply structural checks (each with a negative control: the check must
reject a deliberately broken copy), and execute the steps that differ under bash on real bundle
directories.
``test_workflow_hardening.py`` keeps applying every rule it applied before (imported here, not
copied); ``test_correction_wave_rehearsal.py`` runs the whole path against the local fakes.
"""

from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from repository_presenter.components.readme_correction.committed import (
    COMMITTED_FILES,
    SUMS_NAME,
    write_sums,
)
from support import REPO_ROOT
from test_workflow_hardening import (
    DRY_RUN_JOB,
    EXPRESSION,
    GOOD,
    MINT_ACTION,
    PROPOSE,
    WORKFLOWS,
    WRITE_JOB,
    _bash,
    _load,
    _steps,
    _validate,
    token_exposure_violations,
    write_gate_violations,
)

sys.path.insert(0, str(REPO_ROOT / "tools" / "workflow_rehearsal"))

VERIFY_STEP = "Verify the committed correction bundle"
BUNDLE = "corrections/2026-10-12/acme-org__disposable-target"
RECORD = "ops/proposal-authorizations/acme-org__disposable-target__0123456789ab.json"


def correction_mode_violations(workflow: dict[str, Any]) -> list[str]:
    """The rules correction mode adds, each of which a broken copy must trip."""
    violations: list[str] = []
    for job_name, reference in ((DRY_RUN_JOB, "steps.validate"), (WRITE_JOB, "needs.dry-run")):
        steps = _steps(workflow["jobs"][job_name])
        verify = [i for i, s in enumerate(steps) if VERIFY_STEP in str(s.get("name"))]
        if len(verify) != 1:
            violations.append(f"{job_name} must verify the bundle exactly once")
            continue
        step = steps[verify[0]]
        if f"{reference}.outputs.correction_bundle != ''" not in str(step.get("if")):
            violations.append(f"{job_name}: the verification is not gated on correction mode")
        if "sha256sum --check" not in str(step.get("run")) or SUMS_NAME not in str(step["run"]):
            violations.append(f"{job_name}: the verification does not check SHA256SUMS")
        later = steps[verify[0] + 1 :]
        if any(str(s.get("uses", "")).startswith(MINT_ACTION) for s in steps[: verify[0]]):
            violations.append(f"{job_name}: a token is minted before the bundle is verified")
        if any(
            str(s.get("uses", "")).startswith("actions/setup-python@") for s in steps[: verify[0]]
        ):
            violations.append(
                f"{job_name}: dependencies are installed before the bundle is verified"
            )
        if not any(str(s.get("uses", "")).startswith(MINT_ACTION) for s in later):
            violations.append(f"{job_name}: the token is not minted after the verification")
        final = str(steps[-1]["run"])
        if "--correction-bundle" in final and "--require-sums" not in final:
            violations.append(f"{job_name}: the command does not require the committed digests")
        if '--correction-bundle "$CORRECTION_BUNDLE"' not in final:
            violations.append(f"{job_name}: the command is not given the bundle")
    return violations


def load() -> dict[str, Any]:
    return _load(PROPOSE)


def test_correction_mode_is_a_dispatch_input_only() -> None:
    triggers = load()[True]
    assert "correction_run" in triggers["workflow_dispatch"]["inputs"]
    assert triggers["workflow_dispatch"]["inputs"]["correction_run"]["required"] is False
    assert "correction_run" not in triggers["workflow_call"]["inputs"]  # the scheduled run cannot


def test_a_dispatch_is_a_dry_run_unless_do_propose_is_ticked() -> None:
    inputs = load()[True]["workflow_dispatch"]["inputs"]
    assert inputs["do_propose"]["default"] is False and inputs["do_propose"]["type"] == "boolean"
    write = load()["jobs"][WRITE_JOB]
    assert write["if"] == (
        "${{ inputs.do_propose && needs.dry-run.result == 'success'"
        " && needs.dry-run.outputs.proceed == 'true' }}"
    )


def test_correction_mode_adds_no_job_no_token_no_environment_and_no_variable_read() -> None:
    workflow = load()
    assert set(workflow["jobs"]) == {DRY_RUN_JOB, WRITE_JOB}
    for job in workflow["jobs"].values():
        assert "environment" not in job
        mints = [s for s in _steps(job) if str(s.get("uses", "")).startswith(MINT_ACTION)]
        assert len(mints) == 1
    text = (WORKFLOWS / PROPOSE).read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "vars." not in code  # the repository variable that arms the unattended run is not read
    assert token_exposure_violations(workflow) == []
    assert write_gate_violations(workflow) == []


def test_the_real_workflow_satisfies_the_correction_mode_rules() -> None:
    assert correction_mode_violations(load()) == []


def test_the_write_switch_exists_only_in_the_one_write_step() -> None:
    workflow = load()
    text = yaml.safe_dump(workflow["jobs"][DRY_RUN_JOB])
    assert "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED" not in text
    assert "GH_PROPOSAL_WRITE_TOKEN" not in text
    write_steps = _steps(workflow["jobs"][WRITE_JOB])
    holders = [
        s
        for s in write_steps
        if "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED" in s.get("env", {})
    ]
    assert (
        holders == [write_steps[-1]]
        and holders[0]["env"]["REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"] == "1"
    )


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_the_bundle_reaches_the_command_through_env_and_only_in_correction_mode(
    job_name: str, tmp_path: Path
) -> None:
    final = _steps(load()["jobs"][job_name])[-1]
    assert "CORRECTION_BUNDLE" in final["env"]
    script = str(final["run"])
    assert not EXPRESSION.search(script)
    fake = tmp_path / "bin"
    fake.mkdir()
    command = fake / "repository-presenter"
    command.write_text('#!/usr/bin/env bash\necho "args: $*"\n', newline="\n")
    command.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{fake.as_posix()}{os.pathsep}{env['PATH']}"
    env.update(REPO="acme-org/x", BASE_BRANCH="", AUTHORIZATION_RECORD=RECORD, TRIGGER_SHA="a" * 40)
    sealed = subprocess.run(
        [_bash(), "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    assert "--correction-bundle" not in sealed.stdout and "--require-sums" not in sealed.stdout
    env["CORRECTION_BUNDLE"] = BUNDLE
    correction = subprocess.run(
        [_bash(), "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    assert f"--correction-bundle {BUNDLE} --require-sums" in correction.stdout
    assert ("--propose" in correction.stdout) is (job_name == WRITE_JOB)


# --- the validation step ----------------------------------------------------------------------


def test_a_valid_run_id_yields_the_bundle_directory_for_this_repository(tmp_path: Path) -> None:
    result = _validate(
        tmp_path, correction_run="2026-10-12", authorization_record=RECORD, do_propose="true"
    )
    assert result.returncode == 0, result.stdout + result.stderr
    lines = (tmp_path / "output").read_text(encoding="utf-8").splitlines()
    assert f"correction_bundle={BUNDLE}" in lines


def test_no_run_id_leaves_the_bundle_empty_so_the_sealed_candidate_path_is_unchanged(
    tmp_path: Path,
) -> None:
    assert _validate(tmp_path).returncode == 0
    assert "correction_bundle=" in (tmp_path / "output").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("run_id", ["2026-10-12", "wave.1", "a", "run_2", "A" * 64, "1.2.3-rc1"])
def test_ordinary_run_ids_are_accepted(tmp_path: Path, run_id: str) -> None:
    assert _validate(tmp_path, correction_run=run_id).returncode == 0


def test_a_correction_with_a_sealed_artifact_is_refused_and_echoes_neither(tmp_path: Path) -> None:
    result = _validate(
        tmp_path,
        correction_run="2026-10-12",
        candidate_artifact="sealed-acme-org__disposable-target",
    )
    assert result.returncode != 0 and "correction_run" in result.stdout
    assert "sealed-acme-org" not in result.stdout and not (tmp_path / "output").exists()


def test_a_correction_write_without_a_record_fails_closed(tmp_path: Path) -> None:
    result = _validate(tmp_path, correction_run="2026-10-12", do_propose="true")
    assert result.returncode != 0 and "authorization_record" in result.stdout


def test_the_good_inputs_of_the_hardening_test_name_the_run_input() -> None:
    assert GOOD["INPUT_CORRECTION_RUN"] == ""  # the validate step is always given the variable


# --- the verification step, run under bash on real directories --------------------------------


def verify_script(job_name: str) -> str:
    steps = _steps(load()["jobs"][job_name])
    return str(next(s for s in steps if VERIFY_STEP in str(s.get("name")))["run"])


def make_committed(root: Path) -> Path:
    directory = root / BUNDLE
    directory.mkdir(parents=True)
    for name in sorted(COMMITTED_FILES):
        (directory / name).write_text(f"{name}\n", encoding="utf-8", newline="\n")
    write_sums(directory)
    return directory


def run_verify(root: Path, job_name: str, bundle: str = BUNDLE) -> subprocess.CompletedProcess[str]:
    assert not EXPRESSION.search(verify_script(job_name))
    env = {k: v for k, v in os.environ.items() if k != "CORRECTION_BUNDLE"}
    env["CORRECTION_BUNDLE"] = bundle
    return subprocess.run(
        [_bash(), "-c", verify_script(job_name)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_an_intact_committed_bundle_passes_the_platforms_check(
    tmp_path: Path, job_name: str
) -> None:
    make_committed(tmp_path)
    result = run_verify(tmp_path, job_name)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "matches its SHA256SUMS" in result.stdout


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
@pytest.mark.parametrize("name", sorted(COMMITTED_FILES))
def test_editing_any_committed_file_fails_the_step(
    tmp_path: Path, job_name: str, name: str
) -> None:
    directory = make_committed(tmp_path)
    (directory / name).write_text("edited after assembly\n", encoding="utf-8", newline="\n")
    result = run_verify(tmp_path, job_name)
    assert result.returncode != 0 and "::error::" in result.stdout
    assert "does not match its SHA256SUMS" in result.stdout


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_missing_directory_a_missing_sums_file_and_a_deleted_file_fail_the_step(
    tmp_path: Path, job_name: str
) -> None:
    absent = run_verify(tmp_path, job_name)
    assert absent.returncode != 0 and "not in this checkout" in absent.stdout
    directory = make_committed(tmp_path)
    (directory / "tree.txt").unlink()
    gone = run_verify(tmp_path, job_name)
    assert gone.returncode != 0 and "does not match its SHA256SUMS" in gone.stdout
    (directory / SUMS_NAME).unlink()
    unsigned = run_verify(tmp_path, job_name)
    assert unsigned.returncode != 0 and "has no SHA256SUMS" in unsigned.stdout


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_link_in_place_of_the_directory_or_the_sums_file_fails_the_step(
    tmp_path: Path, job_name: str
) -> None:
    real = make_committed(tmp_path / "elsewhere")
    link = tmp_path / "corrections" / "2026-10-12" / "acme-org__disposable-target"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available")
    result = run_verify(tmp_path, job_name)
    assert result.returncode != 0 and "not in this checkout" in result.stdout


def test_sha256sum_alone_does_not_see_an_added_file_which_is_why_the_command_checks_the_set(
    tmp_path: Path,
) -> None:
    directory = make_committed(tmp_path)
    (directory / "run.log").write_text("internal\n", encoding="utf-8")
    result = run_verify(tmp_path, DRY_RUN_JOB)
    assert (
        result.returncode == 0
    )  # the platform tool passes; sums_problems() refuses (tested there)
    from repository_presenter.components.readme_correction.committed import sums_problems

    assert sums_problems(directory) == ["run.log is not part of a committed correction bundle"]


# --- negative controls: each rule rejects a deliberately broken workflow -------------------------


def _broken(mutate: Any) -> dict[str, Any]:
    workflow = copy.deepcopy(load())
    mutate(workflow)
    return workflow


def _index(workflow: dict[str, Any], job: str, fragment: str) -> int:
    steps = workflow["jobs"][job]["steps"]
    return next(
        i for i, s in enumerate(steps) if fragment in f"{s.get('name', '')} {s.get('uses', '')}"
    )


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_workflow_without_the_verification_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        del workflow["jobs"][job_name]["steps"][_index(workflow, job_name, VERIFY_STEP)]

    assert correction_mode_violations(_broken(mutate))


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_verification_after_the_token_is_minted_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        steps = workflow["jobs"][job_name]["steps"]
        step = steps.pop(_index(workflow, job_name, VERIFY_STEP))
        steps.insert(_index(workflow, job_name, "actions/create-github-app-token") + 1, step)

    assert any("minted" in v for v in correction_mode_violations(_broken(mutate)))


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_verification_after_dependencies_are_installed_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        steps = workflow["jobs"][job_name]["steps"]
        step = steps.pop(_index(workflow, job_name, VERIFY_STEP))
        steps.insert(_index(workflow, job_name, "actions/setup-python") + 1, step)

    assert any("installed" in v for v in correction_mode_violations(_broken(mutate)))


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_verification_that_is_not_gated_on_correction_mode_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        del workflow["jobs"][job_name]["steps"][_index(workflow, job_name, VERIFY_STEP)]["if"]

    assert any("gated" in v for v in correction_mode_violations(_broken(mutate)))


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_verification_that_does_not_check_the_digests_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        step = workflow["jobs"][job_name]["steps"][_index(workflow, job_name, VERIFY_STEP)]
        step["run"] = str(step["run"]).replace("sha256sum --check", "true")

    assert any("SHA256SUMS" in v for v in correction_mode_violations(_broken(mutate)))


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_command_that_does_not_require_the_committed_digests_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        final = workflow["jobs"][job_name]["steps"][-1]
        final["run"] = str(final["run"]).replace(" --require-sums", "")

    assert any("committed digests" in v for v in correction_mode_violations(_broken(mutate)))


@pytest.mark.parametrize("job_name", [DRY_RUN_JOB, WRITE_JOB])
def test_a_command_that_is_not_given_the_bundle_is_rejected(job_name: str) -> None:
    def mutate(workflow: dict[str, Any]) -> None:
        final = workflow["jobs"][job_name]["steps"][-1]
        final["run"] = str(final["run"]).replace('--correction-bundle "$CORRECTION_BUNDLE" ', "")

    assert any("not given the bundle" in v for v in correction_mode_violations(_broken(mutate)))


def test_the_workflow_still_passes_actionlint_when_it_is_installed() -> None:
    import shape_checks

    binary = shape_checks.find_actionlint()
    if binary is None:
        pytest.skip("actionlint is not installed (set ACTIONLINT or put it on PATH)")
    done = subprocess.run(
        [binary, "-no-color", str(WORKFLOWS / PROPOSE)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stdout + done.stderr
