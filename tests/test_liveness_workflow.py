"""The Liveness dead-man workflow: stale in-flight work is an observation, not a red run.

``.github/workflows/liveness.yml`` detects a dead supervisor from outside the session. Its open-PR
step turned every open PR older than 30 minutes into an ``::error::`` and exit 1, so the run was red
on every cycle for work that was simply in flight (2026-09-11 to 2026-10-04). The same step printed
an empty branch name for every PR: bash ``read`` with ``IFS=$'\\t'`` treats tab as whitespace, so an
empty labels field collapsed and the branch landed in the empty slot. And a failed ``gh`` listing
went unnoticed, because the pipeline's status came from the loop, not from ``gh``.

Hosted YAML cannot run offline, so these tests parse the workflow and execute each observation step
under bash, with the GitHub expressions substituted, a fake ``gh`` returning fixture JSON, and real
git refs in a throwaway repository. The contract they pin: observations write ``::notice::`` and a
step summary and exit 0; a red run means the observer is blind (listing or git read fails) or main
has gone quiet during an active sprint. The cron and ``workflow_run`` triggers stay, because they
are what protects against the schedule going silent.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from support import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "liveness.yml"
OPEN_PR_STEP = "Observe open PRs older than 30 minutes"
STRANDED_STEP = "Observe remote branches ahead of main"
INACTIVITY_STEP = "Main inactivity while a sprint is active"


def _load() -> dict[str, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    # PyYAML reads the bare key ``on`` as the boolean True.
    return workflow.get("on", workflow.get(True))


def _run_script(name_fragment: str) -> str:
    steps = _load()["jobs"]["liveness"]["steps"]
    matches = [step for step in steps if name_fragment in str(step.get("name"))]
    assert len(matches) == 1, f"expected one step named {name_fragment!r}"
    return str(matches[0]["run"])


def _bash() -> str:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available to execute the liveness steps")
    return bash


def _render(script: str, fake_prs: Path | None) -> str:
    """Prepend a fake ``gh`` and route ``python3`` to the interpreter running these tests.

    The workflow's own ``python3`` heredoc runs unchanged; only the two external commands are
    stood in for. ``FAKE_GH_MODE=fail`` simulates an unreadable listing (an auth or API failure).
    """
    python = Path(sys.executable).as_posix()
    prs_path = fake_prs.as_posix() if fake_prs else "/dev/null"
    # A ``--jq ... @tsv`` request (the pre-2026-10-04 step) gets the TSV its filter would print, so
    # the same negative control reproduces that step's real output.
    prelude = f"""\
gh() {{
  if [ "${{FAKE_GH_MODE:-ok}}" = fail ]; then echo "gh: HTTP 401" >&2; return 1; fi
  case "$*" in
    *--jq*@tsv*)
      python3 - "$FAKE_PRS" <<'PY'
import json, sys
for pr in json.load(open(sys.argv[1])):
    labels = ",".join(label["name"] for label in pr["labels"])
    print("\\t".join([str(pr["number"]), pr["createdAt"], labels, pr["headRefName"]]))
PY
      ;;
    *) cat "$FAKE_PRS" ;;
  esac
}}
python3() {{ "{python}" "$@"; }}
FAKE_PRS='{prs_path}'
export FAKE_PRS
"""
    return prelude + script


def _run(
    script: str,
    cwd: Path,
    tmp_path: Path,
    *,
    fake_prs: Path | None = None,
    gh_mode: str = "ok",
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "GH_TOKEN"}
    env["GITHUB_STEP_SUMMARY"] = (tmp_path / "summary.md").as_posix()
    env["FAKE_GH_MODE"] = gh_mode
    return subprocess.run(
        [_bash(), "-c", _render(script, fake_prs)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _pr(number: int, age_min: int, now: datetime, labels: tuple[str, ...], branch: str) -> dict:
    created = (now - timedelta(minutes=age_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "number": number,
        "createdAt": created,
        "labels": [{"name": label} for label in labels],
        "headRefName": branch,
    }


def _write_prs(tmp_path: Path, prs: list[dict]) -> Path:
    path = tmp_path / "prs.json"
    path.write_text(json.dumps(prs), encoding="utf-8")
    return path


def _git(repo: Path, *args: str, when: datetime | None = None) -> str:
    env = dict(os.environ)
    if when is not None:
        stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _repo_with_remote_refs(tmp_path: Path, main_age_h: int, branch_age_h: int | None) -> Path:
    """A throwaway repository whose refs/remotes/origin/* mirror a fetched origin.

    ``origin/main`` is one commit ``main_age_h`` hours old. If ``branch_age_h`` is given, a
    ``stale-work`` branch sits one commit ahead of it, that many hours old.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    now = datetime.now(UTC)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "liveness-test@example.invalid")
    _git(repo, "config", "user.name", "liveness-test")
    main_commit = _git(
        repo,
        "commit-tree",
        _git(repo, "write-tree"),
        "-m",
        "main",
        when=now - timedelta(hours=main_age_h),
    )
    _git(repo, "update-ref", "refs/remotes/origin/main", main_commit)
    if branch_age_h is not None:
        branch_commit = _git(
            repo,
            "commit-tree",
            _git(repo, "write-tree"),
            "-p",
            main_commit,
            "-m",
            "stale work",
            when=now - timedelta(hours=branch_age_h),
        )
        _git(repo, "update-ref", "refs/remotes/origin/stale-work", branch_commit)
    return repo


# --- triggers and permissions -------------------------------------------------------------------


def test_schedule_and_workflow_run_triggers_are_kept() -> None:
    triggers = _triggers(_load())
    assert triggers["schedule"] == [{"cron": "13,43 * * * *"}]
    assert "workflow_dispatch" in triggers
    assert triggers["workflow_run"] == {"workflows": ["CI"], "types": ["completed"]}


def test_the_workflow_stays_read_only() -> None:
    assert _load()["permissions"] == {"contents": "read", "pull-requests": "read"}


# --- open PRs: observation is a notice, a blind observer is red ---------------------------------


def test_stale_prs_are_notices_and_the_run_stays_green(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    fake = _write_prs(
        tmp_path,
        [
            _pr(214, 34, now, (), "fix/review-noop-and-example-check"),
            _pr(215, 5, now, (), "fresh-lane"),
            _pr(301, 120, now, ("hold",), "parked-by-owner"),
            _pr(302, 61, now, ("bug",), "labelled-stale"),
        ],
    )
    result = _run(_run_script(OPEN_PR_STEP), tmp_path, tmp_path, fake_prs=fake)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "::error::" not in result.stdout
    # Empty labels: the branch name must survive (the 2026-10-04 bug printed "()" here).
    assert (
        "::notice title=Stale open PR::PR #214 (fix/review-noop-and-example-check) is 34 min old"
        in result.stdout
    )
    assert "PR #302 (labelled-stale)" in result.stdout
    assert "PR #301" not in result.stdout  # held: no notice
    assert "PR #215" not in result.stdout  # younger than 30 minutes
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| #214 | `fix/review-noop-and-example-check` | 34 | stale" in summary
    assert "| #301 | `parked-by-owner` | 120 | held (label hold) |" in summary


def test_no_open_prs_is_a_green_observation(tmp_path: Path) -> None:
    result = _run(_run_script(OPEN_PR_STEP), tmp_path, tmp_path, fake_prs=_write_prs(tmp_path, []))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 open PR(s); 0 older than 30 minutes" in result.stdout


def test_an_unreadable_pr_listing_is_still_red(tmp_path: Path) -> None:
    # Negative control: a blind observer is a real liveness failure and must not be swallowed.
    result = _run(_run_script(OPEN_PR_STEP), tmp_path, tmp_path, fake_prs=None, gh_mode="fail")
    assert result.returncode != 0
    assert "HTTP 401" in result.stderr


# --- stranded remote branches: a notice, and a blind git read is red ----------------------------


def test_stranded_remote_branch_is_a_notice(tmp_path: Path) -> None:
    repo = _repo_with_remote_refs(tmp_path, main_age_h=1, branch_age_h=13)
    result = _run(_run_script(STRANDED_STEP), repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        "::notice title=Stranded remote branch::branch origin/stale-work is 1 commit(s)"
        in result.stdout
    )
    assert "1 remote branch(es) ahead of main and untouched for 12+ hours" in result.stdout


def test_a_recent_remote_branch_is_not_reported(tmp_path: Path) -> None:
    # Negative control for the threshold: 2 hours old is in flight, not stranded.
    repo = _repo_with_remote_refs(tmp_path, main_age_h=1, branch_age_h=2)
    result = _run(_run_script(STRANDED_STEP), repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "::notice" not in result.stdout
    assert "0 remote branch(es)" in result.stdout


# --- main inactivity: the one health signal that stays red --------------------------------------


def test_silent_main_during_an_active_sprint_stays_red(tmp_path: Path) -> None:
    repo = _repo_with_remote_refs(tmp_path, main_age_h=5, branch_age_h=None)
    (repo / "plans" / "sprint").mkdir(parents=True)
    (repo / "plans" / "sprint" / "ACTIVE").write_text("", encoding="utf-8")
    result = _run(_run_script(INACTIVITY_STEP), repo, tmp_path)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "::error::main has been inactive" in result.stdout


def test_silent_main_outside_a_sprint_is_skipped(tmp_path: Path) -> None:
    repo = _repo_with_remote_refs(tmp_path, main_age_h=5, branch_age_h=None)
    result = _run(_run_script(INACTIVITY_STEP), repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "no active sprint; inactivity check skipped" in result.stdout
