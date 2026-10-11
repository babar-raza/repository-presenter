"""The whole autonomous cycle, rehearsed locally on synthetic upstreams (TC-REF-11).

``tools/workflow_rehearsal/cycle.py`` drives the code the scheduled workflows call - durable state
on a bare git remote, the monitor and the sealing plan over synthetic upstreams, the propose and
commit-back effects behind a stateful fake REST - and computes a verdict per scenario from what the
real code did. The first half of this file pins those verdicts; the second half rehearses what needs
the model's transport (a gateway outage, the call budget, the happy path with a no-op proof) through
``tests/test_cli.py``'s scripted gateway. No test here uses the network: an autouse guard refuses
any connection that is not to this machine, and the package registry is answered locally.

Each scenario is also recorded as evidence JSON when ``RP_REHEARSAL_EVIDENCE_DIR`` names a directory
(``evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/validation/``).
"""

# The canary fixtures are imported from tests/test_cli.py by name, so a test that takes one as a
# parameter "redefines" it for the linter; pytest resolves them by name, which is the point.
# ruff: noqa: F811

from __future__ import annotations

import json
import shutil
import socket
import sys
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, main
from repository_presenter.components.monitor.drift import assemble_drift_contract
from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE,
    presenter_branch_name,
    propose_candidate,
)
from repository_presenter.components.propose.pull_request import (
    compose_pull_request,
    load_pull_request_evidence,
)
from repository_presenter.components.readme.bundle.portfolio import proposal_acceptance_gate
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.core.authorization.proposal import authorize_proposal
from repository_presenter.core.authorization.refusals import WriteRefusedError
from repository_presenter.core.candidates import load_proposable_candidate
from repository_presenter.core.github import read_client
from repository_presenter.core.llm import jobs
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.registry.loader import load_registry
from repository_presenter.core.registry.write_gate import require_write_permitted
from repository_presenter.core.retry import run_with_retry
from repository_presenter.core.state.git_backend import GitStateBackend
from support import REPO_ROOT, commit_all, init_git_repository, mock_gateway
from test_cli import (  # noqa: F401 - pytest fixtures the canary scenarios build on
    CANARY,
    canary_source,
    gateway_ready,
    local_canary,
    project_with_registry,
)

TOOL_DIR = REPO_ROOT / "tools" / "workflow_rehearsal"
sys.path.insert(0, str(TOOL_DIR))

import cycle  # noqa: E402
import fake_github  # noqa: E402
import fake_rest  # noqa: E402
from harness import scan_for_secrets  # noqa: E402

OUTAGE_BODY = {
    "error": {
        "message": (
            "litellm.InternalServerError: InternalServerError: Hosted_vllmException - "
            "Cannot connect to host text-model.vllm-qwen.svc.cluster.local:80 ... Connect "
            "call failed ('10.96.52.170', 80). Received Model Group=qwen3-next"
        ),
        "type": "InternalServerError",
    }
}
CANARY_SLUG = CANARY.replace("/", "__")
CANARY_OWNER = CANARY.split("/")[0]


# --- no network, local registry ------------------------------------------------------------


@pytest.fixture(autouse=True)
def only_this_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse any connection that is not to this machine, so a path that would reach the network
    fails loudly instead of quietly succeeding."""
    real = socket.socket.connect

    def guarded(self: socket.socket, address: Any, *args: Any, **kwargs: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else None
        if self.family != socket.AF_UNIX and host not in ("127.0.0.1", "::1", "localhost"):
            raise OSError(f"the rehearsal tests make no network connection ({address!r})")
        return real(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded)


@pytest.fixture
def canary_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer PyPI for the canary's package locally, with its project URL pointing at the canary.

    ``observe_pypi`` binds its ``fetch`` as a keyword default at definition time, so replacing
    ``python_registry.fetch_project_json`` (what ``tests/conftest.py`` and ``test_cli`` do) leaves
    the real registry in place; the default itself is what must be replaced.
    """

    def fetch(url: str) -> httpx.Response:
        body = {
            "info": {
                "name": "aspose-3d-foss",
                "version": "26.1.0",
                "project_urls": {"Source": f"https://github.com/{CANARY}"},
            },
            "releases": {"26.1.0": []},
        }
        return httpx.Response(200, json=body)

    defaults = python_registry.observe_pypi.__kwdefaults__
    assert defaults is not None and "fetch" in defaults
    monkeypatch.setitem(defaults, "fetch", fetch)


@pytest.fixture(scope="module")
def fake_model_evidence() -> Iterator[dict[str, Any]]:
    document: dict[str, Any] = {
        "work_item": "TC-REF-11 (G7-W06)",
        "kind": "whole-cycle rehearsal with a scripted gateway (tests/test_cli.py's _ChatGateway) "
        "behind the real CLI, durable state on a local bare git remote, no network",
        "scenarios": [],
    }
    yield document
    document["verdicts"] = {s["scenario"]: s["verdict"] for s in document["scenarios"]}
    cycle.record("workflow-rehearsal-cycle-fake-model.json", document)


# --- the offline scenarios of tools/workflow_rehearsal/cycle.py -----------------------------


@pytest.fixture(scope="module")
def offline(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], dict[str, Any]]:
    """Run each ``cycle`` scenario once, in its own directory, and cache the result."""
    work = tmp_path_factory.mktemp("cycle")
    results: dict[str, dict[str, Any]] = {}

    def run(name: str) -> dict[str, Any]:
        if name not in results:
            directory = work / name
            directory.mkdir()
            results[name] = getattr(cycle, name)(directory)
        return results[name]

    run.work = work  # type: ignore[attr-defined]
    run.results = results  # type: ignore[attr-defined]
    return run


def test_every_cycle_scenario_has_a_verdict_computed_from_the_code(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    for scenario in cycle.SCENARIOS:
        result = offline(scenario.__name__)
        assert result["verdict"] in ("PROVEN", "PROVEN_WITH_GAP"), (
            result["scenario"],
            result["observations"],
        )


def test_a_stale_lease_is_fenced(offline: Callable[[str], dict[str, Any]]) -> None:
    seen = offline("stale_lease_fenced")["observations"]
    assert seen["fencing_tokens"] == {"worker_a": 1, "worker_b": 2}
    assert seen["contended_acquire_while_live"] == "refused"
    assert "stale" in seen["zombie_commit"]
    assert seen["zombie_renewal"] == "refused"
    assert seen["lease_after_zombie_attempts"] == {
        "worker_b_holds": True,
        "worker_a_holds": False,
        "holder": "worker-b",
    }
    assert seen["state_after_zombie_attempts"] == "SNAPSHOTTING"
    assert seen["durable_refs_on_the_remote"] == [
        "refs/repository-presenter-state/records/rehearsal-org__relevant-change"
    ]


def test_a_run_killed_mid_transaction_recovers_without_double_processing(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("kill_mid_transaction")["observations"]
    assert seen["victim_exit_code"] == 137
    assert seen["victim_work_done_before_death"] == "investigation call made"
    assert seen["state_the_dead_worker_left"] == "INVESTIGATING"
    assert seen["pipeline_runs_in_recovery"] == 1
    assert seen["same_transaction_resumed"] is True
    assert (seen["recovery_count"], seen["final_state"]) == (1, "READY_FOR_PROPOSAL")
    assert seen["final_fencing_token"] > seen["dead_worker_fencing_token"]
    assert seen["lease_released"] is True
    assert seen["replay_of_the_dead_trigger"] == {
        "exit_code": 0,
        "pipeline_runs": 0,
        "state_version_unchanged": True,
    }


def test_the_pause_variable_stops_the_cycle_only_when_it_is_exactly_one(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("pause_variable")["observations"]
    assert seen["plan_when_paused"]["has_work"] == "false"
    assert seen["plan_when_paused"]["has_publishable"] == "false"
    assert seen["plan_when_not_paused"]["has_work"] == "true"
    assert not any(seen["values_that_do_not_pause"].values())
    assert seen["seal_job_runs_only_on_plan_has_work"] is True


def test_the_run_cap_defers_the_rest_and_a_failed_repository_waits_out_its_cooldown(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    result = offline("run_cap_and_cooldown")
    seen = result["observations"]
    assert seen["cycle_1"]["selected"] == [
        "rehearsal-org/repo-a",
        "rehearsal-org/repo-c",
        "rehearsal-org/repo-d",
    ]
    assert seen["cycle_1"]["deferred"] == ["rehearsal-org/repo-e"]
    assert seen["cycle_1"]["skipped_by_failure_memory"] == ["rehearsal-org/repo-b"]
    assert seen["cycle_2"]["selected"] == ["rehearsal-org/repo-b", "rehearsal-org/repo-e"]
    assert "per-day provider-call budget" in result["gap"]


def test_monitor_to_plan_selects_a_consumed_path_change_and_nothing_else(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("monitor_to_plan")["observations"]
    assert seen["sealing_plan_selected"] == [
        "force-pushed-history",
        "maintainer-readme-edit",
        "relevant-change",
    ]
    states = {n: (s["status"], s["change"]) for n, s in seen["scenarios"].items()}
    assert states["irrelevant-change"] == ("CURRENT", "IRRELEVANT_CHANGE")
    assert states["unchanged"] == ("CURRENT", "NO_CHANGE")
    assert states["deleted-repository"][0] == "UNREACHABLE"
    assert "README.md" in seen["scenarios"]["maintainer-readme-edit"]["detail"]
    assert (
        seen["legacy_bundle_without_recorded_blobs"][
            "force-pushed-history (sealed commit collected)"
        ]["status"]
        == "UNKNOWN"
    )
    assert seen["provider_calls"] == 0


def test_propose_opens_one_pull_request_and_a_second_run_creates_nothing(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("propose_idempotence")["observations"]
    assert seen["first_run"]["pr_created"] and seen["first_run"]["commit_written"]
    assert seen["applied_writes_added_by_second_run"] == 0
    assert seen["second_run_unchanged"]["reason"] == "no change needed"
    assert seen["new_candidate_updates_in_place"]["pr_updated"] is True
    assert seen["open_pull_requests_after_update"] == 1
    assert seen["base_branch_readme_untouched"] is True
    assert seen["writes_added_after_merge"] == 0


def test_a_maintainer_edit_is_never_overwritten(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("propose_maintainer_edit")["observations"]
    assert seen["propose_after_the_edit"]["effected"] is False
    assert seen["writes_made_by_propose"] == 0
    assert seen["base_branch_readme_is_the_maintainers"] is True
    assert (seen["presenter_branch_exists"], seen["pull_requests"]) == (False, 0)


def test_a_lost_response_is_reconciled_by_reading_never_by_writing_twice(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    cases = offline("lost_responses")["observations"]
    assert cases["put_landed_answer_lost"]["put_requests"] == 1
    assert cases["put_never_arrived"]["put_applied"] == 1
    assert cases["pr_created_answer_lost"]["pull_requests_after_both"] == 1
    assert cases["branch_created_answer_lost"]["branch_create_applied"] == 1
    assert cases["rate_limited_pr_create"]["pull_requests"] == 1
    assert cases["issue_created_answer_lost"]["reconciled_by_marker"] is True
    assert cases["issue_created_answer_lost"]["issues_on_the_target"] == 1


def test_commit_back_pushes_a_branch_never_the_default_branch(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("commit_back")["observations"]
    assert seen["default_branch_never_pushed"] is True
    assert seen["branch_tip_unchanged_by_second_run"] is True
    assert seen["third_new_revision"]["pr_updated"] is True
    assert seen["open_pull_requests"] == 1
    assert seen["branch_commits_ahead_of_main"] == 2


def test_a_rate_limited_read_honours_retry_after_and_stops_at_the_policy_bound(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    seen = offline("rate_limited_read")["observations"]
    assert seen["recovers_after_two_429"]["waits"] == [7.0, 7.0]
    assert seen["never_clears"]["requests"] == seen["policy_max_attempts"]


def test_no_credential_appears_in_any_output_of_the_rehearsal(
    offline: Callable[[str], dict[str, Any]],
) -> None:
    results = [offline(s.__name__) for s in cycle.SCENARIOS]
    scan = cycle.credential_scan(offline.work, results)  # type: ignore[attr-defined]
    assert scan["verdict"] == "PROVEN", scan
    assert scan["observations"]["files_scanned"] > 10


def test_the_credential_scan_fires_on_a_planted_token(tmp_path: Path) -> None:
    """Negative control: a scan that cannot fire proves nothing."""
    (tmp_path / "log.txt").write_text(f"Authorization: Bearer {cycle.FAKE_TOKEN}\n")
    (tmp_path / "other.txt").write_text("ghp_" + "a" * 36)
    (tmp_path / "clean.txt").write_text("nothing here\n")
    hits = scan_for_secrets([tmp_path], [cycle.FAKE_TOKEN])
    assert sorted(Path(h).name for h in hits) == ["log.txt", "other.txt"]


# --- the fake REST service's own contract ---------------------------------------------------


def _rest() -> fake_rest.FakeGitHubRest:
    rest = fake_rest.FakeGitHubRest(app_id=7, installation_scope=["o/r"])
    rest.add_repository("o/r", readme="old\n")
    return rest


def test_the_fake_rest_enforces_githubs_write_rules() -> None:
    rest = _rest()
    url = f"{fake_rest.API_ROOT}/repos/o/r/contents/README.md"
    payload = {"message": "m", "branch": "main", "content": "bmV3Cg=="}
    assert rest.put(url, "t", payload)[0] == 422  # an existing file needs its sha
    assert rest.put(url, "t", {**payload, "sha": "stale"})[0] == 409
    sha = rest.fetch(f"{url}?ref=main", "t")[1]["sha"]
    assert rest.put(url, "t", {**payload, "sha": sha})[0] == 200
    pulls = f"{fake_rest.API_ROOT}/repos/o/r/pulls"
    assert rest.post(pulls, "t", {"title": "t", "head": "nope", "base": "main"})[0] == 422
    refs = f"{fake_rest.API_ROOT}/repos/o/r/git/refs"
    base = rest.branch("o/r", "main")
    assert rest.post(refs, "t", {"ref": "refs/heads/b", "sha": base})[0] == 201
    assert rest.post(pulls, "t", {"title": "t", "head": "b", "base": "main"})[0] == 201
    assert rest.post(pulls, "t", {"title": "t", "head": "b", "base": "main"})[0] == 422


def test_an_injected_fault_applies_the_write_or_not_as_it_claims() -> None:
    rest = _rest()
    url = f"{fake_rest.API_ROOT}/repos/o/r/issues"
    rest.inject("POST", r"/issues$", "lose_response")
    status, _ = rest.post(url, "t", {"title": "lost", "body": "b"})
    assert status == -1 and len(rest.issues("o/r")) == 1  # applied, answer lost
    rest.inject("POST", r"/issues$", "drop")
    status, _ = rest.post(url, "t", {"title": "dropped", "body": "b"})
    assert status == -1 and len(rest.issues("o/r")) == 1  # never arrived
    rest.inject("POST", r"/issues$", "status", status=429, retry_after="3")
    assert rest.post(url, "t", {"title": "limited", "body": "b"})[0] == 429
    assert rest.post(url, "t", {"title": "fine", "body": "b"})[0] == 201  # faults are consumed
    assert len(rest.issues("o/r")) == 2


def test_the_fake_rest_never_records_a_token_value() -> None:
    rest = _rest()
    rest.fetch(f"{fake_rest.API_ROOT}/repos/o/r", cycle.FAKE_TOKEN)
    rest.post(f"{fake_rest.API_ROOT}/repos/o/r/issues", cycle.FAKE_TOKEN, {"title": "t"})
    dumped = json.dumps([rest.requests, rest.writes])
    assert cycle.FAKE_TOKEN not in dumped and "bearer" in dumped


# --- with the model's transport: outage, budget, the happy path ----------------------------


def _present(root: Path, remote: Path, run_id: str, *extra: str) -> int:
    return main(
        [
            "present",
            "--repo",
            CANARY,
            "--root",
            str(root),
            "--durable-state",
            "--state-remote",
            str(remote),
            "--workflow-run-id",
            run_id,
            *extra,
        ]
    )


def _record(remote: Path) -> Any:
    with GitStateBackend(remote=str(remote)) as backend:
        return backend.load(CANARY)


def _ledger(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "runs" / "transactions").rglob("calls.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text("utf-8").splitlines() if line)
    return rows


@pytest.fixture
def no_retry_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    def fast(op: str, operation: Any, *, sleep: Any = None, max_attempts: int | None = None) -> Any:
        return run_with_retry(op, operation, sleep=lambda _s: None, max_attempts=max_attempts)

    monkeypatch.setattr(jobs, "run_with_retry", fast)


def test_a_gateway_outage_costs_no_content_call_and_the_next_cycle_completes(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: Any,
    canary_registry: None,
    no_retry_sleep: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_model_evidence: dict[str, Any],
) -> None:
    """The documented qwen3-next outage, replayed at the gateway: it is caught at the availability
    probe, before any content call, so the call budget is untouched; the transaction records it as
    FAILED_INTERNAL (TC-REF-06 has not landed, so there is no BLOCKED_EXTERNAL yet) and the next
    cycle, with the gateway back, completes the same repository."""
    remote = init_git_repository(tmp_path / "state-remote")
    outage = {"on": True}
    seen: list[str] = []

    def gateway(request: httpx.Request) -> httpx.Response:
        if outage["on"]:
            seen.append("outage")
            return httpx.Response(500, json=OUTAGE_BODY)
        return gateway_ready(request)

    mock_gateway(monkeypatch, gateway)
    code = _present(project_with_registry, remote, "3001")
    failed_err = capsys.readouterr().err
    failed = _record(remote)

    outage["on"] = False
    recovered_code = _present(project_with_registry, remote, "3002")
    capsys.readouterr()
    recovered = _record(remote)
    again_code = _present(project_with_registry, remote, "3003")
    capsys.readouterr()
    proven = _record(remote)

    observations = {
        "gateway_answered_the_documented_500": len(seen),
        "content_calls_made_during_the_outage": 0,
        "first_cycle_exit_code": code,
        "first_cycle_stderr": failed_err.strip(),
        "provider_calls_recorded_in_the_ledger_before_recovery": 0,
        "durable_state_after_the_outage": failed.state,
        "failure_classification": failed.failure.classification,
        "lease_released": failed.lease is None,
        "recovery_cycle": {"exit_code": recovered_code, "state": recovered.state},
        "no_op_cycle": {"exit_code": again_code, "state": proven.state},
        "content_requests_to_complete": len(gateway_ready.requests),
    }
    assert code != EXIT_OK and "availability probes" in failed_err
    assert seen and not gateway_ready.requests[:0]
    assert failed.state == "FAILED_INTERNAL" and failed.lease is None
    assert (recovered_code, recovered.state) == (EXIT_OK, "ACCEPTED")
    assert (again_code, proven.state) == (EXIT_OK, "READY_FOR_PROPOSAL")
    assert len(gateway_ready.requests) == 12
    fake_model_evidence["scenarios"].append(
        {
            "scenario": "gateway-outage",
            "acceptance": "provider outage is BLOCKED_EXTERNAL, no budget burn, retried next cycle",
            "verdict": "PROVEN_WITH_GAP",
            "observations": observations,
            "gap": "The outage is classified FAILED_INTERNAL, not BLOCKED_EXTERNAL: nothing in "
            "core/llm or core/state maps a gateway outage to BLOCKED_EXTERNAL (TC-REF-06, "
            "OWNER-12). The sealing plan's failure memory then treats the repository as a stuck "
            "defect and skips it for 24 hours unless a new commit lands (run_cap_and_cooldown "
            "shows the skip), so 'retried next cycle' holds for a manual or dispatched run and "
            "not for the scheduled plan. No call budget is spent: the probe fails before any "
            "content call and probes are not recorded in the ledger. Pinned by this test: when "
            "TC-REF-06 lands, the FAILED_INTERNAL assertion here must become BLOCKED_EXTERNAL.",
        }
    )


def test_an_outage_after_the_probes_burns_only_the_bounded_retries_of_one_call(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: Any,
    canary_registry: None,
    no_retry_sleep: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_model_evidence: dict[str, Any],
) -> None:
    remote = init_git_repository(tmp_path / "state-remote")
    sent: list[str] = []

    def gateway(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        if payload["messages"] == [{"role": "user", "content": "ping"}]:
            return gateway_ready(request)  # the probes pass; the content calls then fail
        sent.append(payload["response_format"]["json_schema"]["name"])
        return httpx.Response(500, json=OUTAGE_BODY)

    mock_gateway(monkeypatch, gateway)
    code = _present(project_with_registry, remote, "3101")
    err = capsys.readouterr().err
    record = _record(remote)
    rows = _ledger(project_with_registry)
    attempts = [(r["job"], r["outcome"], r["http_status"]) for r in rows]
    assert code != EXIT_OK and "did not answer after the bounded retries" in err
    assert len(sent) == 3 and set(sent) == {"repository_investigation"}
    assert attempts == [("repository_investigation", "http_error", 500)] * 3
    assert record.state == "FAILED_INTERNAL"
    fake_model_evidence["scenarios"].append(
        {
            "scenario": "gateway-outage-after-the-probes",
            "acceptance": "provider outage is BLOCKED_EXTERNAL, no budget burn, retried next cycle",
            "verdict": "PROVEN_WITH_GAP",
            "observations": {
                "content_requests_sent": len(sent),
                "ledger_attempts": attempts,
                "run_stopped_at": "the first content job; the other jobs never ran",
                "exit_code": code,
                "durable_state": record.state,
            },
            "gap": "An outage that starts after the probes spends the llm_call policy's three "
            "attempts on the first job (3 of the 100-call per-process budget) and the run ends "
            "FAILED_INTERNAL; there is no outage-aware stop that spends nothing.",
        }
    )


def test_the_per_run_call_budget_stops_the_cycle_and_the_next_run_does_not_pay_twice(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: Any,
    canary_registry: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_model_evidence: dict[str, Any],
) -> None:
    remote = init_git_repository(tmp_path / "state-remote")
    budget = 4

    class SmallLedger(Ledger):
        def __init__(self, path: Path, invocation_id: str | None = None) -> None:
            super().__init__(path, invocation_id, call_budget=budget)

    monkeypatch.setattr(cli, "Ledger", SmallLedger)
    code = _present(project_with_registry, remote, "3201")
    err = capsys.readouterr().err
    stopped = _record(remote)
    sent_when_stopped = len(gateway_ready.requests)
    monkeypatch.setattr(cli, "Ledger", Ledger)
    resumed_code = _present(project_with_registry, remote, "3202")
    capsys.readouterr()
    resumed = _record(remote)
    assert code != EXIT_OK and f"budget of {budget} reached" in err
    assert sent_when_stopped == budget
    assert stopped.state == "FAILED_INTERNAL"
    assert (resumed_code, resumed.state) == (EXIT_OK, "ACCEPTED")
    assert len(gateway_ready.requests) == 12  # the four paid calls were reused, not repeated
    fake_model_evidence["scenarios"].append(
        {
            "scenario": "per-run-call-budget",
            "acceptance": "the per-run call budget stops the cycle",
            "verdict": "PROVEN_WITH_GAP",
            "observations": {
                "budget": budget,
                "requests_sent_when_stopped": sent_when_stopped,
                "exit_code": code,
                "stderr": err.strip(),
                "durable_state": stopped.state,
                "requests_in_total_after_the_resumed_run": len(gateway_ready.requests),
                "resumed_run": {"exit_code": resumed_code, "state": resumed.state},
            },
            "gap": "The ceiling is per process (PROVIDER_CALL_BUDGET = 100), so a cycle is bounded "
            "at 3 repositories x 100 calls; a per-day budget does not exist (TC-REF-02-02), and "
            "exhausting the ceiling ends FAILED_INTERNAL rather than a budget-specific stop.",
        }
    )


def test_the_whole_cycle_on_a_synthetic_upstream_opens_one_pull_request_and_then_nothing(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: Any,
    canary_registry: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fake_model_evidence: dict[str, Any],
) -> None:
    """Seal, then watch: monitor -> plan -> present -> verify-noop-proof -> publish-candidates ->
    propose, against a local upstream, a local state remote, a local control remote and the fake
    REST. A consumed-path commit yields one candidate update and one pull request; an irrelevant
    commit and an unchanged revision yield nothing and no provider call."""
    root = project_with_registry
    source = local_canary["source"]
    remote = init_git_repository(tmp_path / "state-remote")
    world_dir = tmp_path / "world"
    bare = world_dir / "upstreams" / CANARY_OWNER / f"{CANARY.split('/')[1]}.git"
    bare.parent.mkdir(parents=True)
    cycle._git(["clone", "-q", "--bare", str(source), str(bare)], tmp_path)
    world = fake_github.World(world_dir)
    fetch = cycle._world_fetch(world)
    monkeypatch.setattr(
        cli,
        "fetch_default_branch_sha",
        lambda repository, token=None: read_client.fetch_default_branch_sha(
            repository, token=token, fetch=fetch, sleep=lambda _s: None
        ),
    )
    monkeypatch.setattr(
        cli,
        "fetch_tree",
        lambda repository, revision, token=None: read_client.fetch_tree(
            repository, revision, token=token, fetch=fetch, sleep=lambda _s: None
        ),
    )
    monkeypatch.setenv("GH_TOKEN", cycle.FAKE_TOKEN)
    gateway = gateway_ready
    phases: dict[str, Any] = {}

    def present_twice(label: str, run_id: str) -> str:
        """The hosted present.yml pair: a run, then its no-op rerun, then the proof gate."""
        before = len(gateway.requests)
        first = root / f"{label}-first.json"
        second = root / f"{label}-second.json"
        assert _present(root, remote, run_id, "--invocation-record", str(first)) == EXIT_OK
        made = len(gateway.requests) - before
        assert (
            _present(root, remote, f"{run_id}-noop-proof", "--invocation-record", str(second))
            == EXIT_OK
        )
        rerun = len(gateway.requests) - before - made
        proof = main(
            [
                "verify-noop-proof",
                "--first",
                str(first),
                "--second",
                str(second),
                "--root",
                str(root),
            ]
        )
        ready = main(["sealed-ready", "--repo", CANARY, "--root", str(root)])
        capsys.readouterr()
        assert (proof, ready) == (EXIT_OK, EXIT_OK)
        phases[label] = {"provider_calls_first_run": made, "provider_calls_rerun": rerun}
        assert rerun == 0
        return (root / "candidates" / CANARY_SLUG / "CURRENT").read_text("utf-8").strip()

    def watch(label: str) -> dict[str, Any]:
        """One monitor + plan cycle; returns the canary's row and the plan's decision."""
        evidence = tmp_path / f"drift-{label}"
        evidence.mkdir()
        code = main(
            [
                "monitor",
                "--root",
                str(root),
                "--owner",
                CANARY_OWNER,
                "--out",
                str(evidence / f"drift-{CANARY_OWNER}.json"),
            ]
        )
        capsys.readouterr()
        assert code == EXIT_OK
        contract = assemble_drift_contract(
            evidence, expected={CANARY_OWNER: frozenset({CANARY})}, now=datetime.now(UTC)
        )
        drift_file = tmp_path / f"contract-{label}.json"
        drift_file.write_text(json.dumps(contract.document), encoding="utf-8")
        outputs = tmp_path / f"plan-{label}.out"
        plan_code = main(
            [
                "sealing-plan",
                "--root",
                str(root),
                "--drift-file",
                str(drift_file),
                "--github-output",
                str(outputs),
            ]
        )
        capsys.readouterr()
        assert plan_code == EXIT_OK
        row = next(
            r
            for r in json.loads((evidence / f"drift-{CANARY_OWNER}.json").read_text("utf-8"))[
                "repositories"
            ]
            if r["repository"] == CANARY
        )
        return {"status": row["status"], "change": row["change"], **cycle._plan_outputs(outputs)}

    # 1. Seal the first candidate through the hosted pair and the no-op proof gate.
    first_revision = present_twice("seal", "4001")
    assert _record(remote).state == "READY_FOR_PROPOSAL"
    assert first_revision == local_canary["revision"]

    # 2. An unchanged revision: nothing to do, and a rerun of present makes no provider call.
    before = len(gateway.requests)
    quiet = watch("unchanged")
    assert (quiet["change"], quiet["has_work"]) == ("NO_CHANGE", "false")
    assert _present(root, remote, "4002") == EXIT_OK
    capsys.readouterr()
    assert len(gateway.requests) == before
    phases["unchanged_revision"] = {**quiet, "provider_calls": 0}

    # 3. A commit that touches nothing the README consumed: seen, classified, not selected.
    (source / "NOTES.txt").write_text("Release notes.\n", encoding="utf-8")
    commit_all(source, "add release notes")
    cycle._git(["push", "-q", "--force", str(bare), "main"], source)
    irrelevant = watch("irrelevant")
    assert (irrelevant["change"], irrelevant["has_work"]) == ("IRRELEVANT_CHANGE", "false")
    phases["irrelevant_commit"] = irrelevant

    # 4. A commit that changes a consumed source file: relevant, selected, one candidate update.
    (source / "aspose" / "threed" / "__init__.py").write_text(
        "class Scene:\n    name = 'scene'\n\n"
        "    def save(self, path):\n        open(path, 'wb').write(b'glb')\n",
        encoding="utf-8",
    )
    commit_all(source, "write a minimal GLB header")
    cycle._git(["push", "-q", "--force", str(bare), "main"], source)
    relevant = watch("relevant")
    assert (relevant["change"], relevant["has_work"]) == ("RELEVANT_CHANGE", "true")
    assert json.loads(relevant["repositories"]) == [{"repository": CANARY, "slug": CANARY_SLUG}]
    phases["relevant_commit"] = relevant
    second_revision = present_twice("reseal", "4003")
    assert second_revision != first_revision
    assert _record(remote).state == "READY_FOR_PROPOSAL"

    # 5. Commit back to the control repository: one pull request on its own branch.
    artifact = tmp_path / "artifact"
    shutil.copytree(root / "candidates" / CANARY_SLUG / second_revision, artifact / second_revision)
    (artifact / "CURRENT").write_text(f"{second_revision}\n", encoding="utf-8")
    control_rest = cycle._rest(cycle.CONTROL, readme="control\n")
    control = cycle.ControlRemote(tmp_path / "control", cycle.CONTROL, control_rest, target=CANARY)
    published = control.publish(artifact, second_revision)
    republished = control.publish(artifact, second_revision)
    assert published.pr_created and published.commit_written and not republished.commit_written
    assert not republished.pr_created
    assert len(control_rest.pulls(cycle.CONTROL, "open")) == 1
    phases["commit_back"] = {
        "first": cycle._publish_view(published),
        "second_run": cycle._publish_view(republished),
        "open_pull_requests": 1,
    }

    # 6. Propose to the product repository: the registry write gate, then the generated PR.
    registry = load_registry(root / "data" / "registry.json")
    with pytest.raises(WriteRefusedError):
        require_write_permitted(registry, CANARY, "readme_proposal")  # the canary is dry_run
    try:
        load_proposable_candidate(root, CANARY, acceptance=proposal_acceptance_gate(root))
        real_gate = "PASS"
    except WriteRefusedError as refusal:
        real_gate = f"refused: {refusal}"[:300]
    candidate = load_proposable_candidate(root, CANARY, acceptance=lambda _b, _d: None)
    evidence_for_pr = load_pull_request_evidence(candidate.bundle)
    rest = fake_rest.FakeGitHubRest(app_id=cycle.EXPECTED_APP_ID, installation_scope=[CANARY])
    rest.add_repository(CANARY, readme=(source / "README.md").read_text("utf-8"))
    head = world.head(CANARY)
    assert head == candidate.revision == second_revision

    def propose() -> Any:
        stamp = "%Y-%m-%dT%H:%M:%SZ"
        now = datetime.now(UTC)
        return propose_candidate(
            repository=CANARY,
            readme_text=candidate.readme_text,
            source_revision=head,
            base_branch="main",
            token=cycle.FAKE_TOKEN,
            environment={AUTHORIZATION_VARIABLE: "1"},
            permit=cycle._permit(CANARY),
            load_authorization=lambda: authorize_proposal(
                repository=CANARY,
                candidate_hash=candidate.candidate_hash,
                source_revision=head,
                base_branch="main",
                branch=presenter_branch_name(),
                approver="rehearsal-owner",
                issued_at=(now - timedelta(minutes=1)).strftime(stamp),
                expires_at=(now + timedelta(hours=1)).strftime(stamp),
            ),
            recheck_source=lambda: world.head(CANARY),
            compose_pull_request=lambda live: compose_pull_request(
                candidate_readme=candidate.readme_text,
                live_readme=live,
                repository=CANARY,
                evidence=evidence_for_pr,
                candidate_hash=candidate.candidate_hash,
                source_revision=head,
                policy_version="rehearsal",
            ),
            **cycle.propose_seams(rest, CANARY),
        )

    opened = propose()
    pull = rest.pulls(CANARY)[0]
    writes_after_open = len(rest.applied_writes())
    again = propose()
    assert opened.effected and opened.pr_created and opened.commit_written
    assert again.effected and again.reason == "no change needed"
    assert len(rest.applied_writes()) == writes_after_open and len(rest.pulls(CANARY)) == 1
    assert rest.file(CANARY, "main", "README.md") == (source / "README.md").read_text("utf-8")
    assert rest.file(CANARY, presenter_branch_name(), "README.md") == candidate.readme_text
    assert "### What changed" in pull["body"] and candidate.candidate_hash in pull["body"]
    assert pull["title"] and len(pull["title"]) < 120
    phases["propose"] = {
        "registry_gate_refuses_the_dry_run_canary": True,
        "real_acceptance_gate_on_the_scripted_candidate": real_gate,
        "first_run": cycle._summary(opened),
        "second_run": cycle._summary(again),
        "pull_requests": 1,
        "pull_request_title": pull["title"],
        "pull_request_body_sections": [
            line for line in pull["body"].splitlines() if line.startswith("### ")
        ],
        "default_branch_readme_untouched": True,
    }

    # 7. The next cycle: the candidate is current, nothing is selected, no provider call.
    before = len(gateway.requests)
    final = watch("final")
    assert (final["change"], final["has_work"]) == ("NO_CHANGE", "false")
    assert _present(root, remote, "4004") == EXIT_OK
    capsys.readouterr()
    assert len(gateway.requests) == before
    phases["next_cycle"] = {**final, "provider_calls": 0}
    leaks = scan_for_secrets([tmp_path], [cycle.FAKE_TOKEN])
    assert leaks == []
    fake_model_evidence["scenarios"].append(
        {
            "scenario": "whole-cycle-happy-path-and-no-op",
            "acceptance": "a synthetic upstream commit that touches a consumed path produces "
            "exactly one candidate update and, at the propose step, one pull request; an "
            "irrelevant commit produces none; an unchanged revision makes zero provider calls",
            "verdict": "PROVEN_WITH_GAP",
            "observations": {
                "upstream": "the canary fixture of tests/test_cli.py served from a local bare "
                "repository through fake_github.route (no network)",
                "phases": phases,
                "credential_scan_hits": len(leaks),
            },
            "gap": "The model is scripted (tests/test_cli.py's _ChatGateway), not the live "
            "gateway, and the product README is the canary's fixture: this proves the wiring, the "
            "idempotence and the zero-call no-op, not the quality of a real composition. The real "
            "30-point acceptance gate does not pass the scripted candidate (recorded under "
            "phases.propose), so the propose step uses a permissive gate for mechanics only; the "
            "registry write gate is shown refusing the dry_run canary and a full-mode permit is "
            "constructed. The owner-named throwaway target (TC-REF-04-02) is where the live "
            "write is proven.",
        }
    )
