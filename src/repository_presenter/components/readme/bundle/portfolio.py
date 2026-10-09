"""The portfolio report: plans/idea.md's seven separated counts, over the live registry.

``plans/idea.md`` (Agile operating model; ``docs/STATE_MACHINE.md`` section 3.1) says: "Portfolio
reporting separates fact-valid, presentation-valid, independently accepted, no-op-proven,
source-fresh, publication-eligible, and effect-authorized counts." This module is the one place
those seven predicates are defined; ``status`` prints and serializes them. It is a pure read: no
network, no provider call, no state change, no credential.

THE SEVEN PREDICATES (one entry, its CURRENT sealed bundle). They are CUMULATIVE: an entry counts
at a stage only when it counted at every stage before it, so the counts are a funnel,
``fact_valid >= presentation_valid >= ... >= effect_authorized``.

1. ``fact_valid``: registry mode is not ``disabled``; ``CURRENT`` names a bundle that passes
   ``verify_bundle`` and describes this repository at that revision; the manifest state is
   ``READY_FOR_PROPOSAL`` or ``VALID_UPDATE_AVAILABLE``; and ``validation.json`` records PASS for
   every factual/safety/protected-content blocking check (``FACT_CHECKS``) at the same source
   revision.
2. ``presentation_valid``: fact-valid, and ``validation.json`` records PASS for the structure check
   (``PRESENTATION_CHECKS``, BC-07).
3. ``independently_accepted``: presentation-valid, manifest state ``READY_FOR_PROPOSAL`` (not
   ``VALID_UPDATE_AVAILABLE``), not behind the running code's component/check versions (the same
   stale-excluded rule ``status``'s ``progress:`` line already applies), ``review.json`` verdict
   ``ACCEPT`` and the review check (BC-10) PASS.
4. ``no_op_proven``: independently accepted, the manifest's ``no_op_proof`` records a fresh-process,
   byte-identical replay with zero provider calls, and the rerun check (BC-11) is PASS.
5. ``source_fresh``: no-op-proven, and a supplied drift observation (``components/monitor``'s
   evidence document) says this repository's upstream head equals the bundle's revision. Freshness
   is a network fact this offline command cannot establish, so without a drift document the count is
   UNOBSERVED (``None``), never guessed, and the two counts after it are 0.
6. ``publication_eligible``: source-fresh, registry mode ``full`` (``dry_run`` is analysis only),
   the 30-point acceptance profile is RATIFIED and the sealed bundle scores the full 30 with no
   disqualifier triggered or unevaluated (the outcome ``PASS``), and the sealed README exists so
   the proposal payload's candidate hash is derivable. The score is recomputed here from the
   sealed README, ``validation.json`` and ``review.json`` plus the other current bundles as D14's
   template corpus (``review/acceptance/sealed.py``); a record stored in ``review.json`` by an
   older seal is not read, so no bundle needs a re-seal for the profile to apply.
7. ``effect_authorized``: publication-eligible, and a supplied authorization record for this
   repository passes ``validate_authorization`` against this exact bundle (candidate hash, source
   revision, presenter branch, unexpired). Records live under ``ops/proposal-authorizations/``;
   none is committed today, so on a plain checkout this is 0. The count is advisory: whether a
   record was merged before the run that uses it is checked by ``propose`` itself, not here.

THE PARTITION. Because the counts are nested, mutual exclusivity lives in the ``bucket`` of each
entry: the first of ``disabled``, ``no_bundle``, ``bundle_corrupt``, ``state_not_accepted``,
``not_fact_valid``, ``update_available`` that applies, otherwise the deepest of the seven stages the
entry reached. Every live registry entry is in exactly one bucket, so the buckets sum to the live
entry count (the denominator). Each count equals the number of entries whose depth reaches it.

``ready_acceptance_advisory`` is reported on its own: entries that are READY_FOR_PROPOSAL but whose
acceptance outcome is not a ratified PASS. READY_FOR_PROPOSAL is blocking checks BC-01..BC-11 plus
the no-op proof and is deliberately NOT gated on the 30-point score (OWNER-13, part two, is
unanswered), so such an entry stays READY and is never publication-eligible.

Ambiguities resolved conservatively are listed in the pull request that introduced this module as
owner questions; none changes a schema (``RegistryRevisionV1`` stays deferred).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.review.acceptance.profile import RATIFIED
from repository_presenter.components.readme.review.acceptance.scorer import PASS
from repository_presenter.components.readme.review.acceptance.sealed import (
    load_current_readmes,
    score_sealed_bundle,
)
from repository_presenter.core.authorization.proposal import (
    ProposalAuthorization,
    validate_authorization,
)
from repository_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    BundleError,
    verify_bundle,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.models import RegistryEntry

COUNT_NAMES: tuple[str, ...] = (
    "fact_valid",
    "presentation_valid",
    "independently_accepted",
    "no_op_proven",
    "source_fresh",
    "publication_eligible",
    "effect_authorized",
)
# Entries that cannot reach the funnel, in the order the partition tests them.
OFF_FUNNEL_BUCKETS: tuple[str, ...] = (
    "disabled",
    "no_bundle",
    "bundle_corrupt",
    "state_not_accepted",
    "not_fact_valid",
    "update_available",
)
BUCKETS: tuple[str, ...] = OFF_FUNNEL_BUCKETS + COUNT_NAMES
# depth = how many cumulative counts an entry reached; no-op-proven is reached at depth 4.
NO_OP_PROVEN_DEPTH = COUNT_NAMES.index("no_op_proven") + 1

# docs/README_CONTRACT.md section 5's checks, split the way docs/STATE_MACHINE.md section 9 splits
# defects: factual, safety and protected-content checks versus the presentation check. The docs do
# not map checks to the two counts explicitly; this is the conservative reading (a check whose
# class is arguable, BC-06 links, is required for the stricter fact count).
FACT_CHECKS: tuple[str, ...] = (
    "BC-01",  # source revision pinned, original bytes exact, every fact has evidence
    "BC-02",  # install command verified
    "BC-03",  # every rendered example executed or compiled
    "BC-04",  # every content unit cites supported facts
    "BC-05",  # every inherited unit has one disposition
    "BC-06",  # links resolve
    "BC-08",  # protected content preserved
    "BC-09",  # no secret in the bundle
)
PRESENTATION_CHECKS: tuple[str, ...] = ("BC-07",)  # structure
REVIEW_CHECK = "BC-10"
RERUN_CHECK = "BC-11"

STATE_READY = "READY_FOR_PROPOSAL"
STATE_UPDATE_AVAILABLE = "VALID_UPDATE_AVAILABLE"
CURRENT_DRIFT_STATUS = "CURRENT"  # components/monitor/drift.py Status

# (sealed bundle path, repository directory name) -> an acceptance record (scorer.score_candidate).
AcceptanceScorer = Callable[[Path, str], Mapping[str, Any]]


def sealed_acceptance_scorer(root: Path) -> AcceptanceScorer:
    """The production scorer: each bundle is scored live, with the other current bundles of
    ``root`` as D14's template corpus."""
    readmes = load_current_readmes(root)
    by_directory = {readme.directory: readme for readme in readmes}

    def score(bundle: Path, directory: str) -> Mapping[str, Any]:
        return score_sealed_bundle(bundle, by_directory.get(directory), readmes)

    return score


@dataclass(frozen=True)
class DriftObservation:
    """One repository's row from the monitor's drift evidence document."""

    status: str
    bundle_revision: str | None


@dataclass(frozen=True)
class EntryAssessment:
    """Where one registry entry stands. ``depth`` is how many of the seven counts it contributes
    to; ``bucket`` is its one place in the partition; ``reason`` says why it stopped."""

    repository: str
    mode: str
    bucket: str
    depth: int
    reason: str
    ready_acceptance_advisory: bool = False


@dataclass(frozen=True)
class PortfolioReport:
    denominator: int
    counts: Mapping[str, int | None]
    buckets: Mapping[str, int]
    ready_acceptance_advisory: int
    acceptance_ratified: bool
    source_freshness_observed: bool
    authorizations_supplied: bool
    entries: Sequence[EntryAssessment] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        return {
            "denominator": self.denominator,
            "counts": dict(self.counts),
            "buckets": dict(self.buckets),
            "ready_acceptance_advisory": self.ready_acceptance_advisory,
            "acceptance_ratified": self.acceptance_ratified,
            "source_freshness_observed": self.source_freshness_observed,
            "authorizations_supplied": self.authorizations_supplied,
            "entries": [
                {
                    "repository": entry.repository,
                    "mode": entry.mode,
                    "bucket": entry.bucket,
                    "depth": entry.depth,
                    "reason": entry.reason,
                }
                for entry in self.entries
            ],
        }


def assess_portfolio(
    root: Path,
    entries: Iterable[RegistryEntry],
    *,
    stale_directories: Collection[str],
    expected_branch: str,
    now: str,
    drift: Mapping[str, DriftObservation] | None = None,
    authorizations: Mapping[str, Sequence[ProposalAuthorization]] | None = None,
    acceptance_ratified: bool = RATIFIED,
    acceptance_scorer: AcceptanceScorer | None = None,
) -> PortfolioReport:
    """Assess every entry and total the seven counts and the partition."""
    if acceptance_scorer is None and acceptance_ratified:
        acceptance_scorer = sealed_acceptance_scorer(root)
    assessments = [
        _assess(
            root,
            entry,
            stale_directories=stale_directories,
            expected_branch=expected_branch,
            now=now,
            drift=drift,
            authorizations=authorizations,
            acceptance_ratified=acceptance_ratified,
            acceptance_scorer=acceptance_scorer,
        )
        for entry in entries
    ]
    counts: dict[str, int | None] = {
        name: sum(1 for a in assessments if a.depth >= position)
        for position, name in enumerate(COUNT_NAMES, start=1)
    }
    if drift is None:
        counts["source_fresh"] = None
    buckets = {name: sum(1 for a in assessments if a.bucket == name) for name in BUCKETS}
    return PortfolioReport(
        denominator=len(assessments),
        counts=counts,
        buckets=buckets,
        ready_acceptance_advisory=sum(1 for a in assessments if a.ready_acceptance_advisory),
        acceptance_ratified=acceptance_ratified,
        source_freshness_observed=drift is not None,
        authorizations_supplied=authorizations is not None,
        entries=tuple(assessments),
    )


def current_reproducible_no_op_proven(
    report: PortfolioReport | None, reproducible: Collection[str]
) -> int:
    """The honest headline count: entries that reach the no-op-proven stage (depth 4, which already
    requires a current, non-stale bundle, a valid fact and presentation check, an independent
    ACCEPT and a zero-call byte-identical no-op proof) AND whose CURRENT bundle still renders
    byte-identical under the running code (``reproducible``: repository directory names from
    ``reproducibility.reproducible_repositories``).

    None of the three is inferred from another: a stale bundle is never counted, a fact-valid bundle
    that is not independently accepted is never counted, and an accepted bundle that no longer
    reproduces is never counted. No report (no registry) counts nothing.
    """
    if report is None:
        return 0
    return sum(
        1
        for assessment in report.entries
        if assessment.depth >= NO_OP_PROVEN_DEPTH
        and assessment.repository.replace("/", "__") in reproducible
    )


def _assess(
    root: Path,
    entry: RegistryEntry,
    *,
    stale_directories: Collection[str],
    expected_branch: str,
    now: str,
    drift: Mapping[str, DriftObservation] | None,
    authorizations: Mapping[str, Sequence[ProposalAuthorization]] | None,
    acceptance_ratified: bool,
    acceptance_scorer: AcceptanceScorer | None,
) -> EntryAssessment:
    def stop(bucket: str, depth: int, reason: str, advisory: bool = False) -> EntryAssessment:
        return EntryAssessment(entry.repository, entry.mode, bucket, depth, reason, advisory)

    if entry.mode == "disabled":
        return stop("disabled", 0, "registry mode is disabled")
    directory = entry.repository.replace("/", "__")
    repository_path = root / CANDIDATES_DIRNAME / directory
    pointer = repository_path / CURRENT_FILENAME
    if not pointer.is_file():
        return stop("no_bundle", 0, "no CURRENT pointer")
    try:
        revision = pointer.read_text(encoding="utf-8").strip()
        bundle = repository_path / revision
        manifest = verify_bundle(bundle)
    except (BundleError, OSError, ValueError) as exc:
        return stop("bundle_corrupt", 0, f"CURRENT bundle fails verification: {exc}")
    if manifest is None:
        return stop("no_bundle", 0, f"CURRENT names {revision!r} with no sealed bundle")
    if manifest.get("revision") != revision or manifest.get("repository") != entry.repository:
        return stop("bundle_corrupt", 0, "bundle manifest does not describe this repository")
    state = manifest.get("state")
    if state not in (STATE_READY, STATE_UPDATE_AVAILABLE):
        return stop("state_not_accepted", 0, f"manifest state is {state}")

    validation = _read_object(bundle / "validation.json")
    verdicts = _verdicts(validation)
    if validation.get("source_revision") != revision or not _all_pass(verdicts, FACT_CHECKS):
        return stop("not_fact_valid", 0, "a factual/safety validation check is not PASS")
    depth = 1  # ``halt`` below reads the depth reached so far
    review = _read_object(bundle / "review.json")
    acceptance_pass = (
        acceptance_ratified
        and acceptance_scorer is not None
        and _acceptance_passed(acceptance_scorer(bundle, directory))
    )
    # READY_FOR_PROPOSAL without a ratified, scored full 30 is "ready but below the acceptance
    # profile": it stays READY whatever else holds (staleness, freshness, mode), and is never
    # publication-eligible.
    advisory = state == STATE_READY and not acceptance_pass

    def halt(bucket: str, reason: str) -> EntryAssessment:
        return stop(bucket, depth, reason, advisory)

    if not _all_pass(verdicts, PRESENTATION_CHECKS):
        return halt("fact_valid", "structure check is not PASS")
    depth = 2
    if state == STATE_UPDATE_AVAILABLE or directory in stale_directories:
        return halt("update_available", "an update is available or the bundle is stale")
    if review.get("verdict") != "ACCEPT" or not _all_pass(verdicts, (REVIEW_CHECK,)):
        return halt("presentation_valid", "no independent ACCEPT")
    depth = 3
    if not _no_op_proven(manifest) or not _all_pass(verdicts, (RERUN_CHECK,)):
        return halt("independently_accepted", "no byte-identical zero-call no-op proof")
    depth = 4

    observation = None if drift is None else drift.get(entry.repository)
    if observation is None:
        why = "source freshness not observed" if drift is None else "no drift observation"
        return halt("no_op_proven", why)
    if observation.status != CURRENT_DRIFT_STATUS or observation.bundle_revision != revision:
        return halt("no_op_proven", f"upstream is {observation.status}, not the bundle revision")
    depth = 5
    readme = bundle / "README.md"
    if entry.mode != "full":
        return halt("source_fresh", f"registry mode is {entry.mode}, not full")
    if not acceptance_pass:
        return halt("source_fresh", "the ratified 30-point acceptance is not scored PASS")
    try:
        candidate_hash = sha256_text(readme.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return halt("source_fresh", "sealed README is unreadable")
    depth = 6
    granted = any(
        validate_authorization(
            authorization,
            now=now,
            expected_repository=entry.repository,
            expected_candidate_hash=candidate_hash,
            expected_source_revision=revision,
            # The report is offline and cannot observe the target's live default branch; the
            # effect (components/propose/effect.py) binds the record's base branch to the live one.
            expected_base_branch=authorization.base_branch,
            expected_branch=expected_branch,
        ).granted
        for authorization in (authorizations or {}).get(entry.repository, ())
    )
    if not granted:
        return halt("publication_eligible", "no valid authorization record")
    depth = 7
    return halt("effect_authorized", "authorized")


def _read_object(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _verdicts(validation: Mapping[str, Any]) -> dict[str, Any]:
    checks = validation.get("checks")
    if not isinstance(checks, list):
        return {}
    return {str(c.get("id")): c.get("verdict") for c in checks if isinstance(c, dict)}


def _all_pass(verdicts: Mapping[str, Any], required: Sequence[str]) -> bool:
    return all(verdicts.get(check) == "PASS" for check in required)


def _no_op_proven(manifest: Mapping[str, Any]) -> bool:
    proof = manifest.get("no_op_proof")
    return (
        isinstance(proof, dict)
        and proof.get("byte_identical") is True
        and proof.get("fresh_process") is True
        and proof.get("provider_calls") == 0
    )


def _acceptance_passed(record: Mapping[str, Any]) -> bool:
    """The full 30, with no disqualifier triggered or unevaluated: scorer outcome PASS."""
    return record.get("ratified") is True and record.get("outcome") == PASS


def load_drift(path: Path) -> dict[str, DriftObservation]:
    """Read the monitor's drift evidence from a document or a directory of them.

    Where two documents disagree about one repository, the observation that is not ``CURRENT``
    wins: a freshness claim needs every source to agree.
    """
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files or not all(file.is_file() for file in files):
        raise ConfigError(f"drift evidence not found: {path}")
    observed: dict[str, DriftObservation] = {}
    for file in files:
        try:
            rows = json.loads(file.read_text(encoding="utf-8"))["repositories"]
            for row in rows:
                incoming = DriftObservation(str(row["status"]), row.get("bundle_revision"))
                prior = observed.get(str(row["repository"]))
                if prior is None or prior.status == CURRENT_DRIFT_STATUS:
                    observed[str(row["repository"])] = incoming
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ConfigError(f"drift evidence is malformed: {file}: {exc}") from exc
    return observed


def load_authorizations(path: Path) -> dict[str, list[ProposalAuthorization]]:
    """Read authorization records: a JSON object, a list of them, or a directory of such files."""
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files or not all(file.is_file() for file in files):
        raise ConfigError(f"authorization records not found: {path}")
    records: dict[str, list[ProposalAuthorization]] = {}
    for file in files:
        try:
            loaded = json.loads(file.read_text(encoding="utf-8"))
            for row in loaded if isinstance(loaded, list) else [loaded]:
                authorization = ProposalAuthorization(**row)
                records.setdefault(authorization.repository, []).append(authorization)
        except (OSError, ValueError, TypeError) as exc:
            raise ConfigError(f"authorization record is malformed: {file}: {exc}") from exc
    return records


def render_lines(report: PortfolioReport) -> list[str]:
    """The plain-text rendering ``status`` prints."""
    labels = {
        "fact_valid": "fact-valid",
        "presentation_valid": "presentation-valid",
        "independently_accepted": "independently accepted",
        "no_op_proven": "no-op-proven",
        "source_fresh": "source-fresh",
        "publication_eligible": "publication-eligible",
        "effect_authorized": "effect-authorized",
    }
    parts = []
    for name in COUNT_NAMES:
        value = report.counts[name]
        shown = "unobserved (no --drift)" if value is None else str(value)
        parts.append(f"{labels[name]} {shown}")
    advisory = (
        f"{report.ready_acceptance_advisory} ready but below the full 30-point acceptance "
        f"(profile {'ratified' if report.acceptance_ratified else 'not ratified'}; "
        "READY_FOR_PROPOSAL is not gated on it, publication eligibility is)"
    )
    buckets = ", ".join(f"{name} {report.buckets[name]}" for name in BUCKETS)
    return [
        f"portfolio: {report.denominator} live registry entries",
        "  counts (cumulative, each of the previous): " + ", ".join(parts),
        f"  {advisory}",
        f"  partition (each entry in exactly one): {buckets}",
    ]
