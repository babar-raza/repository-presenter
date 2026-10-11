"""The local workflow rehearsal tooling (tools/workflow_rehearsal/, TC-REF-10).

What is pinned: the workflow inventory is generated from the YAML and equals the runbook's block;
the shape checks pass on every real workflow and fail on each defect class they claim to catch
(negative controls); the synthetic upstreams are deterministic and each scenario has the shape its
name promises; the fake GitHub routes answer what the workflows read, hand out only a fake token,
record every mutation, and inject failures; the harness plans cover exactly the repository's
workflows and its leak scan fires on a secret. No test touches a network, Docker, act or the LLM
gateway; actionlint runs only when a binary is installed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from support import REPO_ROOT

TOOL_DIR = REPO_ROOT / "tools" / "workflow_rehearsal"
sys.path.insert(0, str(TOOL_DIR))

import fake_github  # noqa: E402
import harness  # noqa: E402
import inventory  # noqa: E402
import scenarios  # noqa: E402
import shape_checks  # noqa: E402

WORKFLOWS = sorted(p.name for p in (REPO_ROOT / ".github" / "workflows").glob("*.yml"))
RUNBOOK = REPO_ROOT / "docs" / "OPERATIONS_RUNBOOK.md"


# --- inventory -------------------------------------------------------------------------------


def test_every_workflow_parses_and_has_a_trigger_and_a_job() -> None:
    rows = inventory.inventory()
    assert [r["file"] for r in rows] == WORKFLOWS
    for row in rows:
        assert row["triggers"], row["file"]
        assert row["jobs"], row["file"]


def test_the_on_key_is_read_as_a_trigger_not_as_boolean_true() -> None:
    workflow = inventory.load_workflow(REPO_ROOT / ".github" / "workflows" / "monitor.yml")
    assert "on" in workflow and True not in workflow


def test_secrets_and_variables_are_read_from_expressions_only() -> None:
    by_file = {r["file"]: r for r in inventory.inventory()}
    # `secrets.py` appears in prose in present.yml; only ${{ secrets.NAME }} counts.
    assert "py" not in by_file["present.yml"]["secrets"]
    assert by_file["sealing-scheduled.yml"]["variables"] == [
        "REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED",
        "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED",
        "REPOSITORY_PRESENTER_SEALING_PAUSED",
    ]
    assert by_file["sealing-scheduled.yml"]["inherits_secrets"] is True
    assert {"GH_APP_ID", "GH_APP_PRIVATE_KEY"} <= set(by_file["monitor.yml"]["secrets"])


def test_the_runbook_inventory_block_equals_what_the_yaml_says_now() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert (
        inventory.generated_block(text).strip() == inventory.render(inventory.inventory()).strip()
    ), "docs/OPERATIONS_RUNBOOK.md is stale: python tools/workflow_rehearsal/inventory.py --write"


def test_splice_refuses_a_runbook_without_markers() -> None:
    with pytest.raises(ValueError):
        inventory.splice("no markers here", "block")


def test_every_owner_variable_a_workflow_reads_is_named_in_the_runbook() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    names = {v for r in inventory.inventory() for v in r["variables"] + r["env_names"]}
    assert names, "the workflows no longer read any owner variable?"
    for name in sorted(names):
        assert text.count(name) >= 2, f"{name} is only in the generated table, not in the prose"


# --- shape checks ----------------------------------------------------------------------------


def test_every_real_workflow_passes_the_shape_checks() -> None:
    assert {name: found for name, found in shape_checks.check_all().items() if found} == {}


def _good() -> dict[str, Any]:
    return {
        "name": "t",
        "on": {"workflow_dispatch": {}},
        "permissions": {"contents": "read"},
        "jobs": {
            "a": {
                "runs-on": "ubuntu-latest",
                "outputs": {"x": "${{ steps.s.outputs.x }}"},
                "steps": [{"id": "s", "run": "echo hi"}, {"uses": "actions/checkout@v5"}],
            },
            "b": {
                "needs": "a",
                "runs-on": "ubuntu-latest",
                "steps": [{"run": "echo ${{ needs.a.outputs.x }}"}],
            },
        },
    }


def _findings(workflow: dict[str, Any]) -> list[str]:
    return shape_checks.check_workflow(workflow, root=REPO_ROOT)


def test_a_well_formed_workflow_is_clean() -> None:
    assert _findings(_good()) == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda w: w["jobs"]["b"].update(needs="ghost"), "unknown job"),
        (lambda w: w["jobs"]["a"].update(needs="b"), "needs cycle"),
        (
            lambda w: w["jobs"]["a"]["steps"][0].update(id="s", run="x", uses="actions/x@v1"),
            "exactly one of run and uses",
        ),
        (lambda w: w["jobs"]["a"]["steps"].append({"uses": "actions/cache@main"}), "not pinned"),
        (
            lambda w: w["jobs"]["a"].update(outputs={"x": "${{ steps.nope.outputs.x }}"}),
            "steps.nope",
        ),
        (lambda w: w["jobs"]["b"]["steps"].append({"run": "${{ needs.zzz.result }}"}), "needs.zzz"),
        (lambda w: w["jobs"]["a"]["steps"].append({"run": "${{ matrix.k }}"}), "no matrix"),
        (lambda w: w.pop("permissions"), "permissions"),
        (lambda w: w["on"].update(pull_request_target={}), "pull_request_target"),
        (lambda w: w["on"].update(schedule=[{"cron": "17 */6 * *"}]), "malformed cron"),
        (
            lambda w: w["jobs"]["a"]["steps"].append(
                {"run": "echo ${{ github.event.issue.title }}"}
            ),
            "untrusted",
        ),
        (lambda w: w["jobs"]["a"].update(uses="./.github/workflows/none.yml"), "does not exist"),
        (lambda w: w["jobs"]["a"].pop("steps"), "no steps"),
    ],
)
def test_each_defect_class_is_reported(mutate: Any, expected: str) -> None:
    workflow = _good()
    mutate(workflow)
    assert any(expected in finding for finding in _findings(workflow)), _findings(workflow)


def test_actionlint_is_clean_on_every_workflow_when_installed() -> None:
    outcome = shape_checks.run_actionlint()
    if outcome is None:
        pytest.skip("actionlint is not installed (set ACTIONLINT or put it on PATH)")
    assert outcome == (0, "")


# --- synthetic upstreams ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[dict[str, Any]]]:
    root = tmp_path_factory.mktemp("world")
    return root, scenarios.build_world(root)


def _has(bare: Path, sha: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", sha], cwd=bare, capture_output=True, check=False
        ).returncode
        == 0
    )


def test_the_scenario_table_names_every_required_scenario(
    world: tuple[Path, list[dict[str, Any]]],
) -> None:
    names = {row["name"] for row in world[1]}
    assert {
        "relevant-change",
        "irrelevant-change",
        "maintainer-readme-edit",
        "force-pushed-history",
        "deleted-repository",
        "archived-repository",
    } <= names
    on_disk = json.loads((world[0] / "scenarios.json").read_text(encoding="utf-8"))
    assert on_disk == world[1]


def test_history_is_deterministic_across_builds(
    world: tuple[Path, list[dict[str, Any]]], tmp_path: Path
) -> None:
    assert scenarios.build_world(tmp_path) == world[1]


def test_changing_scenarios_move_the_head_and_the_unchanged_one_does_not(
    world: tuple[Path, list[dict[str, Any]]],
) -> None:
    rows = {row["name"]: row for row in world[1]}
    assert rows["unchanged"]["sealed_revision"] == rows["unchanged"]["head_revision"]
    for name in ("relevant-change", "irrelevant-change", "maintainer-readme-edit"):
        assert rows[name]["sealed_revision"] != rows[name]["head_revision"], name


def test_a_force_pushed_history_no_longer_contains_the_sealed_revision(
    world: tuple[Path, list[dict[str, Any]]],
) -> None:
    row = next(r for r in world[1] if r["name"] == "force-pushed-history")
    bare = world[0] / "upstreams" / scenarios.OWNER / "force-pushed-history.git"
    assert _has(bare, row["head_revision"])
    reachable = subprocess.run(
        ["git", "rev-list", "main"], cwd=bare, capture_output=True, text=True, check=True
    )
    assert row["sealed_revision"] not in reachable.stdout.split()


def test_world_metadata_marks_the_deleted_and_archived_repositories(
    world: tuple[Path, list[dict[str, Any]]],
) -> None:
    meta = json.loads((world[0] / "world.json").read_text(encoding="utf-8"))
    assert meta["deleted"] == [f"{scenarios.OWNER}/deleted-repository"]
    assert meta["archived"] == [f"{scenarios.OWNER}/archived-repository"]


# --- fake GitHub -----------------------------------------------------------------------------


def _route(world_root: Path, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    split = urlsplit(path)
    return fake_github.route(
        fake_github.World(world_root),
        method,
        split.path,
        parse_qs(split.query),
        json.dumps(body or {}).encode(),
    )


def test_the_default_branch_head_tree_and_contents_come_from_the_bare_repository(
    world: tuple[Path, list[dict[str, Any]]],
) -> None:
    root, rows = world
    row = next(r for r in rows if r["name"] == "relevant-change")
    repo = row["repository"]
    assert _route(root, "GET", f"/repos/{repo}")[:2] == (
        200,
        {"full_name": repo, "default_branch": "main", "archived": False},
    )
    assert _route(root, "GET", f"/repos/{repo}/commits/main")[1] == {"sha": row["head_revision"]}
    status, tree, _ = _route(
        root, "GET", f"/repos/{repo}/git/trees/{row['head_revision']}?recursive=1"
    )
    assert status == 200 and {e["path"] for e in tree["tree"]} >= {
        "README.md",
        "src/synthetic/__init__.py",
    }
    status, content, _ = _route(root, "GET", f"/repos/{repo}/contents/README.md?ref=main")
    assert status == 200 and content["encoding"] == "base64"
    assert _route(root, "GET", f"/repos/{repo}/git/trees/{'0' * 40}?recursive=1")[0] == 404


def test_a_deleted_repository_is_404_and_an_archived_one_says_so(
    world: tuple[Path, list[dict[str, Any]]],
) -> None:
    root, _ = world
    assert _route(root, "GET", f"/repos/{scenarios.OWNER}/deleted-repository")[0] == 404
    assert (
        _route(root, "GET", f"/repos/{scenarios.OWNER}/archived-repository")[1]["archived"] is True
    )


def test_a_head_override_and_an_unknown_repository_answer_deterministically(tmp_path: Path) -> None:
    (tmp_path / "world.json").write_text(json.dumps({"heads": {"o/r": "a" * 40}}), encoding="utf-8")
    assert _route(tmp_path, "GET", "/repos/o/r/commits/main")[1] == {"sha": "a" * 40}
    first = _route(tmp_path, "GET", "/repos/x/y/commits/main")[1]
    assert first == _route(tmp_path, "GET", "/repos/x/y/commits/main")[1]
    assert len(first["sha"]) == 40


def test_the_app_token_exchange_returns_only_a_fake_token(tmp_path: Path) -> None:
    status, token, _ = _route(
        tmp_path,
        "POST",
        "/app/installations/1/access_tokens",
        {"permissions": {"contents": "read"}},
    )
    assert status == 201 and token["token"] == fake_github.FAKE_TOKEN
    assert not re.match(r"gh[ps]_", token["token"])
    assert token["permissions"] == {"contents": "read"}
    assert (
        _route(tmp_path, "GET", "/repos/o/r/installation")[1]["id"] == fake_github.INSTALLATION_ID
    )
    assert _route(tmp_path, "GET", "/orgs/o/installation")[0] == 200
    assert _route(tmp_path, "DELETE", "/installation/token")[0] == 204


def test_an_injected_failure_carries_its_status_and_retry_after(tmp_path: Path) -> None:
    failures = {"o/r": {"status": 429, "retry_after": 7}}
    (tmp_path / "world.json").write_text(json.dumps({"failures": failures}), encoding="utf-8")
    status, _, headers = _route(tmp_path, "GET", "/repos/o/r")
    assert status == 429 and headers["Retry-After"] == "7"


def test_pull_requests_and_issues_are_answered_by_the_fake_and_unknown_routes_are_404(
    tmp_path: Path,
) -> None:
    status, created, _ = _route(
        tmp_path, "POST", "/repos/o/r/pulls", {"title": "t", "head": "h", "base": "b"}
    )
    assert status == 201 and created["html_url"].startswith("https://github.com/o/r/pulls/")
    assert _route(tmp_path, "POST", "/repos/o/r/issues", {"title": "t"})[0] == 201
    assert _route(tmp_path, "GET", "/repos/o/r/pulls")[1] == []
    assert _route(tmp_path, "PUT", "/repos/o/r/contents/README.md")[0] == 404


# --- harness ---------------------------------------------------------------------------------


def test_the_harness_plan_covers_exactly_the_repository_workflows() -> None:
    assert sorted(harness.WORKFLOW_PLAN) == WORKFLOWS
    for name, plan in harness.WORKFLOW_PLAN.items():
        assert plan["mode"] in ("full", "dryrun", "replay"), name
        assert plan["gap"], name


def test_the_plan_event_is_one_the_workflow_actually_declares() -> None:
    for row in inventory.inventory():
        event = harness.WORKFLOW_PLAN[row["file"]]["event"]
        assert any(t.split()[0] == event for t in row["triggers"]), (row["file"], event)


def test_the_act_command_targets_the_fake_network_and_trusts_only_the_rehearsal_ca(
    tmp_path: Path,
) -> None:
    command = harness.act_command(
        "act", "monitor.yml", "schedule", tmp_path, tmp_path, network=True, extra=[]
    )
    joined = " ".join(command)
    assert "--network rp-rehearsal" in joined
    assert "GIT_CONFIG_GLOBAL=/rehearsal/gitconfig" in joined
    assert "NODE_EXTRA_CA_CERTS=/rehearsal/tls/ca.pem" in joined
    assert "ubuntu-latest=catthehacker/ubuntu:act-24.04" in joined
    assert "--pull=false" in command and "--concurrent-jobs" in command


def test_the_gitconfig_rewrites_github_to_the_local_git_host(tmp_path: Path) -> None:
    harness.write_support_files(tmp_path)
    text = (tmp_path / "gitconfig").read_text(encoding="utf-8")
    assert "insteadOf = https://github.com/" in text and harness.GIT_HOST in text


def test_the_leak_scan_finds_a_fake_secret_and_a_credential_shaped_string(tmp_path: Path) -> None:
    clean = tmp_path / "clean.log"
    clean.write_text("nothing here\n", encoding="utf-8")
    bad = tmp_path / "bad.log"
    bad.write_text("token ghs_" + "A" * 30 + "\n", encoding="utf-8")
    pem = tmp_path / "pem.log"
    pem.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    literal = tmp_path / "literal.log"
    literal.write_text("key=FAKE_VALUE\n", encoding="utf-8")
    hits = harness.scan_for_secrets([tmp_path], ["FAKE_VALUE"])
    assert sorted(Path(h).name for h in hits) == ["bad.log", "literal.log", "pem.log"]


def test_the_act_log_summary_counts_job_outcomes() -> None:
    log = "Job succeeded\nJob failed\nJob succeeded\nSuccessfully set up CPython (3.11.9)\n"
    assert harness.summarize_act_log(log) == {
        "jobs_succeeded": 2,
        "jobs_failed": 1,
        "python_versions": ["3.11.9"],
    }
