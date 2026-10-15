"""Hosting preflight: a go/no-go table for the staged go-live H0..H4 (TC-REF-12-01).

Read-only. It compares what the workflows *need* (generated from ``.github/workflows/*.yml`` by
``inventory.py``: secrets, variables, App token scopes, write jobs, environments) with what the
control repository *has* (read-only ``gh`` calls), and prints one verdict per stage plus the owner
action every missing item needs. Names and verdicts only: a variable's value is reduced to
open / closed, a secret's value is never requested, nothing from the environment is printed.

    python tools/workflow_rehearsal/hosting_preflight.py [--repo OWNER/NAME] [--stage H1]
        [--confirm CHECK_ID ...] [--json]

Exit 0: the table was produced (and, with ``--stage``, that stage is GO). Exit 1: ``--stage`` is
NO-GO. Exit 2: ``gh`` is unavailable or unauthenticated, so nothing could be read - doubt never
passes. The stages (docs/OPERATIONS_RUNBOOK.md section 9, plan TC-REF-12): H0 hosted dry run with
every write gate closed; H1 shadow (monitor, seal, commit-back to the control repository only); H2
approved issues; H3 PR pilot on owner-named repositories; H4 per-repository expansion.

Owner decision D5 puts production sealing on a self-hosted runner (docs/SELF_HOSTED_RUNNER.md). When a
workflow reads ``REPOSITORY_PRESENTER_SEAL_RUNNER`` the preflight also requires, from H0 on (the first
seal is the H0 pilot), that the owner has selected that runner, that it is registered and online with
the labels the workflow asks for, that fork pull requests need the owner's approval (the repository is
public), and, as operator confirmations, that the machine check and the account isolation were done.
Until then those items are NO-GO: the workflow keeps running hosted, which is its default.

Standard library plus the sibling ``inventory`` module (PyYAML, already a project dependency). It
only reads: every ``gh`` call passes ``assert_read_only`` before it runs, and the tool has no code
path that sets a variable or a secret, dispatches or enables a workflow, or writes a repository.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventory

REPO_ROOT = inventory.REPO_ROOT
DEFAULT_REPO = "babar-raza/repository-presenter"
STAGES = ("H0", "H1", "H2", "H3", "H4")
STAGE_TITLES = {
    "H0": "hosted dry run: schedules on, every write gate closed",
    "H1": "shadow: monitor, seal and commit-back to the control repository only",
    "H2": "approved upstream issues",
    "H3": "pull-request pilot on owner-named repositories",
    "H4": "per-repository expansion, one owner record each",
}
# Write gate variable -> the stages in which it is open ("1"). A gate open before its stage is the
# unsafe direction, so the posture check refuses it for every earlier stage.
GATES = {
    "REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED": ("H1", "H2", "H3", "H4"),
    "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED": ("H2", "H3", "H4"),
    "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED": ("H3", "H4"),
}
PAUSE = "REPOSITORY_PRESENTER_SEALING_PAUSED"
# The runner the seal pipeline (present.yml) runs on. Not a write gate: unset means hosted.
SEAL_RUNNER = "REPOSITORY_PRESENTER_SEAL_RUNNER"
SEAL_RUNNER_SELF_HOSTED = "self-hosted-windows"
# The labels present.yml's select-runner job asks for (a test pins them to the YAML).
SEAL_RUNNER_LABELS = ("self-hosted", "windows", "x64", "repository-presenter-seal")
RUNNER_STAGE = "H0"
# On a public repository a fork's pull request may ask for a self-hosted runner in a workflow it
# rewrites; only the owner's approval of every outside contributor's run stops that.
FORK_APPROVAL_REQUIRED = "all_external_contributors"
# A second owner switch inside the issues stage (update comments on a filed issue): it narrows what the
# issues gate permits, so it is modelled as known but is not a stage gate of its own.
ISSUES_COMMENTS = "REPOSITORY_PRESENTER_ISSUES_COMMENTS_AUTHORIZED"
AMBIENT_SECRETS = {"GITHUB_TOKEN"}  # minted per run by GitHub, not a repository secret
NOT_A_CYCLE_WORKFLOW = {"mirror-gitlab.yml"}  # its secrets gate no go-live stage
WRITE_JOB_STAGE = {
    "candidates-publish.yml": "H1",
    "issues-scheduled.yml": "H2",
    "propose.yml": "H3",
    # The sandbox canary (docs/PROPOSAL_WAVE_RUNBOOK.md section 9) rehearses the H3 write job on the
    # owner's throwaway repository; it is held to the same environment-reviewers requirement.
    "propose-sandbox.yml": "H3",
}
RECORD_DIRS = {"H2": "ops/issue_approvals", "H3": "ops/proposal-authorizations"}
#: The file-name prefix of the sandbox canary's authorization record (`record_filename`).
SANDBOX_RECORD_PREFIX = "babar-raza__presenter-sandbox__"

OK, MISSING, UNKNOWN, CONFIRM, INFO = "OK", "MISSING", "UNKNOWN", "CONFIRM", "INFO"

Run = Callable[[list[str]], tuple[int, str, str]]


class GhUnavailable(RuntimeError):
    """``gh`` cannot run here (not installed, or no usable authentication)."""


def assert_read_only(args: list[str]) -> None:
    """Refuse any ``gh`` invocation that could write; the single choke point for every call."""
    if args[:2] in (
        ["variable", "list"],
        ["secret", "list"],
        ["workflow", "list"],
        ["run", "list"],
    ):
        return
    if args[:1] == ["api"]:
        for arg in args[1:]:
            if arg.startswith(("-X", "--method", "-f", "-F", "--field", "--raw-field", "--input")):
                raise ValueError(f"refusing a write-shaped gh api call: {arg.split('=')[0]}")
        return
    raise ValueError(f"refusing gh {' '.join(args[:2])}: not on the read-only list")


def _subprocess_run(args: list[str]) -> tuple[int, str, str]:
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1", "GH_PAGER": "cat"}
    try:
        done = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            env=env,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GhUnavailable(f"gh could not run: {type(error).__name__}") from error
    return done.returncode, done.stdout, done.stderr


class Gh:
    """Read-only access to one repository through an injectable runner (a fake in tests)."""

    def __init__(self, repo: str, run: Run | None = None) -> None:
        self.repo = repo
        self._run = run or _subprocess_run
        self.calls: list[list[str]] = []
        self._branch: str | None = None
        self._info: Any | None = None

    def json(self, args: list[str]) -> Any | None:
        """Parsed JSON of one read-only call, or ``None`` when it failed (never an exception)."""
        assert_read_only(args)
        self.calls.append(args)
        code, out, _ = self._run(args)
        if code != 0:
            return None
        try:
            return json.loads(out) if out.strip() else []
        except json.JSONDecodeError:
            return None

    def api(self, path: str) -> Any | None:
        return self.json(["api", path.format(repo=self.repo)])

    def info(self) -> Any | None:
        """``GET /repos/{repo}``, read once."""
        if self._info is None:
            self._info = self.api("repos/{repo}")
        return self._info

    def default_branch(self) -> str:
        if self._branch is None:
            self._branch = str(_nested(self.info(), "default_branch") or "main")
        return self._branch


# --- what the workflows need (generated from the YAML) ---------------------------------------


def required_secrets(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Secret name -> the workflow files that read it (ambient ``GITHUB_TOKEN`` excluded)."""
    users: dict[str, list[str]] = {}
    for row in rows:
        for name in row["secrets"]:
            if name not in AMBIENT_SECRETS:
                users.setdefault(name, []).append(row["file"])
    return dict(sorted(users.items()))


def required_check_contexts(directory: Path) -> list[str]:
    """The status-check names ``ci.yml`` produces (job name with its matrix expanded)."""
    path = directory / "ci.yml"
    if not path.is_file():
        return []
    contexts: list[str] = []
    for job_id, job in (inventory.load_workflow(path).get("jobs") or {}).items():
        name = str(job.get("name", job_id))
        matrix = (job.get("strategy") or {}).get("matrix") or {}
        axes = {
            k: v
            for k, v in matrix.items()
            if isinstance(v, list) and k not in ("include", "exclude")
        }
        for combo in itertools.product(*axes.values()) if axes else [()]:
            values = dict(zip(axes, combo, strict=True))
            contexts.append(
                re.sub(
                    r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}",
                    lambda m, v=values: str(v.get(m.group(1), "")),
                    name,
                )
            )
    return sorted(set(contexts))


def write_jobs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Jobs that mint an App token with a ``write`` scope, with the stage that first needs them."""
    found = []
    for row in rows:
        for job in row["jobs"]:
            scopes = [s for s in job["app_token_scopes"] if "=write" in s]
            if scopes:
                found.append(
                    {
                        "file": row["file"],
                        "job": job["id"],
                        "environment": job["environment"],
                        "scope": "; ".join(scopes),
                        "stage": WRITE_JOB_STAGE.get(row["file"], "H1"),
                    }
                )
    return found


# --- the checks -------------------------------------------------------------------------------


@dataclass
class Check:
    id: str
    title: str
    stage: str | None  # first stage that needs it; None = informational only
    status: str
    detail: str = ""
    action: str = ""


def _names(items: Any, key: str = "name") -> set[str] | None:
    if not isinstance(items, list):
        return None
    return {str(i[key]) for i in items if isinstance(i, dict) and key in i}


def _nested(payload: Any, key: str) -> Any:
    return payload.get(key) if isinstance(payload, dict) else None


def _gate_state(values: dict[str, str], name: str) -> str:
    return "open" if values.get(name) == "1" else "closed"


def _secret_checks(gh: Gh, rows: list[dict[str, Any]]) -> list[Check]:
    names = _names(gh.json(["secret", "list", "-R", gh.repo, "--json", "name"]))
    org = _names(_nested(gh.api("repos/{repo}/actions/organization-secrets"), "secrets"))
    present = None if names is None else names | (org or set())
    checks = []
    for name, files in required_secrets(rows).items():
        stage = None if set(files) <= NOT_A_CYCLE_WORKFLOW else "H0"
        title = f"secret {name} (read by {', '.join(files)})"
        if present is None:
            checks.append(
                Check(
                    f"secret:{name}",
                    title,
                    stage,
                    UNKNOWN,
                    "secret list unreadable",
                    "run with a token that may list repository secrets",
                )
            )
        elif name in present:
            checks.append(Check(f"secret:{name}", title, stage, OK))
        else:
            checks.append(
                Check(
                    f"secret:{name}",
                    title,
                    stage,
                    MISSING,
                    "not set",
                    f"owner: set the repository Actions secret {name}",
                )
            )
    return checks


def _variable_state(gh: Gh) -> tuple[dict[str, str] | None, set[str]]:
    items = gh.json(["variable", "list", "-R", gh.repo, "--json", "name,value"])
    if not isinstance(items, list):
        return None, set()
    values = {
        str(i["name"]): str(i.get("value", ""))
        for i in items
        if isinstance(i, dict) and "name" in i
    }
    return values, set(values)


def _variable_checks(
    gh: Gh, rows: list[dict[str, Any]]
) -> tuple[list[Check], dict[str, str] | None]:
    values, _ = _variable_state(gh)
    known = set(GATES) | {PAUSE, ISSUES_COMMENTS, SEAL_RUNNER}
    unmodelled = sorted({v for row in rows for v in row["variables"]} - known)
    checks = [
        Check(
            "variables:modelled",
            "every `vars.*` the workflows read is modelled by this preflight",
            "H0",
            MISSING if unmodelled else OK,
            f"unmodelled: {', '.join(unmodelled)}" if unmodelled else "",
            "update hosting_preflight.py GATES/PAUSE for the new variable" if unmodelled else "",
        )
    ]
    if values is None:
        checks.append(
            Check(
                "variables:readable",
                "repository variables readable",
                "H0",
                UNKNOWN,
                "variable list unreadable",
                "run with a token that may list repository variables",
            )
        )
        return checks, None
    paused = values.get(PAUSE) == "1"
    checks.append(
        Check(
            f"variable:{PAUSE}",
            "sealing is not paused (the kill switch is released)",
            "H1",
            MISSING if paused else OK,
            "paused" if paused else "not paused",
            f"owner: delete {PAUSE} or set it to 0 to resume sealing" if paused else "",
        )
    )
    return checks, values


def _posture_checks(values: dict[str, str] | None) -> list[Check]:
    """One row per stage: no write gate is open that the stage does not permit."""
    checks = []
    for stage in STAGES:
        if values is None:
            checks.append(
                Check(
                    f"posture:{stage}",
                    f"write gates not more open than {stage} permits",
                    stage,
                    UNKNOWN,
                    "variables unreadable",
                )
            )
            continue
        over = [g for g in GATES if _gate_state(values, g) == "open" and stage not in GATES[g]]
        checks.append(
            Check(
                f"posture:{stage}",
                f"write gates not more open than {stage} permits",
                stage,
                MISSING if over else OK,
                f"open too early: {', '.join(over)}" if over else "",
                f"owner: close {', '.join(over)} (unset the variable or set it to 0) before {stage}"
                if over
                else "",
            )
        )
    return checks


def _workflow_check(gh: Gh, rows: list[dict[str, Any]]) -> Check:
    listed = gh.json(["workflow", "list", "-R", gh.repo, "--all", "--json", "name,path,state"])
    title = "every workflow file is on the default branch and enabled"
    if not isinstance(listed, list):
        return Check(
            "workflows:enabled",
            title,
            "H0",
            UNKNOWN,
            "workflow list unreadable",
            "run with a token that may list workflows",
        )
    state = {
        Path(str(i.get("path", ""))).name: str(i.get("state", ""))
        for i in listed
        if isinstance(i, dict)
    }
    bad = [r["file"] for r in rows if state.get(r["file"]) != "active"]
    return Check(
        "workflows:enabled",
        title,
        "H0",
        MISSING if bad else OK,
        f"not active: {', '.join(bad)}" if bad else "",
        "owner: merge the workflow file or `gh workflow enable <file>`" if bad else "",
    )


def _protection_check(gh: Gh, directory: Path) -> list[Check]:
    branch = gh.default_branch()
    protection = gh.api(f"repos/{{repo}}/branches/{branch}/protection")
    expected = required_check_contexts(directory)
    title = f"{branch} is protected with the CI contexts required"
    if protection is None:
        return [
            Check(
                "branch:protection",
                title,
                "H0",
                UNKNOWN,
                "protection unreadable (no admin read, or not protected)",
                f"owner: protect {branch} with required checks "
                f"{', '.join(expected) or '(ci.yml)'}; read it with an admin token",
            )
        ]
    contexts = set(_nested(_nested(protection, "required_status_checks"), "contexts") or [])
    forced = _nested(_nested(protection, "allow_force_pushes"), "enabled")
    problems = (
        [f"required checks lack: {', '.join(sorted(set(expected) - contexts))}"]
        if set(expected) - contexts
        else []
    )
    problems += ["force pushes allowed"] if forced else []
    return [
        Check(
            "branch:protection",
            title,
            "H0",
            MISSING if problems else OK,
            "; ".join(problems),
            f"owner: fix branch protection on {branch}" if problems else "",
        )
    ]


def _app_checks(gh: Gh, rows: list[dict[str, Any]]) -> list[Check]:
    checks = []
    for workflow, label in (
        ("verify-app-installation.yml", "App credentials mint a token"),
        ("audit-app-installations.yml", "App is installed on the organizations in scope"),
    ):
        runs = gh.json(
            [
                "run",
                "list",
                "-R",
                gh.repo,
                "--workflow",
                workflow,
                "--status",
                "success",
                "--limit",
                "1",
                "--json",
                "databaseId,createdAt",
            ]
        )
        title = f"{label} (a successful {workflow} run)"
        if not isinstance(runs, list):
            checks.append(Check(f"app:{workflow}", title, "H0", UNKNOWN, "run list unreadable"))
        elif runs:
            checks.append(
                Check(f"app:{workflow}", title, "H0", OK, f"run {runs[0].get('databaseId')}")
            )
        else:
            checks.append(
                Check(
                    f"app:{workflow}",
                    title,
                    "H0",
                    MISSING,
                    "no successful run",
                    f"owner: install the App, then dispatch {workflow} once (read-only)",
                )
            )
    for job in write_jobs(rows):
        checks.append(
            Check(
                f"app-scope:{job['file']}:{job['job']}",
                f"App grants `{job['scope']}` for {job['file']}:{job['job']} and nothing wider",
                job["stage"],
                CONFIRM,
                "a user token cannot read an App's installation permissions",
                f"owner: confirm in the App settings, per organization in scope, then "
                f"--confirm app-scope:{job['file']}:{job['job']}",
            )
        )
    return checks


def _environment_checks(gh: Gh, rows: list[dict[str, Any]]) -> list[Check]:
    checks = []
    for job in write_jobs(rows):
        cid, name = f"environment:{job['file']}:{job['job']}", job["environment"]
        title = (
            f"write job {job['file']}:{job['job']} is guarded by an environment "
            "with required reviewers"
        )
        if not name:
            checks.append(
                Check(
                    cid,
                    title,
                    job["stage"],
                    MISSING,
                    "the job declares no `environment:`",
                    "workflow change (TC-REF-12) to declare an environment on the job, then "
                    "owner: create it with required reviewers",
                )
            )
            continue
        env = gh.api(f"repos/{{repo}}/environments/{name}")
        rules = _nested(env, "protection_rules") or []
        reviewers = [
            r for r in rules if isinstance(r, dict) and r.get("type") == "required_reviewers"
        ]
        checks.append(
            Check(
                cid,
                title,
                job["stage"],
                OK if reviewers else (UNKNOWN if env is None else MISSING),
                f"environment {name}" + ("" if reviewers else ": no required reviewers"),
                "" if reviewers else f"owner: add required reviewers to environment {name}",
            )
        )
    return checks


def _seal_runner_choice(values: dict[str, str] | None) -> tuple[str, str]:
    """(status, detail) of the owner's runner selection; the value is classified, not echoed."""
    if values is None:
        return UNKNOWN, "variables unreadable"
    selected = values.get(SEAL_RUNNER, "")
    if selected == SEAL_RUNNER_SELF_HOSTED:
        return OK, "self-hosted"
    if selected in ("", "ubuntu-latest"):
        return MISSING, "hosted (the default)"
    return MISSING, "an unrecognised value (the workflow refuses it)"


def _runner_checks(
    gh: Gh, rows: list[dict[str, Any]], values: dict[str, str] | None
) -> list[Check]:
    """D5: production sealing on the owner's self-hosted runner. Derived from the YAML: a tree in
    which no workflow reads the selection variable has no runner requirement."""
    if not any(SEAL_RUNNER in row["variables"] for row in rows):
        return []
    status, detail = _seal_runner_choice(values)
    checks = [
        Check(
            f"variable:{SEAL_RUNNER}",
            "the seal pipeline is set to run on the self-hosted runner (owner decision D5)",
            RUNNER_STAGE,
            status,
            detail,
            (
                f"owner: once the other runner items are OK, "
                f"`gh variable set {SEAL_RUNNER} --body {SEAL_RUNNER_SELF_HOSTED}` "
                "(docs/SELF_HOSTED_RUNNER.md section 6); unset it to go back to hosted"
            )
            if status != OK
            else "",
        )
    ]
    runners = _nested(gh.api("repos/{repo}/actions/runners"), "runners")
    title = f"a runner carrying {', '.join(SEAL_RUNNER_LABELS)} is registered and online"
    if not isinstance(runners, list):
        checks.append(
            Check(
                "runner:registered",
                title,
                RUNNER_STAGE,
                UNKNOWN,
                "runner list unreadable (needs repository admin)",
                "run with a token that may list the repository's self-hosted runners",
            )
        )
    else:
        wanted = {label.lower() for label in SEAL_RUNNER_LABELS}
        matching = [
            r
            for r in runners
            if isinstance(r, dict)
            and wanted
            <= {
                str(label.get("name", "")).lower()
                for label in r.get("labels") or []
                if isinstance(label, dict)
            }
        ]
        online = [r for r in matching if r.get("status") == "online"]
        if online:
            checks.append(
                Check("runner:registered", title, RUNNER_STAGE, OK, f"{len(online)} online")
            )
        else:
            checks.append(
                Check(
                    "runner:registered",
                    title,
                    RUNNER_STAGE,
                    MISSING,
                    "registered but offline"
                    if matching
                    else f"{len(runners)} runner(s) registered, none with the labels",
                    "owner: start the runner service on the machine"
                    if matching
                    else "owner: register the runner (docs/SELF_HOSTED_RUNNER.md section 3)",
                )
            )
    checks.append(_fork_approval_check(gh))
    checks += [
        Check(
            "runner:host-check",
            "tools/runner/check_runner.py passes on the runner machine, as the service account",
            RUNNER_STAGE,
            CONFIRM,
            "only the machine can say",
            "owner: run `python tools/runner/check_runner.py --work-dir <work folder> "
            "--runner-dir <runner folder>` there, then --confirm runner:host-check",
        ),
        Check(
            "runner:isolation",
            "the service account is the dedicated low-privilege user, with the deny rules and "
            "the LAN egress rule of docs/SELF_HOSTED_RUNNER.md section 4",
            RUNNER_STAGE,
            CONFIRM,
            "only the machine can say",
            "owner: do docs/SELF_HOSTED_RUNNER.md section 4, then --confirm runner:isolation",
        ),
    ]
    return checks


def _fork_approval_check(gh: Gh) -> Check:
    """A public repository's self-hosted runner is only as safe as the fork-run approval."""
    title = "a fork's workflow run needs the owner's approval before it can use a runner"
    private = _nested(gh.info(), "private")
    if private is True:
        return Check("runner:fork-approval", title, RUNNER_STAGE, OK, "private repository")
    policy = _nested(
        gh.api("repos/{repo}/actions/permissions/fork-pr-contributor-approval"), "approval_policy"
    )
    if policy is None:
        return Check(
            "runner:fork-approval",
            title,
            RUNNER_STAGE,
            UNKNOWN,
            "approval policy unreadable (needs repository admin)",
            "run with a token that may read the repository's Actions permissions",
        )
    if policy == FORK_APPROVAL_REQUIRED:
        return Check("runner:fork-approval", title, RUNNER_STAGE, OK, f"public; {policy}")
    return Check(
        "runner:fork-approval",
        title,
        RUNNER_STAGE,
        MISSING,
        f"public; policy is {policy}",
        "owner: Settings > Actions > General > Fork pull request workflows > Require approval "
        "for all external contributors, before the runner is registered "
        "(docs/SELF_HOSTED_RUNNER.md section 2)",
    )


def _record_checks(gh: Gh) -> list[Check]:
    branch = gh.default_branch()
    checks = []
    for stage, directory in RECORD_DIRS.items():
        listing = gh.api(f"repos/{{repo}}/contents/{directory}?ref={branch}")
        records = (
            [
                i
                for i in listing
                if isinstance(i, dict)
                and i.get("name") != "README.md"
                # The sandbox canary's own record (docs/PROPOSAL_WAVE_RUNBOOK.md section 9) is not
                # an owner approval of any product proposal: it must not turn this check green.
                and not (stage == "H3" and str(i.get("name", "")).startswith(SANDBOX_RECORD_PREFIX))
            ]
            if isinstance(listing, list)
            else None
        )
        title = f"owner records exist under {directory}/ on {branch}"
        what = "approved issue list" if stage == "H2" else "per-hash authorization records"
        if records is None:
            checks.append(
                Check(
                    f"records:{directory}",
                    title,
                    stage,
                    MISSING,
                    "directory absent",
                    f"owner: approve the exact {what} and merge the records pull request",
                )
            )
        else:
            checks.append(
                Check(
                    f"records:{directory}",
                    title,
                    stage,
                    OK if records else MISSING,
                    f"{len(records)} record(s)",
                    "" if records else f"owner: approve the exact {what}",
                )
            )
    return checks


def _registry_check() -> Check:
    path = REPO_ROOT / "data" / "registry.json"
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("entries") or []
        full = sorted(str(e["repository"]) for e in entries if e.get("mode") == "full")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return Check(
            "registry:pilot",
            "registry modes readable",
            "H3",
            UNKNOWN,
            "data/registry.json unreadable",
        )
    return Check(
        "registry:pilot",
        f"registry entries in mode `full` ({len(full)}) are exactly the owner-named pilot list",
        "H3",
        CONFIRM,
        f"{len(full)} entr{'y' if len(full) == 1 else 'ies'} in mode full",
        "owner: confirm the list (others back to dry_run), then --confirm registry:pilot",
    )


def collect(
    gh: Gh, directory: Path | None = None, confirmed: set[str] | None = None
) -> list[Check]:
    """Every check, in a stable order; confirmed manual items are promoted to OK."""
    directory = directory or inventory.WORKFLOWS_DIR
    rows = inventory.inventory(directory)
    variable_checks, values = _variable_checks(gh, rows)
    checks = [
        *_secret_checks(gh, rows),
        *variable_checks,
        *_posture_checks(values),
        _workflow_check(gh, rows),
        *_protection_check(gh, directory),
        *_app_checks(gh, rows),
        *_environment_checks(gh, rows),
        *_runner_checks(gh, rows, values),
        *_record_checks(gh),
        _registry_check(),
    ]
    for check in checks:
        if check.status == CONFIRM and check.id in (confirmed or set()):
            check.status, check.detail = OK, "confirmed by the operator for this run"
    return checks


def verdicts(checks: list[Check]) -> dict[str, dict[str, Any]]:
    """Per stage: GO only when every check required up to that stage is OK (UNKNOWN is NO-GO)."""
    result = {}
    for index, stage in enumerate(STAGES):
        blocking = [
            c.id
            for c in checks
            if c.stage in STAGES
            and STAGES.index(c.stage) <= index
            and c.status != OK
            and not (c.id.startswith("posture:") and c.stage != stage)
        ]
        result[stage] = {"title": STAGE_TITLES[stage], "go": not blocking, "blocking": blocking}
    return result


def render(repo: str, checks: list[Check]) -> str:
    out = [f"Hosting preflight for {repo} (read-only; names and verdicts only, no values)", ""]
    width = max(len(c.title) for c in checks)
    for c in checks:
        out.append(f"{c.status:<8} {c.stage or '-':<3} {c.title:<{width}}  {c.detail}".rstrip())
    out += ["", "GO / NO-GO"]
    verdict = verdicts(checks)
    for stage in STAGES:
        v = verdict[stage]
        out.append(
            f"{stage} {'GO' if v['go'] else 'NO-GO':<6} {v['title']}"
            + ("" if v["go"] else f"  [{len(v['blocking'])} blocking]")
        )
    out += ["", "Owner actions, in stage order"]
    seen: set[str] = set()
    for stage in (*STAGES, None):
        for c in checks:
            if c.stage == stage and c.status != OK and c.action and c.action not in seen:
                seen.add(c.action)
                out.append(f"  {stage or '--'}: {c.action}")
    if not seen:
        out.append("  none")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None, run: Run | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--stage", choices=STAGES, help="exit 1 unless this stage is GO")
    parser.add_argument(
        "--confirm",
        action="append",
        default=[],
        metavar="CHECK_ID",
        help="operator confirmation of a manual (CONFIRM) item, for this run only",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workflows", type=Path, default=inventory.WORKFLOWS_DIR)
    args = parser.parse_args(argv)
    gh = Gh(args.repo, run)
    try:
        if gh.info() is None:
            print(
                "hosting_preflight: gh cannot read the repository "
                "(not installed, not authenticated, or no access)",
                file=sys.stderr,
            )
            return 2
        checks = collect(gh, args.workflows, set(args.confirm))
    except GhUnavailable as error:
        print(f"hosting_preflight: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "repo": args.repo,
                    "checks": [asdict(c) for c in checks],
                    "stages": verdicts(checks),
                },
                indent=2,
            )
        )
    else:
        sys.stdout.write(render(args.repo, checks))
    return 1 if args.stage and not verdicts(checks)[args.stage]["go"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
