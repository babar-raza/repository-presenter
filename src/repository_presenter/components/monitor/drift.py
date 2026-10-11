"""The drift monitor: is each enabled repository's upstream default branch still the revision its
sealed bundle was built from?

G7-W06 (``docs/EXECUTION_STATE_MACHINE.md`` G7 work item 3): an unattended, read-only observation.
For each enabled registry entry it reads the repository's current default-branch head through
``core/github/read_client.py`` (one bounded GET pair, the same read the redetection pass uses) and
compares it with the revision the repository's ``CURRENT`` sealed bundle names. Each repository
receives exactly one status:

- ``CURRENT``: the bundle still reflects everything it consumed. Either the head equals the
  bundle's source revision, or the head moved but no path the README consumed changed (the row's
  ``change`` says ``IRRELEVANT_CHANGE``: a release-bump commit is not a reseal).
- ``DRIFTED``: a consumed path changed (``change`` ``RELEVANT_CHANGE``): the README, a manifest, a
  file a fact cites, or, at the 30-day freshness check, a registry reading the facts recorded.
- ``UNKNOWN``: whether a consumed path changed cannot be decided (an unreadable or truncated tree,
  a bundle with neither recorded blob ids nor readable facts). Fail closed: never CURRENT, never
  DRIFTED.
- ``NO_BUNDLE``: no usable sealed bundle (none, a ``CURRENT`` that names none, or one failing
  integrity verification). ``detail`` says which.
- ``UNREACHABLE``: the head could not be read. The failure is recorded and the run continues with
  the remaining repositories; one repository never aborts the others.

Relevance is decided by ``relevance.py`` (``classify_change``): over the files the candidate's own
facts cite (plus README, license and notices), from the git blob ids ``components/readme/bundle/
seal.py`` recorded in the manifest, or, for a bundle sealed without them, from the sealed facts'
cited paths against the sealed-revision and head trees. An unrelated file change never drifts a
repository. ``freshness.py`` re-reads the package registry for a bundle older than 30 days. The
status is a deterministic fact about upstream and local disk, so no LLM is involved (``AGENTS.md``,
Agentic and Deterministic Boundary). Nothing here writes to any repository, and the only
credential is the read-only token the caller passes in. ``observe_drift`` takes its GitHub readers
as arguments, so tests inject fakes and never reach the network.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from repository_presenter.components.monitor.freshness import (
    FreshnessResult,
    freshness_check,
    freshness_due,
)
from repository_presenter.components.monitor.relevance import (
    Classification,
    LiveObservation,
    SealedScope,
    classify_change,
    load_scope,
    needs_head_tree,
    needs_sealed_tree,
    read_sealed_facts,
)
from repository_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    BundleError,
    verify_bundle,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.github.read_client import (
    DefaultBranchRead,
    TreeRead,
    fetch_default_branch_sha,
    fetch_tree,
)
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.sealing_plan import DRIFT_CONTRACT_VERSION
from repository_presenter.core.secrets import redact

Status = Literal["CURRENT", "DRIFTED", "UNKNOWN", "NO_BUNDLE", "UNREACHABLE"]
STATUSES: tuple[Status, ...] = ("CURRENT", "DRIFTED", "UNKNOWN", "NO_BUNDLE", "UNREACHABLE")
CHANGES: tuple[str, ...] = (
    "NO_CHANGE",
    "IRRELEVANT_CHANGE",
    "RELEVANT_CHANGE",
    "UNKNOWN",
    "UNREACHABLE",
)
SCHEMA_VERSION = 1
_REVISION = re.compile(r"^[0-9a-f]{40}$")

HeadReader = Callable[..., DefaultBranchRead]
TreeReader = Callable[..., TreeRead]
RegistryObserve = Callable[..., Any]


@dataclass(frozen=True)
class RepositoryDrift:
    """One repository's observation. A revision the run never observed is ``None``."""

    repository: str
    mode: str
    status: Status
    head_revision: str | None
    branch: str | None
    bundle_revision: str | None
    detail: str | None = None
    # The relevance class (``relevance.ChangeClass``) behind ``status``; ``None`` where no
    # classification ran (no bundle, unreachable head), and absent from evidence older than this.
    change: str | None = None


def observe_drift(
    root: Path,
    entries: Iterable[RegistryEntry],
    *,
    token: str,
    read_head: HeadReader = fetch_default_branch_sha,
    read_tree: TreeReader = fetch_tree,
    freshness_observe: RegistryObserve | None = None,
    now: datetime | None = None,
) -> list[RepositoryDrift]:
    """Observe each entry in order. A failure on one entry is recorded, never raised past it.

    ``freshness_observe`` (the registry probe) enables the 30-day freshness check for bundles
    older than ``FRESHNESS_MAX_AGE``; left ``None`` the check does not run and no registry is read.
    """
    return [
        observe_repository(
            root,
            entry,
            token=token,
            read_head=read_head,
            read_tree=read_tree,
            freshness_observe=freshness_observe,
            now=now,
        )
        for entry in entries
    ]


def observe_repository(
    root: Path,
    entry: RegistryEntry,
    *,
    token: str,
    read_head: HeadReader,
    read_tree: TreeReader = fetch_tree,
    freshness_observe: RegistryObserve | None = None,
    now: datetime | None = None,
) -> RepositoryDrift:
    """Read one repository's head, then classify it against its ``CURRENT`` sealed bundle."""
    repository = entry.repository
    try:
        read = read_head(repository, token=token)
    except Exception as exc:  # the per-repository isolation boundary: nothing escapes it
        message = redact(f"{type(exc).__name__}: {exc}", [token])
        return RepositoryDrift(repository, entry.mode, "UNREACHABLE", None, None, None, message)
    if read.sha is None:
        message = redact(read.error or "no default-branch head returned", [token])
        return RepositoryDrift(
            repository, entry.mode, "UNREACHABLE", None, read.branch, None, message
        )
    bundle_revision, manifest, problem = current_bundle(root, repository)
    if bundle_revision is None or manifest is None:
        return RepositoryDrift(
            repository, entry.mode, "NO_BUNDLE", read.sha, read.branch, None, problem
        )
    bundle = bundle_directory(root, repository) / bundle_revision
    scope = load_scope(bundle, bundle_revision, manifest)
    classification = classify_change(
        scope,
        _read_live(repository, read.sha, scope, token=token, read_tree=read_tree),
    )
    if (
        freshness_observe is not None
        and classification.change in ("NO_CHANGE", "IRRELEVANT_CHANGE")
        and freshness_due(manifest.get("sealed_at"), now=now)
    ):
        classification = _with_freshness(
            classification, bundle, entry.ecosystem, scope, freshness_observe
        )
    return RepositoryDrift(
        repository,
        entry.mode,
        _STATUS_OF_CHANGE[classification.change],
        read.sha,
        read.branch,
        bundle_revision,
        None if classification.change == "NO_CHANGE" else classification.detail,
        classification.change,
    )


# A head that moved without touching anything the README consumed leaves the bundle CURRENT: the
# README is still true of the new head, so nothing is due (``change`` keeps the distinction).
_STATUS_OF_CHANGE: dict[str, Status] = {
    "NO_CHANGE": "CURRENT",
    "IRRELEVANT_CHANGE": "CURRENT",
    "RELEVANT_CHANGE": "DRIFTED",
    "UNKNOWN": "UNKNOWN",
    "UNREACHABLE": "UNREACHABLE",
}


def _read_tree(repository: str, revision: str, *, token: str, read_tree: TreeReader) -> TreeRead:
    try:
        return read_tree(repository, revision, token=token)
    except Exception as exc:  # per-repository isolation, as for the head read
        message = redact(f"{type(exc).__name__}: {exc}", [token])
        return TreeRead(repository, revision, error=message)


def _read_live(
    repository: str, head: str, scope: SealedScope, *, token: str, read_tree: TreeReader
) -> LiveObservation:
    """Read only the trees the classification needs: the head's when blob ids are recorded or the
    head moved, the sealed revision's only to decide a moved head with no recorded blob ids."""
    head_tree = (
        _read_tree(repository, head, token=token, read_tree=read_tree)
        if needs_head_tree(scope, head)
        else None
    )
    sealed_tree = (
        _read_tree(repository, scope.revision, token=token, read_tree=read_tree)
        if needs_sealed_tree(scope, head)
        else None
    )
    return LiveObservation(head, head_tree, sealed_tree)


def _with_freshness(
    classification: Classification,
    bundle: Path,
    ecosystem: str,
    scope: SealedScope,
    observe: RegistryObserve,
) -> Classification:
    """Fold the 30-day registry re-check into an otherwise unchanged classification.

    Only a RELEVANT reading changes it; an inconclusive or unchanged one leaves it as it was.
    """
    facts = read_sealed_facts(bundle)
    if facts is None:
        return classification
    result: FreshnessResult = freshness_check(
        ecosystem, facts, observe=observe, consumed_fact_ids=scope.consumed_fact_ids
    )
    if result.change != "RELEVANT_CHANGE":
        return classification
    return Classification("RELEVANT_CHANGE", f"freshness: {result.detail}")


def bundle_directory(root: Path, repository: str) -> Path:
    """The repository's candidate directory (``CURRENT`` and one directory per revision)."""
    return root / CANDIDATES_DIRNAME / repository.replace("/", "__")


def current_bundle(
    root: Path, repository: str
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """The revision ``CURRENT`` names and its verified manifest, when it has a sealed,
    self-consistent bundle.

    Returns ``(revision, manifest, None)`` on success and ``(None, None, reason)`` otherwise. Only
    the ``CURRENT`` pointer is consulted, the same rule ``core/candidates.py`` applies to progress
    counting, so a superseded revision directory left behind can never stand in for the current
    bundle.
    """
    directory = bundle_directory(root, repository)
    pointer = directory / CURRENT_FILENAME
    if not pointer.is_file():
        return None, None, "no CURRENT pointer"
    try:
        revision = pointer.read_text(encoding="utf-8").strip()
    except (OSError, ValueError) as exc:
        return None, None, f"CURRENT pointer is unreadable: {exc}"
    if not _REVISION.fullmatch(revision):
        return None, None, "CURRENT does not name a 40-character revision"
    try:
        manifest = verify_bundle(directory / revision)
    except (BundleError, OSError) as exc:
        return None, None, f"CURRENT bundle fails verification: {exc}"
    if manifest is None:
        return None, None, f"CURRENT names {revision} with no sealed bundle"
    if manifest.get("revision") != revision or manifest.get("repository") != repository:
        return None, None, f"bundle manifest does not describe {repository} at {revision}"
    return revision, manifest, None


def drift_document(
    observations: Sequence[RepositoryDrift],
    *,
    observed_at: str,
    owner: str | None,
    discovery: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The evidence document: a status summary and one row per repository, sorted by name.

    ``discovery`` (``discovery.DiscoveryReport.to_json()``) is an additive section: present only
    when the run reconciled the registry against its organizations, so a document without it is
    exactly the schema 1 document that existed before and every reader of it is unaffected.
    """
    ordered = sorted(observations, key=lambda observation: observation.repository)
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "owner": owner,
        "summary": {
            status: sum(1 for observation in ordered if observation.status == status)
            for status in STATUSES
        },
        # Additive (schema_version 1 is unchanged): how many rows each relevance class has.
        "changes": {
            change: sum(1 for observation in ordered if observation.change == change)
            for change in CHANGES
        },
        "repositories": [asdict(observation) for observation in ordered],
    }
    if discovery is not None:
        document["discovery"] = dict(discovery)
    return document


def write_drift_document(document: dict[str, Any], path: Path) -> Path:
    """Write the evidence document as deterministic JSON, creating its directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


# The handoff to the scheduled sealing run (G7-W06). The monitor runs every 6 hours, so evidence
# older than twice that cadence is refused rather than sealed from.
MAX_DRIFT_AGE = timedelta(hours=12)
_CLOCK_SKEW = timedelta(minutes=5)
_CONTRACT_STATUS = {"CURRENT": "CURRENT", "DRIFTED": "DRIFTED"}
# A row that carries its relevance class hands the plan that class where it decides the work; a
# row without one (older evidence) keeps the status mapping above, so its selection is unchanged.
_CONTRACT_CHANGE = frozenset({"RELEVANT_CHANGE", "IRRELEVANT_CHANGE"})


@dataclass(frozen=True)
class AssembledContract:
    """The sealing contract built from every owner's evidence, plus one notice per owner whose
    GitHub App is not installed (those repositories cannot be observed and are never sealed)."""

    document: dict[str, Any]
    notices: tuple[str, ...]


def _owner_evidence(directory: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("drift-*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        owner = document.get("owner") if isinstance(document, dict) else None
        if not isinstance(owner, str) or document.get("schema_version") != SCHEMA_VERSION:
            raise ConfigError(
                f"drift evidence {path.name} is not a schema {SCHEMA_VERSION} document"
            )
        if owner in documents:
            raise ConfigError(f"drift evidence names owner {owner} more than once")
        documents[owner] = document
    states: dict[str, str] = {}
    for path in sorted(directory.rglob("install-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(record, dict) and isinstance(record.get("owner"), str):
            states[record["owner"]] = str(record.get("state"))
    return documents, states


def assemble_drift_contract(
    directory: Path,
    *,
    expected: Mapping[str, frozenset[str]],
    now: datetime,
    max_age: timedelta = MAX_DRIFT_AGE,
) -> AssembledContract:
    """Merge the per-owner drift evidence under ``directory`` into the one sealing contract.

    ``expected`` maps each enabled registry owner to its enabled repositories. Fail closed
    (ConfigError) when an owner has no evidence and its install record does not say
    NOT_INSTALLED, when an owner's evidence omits one of its enabled repositories, or when any
    evidence is older than ``max_age`` (or dated in the future). Owners recorded NOT_INSTALLED are
    a notice, never zero drift.
    """
    documents, states = _owner_evidence(directory)
    records: list[dict[str, str]] = []
    notices: list[str] = []
    observed: list[datetime] = []
    for owner in sorted(expected):
        if owner not in documents:
            if states.get(owner) == "NOT_INSTALLED":
                notices.append(f"drift: {owner} has no installed GitHub App; not observed")
                continue
            raise ConfigError(
                f"no drift evidence for enabled owner {owner} (install state "
                f"{states.get(owner, 'unrecorded')}); refusing to plan from partial evidence"
            )
        document = documents[owner]
        try:
            stamp = datetime.fromisoformat(str(document.get("observed_at")))
        except ValueError as exc:
            raise ConfigError(f"drift evidence for {owner} has no valid observed_at") from exc
        if stamp.tzinfo is None:
            raise ConfigError(f"drift evidence for {owner} observed_at has no timezone")
        age = now - stamp
        if age > max_age or age < -_CLOCK_SKEW:
            raise ConfigError(
                f"drift evidence for {owner} is stale or future-dated "
                f"(observed {stamp.isoformat()}, age {age}); the limit is {max_age}"
            )
        observed.append(stamp)
        rows = {row.get("repository"): row for row in document.get("repositories", [])}
        missing = sorted(expected[owner] - set(rows))
        if missing:
            raise ConfigError(f"drift evidence for {owner} omits enabled repositories: {missing}")
        for name in sorted(expected[owner]):
            row = rows[name]
            # NO_BUNDLE and UNREACHABLE are never work for a sealing run: they map to UNKNOWN.
            status = _CONTRACT_STATUS.get(str(row.get("status")), "UNKNOWN")
            if row.get("change") in _CONTRACT_CHANGE and status in ("CURRENT", "DRIFTED"):
                status = str(row["change"])
            record: dict[str, Any] = {"repository": name, "status": status}
            # The observed upstream head, when this run actually read one (G7-W06 #1009): lets
            # the sealing plan's failure memory tell a fresh commit apart from the same stuck
            # drift a past failure already recorded, instead of treating every DRIFTED repeat as
            # new work to retry at full cost.
            head_revision = row.get("head_revision")
            if isinstance(head_revision, str):
                record["source_revision"] = head_revision
            records.append(record)
    if not observed:
        raise ConfigError("no drift evidence was observed for any enabled owner; no work is made")
    document = {
        "schema_version": DRIFT_CONTRACT_VERSION,
        "observed_at": min(observed).isoformat(timespec="seconds"),
        "repositories": sorted(records, key=lambda record: record["repository"]),
    }
    return AssembledContract(document, tuple(notices))
