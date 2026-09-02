"""The call ledger: one record per provider attempt or cache reuse, appended as JSON lines.

Provider calls reconcile with this file: every physical attempt is recorded with its job, prompt
manifest hash, model route, the model the gateway actually served, request and response hashes,
token counts, and outcome; a reuse of a stored output is recorded as ``cache_reuse`` with zero
provider calls, which is how a no-op rerun proves it called nothing. Content is never stored here,
only hashes and counts.

Extracted from the legacy ``call_schema.py`` and ``call_ledger.py``: the record shape, canonical
request hashing, append-only JSON lines, and the provider-versus-reuse summary are retained; the
context-variable session, run and campaign IDs, fixture calls, and pricing fields are removed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Literal

CallDisposition = Literal["provider_call", "cache_reuse"]
CallOutcome = Literal[
    "success",
    "http_error",
    "timeout",
    "connection_error",
    "response_invalid",
    "cache_reuse",
]
LEDGER_FILENAME = "calls.jsonl"


@dataclass(frozen=True)
class CallRecord:
    """One provider attempt or one explicit reuse of a stored output."""

    call_id: str
    logical_call_id: str
    repository: str
    source_revision: str
    stage: str
    job: str
    prompt_sha256: str
    model_route: str
    model_served: str | None
    attempt: int
    disposition: CallDisposition
    started_at: str
    finished_at: str
    latency_ms: int
    outcome: CallOutcome
    http_status: int | None
    request_sha256: str
    response_sha256: str | None
    provider_request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    error_class: str | None
    schema_version: int = 1

    def to_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class LedgerSummary:
    provider_calls: int
    cache_reuses: int
    calls_by_job: dict[str, int]
    total_tokens: int | None


def canonical_hash(value: Any) -> str:
    """SHA-256 of a JSON-serialisable value in its canonical form."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Ledger:
    """Append-only accounting for one transaction's provider calls."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: CallRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(record.to_line() + "\n")

    def records(self) -> list[CallRecord]:
        return load_records(self.path)

    def summary(self) -> LedgerSummary:
        return summarize(self.records())


def load_records(path: Path) -> list[CallRecord]:
    """Every record in the ledger, in order; a malformed or duplicated line is a defect."""
    if not path.is_file():
        return []
    names = {field.name for field in fields(CallRecord)}
    records: list[CallRecord] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if set(payload) != names:
            raise ValueError(f"{path}:{number}: ledger record fields do not match CallRecord")
        record = CallRecord(**payload)
        if record.call_id in seen:
            raise ValueError(f"{path}:{number}: duplicate call ID {record.call_id}")
        seen.add(record.call_id)
        records.append(record)
    return records


def summarize(records: list[CallRecord]) -> LedgerSummary:
    provider = [record for record in records if record.disposition == "provider_call"]
    by_job: dict[str, int] = {}
    for record in provider:
        by_job[record.job] = by_job.get(record.job, 0) + 1
    tokens_known = all(record.total_tokens is not None for record in provider)
    return LedgerSummary(
        provider_calls=len(provider),
        cache_reuses=sum(1 for record in records if record.disposition == "cache_reuse"),
        calls_by_job=dict(sorted(by_job.items())),
        total_tokens=sum(record.total_tokens or 0 for record in provider) if tokens_known else None,
    )
