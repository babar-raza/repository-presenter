"""The no-op proof is measured: a rerun is a different process, and its own ledger counts its calls.

Every test here is a negative control for one way the proof used to pass softly - a nonzero rerun
count behind a zero exit code, a missing ledger, one process claiming both invocations, a
manifest total that no longer matches its ledger (core/noop_proof.py).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, main
from repository_presenter.core import noop_proof
from repository_presenter.core.llm.ledger import CallRecord, Ledger
from repository_presenter.core.noop_proof import (
    INVOCATION_RECORD_INVALID,
    INVOCATION_RECORD_MISSING,
    LEDGER_MISSING,
    LEDGER_NO_RECORDS,
    LEDGER_TOTALS_MISMATCH,
    LEDGER_UNREADABLE,
    NONZERO_PROVIDER_CALLS,
    RERUN_FAILED,
    SAME_PROCESS,
    Invocation,
    LedgerReconciliationError,
    NoOpProofError,
    ProcessIdentity,
    ledger_totals,
    measure_invocation,
    reconcile_ledger,
    require_distinct_processes,
    verify_noop_pair,
)
from support import write_cursor

# The real reading, captured at import: the autouse fixture in conftest.py replaces the module
# attribute with a per-call distinct identity for every test, and these tests need the genuine one.
REAL_IDENTITY = noop_proof.current_process_identity
LEDGER = "runs/transactions/owner__name/rev/calls.jsonl"


def record(
    call_id: str, invocation_id: str | None, disposition: str, tokens: int | None = 15
) -> CallRecord:
    return CallRecord(
        call_id=call_id,
        logical_call_id=f"logical-{call_id}",
        repository="owner/name",
        source_revision="a" * 40,
        stage="INVESTIGATING",
        job="repository_investigation",
        prompt_sha256="p" * 64,
        model_route="qwen3-next",
        model_served="qwen3-next",
        attempt=1 if disposition == "provider_call" else 0,
        disposition=disposition,  # type: ignore[arg-type]
        started_at="2026-10-05T00:00:00.000+00:00",
        finished_at="2026-10-05T00:00:01.000+00:00",
        latency_ms=10,
        outcome="success" if disposition == "provider_call" else "cache_reuse",
        http_status=200,
        request_sha256="r" * 64,
        response_sha256="s" * 64,
        provider_request_id=None,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=tokens,
        error_class=None,
        invocation_id=invocation_id,
    )


def identity(n: int, *, nonce: str | None = None, pid: int | None = None) -> ProcessIdentity:
    return ProcessIdentity(pid or 100 + n, f"start-{n}", "boot-1", nonce or f"nonce-{n}")


def invocation_document(
    invocation_id: str,
    who: ProcessIdentity,
    ledger: str | None = LEDGER,
    exit_code: int | None = 0,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "invocation_id": invocation_id,
        "identity": who.to_dict(),
        "started_at": "2026-10-05T00:00:00Z",
        "finished_at": "2026-10-05T00:00:09Z",
        "exit_code": exit_code,
        "repository": "owner/name",
        "ledger": ledger,
    }


class Rerun:
    """A project root with a first-run record, a second-run record, and the ledger they share."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.first = root / "first.json"
        self.second = root / "second.json"
        self.ledger = root / LEDGER
        self.ledger.parent.mkdir(parents=True)

    def write(
        self,
        *,
        first: ProcessIdentity | None = None,
        second: ProcessIdentity | None = None,
        second_ledger: str | None = LEDGER,
        second_exit: int | None = 0,
        second_id: str = "second",
    ) -> None:
        (self.first).write_text(
            json.dumps(invocation_document("first", first or identity(1))), encoding="utf-8"
        )
        (self.second).write_text(
            json.dumps(
                invocation_document(second_id, second or identity(2), second_ledger, second_exit)
            ),
            encoding="utf-8",
        )

    def ledger_of(self, *records: CallRecord) -> None:
        self.ledger.write_text(
            "".join(f"{item.to_line()}\n" for item in records), encoding="utf-8", newline="\n"
        )


@pytest.fixture
def rerun(tmp_path: Path) -> Rerun:
    return Rerun(tmp_path)


def reason(call: Any) -> str:
    with pytest.raises(NoOpProofError) as caught:
        call()
    return caught.value.reason


# --- process identity ---------------------------------------------------------------------------


def test_identity_is_read_from_the_operating_system_and_is_stable_within_a_process() -> None:
    first, again = REAL_IDENTITY(), REAL_IDENTITY()
    assert first.pid > 0 and first.started and first.boot_id and first.nonce
    assert first == again and first.key == again.key
    # Never a placeholder: the reading is not a constant a caller could have written down.
    assert first.started not in {"unknown", "0", "n/a"}


def test_two_real_processes_have_distinct_identities_that_share_a_boot() -> None:
    code = (
        "import json;from repository_presenter.core import noop_proof as n;"
        "print(json.dumps(n.current_process_identity().to_dict()))"
    )
    outputs = [
        json.loads(
            subprocess.run(
                [sys.executable, "-c", code], check=True, capture_output=True, text=True
            ).stdout
        )
        for _ in range(2)
    ]
    first, second = (ProcessIdentity.from_dict(item) for item in outputs)
    require_distinct_processes(first, second)  # does not raise
    assert first.key != second.key and first.nonce != second.nonce
    assert first.boot_id == second.boot_id  # one machine, one boot: the marker is boot-unique
    assert first.key != REAL_IDENTITY().key and first.nonce != REAL_IDENTITY().nonce


def test_one_process_claiming_both_invocations_is_refused() -> None:
    mine = REAL_IDENTITY()
    assert reason(lambda: require_distinct_processes(mine, REAL_IDENTITY())) == SAME_PROCESS
    # The same operating-system process under a doctored nonce is still one process.
    doctored = ProcessIdentity(mine.pid, mine.started, mine.boot_id, "another-nonce")
    assert reason(lambda: require_distinct_processes(mine, doctored)) == SAME_PROCESS
    # The same interpreter memory under a doctored pid is still one process.
    cloned = ProcessIdentity(mine.pid + 1, "later", mine.boot_id, mine.nonce)
    assert reason(lambda: require_distinct_processes(mine, cloned)) == SAME_PROCESS


def test_an_unreadable_identity_is_an_error_and_never_a_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> tuple[str, str]:
        raise OSError("no such file")

    monkeypatch.setattr(noop_proof, "_platform_identity", broken)
    assert reason(REAL_IDENTITY) == noop_proof.PROCESS_IDENTITY_UNAVAILABLE


def test_a_malformed_identity_in_a_record_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    document = invocation_document("x", identity(1))
    document["identity"]["pid"] = "7"  # not an integer
    path.write_text(json.dumps(document), encoding="utf-8")
    assert reason(lambda: noop_proof.read_invocation_record(path)) == INVOCATION_RECORD_INVALID


# --- the rerun gate -----------------------------------------------------------------------------


def test_a_rerun_that_reused_everything_in_another_process_verifies(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger_of(
        record("a", "first", "provider_call"),
        record("b", "first", "provider_call"),
        record("c", "second", "cache_reuse"),
        record("d", "second", "cache_reuse"),
    )
    verified = verify_noop_pair(rerun.first, rerun.second, rerun.root)
    assert verified.measurement.provider_calls == 0
    assert verified.measurement.records == 2 and verified.measurement.cache_reuses == 2


def test_a_nonzero_rerun_count_fails_whatever_the_exit_code_says(rerun: Rerun) -> None:
    """The defect: the hosted step checked the second invocation's exit code only, and a rerun
    that made calls exits 0 like one that made none."""
    rerun.write(second_exit=0)
    rerun.ledger_of(
        record("a", "first", "provider_call"),
        record("b", "second", "cache_reuse"),
        record("c", "second", "provider_call"),
    )
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        NONZERO_PROVIDER_CALLS
    )


def test_only_the_reruns_own_calls_count_not_the_first_runs(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger_of(
        *(record(f"first-{n}", "first", "provider_call") for n in range(30)),
        record("reuse", "second", "cache_reuse"),
    )
    assert verify_noop_pair(rerun.first, rerun.second, rerun.root).measurement.provider_calls == 0


def test_a_missing_ledger_fails_with_a_typed_reason(rerun: Rerun) -> None:
    rerun.write()  # the record names a ledger that was never written
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_MISSING
    )


def test_an_invocation_that_never_opened_a_ledger_fails(rerun: Rerun) -> None:
    rerun.write(second_ledger=None)
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_MISSING
    )


def test_an_invocation_with_no_ledger_records_proves_nothing(rerun: Rerun) -> None:
    """Zero calls is also what a process that died before its first job made."""
    rerun.write()
    rerun.ledger_of(record("a", "first", "provider_call"))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_NO_RECORDS
    )


def test_a_corrupt_ledger_fails_closed(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger.write_text('{"call_id": "only-this"}\n', encoding="utf-8")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_UNREADABLE
    )


def test_a_missing_invocation_record_fails(rerun: Rerun) -> None:
    rerun.write()
    rerun.second.unlink()
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        INVOCATION_RECORD_MISSING
    )


def test_two_invocations_claiming_one_process_fail(rerun: Rerun) -> None:
    rerun.ledger_of(record("a", "second", "cache_reuse"))
    rerun.write(first=identity(1), second=identity(1))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS
    # One interpreter under two pids: the shared in-memory nonce gives it away.
    rerun.write(first=identity(1, nonce="shared"), second=identity(2, nonce="shared"))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS
    # One invocation recorded twice is not a rerun.
    rerun.write(second_id="first")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS


def test_a_rerun_that_itself_failed_is_not_a_proof(rerun: Rerun) -> None:
    rerun.write(second_exit=1)
    rerun.ledger_of(record("a", "second", "cache_reuse"))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == RERUN_FAILED


def test_a_ledger_path_that_leaves_the_project_is_refused(rerun: Rerun) -> None:
    rerun.write(second_ledger="../outside/calls.jsonl")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        INVOCATION_RECORD_INVALID
    )


# --- stamping and measuring ---------------------------------------------------------------------


def test_the_ledger_stamps_every_record_with_its_invocation(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "calls.jsonl", invocation_id="inv-1")
    ledger.append(record("a", None, "provider_call"))
    ledger.append(record("b", None, "cache_reuse"))
    measured = measure_invocation(tmp_path / "calls.jsonl", "inv-1")
    assert (measured.records, measured.provider_calls, measured.cache_reuses) == (2, 1, 1)
    assert reason(lambda: measure_invocation(tmp_path / "calls.jsonl", "inv-2")) == (
        LEDGER_NO_RECORDS
    )


def test_an_invocation_records_its_own_process_and_ledger(tmp_path: Path) -> None:
    started = Invocation.begin()
    started.attach_ledger("owner/name", tmp_path / "runs" / "t" / "calls.jsonl")
    out = tmp_path / "rec" / "first.json"
    started.write(out, tmp_path, 0)
    loaded = noop_proof.read_invocation_record(out)
    assert loaded.invocation_id == started.invocation_id
    assert loaded.identity == started.identity and loaded.exit_code == 0
    assert loaded.ledger == "runs/t/calls.jsonl"
    # An invocation that never reached its ledger records none.
    bare = Invocation.begin()
    bare.write(out, tmp_path, 1)
    assert noop_proof.read_invocation_record(out).ledger is None


# --- reconciling totals -------------------------------------------------------------------------


def sealed_ledger(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    records = [
        record("a", "first", "provider_call", tokens=20),
        record("b", "first", "provider_call", tokens=30),
        record("c", "second", "cache_reuse"),
    ]
    path = tmp_path / "calls.jsonl"
    path.write_text("".join(f"{item.to_line()}\n" for item in records), encoding="utf-8")
    manifest = {
        "provider_calls": 2,
        "sealed_by": {"invocation_id": "first"},
        "ledger_totals": ledger_totals(records),
    }
    return path, manifest


def test_totals_are_the_sums_over_the_ledger(tmp_path: Path) -> None:
    path, manifest = sealed_ledger(tmp_path)
    assert manifest["ledger_totals"] == {
        "records": 3,
        "provider_calls": 2,
        "cache_reuses": 1,
        "audit_only": 0,
        "total_tokens": 50,
    }
    reconcile_ledger(manifest, path)  # does not raise


def test_an_unknown_token_count_is_not_summed_into_a_partial_total() -> None:
    totals = ledger_totals([record("a", "x", "provider_call", tokens=None)])
    assert totals["total_tokens"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [("records", 4), ("provider_calls", 3), ("cache_reuses", 0), ("total_tokens", 51)],
)
def test_a_tampered_total_is_a_typed_blocking_failure(
    tmp_path: Path, field: str, value: int
) -> None:
    path, manifest = sealed_ledger(tmp_path)
    manifest["ledger_totals"][field] = value
    with pytest.raises(LedgerReconciliationError) as caught:
        reconcile_ledger(manifest, path)
    assert caught.value.reason == LEDGER_TOTALS_MISMATCH and field in str(caught.value)


def test_a_manifest_provider_count_that_the_ledger_does_not_hold_fails(tmp_path: Path) -> None:
    path, manifest = sealed_ledger(tmp_path)
    manifest["provider_calls"] = 0
    with pytest.raises(LedgerReconciliationError, match="sealing invocation"):
        reconcile_ledger(manifest, path)


def test_a_proof_claiming_zero_calls_for_a_rerun_that_made_some_fails(tmp_path: Path) -> None:
    path, manifest = sealed_ledger(tmp_path)
    manifest["no_op_proof"] = {"provider_calls": 0, "rerun": {"invocation_id": "first"}}
    with pytest.raises(LedgerReconciliationError, match="claims zero provider calls"):
        reconcile_ledger(manifest, path)


def test_a_manifest_sealed_before_totals_were_recorded_is_not_judged_by_them(
    tmp_path: Path,
) -> None:
    path, manifest = sealed_ledger(tmp_path)
    del manifest["ledger_totals"]
    reconcile_ledger(manifest, path)  # does not raise: it waits for its pending update instead


# --- the CLI gate -------------------------------------------------------------------------------


def test_the_verify_command_exits_with_the_typed_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_cursor(tmp_path)
    rerun = Rerun(tmp_path)
    rerun.write()
    argv = [
        "verify-noop-proof",
        "--first",
        str(rerun.first),
        "--second",
        str(rerun.second),
        "--root",
        str(tmp_path),
    ]
    assert main(argv) == EXIT_INCONSISTENT
    assert f"no-op proof failed [{LEDGER_MISSING}]" in capsys.readouterr().err

    rerun.ledger_of(record("a", "second", "provider_call"))
    assert main(argv) == EXIT_INCONSISTENT
    assert f"[{NONZERO_PROVIDER_CALLS}]" in capsys.readouterr().err

    rerun.ledger_of(record("a", "second", "cache_reuse"))
    assert main(argv) == EXIT_OK
    assert "no-op proof verified" in capsys.readouterr().out


def test_the_hosted_workflow_gates_its_rerun_on_the_measured_proof() -> None:
    """The rerun step may not go back to trusting the second invocation's exit code."""
    text = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "present.yml"
    ).read_text(encoding="utf-8")
    second = text.index("}}-noop-proof")
    gate = text.index("repository-presenter verify-noop-proof")
    assert gate > second, "the gate must run after the second invocation"
    assert text.count('  --invocation-record "') == 2
    assert "first.json" in text and "second.json" in text
    assert "exit 1" in text[gate:]  # a failed gate fails the step


def test_a_placeholder_repository_has_no_candidate_and_so_nothing_to_prove(rerun: Rerun) -> None:
    """NON_PROCESSABLE: both runs end in a disposition, make no ledger, and exit 0."""
    rerun.write(second_ledger=None)
    for path in (rerun.first, rerun.second):
        document = json.loads(path.read_text(encoding="utf-8"))
        document["ledger"], document["disposition"] = None, "insufficient_evidence.json"
        path.write_text(json.dumps(document), encoding="utf-8")
    verified = verify_noop_pair(rerun.first, rerun.second, rerun.root)
    assert verified.measurement is None and verified.second.disposition
    # Still two processes: the exemption is from counting a ledger, not from being a rerun.
    both = json.loads(rerun.second.read_text(encoding="utf-8"))
    both["identity"] = json.loads(rerun.first.read_text(encoding="utf-8"))["identity"]
    rerun.second.write_text(json.dumps(both), encoding="utf-8")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS


def test_a_rerun_whose_outcome_class_differs_from_the_first_runs_fails(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger_of(record("a", "second", "cache_reuse"))
    document = json.loads(rerun.second.read_text(encoding="utf-8"))
    document["disposition"] = "insufficient_evidence.json"
    rerun.second.write_text(json.dumps(document), encoding="utf-8")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        noop_proof.DISPOSITION_MISMATCH
    )
