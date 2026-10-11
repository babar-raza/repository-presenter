"""A live README's warning that the registry lags the source is a claim the facts can verify, so
omitting it as "contradicted" is refused (wave-3 acceptance review, Slides-Python)."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme.evidence.facts.registry_lag import REGISTRY_LAG_FACT_ID
from repository_presenter.components.readme.reconciliation.dispositions import (
    OMIT_VERSION_SKEW,
    coverage_findings,
    is_version_skew_warning,
    placement_errors,
)
from repository_presenter.components.readme.validation.deferrals import review_deferrals
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

WARNING = (
    "**The PyPI release predates the source tree behind this page.** `pip install` gets "
    "`26.8.0`, and the changes listed in CHANGELOG.md under `## [Unreleased]` are not in that "
    "release. For the behaviour described here, install from the repository instead:"
)
UNIT = "inherited_unit:016.paragraph"


def _fact(fact_id: str, kind: str, value: str) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", "x"),))  # type: ignore[arg-type]


def _facts(lag: bool, text: str = WARNING) -> FactsDocument:
    facts = [
        _fact("package:version", "package", "26.8.0"),
        _fact("package:published_version", "package", "26.8.0"),
        _fact(UNIT, "inherited_unit", text),
    ]
    if lag:
        facts.append(
            Fact(
                REGISTRY_LAG_FACT_ID,
                "package",
                "26.8.0",
                (Evidence("CHANGELOG.md", "`## [Unreleased]` lists 2 entries"),),
            )
        )
    return FactsDocument("org/repo", "a" * 40, tuple(facts))


def _omitted() -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": UNIT,
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": ["package:version", "package:published_version"],
                "rationale": "Contradicted by package:version and package:published_version "
                "both being 26.8.0.",
            }
        ]
    }


def test_the_warning_is_recognised_by_a_lag_word_and_a_release_word() -> None:
    assert is_version_skew_warning(WARNING)
    assert is_version_skew_warning("> **The latest release on PyPI predates this page.**")
    assert is_version_skew_warning("Features marked unreleased are not in the published package.")
    # Negative controls: a release or changelog merely mentioned, or a lag word with no release.
    assert not is_version_skew_warning("See CHANGELOG.md for the release notes of each version.")
    assert not is_version_skew_warning("Install the published package from PyPI.")
    assert not is_version_skew_warning("The docs lag behind the code.")


def test_omitting_a_verified_skew_warning_is_refused_even_with_citations() -> None:
    [gap] = coverage_findings(_omitted(), _facts(lag=True))
    assert (gap.unit_id, gap.reason) == (UNIT, OMIT_VERSION_SKEW)
    assert "CHANGELOG.md: `## [Unreleased]` lists 2 entries" in gap.detail
    [error] = placement_errors(_omitted(), _facts(lag=True))
    assert error.startswith(f"{UNIT}: supported_omission: ")
    assert "into scope_limitations" in error and "predates the source tree" in error


def test_the_same_omission_stands_when_no_fact_verifies_the_lag() -> None:
    """Control: without ``package:registry_lag`` (versions agree, the changelog is quiet) the
    model's cited omission is the existing rule's to judge, and nothing here refuses it."""
    assert coverage_findings(_omitted(), _facts(lag=False)) == []
    assert placement_errors(_omitted(), _facts(lag=False)) == []


def test_keeping_the_warning_is_not_refused() -> None:
    kept = _omitted()
    kept["dispositions"][0].update(
        disposition="VERIFIED_PRESERVE", destination_section="scope_limitations"
    )
    assert coverage_findings(kept, _facts(lag=True)) == []
    assert placement_errors(kept, _facts(lag=True)) == []


def test_deferring_the_warning_as_no_evidence_either_way_blocks_once_the_lag_is_a_fact() -> None:
    deferred = _omitted()
    deferred["dispositions"][0].update(
        disposition="DEFER_UNRESOLVED",
        fact_ids=[],
        rationale="The claim is uncertain; no fact settles it.",
    )
    [finding] = review_deferrals(deferred, _facts(lag=True))
    assert (finding.class_id, finding.decision, finding.stage) == (
        "UNCLASSIFIED",
        "BLOCK",
        "RECONCILING",
    )
    [still] = review_deferrals(deferred, _facts(lag=False))
    assert (still.class_id, still.decision) == ("NO_EVIDENCE_EITHER_WAY", "ADVISORY")
