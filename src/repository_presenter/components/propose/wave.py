"""Operator tooling for a proposal wave: one read-only readiness table, and a dry-run emitter
for the authorization records an owner's single batch signature covers (G6-W03;
``docs/PROPOSAL_WAVE_RUNBOOK.md``).

A wave opens many real pull requests in one sitting. Each one is still its own exact effect
(``components/propose/effect.py``), so what a wave needs is not a new gate but one place to see,
before the owner signs, which repositories can pass every existing gate, and one deterministic step
that turns the owner's signed list into the exact record files - reviewable in a single pull request
together with the registry mode flips.

This module changes no gate and grants nothing:

- :func:`assess_wave` is a pure read. For each sealed candidate it reports the registry mode, the
  candidate's state, hash and sealed revision, whether that revision still equals the live upstream
  default-branch head (``SOURCE_MOVED`` is a refusal in ``propose``), whether the live head
  still has
  a ``README.md`` (the effect writes exactly that path), the authorization record's state (absent,
  unmerged, expired, mismatched, or valid and merged), and - informationally - whether the sealed
  bundle is behind the running code's governed versions. It does not read the App installation
  (not derivable without the App's own JWT; ``audit-app-installations.yml`` is the evidence source).
- :func:`emit_records` writes record files only into a scratch directory the caller names, only for
  repositories the owner listed with their candidate hash, and only when every listed repository
  passes: one refusal writes nothing. It refuses a scratch directory inside ``ops/proposal-
  authorizations/`` - a record reaches that directory only through the reviewed pull request -
  and it
  never writes to GitHub. Each record is checked with the same ``validate_authorization`` the effect
  uses, so an expired window, an over-long window or a hash that does not match is refused here, not
  discovered at dispatch.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repository_presenter.components.propose.effect import presenter_branch_name
from repository_presenter.core.authorization.proposal import (
    AUTHORIZATION_DIRNAME,
    MAX_LIFETIME,
    ProposalAuthorization,
    authorize_proposal,
    load_authorization_file,
    record_filename,
    render_record,
    validate_authorization,
)
from repository_presenter.core.authorization.record_provenance import (
    run_git,
    verify_record_provenance,
)
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    COUNTED_STATES,
    CURRENT_FILENAME,
    README_FILENAME,
    BundleError,
    StaleCandidate,
    verify_bundle,
)
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.models import Registry

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
#: The shortest candidate-hash prefix an owner may pin (the record file name carries 12).
MIN_HASH_PIN = 12
#: Seconds between workflow dispatches in the generated plan. Content-generating requests are
#: limited to 80 per minute and 500 per hour per authenticated entity; one target makes three
#: (branch ref, contents PUT, pull request), so even unpaced a wave of twenty stays far below that.
#: The pacing exists for the operator's own ability to watch and stop, not to appease the limit.
DISPATCH_PAUSE_SECONDS = 30

_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")
_HEX = re.compile(r"^[0-9a-f]+$")

#: ``(repository) -> (sha, default_branch, readme_found, error)``; the live, read-only observation.
LiveRead = Callable[[str], "LiveObservation"]
#: ``(record_path, root) -> detail`` raising :class:`WriteRefusedError` unless merged before HEAD.
ProvenanceFn = Callable[[Path, Path], str]
ClockFn = Callable[[], datetime]


def git_provenance(record: Path, root: Path) -> str:
    """Whether ``record`` is merged to ``origin/main`` and is an ancestor of this checkout's HEAD -
    the same test ``propose`` applies, with HEAD standing in for the trigger commit. Raises
    :class:`WriteRefusedError` when it is not (or when git cannot answer)."""
    code, head = run_git(["rev-parse", "HEAD"], root)
    if code != 0 or not head.strip():
        raise WriteRefusedError(Refusal.AUTHORIZATION_NOT_COMMITTED, "cannot read HEAD")
    provenance = verify_record_provenance(record, control_root=root, trigger_sha=head.strip())
    return provenance.commit


class WaveError(PresenterError):
    """A usage problem with the wave tooling (not a safety refusal)."""

    exit_code = 2


@dataclass(frozen=True)
class LiveObservation:
    """What the upstream shows right now, or why it could not be read."""

    sha: str | None = None
    branch: str | None = None
    readme_found: bool | None = None
    error: str | None = None


@dataclass(frozen=True)
class WaveRow:
    """One sealed candidate against everything a proposal needs."""

    repository: str
    registry: str
    state: str
    revision: str
    candidate_hash: str
    live_sha: str | None
    base_branch: str | None
    source: str
    readme: str
    authorization: str
    record: str
    stale: tuple[str, ...]
    blockers: tuple[str, ...]
    owner_steps: tuple[str, ...]

    @property
    def verdict(self) -> str:
        if self.blockers:
            return "BLOCKED"
        if self.owner_steps:
            return "READY_TO_AUTHORIZE"
        return "READY_TO_DISPATCH"


def _short(value: str | None) -> str:
    return "-" if not value else value[:12]


def _read_manifest(bundle: Path) -> dict[str, Any] | None:
    try:
        return verify_bundle(bundle)
    except BundleError:
        return None


def sealed_candidates(root: Path) -> list[tuple[str, str, str, str]]:
    """``(repository, state, revision, candidate_hash)`` for every ``CURRENT`` bundle that verifies
    and is ``READY_FOR_PROPOSAL``, in path order. A repository whose bundle does not verify or is
    not final is simply absent; ``assess_wave`` still reports an explicitly requested one."""
    found: list[tuple[str, str, str, str]] = []
    base = root / CANDIDATES_DIRNAME
    if not base.is_dir():
        return found
    for directory in sorted(p for p in base.iterdir() if p.is_dir()):
        inspected = _inspect(root, directory.name.replace("__", "/", 1))
        if inspected is not None and inspected[0] in COUNTED_STATES:
            found.append((inspected[3], inspected[0], inspected[1], inspected[2]))
    return found


def _inspect(root: Path, repository: str) -> tuple[str, str, str, str] | None:
    """``(state, revision, candidate_hash, repository)`` of ``repository``'s CURRENT bundle, or
    ``None`` when there is no verifiable bundle for it."""
    owner, name = repository.split("/", 1)
    directory = root / CANDIDATES_DIRNAME / f"{owner}__{name}"
    current = directory / CURRENT_FILENAME
    if not current.is_file():
        return None
    revision = current.read_text(encoding="utf-8").strip()
    manifest = _read_manifest(directory / revision)
    if manifest is None or manifest.get("revision") != revision:
        return None
    declared = manifest.get("repository")
    if declared != repository:
        return None
    state = str(manifest.get("state", ""))
    readme = directory / revision / README_FILENAME
    if README_FILENAME not in dict(manifest.get("files", {})) or not readme.is_file():
        return None
    candidate_hash = sha256_text(readme.read_bytes().decode("utf-8"))
    return state, revision, candidate_hash, repository


def _authorization_state(
    root: Path,
    repository: str,
    candidate_hash: str,
    revision: str,
    base_branch: str | None,
    now: datetime,
    provenance: ProvenanceFn,
) -> tuple[str, str]:
    """``(label, relative_record_path)``: the record for exactly this candidate, if any."""
    relative = (AUTHORIZATION_DIRNAME / record_filename(repository, candidate_hash)).as_posix()
    path = root / relative
    if not path.is_file():
        return "none", relative
    try:
        authorization = load_authorization_file(path)
    except WriteRefusedError:
        return "unreadable", relative
    decision = validate_authorization(
        authorization,
        now=now.strftime(TIME_FORMAT),
        expected_repository=repository,
        expected_candidate_hash=candidate_hash,
        expected_source_revision=revision,
        expected_base_branch=base_branch or authorization.base_branch,
        expected_branch=presenter_branch_name(),
    )
    if not decision.granted:
        if decision.code is Refusal.AUTHORIZATION_EXPIRED:
            return f"expired {authorization.expires_at}", relative
        return f"mismatch ({decision.reason[:60]})", relative
    try:
        provenance(path, root)
    except WriteRefusedError:
        return f"valid until {authorization.expires_at}, NOT merged to origin/main", relative
    return f"valid+merged until {authorization.expires_at}", relative


def assess_wave(
    root: Path,
    registry: Registry,
    *,
    repositories: Sequence[str] | None,
    live_read: LiveRead | None,
    stale: Iterable[StaleCandidate] = (),
    now: datetime | None = None,
    provenance: ProvenanceFn,
) -> list[WaveRow]:
    """The readiness table. ``repositories`` limits it; ``None`` means every READY_FOR_PROPOSAL
    candidate under ``candidates/``. ``live_read`` is ``None`` for an offline report, in which case
    source freshness is reported as unread and counts as a blocker for nothing. A pure read."""
    clock = now or datetime.now(UTC)
    stale_by_directory = {item.repository_dir: item.reasons for item in stale}
    listed = {entry.repository: entry for entry in registry.entries}
    if repositories is None:
        targets = [item[0] for item in sealed_candidates(root)]
    else:
        targets = list(dict.fromkeys(repositories))
    rows: list[WaveRow] = []
    for repository in targets:
        blockers: list[str] = []
        owner_steps: list[str] = []
        entry = listed.get(repository)
        if entry is None:
            registry_label = "NOT LISTED"
            blockers.append(f"{Refusal.REGISTRY_NOT_LISTED}: not in the registry allow-list")
        else:
            registry_label = entry.mode if entry.active else f"{entry.mode} (inactive)"
            if entry.mode == "disabled" or not entry.active:
                blockers.append(f"{Refusal.REGISTRY_DISABLED}: disabled or inactive")
            elif entry.mode != "full":
                owner_steps.append("flip registry mode to full (OWNER-20 / G6-W06)")
        inspected = _inspect(root, repository) if "/" in repository else None
        if inspected is None:
            rows.append(
                WaveRow(
                    repository=repository,
                    registry=registry_label,
                    state="NO BUNDLE",
                    revision="-",
                    candidate_hash="-",
                    live_sha=None,
                    base_branch=None,
                    source="-",
                    readme="-",
                    authorization="-",
                    record="-",
                    stale=(),
                    blockers=(*blockers, f"{Refusal.BUNDLE_MISSING}: no verifiable CURRENT bundle"),
                    owner_steps=(),
                )
            )
            continue
        state, revision, candidate_hash, _ = inspected
        if state not in COUNTED_STATES:
            blockers.append(f"{Refusal.BUNDLE_NOT_READY}: state is {state}, not READY_FOR_PROPOSAL")
        live_sha: str | None = None
        base_branch: str | None = None
        source = "unread (offline)"
        readme = "unread (offline)"
        if live_read is not None:
            observed = live_read(repository)
            if observed.error is not None or observed.sha is None:
                source = f"UNREADABLE ({observed.error})"
                readme = "-"
                blockers.append(f"live head unreadable: {observed.error}")
            else:
                live_sha, base_branch = observed.sha, observed.branch
                if live_sha == revision:
                    source = "current"
                else:
                    source = f"MOVED to {_short(live_sha)}"
                    blockers.append(
                        f"{Refusal.SOURCE_MOVED}: sealed {_short(revision)} is not live "
                        f"{_short(live_sha)}; re-seal"
                    )
                if observed.readme_found is False:
                    readme = "MISSING"
                    blockers.append(
                        f"the live head has no {README_FILENAME}; the effect writes that exact path"
                    )
                elif observed.readme_found:
                    readme = "present"
                else:
                    readme = "unread"
        authorization, record = _authorization_state(
            root, repository, candidate_hash, revision, base_branch, clock, provenance
        )
        if not authorization.startswith("valid+merged") and not blockers:
            if authorization == "none":
                owner_steps.append(f"merge {record}")
            else:
                owner_steps.append(f"replace {record} ({authorization})")
        slug = repository.replace("/", "__")
        rows.append(
            WaveRow(
                repository=repository,
                registry=registry_label,
                state=state,
                revision=revision,
                candidate_hash=candidate_hash,
                live_sha=live_sha,
                base_branch=base_branch,
                source=source,
                readme=readme,
                authorization=authorization,
                record=record,
                stale=stale_by_directory.get(slug, ()),
                blockers=tuple(blockers),
                owner_steps=tuple(owner_steps),
            )
        )
    return rows


def render_table(rows: Sequence[WaveRow]) -> str:
    """The readiness table as aligned text, followed by every blocker and owner step by name."""
    headers = (
        "repository",
        "mode",
        "state",
        "hash",
        "sealed",
        "live",
        "readme",
        "authorization",
        "stale",
        "verdict",
    )
    body = [
        (
            row.repository,
            row.registry,
            row.state,
            _short(row.candidate_hash),
            _short(row.revision),
            row.source,
            row.readme,
            row.authorization,
            "behind code" if row.stale else "current",
            row.verdict,
        )
        for row in rows
    ]
    widths = [max(len(headers[i]), *(len(line[i]) for line in body)) for i in range(len(headers))]
    lines = ["  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))).rstrip()]
    lines += [
        "  ".join(line[i].ljust(widths[i]) for i in range(len(headers))).rstrip() for line in body
    ]
    detail: list[str] = []
    for row in rows:
        for blocker in row.blockers:
            detail.append(f"  BLOCKED {row.repository}: {blocker}")
        for step in () if row.blockers else row.owner_steps:
            detail.append(f"  owner step {row.repository}: {step}")
    counts = {
        name: sum(1 for row in rows if row.verdict == name)
        for name in ("READY_TO_DISPATCH", "READY_TO_AUTHORIZE", "BLOCKED")
    }
    summary = ", ".join(f"{count} {name}" for name, count in counts.items())
    stale_count = sum(1 for row in rows if row.stale)
    footer = [
        f"{len(rows)} candidate(s): {summary}",
        f"stale (informational only; a stale bundle is still proposable by hash): {stale_count}",
        "App installation and permissions are not derivable offline: "
        "see audit-app-installations.yml",
    ]
    return "\n".join([*lines, *detail, "", *footer])


# ----------------------------------------------------------------------------------------------
# the dry-run record emitter
# ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OwnerEntry:
    """One line of the owner's signed list: a repository and the candidate hash it approves."""

    repository: str
    hash_pin: str


def parse_owner_entries(lines: Iterable[str]) -> list[OwnerEntry]:
    """``OWNER/NAME@HASH`` lines (hash: at least 12 lowercase hex characters, a prefix of the full
    candidate hash). Blank lines and ``#`` comments are skipped. A bare repository name with no hash
    is a usage error: the owner approves an exact candidate, never "whatever is current"."""
    entries: list[OwnerEntry] = []
    seen: set[str] = set()
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        repository, separator, pin = line.partition("@")
        repository, pin = repository.strip(), pin.strip().lower()
        if not separator or not _REPOSITORY.match(repository):
            raise WaveError(f"owner list line {line!r} must be OWNER/NAME@<candidate hash prefix>")
        if len(pin) < MIN_HASH_PIN or not _HEX.match(pin):
            raise WaveError(
                f"owner list line {line!r}: the hash must be at least {MIN_HASH_PIN} lowercase hex "
                "characters"
            )
        if repository in seen:
            raise WaveError(f"owner list names {repository} twice")
        seen.add(repository)
        entries.append(OwnerEntry(repository, pin))
    if not entries:
        raise WaveError("the owner list is empty: nothing to emit")
    return entries


@dataclass(frozen=True)
class EmitRefusal:
    repository: str
    code: str
    reason: str


@dataclass(frozen=True)
class EmitResult:
    written: tuple[Path, ...] = ()
    refusals: tuple[EmitRefusal, ...] = ()


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def emit_records(
    root: Path,
    registry: Registry,
    rows: Sequence[WaveRow],
    owner_entries: Sequence[OwnerEntry],
    *,
    approver: str,
    issued_at: datetime,
    expires_at: datetime,
    destination: Path,
    now: datetime | None = None,
) -> EmitResult:
    """Write the record files for ``owner_entries`` into ``destination`` - or write nothing.

    Every refusal is collected first; when there is any, no file is created. Records are rendered by
    the same ``render_record`` ``draft-proposal-authorization`` uses and checked with the effect's
    own ``validate_authorization``, so what is emitted is what the effect later accepts.
    Besides the records, ``destination`` receives ``registry.json`` (the registry with exactly the
    listed repositories at mode ``full``, for the owner's reviewable flip), ``dispatch-plan.sh``
    (the paced ``gh workflow run`` lines, never run by this tool) and ``wave-manifest.json``."""
    clock = now or datetime.now(UTC)
    refusals: list[EmitRefusal] = []
    protected = root / AUTHORIZATION_DIRNAME
    if _inside(destination, protected) or _inside(protected, destination):
        return EmitResult(
            refusals=(
                EmitRefusal(
                    "-",
                    "destination_is_the_record_directory",
                    f"{destination} is or contains {AUTHORIZATION_DIRNAME.as_posix()}/: records "
                    "reach that directory only through a reviewed pull request",
                ),
            )
        )
    if _inside(destination, root / ".git"):
        return EmitResult(
            refusals=(EmitRefusal("-", "destination_is_git", "refusing to write inside .git"),)
        )
    if expires_at <= clock:
        refusals.append(
            EmitRefusal(
                "-",
                str(Refusal.AUTHORIZATION_EXPIRED),
                f"the window ends {expires_at.strftime(TIME_FORMAT)}, which is not in the future",
            )
        )
    if expires_at - issued_at > MAX_LIFETIME:
        refusals.append(
            EmitRefusal(
                "-",
                str(Refusal.AUTHORIZATION_MISMATCH),
                f"the window exceeds {MAX_LIFETIME.days} days: a standing authorization is not an "
                "authorization of one exact effect",
            )
        )
    if expires_at <= issued_at:
        refusals.append(
            EmitRefusal(
                "-", str(Refusal.AUTHORIZATION_MISMATCH), "expires_at is not after issued_at"
            )
        )
    if not approver.strip():
        refusals.append(EmitRefusal("-", "approver_missing", "--approver is required"))

    by_repository = {row.repository: row for row in rows}
    listed = {entry.repository: entry for entry in registry.entries}
    records: list[tuple[OwnerEntry, ProposalAuthorization, str]] = []
    for owner_entry in owner_entries:
        repository = owner_entry.repository
        row = by_repository.get(repository)
        if repository not in listed:
            refusals.append(
                EmitRefusal(repository, str(Refusal.REGISTRY_NOT_LISTED), "not in the registry")
            )
            continue
        if row is None:
            refusals.append(
                EmitRefusal(
                    repository,
                    "not_in_selection",
                    "the owner listed it but it is not among the assessed candidates",
                )
            )
            continue
        if row.blockers:
            refusals.append(EmitRefusal(repository, "blocked", "; ".join(row.blockers)))
            continue
        if row.live_sha is None or row.base_branch is None:
            refusals.append(
                EmitRefusal(
                    repository,
                    "source_unobserved",
                    "records bind a source revision and base branch: run without --offline",
                )
            )
            continue
        if not row.candidate_hash.startswith(owner_entry.hash_pin):
            refusals.append(
                EmitRefusal(
                    repository,
                    str(Refusal.AUTHORIZATION_MISMATCH),
                    f"the owner approved hash {owner_entry.hash_pin} but the sealed candidate is "
                    f"{row.candidate_hash[:MIN_HASH_PIN]}: the candidate changed since the list "
                    "was written",
                )
            )
            continue
        authorization = authorize_proposal(
            repository=repository,
            candidate_hash=row.candidate_hash,
            source_revision=row.revision,
            base_branch=row.base_branch,
            branch=presenter_branch_name(),
            approver=approver,
            issued_at=issued_at.strftime(TIME_FORMAT),
            expires_at=expires_at.strftime(TIME_FORMAT),
        )
        decision = validate_authorization(
            authorization,
            now=max(clock, issued_at).strftime(TIME_FORMAT),
            expected_repository=repository,
            expected_candidate_hash=row.candidate_hash,
            expected_source_revision=row.revision,
            expected_base_branch=row.base_branch,
            expected_branch=presenter_branch_name(),
        )
        if not decision.granted:
            refusals.append(
                EmitRefusal(
                    repository,
                    str(decision.code or Refusal.AUTHORIZATION_MISMATCH),
                    decision.reason,
                )
            )
            continue
        name = record_filename(repository, row.candidate_hash)
        if (destination / name).exists():
            refusals.append(
                EmitRefusal(repository, "exists", f"{name} already exists in the scratch directory")
            )
            continue
        records.append((owner_entry, authorization, name))
    if refusals:
        return EmitResult(refusals=tuple(refusals))

    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for _, authorization, name in records:
        path = destination / name
        path.write_text(render_record(authorization), encoding="utf-8", newline="\n")
        written.append(path)
    flipped = {item[0].repository for item in records}
    registry_path = destination / "registry.json"
    registry_path.write_text(_registry_with_full(root, flipped), encoding="utf-8", newline="\n")
    written.append(registry_path)
    plan_path = destination / "dispatch-plan.sh"
    plan_path.write_text(
        render_dispatch_plan([(o.repository, n) for o, _, n in records]),
        encoding="utf-8",
        newline="\n",
    )
    written.append(plan_path)
    manifest_path = destination / "wave-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "approver": approver,
                "issued_at": issued_at.strftime(TIME_FORMAT),
                "expires_at": expires_at.strftime(TIME_FORMAT),
                "targets": [
                    {
                        "repository": o.repository,
                        "candidate_hash": a.candidate_hash,
                        "source_revision": a.source_revision,
                        "base_branch": a.base_branch,
                        "record": f"{AUTHORIZATION_DIRNAME.as_posix()}/{n}",
                    }
                    for o, a, n in records
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    written.append(manifest_path)
    return EmitResult(written=tuple(written))


def _registry_with_full(root: Path, repositories: set[str]) -> str:
    """``data/registry.json`` with exactly ``repositories`` at mode ``full`` (everything else as it
    is), in the file's own canonical formatting, so the flip is a minimal reviewable diff."""
    document: Mapping[str, Any] = json.loads(
        (root / "data" / "registry.json").read_text(encoding="utf-8")
    )
    entries = [
        {**entry, "mode": "full"} if entry["repository"] in repositories else entry
        for entry in document["entries"]
    ]
    return json.dumps({**document, "entries": entries}, indent=2, ensure_ascii=False) + "\n"


def render_dispatch_plan(targets: Sequence[tuple[str, str]]) -> str:
    """A reviewed shell plan: one ``gh workflow run propose.yml`` per target, paced. The tool never
    runs it. Stopping the wave is Ctrl-C; a target not yet dispatched is never started."""
    lines = [
        "#!/usr/bin/env bash",
        "# Generated by `repository-presenter wave-readiness --emit-records`.",
        "# This file is NOT executed by the tool.",
        "# Read docs/PROPOSAL_WAVE_RUNBOOK.md first. Run only after the single wave pull request",
        "# (registry flips + records) is merged, as the runbook says.",
        "# To stop the wave: Ctrl-C. Targets not yet dispatched are never started.",
        "set -euo pipefail",
        'CONTROL="babar-raza/repository-presenter"',
        "",
    ]
    for index, (repository, name) in enumerate(targets):
        lines.append(f"# {index + 1}/{len(targets)} {repository}")
        lines.append(
            f'gh workflow run propose.yml -R "$CONTROL" --ref main -f repo={repository} '
            f"-f authorization_record={AUTHORIZATION_DIRNAME.as_posix()}/{name} -f do_propose=true"
        )
        if index != len(targets) - 1:
            lines.append(f"sleep {DISPATCH_PAUSE_SECONDS}")
    return "\n".join(lines) + "\n"
