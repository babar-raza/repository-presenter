"""tools/workflow_rehearsal/hosting_preflight.py: go/no-go for stages H0..H4 (TC-REF-12-01).

A fake ``gh`` stands in for GitHub; nothing here touches a network, the real ``gh``, or a provider.
What is pinned: the secrets, variables, write jobs and CI contexts are generated from the workflow
YAML (the real tree and a synthetic one that does declare environments); each stage's verdict moves
for exactly the defect that should move it; an unreadable fact is NO-GO, never GO; no value (secret
or variable) ever reaches the output; and every ``gh`` call the tool makes is read-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from support import REPO_ROOT

TOOL_DIR = REPO_ROOT / "tools" / "workflow_rehearsal"
sys.path.insert(0, str(TOOL_DIR))

import hosting_preflight as hp  # noqa: E402
import inventory  # noqa: E402

REPO = "owner/control"
RUNBOOK = (REPO_ROOT / "docs" / "OPERATIONS_RUNBOOK.md").read_text(encoding="utf-8")
SENTINEL_SECRET = "sentinel-secret-value-4567"
SENTINEL_VARIABLE = "sentinel-variable-value-8910"

APP_STEP = (
    "      - uses: actions/create-github-app-token@v2\n"
    "        with:\n"
    "          permission-contents: write\n"
    "          permission-pull-requests: write\n"
)
CI = (
    "name: CI\non: [pull_request]\njobs:\n  checks:\n"
    "    name: Python ${{ matrix.python-version }}\n    runs-on: ubuntu-latest\n"
    "    strategy:\n      matrix:\n        python-version: ['3.11', '3.12']\n"
    "    steps:\n      - run: echo ok\n"
)


def write_job_workflow(name: str, job: str, environment: str | None, gate: str) -> str:
    env = f"    environment: {environment}\n" if environment else ""
    return (
        f"name: {name}\non: [workflow_dispatch]\njobs:\n  {job}:\n    runs-on: ubuntu-latest\n"
        f"    if: ${{{{ vars.{gate} == '1' }}}}\n{env}    steps:\n{APP_STEP}"
        "      - run: echo ${{ secrets.GH_APP_ID }} ${{ secrets.GH_APP_PRIVATE_KEY }}\n"
    )


@pytest.fixture
def guarded_tree(tmp_path: Path) -> Path:
    """A workflow tree whose three write jobs each declare an environment."""
    directory = tmp_path / "workflows"
    directory.mkdir()
    files = {
        "ci.yml": CI,
        "candidates-publish.yml": write_job_workflow(
            "Candidates Publish", "write", "candidates", "REPOSITORY_PRESENTER_SEALING_PAUSED"
        ),
        "issues-scheduled.yml": write_job_workflow(
            "Issues", "file-and-close", "issues", "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED"
        ),
        "propose.yml": write_job_workflow(
            "Propose", "write", "propose", "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"
        ),
        "monitor.yml": "name: Monitor\non: [workflow_dispatch]\njobs:\n  j:\n    runs-on: x\n"
        "    steps:\n      - run: echo ${{ secrets.GPT_OSS_API_KEY }}"
        " ${{ secrets.GPT_OSS_ENDPOINT }} ${{ secrets.GH_APP_ID }}"
        " ${{ secrets.GH_APP_PRIVATE_KEY }}\n",
        "verify-app-installation.yml": "name: V\non: [workflow_dispatch]\njobs:\n  j:\n"
        "    runs-on: x\n    steps:\n      - run: echo hi\n",
        "audit-app-installations.yml": "name: A\non: [workflow_dispatch]\njobs:\n  j:\n"
        "    runs-on: x\n    steps:\n      - run: echo hi\n",
    }
    for file, text in files.items():
        (directory / file).write_text(text, encoding="utf-8", newline="\n")
    return directory


class FakeGh:
    """Answers the read-only calls of the preflight from a mutable description of the repository."""

    def __init__(self, directory: Path | None = None) -> None:
        rows = inventory.inventory(directory or inventory.WORKFLOWS_DIR)
        self.files = [r["file"] for r in rows]
        self.secrets = set(hp.required_secrets(rows))
        self.variables: dict[str, str] = {}
        self.disabled: set[str] = set()
        self.contexts = hp.required_check_contexts(directory or inventory.WORKFLOWS_DIR)
        self.force_push = False
        self.protected = True
        self.successful_runs: set[str] = {
            "verify-app-installation.yml",
            "audit-app-installations.yml",
        }
        self.environments: dict[str, bool] = {"candidates": True, "issues": True, "propose": True}
        self.records: dict[str, list[str] | None] = {
            "ops/issue_approvals": ["README.md", "a.json"],
            "ops/proposal-authorizations": ["a.json"],
        }
        self.unreadable: set[str] = set()
        self.seen: list[list[str]] = []

    def __call__(self, args: list[str]) -> tuple[int, str, str]:
        self.seen.append(args)
        kind = args[0]
        if kind in self.unreadable:
            return 1, "", "HTTP 403"
        if args[:2] == ["secret", "list"]:
            return 0, json.dumps([{"name": n, "value": SENTINEL_SECRET} for n in self.secrets]), ""
        if args[:2] == ["variable", "list"]:
            items = [{"name": n, "value": v} for n, v in self.variables.items()]
            return 0, json.dumps(items), ""
        if args[:2] == ["workflow", "list"]:
            listing = [
                {
                    "name": f,
                    "path": f".github/workflows/{f}",
                    "state": "disabled_manually" if f in self.disabled else "active",
                }
                for f in self.files
            ]
            return 0, json.dumps(listing), ""
        if args[:2] == ["run", "list"]:
            workflow = args[args.index("--workflow") + 1]
            runs = [{"databaseId": 42, "createdAt": "2026-10-11T00:00:00Z"}]
            return 0, json.dumps(runs if workflow in self.successful_runs else []), ""
        return self.api(args[1])

    def api(self, path: str) -> tuple[int, str, str]:
        assert path.startswith(f"repos/{REPO}"), path
        rest = path[len(f"repos/{REPO}") :]
        if rest == "":
            return 0, json.dumps({"default_branch": "main"}), ""
        if rest == "/actions/organization-secrets":
            return 0, json.dumps({"secrets": []}), ""
        if rest == "/branches/main/protection":
            if not self.protected:
                return 1, "", "HTTP 404"
            body = {
                "required_status_checks": {"contexts": self.contexts},
                "allow_force_pushes": {"enabled": self.force_push},
            }
            return 0, json.dumps(body), ""
        if rest.startswith("/environments/"):
            name = rest.rsplit("/", 1)[1]
            if name not in self.environments:
                return 1, "", "HTTP 404"
            rules = [{"type": "required_reviewers"}] if self.environments[name] else []
            return 0, json.dumps({"name": name, "protection_rules": rules}), ""
        if rest.startswith("/contents/"):
            directory = rest[len("/contents/") :].split("?")[0]
            names = self.records.get(directory)
            if names is None:
                return 1, "", "HTTP 404"
            return 0, json.dumps([{"name": n} for n in names]), ""
        raise AssertionError(f"unexpected read: {path}")


def run_preflight(
    fake: FakeGh, directory: Path | None = None, confirm: bool = True
) -> tuple[list[hp.Check], dict[str, dict[str, Any]]]:
    directory = directory or inventory.WORKFLOWS_DIR
    unconfirmed = hp.collect(hp.Gh(REPO, fake), directory)
    ids = {c.id for c in unconfirmed if c.status == hp.CONFIRM} if confirm else set()
    checks = hp.collect(hp.Gh(REPO, fake), directory, ids)
    return checks, hp.verdicts(checks)


def by_id(checks: list[hp.Check]) -> dict[str, hp.Check]:
    return {c.id: c for c in checks}


# --- generated from the YAML ------------------------------------------------------------------


def test_required_secrets_are_the_workflows_and_the_runbook_names_them() -> None:
    needed = hp.required_secrets(inventory.inventory())
    assert "GITHUB_TOKEN" not in needed
    assert {"GH_APP_ID", "GH_APP_PRIVATE_KEY", "GPT_OSS_API_KEY", "GPT_OSS_ENDPOINT"} <= set(needed)
    assert needed["GITLAB_TOKEN"] == ["mirror-gitlab.yml"]
    assert all(f"`{name}`" in RUNBOOK for name in needed)


def test_ci_contexts_expand_the_matrix_of_the_real_ci_workflow() -> None:
    assert hp.required_check_contexts(inventory.WORKFLOWS_DIR) == [
        "Python 3.11",
        "Python 3.12",
        "Python 3.13",
    ]


def test_the_write_jobs_are_found_with_the_stage_that_first_needs_them() -> None:
    found = {(j["file"], j["job"]): j for j in hp.write_jobs(inventory.inventory())}
    assert found[("candidates-publish.yml", "write")]["stage"] == "H1"
    assert found[("issues-scheduled.yml", "file-and-close")]["stage"] == "H2"
    assert found[("propose.yml", "write")]["stage"] == "H3"
    assert found[("propose-sandbox.yml", "write")]["stage"] == "H3"
    # Today no production write job declares an environment: the preflight must say so, not assume
    # it. The sandbox canary's write job is the one exception, and it names its environment.
    assert all(
        j["environment"] is None for key, j in found.items() if key[0] != "propose-sandbox.yml"
    )
    assert found[("propose-sandbox.yml", "write")]["environment"] == "sandbox-canary"


# --- the real workflow tree --------------------------------------------------------------------


def test_the_real_tree_is_h0_go_and_h1_no_go_without_environments() -> None:
    checks, verdict = run_preflight(FakeGh())
    assert verdict["H0"]["go"], verdict["H0"]["blocking"]
    assert not verdict["H1"]["go"]
    assert "environment:candidates-publish.yml:write" in verdict["H1"]["blocking"]
    assert by_id(checks)["environment:candidates-publish.yml:write"].status == hp.MISSING


def test_an_unconfirmed_manual_item_blocks_its_stage(guarded_tree: Path) -> None:
    _, confirmed = run_preflight(FakeGh(guarded_tree), guarded_tree)
    _, unconfirmed = run_preflight(FakeGh(guarded_tree), guarded_tree, confirm=False)
    assert confirmed["H1"]["go"] and not unconfirmed["H1"]["go"]
    assert unconfirmed["H1"]["blocking"] == ["app-scope:candidates-publish.yml:write"]
    assert unconfirmed["H0"]["go"]  # no manual item belongs to the dry run


# --- a tree whose write jobs are guarded -------------------------------------------------------


def posture_h3(fake: FakeGh) -> FakeGh:
    fake.variables = {name: "1" for name in hp.GATES}
    return fake


def test_a_fully_provisioned_repository_is_go_for_every_stage(guarded_tree: Path) -> None:
    fake = posture_h3(FakeGh(guarded_tree))
    _, verdict = run_preflight(fake, guarded_tree)
    assert {s: v["go"] for s, v in verdict.items()} == {
        "H0": False,  # the write gates are already open: H0 forbids that
        "H1": False,
        "H2": False,
        "H3": True,
        "H4": True,
    }
    assert verdict["H0"]["blocking"] == ["posture:H0"]
    fake.variables = {}
    _, closed = run_preflight(fake, guarded_tree)
    assert closed["H0"]["go"] and closed["H1"]["go"] and closed["H2"]["go"]


def test_each_stage_refuses_a_gate_that_is_open_too_early(guarded_tree: Path) -> None:
    fake = FakeGh(guarded_tree)
    fake.variables = {"REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED": "1"}
    _, verdict = run_preflight(fake, guarded_tree)
    assert not verdict["H1"]["go"] and "posture:H1" in verdict["H1"]["blocking"]
    assert not verdict["H2"]["go"]
    assert "posture:H3" not in verdict["H2"]["blocking"]


def test_a_paused_sealing_blocks_h1_but_not_the_dry_run(guarded_tree: Path) -> None:
    fake = FakeGh(guarded_tree)
    fake.variables = {hp.PAUSE: "1"}
    _, verdict = run_preflight(fake, guarded_tree)
    assert verdict["H0"]["go"] and not verdict["H1"]["go"]
    assert f"variable:{hp.PAUSE}" in verdict["H1"]["blocking"]


@pytest.mark.parametrize(
    ("defect", "check_id", "first_no_go"),
    [
        ("secret", "secret:GH_APP_ID", "H0"),
        ("workflow", "workflows:enabled", "H0"),
        ("context", "branch:protection", "H0"),
        ("forcepush", "branch:protection", "H0"),
        ("unprotected", "branch:protection", "H0"),
        ("app-audit", "app:audit-app-installations.yml", "H0"),
        ("environment", "environment:issues-scheduled.yml:file-and-close", "H2"),
        ("issue-records", "records:ops/issue_approvals", "H2"),
        ("pr-records", "records:ops/proposal-authorizations", "H3"),
    ],
)
def test_each_defect_moves_the_stage_it_belongs_to(
    guarded_tree: Path, defect: str, check_id: str, first_no_go: str
) -> None:
    fake = FakeGh(guarded_tree)
    if defect == "secret":
        fake.secrets.discard("GH_APP_ID")
    elif defect == "workflow":
        fake.disabled.add("monitor.yml")
    elif defect == "context":
        fake.contexts = fake.contexts[:1]
    elif defect == "forcepush":
        fake.force_push = True
    elif defect == "unprotected":
        fake.protected = False
    elif defect == "app-audit":
        fake.successful_runs.discard("audit-app-installations.yml")
    elif defect == "environment":
        fake.environments["issues"] = False
    elif defect == "issue-records":
        fake.records["ops/issue_approvals"] = ["README.md"]
    else:
        fake.records["ops/proposal-authorizations"] = None
    checks, verdict = run_preflight(fake, guarded_tree)
    assert by_id(checks)[check_id].status != hp.OK
    assert not verdict[first_no_go]["go"] and check_id in verdict[first_no_go]["blocking"]
    earlier = hp.STAGES[: hp.STAGES.index(first_no_go)]
    # Closed gates (the default fake) so the earlier stages stay GO.
    assert all(verdict[s]["go"] for s in earlier), (defect, [verdict[s] for s in earlier])


def test_a_missing_secret_names_the_secret_in_the_owner_action(guarded_tree: Path) -> None:
    fake = FakeGh(guarded_tree)
    fake.secrets.discard("GPT_OSS_API_KEY")
    checks, _ = run_preflight(fake, guarded_tree)
    check = by_id(checks)["secret:GPT_OSS_API_KEY"]
    assert check.status == hp.MISSING and "GPT_OSS_API_KEY" in check.action


def test_an_unreadable_fact_is_no_go_never_go(guarded_tree: Path) -> None:
    for kind in ("secret", "variable", "workflow", "run"):
        fake = FakeGh(guarded_tree)
        fake.unreadable.add(kind)
        checks, verdict = run_preflight(fake, guarded_tree)
        assert any(c.status == hp.UNKNOWN for c in checks), kind
        assert not verdict["H0"]["go"], kind


def test_a_variable_the_preflight_does_not_model_is_flagged(tmp_path: Path) -> None:
    directory = tmp_path / "workflows"
    directory.mkdir()
    (directory / "x.yml").write_text(
        "name: X\non: [workflow_dispatch]\njobs:\n  j:\n    runs-on: x\n"
        "    if: ${{ vars.SOME_NEW_GATE == '1' }}\n    steps:\n      - run: echo hi\n",
        encoding="utf-8",
    )
    checks = hp.collect(hp.Gh(REPO, FakeGh(directory)), directory)
    flagged = by_id(checks)["variables:modelled"]
    assert flagged.status == hp.MISSING and "SOME_NEW_GATE" in flagged.detail


# --- nothing leaks, nothing writes -------------------------------------------------------------


def test_no_secret_or_variable_value_reaches_any_output(
    guarded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeGh(guarded_tree)
    fake.variables = {
        hp.PAUSE: SENTINEL_VARIABLE,
        "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED": "1",
    }
    checks, _ = run_preflight(fake, guarded_tree)
    text = hp.render(REPO, checks)
    assert SENTINEL_SECRET not in text and SENTINEL_VARIABLE not in text
    argv = ["--repo", REPO, "--workflows", str(guarded_tree), "--json"]
    assert hp.main(argv, run=fake) == 0
    printed = capsys.readouterr().out
    assert SENTINEL_SECRET not in printed and SENTINEL_VARIABLE not in printed
    assert json.loads(printed)["stages"]["H0"]["title"].startswith("hosted dry run")


@pytest.mark.parametrize(
    "args",
    [
        ["secret", "set", "X"],
        ["variable", "set", "X", "--body", "1"],
        ["variable", "delete", "X"],
        ["workflow", "run", "x.yml"],
        ["workflow", "enable", "x.yml"],
        ["run", "rerun", "1"],
        ["api", "-X", "POST", "repos/o/r/issues"],
        ["api", "--method=DELETE", "repos/o/r"],
        ["api", "-f", "title=x", "repos/o/r/issues"],
        ["api", "-F", "a=b", "repos/o/r"],
        ["api", "--input", "body.json", "repos/o/r"],
        ["pr", "create"],
        [],
    ],
)
def test_the_read_only_guard_refuses_a_write_shaped_call(args: list[str]) -> None:
    with pytest.raises(ValueError, match=r"refusing|not on the read-only list"):
        hp.assert_read_only(args)
    with pytest.raises((ValueError, IndexError)):
        hp.Gh(REPO, FakeGh()).json(args)


def test_every_call_a_full_run_makes_is_read_only(guarded_tree: Path) -> None:
    fake = FakeGh(guarded_tree)
    run_preflight(fake, guarded_tree)
    assert fake.seen
    for args in fake.seen:
        hp.assert_read_only(args)


# --- the command line --------------------------------------------------------------------------


def test_the_stage_flag_sets_the_exit_code(
    guarded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeGh(guarded_tree)
    base = ["--repo", REPO, "--workflows", str(guarded_tree)]
    assert hp.main([*base, "--stage", "H1"], run=fake) == 1  # manual items unconfirmed
    confirms = [c.id for c in hp.collect(hp.Gh(REPO, fake), guarded_tree) if c.status == hp.CONFIRM]
    flags = [arg for cid in confirms for arg in ("--confirm", cid)]
    assert hp.main([*base, "--stage", "H1", *flags], run=fake) == 0
    assert "GO" in capsys.readouterr().out


def test_gh_missing_or_unreadable_exits_2_without_a_table(
    guarded_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def missing(args: list[str]) -> tuple[int, str, str]:
        raise hp.GhUnavailable("gh could not run: FileNotFoundError")

    def denied(args: list[str]) -> tuple[int, str, str]:
        return 1, "", "HTTP 401"

    base = ["--repo", REPO, "--workflows", str(guarded_tree), "--stage", "H0"]
    assert hp.main(base, run=missing) == 2
    assert hp.main(base, run=denied) == 2
    assert "GO / NO-GO" not in capsys.readouterr().out


# --- the runbook states what the tool computes ---------------------------------------------------


def test_the_runbook_gate_posture_table_equals_the_preflights_stage_model() -> None:
    rows = {
        cells[0]: cells[2:]
        for line in RUNBOOK.splitlines()
        if line.startswith("| H")
        and len(cells := [c.strip() for c in line.strip("|").split("|")]) == 5
    }
    assert sorted(rows) == list(hp.STAGES)
    order = list(hp.GATES)  # candidates, issues, proposal: the table's column order
    assert [g.split("_")[2] for g in order] == ["CANDIDATES", "ISSUES", "PROPOSAL"]
    for stage, cells in rows.items():
        expected = ["open" if stage in hp.GATES[gate] else "closed" for gate in order]
        assert [c.strip("*") for c in cells] == expected, stage


def test_the_runbook_wires_both_tools_and_every_stage() -> None:
    for needle in (
        "tools/workflow_rehearsal/hosting_preflight.py",
        "tools/workflow_rehearsal/no_bump_check.py origin/main --no-src",
        "assert_read_only",
        "**H0, hosted dry run",
        "**H4, per-repository expansion",
        "Kill switch and rollback rehearsal",
    ):
        assert needle in RUNBOOK, needle
