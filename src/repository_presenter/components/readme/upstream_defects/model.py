"""The typed shape of one `evidence/upstream-defects/<owner>__<name>/<fingerprint>.json` artifact.

Mirrors `schemas/upstream-defect-handoff.schema.json` field for field. This module does not run
the JSON-Schema validator itself — `tests/test_schemas.py` already holds every committed artifact
to that schema mechanically, the same governance every other `schemas/*.schema.json` file gets
(`AGENTS.md`: "Accepted schemas and tests own implemented interfaces"). Loading here only needs to
fail closed on a shape the ledger and the redetector cannot safely reason about — the same split
`cursor.py` already uses for `project/state.yaml` (a typed reader, not a second schema validator).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Status = Literal["HANDOFF_PENDING", "HANDOFF_ACKNOWLEDGED", "FILED", "RESOLVED_UPSTREAM"]
STATUSES: tuple[Status, ...] = (
    "HANDOFF_PENDING",
    "HANDOFF_ACKNOWLEDGED",
    "FILED",
    "RESOLVED_UPSTREAM",
)
_STATUSES_REQUIRING_ISSUE_REF = frozenset({"FILED", "RESOLVED_UPSTREAM"})


class HandoffError(ValueError):
    """A handoff artifact on disk does not have the shape the ledger/redetector depend on."""


@dataclass(frozen=True)
class TriggeringCheck:
    """The exact `validation.json` check, or repository-level disposition, that fired."""

    id: str
    version: str
    causal_stage: Literal["EXTRACTING"]


@dataclass(frozen=True)
class EvidenceEntry:
    """One `{path, detail}` record — the same shape `Fact.evidence` already uses."""

    path: str
    detail: str | None


@dataclass(frozen=True)
class IssueRef:
    """The filed issue this handoff became, once creation is authorized. Never set here."""

    number: int
    url: str


@dataclass(frozen=True)
class Handoff:
    """One evidence-backed upstream-defect handoff, as committed under
    `evidence/upstream-defects/`."""

    schema_version: int
    repository: str
    source_revision: str
    defect_fingerprint: str
    triggering_check: TriggeringCheck
    evidence: tuple[EvidenceEntry, ...]
    claim: str
    suggested_issue_title: str
    suggested_issue_body: str
    status: Status
    issue_ref: IssueRef | None

    @property
    def key(self) -> tuple[str, str]:
        """The dedup ledger's own key: `{repository, defect_fingerprint}` (investigation
        section 4.1)."""
        return (self.repository, self.defect_fingerprint)


def _require(payload: dict[str, Any], field: str, path: Path) -> Any:
    if field not in payload:
        raise HandoffError(f"{path}: missing required field {field!r}")
    return payload[field]


def handoff_from_dict(payload: dict[str, Any], *, path: Path) -> Handoff:
    """Build a `Handoff` from parsed JSON, failing closed on a missing or malformed field."""
    triggering = _require(payload, "triggering_check", path)
    if not isinstance(triggering, dict):
        raise HandoffError(f"{path}: triggering_check must be an object")
    triggering_check = TriggeringCheck(
        id=_require(triggering, "id", path),
        version=_require(triggering, "version", path),
        causal_stage=_require(triggering, "causal_stage", path),
    )
    if triggering_check.causal_stage != "EXTRACTING":
        raise HandoffError(
            f"{path}: triggering_check.causal_stage is {triggering_check.causal_stage!r}, "
            "not EXTRACTING (schemas/upstream-defect-handoff.schema.json pins this)"
        )
    raw_evidence = _require(payload, "evidence", path)
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise HandoffError(f"{path}: evidence must be a non-empty list")
    evidence = tuple(
        EvidenceEntry(path=_require(e, "path", path), detail=e.get("detail")) for e in raw_evidence
    )
    status = _require(payload, "status", path)
    if status not in STATUSES:
        raise HandoffError(f"{path}: unknown status {status!r}")
    raw_issue_ref = payload.get("issue_ref")
    issue_ref = (
        None
        if raw_issue_ref is None
        else IssueRef(number=raw_issue_ref["number"], url=raw_issue_ref["url"])
    )
    if status in _STATUSES_REQUIRING_ISSUE_REF and issue_ref is None:
        raise HandoffError(f"{path}: status {status!r} requires issue_ref to be set")
    if status not in _STATUSES_REQUIRING_ISSUE_REF and issue_ref is not None:
        raise HandoffError(f"{path}: status {status!r} must not carry an issue_ref")
    return Handoff(
        schema_version=_require(payload, "schema_version", path),
        repository=_require(payload, "repository", path),
        source_revision=_require(payload, "source_revision", path),
        defect_fingerprint=_require(payload, "defect_fingerprint", path),
        triggering_check=triggering_check,
        evidence=evidence,
        claim=_require(payload, "claim", path),
        suggested_issue_title=_require(payload, "suggested_issue_title", path),
        suggested_issue_body=_require(payload, "suggested_issue_body", path),
        status=status,
        issue_ref=issue_ref,
    )


def load_handoff(path: Path) -> Handoff:
    """Read and parse one handoff artifact from disk."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"{path}: cannot read/parse as JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise HandoffError(f"{path}: top level must be a JSON object")
    return handoff_from_dict(payload, path=path)


def handoff_to_dict(handoff: Handoff) -> dict[str, Any]:
    """The JSON-serializable shape, field order matching the schema's own `required` list."""
    payload = asdict(handoff)
    return payload


def write_handoff(handoff: Handoff, path: Path) -> None:
    """Write a handoff artifact back to disk — used only to advance `status`/`issue_ref`, never
    to author a new finding (that stays a human/future-extraction concern, out of this task's
    scope)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(handoff_to_dict(handoff), indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
