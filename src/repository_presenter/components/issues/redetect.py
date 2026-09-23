"""The re-detection pass: does a handoff's own `triggering_check` still fire, right now?

`docs/investigations/03-issue-tracking.md` section 6: "on a later drift-triggered re-run ... the
same `triggering_check` is re-evaluated at the new pinned revision. If it now returns `PASS` ...
that is the close signal - no new machinery needed beyond re-running the check the handoff already
points to and comparing verdicts."

For the two triggering-check shapes this codebase has actually produced so far (`BC-02`, an
`install_command` fact CONTRADICTED against the package registry; `NOT_PROCESSABLE`, a repository
whose own source does not parse), the check itself is entirely deterministic and pre-LLM
(`validation/registry.py::_check_install`'s registry-evidence branch; `ast.parse` on the
repository's own source) - `AGENTS.md`'s Agentic/Deterministic Boundary already puts "validation"
and "immutable snapshots, facts" on the deterministic side. So re-evaluating one of these at the
repository's *current* revision never needs a live LLM call or the full multi-stage `present()`
pipeline (which additionally requires a write-disabled clone, a toolchain, and a reachable
gateway) - it only needs the same *outside-the-pipeline* reproduction
`docs/investigations/03-issue-tracking.md` section 3 already holds the original finding to: a
literal read against the target repository's current state, via `core/github/read_client.py`
(files, tree) and `extractors/platforms/python_registry.py::observe_pypi` (registry), replaying
the exact evidence shape the handoff itself already carries rather than inventing a new oracle.

Each redetector is registered by the `triggering_check.id`/disposition value it knows how to
re-check (`_REDETECTORS`); an id with no redetector fails closed
(`RedetectorNotRegisteredError`) rather than guessing - the same "add through a registry, never
an if/elif chain" discipline `docs/REPOSITORY_LAYOUT.md` section 2.1 already requires of
ecosystem extractors.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    Status,
)
from repository_presenter.components.readme.extractors.platforms.python_registry import (
    RegistryObservation,
    observe_pypi,
)
from repository_presenter.core.github.read_client import (
    DefaultBranchRead,
    FileRead,
    fetch_default_branch_sha,
    fetch_file,
)

_PYPI_EVIDENCE_URL = re.compile(r"^https://pypi\.org/pypi/(?P<name>[^/]+)/json$")
_STATUS_THAT_CAN_RESOLVE: frozenset[Status] = frozenset({"FILED"})


class RedetectorNotRegisteredError(ValueError):
    """No re-detection mechanism is registered for this handoff's `triggering_check.id`."""


@dataclass(frozen=True)
class RedetectionReads:
    """The read-only capabilities a redetector needs, each independently overridable for a test -
    mirrors `observe_pypi`'s own `fetch=` injection point rather than mocking a transport."""

    fetch_default_branch_sha: Callable[..., DefaultBranchRead] = fetch_default_branch_sha
    fetch_file: Callable[..., FileRead] = fetch_file
    observe_pypi: Callable[..., RegistryObservation] = observe_pypi


DEFAULT_READS = RedetectionReads()


@dataclass(frozen=True)
class RedetectionResult:
    """What re-evaluating one handoff's `triggering_check` at the repository's current revision
    found. `still_fires` is `None`, never guessed, when the fresh read itself was inconclusive
    (a network/registry error) - AGENTS.md: "Preserve uncertainty when evidence cannot resolve
    it; never invent a resolution."
    """

    repository: str
    defect_fingerprint: str
    triggering_check_id: str
    checked_at: str
    checked_at_revision: str | None
    revision_drifted: bool
    still_fires: bool | None
    note: str
    fresh_evidence: tuple[EvidenceEntry, ...]
    proposed_status: Status | None


Redetector = Callable[[Handoff, RedetectionReads], RedetectionResult]
_REDETECTORS: dict[str, Redetector] = {}


def register(check_id: str) -> Callable[[Redetector], Redetector]:
    def _decorator(fn: Redetector) -> Redetector:
        _REDETECTORS[check_id] = fn
        return fn

    return _decorator


def registered_check_ids() -> tuple[str, ...]:
    return tuple(sorted(_REDETECTORS))


def redetect(handoff: Handoff, *, reads: RedetectionReads = DEFAULT_READS) -> RedetectionResult:
    """Re-evaluate ``handoff``'s own ``triggering_check`` against the repository's current state."""
    redetector = _REDETECTORS.get(handoff.triggering_check.id)
    if redetector is None:
        ids = ", ".join(registered_check_ids()) or "none"
        raise RedetectorNotRegisteredError(
            f"no redetector registered for triggering_check.id={handoff.triggering_check.id!r} "
            f"({handoff.repository}); registered ids: {ids} - add one in redetect.py before "
            "this handoff can be re-evaluated (never guessed)"
        )
    return redetector(handoff, reads)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _propose_status(handoff: Handoff, *, still_fires: bool | None) -> Status | None:
    """The only schema-valid status change a redetection can ever propose.

    `docs/DECISION_LOG.md`'s 2026-09-17 15:40 UTC ruling: this system only ever closes an issue
    (and by extension only ever proposes `RESOLVED_UPSTREAM`) for a handoff it itself filed -
    `status == FILED`, `issue_ref` already set - never a pre-existing upstream issue, and never a
    still-`HANDOFF_PENDING`/`HANDOFF_ACKNOWLEDGED` one: `RESOLVED_UPSTREAM` requires `issue_ref`
    populated (`schemas/upstream-defect-handoff.schema.json`), which an unfiled handoff does not
    carry, so there is no schema-valid target status for "the defect is gone before it was ever
    filed" - that case is reported (`still_fires=False`) but never auto-transitioned.
    """
    if still_fires is not False:
        return None
    if handoff.status not in _STATUS_THAT_CAN_RESOLVE:
        return None
    return "RESOLVED_UPSTREAM"


def apply_redetection(handoff: Handoff, result: RedetectionResult) -> Handoff:
    """Return the handoff with `result.proposed_status` applied, or ``handoff`` unchanged.

    Never mutates in place; the caller decides whether/when to `write_handoff` the result. Never
    touches `issue_ref` - a `FILED` handoff's `issue_ref` is exactly what `RESOLVED_UPSTREAM` still
    needs, and no other transition this module proposes changes it.
    """
    if result.proposed_status is None:
        return handoff
    return replace(handoff, status=result.proposed_status)


def _pypi_package_names(handoff: Handoff) -> frozenset[str]:
    return frozenset(
        match.group("name")
        for entry in handoff.evidence
        if (match := _PYPI_EVIDENCE_URL.match(entry.path)) is not None
    )


@register("BC-02")
def _redetect_install_command_defect(
    handoff: Handoff, reads: RedetectionReads
) -> RedetectionResult:
    """BC-02 (`validation/registry.py::_check_install`): re-probe the exact package-registry URL
    this handoff's own evidence already recorded, at the repository's current default-branch
    revision. Only the manifest-published-distribution half is replayed - the primary, mechanical
    signal `_check_install` actually keys `install_command`'s polarity on for this shape
    (a CONTRADICTED fact's own evidence detail: "package registry: distribution not found").
    """
    names = _pypi_package_names(handoff)
    branch = reads.fetch_default_branch_sha(handoff.repository)
    revision = branch.sha or handoff.source_revision
    drifted = branch.sha is not None and branch.sha != handoff.source_revision

    if len(names) != 1:
        return RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id=handoff.triggering_check.id,
            checked_at=_now(),
            checked_at_revision=revision,
            revision_drifted=drifted,
            still_fires=None,
            note=(
                "cannot redetect: expected exactly one PyPI evidence URL "
                f"(https://pypi.org/pypi/<name>/json) in this handoff's own evidence, found "
                f"{len(names)}"
            ),
            fresh_evidence=(),
            proposed_status=None,
        )
    name = next(iter(names))
    observation = reads.observe_pypi(name, None)
    fresh: tuple[EvidenceEntry, ...] = (
        EvidenceEntry(path=observation.url, detail=observation.summary),
    )

    manifest_entry = next((e for e in handoff.evidence if e.path.endswith("pyproject.toml")), None)
    if manifest_entry is not None and branch.sha is not None:
        file_read = reads.fetch_file(handoff.repository, revision, "pyproject.toml")
        if file_read.found and file_read.content is not None:
            build_backend = next(
                (
                    line.strip()
                    for line in file_read.content.splitlines()
                    if line.strip().startswith("build-backend")
                ),
                "(no build-backend line found)",
            )
            fresh = (*fresh, EvidenceEntry(path="pyproject.toml", detail=build_backend))

    if observation.error is not None:
        return RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id=handoff.triggering_check.id,
            checked_at=_now(),
            checked_at_revision=revision,
            revision_drifted=drifted,
            still_fires=None,
            note=f"inconclusive: package registry probe failed: {observation.error}",
            fresh_evidence=fresh,
            proposed_status=None,
        )

    still_fires = not observation.found
    note = (
        f"still fires: package registry still has no distribution named {name!r}"
        if still_fires
        else f"no longer fires: package registry now lists a distribution named {name!r}"
    )
    return RedetectionResult(
        repository=handoff.repository,
        defect_fingerprint=handoff.defect_fingerprint,
        triggering_check_id=handoff.triggering_check.id,
        checked_at=_now(),
        checked_at_revision=revision,
        revision_drifted=drifted,
        still_fires=still_fires,
        note=note,
        fresh_evidence=fresh,
        proposed_status=_propose_status(handoff, still_fires=still_fires),
    )


@register("NOT_PROCESSABLE")
def _redetect_not_processable_defect(
    handoff: Handoff, reads: RedetectionReads
) -> RedetectionResult:
    """A repository-level `NOT_PROCESSABLE` disposition whose evidence names one or more `.py`
    source paths that failed `ast.parse` (the unparseable-source shape, distinct from
    `evidence/facts/processability.py::NO_IMPLEMENTATION_EVIDENCE`, which has no source to parse
    at all). Re-fetches exactly those named paths at the repository's current revision and
    re-parses them - the same `ast.parse` reproduction this handoff's own evidence already used,
    replayed fresh rather than assumed unchanged. Scope note: this checks the specific path(s) the
    evidence names, not a full repository-wide rescan; a broader corroborating scan is a natural
    future extension once a handoff's evidence typically names more than one representative file.
    """
    named_paths = tuple(sorted({e.path for e in handoff.evidence if e.path.endswith(".py")}))
    branch = reads.fetch_default_branch_sha(handoff.repository)
    revision = branch.sha or handoff.source_revision
    drifted = branch.sha is not None and branch.sha != handoff.source_revision

    if not named_paths:
        return RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id=handoff.triggering_check.id,
            checked_at=_now(),
            checked_at_revision=revision,
            revision_drifted=drifted,
            still_fires=None,
            note="cannot redetect: no .py source path recorded in this handoff's own evidence",
            fresh_evidence=(),
            proposed_status=None,
        )
    if branch.error is not None:
        return RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id=handoff.triggering_check.id,
            checked_at=_now(),
            checked_at_revision=None,
            revision_drifted=False,
            still_fires=None,
            note=f"inconclusive: cannot resolve current default-branch revision: {branch.error}",
            fresh_evidence=(),
            proposed_status=None,
        )

    fresh: list[EvidenceEntry] = []
    failing: list[str] = []
    inconclusive = False
    for path in named_paths:
        file_read = reads.fetch_file(handoff.repository, revision, path)
        if not file_read.found or file_read.content is None:
            inconclusive = True
            reason = file_read.error or "not found"
            fresh.append(EvidenceEntry(path=path, detail=f"could not re-fetch: {reason}"))
            continue
        try:
            ast.parse(file_read.content)
            fresh.append(EvidenceEntry(path=path, detail="ast.parse: OK"))
        except SyntaxError as exc:
            failing.append(path)
            fresh.append(EvidenceEntry(path=path, detail=f"ast.parse: {type(exc).__name__}: {exc}"))

    if inconclusive and not failing:
        return RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id=handoff.triggering_check.id,
            checked_at=_now(),
            checked_at_revision=revision,
            revision_drifted=drifted,
            still_fires=None,
            note=(
                "inconclusive: could not re-fetch one or more of this handoff's named source paths"
            ),
            fresh_evidence=tuple(fresh),
            proposed_status=None,
        )

    still_fires = bool(failing)
    note = (
        f"still fires: {len(failing)}/{len(named_paths)} named source path(s) still fail ast.parse"
        if still_fires
        else f"no longer fires: all {len(named_paths)} named source path(s) now parse cleanly"
    )
    return RedetectionResult(
        repository=handoff.repository,
        defect_fingerprint=handoff.defect_fingerprint,
        triggering_check_id=handoff.triggering_check.id,
        checked_at=_now(),
        checked_at_revision=revision,
        revision_drifted=drifted,
        still_fires=still_fires,
        note=note,
        fresh_evidence=tuple(fresh),
        proposed_status=_propose_status(handoff, still_fires=still_fires),
    )
