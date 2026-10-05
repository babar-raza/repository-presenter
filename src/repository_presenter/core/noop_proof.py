"""The no-op proof, measured: which process ran, what its ledger says, and whether it adds up.

AGENTS.md asks that an unchanged rerun be *proven* a zero-provider-call no-op in a fresh process.
Three things used to make that proof soft, and each is replaced here by something measured:

* the hosted rerun checked only the second invocation's exit code, which is 0 whether the rerun
  made no calls or fifty. The count now comes from the run's own call ledger
  (``measure_invocation``), counting the ``provider_call`` records stamped with that invocation's
  id, and a missing ledger, an invocation that recorded nothing, or a nonzero count each fail with
  a typed reason (``verify_noop_pair``);
* ``fresh_process`` was a literal ``True`` in the proof record. It is now what
  ``require_distinct_processes`` finds: every invocation records its process id, its process start
  time, a boot-unique marker, and a nonce minted when the interpreter imported this module (state
  shared in memory would share the nonce), and two invocations that agree on any of those are one
  process, not two;
* nothing reconciled a bundle's recorded totals against its ledger. ``ledger_totals`` is the one
  place the sums are taken and ``reconcile_ledger`` the one place they are compared, so a manifest
  whose totals disagree with the ``calls.jsonl`` it seals is a typed, blocking failure.

Process identity uses the standard library on purpose: the two reads needed (process start time,
boot marker) are a few lines per platform, ``psutil`` is not a dependency of this project, and
adding a compiled, hash-pinned package to ``requirements-lock.txt`` for two reads is the heavier
mechanism (docs/RESEARCH_AND_GUIDELINES.md section 18: a departure from the first choice names the
alternative). A platform whose identity cannot be read fails closed rather than recording a
placeholder, because a placeholder is exactly the literal this module removes.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repository_presenter.core.errors import PresenterError
from repository_presenter.core.llm.ledger import CallRecord, load_records

RECORD_SCHEMA_VERSION = 1

# The typed reasons. A caller (the workflow, a test, a reader of a failure line) routes on these;
# none is ever recovered by parsing the prose that accompanies it.
LEDGER_MISSING = "LEDGER_MISSING"
LEDGER_UNREADABLE = "LEDGER_UNREADABLE"
LEDGER_NO_RECORDS = "LEDGER_NO_RECORDS"
NONZERO_PROVIDER_CALLS = "NONZERO_PROVIDER_CALLS"
INVOCATION_RECORD_MISSING = "INVOCATION_RECORD_MISSING"
INVOCATION_RECORD_INVALID = "INVOCATION_RECORD_INVALID"
RERUN_FAILED = "RERUN_FAILED"
SAME_PROCESS = "SAME_PROCESS"
PROCESS_IDENTITY_UNAVAILABLE = "PROCESS_IDENTITY_UNAVAILABLE"
LEDGER_TOTALS_MISMATCH = "LEDGER_TOTALS_MISMATCH"
DISPOSITION_MISMATCH = "DISPOSITION_MISMATCH"

# Minted once when this module is imported: two invocations that share it shared an interpreter.
_PROCESS_NONCE = uuid.uuid4().hex


class NoOpProofError(PresenterError):
    """The no-op proof does not hold; ``reason`` is one of the typed constants above."""

    exit_code = 1

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"[{reason}] {detail}")
        self.reason = reason
        self.detail = detail


class LedgerReconciliationError(NoOpProofError):
    """A bundle's recorded totals disagree with the ledger it seals."""

    def __init__(self, detail: str) -> None:
        super().__init__(LEDGER_TOTALS_MISMATCH, detail)


# --- process identity -------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessIdentity:
    """What distinguishes one process from every other: where it ran and when it started."""

    pid: int
    started: str
    boot_id: str
    nonce: str

    @property
    def key(self) -> tuple[str, int, str]:
        """The operating system's own identity of the process: unique within a boot, and the boot
        marker keeps a recycled process id from a previous boot from looking like this one."""
        return (self.boot_id, self.pid, self.started)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "started": self.started,
            "boot_id": self.boot_id,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, value: object) -> ProcessIdentity:
        if not isinstance(value, Mapping):
            raise NoOpProofError(INVOCATION_RECORD_INVALID, "process identity is not an object")
        pid, started = value.get("pid"), value.get("started")
        boot_id, nonce = value.get("boot_id"), value.get("nonce")
        if (
            not isinstance(pid, int)
            or isinstance(pid, bool)
            or not all(isinstance(item, str) and item for item in (started, boot_id, nonce))
        ):
            raise NoOpProofError(INVOCATION_RECORD_INVALID, "process identity is incomplete")
        return cls(pid, str(started), str(boot_id), str(nonce))


def _unavailable(what: str, exc: object) -> NoOpProofError:
    return NoOpProofError(
        PROCESS_IDENTITY_UNAVAILABLE,
        f"cannot read {what} on {sys.platform}: {exc}; a no-op proof is never recorded without it",
    )


def _run_text(command: list[str]) -> str:
    return subprocess.run(
        command, check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


if sys.platform == "win32":

    def _platform_identity() -> tuple[str, str]:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        ok = kernel32.GetProcessTimes(
            kernel32.GetCurrentProcess(),
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
        started = (created.dwHighDateTime << 32) | created.dwLowDateTime
        # SystemTimeOfDayInformation (class 3) begins with the boot time as a LARGE_INTEGER, a
        # value fixed for the life of the boot (now() minus the tick count would jitter).
        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtQuerySystemInformation.restype = ctypes.c_long
        buffer = ctypes.create_string_buffer(48)
        status = ntdll.NtQuerySystemInformation(3, buffer, 48, None)
        if status != 0:
            raise OSError(status, "NtQuerySystemInformation(SystemTimeOfDayInformation) failed")
        boot = struct.unpack_from("<q", buffer.raw, 0)[0]
        return f"win:{started}", f"win:{boot}"

elif sys.platform == "darwin":

    def _platform_identity() -> tuple[str, str]:
        started = _run_text(["ps", "-o", "lstart=", "-p", str(os.getpid())])
        boot = _run_text(["sysctl", "-n", "kern.bootsessionuuid"])
        return f"ps:{started}", f"boot:{boot}"

else:

    def _platform_identity() -> tuple[str, str]:
        stat = Path("/proc/self/stat").read_text(encoding="utf-8")
        # Field 22 (start time in clock ticks since boot); field 2 is parenthesised and may hold
        # spaces, so count from the last ")" - fields 3.. follow it.
        started = stat.rsplit(")", 1)[1].split()[19]
        boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
        return f"proc:{started}", f"boot:{boot}"


def current_process_identity() -> ProcessIdentity:
    """This process's identity, read from the operating system and never defaulted."""
    try:
        started, boot_id = _platform_identity()
    except (OSError, ValueError, IndexError, TypeError, subprocess.SubprocessError) as exc:
        raise _unavailable("the process start time or boot marker", exc) from exc
    if not started or not boot_id:
        raise _unavailable("the process start time or boot marker", "empty reading")
    return ProcessIdentity(os.getpid(), started, boot_id, _PROCESS_NONCE)


def same_process(first: ProcessIdentity, second: ProcessIdentity) -> bool:
    """Whether two identities are one process: the same in-memory nonce means one interpreter
    whatever else is claimed, and the same (boot, pid, start time) means the operating system
    sees one process. Either is enough."""
    return first.nonce == second.nonce or first.key == second.key


def require_distinct_processes(first: ProcessIdentity, second: ProcessIdentity) -> None:
    """Raise ``SAME_PROCESS`` unless the two identities are distinct processes."""
    if first.nonce == second.nonce:
        raise NoOpProofError(
            SAME_PROCESS,
            "the two invocations share one in-memory nonce; they ran in a single interpreter",
        )
    if same_process(first, second):
        raise NoOpProofError(
            SAME_PROCESS,
            f"the two invocations share one process (pid {first.pid}, started {first.started})",
        )


# --- the invocation record --------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class Invocation:
    """One ``present`` run: its own id, its process, and the ledger it wrote its calls to."""

    invocation_id: str
    identity: ProcessIdentity
    started_at: str
    repository: str | None = None
    ledger_path: Path | None = None
    # Set when the run ended in a processability disposition (a README-only placeholder): there is
    # no candidate, so there is no ledger and nothing to prove a no-op of.
    disposition: str | None = None

    @classmethod
    def begin(cls) -> Invocation:
        return cls(uuid.uuid4().hex, current_process_identity(), _now())

    def run_ref(self) -> dict[str, Any]:
        """The compact reference a bundle's manifest keeps for the invocation that wrote it."""
        return {
            "invocation_id": self.invocation_id,
            "identity": self.identity.to_dict(),
            "started_at": self.started_at,
        }

    def attach_ledger(self, repository: str, path: Path) -> None:
        self.repository = repository
        self.ledger_path = path

    def document(self, root: Path, exit_code: int | None) -> dict[str, Any]:
        """The record a verifier reads later; the ledger is named relative to the project root."""
        ledger: str | None = None
        if self.ledger_path is not None:
            try:
                ledger = self.ledger_path.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                ledger = None
        return {
            "schema_version": RECORD_SCHEMA_VERSION,
            "invocation_id": self.invocation_id,
            "identity": self.identity.to_dict(),
            "started_at": self.started_at,
            "finished_at": _now(),
            "exit_code": exit_code,
            "repository": self.repository,
            "ledger": ledger,
            "disposition": self.disposition,
        }

    def write(self, path: Path, root: Path, exit_code: int | None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.document(root, exit_code), indent=2, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")


def identity_of_run_ref(ref: object) -> ProcessIdentity | None:
    """The process a manifest's run reference names, or ``None`` when the manifest predates run
    references (a bundle sealed before this proof was measured) or the reference is malformed."""
    if not isinstance(ref, Mapping):
        return None
    try:
        return ProcessIdentity.from_dict(ref.get("identity"))
    except NoOpProofError:
        return None


@dataclass(frozen=True)
class InvocationRecord:
    invocation_id: str
    identity: ProcessIdentity
    started_at: str
    exit_code: int | None
    ledger: str | None
    disposition: str | None = None


def read_invocation_record(path: Path) -> InvocationRecord:
    if not path.is_file():
        raise NoOpProofError(
            INVOCATION_RECORD_MISSING,
            f"{path.name}: the invocation left no record, so nothing measured it",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise NoOpProofError(INVOCATION_RECORD_INVALID, f"{path.name}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != RECORD_SCHEMA_VERSION:
        raise NoOpProofError(INVOCATION_RECORD_INVALID, f"{path.name}: unsupported record")
    invocation_id, started_at = value.get("invocation_id"), value.get("started_at")
    exit_code, ledger = value.get("exit_code"), value.get("ledger")
    if not isinstance(invocation_id, str) or not invocation_id or not isinstance(started_at, str):
        raise NoOpProofError(INVOCATION_RECORD_INVALID, f"{path.name}: no invocation id")
    if exit_code is not None and not isinstance(exit_code, int):
        raise NoOpProofError(INVOCATION_RECORD_INVALID, f"{path.name}: exit_code is not an integer")
    if ledger is not None and not isinstance(ledger, str):
        raise NoOpProofError(INVOCATION_RECORD_INVALID, f"{path.name}: ledger is not a path")
    disposition = value.get("disposition")
    if disposition is not None and not isinstance(disposition, str):
        raise NoOpProofError(INVOCATION_RECORD_INVALID, f"{path.name}: disposition is not a name")
    return InvocationRecord(
        invocation_id,
        ProcessIdentity.from_dict(value.get("identity")),
        started_at,
        exit_code,
        ledger,
        disposition,
    )


# --- measuring the ledger ---------------------------------------------------------------------


@dataclass(frozen=True)
class Measurement:
    """What one invocation's own ledger records say it did."""

    records: int
    provider_calls: int
    cache_reuses: int

    def to_dict(self) -> dict[str, int]:
        return {
            "records": self.records,
            "provider_calls": self.provider_calls,
            "cache_reuses": self.cache_reuses,
        }


def _load(ledger: Path) -> list[CallRecord]:
    if not ledger.is_file():
        raise NoOpProofError(LEDGER_MISSING, f"{ledger.name}: the call ledger does not exist")
    try:
        return load_records(ledger)
    except (ValueError, TypeError) as exc:
        raise NoOpProofError(LEDGER_UNREADABLE, f"{ledger.name}: {exc}") from exc


def measure_invocation(ledger: Path, invocation_id: str) -> Measurement:
    """Count what ``invocation_id`` recorded in ``ledger``, read from disk.

    An invocation with no record at all proves nothing - a process that died before its first
    job also made zero calls - so that is a failure too (``LEDGER_NO_RECORDS``): a real rerun
    answers every job from stored output and says so with a ``cache_reuse`` record each.
    """
    own = [record for record in _load(ledger) if record.invocation_id == invocation_id]
    if not own:
        raise NoOpProofError(
            LEDGER_NO_RECORDS,
            f"{ledger.name}: no record belongs to invocation {invocation_id}; a rerun that "
            "reused its stored outputs would have recorded each reuse",
        )
    return Measurement(
        len(own),
        sum(1 for record in own if record.disposition == "provider_call"),
        sum(1 for record in own if record.disposition == "cache_reuse"),
    )


def require_zero_provider_calls(measurement: Measurement, ledger: str) -> None:
    if measurement.provider_calls != 0:
        raise NoOpProofError(
            NONZERO_PROVIDER_CALLS,
            f"{ledger}: the rerun made {measurement.provider_calls} provider calls; a no-op "
            "makes none",
        )


@dataclass(frozen=True)
class Verification:
    first: InvocationRecord
    second: InvocationRecord
    # ``None`` only when both runs ended in the same processability disposition: no candidate
    # exists, so there is no ledger to count and nothing to prove a no-op of.
    measurement: Measurement | None


def _ledger_path(root: Path, record: InvocationRecord) -> Path:
    if record.ledger is None:
        raise NoOpProofError(
            LEDGER_MISSING,
            f"invocation {record.invocation_id} never opened a call ledger (it stopped before "
            "its first job)",
        )
    path = (root / record.ledger).resolve()
    if not path.is_relative_to(root.resolve()):
        raise NoOpProofError(INVOCATION_RECORD_INVALID, "the ledger path leaves the project root")
    return path


def verify_noop_pair(first: Path, second: Path, root: Path) -> Verification:
    """The workflow's gate: the rerun was a different process and made zero provider calls.

    Reads two invocation records, requires them to be distinct processes, and counts the second
    invocation's provider calls from its ledger on disk. It never reads an exit status except to
    refuse a rerun that itself failed.
    """
    first_record = read_invocation_record(first)
    second_record = read_invocation_record(second)
    if second_record.exit_code not in (0, None):
        raise NoOpProofError(RERUN_FAILED, f"the rerun exited {second_record.exit_code}")
    if first_record.invocation_id == second_record.invocation_id:
        raise NoOpProofError(SAME_PROCESS, "both records name one invocation")
    require_distinct_processes(first_record.identity, second_record.identity)
    if second_record.disposition is not None or first_record.disposition is not None:
        if first_record.disposition != second_record.disposition:
            raise NoOpProofError(
                DISPOSITION_MISMATCH,
                f"the first run ended in {first_record.disposition!r}, the rerun in "
                f"{second_record.disposition!r}; one repository, two outcomes",
            )
        return Verification(first_record, second_record, None)
    ledger = _ledger_path(root, second_record)
    measurement = measure_invocation(ledger, second_record.invocation_id)
    require_zero_provider_calls(measurement, second_record.ledger or ledger.name)
    return Verification(first_record, second_record, measurement)


# --- reconciling totals -----------------------------------------------------------------------


def ledger_totals(records: Sequence[CallRecord]) -> dict[str, Any]:
    """The sums a bundle records about its own ledger, taken over every record sealed in it.

    ``total_tokens`` is the sum over provider calls, or ``None`` when any provider call carries
    no token count (a partial sum would read as a measurement it is not).
    """
    provider = [record for record in records if record.disposition == "provider_call"]
    known = all(record.total_tokens is not None for record in provider)
    return {
        "records": len(records),
        "provider_calls": len(provider),
        "cache_reuses": sum(1 for record in records if record.disposition == "cache_reuse"),
        "audit_only": sum(1 for record in records if record.retained_reason),
        "total_tokens": sum(record.total_tokens or 0 for record in provider) if known else None,
    }


def reconcile_ledger(manifest: Mapping[str, Any], ledger: Path) -> None:
    """Fail with ``LEDGER_TOTALS_MISMATCH`` unless the manifest's totals equal the ledger's sums.

    Checked: the recorded ``ledger_totals`` against the sums taken here; ``provider_calls``
    against the provider calls the sealing invocation stamped; and, for a proven bundle, the
    proof's claim of zero provider calls against what its rerun invocation stamped. A manifest
    that records no ``ledger_totals`` was sealed before they existed and is left to its pending
    update rather than judged by a rule it could not have met.
    """
    recorded = manifest.get("ledger_totals")
    if recorded is None:
        return
    try:
        records = load_records(ledger)
    except (OSError, ValueError, TypeError) as exc:
        raise LedgerReconciliationError(f"{ledger.name} cannot be read: {exc}") from exc
    actual = ledger_totals(records)
    if not isinstance(recorded, Mapping):
        raise LedgerReconciliationError("the manifest's ledger_totals is not an object")
    if dict(recorded) != actual:
        differing = sorted(
            key for key in set(actual) | set(recorded) if recorded.get(key) != actual.get(key)
        )
        raise LedgerReconciliationError(
            "the manifest's ledger_totals disagree with the sums over its calls.jsonl: "
            + ", ".join(
                f"{key} recorded {recorded.get(key)!r} ledger {actual.get(key)!r}"
                for key in differing
            )
        )
    sealed_by = manifest.get("sealed_by")
    if isinstance(sealed_by, dict) and isinstance(sealed_by.get("invocation_id"), str):
        stamped = sum(
            1
            for record in records
            if record.invocation_id == sealed_by["invocation_id"]
            and record.disposition == "provider_call"
        )
        if manifest.get("provider_calls") != stamped:
            raise LedgerReconciliationError(
                f"the manifest records {manifest.get('provider_calls')!r} provider calls for its "
                f"sealing invocation, the ledger holds {stamped}"
            )
    proof = manifest.get("no_op_proof")
    rerun = proof.get("rerun") if isinstance(proof, dict) else None
    if isinstance(proof, dict) and isinstance(rerun, dict):
        if not isinstance(rerun.get("invocation_id"), str):
            raise LedgerReconciliationError("the no-op proof names no rerun invocation")
        calls = sum(
            1
            for record in records
            if record.invocation_id == rerun["invocation_id"]
            and record.disposition == "provider_call"
        )
        if calls != 0 or proof.get("provider_calls") != 0:
            raise LedgerReconciliationError(
                f"the no-op proof claims zero provider calls, the ledger holds {calls} stamped "
                "to its rerun invocation"
            )
