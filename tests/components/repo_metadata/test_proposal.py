"""Phase 1 proposal: description/topics/homepage derived only from already-verified facts, and the
diff against Phase 0's observation. Includes the negative control: an observation that already
matches the proposal has nothing to propose."""

from __future__ import annotations

from repository_presenter.components.repo_metadata.proposal import (
    build_proposal,
    diff_against_observed,
    opening_paragraph,
    propose_description,
    propose_homepage,
    propose_topics,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id

README_TEXT = """# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/)

[![Aspose.3D FOSS for Python](https://products.aspose.org/media/3d/python/banner-readme.png)](https://products.aspose.org/3d/python/)

Aspose.3D FOSS for Python is a Python library that enables developers to read, write, and convert \
3D documents in formats including `.obj` and `.stl`. It solves the problem of integrating 3D \
content processing into Python applications.

## Navigation

- [At a Glance](#at-a-glance)
"""


def _facts(*extra: Fact) -> FactsDocument:
    base = (
        Fact(
            fact_id("identity", "repository"),
            "identity",
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            (Evidence("registry", None),),
        ),
        Fact(fact_id("identity", "platform"), "identity", "python", (Evidence("registry", None),)),
        Fact(fact_id("identity", "family"), "identity", "3d", (Evidence("registry", None),)),
        Fact(fact_id("identity", "ecosystem"), "identity", "python", (Evidence("registry", None),)),
        Fact(fact_id("license", "spdx"), "license", "MIT", (Evidence("LICENSE", None),)),
    )
    return FactsDocument("aspose-3d-foss/Aspose.3D-FOSS-for-Python", "f" * 40, base + extra)


def _homepage_fact(polarity: str = "SUPPORTED") -> Fact:
    return Fact(
        fact_id("link_target", "product.homepage"),
        "link_target",
        "https://products.aspose.org/3d/python/",
        (Evidence("https://products.aspose.org/3d/python/", "HTTP 200"),),
        polarity=polarity,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# opening_paragraph / propose_description
# ---------------------------------------------------------------------------


def test_opening_paragraph_skips_the_h1_badges_and_banner_image() -> None:
    paragraph = opening_paragraph(README_TEXT)
    assert paragraph is not None
    assert paragraph.startswith("Aspose.3D FOSS for Python is a Python library")
    assert "PyPI" not in paragraph
    assert "banner-readme.png" not in paragraph


def test_opening_paragraph_is_none_without_an_h1() -> None:
    assert opening_paragraph("no heading here\n\njust text\n") is None


def test_opening_paragraph_is_none_when_only_badges_precede_the_first_section() -> None:
    text = "# Title\n\n[![badge](https://x/img.svg)](https://x/)\n\n## Navigation\n"
    assert opening_paragraph(text) is None


def test_propose_description_returns_the_first_sentence_backticks_stripped() -> None:
    description, source = propose_description(README_TEXT)
    assert description == (
        "Aspose.3D FOSS for Python is a Python library that enables developers to read, write, "
        "and convert 3D documents in formats including .obj and .stl."
    )
    assert source == "sealed README opening paragraph, first sentence"


def test_propose_description_none_when_no_readme_is_available() -> None:
    description, reason = propose_description(None)
    assert description is None
    assert reason is not None and "no sealed candidate" in reason


def test_propose_description_none_when_the_first_sentence_is_over_the_length_limit() -> None:
    long_sentence = "Aspose.3D FOSS for Python " + ("word " * 80) + "done."
    text = f"# Title\n\n{long_sentence}\n\n## Navigation\n"
    description, reason = propose_description(text)
    assert description is None
    assert reason is not None and "over the" in reason


# ---------------------------------------------------------------------------
# propose_topics
# ---------------------------------------------------------------------------


def test_propose_topics_derives_platform_family_license_and_static_labels() -> None:
    topics, sources = propose_topics(_facts())
    assert topics == ("python", "3d", "mit", "aspose", "foss")
    assert sources == ("identity:platform", "identity:family", "license:spdx")


def test_propose_topics_falls_back_to_ecosystem_when_platform_is_unresolved() -> None:
    facts = _facts()
    facts = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(f for f in facts.facts if f.id != "identity:platform"),
    )
    topics, sources = propose_topics(facts)
    assert "python" in topics
    assert "identity:ecosystem" in sources
    assert "identity:platform" not in sources


def test_propose_topics_ignores_unsupported_facts() -> None:
    facts = _facts()
    facts = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(
            f
            if f.id != "license:spdx"
            else Fact(f.id, f.kind, f.value, f.evidence, polarity="UNRESOLVED")
            for f in facts.facts
        ),
    )
    topics, sources = propose_topics(facts)
    assert "mit" not in topics
    assert "license:spdx" not in sources


# ---------------------------------------------------------------------------
# propose_homepage
# ---------------------------------------------------------------------------


def test_propose_homepage_reads_the_supported_product_homepage_fact() -> None:
    facts = _facts(_homepage_fact())
    homepage, source = propose_homepage(facts)
    assert homepage == "https://products.aspose.org/3d/python/"
    assert source == "link_target:product.homepage"


def test_propose_homepage_none_when_unresolved() -> None:
    facts = _facts(_homepage_fact(polarity="UNRESOLVED"))
    homepage, source = propose_homepage(facts)
    assert homepage is None
    assert source is None


def test_propose_homepage_none_when_absent() -> None:
    homepage, source = propose_homepage(_facts())
    assert homepage is None
    assert source is None


# ---------------------------------------------------------------------------
# diff_against_observed, including the negative control
# ---------------------------------------------------------------------------


def test_diff_negative_control_matching_observation_has_no_changes() -> None:
    """A repository whose GitHub-observed values already match the derived proposal: nothing to
    propose. This is the required negative control."""
    facts = _facts(_homepage_fact())
    proposed = build_proposal(facts, README_TEXT)
    diff = diff_against_observed(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        proposed,
        observed_description=proposed.description,
        observed_homepage=proposed.homepage,
        observed_topics=proposed.topics,
    )
    assert diff.has_changes is False
    assert diff.description_changed is False
    assert diff.homepage_changed is False
    assert diff.topics_changed is False


def test_diff_detects_a_changed_description_only() -> None:
    facts = _facts(_homepage_fact())
    proposed = build_proposal(facts, README_TEXT)
    diff = diff_against_observed(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        proposed,
        observed_description="an old, stale description",
        observed_homepage=proposed.homepage,
        observed_topics=proposed.topics,
    )
    assert diff.description_changed is True
    assert diff.homepage_changed is False
    assert diff.topics_changed is False
    assert diff.has_changes is True


def test_diff_topics_compares_as_a_set_order_is_not_a_change() -> None:
    facts = _facts(_homepage_fact())
    proposed = build_proposal(facts, README_TEXT)
    diff = diff_against_observed(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        proposed,
        observed_description=proposed.description,
        observed_homepage=proposed.homepage,
        observed_topics=tuple(reversed(proposed.topics)),
    )
    assert diff.topics_changed is False


def test_diff_never_flags_a_field_the_proposal_could_not_derive() -> None:
    """No sealed README, so description could not be proposed - the diff must not claim the
    observed description "changed" against a value that was never actually proposed."""
    facts = _facts()
    proposed = build_proposal(facts, readme_text=None)
    assert proposed.description is None
    diff = diff_against_observed(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        proposed,
        observed_description="whatever GitHub currently has",
        observed_homepage=None,
        observed_topics=(),
    )
    assert diff.description_changed is False
