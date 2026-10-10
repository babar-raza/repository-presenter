"""Filing readiness per handoff, and the owner's batch approval as one reviewable step.

`file.py` refuses a filing unless a long list of gates hold; each gate lives in its own module and
is only visible one handoff and one refusal at a time. The owner who wants N issues logged needs
the whole picture before signing anything, and needs the approval records for the handoffs they
chose, byte-exact, without hand-computing digests. This module is that read side and nothing more:

- :func:`build_rows` joins every handoff under ``evidence/upstream-defects/`` with the gates that
  can be decided offline from committed files - registry write gate, recheck replayability
  (``redetect.replay_gap``), the committed owner approval (``approval.verify_approval``, so the
  same verdict filing itself would reach) and the independent re-verification record - and names
  every blocker.
- :func:`emit_approvals` writes the approval record files for an owner-supplied list of handoff ids
  into a scratch directory. It is all-or-nothing, binds each record to the digest of the handoff
  the owner reviewed, refuses any handoff not on the list, and refuses a scratch directory inside
  ``ops/``. Nothing here commits, pushes or calls GitHub: the owner copies the files into
  ``ops/issue_approvals/`` through a reviewed pull request, the one human act
  ``approval.py`` requires (a bot-authored record is refused at filing time).

The re-verification record (``evidence/upstream-defects/reverification.json``) is how a handoff is
*flagged* without rewriting its claim: ``plans/idea.md`` allows filing only after the defect is
independently confirmed against evidence, so an entry whose verdict is not ``CONFIRMED``, or whose
``evidence_digest`` no longer matches the handoff (the content changed after it was checked), makes
the handoff unapprovable here. A handoff with no entry is ``UNVERIFIED`` and equally unapprovable.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from repository_presenter.components.issues.approval import (
    BOT_MARKERS,
    DIGEST_PATTERN,
    HANDOFF_ID_PATTERN,
    MAX_APPROVAL_LIFETIME,
    ApprovalStore,
    ApprovalVerdict,
    approval_relative_path,
    evidence_digest,
    handoff_id,
    is_valid_repository,
    parse_approval,
    verify_approval,
)
from repository_presenter.components.issues.ledger import discover_handoff_paths
from repository_presenter.components.issues.model import Handoff, load_handoff
from repository_presenter.components.issues.quality import issue_quality_findings
from repository_presenter.components.issues.redetect import replay_gap
from repository_presenter.core.registry.loader import find_entry
from repository_presenter.core.registry.models import Registry

VERIFICATION_RELATIVE_PATH = "evidence/upstream-defects/reverification.json"
Verdict = Literal["CONFIRMED", "NOT_A_DEFECT", "FIXED_OR_CHANGED", "NOT_VERIFIABLE"]
VERDICTS: tuple[Verdict, ...] = ("CONFIRMED", "NOT_A_DEFECT", "FIXED_OR_CHANGED", "NOT_VERIFIABLE")
DEFAULT_VALID_DAYS = 7
_GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_FIELDS = ("handoff_id", "verdict", "live_head_sha", "verified_at", "evidence_digest", "method")


class ReadinessError(ValueError):
    """A re-verification record or an approval request is not well formed."""


@dataclass(frozen=True)
class Reverification:
    """One independent re-check of a handoff against the live upstream default-branch head."""

    handoff_id: str
    verdict: Verdict
    live_head_sha: str
    verified_at: datetime
    evidence_digest: str
    method: str
    note: str


def load_reverifications(path: Path) -> dict[str, Reverification]:
    """Read the re-verification record; an absent file is an empty record, a malformed one
    raises :class:`ReadinessError` (fail closed: never silently treat a damaged record as
    'nothing was flagged')."""
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReadinessError(f"{path}: cannot read/parse as JSON: {exc}") from exc
    if (
        not isinstance(loaded, dict)
        or loaded.get("schema_version") != 1
        or not isinstance(loaded.get("entries"), list)
    ):
        raise ReadinessError(f"{path}: expected an object with schema_version 1 and entries[]")
    records: dict[str, Reverification] = {}
    for raw in loaded["entries"]:
        if not isinstance(raw, dict):
            raise ReadinessError(f"{path}: every entry must be an object")
        missing = [f for f in _FIELDS if f not in raw]
        if missing:
            raise ReadinessError(f"{path}: entry missing field(s): {', '.join(missing)}")
        identifier = raw["handoff_id"]
        if not isinstance(identifier, str) or not HANDOFF_ID_PATTERN.match(identifier):
            raise ReadinessError(f"{path}: bad handoff_id {identifier!r}")
        if identifier in records:
            raise ReadinessError(f"{path}: duplicate entry for {identifier}")
        verdict = raw["verdict"]
        if verdict not in VERDICTS:
            raise ReadinessError(f"{path}: {identifier}: unknown verdict {verdict!r}")
        if not isinstance(raw["live_head_sha"], str) or not re.fullmatch(
            r"[0-9a-f]{40}", raw["live_head_sha"]
        ):
            raise ReadinessError(f"{path}: {identifier}: live_head_sha is not a 40-hex revision")
        if not isinstance(raw["evidence_digest"], str) or not DIGEST_PATTERN.match(
            raw["evidence_digest"]
        ):
            raise ReadinessError(f"{path}: {identifier}: evidence_digest is not sha256:<64 hex>")
        if not isinstance(raw["method"], str) or not raw["method"].strip():
            raise ReadinessError(f"{path}: {identifier}: method must say how it was re-verified")
        try:
            verified_at = datetime.fromisoformat(str(raw["verified_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReadinessError(f"{path}: {identifier}: verified_at is not ISO-8601") from exc
        if verified_at.tzinfo is None:
            raise ReadinessError(f"{path}: {identifier}: verified_at carries no timezone")
        records[identifier] = Reverification(
            handoff_id=identifier,
            verdict=verdict,
            live_head_sha=raw["live_head_sha"],
            verified_at=verified_at.astimezone(UTC),
            evidence_digest=raw["evidence_digest"],
            method=raw["method"],
            note=str(raw.get("note", "")),
        )
    return records


@dataclass(frozen=True)
class ReadinessRow:
    """Everything the owner needs to decide on one handoff, from committed files alone."""

    handoff: Handoff
    handoff_id: str
    evidence_digest: str
    registry_state: str
    registry_ok: bool
    replay_gap: str | None
    approval: ApprovalVerdict
    reverification: str
    reverified_ok: bool
    blockers: tuple[str, ...] = field(default_factory=tuple)
    quality: tuple[str, ...] = field(default_factory=tuple)

    @property
    def repository(self) -> str:
        return self.handoff.repository

    @property
    def pending(self) -> bool:
        return self.handoff.status == "HANDOFF_PENDING"

    @property
    def approvable(self) -> bool:
        """May the owner's approval be emitted for it: pending, independently confirmed (and
        unchanged since), its recheck can actually conclude, and its issue text passes the
        deterministic quality gate (``quality.py``). The registry gate is deliberately not part
        of this: flipping a registry entry to ``full`` is its own owner decision."""
        return self.pending and self.reverified_ok and self.replay_gap is None and not self.quality

    @property
    def fileable_now(self) -> bool:
        return self.approvable and self.registry_ok and self.approval.approved


def _registry_state(registry: Registry | None, repository: str) -> tuple[str, bool]:
    if registry is None:
        return "registry not loaded", False
    entry = find_entry(registry, repository)
    if entry is None:
        return "not listed", False
    if not entry.active:
        return f"{entry.mode} (inactive)", False
    return entry.mode, entry.mode == "full"


def _reverification_state(record: Reverification | None, digest: str) -> tuple[str, bool]:
    if record is None:
        return "UNVERIFIED (no entry in reverification.json)", False
    stamp = record.verified_at.strftime("%Y-%m-%dT%H:%MZ")
    head = record.live_head_sha[:12]
    if record.verdict != "CONFIRMED":
        return f"{record.verdict} at {head} ({stamp})", False
    if record.evidence_digest != digest:
        return (
            f"STALE (verified {stamp} at {head}, but the handoff changed since: digest "
            f"{record.evidence_digest} != {digest})",
            False,
        )
    return f"CONFIRMED at live head {head} ({stamp})", True


def build_rows(
    upstream_defects_root: Path,
    *,
    registry: Registry | None,
    approvals: ApprovalStore | None,
    reverifications: Mapping[str, Reverification],
    now: Callable[[], datetime] | None = None,
    repository: str | None = None,
) -> list[ReadinessRow]:
    """One row per handoff on record (optionally one repository's), ordered by repository then
    id, each with the blockers that stand between it and a filing."""
    rows: list[ReadinessRow] = []
    for path in discover_handoff_paths(upstream_defects_root):
        handoff = load_handoff(path)
        if repository is not None and handoff.repository != repository:
            continue
        identifier = handoff_id(handoff)
        digest = evidence_digest(handoff)
        registry_state, registry_ok = _registry_state(registry, handoff.repository)
        gap = replay_gap(handoff)
        quality = tuple(str(finding) for finding in issue_quality_findings(handoff))
        if approvals is None:
            approval = ApprovalVerdict(False, "no approval source configured")
        else:
            approval = verify_approval(handoff, approvals, now=now)
        reverification, reverified_ok = _reverification_state(
            reverifications.get(identifier), digest
        )
        blockers: list[str] = []
        if handoff.status != "HANDOFF_PENDING":
            blockers.append(f"status is {handoff.status}, not HANDOFF_PENDING (never re-filed)")
        if not reverified_ok:
            blockers.append(f"not independently confirmed: {reverification}")
        if gap is not None:
            blockers.append(gap)
        if quality:
            blockers.append(
                f"issue text fails the quality gate ({len(quality)} finding(s)): "
                + "; ".join(quality[:3])
                + (" ..." if len(quality) > 3 else "")
            )
        if not registry_ok:
            blockers.append(
                f"registry write gate refuses issue_filing: {handoff.repository} is "
                f"{registry_state}, not full (owner decision, OWNER-20)"
            )
        if not approval.approved:
            blockers.append(f"owner approval: {approval.reason}")
        rows.append(
            ReadinessRow(
                handoff=handoff,
                handoff_id=identifier,
                evidence_digest=digest,
                registry_state=registry_state,
                registry_ok=registry_ok,
                replay_gap=gap,
                approval=approval,
                reverification=reverification,
                reverified_ok=reverified_ok,
                blockers=tuple(blockers),
                quality=quality,
            )
        )
    rows.sort(key=lambda r: (r.repository, r.handoff_id))
    return rows


@dataclass(frozen=True)
class ApprovalRequest:
    """One handoff the owner chose, optionally bound to the digest they reviewed."""

    handoff_id: str
    evidence_digest: str | None = None


def parse_request(token: str) -> ApprovalRequest:
    """``<handoff-id>`` or ``<handoff-id>@sha256:<64 hex>``."""
    identifier, separator, digest = token.strip().partition("@")
    if not HANDOFF_ID_PATTERN.match(identifier):
        raise ReadinessError(f"{token!r}: not a handoff id (<owner>__<name>__<64 hex>)")
    if separator and not DIGEST_PATTERN.match(digest):
        raise ReadinessError(f"{token!r}: the digest after '@' must be sha256:<64 hex>")
    return ApprovalRequest(identifier, digest if separator else None)


def parse_requests(lines: Iterable[str]) -> list[ApprovalRequest]:
    """Requests from a file's lines: blank lines and ``#`` comments are skipped."""
    return [
        parse_request(stripped) for line in lines if (stripped := line.split("#", 1)[0].strip())
    ]


@dataclass(frozen=True)
class EmitOutcome:
    """What an emission did. ``written`` is empty whenever ``refusals`` is not: all or nothing."""

    written: tuple[Path, ...]
    refusals: tuple[tuple[str, str], ...]
    notices: tuple[str, ...]


def build_record_text(
    handoff: Handoff, *, approver: str, approved_at: datetime, expires_at: datetime
) -> str:
    """The exact ``ops/issue_approvals/<handoff-id>.json`` text for ``handoff``."""
    record = {
        "handoff_id": handoff_id(handoff),
        "repository": handoff.repository,
        "evidence_digest": evidence_digest(handoff),
        "approver": approver,
        "approved_at": approved_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return json.dumps(record, indent=2) + "\n"


class _SingleRecordStore:
    def __init__(self, identifier: str, text: str) -> None:
        self._identifier = identifier
        self._text = text

    def read(self, identifier: str) -> str | None:
        return self._text if identifier == self._identifier else None


def _scratch_refusal(root: Path, out_dir: Path) -> str | None:
    resolved = out_dir.resolve()
    for protected in (root / "ops", root / ".git"):
        guard = protected.resolve()
        if resolved == guard or guard in resolved.parents:
            return (
                f"{out_dir} is inside {protected.relative_to(root).as_posix()}/: approval records "
                "are emitted to a scratch directory and reach ops/ only through the owner's own "
                "reviewed pull request"
            )
    return None


def emit_approvals(
    rows: Iterable[ReadinessRow],
    requests: Iterable[ApprovalRequest],
    *,
    root: Path,
    out_dir: Path,
    approver: str,
    now: datetime,
    expires_at: datetime | None = None,
    valid_days: int = DEFAULT_VALID_DAYS,
) -> EmitOutcome:
    """Write one approval record file per requested handoff into ``out_dir``, or none at all.

    Every request is validated before any file is created. A handoff that is not on the list is
    never written; an id that names no handoff on record, a handoff that is not ``approvable``, a
    stale digest, an unusable approver or window, an existing file, or a scratch directory inside
    ``ops/`` is a refusal for the whole batch. Each record is then proved against
    ``approval.verify_approval`` for the same handoff before it is written, so an emitted file is
    one filing would accept at the moment it is committed (until it expires)."""
    by_id = {row.handoff_id: row for row in rows}
    refusals: list[tuple[str, str]] = []
    notices: list[str] = []
    requested = list(requests)
    if not requested:
        return EmitOutcome((), (("(batch)", "no handoff ids were supplied"),), ())

    if not _GITHUB_LOGIN.match(approver) or any(m in approver.lower() for m in BOT_MARKERS):
        return EmitOutcome(
            (), (("(batch)", f"approver {approver!r} is not a person's GitHub login"),), ()
        )
    if now.tzinfo is None:
        raise ReadinessError("now must be timezone-aware")
    window_end = expires_at if expires_at is not None else now + timedelta(days=valid_days)
    if window_end <= now:
        return EmitOutcome(
            (), (("(batch)", f"expiry {window_end.isoformat()} is not after now"),), ()
        )
    if window_end - now > MAX_APPROVAL_LIFETIME:
        return EmitOutcome(
            (),
            (
                (
                    "(batch)",
                    f"validity window exceeds {MAX_APPROVAL_LIFETIME.days} days - an approval is "
                    "not a standing authorization",
                ),
            ),
            (),
        )
    scratch = _scratch_refusal(root, out_dir)
    if scratch is not None:
        return EmitOutcome((), (("(batch)", scratch),), ())

    seen: set[str] = set()
    texts: dict[str, str] = {}
    for request in requested:
        identifier = request.handoff_id
        if identifier in seen:
            refusals.append((identifier, "listed twice"))
            continue
        seen.add(identifier)
        row = by_id.get(identifier)
        if row is None:
            refusals.append((identifier, "not a handoff on record - unlisted ids are refused"))
            continue
        if not is_valid_repository(row.repository):
            refusals.append((identifier, f"target {row.repository!r} is not owner/name"))
            continue
        if request.evidence_digest is not None and request.evidence_digest != row.evidence_digest:
            refusals.append(
                (
                    identifier,
                    f"stale evidence digest: you reviewed {request.evidence_digest} but the "
                    f"handoff is now {row.evidence_digest} - review it again",
                )
            )
            continue
        if not row.approvable:
            refusals.append((identifier, "not approvable: " + "; ".join(row.blockers[:2])))
            continue
        if row.approval.approved:
            refusals.append((identifier, f"already approved ({row.approval.reason})"))
            continue
        target = out_dir / f"{identifier}.json"
        if target.exists():
            refusals.append((identifier, f"{target} already exists - not overwritten"))
            continue
        text = build_record_text(
            row.handoff, approver=approver, approved_at=now, expires_at=window_end
        )
        proof = verify_approval(row.handoff, _SingleRecordStore(identifier, text), now=lambda: now)
        if not proof.approved:  # a bug guard: the emitted record must be one filing accepts
            refusals.append((identifier, f"emitted record would not verify: {proof.reason}"))
            continue
        parse_approval(text)
        texts[identifier] = text
        if request.evidence_digest is None:
            notices.append(
                f"{identifier}: no digest was supplied, so the record binds the handoff as it is "
                f"now ({row.evidence_digest}); supply id@digest from the listing to pin it"
            )
        if not row.registry_ok:
            notices.append(
                f"{identifier}: registry state is {row.registry_state}; the record is emitted but "
                "filing stays refused until the owner makes that entry mode full"
            )
    if refusals:
        return EmitOutcome((), tuple(refusals), tuple(notices))
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for identifier, text in texts.items():
        target = out_dir / f"{identifier}.json"
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
    return EmitOutcome(tuple(written), (), tuple(notices))


def render_listing(rows: list[ReadinessRow], *, kill_switch_on: bool) -> str:
    """The readiness report, grouped by target repository."""
    lines = [
        f"issue-readiness: {len(rows)} handoff(s) on record; kill switch "
        "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED is "
        f"{'ON' if kill_switch_on else 'OFF'} in this process "
        "(the repository variable itself is not readable from here)"
    ]
    current: str | None = None
    for row in rows:
        if row.repository != current:
            current = row.repository
            gate = "write gate OPEN" if row.registry_ok else "write gate REFUSES issue_filing"
            lines += ["", f"== {current}  [registry: {row.registry_state}; {gate}]"]
        lines += [
            f"  handoff {row.handoff_id}",
            f"    status {row.handoff.status}; check {row.handoff.triggering_check.id} "
            f"v{row.handoff.triggering_check.version}; revision {row.handoff.source_revision}",
            f"    title: {row.handoff.suggested_issue_title}",
            f"    evidence_digest: {row.evidence_digest}",
            f"    re-verification: {row.reverification}",
            f"    recheck: {'replayable' if row.replay_gap is None else 'NOT replayable'}",
            "    issue text: "
            + ("passes the quality gate" if not row.quality else "FAILS the quality gate"),
            f"    owner approval: {row.approval.reason}",
            f"    approvable: {'YES' if row.approvable else 'NO'}; "
            f"fileable now: {'YES' if row.fileable_now else 'NO'}",
        ]
        lines += [
            f"    blocker: {blocker}"
            for blocker in row.blockers
            if not blocker.startswith("owner approval:")  # printed on its own line above
        ]
    approvable = [r for r in rows if r.approvable and not r.approval.approved]
    lines += ["", f"{len(approvable)} handoff(s) the owner can approve now:"]
    lines += [f"  {r.handoff_id}@{r.evidence_digest}" for r in approvable]
    lines += [
        "",
        "To approve a batch: repository-presenter issue-readiness --emit-approvals <scratch dir> "
        "--approver <your login> --handoff-id <id>@<digest> ... (writes files only; nothing is "
        "committed, nothing is sent to GitHub). Then commit the files under "
        f"{approval_relative_path('<handoff-id>').rsplit('/', 1)[0]}/ in a reviewed pull request.",
    ]
    return "\n".join(lines)
