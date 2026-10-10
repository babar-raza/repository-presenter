"""Live product-page facts: platform first, family fallback, ambiguity refused, nothing guessed."""

from __future__ import annotations

import httpx
import pytest

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    enterprise_target,
    product_page_facts,
)
from repository_presenter.core.registry.models import RegistryEntry

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)


def _serve(
    monkeypatch: pytest.MonkeyPatch, live: set[str], redirects: dict[str, str] | None = None
) -> list[str]:
    asked: list[str] = []
    moved = redirects or {}

    def fetch(url: str) -> tuple[int, str]:
        asked.append(url)
        final = moved.get(url, url)
        return (200, final) if (url in live or url in moved) else (404, url)

    monkeypatch.setattr(links, "fetch_status", fetch)
    return asked


def _entry(family: str, platform: str) -> RegistryEntry:
    return ENTRY.model_copy(update={"family": family, "platform": platform})


def test_a_single_live_platform_page_is_the_platform_level_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = _serve(
        monkeypatch,
        {
            "https://products.aspose.com/3d/python-net/",
            "https://products.aspose.org/3d/python/",
            "https://products.aspose.org/media/3d/python/banner-readme.png",
        },
    )
    facts = {fact.id: fact for fact in product_page_facts(ENTRY)}
    target = facts[ENTERPRISE_FACT_ID]
    assert target.polarity == "SUPPORTED"
    assert target.value == "https://products.aspose.com/3d/python-net/"
    assert target.attributes == {"role": "enterprise", "level": "platform", "platform": "python"}
    assert "slug python-net" in (target.evidence[0].detail or "")
    assert facts[HOMEPAGE_FACT_ID].polarity == "SUPPORTED"
    assert facts[BANNER_FACT_ID].polarity == "SUPPORTED"
    assert enterprise_target(tuple(facts.values())) is target
    assert asked[:4] == [
        "https://products.aspose.com/3d/python/",
        "https://products.aspose.com/3d/python-net/",
        "https://products.aspose.com/3d/python-cpp/",
        "https://products.aspose.com/3d/python-java/",
    ]


def test_the_products_own_live_slug_wins_over_other_live_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serve(
        monkeypatch,
        {"https://products.aspose.com/3d/python/", "https://products.aspose.com/3d/python-net/"},
    )
    target = product_page_facts(ENTRY)[0]
    assert (
        target.polarity == "SUPPORTED" and target.value == "https://products.aspose.com/3d/python/"
    )
    assert target.attributes is not None and target.attributes["level"] == "platform"


def test_a_curated_override_beats_the_slug_that_redirects_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Measured live 2026-10-10: cells/python/ lands on python-java, python-net is also 200."""
    base = "https://products.aspose.com/cells"
    _serve(
        monkeypatch,
        {f"{base}/python-net/", f"{base}/python-java/", f"{base}/"},
        {f"{base}/python/": f"{base}/python-java/"},
    )
    target = product_page_facts(_entry("cells", "python"))[0]
    assert target.polarity == "SUPPORTED" and target.value == f"{base}/python-net/"
    assert target.attributes == {"role": "enterprise", "level": "platform", "platform": "python"}
    assert "curated override" in (target.evidence[0].detail or "")


def test_an_override_whose_page_is_not_live_is_ignored_not_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = "https://products.aspose.com/cells"
    _serve(
        monkeypatch,
        {f"{base}/python-java/", f"{base}/"},
        {f"{base}/python/": f"{base}/python-java/"},
    )
    target = product_page_facts(_entry("cells", "python"))[0]
    assert target.value == f"{base}/python-java/"
    assert "curated override" not in (target.evidence[0].detail or "")


def test_an_override_that_itself_redirects_elsewhere_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = "https://products.aspose.com/cells"
    _serve(
        monkeypatch,
        {f"{base}/python/", f"{base}/"},
        {f"{base}/python-net/": f"{base}/python-java/"},
    )
    target = product_page_facts(_entry("cells", "python"))[0]
    assert target.value == f"{base}/python/"


def test_a_slug_that_redirects_names_its_destination_not_a_second_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """cells/go redirects to go-cpp; the override agrees, and an unknown product follows the
    redirect rather than seeing two live pages."""
    base = "https://products.aspose.com/zeta"
    _serve(monkeypatch, {f"{base}/go-cpp/", f"{base}/"}, {f"{base}/go/": f"{base}/go-cpp/"})
    target = product_page_facts(_entry("zeta", "go"))[0]
    assert target.value == f"{base}/go-cpp/"
    assert "go lands on it" in (target.evidence[0].detail or "")


def test_several_distinct_platform_pages_without_a_rule_fall_back_to_the_family_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = "https://products.aspose.com/zeta"
    _serve(monkeypatch, {f"{base}/python-net/", f"{base}/python-java/", f"{base}/"})
    target = product_page_facts(_entry("zeta", "python"))[0]
    assert target.polarity == "SUPPORTED" and target.value == f"{base}/"
    assert target.attributes is not None and target.attributes["level"] == "family"
    assert "ambiguous platform pages python-java, python-net" in (target.evidence[0].detail or "")


def test_a_redirect_out_of_the_family_tree_is_not_a_platform_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = "https://products.aspose.com/zeta"
    _serve(monkeypatch, {f"{base}/"}, {f"{base}/python/": "https://example.com/elsewhere/"})
    target = product_page_facts(_entry("zeta", "python"))[0]
    assert target.value == f"{base}/" and target.attributes is not None
    assert target.attributes["level"] == "family"


def test_override_rows_name_only_the_products_in_progress_with_live_evidence() -> None:
    from repository_presenter.components.readme.evidence.facts.product_pages import (
        ENTERPRISE_OVERRIDES,
        PLATFORM_SLUGS,
    )

    assert ENTERPRISE_OVERRIDES == {
        ("cells", "python"): "python-net",
        ("pdf", "python"): "python-net",
        ("cells", "go"): "go-cpp",
    }
    for (_family, platform), slug in ENTERPRISE_OVERRIDES.items():
        assert slug in PLATFORM_SLUGS[platform]


def test_the_family_page_is_the_fallback_and_nothing_live_stays_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serve(monkeypatch, {"https://products.aspose.com/3d/"})
    target = product_page_facts(ENTRY)[0]
    assert target.polarity == "SUPPORTED" and target.attributes is not None
    assert target.attributes["level"] == "family"
    assert target.value == "https://products.aspose.com/3d/"
    _serve(monkeypatch, set())
    facts = product_page_facts(ENTRY)
    assert [fact.polarity for fact in facts] == ["UNRESOLVED"] * 3
    assert facts[0].attributes is not None and facts[0].attributes["level"] == "unresolved"
    assert "HTTP 404" in (facts[0].evidence[0].detail or "")


def test_an_unreachable_host_is_recorded_not_guessed(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: str) -> tuple[int, str]:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(links, "fetch_status", refuse)
    facts = product_page_facts(ENTRY)
    assert all(fact.polarity == "UNRESOLVED" for fact in facts)
    assert "unreachable (ConnectError)" in (facts[1].evidence[0].detail or "")
