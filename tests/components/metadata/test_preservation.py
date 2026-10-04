"""Preservation rules: a maintainer-authored value is kept, a weak one is replaced, topics are
merged and never replaced. Each rule has a positive case and a negative control."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.components.metadata.preservation import (
    GITHUB_TOPIC_LIMIT,
    assess_description,
    assess_homepage,
    justified_topic_removals,
    merge_topics,
)
from repository_presenter.components.metadata.proposal import (
    ProposedRepoMetadata,
    build_proposal,
    diff_against_observed,
    diff_record,
    write_diff_record,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id

REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
PROPOSED_DESCRIPTION = "Aspose.3D FOSS for Python is a Python library that reads and writes STL."
STRONG = "Reads, writes and converts STL, OBJ and glTF 3D scenes without native dependencies."
README = f"# Aspose.3D FOSS for Python\n\n{PROPOSED_DESCRIPTION} More text.\n\n## Navigation\n"
_GITHUB_AUTOTEXT = (
    "Contribute to aspose-3d-foss/Aspose.3D-FOSS-for-Python development by creating an "
    "account on GitHub."
)


def _facts(platform: str = "python") -> FactsDocument:
    registry = (Evidence("registry", None),)
    return FactsDocument(
        REPO,
        "f" * 40,
        (
            Fact(fact_id("identity", "platform"), "identity", platform, registry),
            Fact(fact_id("identity", "family"), "identity", "3d", registry),
            Fact(fact_id("license", "spdx"), "license", "MIT", (Evidence("LICENSE", None),)),
            Fact(
                fact_id("link_target", "product.homepage"),
                "link_target",
                "https://products.aspose.org/3d/python/",
                (Evidence("https://products.aspose.org/3d/python/", "HTTP 200"),),
            ),
        ),
    )


def _proposal() -> ProposedRepoMetadata:
    return build_proposal(_facts(), README)


# ---------------------------------------------------------------------------
# description
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("observed", "rule"),
    [
        (None, "empty"),
        ("", "empty"),
        ("   \n", "empty"),
        ("Work in progress", "placeholder"),
        (_GITHUB_AUTOTEXT, "placeholder"),
        ("Aspose.3D-FOSS-for-Python", "bare_name_or_filler"),
        ("Aspose 3D FOSS for Python", "bare_name_or_filler"),
        ("aspose-3d-foss/Aspose.3D-FOSS-for-Python", "bare_name_or_filler"),
        ("A Python library.", "bare_name_or_filler"),
        ("TODO", "bare_name_or_filler"),
        ("Reads and writes STL files for the .NET platform.", "contradicted_by_verified_platform"),
        ("A C++ engine for scene graphs", "contradicted_by_verified_platform"),
    ],
)
def test_weak_descriptions_are_recognised_with_their_rule(observed: str | None, rule: str) -> None:
    verdict = assess_description(observed, REPO, "python")
    assert verdict.weak is True
    assert verdict.rule == rule


@pytest.mark.parametrize(
    "observed",
    [
        STRONG,
        "Python bindings for a Java scene-graph engine.",  # another platform AND the verified one
        "Fast STL parser",  # short, but every word carries content
        "Mesh toolkit",
    ],
)
def test_strong_descriptions_are_maintainer_authored(observed: str) -> None:
    verdict = assess_description(observed, REPO, "python")
    assert verdict.weak is False
    assert verdict.rule == "maintainer-authored"


def test_platform_contradiction_is_inactive_without_a_verified_platform() -> None:
    assert assess_description("Reads STL files for .NET", REPO, None).weak is False
    assert assess_description("Reads STL files for .NET", REPO, "klingon").weak is False


def test_strong_description_is_kept_not_replaced() -> None:
    diff = diff_against_observed(REPO, _proposal(), STRONG, None, ())
    assert diff.description_changed is False
    assert diff.description_decision.summary == "kept, maintainer-authored"
    assert diff.proposed.description == PROPOSED_DESCRIPTION  # still visible as advisory


def test_weak_description_is_replaced_with_the_rule_recorded() -> None:
    diff = diff_against_observed(REPO, _proposal(), "Aspose.3D-FOSS-for-Python", None, ())
    assert diff.description_changed is True
    assert diff.description_decision.summary == "replace (bare_name_or_filler)"


def test_empty_description_is_set() -> None:
    diff = diff_against_observed(REPO, _proposal(), None, None, ())
    assert diff.description_changed is True
    assert diff.description_decision.summary == "set (empty)"


def test_description_contradicting_the_verified_platform_is_replaced() -> None:
    diff = diff_against_observed(REPO, _proposal(), "Reads STL files for .NET", None, ())
    assert diff.description_changed is True
    assert diff.description_decision.rule == "contradicted_by_verified_platform"


# ---------------------------------------------------------------------------
# homepage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("observed", "rule"),
    [
        (None, "empty"),
        ("  ", "empty"),
        ("not a url", "invalid_url"),
        ("ftp://files.example.net/x", "invalid_url"),
        ("https://old/", "invalid_url"),
        ("https://example.com/", "reserved_placeholder_host"),
        ("https://old.example/", "reserved_placeholder_host"),
        ("http://localhost:8000", "reserved_placeholder_host"),
        ("https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python", "self_reference"),
        ("https://github.com/Aspose-3D-FOSS/aspose.3d-foss-for-python/", "self_reference"),
    ],
)
def test_weak_homepages_are_recognised(observed: str | None, rule: str) -> None:
    verdict = assess_homepage(observed, REPO)
    assert verdict.weak is True
    assert verdict.rule == rule


@pytest.mark.parametrize(
    "observed",
    [
        "https://docs.example-corp.io/stl/",
        "https://products.aspose.org/3d/net/",  # a live site, even if it is not the proposal
        "https://github.com/someone-else/other-repo",
        "https://myexample.com/",
    ],
)
def test_strong_homepages_are_maintainer_authored(observed: str) -> None:
    assert assess_homepage(observed, REPO).weak is False


def test_strong_homepage_is_kept_not_replaced() -> None:
    diff = diff_against_observed(REPO, _proposal(), STRONG, "https://docs.example-corp.io/", ())
    assert diff.homepage_changed is False
    assert diff.homepage_decision.summary == "kept, maintainer-authored"


def test_weak_homepage_is_replaced() -> None:
    diff = diff_against_observed(REPO, _proposal(), STRONG, "https://example.com/", ())
    assert diff.homepage_changed is True
    assert diff.homepage_decision.summary == "replace (reserved_placeholder_host)"


# ---------------------------------------------------------------------------
# topics: merge, never replace
# ---------------------------------------------------------------------------


def test_topics_are_merged_not_replaced() -> None:
    existing = ("stl-parser", "my-custom-tag", "python")
    diff = diff_against_observed(REPO, _proposal(), STRONG, None, existing)
    assert diff.topics_changed is True
    assert diff.final_topics[:3] == existing  # existing order and members survive
    assert set(diff.final_topics) == set(existing) | set(diff.proposed.topics)
    assert diff.topic_removals == ()


def test_topics_already_covering_the_proposal_are_unchanged_even_with_extras() -> None:
    """Negative control: the old rule saw 'differs' (maintainer extras) and replaced the set."""
    existing = (*_proposal().topics, "maintainer-extra")
    diff = diff_against_observed(REPO, _proposal(), STRONG, None, existing)
    assert diff.topics_changed is False
    assert diff.topics_decision.action == "unchanged"
    assert "maintainer-extra" in diff.final_topics


def test_merge_topics_never_truncates_existing_and_respects_the_github_cap() -> None:
    existing = tuple(f"t{i}" for i in range(GITHUB_TOPIC_LIMIT - 1))
    assert merge_topics(existing, ("x", "y", "z")) == (*existing, "x")
    full = tuple(f"t{i}" for i in range(GITHUB_TOPIC_LIMIT))
    assert merge_topics(full, ("x",)) == full


def test_merge_topics_dedupes() -> None:
    assert merge_topics(("a", "b"), ("b", "c", "a")) == ("a", "b", "c")


def test_a_contradicting_platform_topic_is_removed_only_with_a_cited_verified_fact() -> None:
    existing = ("java", "stl-parser", "python")
    diff = diff_against_observed(REPO, _proposal(), STRONG, None, existing)
    assert [r.topic for r in diff.topic_removals] == ["java"]
    removal = diff.topic_removals[0]
    assert removal.fact_id == "identity:platform"
    assert removal.fact_value == "python"
    assert "java" not in diff.final_topics
    assert "stl-parser" in diff.final_topics  # unrelated maintainer topic untouched


def test_no_removal_without_a_verified_platform() -> None:
    assert justified_topic_removals(("java", "rust"), None, None) == ()
    assert justified_topic_removals(("java",), "identity:platform", "klingon") == ()


def test_own_platform_topic_and_unrelated_topics_are_never_removed() -> None:
    removals = justified_topic_removals(
        ("python", "3d", "stl-parser"), "identity:platform", "python"
    )
    assert removals == ()


# ---------------------------------------------------------------------------
# audit record
# ---------------------------------------------------------------------------


def test_diff_record_records_existing_topics_decisions_and_removals(tmp_path: Path) -> None:
    existing = ("java", "stl-parser")
    diff = diff_against_observed(REPO, _proposal(), STRONG, None, existing)
    record = diff_record(diff)
    assert record["topics"]["existing"] == ["java", "stl-parser"]
    assert record["topics"]["removed"][0]["fact_id"] == "identity:platform"
    assert record["topics"]["final"] == list(diff.final_topics)
    assert record["description"]["decision"] == "kept, maintainer-authored"
    path = tmp_path / "out" / "record.json"
    digest = write_diff_record(diff, path)
    assert len(digest) == 64
    assert json.loads(path.read_text(encoding="utf-8")) == record
    assert write_diff_record(diff, path) == digest  # deterministic
