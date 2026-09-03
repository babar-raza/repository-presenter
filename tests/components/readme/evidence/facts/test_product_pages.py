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


def _serve(monkeypatch: pytest.MonkeyPatch, live: set[str]) -> list[str]:
    asked: list[str] = []

    def fetch(url: str) -> tuple[int, str]:
        asked.append(url)
        return (200, url) if url in live else (404, url)

    monkeypatch.setattr(links, "fetch_status", fetch)
    return asked


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


def test_two_live_platform_variants_are_ambiguous_and_stay_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serve(
        monkeypatch,
        {"https://products.aspose.com/3d/python/", "https://products.aspose.com/3d/python-net/"},
    )
    target = product_page_facts(ENTRY)[0]
    assert target.polarity == "UNRESOLVED" and target.attributes is not None
    assert target.attributes["level"] == "ambiguous"
    assert "python, python-net" in (target.evidence[0].detail or "")
    assert enterprise_target([target]) is None


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
