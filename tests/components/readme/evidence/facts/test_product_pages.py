"""Live product-page facts: platform first, family fallback, ambiguity refused, nothing guessed."""

from __future__ import annotations

import httpx
import pytest

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
    product_page_facts,
)
from repository_presenter.core.probes import ProbeRecord
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


def test_http_detail_goes_to_the_probe_record_and_never_into_hashed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-INV-02: a changed status or redirect with the same verdict changes no fact, so it
    reopens nothing; the status, final URL and timing are kept in the probe records."""
    live = {
        "https://products.aspose.com/3d/python-net/",
        "https://products.aspose.org/3d/python/",
        "https://products.aspose.org/media/3d/python/banner-readme.png",
    }

    def serve(status_of_gone: int, suffix: str) -> None:
        monkeypatch.setattr(
            links,
            "fetch_status",
            lambda url: (200, url + suffix) if url in live else (status_of_gone, url + suffix),
        )

    serve(404, "")
    probes_before: list[ProbeRecord] = []
    before = product_page_facts(ENTRY, probes_before)
    serve(410, "?moved")
    probes_after: list[ProbeRecord] = []
    after = product_page_facts(ENTRY, probes_after)
    assert before == after
    for fact in before:
        assert "HTTP" not in (fact.evidence[0].detail or "")
        assert "resolved to" not in (fact.evidence[0].detail or "")
    assert any("slug python-net" in (fact.evidence[0].detail or "") for fact in before)
    # The volatile detail is not lost: it is in the probes, which differ.
    assert {probe.status for probe in probes_before} == {200, 404}
    assert {probe.status for probe in probes_after} == {200, 410}
    assert all(probe.elapsed_ms is not None and probe.kind == "link" for probe in probes_after)
    assert any(probe.observation and probe.observation.endswith("?moved") for probe in probes_after)


def test_a_broken_page_still_leaves_the_fact_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    """The verdict survives the move: a non-200 homepage and banner are not SUPPORTED, so the
    banner is still omitted (banner_target) however the status is recorded."""
    _serve(monkeypatch, set())
    facts = {fact.id: fact for fact in product_page_facts(ENTRY)}
    assert facts[HOMEPAGE_FACT_ID].polarity == "UNRESOLVED"
    assert facts[HOMEPAGE_FACT_ID].evidence[0].detail == "BROKEN; product homepage"
    assert banner_target(tuple(facts.values())) is None


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
    assert (facts[0].evidence[0].detail or "").startswith("BROKEN; enterprise target")


def test_an_unreachable_host_is_recorded_not_guessed(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(url: str) -> tuple[int, str]:
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(links, "fetch_status", refuse)
    facts = product_page_facts(ENTRY)
    assert all(fact.polarity == "UNRESOLVED" for fact in facts)
    assert facts[1].evidence[0].detail == "UNCHECKED; product homepage"
