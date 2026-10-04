"""Aspose-link ceilings derived per document, domain, and surface slot (plans/idea.md:
"Aspose-link density must adapt to the README rather than follow a universal quota")."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.composition.link_budget import (
    AUTOMATIC_TOTAL_CAP,
    ContentMeasurement,
    LinkAllocationPolicy,
    SlotCounter,
    classify_link,
    code_sha256,
    measure_content,
    plan_time_budget,
    resolve_link_budget,
    slot_violations,
)
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
    policy_packet,
)

DOCS = "https://docs.aspose.org/3d/python/"
KB = "https://kb.aspose.org/3d/python/"
REFERENCE = "https://reference.aspose.org/3d/python/"
BLOG = "https://blog.aspose.org/3d/"
PRODUCTS_COM = "https://products.aspose.com/3d/python-net/"


def _budget(words: int, examples: int = 0, cap: int = AUTOMATIC_TOTAL_CAP):
    return resolve_link_budget(ContentMeasurement(words, examples), None, cap)


def test_the_ceiling_grows_with_visible_content_and_verified_examples() -> None:
    assert _budget(100).max_total == 2
    assert _budget(700).max_total == 3
    assert _budget(1_500).max_total == 4
    # A verified example is worth 100 units: the same prose with examples earns more room.
    assert _budget(400, 0).max_total == 2
    assert _budget(400, 4).max_total == 3
    assert _budget(400, 9).max_total == 4


def test_the_automatic_total_never_exceeds_the_policy_cap() -> None:
    assert _budget(10_000, 20).max_total == AUTOMATIC_TOTAL_CAP == 4
    assert _budget(10_000, 20, cap=6).max_total == 6
    assert _budget(10_000, 20, cap=2).max_total == 2
    assert _budget(1_000, 0, cap=2).max_total == 2


def test_every_slot_is_a_ceiling_no_larger_than_the_total() -> None:
    small = _budget(100)
    assert small.max_total == 2
    assert all(small.surface_maxima[s] <= small.max_total for s in small.surface_maxima)
    assert small.surface_maxima["blog"] == 1
    assert small.domain_maxima["aspose.com"] == 1


def test_configured_maxima_replace_the_automatic_allocation() -> None:
    configured = LinkAllocationPolicy(
        max_total=6, aspose_org=5, aspose_com=1, products=1, docs=3, kb=3, blog=0, reference=3
    )
    budget = resolve_link_budget(ContentMeasurement(10, 0), configured)
    assert budget.mode == "configured"
    assert budget.max_total == 6  # above both the content tier and the automatic cap
    assert budget.surface_maxima["blog"] == 0
    assert slot_violations(budget, [BLOG]) == ["1 blog links exceed the blog slot ceiling of 0"]
    assert slot_violations(budget, [DOCS, DOCS, DOCS]) == []


@pytest.mark.parametrize("bad", [-1, True, 1.5])
def test_a_configured_maximum_must_be_a_non_negative_integer(bad: object) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        LinkAllocationPolicy(bad, 1, 1, 1, 1, 1, 1, 1)  # type: ignore[arg-type]


def test_links_are_classified_by_their_host() -> None:
    assert classify_link(DOCS) is not None and classify_link(DOCS).surface == "docs"  # type: ignore[union-attr]
    assert classify_link(PRODUCTS_COM).domain == "aspose.com"  # type: ignore[union-attr]
    assert classify_link("https://www.aspose.org/").surface is None  # type: ignore[union-attr]
    assert classify_link("https://aspose.app/x").domain is None  # type: ignore[union-attr]
    assert classify_link("https://github.com/aspose.com/x") is None
    assert classify_link("https://notaspose.org/") is None
    assert classify_link("relative/path.md") is None


def test_total_domain_and_surface_ceilings_are_each_enforced() -> None:
    budget = _budget(100)  # total 2, aspose.com 1, docs/kb/reference 2, blog 1
    assert slot_violations(budget, [DOCS, KB]) == []
    assert slot_violations(budget, [DOCS, KB, REFERENCE]) == [
        "3 Aspose links exceed the ceiling of 2",
        "3 aspose.org links exceed the aspose.org ceiling of 2",
    ]
    assert slot_violations(budget, [BLOG, BLOG]) == [
        "2 blog links exceed the blog slot ceiling of 1"
    ]
    assert slot_violations(budget, [PRODUCTS_COM, "https://docs.aspose.com/3d/"]) == [
        "2 aspose.com links exceed the aspose.com ceiling of 1"
    ]
    # Links that are not Aspose hosts never count.
    assert slot_violations(budget, ["https://github.com/a/b"] * 9) == []


def test_the_counter_admits_links_until_a_slot_is_full() -> None:
    counter = SlotCounter(_budget(100))
    assert counter.would_fit(BLOG)
    counter.add(BLOG)
    assert not counter.would_fit("https://blog.aspose.org/other/")  # blog slot is 1
    assert counter.would_fit(DOCS)
    counter.add(DOCS)
    assert not counter.would_fit(KB)  # total of 2 reached
    assert counter.would_fit("https://github.com/x/y")


def test_the_plan_stage_trims_to_the_largest_ceiling_the_policy_admits() -> None:
    assert plan_time_budget().max_total == 4
    assert plan_time_budget(None, 2).max_total == 2
    configured = LinkAllocationPolicy(3, 3, 1, 1, 1, 1, 1, 1)
    assert plan_time_budget(configured, 4).max_total == 3


def test_measure_counts_visible_prose_not_details_urls_or_mermaid() -> None:
    example = "print('hi')\n"
    readme = "\n".join(
        [
            "# Title",
            "",
            "One two three [four five](https://example.com/very/long/url) six.",
            "",
            "![alt text ignored](img.png)",
            "",
            "```python",
            example.rstrip(),
            "```",
            "",
            "```mermaid",
            "flowchart TD",
            "```",
            "",
            "<details>",
            "<summary>More</summary>",
            "",
            "hidden words that never count",
            "",
            "```python",
            example.rstrip(),
            "```",
            "",
            "</details>",
            "",
            "After the block two words.",
            "",
        ]
    )
    measured = measure_content(readme, [code_sha256(example)])
    assert measured.verified_examples == 2  # a verified fence counts wherever it sits
    # Words: "Title"(1) + "One two three four five six"(6) + "After the block two words"(5)
    assert measured.visible_prose_words == 12
    assert measure_content(readme, []).verified_examples == 0


def test_unconfigured_policy_packet_is_unchanged_and_configured_one_carries_the_maxima() -> None:
    baseline = policy_packet(DEFAULT_POLICY)
    assert "link_allocation" not in baseline
    assert baseline["aspose_links_max"] == 4
    configured = LinkAllocationPolicy(3, 3, 1, 1, 1, 1, 1, 1)
    packet = policy_packet(PlanningPolicy(link_allocation=configured))
    assert packet["aspose_links_max"] == 3
    assert packet["link_allocation"]["docs"] == 1
