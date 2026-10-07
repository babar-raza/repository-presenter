"""The seven separated portfolio counts and the partition under them (plans/idea.md, Agile
operating model): one predicate per count, every live registry entry in exactly one bucket, and a
negative control for each way an entry fails to advance."""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.bundle.portfolio import (
    BUCKETS,
    COUNT_NAMES,
    FACT_CHECKS,
    PRESENTATION_CHECKS,
    RERUN_CHECK,
    REVIEW_CHECK,
    DriftObservation,
    assess_portfolio,
    current_reproducible_no_op_proven,
    load_authorizations,
    load_drift,
    render_lines,
)
from repository_presenter.components.readme.review.acceptance.profile import RATIFIED
from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS
from repository_presenter.core.authorization.proposal import authorize_proposal
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.loader import load_registry
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT, monitor_registry_entry

BRANCH = "repository-presenter/readme-update"
NOW = "2026-10-05T12:00:00Z"
LATER = "2026-10-06T12:00:00Z"
EARLIER = "2026-10-04T12:00:00Z"
README = "# Product\n\nA product.\n"
ALL_CHECKS = (*FACT_CHECKS, *PRESENTATION_CHECKS, REVIEW_CHECK, RERUN_CHECK)


def _entry(name: str, *, mode: str = "full", identifier: int = 1) -> RegistryEntry:
    repository = f"aspose-words-foss/Aspose.Words-FOSS-for-{name}"
    return RegistryEntry.model_validate(
        monitor_registry_entry(repository, mode=mode, repository_id=identifier)
    )


def _revision(entry: RegistryEntry) -> str:
    return hashlib.sha1(entry.repository.encode()).hexdigest()


def _seal(
    root: Path,
    entry: RegistryEntry,
    *,
    state: str = "READY_FOR_PROPOSAL",
    failing: tuple[str, ...] = (),
    review_verdict: str = "ACCEPT",
    no_op: dict[str, Any] | None = None,
    acceptance: dict[str, Any] | None = None,
) -> Path:
    """A real, integrity-valid bundle: every file listed in the manifest exists with its digest."""
    revision = _revision(entry)
    bundle = root / "candidates" / entry.repository.replace("/", "__") / revision
    bundle.mkdir(parents=True)
    review: dict[str, Any] = {"verdict": review_verdict}
    if acceptance is not None:
        review["acceptance_profile"] = acceptance
    files = {
        "README.md": README.encode(),
        "validation.json": json.dumps(
            {
                "source_revision": revision,
                "checks": [
                    {"id": check, "verdict": "FAIL" if check in failing else "PASS"}
                    for check in ALL_CHECKS
                ],
            }
        ).encode(),
        "review.json": json.dumps(review).encode(),
    }
    for name, data in files.items():
        (bundle / name).write_bytes(data)
    proof = (
        {"byte_identical": True, "fresh_process": True, "provider_calls": 0}
        if no_op is None
        else no_op
    )
    manifest = {
        "schema_version": 1,
        "repository": entry.repository,
        "revision": revision,
        "state": state,
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for name, data in files.items()
        },
        "no_op_proof": proof or None,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    return bundle


def _current(entry: RegistryEntry) -> dict[str, DriftObservation]:
    return {entry.repository: DriftObservation("CURRENT", _revision(entry))}


def _authorization(entry: RegistryEntry, *, expires_at: str = LATER, readme: str = README):
    return authorize_proposal(
        repository=entry.repository,
        candidate_hash=sha256_text(readme),
        source_revision=_revision(entry),
        base_branch="main",
        branch=BRANCH,
        approver="a-person",
        issued_at=EARLIER,
        expires_at=expires_at,
    )


PASSING = {"ratified": True, "outcome": "PASS"}


def _bucket(
    root: Path,
    entry: RegistryEntry,
    *,
    stale: tuple[str, ...] = (),
    drift: dict[str, DriftObservation] | None = None,
    authorizations: Any = None,
    ratified: bool = False,
) -> tuple[str, int]:
    report = assess_portfolio(
        root,
        [entry],
        stale_directories=stale,
        expected_branch=BRANCH,
        now=NOW,
        drift=drift,
        authorizations=authorizations,
        acceptance_ratified=ratified,
    )
    assessed = report.entries[0]
    return assessed.bucket, assessed.depth


def test_every_check_the_predicates_name_is_a_real_blocking_check() -> None:
    assert set(ALL_CHECKS) <= {check.id for check in BLOCKING_CHECKS}
    # No check is counted twice, and the two validity counts do not share one.
    assert len(set(ALL_CHECKS)) == len(ALL_CHECKS)
    assert len(BUCKETS) == len(set(BUCKETS))


def test_disabled_entry_never_advances_even_with_a_perfect_bundle(tmp_path: Path) -> None:
    entry = _entry("Python", mode="disabled")
    _seal(tmp_path, entry, acceptance=PASSING)
    assert _bucket(tmp_path, entry, drift=_current(entry), ratified=True) == ("disabled", 0)


def test_entry_with_no_bundle_is_no_bundle(tmp_path: Path) -> None:
    assert _bucket(tmp_path, _entry("Python")) == ("no_bundle", 0)


def test_corrupt_bundle_is_corrupt_not_counted(tmp_path: Path) -> None:
    entry = _entry("Python")
    bundle = _seal(tmp_path, entry)
    (bundle / "README.md").write_text("tampered", encoding="utf-8")
    assert _bucket(tmp_path, entry) == ("bundle_corrupt", 0)


def test_current_naming_a_missing_bundle_is_no_bundle(tmp_path: Path) -> None:
    entry = _entry("Python")
    pointer = tmp_path / "candidates" / entry.repository.replace("/", "__") / "CURRENT"
    pointer.parent.mkdir(parents=True)
    pointer.write_text("a" * 40, encoding="utf-8")
    assert _bucket(tmp_path, entry) == ("no_bundle", 0)


@pytest.mark.parametrize("state", ["INVALIDATED", "ACCEPTED", "SUPERSEDED"])
def test_a_non_ready_state_is_not_accepted(tmp_path: Path, state: str) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, state=state)
    assert _bucket(tmp_path, entry) == ("state_not_accepted", 0)


@pytest.mark.parametrize("check", FACT_CHECKS)
def test_any_failing_fact_check_is_not_fact_valid(tmp_path: Path, check: str) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, failing=(check,))
    assert _bucket(tmp_path, entry) == ("not_fact_valid", 0)


def test_a_failing_structure_check_is_fact_valid_but_not_presentation_valid(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, failing=PRESENTATION_CHECKS)
    assert _bucket(tmp_path, entry) == ("fact_valid", 1)


def test_valid_update_available_is_its_own_bucket_and_not_accepted(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, state="VALID_UPDATE_AVAILABLE")
    assert _bucket(tmp_path, entry, drift=_current(entry)) == ("update_available", 2)


def test_a_stale_ready_bundle_is_update_available_and_excluded_from_acceptance(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry)
    stale = (entry.repository.replace("/", "__"),)
    assert _bucket(tmp_path, entry, stale=stale, drift=_current(entry)) == ("update_available", 2)


def test_a_stale_ready_bundle_is_still_reported_as_ready_acceptance_advisory(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry)
    report = assess_portfolio(
        tmp_path,
        [entry],
        stale_directories=(entry.repository.replace("/", "__"),),
        expected_branch=BRANCH,
        now=NOW,
    )
    assert report.ready_acceptance_advisory == 1
    assert report.counts["independently_accepted"] == 0


def test_review_that_did_not_accept_stops_at_presentation_valid(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, review_verdict="REJECT_PRESENTATION")
    assert _bucket(tmp_path, entry) == ("presentation_valid", 2)
    other = _entry("Java", identifier=2)
    _seal(tmp_path, other, failing=(REVIEW_CHECK,))
    assert _bucket(tmp_path, other) == ("presentation_valid", 2)


@pytest.mark.parametrize(
    "proof",
    [
        {"byte_identical": False, "fresh_process": True, "provider_calls": 0},
        {"byte_identical": True, "fresh_process": False, "provider_calls": 0},
        {"byte_identical": True, "fresh_process": True, "provider_calls": 3},
        {"byte_identical": True, "fresh_process": True},
        {},
    ],
)
def test_no_op_proof_must_be_fresh_byte_identical_and_zero_call(
    tmp_path: Path, proof: dict[str, Any]
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, no_op=proof)
    assert _bucket(tmp_path, entry) == ("independently_accepted", 3)


def test_a_failing_rerun_check_is_not_no_op_proven(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, failing=(RERUN_CHECK,))
    assert _bucket(tmp_path, entry) == ("independently_accepted", 3)


def test_without_drift_evidence_freshness_is_unobserved_not_assumed(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    report = assess_portfolio(
        tmp_path,
        [entry],
        stale_directories=(),
        expected_branch=BRANCH,
        now=NOW,
        acceptance_ratified=True,
    )
    assert report.entries[0].bucket == "no_op_proven"
    assert report.counts["source_fresh"] is None
    assert report.counts["publication_eligible"] == 0
    assert report.source_freshness_observed is False


@pytest.mark.parametrize("status", ["DRIFTED", "NO_BUNDLE", "UNREACHABLE"])
def test_a_drift_observation_that_is_not_current_is_not_source_fresh(
    tmp_path: Path, status: str
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry)
    drift = {entry.repository: DriftObservation(status, _revision(entry))}
    assert _bucket(tmp_path, entry, drift=drift) == ("no_op_proven", 4)


def test_a_current_observation_of_a_different_bundle_revision_is_not_fresh(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry)
    drift = {entry.repository: DriftObservation("CURRENT", "b" * 40)}
    assert _bucket(tmp_path, entry, drift=drift) == ("no_op_proven", 4)
    assert _bucket(tmp_path, entry, drift={}) == ("no_op_proven", 4)


def test_dry_run_entry_stops_at_source_fresh_even_when_everything_else_holds(
    tmp_path: Path,
) -> None:
    entry = _entry("Python", mode="dry_run")
    _seal(tmp_path, entry, acceptance=PASSING)
    assert _bucket(tmp_path, entry, drift=_current(entry), ratified=True) == ("source_fresh", 5)


def test_ready_is_not_publication_eligible_while_the_profile_is_unratified(
    tmp_path: Path,
) -> None:
    """The load-bearing negative control: a full, fresh, no-op-proven READY_FOR_PROPOSAL bundle
    whose own record claims PASS is still not publication-eligible when the profile is not
    ratified - and is counted as ready but acceptance advisory."""
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    report = assess_portfolio(
        tmp_path,
        [entry],
        stale_directories=(),
        expected_branch=BRANCH,
        now=NOW,
        drift=_current(entry),
        authorizations={entry.repository: [_authorization(entry)]},
        acceptance_ratified=False,
    )
    assert report.entries[0].bucket == "source_fresh"
    assert report.counts["publication_eligible"] == 0
    assert report.counts["effect_authorized"] == 0
    assert report.ready_acceptance_advisory == 1


@pytest.mark.parametrize(
    "acceptance",
    [None, {"ratified": False, "outcome": "UNSCORED"}, {"ratified": True, "outcome": "FAIL"}],
)
def test_ratified_profile_still_needs_a_recorded_pass(
    tmp_path: Path, acceptance: dict[str, Any] | None
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=acceptance)
    assert _bucket(tmp_path, entry, drift=_current(entry), ratified=True) == ("source_fresh", 5)


def test_ratified_scored_fresh_full_candidate_is_publication_eligible_and_not_advisory(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    report = assess_portfolio(
        tmp_path,
        [entry],
        stale_directories=(),
        expected_branch=BRANCH,
        now=NOW,
        drift=_current(entry),
        acceptance_ratified=True,
    )
    assert report.entries[0].bucket == "publication_eligible"
    assert report.counts["publication_eligible"] == 1
    assert report.counts["effect_authorized"] == 0
    assert report.ready_acceptance_advisory == 0


def test_a_valid_authorization_makes_the_entry_effect_authorized(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    authorizations = {entry.repository: [_authorization(entry)]}
    assert _bucket(
        tmp_path, entry, drift=_current(entry), authorizations=authorizations, ratified=True
    ) == ("effect_authorized", 7)


@pytest.mark.parametrize("flaw", ["expired", "other_candidate", "other_repository"])
def test_an_authorization_that_does_not_bind_this_candidate_does_not_count(
    tmp_path: Path, flaw: str
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    if flaw == "expired":
        authorization = _authorization(entry, expires_at=EARLIER)
    elif flaw == "other_candidate":
        authorization = _authorization(entry, readme="# Another\n")
    else:
        authorization = _authorization(_entry("Java", identifier=2))
    authorizations = {entry.repository: [authorization]}
    assert _bucket(
        tmp_path, entry, drift=_current(entry), authorizations=authorizations, ratified=True
    ) == ("publication_eligible", 6)


def test_every_live_entry_is_in_exactly_one_bucket_and_counts_are_a_funnel(
    tmp_path: Path,
) -> None:
    """One registry exercising every bucket: the buckets partition it, their sum is the live
    entry count, each count is the number of entries that reached its depth, and the counts never
    grow along the funnel."""
    names = (
        "Python", "Java", "Go", "Rust", "Cpp", "Typescript", "NET", "Nodejs", "Javascript",
        "Disabled", "Missing", "Corrupt", "Invalid", "Update", "Stale", "Struct", "Review",
        "Proof", "Dry", "Eligible", "Authorized",
    )  # fmt: skip
    modes = {"Disabled": "disabled", "Dry": "dry_run"}
    entries = [
        _entry(name, mode=modes.get(name, "full"), identifier=i)
        for i, name in enumerate(names, start=1)
    ]
    by = {entry.repository.rsplit("-for-", 1)[1]: entry for entry in entries}

    for name in (
        "Python",
        "Java",
        "Go",
        "Rust",
        "Cpp",
        "Typescript",
        "NET",
        "Nodejs",
        "Javascript",
    ):
        _seal(tmp_path, by[name], acceptance=PASSING)  # ordinary READY bundles, no drift row
    _seal(tmp_path, by["Disabled"])
    corrupt = _seal(tmp_path, by["Corrupt"])
    (corrupt / "README.md").write_text("tampered", encoding="utf-8")
    _seal(tmp_path, by["Invalid"], failing=("BC-04",))
    _seal(tmp_path, by["Update"], state="VALID_UPDATE_AVAILABLE")
    _seal(tmp_path, by["Stale"])
    _seal(tmp_path, by["Struct"], failing=PRESENTATION_CHECKS)
    _seal(tmp_path, by["Review"], review_verdict="REJECT_PRESENTATION")
    _seal(tmp_path, by["Proof"], no_op={})
    _seal(tmp_path, by["Dry"], acceptance=PASSING)
    _seal(tmp_path, by["Eligible"], acceptance=PASSING)
    _seal(tmp_path, by["Authorized"], acceptance=PASSING)
    drift = {entry.repository: DriftObservation("CURRENT", _revision(entry)) for entry in entries}
    report = assess_portfolio(
        tmp_path,
        entries,
        stale_directories=(by["Stale"].repository.replace("/", "__"),),
        expected_branch=BRANCH,
        now=NOW,
        drift=drift,
        authorizations={by["Authorized"].repository: [_authorization(by["Authorized"])]},
        acceptance_ratified=True,
    )

    assert report.denominator == len(entries)
    assert sum(report.buckets.values()) == len(entries)
    assert set(report.buckets) == set(BUCKETS)
    assert sum(1 for a in report.entries if a.bucket in BUCKETS) == len(entries)
    assert len({a.repository for a in report.entries}) == len(entries)
    for position, name in enumerate(COUNT_NAMES, start=1):
        assert report.counts[name] == sum(1 for a in report.entries if a.depth >= position)
    series = [report.counts[name] for name in COUNT_NAMES]
    assert all(left >= right for left, right in pairwise(series))
    # Each deliberate case landed in its own place.
    landed = {a.repository.rsplit("-for-", 1)[1]: a.bucket for a in report.entries}
    assert landed["Disabled"] == "disabled"
    assert landed["Missing"] == "no_bundle"
    assert landed["Corrupt"] == "bundle_corrupt"
    assert landed["Invalid"] == "not_fact_valid"
    assert landed["Update"] == "update_available"
    assert landed["Stale"] == "update_available"
    assert landed["Struct"] == "fact_valid"
    assert landed["Review"] == "presentation_valid"
    assert landed["Proof"] == "independently_accepted"
    assert landed["Dry"] == "source_fresh"
    assert landed["Eligible"] == "publication_eligible"
    assert landed["Authorized"] == "effect_authorized"
    assert landed["Python"] == "publication_eligible"


def test_real_registry_and_candidates_partition_into_exactly_the_live_entry_count() -> None:
    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    report = assess_portfolio(
        REPO_ROOT,
        registry.entries,
        stale_directories=(),
        expected_branch=BRANCH,
        now=NOW,
    )
    assert report.denominator == len(registry.entries)
    assert sum(report.buckets.values()) == len(registry.entries)
    assert all(count >= 0 for count in report.buckets.values())
    # Honest by construction: nothing is publication-eligible while the profile is unratified.
    if not RATIFIED:
        assert report.counts["publication_eligible"] == 0
        assert report.counts["effect_authorized"] == 0
    # Disabled entries never advance.
    disabled = [e for e in registry.entries if e.mode == "disabled"]
    assert report.buckets["disabled"] == len(disabled)


def test_report_serializes_and_renders_all_seven_counts_and_the_denominator(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry)
    report = assess_portfolio(
        tmp_path, [entry], stale_directories=(), expected_branch=BRANCH, now=NOW
    )
    document = json.loads(json.dumps(report.to_json()))
    assert list(document["counts"]) == list(COUNT_NAMES)
    assert document["denominator"] == 1
    text = "\n".join(render_lines(report))
    for label in (
        "fact-valid",
        "presentation-valid",
        "independently accepted",
        "no-op-proven",
        "source-fresh unobserved",
        "publication-eligible",
        "effect-authorized",
        "1 live registry entries",
        "1 ready but acceptance advisory",
    ):
        assert label in text


def test_load_drift_reads_documents_and_a_non_current_row_wins(tmp_path: Path) -> None:
    def document(status: str) -> str:
        return json.dumps(
            {"repositories": [{"repository": "o/r", "status": status, "bundle_revision": "a" * 40}]}
        )

    (tmp_path / "one.json").write_text(document("CURRENT"), encoding="utf-8")
    (tmp_path / "two.json").write_text(document("DRIFTED"), encoding="utf-8")
    assert load_drift(tmp_path)["o/r"].status == "DRIFTED"
    assert load_drift(tmp_path / "one.json")["o/r"] == DriftObservation("CURRENT", "a" * 40)


def test_load_drift_and_authorizations_fail_closed_on_malformed_input(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_drift(bad)
    with pytest.raises(ConfigError):
        load_authorizations(bad)
    with pytest.raises(ConfigError):
        load_drift(tmp_path / "missing.json")
    bad.write_text(json.dumps({"repository": "o/r", "surprise": 1}), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_authorizations(bad)


def test_load_authorizations_accepts_an_object_a_list_and_a_directory(tmp_path: Path) -> None:
    entry = _entry("Python")
    record = _authorization(entry).model_dump(mode="json")
    (tmp_path / "a.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps([record, record]), encoding="utf-8")
    assert len(load_authorizations(tmp_path)[entry.repository]) == 3
    assert len(load_authorizations(tmp_path / "a.json")[entry.repository]) == 1


def _headline_report(root: Path, entry: RegistryEntry, *, stale: tuple[str, ...] = ()):
    return assess_portfolio(
        root,
        [entry],
        stale_directories=stale,
        expected_branch=BRANCH,
        now=NOW,
        drift=_current(entry),
    )


def test_headline_counts_a_current_accepted_no_op_proven_reproducible_bundle(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    report = _headline_report(tmp_path, entry)
    reproducible = {entry.repository.replace("/", "__")}
    assert current_reproducible_no_op_proven(report, reproducible) == 1
    # The funnel the headline sits above is the same report, read unchanged.
    assert report.counts["independently_accepted"] == 1
    assert report.counts["no_op_proven"] == 1


def test_headline_does_not_count_a_bundle_behind_the_running_code(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    directory = entry.repository.replace("/", "__")
    report = _headline_report(tmp_path, entry, stale=(directory,))
    assert current_reproducible_no_op_proven(report, {directory}) == 0
    assert report.counts["no_op_proven"] == 0


def test_headline_does_not_count_fact_valid_but_not_independently_accepted(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, review_verdict="REJECT_PRESENTATION", acceptance=PASSING)
    report = _headline_report(tmp_path, entry)
    directory = entry.repository.replace("/", "__")
    assert report.counts["fact_valid"] == 1
    assert report.counts["independently_accepted"] == 0
    assert current_reproducible_no_op_proven(report, {directory}) == 0


def test_headline_does_not_count_an_accepted_bundle_without_a_zero_call_proof(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(
        tmp_path, entry, no_op={"byte_identical": True, "fresh_process": True}, acceptance=PASSING
    )
    report = _headline_report(tmp_path, entry)
    assert current_reproducible_no_op_proven(report, {entry.repository.replace("/", "__")}) == 0


def test_headline_does_not_count_an_accepted_bundle_that_no_longer_reproduces(
    tmp_path: Path,
) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    report = _headline_report(tmp_path, entry)
    assert report.counts["no_op_proven"] == 1
    assert current_reproducible_no_op_proven(report, set()) == 0


def test_headline_with_no_registry_counts_nothing() -> None:
    assert current_reproducible_no_op_proven(None, {"owner__name"}) == 0


def test_funnel_lines_are_printed_unchanged_by_the_headline(tmp_path: Path) -> None:
    entry = _entry("Python")
    _seal(tmp_path, entry, acceptance=PASSING)
    report = _headline_report(tmp_path, entry)
    current_reproducible_no_op_proven(report, {entry.repository.replace("/", "__")})
    lines = render_lines(report)
    assert lines[0] == "portfolio: 1 live registry entries"
    assert lines[1] == (
        "  counts (cumulative, each of the previous): fact-valid 1, presentation-valid 1, "
        "independently accepted 1, no-op-proven 1, source-fresh 1, publication-eligible 0, "
        "effect-authorized 0"
    )
