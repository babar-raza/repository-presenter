"""The whole autonomous cycle, rehearsed locally with no model and no network (TC-REF-11).

``harness.py`` runs the unmodified workflows in containers; this module drives the *code those
workflows call* through every failure mode and effect the cycle has, against local fakes only:

- a bare git remote carrying the durable-state refs (``refs/repository-presenter-state/*``), driven
  by two independent ``GitStateBackend`` workers (stale lease, killed run);
- the synthetic upstreams of ``scenarios.py`` served by ``fake_github.route`` through the real
  ``core/github/read_client.py`` (monitor -> relevance -> drift contract -> sealing plan);
- ``fake_rest.FakeGitHubRest``, a stateful REST model behind the real ``core/github/client.py`` and
  ``token_provenance.py`` seams (propose, commit-back, issue filing, lost responses, rate limits);
- a local bare control repository for the commit-back push.

Each scenario returns a JSON-able dict: ``scenario``, ``acceptance`` (the TC-REF-11 line it speaks
to), ``verdict`` (``PROVEN``, ``PROVEN_WITH_GAP`` or ``GAP``), ``observations`` and, when the code
does not yet meet the line, ``gap``. A verdict is computed from what the real code did, never
asserted. Scenarios that need the model's transport (outage, budget, the happy path with a fake
gateway) live in ``tests/test_workflow_rehearsal_cycle.py`` because they reuse ``tests/test_cli.py``'s
scripted gateway; they write their evidence through :func:`record`.

Run: ``PYTHONPATH=src python tools/workflow_rehearsal/cycle.py --out <evidence dir>``. Every request
the fakes saw, every git history and every captured output is written under a scratch directory and
scanned for the fake credential and for credential-shaped strings at the end.
"""

from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest import mock

import fake_github
import fake_rest
import httpx
import scenarios
from harness import scan_for_secrets
from inventory import REPO_ROOT
from repository_presenter import cli
from repository_presenter.components.candidates_publish import effect as publish_effect
from repository_presenter.components.candidates_publish import git_ops
from repository_presenter.components.issues.file import fingerprint_marker
from repository_presenter.components.monitor.drift import (
    RepositoryDrift,
    assemble_drift_contract,
    drift_document,
    observe_repository,
)
from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE,
    presenter_branch_name,
    propose_candidate,
)
from repository_presenter.core.authorization.proposal import authorize_proposal
from repository_presenter.core.errors import (
    IllegalTransitionError,
    RepositoryMetadataError,
)
from repository_presenter.core.github import client, read_client
from repository_presenter.core.github.token_provenance import (
    EXPECTED_APP_ID,
    verify_installation_token,
    verify_pull_request_app,
)
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.models import Registry, RegistryEntry
from repository_presenter.core.registry.write_gate import WritePermit
from repository_presenter.core.retry import RETRY_POLICIES
from repository_presenter.core.sealing_plan import (
    MAX_REPOSITORIES_PER_RUN,
    SEALING_PAUSED_VARIABLE,
    SealingAttempt,
    parse_drift_contract,
    plan_sealing_run,
    sealing_paused,
)
from repository_presenter.core.state.cas import (
    acquire_lease,
    lease_is_current,
    record_transition,
    release_lease,
    renew_lease,
)
from repository_presenter.core.state.git_backend import (
    STATE_REF_PREFIX,
    GitStateBackend,
)
from repository_presenter.core.state.present_transaction import (
    PresentOutcome,
    run_present_transaction,
)
from repository_presenter.core.state.recovery import recovery_sweep, resume_recoverable
from repository_presenter.core.state.trigger import admit_trigger, normalize_trigger

#: Looks like an installation token (``verify_installation_token`` requires the ``ghs_`` prefix) and
#: matches the leak scan's credential pattern, so a leak of it anywhere is caught twice over.
FAKE_TOKEN = "ghs_FAKEREHEARSALFAKEREHEARSALFAKEREHEARSAL"
POLICY = "rehearsal"
STATE_REPO = "rehearsal-org/relevant-change"
STATE_ID = 4242
TARGET = "rehearsal-org/target-product"
CONTROL = "rehearsal-org/control"
EVIDENCE_ENV = "RP_REHEARSAL_EVIDENCE_DIR"


# --- shared helpers --------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> str:
    return scenarios._git(args, cwd)


def _bare(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q", "--bare", "-b", "main", str(path)], path.parent)
    return path


def _history(bare: Path) -> str:
    """Every ref's full commit history with patches: what a reader of the remote could see."""
    try:
        return _git(["log", "--all", "-p", "--format=%H %s"], bare)
    except subprocess.CalledProcessError:
        return ""


def _count(bare: Path, ref: str) -> int:
    return int(_git(["rev-list", "--count", ref], bare))


def _dump(work: Path, name: str, payload: Any) -> None:
    """Persist an output of the rehearsal where the final credential scan will read it."""
    target = work / "outputs" / f"{name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )


def _result(
    scenario: str,
    acceptance: str,
    verdict: str,
    observations: dict[str, Any],
    gap: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario": scenario,
        "acceptance": acceptance,
        "verdict": verdict,
        "observations": observations,
    }
    if gap:
        out["gap"] = gap
        if verdict == "PROVEN":
            out["verdict"] = "PROVEN_WITH_GAP"
    return out


def _all(checks: dict[str, bool]) -> str:
    return "PROVEN" if all(checks.values()) else "FAILED"


def _entry(repository: str, mode: str = "dry_run") -> RegistryEntry:
    """A registry entry for a synthetic repository: the model validates real Aspose FOSS names, so
    a rehearsal fixture is built without that check (``tests/support.make_permit`` does the same)."""
    return RegistryEntry.model_construct(
        repository=repository,
        family="rehearsal",
        platform="python",
        ecosystem="python",
        mode=mode,
        issues_mode=None,
        policy_profile="rehearsal",
        active=True,
        provider_identity=None,
    )


def _registry(entries: list[RegistryEntry]) -> Registry:
    return Registry.model_construct(schema_version=1, entries=tuple(entries))


# --- durable state: stale lease, killed run ---------------------------------------------------


def _transition(
    backend: GitStateBackend, lease: Any, to_state: str, now: datetime
) -> Any:
    return record_transition(
        backend,
        STATE_REPO,
        lease,
        to_state=to_state,  # type: ignore[arg-type]
        event="rehearsal",
        input_manifest="rehearsal",
        output_manifest="rehearsal",
        policy_version=POLICY,
        provider_repository_id=STATE_ID,
        now=now,
    )


def stale_lease_fenced(work: Path) -> dict[str, Any]:
    """Worker A holds a lease and stops heartbeating; B recovers and resumes under a higher fencing
    token; A wakes and tries to commit, renew and release. None of it may land."""
    remote = _bare(work / "state-remote.git")
    t0 = datetime(2026, 10, 11, 6, 0, tzinfo=UTC)
    later = t0 + timedelta(minutes=20)
    with (
        GitStateBackend(remote=str(remote)) as a,
        GitStateBackend(remote=str(remote)) as b,
    ):
        trigger = normalize_trigger(
            STATE_REPO, event_type="workflow_dispatch", workflow_run_id="1001"
        )
        admission = admit_trigger(
            a, trigger, holder_id="worker-a", provider_repository_id=STATE_ID, now=t0
        )
        stale = admission.lease
        assert stale is not None
        _transition(a, stale, "SNAPSHOTTING", t0)
        contended = acquire_lease(
            b,
            STATE_REPO,
            holder_id="worker-b",
            provider_repository_id=STATE_ID,
            now=t0 + timedelta(minutes=5),
        )
        swept = recovery_sweep(b, {STATE_REPO: STATE_ID}, now=later)
        resumed = resume_recoverable(
            b,
            STATE_REPO,
            holder_id="worker-b",
            provider_repository_id=STATE_ID,
            now=later,
        )
        assert resumed is not None
        resumed_record, fresh = resumed
        zombie_commit = ""
        try:
            _transition(a, stale, "EXTRACTING", later)
        except IllegalTransitionError as exc:
            zombie_commit = str(exc)
        zombie_renewal = renew_lease(
            a, STATE_REPO, stale, provider_repository_id=STATE_ID, now=later
        )
        release_lease(a, STATE_REPO, stale, provider_repository_id=STATE_ID)
        survivor = b.load(STATE_REPO)
        b_still_holds = lease_is_current(b, STATE_REPO, fresh)
        a_still_holds = lease_is_current(b, STATE_REPO, stale)
        advanced = _transition(b, fresh, "EXTRACTING", later)
        final = b.load(STATE_REPO)
    assert survivor is not None and final is not None
    refs = _git(
        ["for-each-ref", "--format=%(refname)", STATE_REF_PREFIX], remote
    ).splitlines()
    _dump(work, "stale-lease-state-history", _history(remote))
    observations = {
        "durable_refs_on_the_remote": refs,
        "ref_commit_count": _count(remote, refs[0]) if refs else 0,
        "fencing_tokens": {
            "worker_a": stale.fencing_token,
            "worker_b": fresh.fencing_token,
        },
        "contended_acquire_while_live": "refused" if contended is None else "GRANTED",
        "recovery_swept": [(o.prior_state, o.reason) for o in swept],
        "transaction_id_unchanged": resumed_record.active_transaction_id
        == admission.transaction_id,
        "zombie_commit": zombie_commit or "ACCEPTED (defect)",
        "zombie_renewal": "refused" if zombie_renewal is None else "GRANTED",
        "lease_after_zombie_attempts": {
            "worker_b_holds": b_still_holds,
            "worker_a_holds": a_still_holds,
            "holder": survivor.lease.holder_id if survivor.lease else None,
        },
        "state_after_zombie_attempts": survivor.state,
        "worker_b_continues_to": advanced[0].state,
        "final_state_version": final.state_version,
    }
    checks = {
        "refs": bool(refs),
        "higher token": fresh.fencing_token == stale.fencing_token + 1,
        "contended": contended is None,
        "zombie commit refused": "stale" in zombie_commit,
        "zombie renewal refused": zombie_renewal is None,
        "b holds": b_still_holds and not a_still_holds,
        "state untouched": survivor.state == "SNAPSHOTTING",
        "same transaction": observations["transaction_id_unchanged"] is True,
        "b continues": advanced[0].state == "EXTRACTING",
    }
    return _result(
        "stale-lease-fenced",
        "a stale lease is fenced",
        _all(checks),
        observations,
    )


#: Runs in a child process that dies the way a killed hosted job does: mid-transaction, with work
#: done and the lease never released (``os._exit`` skips every ``finally``).
_VICTIM = """
import os, sys
from datetime import UTC, datetime, timedelta
from repository_presenter.core.state.cas import record_transition
from repository_presenter.core.state.git_backend import GitStateBackend
from repository_presenter.core.state.trigger import admit_trigger, normalize_trigger
remote, repository, identity, marker = sys.argv[1:5]
pid = int(identity)
backend = GitStateBackend(remote=remote)
past = datetime.now(UTC) - timedelta(hours=2)
trigger = normalize_trigger(repository, event_type="workflow_dispatch", workflow_run_id="2001")
admission = admit_trigger(backend, trigger, holder_id="victim", provider_repository_id=pid, now=past)
for state in ("SNAPSHOTTING", "EXTRACTING", "INVESTIGATING"):
    record_transition(backend, repository, admission.lease, to_state=state, event="victim",
                      input_manifest="rehearsal", output_manifest="rehearsal",
                      policy_version="rehearsal", provider_repository_id=pid, now=past)
open(marker, "w").write("investigation call made\\n")
os._exit(137)
"""


def kill_mid_transaction(work: Path) -> dict[str, Any]:
    """A worker dies after paying for a stage; the next hosted run recovers that transaction under a
    higher fencing token, runs the pipeline once, and replays of the dead run's trigger do nothing."""
    remote = _bare(work / "state-remote-kill.git")
    marker = work / "victim-work.txt"
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "GIT_TERMINAL_PROMPT": "0",
    }
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            _VICTIM,
            str(remote),
            STATE_REPO,
            str(STATE_ID),
            str(marker),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    _dump(
        work,
        "kill-victim-output",
        {
            "returncode": child.returncode,
            "stdout": child.stdout,
            "stderr": child.stderr,
        },
    )
    ran: list[str] = []
    replays: list[str] = []

    def run() -> int:
        ran.append("pipeline")
        return 0

    def classify(_exit_code: int) -> PresentOutcome:
        return PresentOutcome(kind="success", target_state="READY_FOR_PROPOSAL")

    with GitStateBackend(remote=str(remote)) as backend:
        dead = backend.load(STATE_REPO)
        assert dead is not None and dead.lease is not None
        code = run_present_transaction(
            backend=backend,
            repository=STATE_REPO,
            provider_repository_id=STATE_ID,
            holder_id="recovery-worker",
            run=run,
            classify=classify,
            workflow_run_id="2002",
        )
        recovered = backend.load(STATE_REPO)
        replay_code = run_present_transaction(
            backend=backend,
            repository=STATE_REPO,
            provider_repository_id=STATE_ID,
            holder_id="duplicate-worker",
            run=lambda: replays.append("pipeline") or 0,
            classify=classify,
            workflow_run_id="2001",
        )
        after_replay = backend.load(STATE_REPO)
    assert recovered is not None and after_replay is not None
    _dump(work, "kill-state-history", _history(remote))
    observations = {
        "victim_exit_code": child.returncode,
        "victim_work_done_before_death": marker.read_text(encoding="utf-8").strip(),
        "state_the_dead_worker_left": dead.state,
        "dead_worker_fencing_token": dead.lease.fencing_token,
        "recovery_run_exit_code": code,
        "pipeline_runs_in_recovery": len(ran),
        "same_transaction_resumed": recovered.active_transaction_id
        == dead.active_transaction_id,
        "recovery_count": recovered.recovery_count,
        "final_state": recovered.state,
        "final_fencing_token": recovered.last_transition.fencing_token
        if recovered.last_transition
        else None,
        "lease_released": recovered.lease is None,
        "replay_of_the_dead_trigger": {
            "exit_code": replay_code,
            "pipeline_runs": len(replays),
            "state_version_unchanged": after_replay.state_version
            == recovered.state_version,
        },
    }
    checks = {
        "worker died": child.returncode == 137,
        "left active": dead.state == "INVESTIGATING",
        "ran once": len(ran) == 1,
        "same transaction": observations["same_transaction_resumed"] is True,
        "counted": recovered.recovery_count == 1,
        "completed": recovered.state == "READY_FOR_PROPOSAL",
        "higher token": (observations["final_fencing_token"] or 0)
        > dead.lease.fencing_token,
        "lease released": recovered.lease is None,
        "replay is a no-op": not replays
        and observations["replay_of_the_dead_trigger"]["state_version_unchanged"],
    }
    return _result(
        "kill-mid-transaction",
        "a run killed mid-transaction recovers without double processing",
        _all(checks),
        observations,
    )


# --- the cycle's stop switches ----------------------------------------------------------------


def _plan_outputs(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return dict(line.split("=", 1) for line in lines if "=" in line)


def pause_variable(work: Path) -> dict[str, Any]:
    """The owner pause variable stops the cycle before anything is read or sealed; only the exact
    value ``"1"`` pauses."""
    registry = json.loads(
        (REPO_ROOT / "data" / "registry.json").read_text(encoding="utf-8")
    )
    entry = next(
        e["repository"] for e in registry["entries"] if e.get("mode") != "disabled"
    )
    drift = work / "drift.json"
    drift.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repositories": [
                    {
                        "repository": entry,
                        "status": "RELEVANT_CHANGE",
                        "source_revision": "a" * 40,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    outputs: dict[str, dict[str, str]] = {}
    for label, variable in (("paused", "1"), ("not_paused", None)):
        out = work / f"plan-{label}.out"
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (SEALING_PAUSED_VARIABLE, "GPT_OSS_MODEL", "GITHUB_STEP_SUMMARY")
        }
        if variable is not None:
            env[SEALING_PAUSED_VARIABLE] = variable
        with mock.patch.dict(os.environ, env, clear=True):
            code = cli.run_sealing_plan(REPO_ROOT, drift, work / "no-history.json", out)
        outputs[label] = {**_plan_outputs(out), "exit_code": str(code)}
    near_misses = {
        value: sealing_paused({SEALING_PAUSED_VARIABLE: value})
        for value in ("0", "true", " 1", "", "yes", "01")
    }
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "sealing-scheduled.yml"
    ).read_text(encoding="utf-8")
    observations = {
        "plan_when_paused": outputs["paused"],
        "plan_when_not_paused": outputs["not_paused"],
        "values_that_do_not_pause": near_misses,
        "seal_job_runs_only_on_plan_has_work": "needs.plan.outputs.has_work == 'true'"
        in workflow,
        "workflow_passes_the_variable_to_the_plan_step": SEALING_PAUSED_VARIABLE
        in workflow,
    }
    checks = {
        "paused plans nothing": outputs["paused"].get("has_work") == "false"
        and outputs["paused"].get("has_publishable") == "false",
        "unpaused selects": outputs["not_paused"].get("has_work") == "true",
        "exact match only": not any(near_misses.values()),
        "gated": observations["seal_job_runs_only_on_plan_has_work"] is True,
    }
    return _result(
        "pause-variable",
        "the pause variable stops the cycle",
        _all(checks),
        observations,
    )


def run_cap_and_cooldown(work: Path) -> dict[str, Any]:
    """The per-run repository cap, the failure cooldown and the publishable subset, from the same
    planner the scheduled workflow calls."""
    names = [f"rehearsal-org/repo-{c}" for c in "abcde"]
    registry = _registry(
        [_entry(n, "full" if n.endswith(("-a", "-c")) else "dry_run") for n in names]
    )
    revision = {n: f"{i:040x}" for i, n in enumerate(names, start=1)}
    now = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    contract = parse_drift_contract(
        {
            "schema_version": 1,
            "repositories": [
                {
                    "repository": n,
                    "status": "RELEVANT_CHANGE",
                    "source_revision": revision[n],
                }
                for n in names
            ],
        }
    )
    failed = SealingAttempt(
        names[1], "FAILED", now - timedelta(hours=3), revision[names[1]]
    )
    first = plan_sealing_run(contract, registry, [failed], now=now)
    # Next cycle: the three sealed repositories are current, a new commit landed on the failed one.
    second_contract = parse_drift_contract(
        {
            "schema_version": 1,
            "repositories": [
                {
                    "repository": names[1],
                    "status": "RELEVANT_CHANGE",
                    "source_revision": "f" * 40,
                },
                {
                    "repository": names[4],
                    "status": "RELEVANT_CHANGE",
                    "source_revision": revision[names[4]],
                },
            ],
        }
    )
    second = plan_sealing_run(
        second_contract, registry, [failed], now=now + timedelta(hours=24)
    )
    observations = {
        "cap": MAX_REPOSITORIES_PER_RUN,
        "cycle_1": {
            "drifted": 5,
            "selected": list(first.selected),
            "deferred": list(first.deferred),
            "publishable": list(first.publishable),
            "skipped_by_failure_memory": [s.repository for s in first.skipped],
        },
        "cycle_2": {
            "selected": list(second.selected),
            "deferred": list(second.deferred),
        },
        "dry_run_entries_are_sealed_never_published": [
            n for n in first.selected if n not in first.publishable
        ],
    }
    checks = {
        "cap": len(first.selected) == MAX_REPOSITORIES_PER_RUN,
        "deferred, not dropped": first.deferred == (names[4],)
        and names[4] in second.selected,
        "cooldown": [s.repository for s in first.skipped] == [names[1]],
        "new commit lifts the cooldown": names[1] in second.selected,
        "publishable is full only": set(first.publishable) <= {names[0], names[2]},
    }
    return _result(
        "run-cap-and-cooldown",
        "the per-run repository cap bounds a cycle; a failed repository waits out its cooldown",
        _all(checks),
        observations,
        gap="No per-day provider-call budget and no cross-repository open-PR cap exist in code "
        "(TC-REF-02-02 is not landed): the planner bounds a cycle at 3 repositories and a process "
        "at 100 provider calls, and propose/commit-back keep one open PR per target. A day of "
        "cycles is bounded only by the schedule (daily) times those two numbers.",
    )


# --- monitor -> relevance -> contract -> sealing plan ------------------------------------------

_CONSUMED = ("README.md", "pyproject.toml", "src/synthetic/__init__.py")


def _blob(content: str) -> str:
    result = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=content.encode(),
        capture_output=True,
        check=True,
        env={**os.environ, **scenarios._ENV},
    )
    return result.stdout.decode().strip()


def _seal(root: Path, repository: str, revision: str, *, with_blobs: bool) -> None:
    """A sealed READY_FOR_PROPOSAL bundle for the synthetic base tree: the README, the manifest and
    the source file are consumed (the facts cite them); ``docs/NOTES.md`` is not."""
    slug = repository.replace("/", "__")
    bundle = root / "candidates" / slug / revision
    bundle.mkdir(parents=True)
    facts = json.dumps(
        {
            "facts": [
                {"id": "package:name", "evidence": [{"path": "pyproject.toml"}]},
                {
                    "id": "public_symbol:synthetic.hello",
                    "evidence": [{"path": "src/synthetic/__init__.py"}],
                },
            ]
        }
    ).encode()
    readme = scenarios.BASE_FILES["README.md"].encode()
    files = {"facts.json": facts, "README.md": readme}
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "repository": repository,
        "revision": revision,
        "state": "READY_FOR_PROPOSAL",
        "files": {
            n: {"sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)}
            for n, d in files.items()
        },
        "consumed_fact_ids": ["package:name", "public_symbol:synthetic.hello"],
    }
    if with_blobs:
        manifest["upstream_blobs"] = {
            p: _blob(scenarios.BASE_FILES[p]) for p in _CONSUMED
        }
    for name, data in files.items():
        (bundle / name).write_bytes(data)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")


def _world_fetch(world: fake_github.World) -> Callable[..., Any]:
    """A ``read_client`` ``fetch`` that answers from the synthetic world through ``fake_github.route``."""

    def fetch(url: str, token: str | None) -> httpx.Response:
        from urllib.parse import parse_qs, urlsplit

        split = urlsplit(url)
        status, payload, headers = fake_github.route(
            world, "GET", split.path, parse_qs(split.query), b""
        )
        return httpx.Response(status, json=payload, headers=headers)

    return fetch


def monitor_to_plan(work: Path) -> dict[str, Any]:
    """Each synthetic upstream through the real monitor, the drift contract and the sealing plan."""
    world_dir = work / "world"
    table = scenarios.build_world(world_dir)
    world = fake_github.World(world_dir)
    fetch = _world_fetch(world)
    read_head = functools.partial(
        read_client.fetch_default_branch_sha, fetch=fetch, sleep=lambda _: None
    )
    read_tree = functools.partial(
        read_client.fetch_tree, fetch=fetch, sleep=lambda _: None
    )

    def observe(root: Path, row: dict[str, Any]) -> RepositoryDrift:
        return observe_repository(
            root,
            _entry(row["repository"]),
            token=FAKE_TOKEN,
            read_head=read_head,
            read_tree=read_tree,
        )

    with_blobs = work / "control-blobs"
    for row in table:
        _seal(with_blobs, row["repository"], row["sealed_revision"], with_blobs=True)
    observed = {row["name"]: observe(with_blobs, row) for row in table}
    sealed_without = work / "control-legacy"
    for row in table:
        _seal(
            sealed_without, row["repository"], row["sealed_revision"], with_blobs=False
        )
    legacy = {
        row["name"]: observe(sealed_without, row)
        for row in table
        if row["name"]
        in ("relevant-change", "irrelevant-change", "force-pushed-history")
    }

    # A force-push whose old commit GitHub has since collected: a bundle sealed without recorded
    # blob ids can no longer read the sealed tree, so the question is undecidable.
    collected = work / "control-collected"
    forced = next(r for r in table if r["name"] == "force-pushed-history")
    _seal(collected, forced["repository"], "9" * 40, with_blobs=False)
    legacy["force-pushed-history (sealed commit collected)"] = observe(
        collected, forced
    )

    document = drift_document(
        list(observed.values()),
        observed_at=datetime.now(UTC).isoformat(timespec="seconds"),
        owner=scenarios.OWNER,
    )
    evidence = work / "drift-evidence"
    evidence.mkdir()
    (evidence / f"drift-{scenarios.OWNER}.json").write_text(
        json.dumps(document), encoding="utf-8"
    )
    expected = {scenarios.OWNER: frozenset(r["repository"] for r in table)}
    contract = assemble_drift_contract(
        evidence, expected=expected, now=datetime.now(UTC)
    )
    records = parse_drift_contract(contract.document)
    registry = _registry([_entry(r["repository"]) for r in table])
    plan = plan_sealing_run(records, registry, now=datetime.now(UTC))
    _dump(work, "monitor-drift-document", document)
    _dump(work, "monitor-contract", contract.document)
    _dump(
        work,
        "monitor-fake-requests",
        (world_dir / "requests.jsonl").read_text(encoding="utf-8")
        if (world_dir / "requests.jsonl").is_file()
        else "",
    )

    def view(drift: RepositoryDrift) -> dict[str, Any]:
        return {"status": drift.status, "change": drift.change, "detail": drift.detail}

    selected = {r.split("/", 1)[1] for r in plan.selected}
    observations = {
        "scenarios": {name: view(drift) for name, drift in observed.items()},
        "contract_status": {r.repository.split("/", 1)[1]: r.status for r in records},
        "sealing_plan_selected": sorted(selected),
        "sealing_plan_publishable": list(plan.publishable),
        "registry_mode": "dry_run (every fixture entry)",
        "legacy_bundle_without_recorded_blobs": {n: view(d) for n, d in legacy.items()},
        "provider_calls": 0,
    }
    readme_detail = observed["maintainer-readme-edit"].detail or ""
    checks = {
        "relevant selects": observed["relevant-change"].change == "RELEVANT_CHANGE"
        and "relevant-change" in selected,
        "irrelevant does not": observed["irrelevant-change"].change
        == "IRRELEVANT_CHANGE"
        and observed["irrelevant-change"].status == "CURRENT"
        and "irrelevant-change" not in selected,
        "unchanged is quiet": observed["unchanged"].change == "NO_CHANGE"
        and "unchanged" not in selected,
        "maintainer edit flagged on README": observed["maintainer-readme-edit"].change
        == "RELEVANT_CHANGE"
        and "README.md" in readme_detail
        and "maintainer-readme-edit" in selected,
        "force push is drift": observed["force-pushed-history"].change
        == "RELEVANT_CHANGE",
        "deleted is unreachable and never work": observed["deleted-repository"].status
        == "UNREACHABLE"
        and "deleted-repository" not in selected,
        "archived is not work": "archived-repository" not in selected,
        "dry_run never published": plan.publishable == (),
        "legacy force push with a readable sealed tree compares": legacy[
            "force-pushed-history"
        ].change
        == "RELEVANT_CHANGE",
        "legacy force push with a collected sealed commit fails closed": legacy[
            "force-pushed-history (sealed commit collected)"
        ].status
        == "UNKNOWN",
        "legacy relevant still detected": legacy["relevant-change"].change
        == "RELEVANT_CHANGE",
        "legacy irrelevant still quiet": legacy["irrelevant-change"].change
        == "IRRELEVANT_CHANGE",
    }
    return _result(
        "monitor-to-plan-relevance",
        "a synthetic upstream commit that touches a consumed path is selected exactly once; an "
        "irrelevant commit selects nothing; a maintainer README edit is flagged, not overwritten",
        _all(checks),
        observations,
        gap="An archived repository is unchanged by nature, so the monitor reports it CURRENT; no "
        "code reads the archived flag, so a stale README on an archived repository would reach the "
        "propose write and be refused only by GitHub itself.",
    )


# --- effects: propose, commit-back, issues -----------------------------------------------------

OLD_README = "# Target\n\nOriginal text.\n"
README_V1 = "# Target\n\nAn updated, verified README.\n"
README_V2 = "# Target\n\nA second, further updated README.\n"
SOURCE_1 = "1" * 40
SOURCE_2 = "2" * 40


def _permit(repository: str) -> WritePermit:
    return WritePermit(effect="readme_proposal", entry=_entry(repository, "full"))


def _rest(repository: str, *, readme: str | None = None) -> fake_rest.FakeGitHubRest:
    rest = fake_rest.FakeGitHubRest(
        app_id=EXPECTED_APP_ID, installation_scope=[repository]
    )
    rest.add_repository(repository, readme=readme)
    return rest


def propose_seams(rest: fake_rest.FakeGitHubRest, repository: str) -> dict[str, Any]:
    """The real ``core/github`` functions bound to the fake REST: what ``propose_candidate`` takes
    for every network call, so its gates, ordering and reconciliation run unchanged."""
    owner, name = repository.split("/")
    return {
        "verify_token": functools.partial(verify_installation_token, fetch=rest.fetch),
        "verify_pull_request_app": functools.partial(
            verify_pull_request_app, fetch=rest.fetch
        ),
        "get_ref": functools.partial(client.get_ref, fetch=rest.fetch),
        "create_ref": functools.partial(client.create_ref, write=rest.post),
        "get_contents": functools.partial(client.get_contents, fetch=rest.fetch),
        "put_contents": functools.partial(client.put_contents, write=rest.put),
        "find_pull_requests": functools.partial(
            client.find_pull_requests, fetch=rest.fetch
        ),
        "create_pull_request": functools.partial(
            client.create_pull_request, write=rest.post
        ),
        "update_pull_request": functools.partial(
            client.update_pull_request, write=rest.patch
        ),
        "reconcile_write": lambda: client.get_contents(
            owner,
            name,
            "README.md",
            ref=presenter_branch_name(),
            token=FAKE_TOKEN,
            fetch=rest.fetch,
        ),
    }


def _propose(
    rest: fake_rest.FakeGitHubRest,
    *,
    readme: str,
    source: str,
    head: str | None = None,
    title: str = "Update README",
) -> Any:
    now = datetime.now(UTC)
    stamp = "%Y-%m-%dT%H:%M:%SZ"
    body = f"A rehearsal pull request.\n\ncandidate_hash: {sha256_text(readme)}\n"
    return propose_candidate(
        repository=TARGET,
        readme_text=readme,
        source_revision=source,
        base_branch="main",
        token=FAKE_TOKEN,
        environment={AUTHORIZATION_VARIABLE: "1"},
        permit=_permit(TARGET),
        load_authorization=lambda: authorize_proposal(
            repository=TARGET,
            candidate_hash=sha256_text(readme),
            source_revision=source,
            base_branch="main",
            branch=presenter_branch_name(),
            approver="rehearsal-owner",
            issued_at=(now - timedelta(minutes=1)).strftime(stamp),
            expires_at=(now + timedelta(hours=1)).strftime(stamp),
        ),
        recheck_source=lambda: head or source,
        **propose_seams(rest, TARGET),
        pr_title=title,
        pr_body=body,
    )


def _summary(result: Any) -> dict[str, Any]:
    return {
        "effected": result.effected,
        "reason": result.reason,
        "reason_code": str(result.reason_code) if result.reason_code else None,
        "commit_written": result.commit_written,
        "pr_created": result.pr_created,
        "pr_updated": result.pr_updated,
        "pr_number": result.pr_number,
    }


def propose_idempotence(work: Path) -> dict[str, Any]:
    """Create one PR, make a second run create nothing, update in place on a new candidate, and
    never recreate a settled one."""
    rest = _rest(TARGET, readme=OLD_README)
    first = _propose(rest, readme=README_V1, source=SOURCE_1)
    first_title = rest.pulls(TARGET)[0]["title"]
    writes_after_first = len(rest.applied_writes())
    second = _propose(rest, readme=README_V1, source=SOURCE_1)
    writes_after_second = len(rest.applied_writes())
    third = _propose(
        rest, readme=README_V2, source=SOURCE_2, title="Update README again"
    )
    open_after_update = rest.pulls(TARGET, "open")
    rest.close_pull(TARGET, first.pr_number, merged=True)
    writes_before_settled = len(rest.applied_writes())
    settled = _propose(
        rest, readme=README_V2, source=SOURCE_2, title="Update README again"
    )
    _dump(
        work,
        "propose-idempotence-requests",
        {"requests": rest.requests, "writes": rest.writes},
    )
    observations = {
        "first_run": _summary(first),
        "applied_writes_after_first": writes_after_first,
        "second_run_unchanged": _summary(second),
        "applied_writes_added_by_second_run": writes_after_second - writes_after_first,
        "new_candidate_updates_in_place": _summary(third),
        "open_pull_requests_after_update": len(open_after_update),
        "base_branch_readme_untouched": rest.file(TARGET, "main", "README.md")
        == OLD_README,
        "presenter_branch_readme": rest.file(
            TARGET, presenter_branch_name(), "README.md"
        )
        == README_V2,
        "after_merge_same_candidate": _summary(settled),
        "writes_added_after_merge": len(rest.applied_writes()) - writes_before_settled,
    }
    checks = {
        "one PR with the given title": first.pr_created
        and first.effected
        and first_title == "Update README"
        and writes_after_first > 0,
        "second run creates nothing": writes_after_second == writes_after_first
        and not second.pr_created
        and not second.commit_written
        and second.effected,
        "update in place": third.pr_number == first.pr_number
        and third.pr_updated
        and len(open_after_update) == 1,
        "base branch never written": observations["base_branch_readme_untouched"]
        is True,
        "settled PR not recreated": not settled.effected
        and "merged" in (str(settled.reason_code or "") + settled.reason).lower()
        and observations["writes_added_after_merge"] == 0,
    }
    return _result(
        "propose-create-then-noop",
        "exactly one pull request on the fake remote; a second run creates nothing",
        _all(checks),
        observations,
    )


def propose_maintainer_edit(work: Path) -> dict[str, Any]:
    """The maintainer edits the README upstream after the candidate was sealed: the propose step
    refuses on the moved source and writes nothing, so the edit is never overwritten."""
    rest = _rest(TARGET, readme=OLD_README)
    owner, name = TARGET.split("/")
    current = client.get_contents(
        owner, name, "README.md", ref="main", token=FAKE_TOKEN, fetch=rest.fetch
    )
    assert current is not None
    edited = OLD_README + "\nA paragraph the maintainer added.\n"
    status, _ = rest.put(
        f"{fake_rest.API_ROOT}/repos/{TARGET}/contents/README.md",
        FAKE_TOKEN,
        {
            "message": "maintainer edit",
            "branch": "main",
            "sha": current.sha,
            "content": base64.b64encode(edited.encode()).decode(),
        },
    )
    writes_before = len(rest.applied_writes())
    refused = _propose(rest, readme=README_V1, source=SOURCE_1, head=SOURCE_2)
    _dump(
        work,
        "maintainer-edit-requests",
        {"requests": rest.requests, "writes": rest.writes},
    )
    observations = {
        "maintainer_edit_status": status,
        "propose_after_the_edit": _summary(refused),
        "writes_made_by_propose": len(rest.applied_writes()) - writes_before,
        "base_branch_readme_is_the_maintainers": rest.file(TARGET, "main", "README.md")
        == edited,
        "presenter_branch_exists": rest.branch(TARGET, presenter_branch_name())
        is not None,
        "pull_requests": len(rest.pulls(TARGET)),
    }
    checks = {
        "edit landed": status == 200,
        "refused as source moved": not refused.effected
        and "moved" in str(refused.reason_code).lower(),
        "no write": observations["writes_made_by_propose"] == 0,
        "edit intact": observations["base_branch_readme_is_the_maintainers"] is True,
        "nothing created": not observations["presenter_branch_exists"]
        and observations["pull_requests"] == 0,
    }
    return _result(
        "maintainer-edit-not-overwritten",
        "a maintainer edit to the README upstream is never overwritten",
        _all(checks),
        observations,
        gap="The propose gate stops the stale candidate; the reconciliation of the new README into "
        "a re-sealed candidate is the present pipeline's inherited-content path and is rehearsed "
        "only with the fake model transport (tests/test_workflow_rehearsal_cycle.py).",
    )


def lost_responses(work: Path) -> dict[str, Any]:
    """A write whose answer is lost is reconciled by reading, never retried blind; the next cycle
    never duplicates what landed."""
    owner, name = TARGET.split("/")
    branch = presenter_branch_name()
    cases: dict[str, Any] = {}

    # (a) the contents PUT lands, its answer is lost: reconciliation sees it, no second PUT.
    rest = _rest(TARGET, readme=OLD_README)
    rest.inject("PUT", r"/contents/README\.md$", "lose_response")
    result = _propose(rest, readme=README_V1, source=SOURCE_1)
    puts = [w for w in rest.writes if w["method"] == "PUT"]
    cases["put_landed_answer_lost"] = {
        **_summary(result),
        "put_requests": len(puts),
        "put_applied": sum(w["applied"] for w in puts),
        "pull_requests": len(rest.pulls(TARGET)),
    }

    # (b) the contents PUT never arrives: reconciliation sees the old content and retries once.
    rest = _rest(TARGET, readme=OLD_README)
    rest.inject("PUT", r"/contents/README\.md$", "drop")
    result = _propose(rest, readme=README_V1, source=SOURCE_1)
    puts = [w for w in rest.writes if w["method"] == "PUT"]
    cases["put_never_arrived"] = {
        **_summary(result),
        "put_requests_reaching_github": len(puts),
        "put_applied": sum(w["applied"] for w in puts),
        "branch_has_the_candidate": rest.file(TARGET, branch, "README.md") == README_V1,
    }

    # (c) the PR POST lands, its answer is lost: this run reports it; the next finds the PR.
    rest = _rest(TARGET, readme=OLD_README)
    rest.inject("POST", r"/pulls$", "lose_response")
    lost = _propose(rest, readme=README_V1, source=SOURCE_1)
    next_cycle = _propose(rest, readme=README_V1, source=SOURCE_1)
    cases["pr_created_answer_lost"] = {
        "cycle_1": _summary(lost),
        "cycle_2": _summary(next_cycle),
        "pull_requests_after_both": len(rest.pulls(TARGET)),
    }

    # (d) the branch POST lands, its answer is lost: the next run finds the branch.
    rest = _rest(TARGET, readme=OLD_README)
    rest.inject("POST", r"/git/refs$", "lose_response")
    lost = _propose(rest, readme=README_V1, source=SOURCE_1)
    next_cycle = _propose(rest, readme=README_V1, source=SOURCE_1)
    ref_posts = [w for w in rest.writes if w["path"].endswith("/git/refs")]
    cases["branch_created_answer_lost"] = {
        "cycle_1": _summary(lost),
        "cycle_2": _summary(next_cycle),
        "branch_create_requests": len(ref_posts),
        "branch_create_applied": sum(w["applied"] for w in ref_posts),
        "pull_requests": len(rest.pulls(TARGET)),
    }

    # (e) a rate-limit answer on the PR POST: nothing applied, the next cycle completes it once.
    rest = _rest(TARGET, readme=OLD_README)
    rest.inject("POST", r"/pulls$", "status", status=429, retry_after="60")
    limited = _propose(rest, readme=README_V1, source=SOURCE_1)
    next_cycle = _propose(rest, readme=README_V1, source=SOURCE_1)
    cases["rate_limited_pr_create"] = {
        "cycle_1": _summary(limited),
        "cycle_2": _summary(next_cycle),
        "pull_requests": len(rest.pulls(TARGET)),
    }

    # (f) an issue whose creation answer is lost: found by its fingerprint marker, not re-filed.
    rest = _rest(TARGET)
    marker = fingerprint_marker("rehearsal-defect-1")
    rest.inject("POST", r"/issues$", "lose_response")
    body = f"A reproducible defect.\n\n{marker}\n"
    error = ""
    try:
        client.create_issue(
            owner, name, title="A defect", body=body, token=FAKE_TOKEN, write=rest.post
        )
    except RepositoryMetadataError as exc:
        error = str(exc)
    found = client.find_issue_with_marker(
        owner, name, marker, token=FAKE_TOKEN, fetch=rest.fetch
    )
    cases["issue_created_answer_lost"] = {
        "create_error": error.split("(", 1)[0].strip(),
        "reconciled_by_marker": found is not None,
        "issues_on_the_target": len(rest.issues(TARGET)),
        "issue_posts_applied": sum(
            w["applied"] for w in rest.writes if w["path"].endswith("/issues")
        ),
    }
    _dump(work, "lost-response-cases", cases)

    a, b = cases["put_landed_answer_lost"], cases["put_never_arrived"]
    c, d, e = (
        cases["pr_created_answer_lost"],
        cases["branch_created_answer_lost"],
        cases["rate_limited_pr_create"],
    )
    f = cases["issue_created_answer_lost"]
    checks = {
        "a: landed write reconciled, not repeated": a["effected"]
        and a["put_requests"] == 1
        and a["put_applied"] == 1
        and a["pull_requests"] == 1,
        "b: lost write retried once after reconciliation": b["effected"]
        and b["put_applied"] == 1
        and b["branch_has_the_candidate"],
        "c: no duplicate PR": not c["cycle_1"]["effected"]
        and c["cycle_2"]["effected"]
        and c["pull_requests_after_both"] == 1
        and not c["cycle_2"]["pr_created"],
        "d: no duplicate branch": d["branch_create_applied"] == 1
        and d["cycle_2"]["effected"]
        and d["pull_requests"] == 1,
        "e: rate limit retried next cycle": not e["cycle_1"]["effected"]
        and e["cycle_2"]["effected"]
        and e["pull_requests"] == 1,
        "f: issue reconciled by marker": f["reconciled_by_marker"]
        and f["issues_on_the_target"] == 1
        and f["issue_posts_applied"] == 1,
    }
    return _result(
        "lost-response-reconciled",
        "a lost response on a write is reconciled (propose and issues transports)",
        _all(checks),
        cases,
        gap="Only the contents PUT is reconciled inside one run (reconcile_write). A lost branch, "
        "pull-request or issue-create answer fails that run with a GitHub error and is reconciled "
        "by the next run's reads, one schedule later; nothing duplicates, but the delay is a cycle.",
    )


class ControlRemote:
    """The control repository as the commit-back step sees it: a local bare ``origin``, a checkout
    of it, and the fake REST service that owns its pull requests. Pushes go to the bare remote
    (real git); the branch is then mirrored into the REST model, as GitHub does on a push."""

    def __init__(
        self,
        work: Path,
        repository: str,
        rest: fake_rest.FakeGitHubRest,
        *,
        target: str = TARGET,
    ) -> None:
        self.repository = repository
        self.target = target
        self.slug = target.replace("/", "__")
        self.rest = rest
        self.origin = _bare(work / "control-origin.git")
        seed = work / "control-seed"
        seed.mkdir()
        _git(["init", "-q", "-b", "main"], seed)
        (seed / "candidates" / self.slug).mkdir(parents=True)
        (seed / "candidates" / self.slug / "CURRENT").write_text(
            "0" * 40 + "\n", encoding="utf-8"
        )
        (seed / "README.md").write_text("control\n", encoding="utf-8")
        _git(["add", "-A"], seed)
        _git(["commit", "-q", "-m", "seed"], seed)
        _git(["push", "-q", str(self.origin), "main"], seed)
        self.root = work / "control-checkout"
        _git(["clone", "-q", str(self.origin), str(self.root)], work)
        self.main_before = _git(["rev-parse", "main"], self.origin)
        self.branch = publish_effect.branch_name(target)

    def publish(self, import_dir: Path, revision: str) -> Any:
        root, rest, slug = self.root, self.rest, self.slug

        def push(b: str) -> None:
            git_ops.push_branch(root, b, token=FAKE_TOKEN)
            rest.set_branch(self.repository, b, _git(["rev-parse", "HEAD"], root))

        owner_repo = self.repository
        return publish_effect.publish_candidates(
            repository=self.target,
            control_repository=owner_repo,
            revision=revision,
            base_branch="main",
            token=FAKE_TOKEN,
            environment={publish_effect.AUTHORIZATION_VARIABLE: "1"},
            pr_title=f"Update candidates/ for {self.target}",
            pr_body=f"Automated.\n\n- repository: {self.target}\nrevision: {revision}\n",
            bundle_paths=(f"candidates/{slug}",),
            current_path=f"candidates/{slug}/CURRENT",
            branch=self.branch,
            remote_branch_sha=lambda b: git_ops.remote_branch_sha(
                root, b, token=FAKE_TOKEN
            ),
            checkout=lambda b, start: git_ops.checkout_branch(
                root, b, start, token=FAKE_TOKEN
            ),
            read_committed=lambda p: git_ops.read_committed_file(root, p),
            overlay=lambda: git_ops.overlay_bundle(root, slug, import_dir),
            stage_and_commit=lambda paths, message: git_ops.stage_and_commit(
                root, paths, message
            ),
            push=push,
            verify_token=functools.partial(verify_installation_token, fetch=rest.fetch),
            verify_pull_request_app=functools.partial(
                verify_pull_request_app, fetch=rest.fetch
            ),
            find_pull_requests=functools.partial(
                client.find_pull_requests, fetch=rest.fetch
            ),
            create_pull_request=functools.partial(
                client.create_pull_request, write=rest.post
            ),
            update_pull_request=functools.partial(
                client.update_pull_request, write=rest.patch
            ),
        )


def _publish_view(r: Any) -> dict[str, Any]:
    return {
        "effected": r.effected,
        "commit_written": r.commit_written,
        "pr_created": r.pr_created,
        "pr_updated": r.pr_updated,
        "reason": r.reason,
        "pr_number": r.pr_number,
    }


def commit_back(work: Path) -> dict[str, Any]:
    """Publish a sealed candidate to the control repository on its own branch through a local bare
    remote: one PR, a second run commits nothing, a new revision updates the same PR."""
    rest = _rest(CONTROL, readme="control\n")
    control = ControlRemote(work, CONTROL, rest)
    origin, branch, slug = control.origin, control.branch, control.slug

    def bundle(revision: str) -> Path:
        directory = work / f"import-{revision[:6]}"
        (directory / revision).mkdir(parents=True, exist_ok=True)
        (directory / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
        (directory / revision / "manifest.json").write_text(
            json.dumps({"revision": revision, "state": "READY_FOR_PROPOSAL"}),
            encoding="utf-8",
        )
        return directory

    first = control.publish(bundle(SOURCE_1), SOURCE_1)
    tip_1 = _git(["rev-parse", branch], origin)
    second = control.publish(bundle(SOURCE_1), SOURCE_1)
    tip_2 = _git(["rev-parse", branch], origin)
    third = control.publish(bundle(SOURCE_2), SOURCE_2)
    tip_3 = _git(["rev-parse", branch], origin)
    current = _git(["show", f"{branch}:candidates/{slug}/CURRENT"], origin).strip()
    _dump(work, "commit-back-origin-history", _history(origin))
    _dump(
        work, "commit-back-requests", {"requests": rest.requests, "writes": rest.writes}
    )
    observations = {
        "first": _publish_view(first),
        "second_same_revision": _publish_view(second),
        "third_new_revision": _publish_view(third),
        "branch_commits_ahead_of_main": _count(origin, f"main..{branch}"),
        "branch_tip_unchanged_by_second_run": tip_1 == tip_2,
        "branch_tip_moved_by_third_run": tip_2 != tip_3,
        "default_branch_never_pushed": _git(["rev-parse", "main"], origin)
        == control.main_before,
        "open_pull_requests": len(rest.pulls(CONTROL, "open")),
        "current_on_the_branch": current == SOURCE_2,
    }
    checks = {
        "one PR, one commit": first.pr_created
        and first.commit_written
        and _count(origin, tip_1) - _count(origin, "main") == 1,
        "second run commits and opens nothing": second.effected
        and not second.commit_written
        and not second.pr_created
        and tip_1 == tip_2,
        "new revision updates the same PR": third.pr_updated
        and not third.pr_created
        and third.pr_number == first.pr_number
        and len(rest.pulls(CONTROL, "open")) == 1,
        "default branch never pushed": observations["default_branch_never_pushed"]
        is True,
        "branch carries the new revision": current == SOURCE_2,
    }
    return _result(
        "commit-back-create-then-noop",
        "publish-candidates against a local remote: one PR; a second run creates nothing",
        _all(checks),
        observations,
    )


# --- read-side rate limits ---------------------------------------------------------------------


def rate_limited_read(work: Path) -> dict[str, Any]:
    """The monitor's reads honour ``Retry-After`` within the policy's bounds and give up cleanly."""
    attempts = RETRY_POLICIES["github_api"].max_attempts
    waited: list[float] = []
    calls: list[str] = []

    def limited(url: str, token: str | None) -> httpx.Response:
        calls.append(url)
        if len(calls) <= 2:
            return httpx.Response(
                429, headers={"Retry-After": "7"}, json={"message": "slow down"}
            )
        if url.endswith("/repos/rehearsal-org/r"):
            return httpx.Response(200, json={"default_branch": "main"})
        return httpx.Response(200, json={"sha": "c" * 40})

    recovered = read_client.fetch_default_branch_sha(
        "rehearsal-org/r", token=FAKE_TOKEN, fetch=limited, sleep=waited.append
    )
    always: list[str] = []
    always_waited: list[float] = []

    def refused(url: str, token: str | None) -> httpx.Response:
        always.append(url)
        return httpx.Response(429, headers={"Retry-After": "7"}, json={})

    exhausted = read_client.fetch_default_branch_sha(
        "rehearsal-org/r", token=FAKE_TOKEN, fetch=refused, sleep=always_waited.append
    )
    observations = {
        "policy_max_attempts": attempts,
        "recovers_after_two_429": {
            "sha_read": recovered.sha is not None,
            "waits": waited,
        },
        "never_clears": {
            "requests": len(always),
            "waits": always_waited,
            "outcome": exhausted.error,
        },
    }
    checks = {
        "honours Retry-After": waited[:2] == [7.0, 7.0] and recovered.sha is not None,
        "bounded": len(always) == attempts
        and exhausted.sha is None
        and bool(exhausted.error),
    }
    return _result(
        "rate-limit-read",
        "a rate-limit response is honoured, bounded and retried next cycle",
        _all(checks),
        observations,
    )


# --- credentials -------------------------------------------------------------------------------


def credential_scan(work: Path, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Grep every output of the rehearsal for the fake credential and credential-shaped strings."""
    _dump(work, "scenario-results", evidence)  # the evidence itself is scanned too
    scanned = sorted(p for p in work.rglob("*") if p.is_file())
    hits = scan_for_secrets([work], [FAKE_TOKEN])
    return _result(
        "no-credential-in-any-output",
        "no credential appears in any log or artifact of the rehearsal",
        "PROVEN" if not hits and scanned else "FAILED",
        {
            "files_scanned": len(scanned),
            "hits": [Path(h).name for h in hits],
            "fake_token_was_used_for_every_write": True,
            "scanned": "request logs, git histories of every remote, child output, scenario results",
        },
    )


# --- driver ------------------------------------------------------------------------------------

SCENARIOS: tuple[Callable[[Path], dict[str, Any]], ...] = (
    stale_lease_fenced,
    kill_mid_transaction,
    pause_variable,
    run_cap_and_cooldown,
    monitor_to_plan,
    propose_idempotence,
    propose_maintainer_edit,
    lost_responses,
    commit_back,
    rate_limited_read,
)


def run_all(work: Path) -> dict[str, Any]:
    results = []
    for scenario in SCENARIOS:
        directory = work / scenario.__name__
        directory.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        result = scenario(directory)
        result["seconds"] = round(time.monotonic() - started, 1)
        results.append(result)
    results.append(credential_scan(work, results))
    return {
        "work_item": "TC-REF-11 (G7-W06)",
        "kind": "offline whole-cycle rehearsal: real code, local fakes, no model, no network",
        "scenarios": results,
        "verdicts": {r["scenario"]: r["verdict"] for r in results},
    }


def evidence_header() -> dict[str, Any]:
    """What every evidence file under the mission's evidence directory carries first (REPOSITORY_LAYOUT
    section 6): its authoritative plan, that it holds no execution authority, and what produced it."""
    try:
        revision: str | None = _git(["rev-parse", "HEAD"], REPO_ROOT)
    except (subprocess.CalledProcessError, OSError):
        revision = None
    return {
        "authoritative_plan": "plans/archive/reseal-and-refresh/PLAN.md",
        "execution_authority": False,
        "control_revision_at_run": revision,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "git": _git(["--version"], REPO_ROOT),
        },
        "redaction": "every credential in a rehearsal is the literal fake "
        "ghs_FAKEREHEARSAL...; no real credential exists in this process, and every output was "
        "scanned (scenario no-credential-in-any-output)",
    }


def record(name: str, document: dict[str, Any]) -> Path | None:
    """Write ``document`` as evidence when the run asked for it (``RP_REHEARSAL_EVIDENCE_DIR``)."""
    target = os.environ.get(EVIDENCE_ENV)
    if not target:
        return None
    path = Path(target) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {**evidence_header(), **document}
    path.write_text(
        json.dumps(document, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, help="write the evidence JSON into this directory"
    )
    parser.add_argument("--keep", type=Path, help="keep the scratch directory here")
    args = parser.parse_args(argv)
    scratch = args.keep or Path(tempfile.mkdtemp(prefix="rp-cycle-"))
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        document = run_all(scratch)
    finally:
        if args.keep is None:
            shutil.rmtree(scratch, ignore_errors=True)
    for scenario, verdict in document["verdicts"].items():
        print(f"{verdict:<16} {scenario}")
    if args.out:
        os.environ[EVIDENCE_ENV] = str(args.out)
        record("workflow-rehearsal-cycle-offline.json", document)
    return 0 if all(v != "FAILED" for v in document["verdicts"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
