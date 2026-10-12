"""Which runner the seal pipeline (present.yml) runs on, parsed from the YAML itself (hosted YAML
cannot run offline; tests/test_sealing_workflow.py takes the same approach).

Owner decision D5 (docs/SELF_HOSTED_RUNNER.md): production sealing may run on the owner's machine,
chosen by the repository variable REPOSITORY_PRESENTER_SEAL_RUNNER, with the hosted run as the
default until the owner sets it. What these pin, each with a negative control where a check can be
written as a function:

- the choice is made once, by a hosted job that holds no secret, and `present` reads it from that
  job's output; no other workflow names the self-hosted labels;
- unset, empty or `ubuntu-latest` give exactly the hosted run (runner, shell, timeout), for every
  trigger; any other value fails closed; the self-hosted choice is refused for every trigger that is
  not a schedule, a dispatch or a repository dispatch on the default branch, with the select step
  executed under bash against hostile values;
- every provisioning step is hosted-only and every self-hosted step is self-hosted-only;
- the gateway key and the App secrets are named only by the steps that use them, never at job level,
  and nothing persists a credential;
- a self-hosted job starts from an empty workspace and ends by emptying it, with a guard that
  refuses to empty anything outside the runner's work folder (executed under bash).
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from support import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PRESENT = "present.yml"
SELECT_JOB = "select-runner"
PRESENT_JOB = "present"
SELECT_STEP = "select"
SELECT_NAME = "Select the runner; refuse an untrusted trigger for the self-hosted one"
SELF_HOSTED = "${{ runner.environment == 'self-hosted' }}"
SELF_HOSTED_ALWAYS = "${{ always() && runner.environment == 'self-hosted' }}"
HOSTED = "${{ runner.environment == 'github-hosted' }}"
WIPE_START = "Start from an empty workspace (self-hosted)"
WIPE_END = "Leave nothing behind (self-hosted)"
VERIFY_STEP = "Verify the machine environment (self-hosted, read-only)"
LABELS = ["self-hosted", "windows", "x64", "repository-presenter-seal"]
GATEWAY_SECRETS = ("GPT_OSS_API_KEY", "GPT_OSS_ENDPOINT")
PROVISIONING_ACTIONS = (
    "actions/setup-python@",
    "astral-sh/setup-uv@",
    "actions/setup-dotnet@",
    "actions/setup-java@",
    "actions/setup-node@",
    "actions/setup-go@",
    "dtolnay/rust-toolchain@",
)
PROVISIONING_COMMANDS = ("apt-get", "uv python install", "uv venv", "npm install")

sys.path.insert(0, str(REPO_ROOT / "tools" / "workflow_rehearsal"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "runner"))
import check_runner  # noqa: E402
import hosting_preflight  # noqa: E402
import inventory  # noqa: E402


def _load(name: str = PRESENT) -> dict[str, Any]:
    loaded = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"{name} is not a YAML mapping"
    return loaded


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return list(job.get("steps", []))


def _named(job: dict[str, Any], name: str) -> dict[str, Any]:
    return next(step for step in _steps(job) if step.get("name") == name)


# --- the structural checks: each returns the list of violations, empty when the rule holds --------


def selection_violations(workflow: dict[str, Any]) -> list[str]:
    """The choice is made once, on a hosted job with no secret; `present` only reads it."""
    jobs = workflow["jobs"]
    found: list[str] = []
    select = jobs.get(SELECT_JOB, {})
    if select.get("runs-on") != "ubuntu-latest":
        found.append("select-runner must run on ubuntu-latest, never on the machine it chooses")
    if select.get("permissions") != {}:
        found.append("select-runner must hold no token permission (permissions: {})")
    if not select.get("timeout-minutes"):
        found.append("select-runner has no timeout")
    if "secrets." in yaml.safe_dump(select):
        found.append("select-runner reads a secret")
    present = jobs.get(PRESENT_JOB, {})
    if present.get("needs") != SELECT_JOB:
        found.append("present must need select-runner")
    runs_on = str(present.get("runs-on", ""))
    if runs_on != "${{ fromJSON(needs.select-runner.outputs.runs_on) }}":
        found.append("present must take runs-on from the select-runner output alone")
    if "self-hosted" in runs_on or "vars." in runs_on:
        found.append("present decides the runner itself")
    if "needs.select-runner.outputs.timeout_minutes" not in str(present.get("timeout-minutes")):
        found.append("present's timeout does not come from the selection")
    shell = (present.get("defaults") or {}).get("run", {}).get("shell")
    if shell != "${{ needs.select-runner.outputs.shell }}":
        found.append("present's shell does not come from the selection")
    return found


def provisioning_violations(workflow: dict[str, Any]) -> list[str]:
    """A step that installs or downloads a toolchain is hosted-only; a self-hosted step is
    self-hosted-only; nothing else is conditional on the runner."""
    found: list[str] = []
    for step in _steps(workflow["jobs"][PRESENT_JOB]):
        label = str(step.get("name") or step.get("uses"))
        provisions = str(step.get("uses", "")).startswith(PROVISIONING_ACTIONS) or any(
            command in str(step.get("run", "")) for command in PROVISIONING_COMMANDS
        )
        condition = step.get("if")
        if "(self-hosted" in label:
            if condition not in (SELF_HOSTED, SELF_HOSTED_ALWAYS):
                found.append(f"{label}: a self-hosted step must be self-hosted-only")
        elif provisions and condition != HOSTED:
            found.append(f"{label}: a provisioning step must be hosted-only")
    return found


def secret_violations(workflow: dict[str, Any]) -> list[str]:
    """The gateway key and the App secrets are named by their own steps only."""
    found: list[str] = []
    job = workflow["jobs"][PRESENT_JOB]
    job_level = yaml.safe_dump({k: v for k, v in job.items() if k != "steps"})
    for marker in ("secrets.", "steps.app-token", "github.token"):
        if marker in job_level:
            found.append(f"present names {marker} at job level")
    if "secrets." in yaml.safe_dump(workflow["jobs"][SELECT_JOB]):
        found.append("select-runner reads a secret")
    checkout = next(
        s for s in _steps(job) if str(s.get("uses", "")).startswith("actions/checkout@")
    )
    if (checkout.get("with") or {}).get("persist-credentials") is not False:
        found.append("the checkout persists its credential")
    for step in _steps(job):
        if "(self-hosted" in str(step.get("name")):
            text = yaml.safe_dump(step)
            if "secrets." in text or "steps.app-token" in text:
                found.append(f"{step['name']}: a self-hosted housekeeping step reads a secret")
    if (
        str(_named(job, VERIFY_STEP).get("run")).strip()
        != "python tools/runner/check_runner.py --job"
    ):
        found.append("the machine check must run with --job (no network, no secret)")
    return found


def hygiene_violations(workflow: dict[str, Any]) -> list[str]:
    """The workspace is emptied before the clone and after everything else, guarded."""
    found: list[str] = []
    steps = _steps(workflow["jobs"][PRESENT_JOB])
    names = [str(s.get("name") or s.get("uses")) for s in steps]
    checkout_at = next(
        i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("actions/checkout@")
    )
    if names[0] != WIPE_START or names.index(WIPE_START) > checkout_at:
        found.append("the first step must empty the workspace, before the checkout")
    if names[-1] != WIPE_END:
        found.append("the last step must leave nothing behind")
    if "always()" not in str(steps[-1].get("if")):
        found.append("the final cleanup must run whatever happened (always())")
    for name in (WIPE_START, WIPE_END):
        step = next((s for s in steps if s.get("name") == name), None)
        if step is None:
            found.append(f"{name}: the step is missing")
            continue
        script = str(step.get("run"))
        if "/?*/?*" not in script or "cygpath -u" not in script:
            found.append(f"{name}: no guard against emptying outside the runner work folder")
        if re.search(r"rm -rf [\"']?\$(?:RUNNER_TEMP|GITHUB_WORKSPACE)[\"']?(?:\s|$)", script):
            found.append(f"{name}: removes the temp folder or the workspace itself")
    return found


def all_violations(workflow: dict[str, Any]) -> list[str]:
    return [
        *selection_violations(workflow),
        *provisioning_violations(workflow),
        *secret_violations(workflow),
        *hygiene_violations(workflow),
    ]


def test_the_present_workflow_satisfies_every_rule() -> None:
    assert all_violations(_load()) == []


def test_no_other_workflow_runs_anything_on_the_self_hosted_runner() -> None:
    """D5: the monitor, the publication, the proposals and the issues stay hosted."""
    for path in sorted(WORKFLOWS.glob("*.yml")):
        if path.name == PRESENT:
            continue
        for job_id, job in (_load(path.name).get("jobs") or {}).items():
            runs_on = str(job.get("runs-on", ""))
            assert "self-hosted" not in runs_on, (
                f"{path.name}:{job_id} asks for a self-hosted runner"
            )
            assert "REPOSITORY_PRESENTER_SEAL_RUNNER" not in yaml.safe_dump(job)


def test_the_labels_the_workflow_asks_for_are_the_ones_the_preflight_and_the_docs_check() -> None:
    script = str(_named(_load()["jobs"][SELECT_JOB], SELECT_NAME)["run"])
    asked = re.search(r"runs_on='(\[[^']+\])'", script)
    assert asked is not None
    assert json.loads(asked.group(1)) == LABELS
    assert list(hosting_preflight.SEAL_RUNNER_LABELS) == LABELS
    doc = (REPO_ROOT / "docs" / "SELF_HOSTED_RUNNER.md").read_text(encoding="utf-8")
    assert "repository-presenter-seal" in doc and "REPOSITORY_PRESENTER_SEAL_RUNNER" in doc


def test_the_pinned_interpreter_is_the_one_the_machine_check_expects() -> None:
    step = _named(
        _load()["jobs"][PRESENT_JOB], "Pinned interpreter and virtual environment (self-hosted)"
    )
    pinned = step["env"]["EXPECTED_PYTHON"]
    assert check_runner.expected_python_from_workflow() == pinned == check_runner.FALLBACK_PYTHON


# negative controls: each rule must reject a deliberately broken copy


def _broken(mutate: Any) -> list[str]:
    workflow = copy.deepcopy(_load())
    mutate(workflow)
    return all_violations(workflow)


@pytest.mark.parametrize(
    ("label", "mutate", "expected"),
    [
        (
            "select job moved onto the machine",
            lambda w: w["jobs"][SELECT_JOB].update({"runs-on": "self-hosted"}),
            "must run on ubuntu-latest",
        ),
        (
            "select job given a token",
            lambda w: w["jobs"][SELECT_JOB].pop("permissions"),
            "no token permission",
        ),
        (
            "present chooses its own runner",
            lambda w: w["jobs"][PRESENT_JOB].update(
                {"runs-on": "${{ vars.X == 'a' && 'self-hosted' || 'ubuntu-latest' }}"}
            ),
            "runs-on from the select-runner output alone",
        ),
        (
            "present stops waiting for the selection",
            lambda w: w["jobs"][PRESENT_JOB].pop("needs"),
            "must need select-runner",
        ),
        (
            "toolchain install runs on the machine",
            lambda w: _named(w["jobs"][PRESENT_JOB], "Go for the Go verifier (go)").pop("if"),
            "must be hosted-only",
        ),
        (
            "apt-get runs on the machine",
            lambda w: _named(
                w["jobs"][PRESENT_JOB],
                "GCC, CMake and Ninja for the C++ verifier (g++, cmake, ninja)",
            ).pop("if"),
            "must be hosted-only",
        ),
        (
            "self-hosted step runs hosted too",
            lambda w: _named(w["jobs"][PRESENT_JOB], VERIFY_STEP).pop("if"),
            "must be self-hosted-only",
        ),
        (
            "gateway key at job level",
            lambda w: w["jobs"][PRESENT_JOB].update(
                {"env": {"K": "${{ secrets.GPT_OSS_API_KEY }}"}}
            ),
            "at job level",
        ),
        (
            "checkout persists its credential",
            lambda w: _steps(w["jobs"][PRESENT_JOB])[1]["with"].update(
                {"persist-credentials": True}
            ),
            "persists its credential",
        ),
        (
            "machine check reaches the network",
            lambda w: _named(w["jobs"][PRESENT_JOB], VERIFY_STEP).update(
                {"run": "python tools/runner/check_runner.py"}
            ),
            "--job",
        ),
        (
            "no cleanup at the end",
            lambda w: w["jobs"][PRESENT_JOB]["steps"].pop(),
            "last step must leave nothing behind",
        ),
        (
            "cleanup skipped on failure",
            lambda w: w["jobs"][PRESENT_JOB]["steps"][-1].update(
                {"if": "${{ runner.environment == 'self-hosted' }}"}
            ),
            "whatever happened",
        ),
        (
            "wipe after the checkout",
            lambda w: w["jobs"][PRESENT_JOB]["steps"].insert(
                2, w["jobs"][PRESENT_JOB]["steps"].pop(0)
            ),
            "before the checkout",
        ),
        (
            "wipe without its guard",
            lambda w: w["jobs"][PRESENT_JOB]["steps"][0].update(
                {"run": 'rm -rf "$GITHUB_WORKSPACE"'}
            ),
            "no guard",
        ),
    ],
)
def test_negative_control_each_rule_rejects_a_broken_copy(
    label: str, mutate: Any, expected: str
) -> None:
    found = _broken(mutate)
    assert any(expected in line for line in found), (label, found)


# --- the select step, executed under bash against every trigger and hostile values -------------

DEFAULT_OUTPUT = {
    "runs_on": '"ubuntu-latest"',
    "shell": "bash -e {0}",
    "timeout_minutes": "360",
}
TRUSTED_EVENTS = ["schedule", "workflow_dispatch", "repository_dispatch"]
UNTRUSTED_EVENTS = [
    "pull_request",
    "pull_request_target",
    "push",
    "issue_comment",
    "issues",
    "workflow_run",
    "release",
    "fork",
    "",
]


def _bash() -> str:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available to execute the select step")
    probe = subprocess.run([bash, "-c", "echo ok"], capture_output=True, text=True, check=False)
    if probe.stdout.strip() != "ok":
        pytest.skip("bash on PATH is not a working POSIX shell (a WSL launcher?)")
    return bash


def _select(
    tmp_path: Path,
    selected: str,
    event: str = "workflow_dispatch",
    ref: str = "refs/heads/main",
    default_branch: str = "main",
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    step = _named(_load()["jobs"][SELECT_JOB], SELECT_NAME)
    assert step["id"] == SELECT_STEP
    script = str(step["run"])
    assert "${{" not in script, "the select script interpolates a workflow expression"
    assert set(step["env"]) == {"SELECTED", "EVENT_NAME", "REF", "DEFAULT_BRANCH"}
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("SELECTED", "EVENT_NAME", "REF", "DEFAULT_BRANCH")
    }
    output = tmp_path / "output"
    output.write_text("", encoding="utf-8")
    env.update(
        SELECTED=selected,
        EVENT_NAME=event,
        REF=ref,
        DEFAULT_BRANCH=default_branch,
        GITHUB_OUTPUT=output.as_posix(),
    )
    result = subprocess.run(
        [_bash(), "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    written = {
        key: value
        for key, _, value in (
            line.partition("=") for line in output.read_text(encoding="utf-8").splitlines()
        )
    }
    return result, written


@pytest.mark.parametrize("selected", ["", "ubuntu-latest"])
@pytest.mark.parametrize("event", [*TRUSTED_EVENTS, *UNTRUSTED_EVENTS])
@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/heads/feature", "refs/pull/7/merge"])
def test_unset_or_hosted_is_exactly_the_hosted_run_for_every_trigger(
    tmp_path: Path, selected: str, event: str, ref: str
) -> None:
    result, written = _select(tmp_path, selected, event, ref)
    assert result.returncode == 0, result.stdout + result.stderr
    assert written == DEFAULT_OUTPUT
    assert json.loads(written["runs_on"]) == "ubuntu-latest"
    assert json.loads(written["timeout_minutes"]) == 360


@pytest.mark.parametrize("event", TRUSTED_EVENTS)
def test_self_hosted_is_selected_for_a_trusted_trigger_on_the_default_branch(
    tmp_path: Path, event: str
) -> None:
    result, written = _select(tmp_path, "self-hosted-windows", event)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(written["runs_on"]) == LABELS
    assert written["shell"] == "bash"
    assert json.loads(written["timeout_minutes"]) == 120
    assert set(written) == {"runs_on", "shell", "timeout_minutes"}


@pytest.mark.parametrize("event", UNTRUSTED_EVENTS)
@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/pull/7/merge", "refs/heads/feature"])
def test_self_hosted_is_refused_for_every_untrusted_trigger(
    tmp_path: Path, event: str, ref: str
) -> None:
    result, written = _select(tmp_path, "self-hosted-windows", event, ref)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    assert written == {}


@pytest.mark.parametrize("event", TRUSTED_EVENTS)
@pytest.mark.parametrize(
    "ref",
    ["refs/heads/feature", "refs/tags/v1", "refs/pull/7/merge", "refs/heads/main2", "main", ""],
)
def test_self_hosted_is_refused_off_the_default_branch(
    tmp_path: Path, event: str, ref: str
) -> None:
    result, written = _select(tmp_path, "self-hosted-windows", event, ref)
    assert result.returncode != 0 and written == {}
    assert "::error::" in result.stdout


def test_the_default_branch_is_the_repository_s_and_falls_back_to_main(tmp_path: Path) -> None:
    ok, written = _select(
        tmp_path, "self-hosted-windows", ref="refs/heads/trunk", default_branch="trunk"
    )
    assert ok.returncode == 0 and json.loads(written["runs_on"]) == LABELS
    renamed, none = _select(
        tmp_path, "self-hosted-windows", ref="refs/heads/main", default_branch="trunk"
    )
    assert renamed.returncode != 0 and none == {}
    # A payload with no repository block (a schedule may carry none) means `main`, never "any ref".
    fallback, written = _select(tmp_path, "self-hosted-windows", "schedule", "refs/heads/main", "")
    assert fallback.returncode == 0 and json.loads(written["runs_on"]) == LABELS
    refused, none = _select(tmp_path, "self-hosted-windows", "schedule", "refs/heads/other", "")
    assert refused.returncode != 0 and none == {}


HOSTILE_VALUES = [
    "self-hosted",
    "Self-Hosted-Windows",
    "self-hosted-windows ",
    " self-hosted-windows",
    "self-hosted-windows\nruns_on=evil",
    "ubuntu-latest\nruns_on=evil",
    "ubuntu-24.04",
    "windows-latest",
    "self-hosted-linux",
    "true",
    "1",
    "x; touch pwned",
    "$(touch pwned)",
    "::set-output name=runs_on::evil",
]


@pytest.mark.parametrize("value", HOSTILE_VALUES)
def test_any_other_value_fails_closed_and_is_never_echoed(tmp_path: Path, value: str) -> None:
    result, written = _select(tmp_path, value)
    assert result.returncode != 0
    assert "::error::" in result.stdout
    assert written == {}
    assert not (tmp_path / "pwned").exists()
    assert "evil" not in result.stdout + result.stderr
    assert "touch" not in result.stdout + result.stderr


def test_negative_control_an_interpolated_choice_would_have_emitted_an_injected_output(
    tmp_path: Path,
) -> None:
    """The shape this job avoids: the variable pasted into the script instead of passed in env."""
    hostile = "ubuntu-latest\nruns_on=evil"
    script = 'selected="' + hostile + '"\necho "runs_on=$selected" >> "$GITHUB_OUTPUT"\n'
    output = tmp_path / "output"
    env = {**os.environ, "GITHUB_OUTPUT": output.as_posix()}
    subprocess.run([_bash(), "-c", script], env=env, cwd=tmp_path, check=True, capture_output=True)
    assert "runs_on=evil" in output.read_text(encoding="utf-8").splitlines()


# --- the workspace guard, executed under bash against a throwaway runner layout -----------------


def _shim_dir(tmp_path: Path) -> Path | None:
    """Where a `cygpath` that returns its argument lives, on a machine that has none. Git for
    Windows ships the real one, and the runner's paths are Windows paths there."""
    if shutil.which("cygpath"):
        return None
    shim = tmp_path / "shim"
    shim.mkdir()
    script = shim / "cygpath"
    script.write_text('#!/bin/sh\nshift\nprintf "%s\\n" "$1"\n', encoding="utf-8", newline="\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return shim


def _native(path: Path) -> str:
    """The path as the runner reports it: native on Windows, POSIX elsewhere."""
    return str(path) if shutil.which("cygpath") else path.as_posix()


def _runner_layout(tmp_path: Path) -> dict[str, Path]:
    work = tmp_path / "runner" / "_work"
    layout = {
        "work": work,
        "temp": work / "_temp",
        "workspace": work / "repository-presenter" / "repository-presenter",
        "neighbour": work / "other-repo" / "other-repo",
    }
    for directory in layout.values():
        directory.mkdir(parents=True)
    (layout["workspace"] / ".git" / "objects").mkdir(parents=True)
    locked = layout["workspace"] / ".git" / "objects" / "pack.idx"
    locked.write_text("x", encoding="utf-8")
    locked.chmod(stat.S_IREAD)
    (layout["workspace"] / "runs" / "transactions").mkdir(parents=True)
    (layout["workspace"] / "runs" / "transactions" / "calls.jsonl").write_text(
        "{}", encoding="utf-8"
    )
    (layout["workspace"] / ".hidden").write_text("x", encoding="utf-8")
    (layout["workspace"] / "README.md").write_text("x", encoding="utf-8")
    (layout["neighbour"] / "keep.txt").write_text("keep", encoding="utf-8")
    (layout["temp"] / "step-output").write_text("keep", encoding="utf-8")
    for name in ("rp-venv", "noop-proof", "sealed-export", "transaction-artifact"):
        (layout["temp"] / name).mkdir()
        (layout["temp"] / name / "f").write_text("x", encoding="utf-8")
    (layout["temp"] / "rp-python").mkdir()
    return layout


def _run_housekeeping(
    tmp_path: Path, step_name: str, workspace: Path, temp: Path
) -> subprocess.CompletedProcess[str]:
    script = str(_named(_load()["jobs"][PRESENT_JOB], step_name)["run"])
    assert "${{" not in script
    env = dict(os.environ)
    shim = _shim_dir(tmp_path)
    if shim is not None:
        env["PATH"] = shim.as_posix() + os.pathsep + env.get("PATH", "")
    env.update(GITHUB_WORKSPACE=_native(workspace), RUNNER_TEMP=_native(temp))
    return subprocess.run(
        [_bash(), "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("step_name", [WIPE_START, WIPE_END])
def test_housekeeping_empties_the_workspace_and_its_own_temp_folders_only(
    tmp_path: Path, step_name: str
) -> None:
    layout = _runner_layout(tmp_path)
    result = _run_housekeeping(tmp_path, step_name, layout["workspace"], layout["temp"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert layout["workspace"].is_dir() and list(layout["workspace"].iterdir()) == []
    for name in ("rp-venv", "noop-proof", "sealed-export", "transaction-artifact"):
        assert not (layout["temp"] / name).exists()
    # What is not this job's own survives: the runner's step files, another repository's
    # workspace, and a temp subfolder this job did not make.
    assert (layout["temp"] / "step-output").is_file()
    assert (layout["temp"] / "rp-python").is_dir()
    assert (layout["neighbour"] / "keep.txt").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("step_name", [WIPE_START, WIPE_END])
@pytest.mark.parametrize("where", ["outside", "work-root", "one-level", "shallow-temp"])
def test_housekeeping_refuses_to_empty_outside_the_runner_work_folder(
    tmp_path: Path, step_name: str, where: str
) -> None:
    layout = _runner_layout(tmp_path)
    workspace, temp = layout["workspace"], layout["temp"]
    if where == "outside":
        workspace = tmp_path / "somewhere" / "else" / "entirely"
        workspace.mkdir(parents=True)
        (workspace / "precious").write_text("x", encoding="utf-8")
    elif where == "work-root":
        workspace = layout["work"]
    elif where == "one-level":
        workspace = layout["work"] / "repository-presenter"
    else:
        # A temp folder directly under a shallow parent: the work folder is not recognisable.
        temp = Path(tmp_path.anchor) / "_temp"
        workspace = layout["workspace"]
    result = _run_housekeeping(tmp_path, step_name, workspace, temp)
    survivors = [workspace / "precious", layout["workspace"] / "README.md"]
    assert any(path.exists() for path in survivors), "the guard let the workspace be emptied"
    if step_name == WIPE_START:
        assert result.returncode != 0 and "::error::" in result.stdout
    else:
        assert result.returncode == 0 and "::warning::" in result.stdout
    assert (layout["neighbour"] / "keep.txt").is_file()
    assert (layout["temp"] / "step-output").is_file()


# --- the inventory renders the new shape without breaking its table ---------------------------


def test_the_inventory_renders_a_runs_on_expression_without_a_pipe() -> None:
    cell = inventory._runs_on("${{ a == 'x' && fromJSON('[1]') || 'ubuntu-latest' }}")
    assert "|" not in cell and cell.startswith("`") and cell.endswith("`")
    assert inventory._runs_on("ubuntu-latest") == "ubuntu-latest"
    assert inventory._runs_on(["self-hosted", "windows"]) == "self-hosted, windows"
    rows = {r["file"]: r for r in inventory.inventory()}
    jobs = {job["id"]: job for job in rows[PRESENT]["jobs"]}
    assert jobs[SELECT_JOB]["runs_on"] == "ubuntu-latest"
    assert "REPOSITORY_PRESENTER_SEAL_RUNNER" in rows[PRESENT]["variables"]
