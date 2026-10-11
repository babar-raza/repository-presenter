"""Registry discovery: what do the authorized organizations hold that the registry does not list?

``data/registry.json`` is a hard allow-list, and the portfolio denominator is its size. Nothing
used to compare it with the organizations it was drawn from, so a repository added upstream (or
renamed, or retired) changed no number anywhere: the count was exact for the registry and silent
about the world (``docs/STATE_MACHINE.md``: the portfolio machine "discovers authorized
repositories" and reconciles them with the allow-list; incomplete discovery is ``Degraded``).
This module is that reconciliation, and it is read-only in the strongest sense.

**Discovery never admits.** Admission is an owner act (an edit to ``data/registry.json``); nothing
here reads a candidate repository beyond the organization listing, adds an entry, widens a
permission, or changes the denominator. Its whole output is a classification of every repository
GitHub lists in a registry organization:

- ``REGISTERED``: the registry entry's provider repository id is listed under the same name, alive.
- ``UNREGISTERED``: listed, not admitted, and not excluded: a candidate for the owner's decision.
- ``EXCLUDED_BY_POLICY``: listed, not admitted, and matched by a reason-bearing line of
  ``data/registry_exclusions.json`` (the organization profile repository, archived repositories,
  forks): known not to be a presentation target.
- ``MISSING_UPSTREAM``: a registry entry whose repository id is no longer listed under its name:
  deleted, transferred out, renamed (the new name is then also ``UNREGISTERED``, with
  ``renamed_from`` pointing back), re-created under the same name with a different id, or archived.

Identity is the stable provider repository id, never the name (``core/registry/models.py``): that
is what makes a rename a recognizable pair instead of an unexplained disappearance. An incomplete
listing (a failed page, a malformed record, the page cap) is never read as absence: it makes the
organization ``incomplete`` and produces no ``MISSING_UPSTREAM`` from what it did not show.

The report is evidence, not a gate: it goes into the drift document as an additive ``discovery``
section and into ``status``, and a non-empty ``UNREGISTERED`` is a warning for the owner, never a
red run. ``observe_registry_gaps`` takes the organization lister as an argument, so tests inject
a fake and no test reaches the network; no repository found here is ever read a second time.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
    model_validator,
)

from repository_presenter.components.monitor.org_listing import (
    OrganizationLister,
    OrganizationListing,
    UpstreamRepository,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.registry.models import REPOSITORY_PATTERN, Registry, RegistryEntry
from repository_presenter.core.secrets import redact

Classification = Literal["REGISTERED", "UNREGISTERED", "EXCLUDED_BY_POLICY", "MISSING_UPSTREAM"]
CLASSIFICATIONS: tuple[Classification, ...] = (
    "REGISTERED",
    "UNREGISTERED",
    "EXCLUDED_BY_POLICY",
    "MISSING_UPSTREAM",
)
EXCLUSIONS_RELATIVE_PATH = Path("data") / "registry_exclusions.json"
DOCUMENT_SCHEMA_VERSION = 1
# The most names one workflow annotation carries; the summary table and the JSON carry them all.
ANNOTATION_NAME_LIMIT = 25
PRIVATE_NAME_WITHHELD = "(private repository, name withheld)"


# --- The policy file: which unadmitted repositories are known not to be targets -----------------


class ExclusionMatch(BaseModel):
    """The flags a rule matches on; every criterion present must hold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+$")
    archived: StrictBool | None = None
    fork: StrictBool | None = None
    private: StrictBool | None = None

    @model_validator(mode="after")
    def _names_a_criterion(self) -> ExclusionMatch:
        if all(value is None for value in (self.name, self.archived, self.fork, self.private)):
            raise ValueError("a rule's match must name at least one criterion")
        return self

    def matches(self, repository: UpstreamRepository) -> bool:
        return (
            (self.name is None or repository.name.casefold() == self.name.casefold())
            and (self.archived is None or repository.archived == self.archived)
            and (self.fork is None or repository.fork == self.fork)
            and (self.private is None or repository.private == self.private)
        )


class ExclusionRule(BaseModel):
    """A structural exclusion that applies in every organization (the profile repository...)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    match: ExclusionMatch
    reason: str = Field(min_length=10)


class ExcludedRepository(BaseModel):
    """One named repository the owner decided is not a presentation target.

    ``repository_id``, when given, must match too: an exclusion never silently carries over to a
    different repository that was later created under the same name.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(pattern=REPOSITORY_PATTERN)
    repository_id: StrictInt | None = Field(default=None, gt=0)
    reason: str = Field(min_length=10)


class Exclusions(BaseModel):
    """``data/registry_exclusions.json``: rules first, then named repositories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    rules: tuple[ExclusionRule, ...] = ()
    repositories: tuple[ExcludedRepository, ...] = ()

    @model_validator(mode="after")
    def _identifiers_are_unique(self) -> Exclusions:
        rule_ids = [rule.id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("exclusion rule ids must be unique")
        names = [item.repository.casefold() for item in self.repositories]
        if len(names) != len(set(names)):
            raise ValueError("an excluded repository is named more than once")
        return self

    def reason_for(self, repository: UpstreamRepository) -> tuple[str, str] | None:
        """``(reason id, reason text)`` of the first line that excludes ``repository``."""
        for item in self.repositories:
            if item.repository.casefold() != repository.full_name.casefold():
                continue
            if item.repository_id is None or item.repository_id == repository.repository_id:
                return "listed", item.reason
        for rule in self.rules:
            if rule.match.matches(repository):
                return rule.id, rule.reason
        return None


def load_exclusions(path: Path) -> Exclusions:
    """Load and validate the exclusion policy; raise :class:`ConfigError` if it is unfit."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"registry exclusions not found: {path}") from exc
    except (OSError, ValueError) as exc:
        raise ConfigError(f"registry exclusions are not readable JSON: {path}: {exc}") from exc
    try:
        return Exclusions.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"registry exclusions are malformed: {path}: {exc}") from exc


# --- The classification --------------------------------------------------------------------------


@dataclass(frozen=True)
class DiscoveryRow:
    """One repository that is not simply ``REGISTERED``.

    ``reason`` is the policy rule id (``EXCLUDED_BY_POLICY``) or the cause (``MISSING_UPSTREAM``:
    ``renamed``, ``archived``, ``identity_changed``, ``not_found``); ``detail`` says it in words.
    """

    repository: str
    classification: Classification
    repository_id: int | None
    reason: str | None = None
    detail: str | None = None
    archived: bool = False
    private: bool = False
    fork: bool = False
    language: str | None = None
    pushed_at: str | None = None
    renamed_from: str | None = None
    renamed_to: str | None = None


@dataclass(frozen=True)
class OrganizationDiscovery:
    """The reconciliation of one organization. ``rows`` hold everything but ``REGISTERED``."""

    organization: str
    admitted: int
    listed: int | None
    registered: int
    rows: tuple[DiscoveryRow, ...] = ()
    error: str | None = None
    truncated: bool = False

    @property
    def complete(self) -> bool:
        return self.error is None and not self.truncated

    def count(self, classification: Classification) -> int:
        if classification == "REGISTERED":
            return self.registered
        return sum(1 for row in self.rows if row.classification == classification)


def reconcile_organization(
    organization: str,
    entries: Sequence[RegistryEntry],
    listing: OrganizationListing,
    exclusions: Exclusions,
) -> OrganizationDiscovery:
    """Classify every upstream repository and every admitted entry of one organization.

    Pure: no I/O, no registry mutation. An organization whose listing failed is reported as such
    with no rows at all, since nothing can be concluded about presence *or* absence.
    """
    if listing.error is not None:
        return OrganizationDiscovery(organization, len(entries), None, 0, error=listing.error)
    upstream = listing.repositories
    by_id = {repository.repository_id: repository for repository in upstream}
    by_name = {repository.full_name.casefold(): repository for repository in upstream}
    rows: list[DiscoveryRow] = []
    claimed: set[int] = set()
    renamed_from: dict[int, str] = {}
    registered = 0
    for entry in sorted(entries, key=lambda item: item.repository):
        identity = entry.provider_identity.repository_id
        match = by_id.get(identity)
        if match is not None and match.full_name == entry.repository:
            claimed.add(identity)
            if match.archived:
                rows.append(
                    _missing(entry, "archived", "the upstream repository is archived (read-only)")
                )
            else:
                registered += 1
        elif match is not None:
            renamed_from[identity] = entry.repository
            rows.append(
                _missing(
                    entry,
                    "renamed",
                    f"renamed upstream to {match.full_name} (same repository id); the registry "
                    "still names the old repository",
                    renamed_to=match.full_name,
                )
            )
        elif (holder := by_name.get(entry.repository.casefold())) is not None:
            rows.append(
                _missing(
                    entry,
                    "identity_changed",
                    f"the name is now held by repository id {holder.repository_id}, not the "
                    f"admitted id {identity} (deleted and re-created, or transferred)",
                )
            )
        elif not listing.truncated:
            rows.append(
                _missing(
                    entry,
                    "not_found",
                    "no repository with the admitted id or name is listed (deleted, transferred "
                    "out, or not visible to the token)",
                )
            )
    for repository in sorted(upstream, key=lambda item: item.full_name.casefold()):
        if repository.repository_id in claimed:
            continue
        excluded = exclusions.reason_for(repository)
        rows.append(
            DiscoveryRow(
                repository=repository.full_name,
                classification="UNREGISTERED" if excluded is None else "EXCLUDED_BY_POLICY",
                repository_id=repository.repository_id,
                reason=None if excluded is None else excluded[0],
                detail=None if excluded is None else excluded[1],
                archived=repository.archived,
                private=repository.private,
                fork=repository.fork,
                language=repository.language,
                pushed_at=repository.pushed_at,
                renamed_from=renamed_from.get(repository.repository_id),
            )
        )
    return OrganizationDiscovery(
        organization,
        len(entries),
        len(upstream),
        registered,
        tuple(sorted(rows, key=_row_order)),
        truncated=listing.truncated,
    )


def _missing(
    entry: RegistryEntry, reason: str, detail: str, *, renamed_to: str | None = None
) -> DiscoveryRow:
    return DiscoveryRow(
        repository=entry.repository,
        classification="MISSING_UPSTREAM",
        repository_id=entry.provider_identity.repository_id,
        reason=reason,
        detail=detail,
        renamed_to=renamed_to,
    )


def _row_order(row: DiscoveryRow) -> tuple[int, str]:
    return CLASSIFICATIONS.index(row.classification), row.repository.casefold()


@dataclass(frozen=True)
class DiscoveryReport:
    """Every observed organization's reconciliation, with the instant it was observed.

    ``error`` is set only when discovery could not run at all (its policy file was unreadable);
    an organization that could not be listed carries its own ``error`` instead.
    """

    observed_at: str
    organizations: tuple[OrganizationDiscovery, ...] = ()
    error: str | None = None

    @property
    def complete(self) -> bool:
        return self.error is None and all(item.complete for item in self.organizations)

    @property
    def admitted(self) -> int:
        return sum(item.admitted for item in self.organizations)

    @property
    def listed(self) -> int:
        return sum(item.listed or 0 for item in self.organizations)

    def counts(self) -> dict[Classification, int]:
        return {
            name: sum(item.count(name) for item in self.organizations) for name in CLASSIFICATIONS
        }

    def rows(self, classification: Classification) -> tuple[DiscoveryRow, ...]:
        return tuple(
            row
            for item in self.organizations
            for row in item.rows
            if row.classification == classification
        )

    @property
    def unregistered(self) -> tuple[DiscoveryRow, ...]:
        return self.rows("UNREGISTERED")

    @property
    def missing_upstream(self) -> tuple[DiscoveryRow, ...]:
        return self.rows("MISSING_UPSTREAM")

    @property
    def excluded(self) -> tuple[DiscoveryRow, ...]:
        return self.rows("EXCLUDED_BY_POLICY")

    @property
    def incomplete_organizations(self) -> tuple[OrganizationDiscovery, ...]:
        return tuple(item for item in self.organizations if not item.complete)

    def to_json(self) -> dict[str, Any]:
        """The ``discovery`` section: counts, per-organization totals, every non-registered row."""
        return {
            "observed_at": self.observed_at,
            "complete": self.complete,
            "error": self.error,
            "admitted": self.admitted,
            "listed": self.listed,
            "counts": self.counts(),
            "organizations": {
                item.organization: {
                    "admitted": item.admitted,
                    "listed": item.listed,
                    "registered": item.registered,
                    "unregistered": item.count("UNREGISTERED"),
                    "excluded_by_policy": item.count("EXCLUDED_BY_POLICY"),
                    "missing_upstream": item.count("MISSING_UPSTREAM"),
                    "error": item.error,
                    "truncated": item.truncated,
                }
                for item in sorted(self.organizations, key=lambda o: o.organization.casefold())
            },
            "unregistered": [asdict(row) for row in self.unregistered],
            "excluded_by_policy": [asdict(row) for row in self.excluded],
            "missing_upstream": [asdict(row) for row in self.missing_upstream],
        }

    @classmethod
    def from_json(cls, section: Mapping[str, Any]) -> DiscoveryReport:
        """Rebuild a report from a ``discovery`` section; :class:`ConfigError` if it is unfit."""
        try:
            rows: dict[str, list[DiscoveryRow]] = {}
            for key in ("unregistered", "excluded_by_policy", "missing_upstream"):
                for raw in section[key]:
                    row = DiscoveryRow(**raw)
                    if row.classification not in CLASSIFICATIONS:
                        raise ValueError(f"unknown classification {row.classification!r}")
                    rows.setdefault(row.repository.split("/", 1)[0].casefold(), []).append(row)
            organizations = tuple(
                OrganizationDiscovery(
                    organization=name,
                    admitted=int(summary["admitted"]),
                    listed=None if summary["listed"] is None else int(summary["listed"]),
                    registered=int(summary["registered"]),
                    rows=tuple(sorted(rows.get(name.casefold(), ()), key=_row_order)),
                    error=None if summary["error"] is None else str(summary["error"]),
                    truncated=summary["truncated"] is True,
                )
                for name, summary in sorted(section["organizations"].items())
            )
            error = section["error"]
            return cls(
                observed_at=str(section["observed_at"]),
                organizations=organizations,
                error=None if error is None else str(error),
            )
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ConfigError(
                f"discovery evidence is malformed: {type(exc).__name__}: {exc}"
            ) from exc


def merge_reports(reports: Sequence[DiscoveryReport]) -> DiscoveryReport | None:
    """One report from several (a monitor leg per organization): the newest word on each one.

    The merged ``observed_at`` is the oldest used, since the whole is only as fresh as its
    stalest part; a report that could not run at all contributes its error and no organizations.
    """
    if not reports:
        return None
    newest: dict[str, tuple[str, OrganizationDiscovery]] = {}
    errors: list[str] = []
    for report in sorted(reports, key=lambda item: item.observed_at):
        if report.error is not None:
            errors.append(report.error)
        for item in report.organizations:
            newest[item.organization.casefold()] = (report.observed_at, item)
    used = [stamp for stamp, _ in newest.values()] or [report.observed_at for report in reports]
    return DiscoveryReport(
        observed_at=min(used),
        organizations=tuple(
            item for _, item in sorted(newest.values(), key=lambda p: p[1].organization.casefold())
        ),
        error="; ".join(dict.fromkeys(errors)) or None,
    )


# --- Observation ---------------------------------------------------------------------------------


def discover(
    registry: Registry,
    exclusions: Exclusions,
    *,
    lister: OrganizationLister,
    token: str,
    observed_at: str,
    organization: str | None = None,
) -> DiscoveryReport:
    """List each authorized organization once and reconcile it with the registry.

    The organizations are exactly the registry's owners (``organization`` narrows to one of
    them): no organization the registry does not name is ever listed, and a repository found in
    a listing is never read again. A failure listing one organization is recorded on it and the
    others continue.
    """
    groups: dict[str, list[RegistryEntry]] = {}
    spelling: dict[str, str] = {}
    for entry in registry.entries:
        key = entry.owner.casefold()
        groups.setdefault(key, []).append(entry)
        spelling.setdefault(key, entry.owner)
    if organization is not None and organization.casefold() not in groups:
        raise ConfigError(f"{organization} is not an organization in the registry")
    wanted = sorted(key for key in groups if organization is None or key == organization.casefold())
    results: list[OrganizationDiscovery] = []
    for key in wanted:
        name = spelling[key]
        try:
            listing = lister(name, token=token)
        except Exception as exc:  # the per-organization isolation boundary: nothing escapes it
            listing = OrganizationListing(
                name, error=redact(f"{type(exc).__name__}: {exc}", [token])
            )
        results.append(reconcile_organization(name, groups[key], listing, exclusions))
    return DiscoveryReport(observed_at, tuple(results))


def observe_registry_gaps(
    root: Path,
    registry: Registry,
    *,
    lister: OrganizationLister,
    token: str,
    now: datetime,
    organization: str | None = None,
) -> DiscoveryReport:
    """``discover`` with the project's own exclusion policy.

    An unreadable policy file is a typed discovery failure carried in the report (``error``),
    never an exception past the caller: the drift observation it rides on must still complete.
    """
    observed_at = now.isoformat(timespec="seconds")
    try:
        exclusions = load_exclusions(root / EXCLUSIONS_RELATIVE_PATH)
    except ConfigError as exc:
        return DiscoveryReport(observed_at, error=str(exc))
    return discover(
        registry,
        exclusions,
        lister=lister,
        token=token,
        observed_at=observed_at,
        organization=organization,
    )


def discovery_document(report: DiscoveryReport) -> dict[str, Any]:
    """The standalone evidence document (``registry-gaps --out``), shaped like a drift document's
    additive section so one loader reads both."""
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "discovery": report.to_json()}


def load_discovery(path: Path) -> DiscoveryReport | None:
    """Read the discovery section(s) under ``path``: a drift or discovery document, or a directory.

    ``None`` when nothing there carries a section (older evidence, an install record): the
    caller reports "not observed" rather than guessing zero. A file that is not JSON is
    :class:`ConfigError`.
    """
    if not path.exists():
        raise ConfigError(f"discovery evidence not found: {path}")
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    reports: list[DiscoveryReport] = []
    for file in files:
        try:
            document = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ConfigError(f"discovery evidence is unreadable: {file}: {exc}") from exc
        section = document.get("discovery") if isinstance(document, dict) else None
        if isinstance(section, dict):
            reports.append(DiscoveryReport.from_json(section))
    return merge_reports(reports)


# --- Presentation --------------------------------------------------------------------------------


def row_label(row: DiscoveryRow) -> str:
    """One line for a row: the name, then the facts an owner needs to decide."""
    facts: list[str] = []
    if row.repository_id is not None:
        facts.append(f"id {row.repository_id}")
    if row.language:
        facts.append(row.language)
    if row.pushed_at:
        facts.append(f"pushed {row.pushed_at[:10]}")
    facts.extend(flag for flag in ("archived", "private", "fork") if getattr(row, flag))
    if row.renamed_from:
        facts.append(f"renamed from {row.renamed_from}")
    if row.renamed_to:
        facts.append(f"renamed to {row.renamed_to}")
    if row.reason and row.classification != "UNREGISTERED":
        facts.append(row.reason)
    return f"{row.repository} ({', '.join(facts)})" if facts else row.repository


def summary_line(report: DiscoveryReport) -> str:
    counts = report.counts()
    return (
        f"discovery: {counts['REGISTERED']} registered, {counts['UNREGISTERED']} unregistered, "
        f"{counts['EXCLUDED_BY_POLICY']} excluded by policy, {counts['MISSING_UPSTREAM']} "
        f"missing upstream - {report.listed} listed in {len(report.organizations)} "
        f"organization(s)"
    )


def render_lines(report: DiscoveryReport, *, verbose: bool = True) -> list[str]:
    """The text report: a summary line, then (``verbose``) every non-registered repository."""
    lines = [summary_line(report)]
    if report.error is not None:
        lines.append(f"discovery incomplete: {report.error}")
    for item in report.incomplete_organizations:
        why = item.error or "listing truncated at the page cap"
        lines.append(f"discovery incomplete: {item.organization}: {why}")
    if verbose:
        for row in report.unregistered:
            lines.append(f"unregistered: {row_label(row)}")
        for row in report.missing_upstream:
            lines.append(f"missing upstream: {row_label(row)}: {row.detail}")
        for row in report.excluded:
            lines.append(f"excluded by policy: {row_label(row)}")
    return lines


def status_lines(
    admitted: int,
    report: DiscoveryReport | None,
    *,
    authorized_organizations: int,
    verbose: bool = False,
    note: str | None = None,
) -> list[str]:
    """``status``'s ``registry:`` line (and, ``verbose``, the repositories behind it).

    The denominator is ``admitted``, the registry's own size: discovery adds a line, never a
    number to the count.
    """
    if report is None:
        reason = note or "no monitor evidence; run `repository-presenter registry-gaps`"
        return [f"registry: {admitted} admitted; discovery not observed ({reason})"]
    counts = report.counts()
    line = (
        f"registry: {admitted} admitted; {counts['UNREGISTERED']} unregistered in authorized "
        "organizations"
    )
    if counts["UNREGISTERED"] and not verbose:
        line += " (list with --verbose)"
    if counts["MISSING_UPSTREAM"]:
        line += f"; {counts['MISSING_UPSTREAM']} admitted missing upstream"
    if counts["EXCLUDED_BY_POLICY"]:
        line += f"; {counts['EXCLUDED_BY_POLICY']} excluded by policy"
    problems = _incompleteness(report, authorized_organizations)
    if problems:
        line += f"; discovery incomplete ({problems})"
    line += f"; observed {report.observed_at}"
    lines = [line]
    if verbose:
        for row in report.unregistered:
            lines.append(f"  unregistered: {row_label(row)}")
        for row in report.missing_upstream:
            lines.append(f"  missing upstream: {row_label(row)}: {row.detail}")
        for row in report.excluded:
            lines.append(f"  excluded by policy: {row_label(row)}")
    return lines


def _incompleteness(report: DiscoveryReport, authorized_organizations: int) -> str:
    parts: list[str] = []
    if report.error is not None:
        parts.append(report.error)
    failed = report.incomplete_organizations
    if failed:
        parts.append(f"{len(failed)} organization(s) not fully listed")
    unobserved = authorized_organizations - len(report.organizations)
    if unobserved > 0 and report.error is None:
        parts.append(f"{unobserved} of {authorized_organizations} organizations not observed")
    return "; ".join(parts)


def registry_status_json(
    admitted: int, authorized_organizations: int, report: DiscoveryReport | None
) -> dict[str, Any]:
    """``status --json``'s additive ``registry`` key."""
    return {
        "admitted": admitted,
        "authorized_organizations": authorized_organizations,
        "discovery": None if report is None else report.to_json(),
    }


def _data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(value: str) -> str:
    return _data(value).replace(":", "%3A").replace(",", "%2C")


def _names(rows: Iterable[DiscoveryRow]) -> str:
    """Repository names for an annotation: a private repository's name is never published."""
    shown = [PRIVATE_NAME_WITHHELD if row.private else row.repository for row in rows]
    head = ", ".join(shown[:ANNOTATION_NAME_LIMIT])
    extra = len(shown) - ANNOTATION_NAME_LIMIT
    return f"{head} and {extra} more" if extra > 0 else head


def workflow_annotations(report: DiscoveryReport, *, authorized_organizations: int) -> list[str]:
    """GitHub Actions ``::warning`` lines: a finding is visible, never a red run."""
    lines: list[str] = []

    def warn(title: str, message: str) -> None:
        lines.append(f"::warning title={_property(title)}::{_data(message)}")

    unregistered = report.unregistered
    if unregistered:
        warn(
            "Repositories not in the registry",
            f"{len(unregistered)} repositor(ies) in authorized organizations are not in the "
            f"registry allow-list (admission is an owner act): {_names(unregistered)}",
        )
    missing = report.missing_upstream
    if missing:
        warn(
            "Admitted repositories missing upstream",
            f"{len(missing)} admitted repositor(ies) no longer exist upstream under their "
            f"admitted identity: {_names(missing)}",
        )
    problems = _incompleteness(report, authorized_organizations)
    if problems:
        failed = ", ".join(
            f"{item.organization} ({item.error or 'truncated'})"
            for item in report.incomplete_organizations
        )
        warn(
            "Registry discovery incomplete",
            problems + (f": {failed}" if failed else ""),
        )
    return lines


def _cell(value: str | None) -> str:
    return (value or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def summary_markdown(
    report: DiscoveryReport, *, admitted: int, authorized_organizations: int
) -> str:
    """The workflow summary block: the count, then a table of what needs an owner decision."""
    counts = report.counts()
    lines = [
        "### Registry discovery",
        "",
        f"{admitted} admitted; **{counts['UNREGISTERED']} unregistered** in authorized "
        f"organizations; {counts['EXCLUDED_BY_POLICY']} excluded by policy; "
        f"{counts['MISSING_UPSTREAM']} admitted missing upstream. "
        f"{report.listed} repositories listed in {len(report.organizations)} of "
        f"{authorized_organizations} authorized organizations. Discovery never admits: "
        "the registry is a hard allow-list and admission is an owner act.",
    ]
    problems = _incompleteness(report, authorized_organizations)
    if problems:
        lines += ["", f"Discovery incomplete: {_cell(problems)}"]
    if report.unregistered:
        lines += [
            "",
            "| Unregistered repository | Language | Last push | Notes |",
            "|---|---|---|---|",
        ]
        for row in report.unregistered:
            notes = ", ".join(
                [flag for flag in ("archived", "private", "fork") if getattr(row, flag)]
                + ([f"renamed from {row.renamed_from}"] if row.renamed_from else [])
            )
            name = PRIVATE_NAME_WITHHELD if row.private else row.repository
            lines.append(
                f"| {_cell(name)} | {_cell(row.language)} | {_cell((row.pushed_at or '')[:10])} "
                f"| {_cell(notes)} |"
            )
    if report.missing_upstream:
        lines += ["", "| Admitted repository missing upstream | Cause |", "|---|---|"]
        lines += [
            f"| {_cell(row.repository)} | {_cell(row.detail)} |" for row in report.missing_upstream
        ]
    return "\n".join(lines) + "\n"
