"""The seal: a content-addressed bundle, exactly the consumed inputs, and the no-op proof."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from repository_presenter.components.readme.bundle.seal import (
    BundleLeakError,
    SealError,
    SealInputs,
    composition_ledger,
    dependencies_document,
    invalidate_bundle,
    invalidates,
    seal_candidate,
    seed_additional_calls,
    seed_call_store,
    verify_bundle,
)
from repository_presenter.core.candidates import (
    BundleError,
    BundleLedgerError,
    count_current_candidates,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.jobs import CallStore
from repository_presenter.core.llm.ledger import CallRecord
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.noop_proof import (
    Invocation,
    LedgerReconciliationError,
    NoOpProofError,
    ProcessIdentity,
)
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
REVISION = "c" * 40
PROMPTS = load_manifests(REPO_ROOT / "prompts")
FACTS = FactsDocument(
    ENTRY.repository,
    REVISION,
    (
        Fact("identity:repository", "identity", ENTRY.repository, (Evidence("x"),)),
        Fact("format:output.glb", "format", ".glb", (Evidence("x"),)),
    ),
)
SCHEMA = json.loads((REPO_ROOT / "schemas" / "candidate-bundle.schema.json").read_text("utf-8"))


def _validation(pending: bool = True) -> dict[str, Any]:
    eleven = {
        "id": "BC-11",
        "verdict": "PENDING" if pending else "PASS",
        "causal_stage": None,
        "details": ["judged at S12"],
    }
    return {
        "schema_version": 1,
        "validator_version": "1",
        "protected_content_fingerprint": "f" * 64,
        "checks": [{"id": "BC-01", "verdict": "PASS", "causal_stage": None, "details": []}, eleven],
        "advisory": [],
        "summary": {"pass": 1, "fail": 0, "pending": 1 if pending else 0},
    }


_SEQUENCE = iter(range(1, 10**9))


def _ledger_line(
    call_id: str,
    invocation_id: str | None,
    disposition: str,
    *,
    logical: str = "logical-a",
    outcome: str = "success",
    job: str = "repository_investigation",
    retained_reason: str | None = None,
    response: str = "s" * 64,
) -> str:
    return CallRecord(
        call_id=call_id,
        logical_call_id=logical,
        repository=ENTRY.repository,
        source_revision=REVISION,
        stage="INVESTIGATING",
        job=job,
        prompt_sha256="p" * 64,
        model_route="qwen3-next",
        model_served="qwen3-next",
        attempt=1 if disposition == "provider_call" else 0,
        disposition=disposition,  # type: ignore[arg-type]
        started_at="2026-10-05T00:00:00.000+00:00",
        finished_at="2026-10-05T00:00:01.000+00:00",
        latency_ms=1000,
        outcome=outcome,  # type: ignore[arg-type]
        http_status=200,
        request_sha256="r" * 64,
        response_sha256=response,
        provider_request_id=None,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        error_class=None,
        invocation_id=invocation_id,
        retained_reason=retained_reason,
    ).to_line()


def _invocation() -> Invocation:
    """A distinct synthetic process: what a fresh `present` run would have recorded."""
    n = next(_SEQUENCE)
    identity = ProcessIdentity(1000 + n, f"start-{n}", "boot-1", f"nonce-{n}")
    return Invocation(f"invocation-{n}", identity, "2026-10-05T00:00:00Z")


def _record_calls(transaction: Path, invocation: Invocation, provider_calls: int) -> None:
    """Append what the invocation's ledger would hold: its provider calls, or - when it made
    none - the cache reuse a real rerun records for each job it answers from stored output."""
    name = invocation.invocation_id
    lines = [
        _ledger_line(f"{name}-{index}", name, "provider_call") for index in range(provider_calls)
    ] or [_ledger_line(f"{name}-reuse", name, "cache_reuse")]
    with (transaction / "calls.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.writelines(f"{line}\n" for line in lines)


def _transaction(tmp_path: Path, readme: str = "# Doc\n", revision: str = REVISION) -> Path:
    transaction = tmp_path / "runs" / "transactions" / "owner__name" / revision
    transaction.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "README.md": readme,
        "README.patch": "--- a\n+++ b\n",
        "facts.json": '{"facts": []}\n',
        "investigation.json": "{}\n",
        "dispositions.json": '{"dispositions": []}\n',
        "plan.json": '{"sections": []}\n',
        "content_units.json": '{"units": []}\n',
        "validation.json": json.dumps(_validation(), indent=2, sort_keys=True) + "\n",
        "review.json": '{"verdict": "ACCEPT"}\n',
        "repairs.json": '{"attempts": {}}\n',
        "calls.jsonl": _ledger_line("base", None, "cache_reuse") + "\n",
    }
    for name, text in artifacts.items():
        (transaction / name).write_text(text, encoding="utf-8", newline="\n")
    return transaction


def _inputs(
    tmp_path: Path,
    provider_calls: int,
    secrets: tuple[ConfiguredSecret, ...] = (),
    stage: str | None = None,
    revision: str = REVISION,
    invocation: Invocation | None = None,
    dependencies: tuple[str, ...] = (),
) -> SealInputs:
    invocation = invocation or _invocation()
    transaction = tmp_path / "runs" / "transactions" / "owner__name" / revision
    _record_calls(transaction, invocation, provider_calls)
    return SealInputs(
        entry=ENTRY,
        source_revision=revision,
        tree_sha256="t" * 64,
        facts=FACTS,
        prompts=PROMPTS,
        validation=_validation(),
        transaction=transaction,
        candidates=tmp_path / "candidates",
        provider_calls=provider_calls,
        secrets=secrets,
        invocation=invocation,
        earliest_affected_stage=stage,
        changed_dependencies=dependencies,
    )


def test_the_sealed_canary_carries_the_receipt_its_example_facts_cite() -> None:
    """README_CONTRACT.md section 7: a bundle carries the artifacts its own facts cite.

    Measured 2026-09-05 (section 27.2 RC7): every one of the canary's twelve example facts
    named examples.json as the evidence for its outcome, and the bundle did not hold that
    file - the verification receipt lived only in the gitignored transaction, so a reader of
    the sealed candidate could not see why an example was SUPPORTED or UNRESOLVED.

    Deliberately reads the real, current canary bundle off disk, the same way
    tests/test_sealed_bytes.py does (CS-05, plans/healing/ci-staleness-followup.md,
    2026-09-09): this checks real, evolving content (which facts a real candidate's real
    examples currently cite), not a structural shape a frozen fixture could stand in for -
    freezing it would defeat the point of catching a real future regression.
    """
    bundle = (
        REPO_ROOT
        / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
        / "65b1f577c0f16d0d9112bb6c1153d3024543ac02"
    )
    facts = json.loads((bundle / "facts.json").read_text(encoding="utf-8"))
    receipts = {"examples.json"}
    cited = {
        evidence["path"]
        for fact in facts["facts"]
        for evidence in fact["evidence"]
        if evidence["path"] in receipts
    }
    # The canary's example facts do cite the receipt, so this test is measuring something.
    assert cited == {"examples.json"}
    for name in sorted(cited):
        assert (bundle / name).is_file(), name
    sealed = json.loads((bundle / "examples.json").read_text(encoding="utf-8"))
    ordinals = {int(receipt["ordinal"]) for receipt in sealed}
    examples = [f for f in facts["facts"] if f["kind"] == "example"]
    # One receipt per example fact, and each fact's polarity is the one its receipt supports.
    assert ordinals == {index for index in range(1, len(examples) + 1)}
    outcomes = {int(r["ordinal"]): r["outcome"] for r in sealed}
    supported = {"EXECUTED"}
    for index, fact in enumerate(sorted(examples, key=lambda f: f["id"]), start=1):
        expected = "SUPPORTED" if outcomes[index] in supported else fact["polarity"]
        assert fact["polarity"] == expected, fact["id"]


def test_the_sealed_ledger_keeps_every_attempt_and_marks_the_unconsumed_ones() -> None:
    """A transaction outlives its compositions, and the sealed ledger still shows all of it.

    Measured on the canary on 2026-09-05: the transaction carried 65 provider calls across four
    prompt versions where the composition it sealed consumed 28. Dropping the other 37 made a
    rejected or abandoned call vanish and left per-README totals unable to reconcile with the
    calls actually made; they are kept now, each marked with why it is not part of this
    composition, so the first-attempt measure (docs/RESEARCH_AND_GUIDELINES.md section 27.6
    control 1) filters on the mark instead of the bundle hiding the work.
    """
    lines = [
        '{"logical_call_id": "a", "attempt": 1, "outcome": "response_invalid"}',
        '{"logical_call_id": "a", "attempt": 2, "outcome": "success"}',
        '{"logical_call_id": "superseded", "attempt": 1, "outcome": "response_invalid"}',
        '{"logical_call_id": "b", "attempt": 1, "outcome": "success"}',
    ]
    raw = "".join(f"{line}\n" for line in lines).encode("utf-8")
    sealed = composition_ledger(raw, frozenset({"a", "b"})).decode("utf-8").splitlines()
    records = [json.loads(line) for line in sealed]
    # Nothing is dropped, in the order written; every attempt of a consumed call is as written.
    assert [record["logical_call_id"] for record in records] == ["a", "a", "superseded", "b"]
    assert sealed[0] == lines[0] and sealed[1] == lines[1] and sealed[3] == lines[3]
    # Only the call no artifact came from carries the audit-only mark, with its reason.
    assert [bool(record.get("retained_reason")) for record in records] == [
        False,
        False,
        True,
        False,
    ]
    assert "response_invalid" in records[2]["retained_reason"]
    assert composition_ledger(raw, frozenset({"a", "b"})).endswith(b"\n")
    # A run that consumed nothing has nothing to mark.
    assert composition_ledger(raw, frozenset()) == raw


def test_dependencies_name_exactly_the_consumed_inputs(tmp_path: Path) -> None:
    _transaction(tmp_path)
    document = dependencies_document(_inputs(tmp_path, 3))
    assert document["source"] == {"revision": REVISION, "tree_sha256": "t" * 64}
    assert list(document["facts"]) == ["format:output.glb", "identity:repository"]
    assert all(len(digest) == 64 for digest in document["facts"].values())
    assert document["prompts"]["independent_review"]["sha256"] == (
        PROMPTS["independent_review"].sha256
    )
    assert document["prompts"]["targeted_repair"]["version"] == "11"
    assert document["contract_version"] == "readme-contract-v1"
    assert document["components"] == {
        "shell": "6",
        "renderer": "30",
        "normalisation": "32",
        "reviewer_logic": "19",
    }
    assert document["validators"]["BC-01"] == "1" and len(document["validators"]) == 12
    assert document["acceptance_profile_version"] == "1"
    assert document["protected_content_fingerprint"] == "f" * 64
    assert len(document["policy"]["sha256"]) == 64 and document["policy"]["version"] == "1"


def test_call_variance_surfaces_non_determinism_and_is_absent_without_it(tmp_path: Path) -> None:
    """RC-05 (RESEARCH_AND_GUIDELINES.md 27.2 RC5/SW6): the Aspose.Email Python
    source_reconciliation diagnosis took over 30 minutes of manual calls.jsonl reading; a
    manifest field makes the same non-determinism visible from one manifest.json lookup.

    Grouped by job across the whole transaction, not by one logical_call_id: confirmed directly
    against that real candidate's own transaction ledger, where every one of the four distinct
    source_reconciliation responses the diagnosis found came from a *different* logical_call_id
    (a different repair-round packet each time) - restricting to one logical_call_id would have
    shown no variance for it at all.
    """
    transaction = _transaction(tmp_path)

    def line(call_id: str, logical: str, job: str, response: str, outcome: str = "success") -> str:
        return _ledger_line(
            call_id, None, "provider_call", logical=logical, job=job, outcome=outcome,
            response=response,
        )  # fmt: skip

    lines = [
        # a repair round (different logical_call_id) still counts toward the same job.
        line("v1", "a", "source_reconciliation", "1" * 64),
        line("v2", "b", "source_reconciliation", "2" * 64),
        # a different job: on its own, one successful attempt is not variance.
        line("v3", "c", "presentation_planning", "3" * 64),
        # rejected, so it never counts as a second successful response.
        line("v4", "c", "presentation_planning", "4" * 64, outcome="response_invalid"),
    ]
    (transaction / "calls.jsonl").write_text(
        "".join(f"{entry}\n" for entry in lines), encoding="utf-8", newline="\n"
    )
    sealed = seal_candidate(_inputs(tmp_path, provider_calls=0))
    manifest = json.loads((sealed.bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["call_variance"] == [
        {
            "job": "source_reconciliation",
            "distinct_responses": 2,
            "response_sha256s": ["1" * 64, "2" * 64],
        }
    ]

    # A no-op case - one successful attempt only - surfaces no such field at all.
    other_revision = "d" * 40
    other_transaction = _transaction(tmp_path, revision=other_revision)
    (other_transaction / "calls.jsonl").write_text(
        line("q1", "b", "presentation_planning", "5" * 64) + "\n", encoding="utf-8", newline="\n"
    )
    quiet = seal_candidate(_inputs(tmp_path, provider_calls=0, revision=other_revision))
    quiet_manifest = json.loads((quiet.bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(quiet_manifest)
    assert "call_variance" not in quiet_manifest


def test_the_first_seal_is_accepted_and_a_fresh_zero_call_replay_proves_the_no_op(
    tmp_path: Path,
) -> None:
    _transaction(tmp_path)
    first = seal_candidate(_inputs(tmp_path, provider_calls=7))
    bundle = tmp_path / "candidates" / "aspose-3d-foss__Aspose.3D-FOSS-for-Python" / REVISION
    assert first.bundle == bundle and first.state == "ACCEPTED" and first.changed
    assert first.proof is None and first.note.startswith("sealed;")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["provider_calls"] == 7 and manifest["no_op_proof"] is None
    assert set(manifest["files"]) == set(first.files) and "dependencies.json" in manifest["files"]
    for name, digest in manifest["files"].items():
        data = (bundle / name).read_bytes()
        assert digest == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    assert (bundle.parent / "CURRENT").read_text("utf-8") == f"{REVISION}\n"

    withheld = seal_candidate(_inputs(tmp_path, provider_calls=1))
    assert withheld.state == "ACCEPTED" and not withheld.changed
    assert "proof withheld" in withheld.note

    # An unproven seal that differs is simply replaced.
    _transaction(tmp_path, readme="# Draft\n")
    replaced = seal_candidate(_inputs(tmp_path, provider_calls=2))
    assert replaced.state == "ACCEPTED" and replaced.proof is None and replaced.changed
    assert replaced.note.startswith("re-sealed: README.md changed")
    _transaction(tmp_path)
    restored = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert restored.state == "ACCEPTED" and restored.note.startswith("re-sealed")

    proven = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert proven.state == "READY_FOR_PROPOSAL" and proven.changed
    assert proven.proof is not None and proven.proof["provider_calls"] == 0
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "READY_FOR_PROPOSAL" and manifest["provider_calls"] == 0
    judged = json.loads((bundle / "validation.json").read_text("utf-8"))
    assert judged["checks"][1]["verdict"] == "PASS"
    assert judged["summary"] == {"pass": 2, "fail": 0, "pending": 0}
    # The proof is measured, not asserted: both runs are named, the rerun's ledger counts are
    # recorded, and freshness is the comparison of the two recorded processes.
    proof = manifest["no_op_proof"]
    assert proof["fresh_process"] is True and proof["provider_calls"] == 0
    assert proof["first_run"]["identity"]["pid"] != proof["rerun"]["identity"]["pid"]
    assert proof["first_run"]["invocation_id"] != proof["rerun"]["invocation_id"]
    assert proof["rerun"]["provider_calls"] == 0 and proof["rerun"]["cache_reuses"] == 1
    assert manifest["sealed_by"]["invocation_id"] == proof["rerun"]["invocation_id"]
    sealed_lines = (bundle / "calls.jsonl").read_text("utf-8").splitlines()
    assert manifest["ledger_totals"]["records"] == len(sealed_lines)
    # The ledger was reset before the last two invocations: the base line and one reuse each.
    assert manifest["ledger_totals"]["provider_calls"] == 0
    assert manifest["ledger_totals"]["cache_reuses"] == 3

    before = (bundle / "manifest.json").read_bytes()
    again = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert again.state == "READY_FOR_PROPOSAL" and not again.changed
    assert again.note.startswith("no-op:")
    assert (bundle / "manifest.json").read_bytes() == before

    # A proven candidate stays valid: a differing run records an update and touches no file. An
    # authoring-prompt change is not a factual input, so the state is VALID_UPDATE_AVAILABLE and
    # the manifest names the scope that triggered it (docs/STATE_MACHINE.md section 9).
    _transaction(tmp_path, readme="# Changed\n")
    authoring = ("prompts.section_authoring",)
    updated = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="COMPOSING", dependencies=authoring)
    )
    assert updated.state == "VALID_UPDATE_AVAILABLE" and updated.proof is not None
    assert updated.changed
    assert updated.note.startswith("valid update available (authoring): README.md changed")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "VALID_UPDATE_AVAILABLE" and "invalidated" not in manifest
    assert manifest["update"]["classification"] == "presentation"
    assert manifest["update"]["triggering_scope"] == "authoring"
    assert manifest["update"]["scopes"] == ["authoring"]
    assert manifest["update"]["scope_basis"] == "inputs"
    assert manifest["update"]["changed"] == ["README.md"]
    assert manifest["update"]["earliest_affected_stage"] == "COMPOSING"
    assert (bundle / "README.md").read_text("utf-8") == "# Doc\n"
    assert manifest["update"]["files"]["README.md"] == hashlib.sha256(b"# Changed\n").hexdigest()
    withheld = seal_candidate(
        _inputs(tmp_path, provider_calls=1, stage="COMPOSING", dependencies=authoring)
    )
    assert not withheld.changed  # the same update is not recorded twice, nor adopted unproven
    assert (bundle / "README.md").read_text("utf-8") == "# Doc\n"
    # A fresh zero-call process reproducing the waiting update proves it; the bundle adopts it.
    adopted = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="COMPOSING", dependencies=authoring)
    )
    assert adopted.state == "READY_FOR_PROPOSAL" and adopted.changed
    assert adopted.note.startswith("update adopted (authoring): a fresh process reproduced")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert "update" not in manifest and manifest["adopted"]["changed"] == ["README.md"]
    assert manifest["adopted"]["triggering_scope"] == "authoring"
    assert manifest["adopted"]["previous_proof"]["provider_calls"] == 0
    assert manifest["no_op_proof"]["provider_calls"] == 0 and manifest["provider_calls"] == 0
    assert (bundle / "README.md").read_text("utf-8") == "# Changed\n"
    assert json.loads((bundle / "validation.json").read_text("utf-8"))["summary"]["pending"] == 0
    (tmp_path / "runs" / "transactions" / "owner__name" / REVISION / "facts.json").write_text(
        '{"facts": ["new"]}\n', encoding="utf-8", newline="\n"
    )
    facts = ("facts",)
    factual = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="EXTRACTING", dependencies=facts)
    )
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    assert factual.changed and manifest["update"]["classification"] == "factual"
    assert manifest["update"]["changed"] == ["facts.json"] and "adopted" in manifest
    # A changed factual input the candidate consumed invalidates it (docs/STATE_MACHINE.md section
    # 9); the manifest records the scope, and the update the re-entered pipeline produced waits.
    assert factual.state == "INVALIDATED"
    assert manifest["state"] == "INVALIDATED"
    assert manifest["invalidated"]["scope"] == "facts" and manifest["invalidated"]["check"] is None
    assert manifest["invalidated"]["causal_stage"] == "EXTRACTING"
    assert manifest["update"]["triggering_scope"] == "facts"
    assert factual.note.startswith("invalidated (facts): facts.json changed")
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert count_current_candidates(tmp_path) == 0  # no longer counts as current
    # A fresh zero-call process reproducing that exact update still proves and adopts it (the
    # Forbidden clause: the two-run, zero-provider-call discipline is preserved exactly even
    # once the state has moved off READY_FOR_PROPOSAL to INVALIDATED).
    resolved = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="EXTRACTING", dependencies=facts)
    )
    assert resolved.state == "READY_FOR_PROPOSAL" and resolved.changed
    assert resolved.note.startswith("update adopted (facts): a fresh process reproduced")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "READY_FOR_PROPOSAL" and "update" not in manifest
    assert "invalidated" not in manifest and manifest["adopted"]["triggering_scope"] == "facts"
    assert (bundle / "facts.json").read_text("utf-8") == '{"facts": ["new"]}\n'
    assert count_current_candidates(tmp_path) == 1  # counts again once adopted


def test_seed_call_store_reuses_the_three_one_to_one_stages_from_a_sealed_bundle(
    tmp_path: Path,
) -> None:
    """G5-W02 (27.2 RC4). runs/ is gitignored, so a hosted runner's first run of an
    already-sealed revision starts with nothing to reuse. investigation.json, dispositions.json,
    and plan.json are each one job's accepted output written verbatim (confirmed against
    write_investigation/write_dispositions/write_plan before relying on it), so calls.jsonl's own
    ``logical_call_id`` for that job's one successful attempt can be paired with the sealed
    artifact directly - never the record's own ``request_sha256`` field, which is
    ``canonical_hash(payload)`` for one physical attempt, distinct from
    ``core/llm/jobs.py::run_job``'s actual ``CallStore`` key
    (``canonical_hash({"prompt_sha256":..., "payload":...})``, carried as ``logical_call_id`` on
    every attempt precisely so a caller never recomputes it) - confirmed live, after this exact
    field mix-up shipped and silently seeded nothing anything ever looked up
    (``test_present_from_an_empty_runs_directory_reuses_a_sealed_bundle``, tests/test_cli.py). A
    job with two successful attempts (a repair reopened it) is left unseeded - only the last
    attempt's output matches the sealed artifact, and calls.jsonl alone cannot say which one that
    was."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "investigation.json").write_text('{"capabilities": []}\n', encoding="utf-8")
    (bundle / "dispositions.json").write_text('{"dispositions": []}\n', encoding="utf-8")
    (bundle / "plan.json").write_text('{"sections": []}\n', encoding="utf-8")

    def _record(job: str, logical_call_id: str, outcome: str = "success") -> str:
        return json.dumps(
            {
                "job": job,
                "outcome": outcome,
                "logical_call_id": logical_call_id,
                "request_sha256": f"attempt-payload-hash-{logical_call_id}",
                "model_served": "qwen3-next-2026",
            }
        )

    (bundle / "calls.jsonl").write_text(
        "\n".join(
            [
                _record("repository_investigation", "a" * 64),
                _record("source_reconciliation", "b" * 64),
                _record("presentation_planning", "c" * 64),
                _record("presentation_planning", "d" * 64),  # a repair round re-asked it
                _record("source_reconciliation", "e" * 64, outcome="response_invalid"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    store = CallStore(tmp_path / "runs" / "calls")
    seeded = seed_call_store(bundle, store)
    assert seeded == ["repository_investigation", "source_reconciliation"]
    assert store.get("a" * 64) == {"capabilities": []}
    assert store.get("b" * 64) == {"dispositions": []}
    # presentation_planning had two successful attempts (a repair round), so neither is seeded -
    # calls.jsonl alone cannot say which one produced the sealed plan.json.
    assert store.get("c" * 64) is None and store.get("d" * 64) is None
    assert store.record("a" * 64)["model_served"] == "qwen3-next-2026"

    empty = seed_call_store(tmp_path / "nonexistent", CallStore(tmp_path / "runs" / "calls2"))
    assert empty == []


def test_seed_additional_calls_reuses_whatever_raw_calls_json_names_by_its_own_hash(
    tmp_path: Path,
) -> None:
    """G5-W02's own remaining gap (27.2 RC4): seed_call_store's _SEEDABLE_JOBS only ever reaches
    the three 1:1 jobs (repository_investigation/source_reconciliation/presentation_planning);
    coherence, independent_review's reads, and a batch section_authoring task need
    composition/authoring.py::write_raw_calls's own raw_calls.json instead - keyed directly by
    each call's own request_sha256, so a match needs no separate lineage check (write_raw_calls's
    own docstring explains why: the key itself only matches a later run's freshly computed
    request hash when the request that produced it is byte-identical). raw_calls.json never
    carries model_served (write_raw_calls's own docstring explains why: run_job hardcodes it to
    None on its own cache-reuse path, so sealing the originally-served model name here would make
    a seeded rerun's own raw_calls.json differ from the one the original, live call wrote - the
    exact defect a hosted CI run of this item's own canary caught live, before this fix)."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "raw_calls.json").write_text(
        json.dumps(
            {
                "f" * 64: {"job": "section_authoring", "output": {"units": []}},
                "g" * 64: {
                    "job": "independent_review",
                    "output": {"verdict": "ACCEPT", "findings": []},
                },
                # A malformed entry (not an object) is skipped, never raises - the same
                # fail-safe-not-fail-closed shape seed_call_store's own malformed-line handling
                # already has for calls.jsonl.
                "h" * 64: "not a mapping",
            }
        ),
        encoding="utf-8",
    )
    store = CallStore(tmp_path / "runs" / "calls")
    seeded = seed_additional_calls(bundle, store)
    assert seeded == ["independent_review", "section_authoring"]
    assert store.get("f" * 64) == {"units": []}
    assert store.get("g" * 64) == {"verdict": "ACCEPT", "findings": []}
    assert store.get("h" * 64) is None
    assert store.record("f" * 64)["model_served"] is None

    # An entry already present in the store (from seed_call_store, or an earlier call here) is
    # left alone, never overwritten - "seeded" only ever reports what this call actually wrote.
    again = seed_additional_calls(bundle, store)
    assert again == []

    empty = seed_additional_calls(tmp_path / "nonexistent", CallStore(tmp_path / "runs" / "calls2"))
    assert empty == []


def test_a_newer_proven_revision_supersedes_the_older_one(tmp_path: Path) -> None:
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=3))
    older = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert older.state == "READY_FOR_PROPOSAL"
    newer_revision = "d" * 40
    _transaction(tmp_path, readme="# Newer\n", revision=newer_revision)
    seal_candidate(_inputs(tmp_path, provider_calls=5, revision=newer_revision))
    manifest = json.loads((older.bundle / "manifest.json").read_text("utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL"  # an unproven newer seal supersedes nothing
    newer = seal_candidate(_inputs(tmp_path, provider_calls=0, revision=newer_revision))
    assert newer.state == "READY_FOR_PROPOSAL"
    manifest = json.loads((older.bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "SUPERSEDED" and manifest["superseded_by"] == newer_revision
    assert manifest["no_op_proof"] is not None  # history stays in place
    assert (older.bundle.parent / "CURRENT").read_text("utf-8") == f"{newer_revision}\n"


def test_a_corrupt_bundle_fails_closed_and_a_factual_failure_invalidates(tmp_path: Path) -> None:
    _transaction(tmp_path)
    sealed = seal_candidate(_inputs(tmp_path, provider_calls=0))
    bundle = sealed.bundle
    assert verify_bundle(bundle) is not None
    assert verify_bundle(tmp_path / "nowhere") is None
    (bundle / "plan.json").write_text('{"sections": ["x"]}\n', encoding="utf-8", newline="\n")
    with pytest.raises(BundleError, match=r"bundle artifact plan\.json is corrupt in c{40}"):
        verify_bundle(bundle)
    with pytest.raises(BundleError, match=r"plan\.json is corrupt"):
        seal_candidate(_inputs(tmp_path, provider_calls=0))
    (bundle / "plan.json").unlink()
    with pytest.raises(BundleError, match=r"bundle artifact plan\.json is missing"):
        verify_bundle(bundle)

    transaction = _transaction(tmp_path)
    with pytest.raises(BundleError, match=r"plan\.json is missing"):
        seal_candidate(_inputs(tmp_path, provider_calls=0))  # a bundle never self-heals
    (bundle / "plan.json").write_bytes((transaction / "plan.json").read_bytes())
    assert verify_bundle(bundle) is not None
    failing = {
        "id": "BC-02",
        "verdict": "FAIL",
        "causal_stage": "EXTRACTING",
        "details": ["install_command:pip is CONTRADICTED: package registry: not found"],
    }
    assert invalidates(failing)
    assert not invalidates({"id": "BC-07", "verdict": "FAIL", "details": ["h1"]})
    # The reviewer's verdict decides from its own field; the detail string is prose the record
    # shows a reader, never a control plane (RESEARCH_AND_GUIDELINES.md section 27.2 RC8).
    factual = {"id": "BC-10", "verdict": "FAIL", "review_verdict": "REJECT_FACTUAL"}
    assert invalidates(factual)
    assert not invalidates({**factual, "review_verdict": "REJECT_PRESENTATION"})
    assert not invalidates(
        {"id": "BC-10", "verdict": "FAIL", "details": ["REJECT_FACTUAL"]}
    )  # no field, no invalidation
    manifest = invalidate_bundle(bundle, failing)
    assert manifest is not None and manifest["state"] == "INVALIDATED"
    stored = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(stored)
    assert stored["invalidated"]["check"] == "BC-02"
    assert stored["invalidated"]["causal_stage"] == "EXTRACTING"
    assert invalidate_bundle(tmp_path / "nowhere", failing) is None


def test_a_missing_artifact_or_a_leaked_secret_fails_the_seal_closed(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path, readme="# Doc with sk-live-secret-value\n")
    secret = ConfiguredSecret("GPT_OSS_API_KEY", b"sk-live-secret-value")
    bundle = tmp_path / "candidates" / "aspose-3d-foss__Aspose.3D-FOSS-for-Python" / REVISION
    with pytest.raises(BundleLeakError, match=r"GPT_OSS_API_KEY in README\.md"):
        seal_candidate(_inputs(tmp_path, provider_calls=0, secrets=(secret,)))
    # TB-06 (external review D6, 2026-09-08): a leak must leave no trace on disk, not merely
    # raise after the files and CURRENT pointer were already published - there was never a
    # prior bundle here (this is a first seal), so nothing at all should exist now.
    assert not bundle.is_dir()
    assert not (bundle.parent / "CURRENT").exists()
    assert list(bundle.parent.iterdir()) == []  # no orphaned staging directory either
    (transaction / "review.json").unlink()
    with pytest.raises(SealError, match=r"no review\.json"):
        seal_candidate(_inputs(tmp_path, provider_calls=0))


def test_a_publish_failure_partway_through_leaves_no_partial_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TB-06 (external review D6, 2026-09-08): staged to a temp directory and promoted only
    after the secret scan passes, so a crash partway through never leaves CURRENT pointing at a
    partially-written bundle, and never corrupts a pre-existing proven one."""
    _transaction(tmp_path)
    first = seal_candidate(_inputs(tmp_path, provider_calls=0))
    bundle = first.bundle
    before_files = {p.name: p.read_bytes() for p in bundle.iterdir()}
    before_current = (bundle.parent / "CURRENT").read_bytes()

    _transaction(tmp_path, readme="# Draft\n")
    original_write_bytes = Path.write_bytes

    def _flaky_write_bytes(self: Path, data: bytes) -> int:
        if self.name == "dependencies.json":
            raise OSError("simulated crash mid-publish")
        return original_write_bytes(self, data)

    monkeypatch.setattr(Path, "write_bytes", _flaky_write_bytes)
    with pytest.raises(OSError, match="simulated crash mid-publish"):
        seal_candidate(_inputs(tmp_path, provider_calls=2))
    monkeypatch.undo()

    assert {p.name: p.read_bytes() for p in bundle.iterdir()} == before_files
    assert (bundle.parent / "CURRENT").read_bytes() == before_current
    assert [p for p in bundle.parent.iterdir() if p.name.startswith(".")] == []


# --- models_used: a sealed bundle records the models it was produced with ------------------

PRIMARY = "qwen3-next"


def _manifest_path(tmp_path: Path) -> Path:
    return (
        tmp_path
        / "candidates"
        / "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
        / REVISION
        / "manifest.json"
    )


def _sealed_manifest(tmp_path: Path) -> dict[str, Any]:
    manifest = json.loads(_manifest_path(tmp_path).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    return manifest


def _with_models(tmp_path: Path, provider_calls: int, models: dict[str, str] | None) -> SealInputs:
    return replace(_inputs(tmp_path, provider_calls=provider_calls), models_used=models)


def _proven_bundle(tmp_path: Path) -> None:
    """A transaction sealed at ACCEPTED, then reproduced by a zero-call process: READY."""
    _transaction(tmp_path)
    assert seal_candidate(_inputs(tmp_path, provider_calls=7)).state == "ACCEPTED"
    assert seal_candidate(_inputs(tmp_path, provider_calls=0)).state == "READY_FOR_PROPOSAL"


def test_the_seal_records_the_models_it_was_produced_with(tmp_path: Path) -> None:
    _transaction(tmp_path)
    seal_candidate(_with_models(tmp_path, 7, {PRIMARY: "gpt-oss"}))
    assert _sealed_manifest(tmp_path)["models_used"] == {PRIMARY: "gpt-oss"}


def test_a_changed_model_reopens_valid_update_available_and_names_the_change(
    tmp_path: Path,
) -> None:
    _proven_bundle(tmp_path)
    readme = _manifest_path(tmp_path).parent / "README.md"
    before = readme.read_bytes()

    result = seal_candidate(_with_models(tmp_path, 2, {PRIMARY: "gpt-oss"}))

    # A model-route change is a prompt-class change (docs/DECISION_LOG.md 2026-09-06 07:45): the
    # sealed candidate stays valid with an update available, scoped by the prompts the route
    # answers - never a factual input, so never an invalidation. No sealed byte is replaced.
    assert result.state == "VALID_UPDATE_AVAILABLE" and result.changed
    manifest = _sealed_manifest(tmp_path)
    assert manifest["state"] == "VALID_UPDATE_AVAILABLE" and "invalidated" not in manifest
    assert manifest["update"]["classification"] == "presentation"
    assert manifest["update"]["triggering_scope"] == "evidence"
    assert "facts" not in manifest["update"]["scopes"]
    assert manifest["update"]["changed"] == ["models[qwen3-next]: qwen3-next -> gpt-oss"]
    assert manifest["update"]["models_used"] == {PRIMARY: "gpt-oss"}
    assert manifest["models_used"] == {PRIMARY: PRIMARY}  # the sealed content keeps its model
    assert readme.read_bytes() == before


def test_a_rerun_on_the_sealed_model_stays_a_zero_call_no_op(tmp_path: Path) -> None:
    """Negative control: an unchanged model is not an update, so the proof is not disturbed."""
    _proven_bundle(tmp_path)
    again = seal_candidate(_with_models(tmp_path, 0, {PRIMARY: PRIMARY}))
    assert again.state == "READY_FOR_PROPOSAL" and not again.changed
    assert again.note.startswith("no-op:")
    assert "update" not in _sealed_manifest(tmp_path)


def test_a_fresh_zero_call_run_on_the_waiting_model_adopts_the_update(tmp_path: Path) -> None:
    _proven_bundle(tmp_path)
    seal_candidate(_with_models(tmp_path, 2, {PRIMARY: "gpt-oss"}))

    adopted = seal_candidate(_with_models(tmp_path, 0, {PRIMARY: "gpt-oss"}))

    assert adopted.state == "READY_FOR_PROPOSAL" and adopted.changed
    assert adopted.note.startswith("update adopted (evidence)")
    manifest = _sealed_manifest(tmp_path)
    assert manifest["models_used"] == {PRIMARY: "gpt-oss"}
    assert manifest["adopted"]["previous_models_used"] == {PRIMARY: PRIMARY}
    assert "update" not in manifest and manifest["no_op_proof"]["provider_calls"] == 0


def test_a_run_on_a_different_model_than_the_waiting_update_is_not_adopted(
    tmp_path: Path,
) -> None:
    """Negative control: adoption is only for the exact update a fresh process reproduced."""
    _proven_bundle(tmp_path)
    seal_candidate(_with_models(tmp_path, 2, {PRIMARY: "gpt-oss"}))

    other = seal_candidate(_with_models(tmp_path, 0, {PRIMARY: "recommended"}))

    assert other.state == "VALID_UPDATE_AVAILABLE" and other.changed
    manifest = _sealed_manifest(tmp_path)
    assert manifest["update"]["models_used"] == {PRIMARY: "recommended"}
    assert "adopted" not in manifest and manifest["models_used"] == {PRIMARY: PRIMARY}


def test_a_bundle_sealed_before_models_were_recorded_reads_its_routes_as_their_own_names(
    tmp_path: Path,
) -> None:
    """Every route answered as itself before fallback chains; that is what such a bundle says."""
    _proven_bundle(tmp_path)
    manifest = _sealed_manifest(tmp_path)
    del manifest["models_used"]
    _manifest_path(tmp_path).write_text(json.dumps(manifest), encoding="utf-8")

    unchanged = seal_candidate(_with_models(tmp_path, 0, {PRIMARY: PRIMARY}))
    assert unchanged.state == "READY_FOR_PROPOSAL" and not unchanged.changed

    changed = seal_candidate(_with_models(tmp_path, 2, {PRIMARY: "gpt-oss"}))
    assert changed.state == "VALID_UPDATE_AVAILABLE"
    assert _sealed_manifest(tmp_path)["update"]["changed"] == [
        "models[qwen3-next]: qwen3-next -> gpt-oss"
    ]


# --- the no-op proof is measured (core/noop_proof.py) -------------------------------------------


def _bundle_of(tmp_path: Path) -> Path:
    return tmp_path / "candidates" / "aspose-3d-foss__Aspose.3D-FOSS-for-Python" / REVISION


def _manifest(tmp_path: Path) -> dict[str, Any]:
    return json.loads((_bundle_of(tmp_path) / "manifest.json").read_text("utf-8"))


def test_a_rerun_in_the_sealing_process_cannot_prove_the_no_op(tmp_path: Path) -> None:
    """fresh_process used to be a literal; it is the comparison of two recorded processes."""
    _transaction(tmp_path)
    first = _invocation()
    seal_candidate(_inputs(tmp_path, provider_calls=2, invocation=first))
    # A different invocation id (a second call to present) in the same operating-system process.
    again = Invocation("a-second-call", first.identity, "2026-10-05T00:00:00Z")
    withheld = seal_candidate(_inputs(tmp_path, provider_calls=0, invocation=again))
    assert withheld.state == "ACCEPTED" and withheld.proof is None and not withheld.changed
    assert "not a fresh one" in withheld.note
    assert _manifest(tmp_path)["no_op_proof"] is None
    # The same interpreter under a new pid still shares its in-memory nonce.
    cloned = Invocation(
        "a-third-call",
        ProcessIdentity(9999, "later", first.identity.boot_id, first.identity.nonce),
        "2026-10-05T00:00:00Z",
    )
    assert not seal_candidate(_inputs(tmp_path, provider_calls=0, invocation=cloned)).proof
    # A genuinely different process proves it.
    assert seal_candidate(_inputs(tmp_path, provider_calls=0)).state == "READY_FOR_PROPOSAL"


def test_a_bundle_sealed_before_processes_were_identified_is_sealed_again_not_proven(
    tmp_path: Path,
) -> None:
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=2))
    manifest = _manifest(tmp_path)
    del manifest["sealed_by"], manifest["ledger_totals"]  # as a bundle sealed before them reads
    (_bundle_of(tmp_path) / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    sealed_again = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert sealed_again.state == "ACCEPTED" and sealed_again.proof is None and sealed_again.changed
    assert "recorded no sealing process" in sealed_again.note
    assert "sealed_by" in _manifest(tmp_path)
    # Now there is a process to differ from.
    assert seal_candidate(_inputs(tmp_path, provider_calls=0)).state == "READY_FOR_PROPOSAL"


def test_the_seal_counts_provider_calls_from_the_ledger_not_from_the_caller(
    tmp_path: Path,
) -> None:
    _transaction(tmp_path)
    inputs = _inputs(tmp_path, provider_calls=3)
    # The caller says zero; the ledger on disk holds three for this invocation.
    with pytest.raises(LedgerReconciliationError, match="holds 3"):
        seal_candidate(replace(inputs, provider_calls=0))
    assert not _bundle_of(tmp_path).exists()


def test_a_seal_with_no_record_of_its_invocation_in_the_ledger_stops(tmp_path: Path) -> None:
    _transaction(tmp_path)
    inputs = _inputs(tmp_path, provider_calls=0)
    with pytest.raises(NoOpProofError) as caught:
        seal_candidate(replace(inputs, invocation=_invocation()))
    assert caught.value.reason == "LEDGER_NO_RECORDS"
    (inputs.transaction / "calls.jsonl").write_text("not a ledger\n", encoding="utf-8")
    with pytest.raises(NoOpProofError) as unreadable:
        seal_candidate(inputs)
    assert unreadable.value.reason == "LEDGER_UNREADABLE"


def test_the_sealed_ledger_retains_unconsumed_attempts_with_their_reason(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    inputs = _inputs(tmp_path, provider_calls=0)
    name = inputs.invocation.invocation_id
    with (transaction / "calls.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(
            _ledger_line(
                "abandoned", name, "provider_call", logical="old", outcome="response_invalid"
            )
            + "\n"
        )
    # The caller's own count must follow the ledger, so account for the abandoned attempt too.
    inputs = replace(inputs, provider_calls=1, consumed_calls=frozenset({"logical-a"}))
    seal_candidate(inputs)
    bundle = _bundle_of(tmp_path)
    sealed = [json.loads(line) for line in (bundle / "calls.jsonl").read_text("utf-8").splitlines()]
    kept = {record["call_id"]: record.get("retained_reason") for record in sealed}
    assert "abandoned" in kept and "response_invalid" in str(kept["abandoned"])
    assert kept["base"] is None  # a consumed call is written as it was
    manifest = _manifest(tmp_path)
    assert manifest["ledger_totals"]["audit_only"] == 1
    assert manifest["ledger_totals"]["provider_calls"] == 1 and manifest["provider_calls"] == 1
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    verify_bundle(bundle)  # the retained line reconciles


def test_replay_seeding_ignores_audit_only_lines(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "investigation.json").write_text('{"capabilities": []}\n', encoding="utf-8")
    consumed = _ledger_line("c1", None, "provider_call", logical="a" * 64)
    abandoned = _ledger_line(
        "c2",
        None,
        "provider_call",
        logical="b" * 64,
        retained_reason="unconsumed by the sealed composition (outcome success)",
    )
    (bundle / "calls.jsonl").write_text(f"{consumed}\n{abandoned}\n", encoding="utf-8")
    store = CallStore(tmp_path / "runs" / "calls")
    # Without the mark the job would have two successes and seed nothing; with it, one.
    assert seed_call_store(bundle, store) == ["repository_investigation"]
    assert store.get("a" * 64) == {"capabilities": []} and store.get("b" * 64) is None


@pytest.mark.parametrize(
    "tamper",
    [
        lambda m: m["ledger_totals"].__setitem__("provider_calls", 99),
        lambda m: m["ledger_totals"].__setitem__("records", 0),
        lambda m: m["ledger_totals"].__setitem__("total_tokens", 1),
        lambda m: m.__setitem__("provider_calls", 41),
    ],
    ids=["provider_calls", "records", "total_tokens", "manifest_provider_calls"],
)
def test_a_bundle_whose_totals_disagree_with_its_ledger_is_a_blocking_failure(
    tmp_path: Path, tamper: Any
) -> None:
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=2))
    bundle = _bundle_of(tmp_path)
    assert verify_bundle(bundle) is not None  # sound as sealed
    manifest = _manifest(tmp_path)
    tamper(manifest)
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleLedgerError) as caught:
        verify_bundle(bundle)
    assert caught.value.reason == "LEDGER_TOTALS_MISMATCH"
    # Every path that fails closed on a corrupt bundle fails closed on this: the seal itself.
    with pytest.raises(BundleLedgerError):
        seal_candidate(_inputs(tmp_path, provider_calls=0))


def test_a_proof_whose_rerun_made_calls_fails_verification(tmp_path: Path) -> None:
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=2))
    seal_candidate(_inputs(tmp_path, provider_calls=0))
    bundle = _bundle_of(tmp_path)
    manifest = _manifest(tmp_path)
    assert manifest["state"] == "READY_FOR_PROPOSAL" and verify_bundle(bundle) is not None
    # Re-point the proof at the invocation that made the calls: the ledger contradicts it.
    manifest["no_op_proof"]["rerun"]["invocation_id"] = manifest["no_op_proof"]["first_run"][
        "invocation_id"
    ]
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleLedgerError, match="claims zero provider calls"):
        verify_bundle(bundle)


def test_a_bundle_sealed_before_totals_were_recorded_still_verifies(tmp_path: Path) -> None:
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=2))
    bundle = _bundle_of(tmp_path)
    manifest = _manifest(tmp_path)
    del manifest["ledger_totals"], manifest["sealed_by"]
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_bundle(bundle) is not None  # it waits for its pending update; it is not judged


def test_an_existing_proven_bundle_records_a_pending_update_and_keeps_its_proof(
    tmp_path: Path,
) -> None:
    """The validator moved (BC-11 version 2): a proven bundle sealed under 1 stays READY with its
    proof and records a presentation update, which the next fresh process adopts."""
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=2))
    seal_candidate(_inputs(tmp_path, provider_calls=0))
    bundle = _bundle_of(tmp_path)
    manifest = _manifest(tmp_path)
    proof = manifest["no_op_proof"]
    # Make it read as sealed by the old code: no identities, no totals, old validator record.
    del manifest["sealed_by"], manifest["ledger_totals"]
    manifest["no_op_proof"] = {
        key: proof[key]
        for key in ("proven_at", "fresh_process", "byte_identical", "provider_calls")
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    old_validation = json.loads((bundle / "validation.json").read_text("utf-8"))
    for check in old_validation["checks"]:
        if check["id"] == "BC-11":
            check["version"] = "1"
    (bundle / "validation.json").write_text(json.dumps(old_validation), encoding="utf-8")
    manifest = _manifest(tmp_path)
    manifest["files"]["validation.json"] = {
        "sha256": hashlib.sha256((bundle / "validation.json").read_bytes()).hexdigest(),
        "bytes": len((bundle / "validation.json").read_bytes()),
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    updated = seal_candidate(_inputs(tmp_path, provider_calls=0))
    # A validator-version change is a non-invalidating scope: the proven candidate stays valid
    # and its update waits as VALID_UPDATE_AVAILABLE (invalidation.py), which the next fresh
    # process adopts.
    assert updated.state == "VALID_UPDATE_AVAILABLE" and updated.changed
    assert updated.note.startswith("valid update available (validator)")
    after = _manifest(tmp_path)
    assert after["no_op_proof"] == manifest["no_op_proof"]  # the proof is retained as it was
    assert after["update"]["recorded_by"]["invocation_id"]
    adopted = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert adopted.note.startswith("update adopted")
    final = _manifest(tmp_path)
    assert final["adopted"]["previous_proof"] == manifest["no_op_proof"]
    assert final["no_op_proof"]["first_run"] and final["ledger_totals"]


# --- typed invalidation scopes: each scope lands in the state the scope table defines ------------


def _bundle_dir(tmp_path: Path) -> Path:
    return _manifest_path(tmp_path).parent


def _alter(tmp_path: Path, name: str, text: str) -> None:
    transaction = tmp_path / "runs" / "transactions" / "owner__name" / REVISION
    (transaction / name).write_text(text, encoding="utf-8", newline="\n")


def _sealed_files(tmp_path: Path) -> dict[str, bytes]:
    return {
        p.name: p.read_bytes() for p in _bundle_dir(tmp_path).iterdir() if p.name != "manifest.json"
    }


def _changed_validation() -> str:
    changed = _validation()
    changed["checks"][0]["details"] = ["a newer check noted something"]
    return json.dumps(changed, indent=2, sort_keys=True) + "\n"


# scope -> (a consumed input class that changed, the artifact its stage rewrites, new bytes)
SCOPE_CASES: dict[str, tuple[str, str, str]] = {
    "facts": ("facts", "facts.json", '{"facts": ["new"]}\n'),
    "evidence": ("prompts.repository_investigation", "investigation.json", '{"new": 1}\n'),
    "reconciliation": ("prompts.source_reconciliation", "dispositions.json", '{"new": 1}\n'),
    "presentation": ("components.renderer", "README.md", "# Re-rendered\n"),
    "planning": ("prompts.presentation_planning", "plan.json", '{"sections": ["new"]}\n'),
    "authoring": ("prompts.section_authoring", "content_units.json", '{"units": ["new"]}\n'),
    "validator": ("validators", "validation.json", _changed_validation()),
    "reviewer": ("prompts.independent_review", "review.json", '{"verdict": "ACCEPT", "n": 2}\n'),
}


def test_every_scope_has_a_case() -> None:
    from repository_presenter.components.readme.bundle.invalidation import SCOPES

    assert set(SCOPE_CASES) == {scope.name for scope in SCOPES}


@pytest.mark.parametrize("scope_name", sorted(SCOPE_CASES))
def test_a_changed_input_lands_in_the_state_its_scope_defines(
    tmp_path: Path, scope_name: str
) -> None:
    from repository_presenter.components.readme.bundle.invalidation import (
        SCOPE_BY_NAME,
        reopening_stage,
    )

    dependency, artifact, text = SCOPE_CASES[scope_name]
    scope = SCOPE_BY_NAME[scope_name]
    _proven_bundle(tmp_path)
    sealed = _sealed_files(tmp_path)
    _alter(tmp_path, artifact, text)
    stage = reopening_stage(dependency)

    result = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage=stage, dependencies=(dependency,))
    )

    manifest = _sealed_manifest(tmp_path)
    assert result.state == scope.state == manifest["state"]
    assert manifest["update"]["triggering_scope"] == scope_name
    assert manifest["update"]["scopes"] == [scope_name]
    assert manifest["update"]["scope_basis"] == "inputs"
    assert manifest["update"]["earliest_affected_stage"] == stage
    if scope.state == "INVALIDATED":
        assert scope_name == "facts"  # the one scope that is itself a factual input
        assert manifest["invalidated"]["scope"] == scope_name
        assert manifest["invalidated"]["causal_stage"] == stage
        assert manifest["update"]["classification"] == "factual"
        assert result.note.startswith(f"invalidated ({scope_name}):")
    else:
        assert "invalidated" not in manifest
        assert manifest["update"]["classification"] == "presentation"
        assert result.note.startswith(f"valid update available ({scope_name}):")
    # The sealed bytes are never modified by recording an update, whatever the scope.
    assert _sealed_files(tmp_path) == sealed


@pytest.mark.parametrize("dependency", ["validators", "contract_version"])
def test_a_validator_change_never_invalidates(tmp_path: Path, dependency: str) -> None:
    """Negative control (AGENTS.md): a validator change re-checks and may yield
    VALID_UPDATE_AVAILABLE, never invalidation."""
    _proven_bundle(tmp_path)
    _alter(tmp_path, "validation.json", _changed_validation())

    result = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="VALIDATING", dependencies=(dependency,))
    )

    assert result.state == "VALID_UPDATE_AVAILABLE"
    assert "invalidated" not in _sealed_manifest(tmp_path)


@pytest.mark.parametrize("dependency", ["prompts.independent_review", "acceptance_profile_version"])
def test_a_reviewer_change_never_invalidates(tmp_path: Path, dependency: str) -> None:
    _proven_bundle(tmp_path)
    _alter(tmp_path, "review.json", '{"verdict": "ACCEPT", "n": 2}\n')
    result = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="REVIEWING", dependencies=(dependency,))
    )
    assert result.state == "VALID_UPDATE_AVAILABLE"
    assert "invalidated" not in _sealed_manifest(tmp_path)


def test_a_facts_change_alongside_other_scopes_invalidates_and_names_facts(
    tmp_path: Path,
) -> None:
    _proven_bundle(tmp_path)
    _alter(tmp_path, "facts.json", '{"facts": ["new"]}\n')
    _alter(tmp_path, "README.md", "# Re-rendered\n")

    result = seal_candidate(
        _inputs(
            tmp_path,
            provider_calls=0,
            stage="EXTRACTING",
            dependencies=("validators", "facts", "components.renderer"),
        )
    )

    manifest = _sealed_manifest(tmp_path)
    assert result.state == "INVALIDATED"
    assert manifest["update"]["triggering_scope"] == "facts"
    assert manifest["update"]["scopes"] == ["facts", "presentation", "validator"]


def test_an_unrelated_component_change_affects_nothing(tmp_path: Path) -> None:
    """Negative control: a component the candidate did not consume changed in the running code,
    so no consumed input moved and the rerun reproduces every sealed byte: no update, no state
    change, and the manifest is not even rewritten."""
    _proven_bundle(tmp_path)
    before = _manifest_path(tmp_path).read_bytes()

    result = seal_candidate(_inputs(tmp_path, provider_calls=0, dependencies=()))

    assert result.state == "READY_FOR_PROPOSAL" and not result.changed
    assert result.note.startswith("no-op:")
    assert _manifest_path(tmp_path).read_bytes() == before


def test_drift_with_no_changed_input_is_scoped_by_the_artifact_that_moved(
    tmp_path: Path,
) -> None:
    _proven_bundle(tmp_path)
    _alter(tmp_path, "plan.json", '{"sections": ["drift"]}\n')

    result = seal_candidate(_inputs(tmp_path, provider_calls=0, dependencies=()))

    manifest = _sealed_manifest(tmp_path)
    assert result.state == "VALID_UPDATE_AVAILABLE"
    assert manifest["update"]["triggering_scope"] == "planning"
    assert manifest["update"]["scope_basis"] == "artifacts"


def test_a_dependency_no_scope_covers_fails_the_seal_closed(tmp_path: Path) -> None:
    """Negative control: an input class with no row in the scope table never guesses a state."""
    _proven_bundle(tmp_path)
    _alter(tmp_path, "README.md", "# Changed\n")
    with pytest.raises(SealError, match="no invalidation scope for the dependency 'surprise'"):
        seal_candidate(_inputs(tmp_path, provider_calls=0, dependencies=("surprise",)))
    assert _sealed_manifest(tmp_path)["state"] == "READY_FOR_PROPOSAL"


def test_a_bundle_invalidated_by_a_failing_check_is_resealed_not_adopted(tmp_path: Path) -> None:
    """Negative control: only an INVALIDATED bundle that carries a waiting update adopts it; one a
    failing check invalidated holds no update and re-enters through a fresh seal as before."""
    _proven_bundle(tmp_path)
    failing = {"id": "BC-02", "verdict": "FAIL", "causal_stage": "EXTRACTING", "details": ["x"]}
    invalidate_bundle(_bundle_dir(tmp_path), failing)
    _alter(tmp_path, "README.md", "# Re-composed\n")

    result = seal_candidate(_inputs(tmp_path, provider_calls=0, dependencies=("facts",)))

    assert result.state == "ACCEPTED" and result.proof is None
    assert result.note.startswith("re-sealed:")
    assert "invalidated" not in _sealed_manifest(tmp_path)


def test_a_waiting_invalidation_is_replaced_when_a_different_update_arrives(
    tmp_path: Path,
) -> None:
    _proven_bundle(tmp_path)
    _alter(tmp_path, "facts.json", '{"facts": ["a"]}\n')
    seal_candidate(_inputs(tmp_path, provider_calls=0, stage="EXTRACTING", dependencies=("facts",)))
    first = _sealed_manifest(tmp_path)["update"]["files"]["facts.json"]

    _alter(tmp_path, "facts.json", '{"facts": ["b"]}\n')
    other = seal_candidate(
        _inputs(tmp_path, provider_calls=0, stage="EXTRACTING", dependencies=("facts",))
    )

    manifest = _sealed_manifest(tmp_path)
    assert other.state == "INVALIDATED" and other.changed and "adopted" not in manifest
    assert manifest["update"]["files"]["facts.json"] != first
