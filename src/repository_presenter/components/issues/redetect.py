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
(files, tree) and `core/package_registry.py::observe_distribution` (registry; the ecosystem's
own platform module registers its observer, this module never imports it), replaying
the exact evidence shape the handoff itself already carries rather than inventing a new oracle.

Each redetector is registered by the `triggering_check.id`/disposition value it knows how to
re-check (`_REDETECTORS`); an id with no redetector fails closed
(`RedetectorNotRegisteredError`) rather than guessing - the same "add through a registry, never
an if/elif chain" discipline `docs/REPOSITORY_LAYOUT.md` section 2.1 already requires of
ecosystem extractors.

`docs/investigations/03-issue-tracking.md` section 6 names two distinct close reasons, matching
`gh issue close --reason`'s own two values, and requires they never be inferred silently:
`completed` - the defect was genuinely fixed upstream - only when the *same* `triggering_check`
the handoff already points to is re-evaluated at a revision that has actually moved since filing;
`not planned` - a check-version change or a false positive - whenever the check's own definition
has changed since filing (`triggering_check.version` no longer matches `validation/registry.py::
BLOCKING_CHECKS`' current version for that id, the one place this codebase already records a
check's own version history) **or** the check no longer fires at the identical revision that was
filed against (nothing about the target repository changed, so the original finding itself must
have been wrong). `_current_check_version`/`_propose_close_reason` below are the deterministic
rule; this module never asks the LLM to adjudicate which reason applies (AGENTS.md's
Agentic/Deterministic Boundary).
"""

from __future__ import annotations

import os
import posixpath
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import partial
from typing import Any

from repository_presenter.components.issues import source_parse
from repository_presenter.components.issues.model import (
    CloseReason,
    EvidenceEntry,
    Handoff,
    Status,
)
from repository_presenter.components.issues.registry_evidence import (
    RegistryIdentity,
    registry_identities,
)
from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS
from repository_presenter.core.github.read_client import (
    DefaultBranchRead,
    FileRead,
    TreeRead,
    fetch_default_branch_sha,
    fetch_file,
    fetch_tree,
)
from repository_presenter.core.package_registry import (
    RegistryObservation,
    observe_distribution,
)

# A BC-02 handoff about a missing distribution records the registry URL it probed; the replay asks
# the observer registered for that URL's ecosystem (`registry_evidence.py` names it).
# core/package_registry.py resolves the observer by name without this module importing any
# ecosystem's extractor. PyPI keeps its own `observe_pypi` read (the one existing tests inject).
_PYTHON_ECOSYSTEM = "python"
_observe_pypi = partial(observe_distribution, _PYTHON_ECOSYSTEM)
_STATUS_THAT_CAN_RESOLVE: frozenset[Status] = frozenset({"FILED"})

# The repository-level disposition shape (`NOT_PROCESSABLE`) carries no independent versioning of
# its own (schemas/upstream-defect-handoff.schema.json: "\"1\" for a repository-level disposition
# with no independent versioning of its own") - its current version is always "1", so a
# check-version-change close reason can never apply to it, only to a real `BLOCKING_CHECKS` entry.
_NOT_PROCESSABLE_VERSION = "1"


class RedetectorNotRegisteredError(ValueError):
    """No re-detection mechanism is registered for this handoff's `triggering_check.id`."""


def _with_env_token(read: Callable[..., Any]) -> Callable[..., Any]:
    """Pass ``GH_TOKEN`` - the repository-scoped read credential, when the workflow supplies one -
    to a GitHub read, read at call time and never stored. Without it the read is anonymous (public
    repositories only, far lower rate limit), which is what an unauthenticated local run gets."""

    def _call(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("token", os.environ.get("GH_TOKEN") or None)
        return read(*args, **kwargs)

    return _call


@dataclass(frozen=True)
class RedetectionReads:
    """The read-only capabilities a redetector needs, each independently overridable for a test -
    mirrors the registry observer's own injection point rather than mocking a transport."""

    fetch_default_branch_sha: Callable[..., DefaultBranchRead] = fetch_default_branch_sha
    fetch_file: Callable[..., FileRead] = fetch_file
    fetch_tree: Callable[..., TreeRead] = fetch_tree
    observe_pypi: Callable[..., RegistryObservation] = _observe_pypi
    # (ecosystem, name, manifest_version) -> the registry's reading, for every ecosystem but
    # Python; `core/package_registry.py` answers by the ecosystem name each platform registered.
    observe_registry: Callable[..., RegistryObservation] = observe_distribution


DEFAULT_READS = RedetectionReads(
    fetch_default_branch_sha=_with_env_token(fetch_default_branch_sha),
    fetch_file=_with_env_token(fetch_file),
    fetch_tree=_with_env_token(fetch_tree),
    observe_pypi=_observe_pypi,
    observe_registry=observe_distribution,
)


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
    proposed_close_reason: CloseReason | None = None


Redetector = Callable[[Handoff, RedetectionReads], RedetectionResult]
# A redetector's companion: why a handoff's own evidence has not the shape that redetector replays,
# decided from the handoff alone (no network), or None. It is registered with the redetector so the
# two cannot drift apart - `replay_gap` and `redetect` read the same classification.
GapCheck = Callable[[Handoff], str | None]
_REDETECTORS: dict[str, Redetector] = {}
_GAP_CHECKS: dict[str, GapCheck] = {}


def register(check_id: str, *, gap: GapCheck | None = None) -> Callable[[Redetector], Redetector]:
    def _decorator(fn: Redetector) -> Redetector:
        _REDETECTORS[check_id] = fn
        if gap is not None:
            _GAP_CHECKS[check_id] = gap
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


def replay_gap(handoff: Handoff) -> str | None:
    """Why ``redetect`` could not give ``handoff`` a conclusive reading, decided from the handoff
    alone (no network), or ``None`` when its evidence has the shape its redetector replays.

    Filing refuses an inconclusive recheck (``file.py``), so a handoff with a gap here can never be
    filed through the gated path however complete its approval: ``issue-readiness`` reports it
    before the owner signs anything. Kept beside the redetectors it mirrors."""
    if handoff.triggering_check.id not in _REDETECTORS:
        ids = ", ".join(registered_check_ids()) or "none"
        return (
            f"no redetector is registered for triggering_check.id={handoff.triggering_check.id!r} "
            f"(registered: {ids}), so the recheck-before-filing is always inconclusive"
        )
    gap = _GAP_CHECKS.get(handoff.triggering_check.id)
    return gap(handoff) if gap is not None else None


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


def _current_check_version(check_id: str) -> str | None:
    """The live, currently-registered version for ``check_id`` - `None` only if the id itself is
    unknown (never happens for a redetector-registered id, since every registered id is either a
    real `BLOCKING_CHECKS` entry or `NOT_PROCESSABLE`)."""
    if check_id == "NOT_PROCESSABLE":
        return _NOT_PROCESSABLE_VERSION
    check = next((c for c in BLOCKING_CHECKS if c.id == check_id), None)
    return check.version if check is not None else None


def _propose_close_reason(handoff: Handoff, *, revision_drifted: bool) -> CloseReason | None:
    """The reason a `RESOLVED_UPSTREAM` transition carries, per `docs/investigations/
    03-issue-tracking.md` section 6 - only ever called once `_propose_status` has already decided
    `still_fires is False` and the handoff is `FILED`, so this never runs for any other outcome.

    Three-way, deterministic, never defaulted (AGENTS.md: "distinguish these two cases for real"):

    1. The check's own version has changed since this handoff was filed
       (`triggering_check.version` no longer matches its current, live `BLOCKING_CHECKS` entry, or
       `NOT_PROCESSABLE`'s fixed "1") - `not planned`: what counts as passing moved, not the target
       repository.
    2. Otherwise, if the repository's own revision has genuinely drifted since filing - `completed`:
       the identical check, at the identical version, no longer fires at a revision that has moved,
       the literal shape of "the maintainers fixed it."
    3. Otherwise (same check version, same revision) - `not planned`: nothing about the target
       repository or the check changed, so a check that no longer fires at the exact revision it
       was filed against means the original finding was a false positive, not a fix.
    """
    current_version = _current_check_version(handoff.triggering_check.id)
    if current_version is not None and current_version != handoff.triggering_check.version:
        return "not planned"
    if revision_drifted:
        return "completed"
    return "not planned"


def apply_redetection(handoff: Handoff, result: RedetectionResult) -> Handoff:
    """Return the handoff with `result.proposed_status`/`result.proposed_close_reason` applied, or
    ``handoff`` unchanged.

    Never mutates in place; the caller decides whether/when to `write_handoff` the result. Never
    touches `issue_ref` - a `FILED` handoff's `issue_ref` is exactly what `RESOLVED_UPSTREAM` still
    needs, and no other transition this module proposes changes it.
    """
    if result.proposed_status is None:
        return handoff
    return replace(
        handoff, status=result.proposed_status, close_reason=result.proposed_close_reason
    )


def _result(
    handoff: Handoff,
    *,
    revision: str | None,
    drifted: bool,
    still_fires: bool | None,
    note: str,
    fresh: tuple[EvidenceEntry, ...] = (),
) -> RedetectionResult:
    """One `RedetectionResult`, its proposed status and close reason decided by the shared rules
    (``still_fires`` of ``None`` never proposes anything)."""
    proposed_status = _propose_status(handoff, still_fires=still_fires)
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
        proposed_status=proposed_status,
        proposed_close_reason=(
            _propose_close_reason(handoff, revision_drifted=drifted)
            if proposed_status == "RESOLVED_UPSTREAM"
            else None
        ),
    )


# An evidence `path` that names a file in the repository (as opposed to a command line, a URL, or
# prose like "live run"): no whitespace, no scheme, and a dotted file name.
_REPO_PATH = re.compile(r"^(?!https?:)[A-Za-z0-9_@+\-./]*[A-Za-z0-9_@+\-]\.[A-Za-z0-9]+$")


def _repo_paths(handoff: Handoff) -> tuple[str, ...]:
    return tuple(dict.fromkeys(e.path for e in handoff.evidence if _REPO_PATH.match(e.path)))


def _read_head(handoff: Handoff, reads: RedetectionReads) -> tuple[str | None, bool, str | None]:
    """The repository's current default-branch head, whether it moved since ``handoff`` was
    written, and the read error (the head is ``None`` exactly when there is one)."""
    branch = reads.fetch_default_branch_sha(handoff.repository)
    if branch.sha is None:
        return None, False, branch.error or "no default-branch head returned"
    return branch.sha, branch.sha != handoff.source_revision, None


# --- BC-02 / BC-03 / BC-06: which replay a handoff's evidence supports ----------------------------


def _bc02_gap(handoff: Handoff) -> str | None:
    identities = registry_identities(handoff.evidence)
    if len(identities) > 1:
        names = ", ".join(sorted(f"{i.ecosystem}:{i.name}" for i in identities))
        return (
            "the BC-02 redetector replays one package-registry URL and this handoff's evidence "
            f"names {len(identities)} packages ({names}), so the recheck-before-filing is "
            "inconclusive"
        )
    if not identities:
        return _toolchain_gap(handoff)
    return None


def _toolchain_gap(handoff: Handoff) -> str | None:
    if _repo_paths(handoff):
        return None
    return (
        f"the {handoff.triggering_check.id} redetector replays a recorded toolchain finding "
        "against the repository files its evidence cites, and this handoff's evidence cites no "
        "repository file path nor a registry URL, so the recheck-before-filing is inconclusive"
    )


@register("BC-02", gap=_bc02_gap)
def _redetect_install_command_defect(
    handoff: Handoff, reads: RedetectionReads
) -> RedetectionResult:
    """BC-02 (`validation/registry.py::_check_install`). Two evidence shapes, told apart by the
    evidence alone: a package-registry URL (the install command names a distribution the registry
    does not have) is re-probed at the same registry; with no registry URL the finding is a
    toolchain failure (a source build the README documents) and is carried by
    :func:`_redetect_toolchain_defect`. More than one distinct package is refused, not guessed."""
    identities = registry_identities(handoff.evidence)
    if not identities:
        return _redetect_toolchain_defect(handoff, reads)
    if len(identities) != 1:
        head, drifted, _ = _read_head(handoff, reads)
        return _result(
            handoff,
            revision=head or handoff.source_revision,
            drifted=drifted,
            still_fires=None,
            note=(
                "cannot redetect: expected exactly one package-registry identity in this "
                f"handoff's own evidence, found {len(identities)}"
            ),
        )
    return _redetect_registry_defect(handoff, reads, next(iter(identities)))


def _redetect_registry_defect(
    handoff: Handoff, reads: RedetectionReads, identity: RegistryIdentity
) -> RedetectionResult:
    """Re-probe the exact package this handoff's own evidence recorded, at the repository's
    current default-branch revision. Only the manifest-published-distribution half is replayed -
    the primary, mechanical signal `_check_install` actually keys `install_command`'s polarity on
    for this shape (a CONTRADICTED fact's own evidence detail: "package registry: distribution not
    found")."""
    name = identity.name
    head, drifted, _ = _read_head(handoff, reads)
    revision = head or handoff.source_revision
    if identity.ecosystem == _PYTHON_ECOSYSTEM:
        observation = reads.observe_pypi(name, None)
    else:
        observation = reads.observe_registry(identity.ecosystem, name, None)
    fresh: tuple[EvidenceEntry, ...] = (
        EvidenceEntry(path=observation.url, detail=observation.summary),
    )

    manifest_entry = next((e for e in handoff.evidence if e.path.endswith("pyproject.toml")), None)
    if identity.ecosystem == _PYTHON_ECOSYSTEM and manifest_entry is not None and head is not None:
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
        return _result(
            handoff,
            revision=revision,
            drifted=drifted,
            still_fires=None,
            note=f"inconclusive: package registry probe failed: {observation.error}",
            fresh=fresh,
        )

    still_fires = not observation.found
    note = (
        f"still fires: package registry still has no distribution named {name!r}"
        if still_fires
        else f"no longer fires: package registry now lists a distribution named {name!r}"
    )
    return _result(
        handoff,
        revision=revision,
        drifted=drifted,
        still_fires=still_fires,
        note=note,
        fresh=fresh,
    )


@register("BC-03", gap=_toolchain_gap)
def _redetect_example_defect(handoff: Handoff, reads: RedetectionReads) -> RedetectionResult:
    """BC-03 (a README example that does not build or run): the finding is a toolchain run, so it
    is carried by :func:`_redetect_toolchain_defect`."""
    return _redetect_toolchain_defect(handoff, reads)


def _changed_blobs(old: TreeRead, new: TreeRead) -> list[str]:
    paths = old.blob_shas.keys() | new.blob_shas.keys()
    return sorted(p for p in paths if old.blob_shas.get(p) != new.blob_shas.get(p))


def _redetect_toolchain_defect(handoff: Handoff, reads: RedetectionReads) -> RedetectionResult:
    """A finding whose reproduction is a toolchain run recorded in the handoff's evidence (a
    ``dotnet build``, ``tsc``, ``cmake``/``gcc``, or a Python example run) - not a read this
    process can repeat, because it needs a sandbox and the language's SDK.

    What this process *can* establish deterministically is whether any input of that run changed.
    Unchanged inputs give the unchanged outcome, so the defect is carried forward as still present
    when the default branch is still at the revision the finding was made against, or when the
    revision moved but the whole tree's git blob ids are identical. Anything else is
    **inconclusive, never resolved**: a changed tree may or may not have fixed the defect, and only
    re-running the recorded command can say, so ``still_fires`` stays ``None`` and the filing
    path's recheck refuses until the handoff is re-verified at the new revision. This redetector
    therefore never proposes ``RESOLVED_UPSTREAM`` - a fix is recognised only by a re-run.
    """
    cited = _repo_paths(handoff)
    head, drifted, error = _read_head(handoff, reads)
    if not cited:
        return _result(
            handoff,
            revision=head or handoff.source_revision,
            drifted=drifted,
            still_fires=None,
            note=(
                "cannot redetect: this handoff's evidence cites no repository file path nor a "
                "package-registry URL"
            ),
        )
    if head is None:
        return _result(
            handoff,
            revision=None,
            drifted=False,
            still_fires=None,
            note=f"inconclusive: cannot resolve current default-branch revision: {error}",
        )
    short = handoff.source_revision[:12]
    if not drifted:
        return _result(
            handoff,
            revision=head,
            drifted=False,
            still_fires=True,
            note=(
                f"still fires: the default branch is still at {short}, the revision this finding "
                "was made against, so none of the inputs of the recorded toolchain run changed "
                "(the run itself is not re-executed here)"
            ),
            fresh=(EvidenceEntry(path="default branch head", detail=f"{head} (unchanged)"),),
        )
    old = reads.fetch_tree(handoff.repository, handoff.source_revision)
    new = reads.fetch_tree(handoff.repository, head)
    unreadable = next((t for t in (old, new) if t.error or t.truncated), None)
    if unreadable is not None:
        why = unreadable.error or "listing truncated"
        return _result(
            handoff,
            revision=head,
            drifted=True,
            still_fires=None,
            note=(
                f"inconclusive: the default branch moved from {short} to {head[:12]} and the "
                f"trees could not be compared ({why}); re-run the recorded toolchain command"
            ),
        )
    changed = _changed_blobs(old, new)
    if not changed:
        return _result(
            handoff,
            revision=head,
            drifted=True,
            still_fires=True,
            note=(
                f"still fires: the default branch moved from {short} to {head[:12]} but every "
                "file's content is identical, so the recorded toolchain run's inputs are unchanged"
            ),
            fresh=(EvidenceEntry(path="repository tree", detail="no file differs"),),
        )
    cited_changed = [p for p in cited if p in changed]
    fresh = tuple(
        EvidenceEntry(path=p, detail="changed since the finding" if p in changed else "unchanged")
        for p in cited
    )
    return _result(
        handoff,
        revision=head,
        drifted=True,
        still_fires=None,
        note=(
            f"inconclusive: the default branch moved from {short} to {head[:12]} and "
            f"{len(changed)} file(s) differ ({len(cited_changed)} of the {len(cited)} this "
            "handoff cites); the finding is a toolchain run, so re-run the recorded command at "
            "the new revision before relying on it"
        ),
        fresh=fresh,
    )


# A Markdown inline link target in an evidence detail: `[text](docs/guide.md)`. Only a relative
# path is checkable against the tree; a URL, an anchor and a mail link are not.
_MD_LINK = re.compile(r"\]\((?P<target>[^)\s]+)\)")
_NOT_RELATIVE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.\-]*:|#|/)")


def _broken_links(handoff: Handoff) -> tuple[tuple[str, str], ...]:
    """The ``(document, relative target)`` pairs this handoff's evidence says are broken: an
    evidence entry for a Markdown document whose detail quotes an inline link to a repository
    path."""
    pairs: list[tuple[str, str]] = []
    for entry in handoff.evidence:
        if not entry.path.lower().endswith(".md") or entry.detail is None:
            continue
        for match in _MD_LINK.finditer(entry.detail):
            raw = match.group("target")
            target = raw.split("#", 1)[0].split("?", 1)[0]
            if target and not _NOT_RELATIVE.match(raw):
                pairs.append((entry.path, target))
    return tuple(dict.fromkeys(pairs))


def _link_gap(handoff: Handoff) -> str | None:
    if _broken_links(handoff):
        return None
    return (
        "the BC-06 redetector re-checks a Markdown link to a repository path and this handoff's "
        "evidence quotes none (a `[text](relative/path)` in a .md entry's detail), so the "
        "recheck-before-filing is inconclusive"
    )


def _exists(tree: TreeRead, path: str) -> bool:
    return path in tree.blob_shas or any(p.startswith(f"{path}/") for p in tree.paths)


@register("BC-06", gap=_link_gap)
def _redetect_link_defect(handoff: Handoff, reads: RedetectionReads) -> RedetectionResult:
    """BC-06 (a README link to a repository path that does not exist): re-read the document and
    the tree at the repository's current revision. The defect still fires while the document still
    carries the link and the tree still lacks its target; it is gone when the link was removed or
    the target now exists. Anything unreadable is inconclusive, never a resolution."""
    links = _broken_links(handoff)
    head, drifted, error = _read_head(handoff, reads)
    if not links:
        return _result(
            handoff,
            revision=head or handoff.source_revision,
            drifted=drifted,
            still_fires=None,
            note="cannot redetect: no Markdown link to a repository path in this handoff's "
            "evidence",
        )
    if head is None:
        return _result(
            handoff,
            revision=None,
            drifted=False,
            still_fires=None,
            note=f"inconclusive: cannot resolve current default-branch revision: {error}",
        )
    tree = reads.fetch_tree(handoff.repository, head)
    if tree.error is not None or tree.truncated:
        return _result(
            handoff,
            revision=head,
            drifted=drifted,
            still_fires=None,
            note=f"inconclusive: cannot list the repository tree: {tree.error or 'truncated'}",
        )
    fresh: list[EvidenceEntry] = []
    still_broken: list[str] = []
    for document, target in links:
        read = reads.fetch_file(handoff.repository, head, document)
        if not read.found or read.content is None:
            reason = read.error or "not found"
            fresh.append(EvidenceEntry(path=document, detail=f"could not re-fetch: {reason}"))
            return _result(
                handoff,
                revision=head,
                drifted=drifted,
                still_fires=None,
                note=f"inconclusive: could not re-read {document}: {reason}",
                fresh=tuple(fresh),
            )
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(document), target))
        present = f"]({target}" in read.content
        exists = _exists(tree, resolved)
        fresh.append(
            EvidenceEntry(
                path=document,
                detail=f"link to {target} {'still present' if present else 'no longer present'}",
            )
        )
        fresh.append(EvidenceEntry(path=resolved, detail="in tree" if exists else "not in tree"))
        if present and not exists:
            still_broken.append(target)
    still_fires = bool(still_broken)
    note = (
        f"still fires: {', '.join(still_broken)} is still linked and still absent from the tree"
        if still_fires
        else "no longer fires: every recorded link was removed or now resolves to a repository path"
    )
    return _result(
        handoff,
        revision=head,
        drifted=drifted,
        still_fires=still_fires,
        note=note,
        fresh=tuple(fresh),
    )


# --- NOT_PROCESSABLE: a repository whose own source does not parse --------------------------------


def _unparseable_paths(handoff: Handoff) -> tuple[str, ...]:
    """The source paths the evidence names that a registered parser can check."""
    return tuple(sorted({p for p in _repo_paths(handoff) if source_parse.supported(p)}))


def _not_processable_gap(handoff: Handoff) -> str | None:
    if _unparseable_paths(handoff):
        return None
    return (
        "the NOT_PROCESSABLE redetector re-parses named source paths (Python through ast, every "
        "other language through its pinned tree-sitter grammar) and this handoff's evidence names "
        "none, so the recheck-before-filing is inconclusive"
    )


@register("NOT_PROCESSABLE", gap=_not_processable_gap)
def _redetect_not_processable_defect(
    handoff: Handoff, reads: RedetectionReads
) -> RedetectionResult:
    """A repository-level `NOT_PROCESSABLE` disposition whose evidence names one or more source
    paths that failed to parse (the unparseable-source shape, distinct from
    `evidence/facts/processability.py::NO_IMPLEMENTATION_EVIDENCE`, which has no source to parse
    at all). Re-fetches exactly those named paths at the repository's current revision and
    re-parses them with `source_parse` - Python through the same ``ast.parse`` the finding was
    made with, any other language through its pinned tree-sitter grammar (`core/grammars.py`) -
    replayed fresh rather than assumed unchanged. Scope note: this checks the specific path(s) the
    evidence names, not a full repository-wide rescan; a broader corroborating scan is a natural
    future extension once a handoff's evidence typically names more than one representative file.
    """
    named_paths = _unparseable_paths(handoff)
    head, drifted, error = _read_head(handoff, reads)
    revision = head or handoff.source_revision

    if not named_paths:
        return _result(
            handoff,
            revision=revision,
            drifted=drifted,
            still_fires=None,
            note="cannot redetect: no parseable source path recorded in this handoff's own "
            "evidence",
        )
    if head is None:
        return _result(
            handoff,
            revision=None,
            drifted=False,
            still_fires=None,
            note=f"inconclusive: cannot resolve current default-branch revision: {error}",
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
            problem = source_parse.syntax_error(path, file_read.content)
        except source_parse.GrammarUnavailableError as exc:
            inconclusive = True
            fresh.append(EvidenceEntry(path=path, detail=f"cannot parse: {exc}"))
            continue
        if problem is None:
            fresh.append(EvidenceEntry(path=path, detail=f"{source_parse.parser_name(path)}: OK"))
        else:
            failing.append(path)
            fresh.append(EvidenceEntry(path=path, detail=problem))

    if inconclusive and not failing:
        return _result(
            handoff,
            revision=revision,
            drifted=drifted,
            still_fires=None,
            note="inconclusive: could not re-fetch or parse one or more of this handoff's named "
            "source paths",
            fresh=tuple(fresh),
        )

    still_fires = bool(failing)
    note = (
        f"still fires: {len(failing)}/{len(named_paths)} named source path(s) still fail to parse"
        if still_fires
        else f"no longer fires: all {len(named_paths)} named source path(s) now parse cleanly"
    )
    return _result(
        handoff,
        revision=revision,
        drifted=drifted,
        still_fires=still_fires,
        note=note,
        fresh=tuple(fresh),
    )
