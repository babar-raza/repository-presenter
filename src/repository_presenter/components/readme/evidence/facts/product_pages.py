"""Live product-page facts: the Enterprise Edition target, the product homepage, and the banner.

docs/RESEARCH_AND_GUIDELINES.md section 20 adopts the resolution shape, not the data: one live
lookup per candidate, platform first (``products.aspose.com/{family}/{platform}/`` through the
portfolio's known platform slugs) and the family page as the fallback, classified platform,
family, or unresolved. Two live platform variants with no rule to pick between them are
ambiguous and stay unresolved rather than silently chosen. README_CONTRACT.md row 3 needs a
verified illustration and homepage for the banner, so the same lookup records the product
homepage on products.aspose.org and its banner image, each SUPPORTED only on a live 200.
Nothing here guesses: an unreachable page is recorded as unresolved.

A fact's evidence is hashed into dependencies.json, so it carries only a verdict word per page
(RESOLVED, BROKEN or UNCHECKED); the HTTP status, the final URL after redirects and the time the
read took go to a ProbeRecord (``core/probes.py``, sealed unhashed as probes.json), so a changed
status with the same verdict reopens nothing (TC-INV-02).
"""

from __future__ import annotations

import time

import httpx

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.core.facts import Evidence, Fact, fact_id
from repository_presenter.core.probes import ProbeRecord
from repository_presenter.core.registry.models import RegistryEntry

ENTERPRISE_FACT_ID = fact_id("link_target", "product.enterprise")
HOMEPAGE_FACT_ID = fact_id("link_target", "product.homepage")
BANNER_FACT_ID = fact_id("link_target", "product.banner")
ENTERPRISE_HOST = "https://products.aspose.com"
FOSS_HOST = "https://products.aspose.org"
# Platform slugs the portfolio publishes for each registry platform, the registry's own slug
# first; bridge slugs (python-net, go-cpp) are real, documented product pages (section 20).
PLATFORM_SLUGS: dict[str, tuple[str, ...]] = {
    "python": ("python", "python-net", "python-cpp", "python-java"),
    "net": ("net",),
    "java": ("java",),
    "cpp": ("cpp",),
    "go": ("go", "go-cpp"),
    "rust": ("rust", "rust-cpp"),
    "nodejs": ("nodejs", "nodejs-java", "nodejs-cpp"),
    "php": ("php", "php-java"),
}


def _verdict(status: int | None) -> str:
    """The verdict word a fact's evidence carries: RESOLVED on a live 200, BROKEN on any other
    answer, UNCHECKED when there was none."""
    if status is None:
        return "UNCHECKED"
    return "RESOLVED" if status == 200 else "BROKEN"


def _status(url: str, probes: list[ProbeRecord]) -> tuple[int | None, str]:
    """The live status of ``url`` and the URL it resolved to (the error name when unreachable,
    status None); the read is recorded in ``probes`` with its status and duration."""
    started = time.monotonic()
    try:
        status, final = links.fetch_status(url)
    except httpx.HTTPError as exc:
        status, final = None, type(exc).__name__
    probes.append(
        ProbeRecord(
            "link",
            url,
            _verdict(status),
            status=status,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            observation=final,
        )
    )
    return status, final


def _lookup(fact: str, url: str, role: str, probes: list[ProbeRecord]) -> Fact:
    status, _ = _status(url, probes)
    verdict = _verdict(status)
    if status == 200:
        return Fact(
            fact,
            "link_target",
            url,
            (Evidence(url, f"{verdict}; {role}"),),
            attributes={"role": role},
        )
    return Fact(
        fact,
        "link_target",
        url,
        (Evidence(url, f"{verdict}; {role}"),),
        polarity="UNRESOLVED",
        confidence=0.5,
        attributes={"role": role},
    )


def enterprise_fact(entry: RegistryEntry, probes: list[ProbeRecord]) -> Fact:
    """The Enterprise Edition target: the one live platform page, else the family page, else
    unresolved; two live platform variants are ambiguous and unresolved."""
    slugs = PLATFORM_SLUGS.get(entry.platform, (entry.platform,))
    live: list[tuple[str, str]] = []
    seen: list[str] = []
    for slug in slugs:
        url = f"{ENTERPRISE_HOST}/{entry.family}/{slug}/"
        status, _ = _status(url, probes)
        seen.append(f"{slug}: {_verdict(status)}")
        if status == 200:
            live.append((slug, url))
    if len(live) == 1:
        slug, url = live[0]
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            url,
            (Evidence(url, f"RESOLVED; enterprise target; platform level; slug {slug}"),),
            attributes={"role": "enterprise", "level": "platform", "platform": entry.platform},
        )
    if len(live) > 1:
        variants = ", ".join(slug for slug, _ in live)
        url = f"{ENTERPRISE_HOST}/{entry.family}/"
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            url,
            (Evidence(url, f"ambiguous platform targets: {variants}; enterprise target"),),
            polarity="UNRESOLVED",
            confidence=0.5,
            attributes={"role": "enterprise", "level": "ambiguous"},
        )
    family_url = f"{ENTERPRISE_HOST}/{entry.family}/"
    status, _ = _status(family_url, probes)
    if status == 200:
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            family_url,
            (
                Evidence(
                    family_url,
                    f"RESOLVED; enterprise target; family level; platform pages {'; '.join(seen)}",
                ),
            ),
            attributes={"role": "enterprise", "level": "family"},
        )
    return Fact(
        ENTERPRISE_FACT_ID,
        "link_target",
        family_url,
        (
            Evidence(
                family_url,
                f"{_verdict(status)}; enterprise target; platform pages {'; '.join(seen)}",
            ),
        ),
        polarity="UNRESOLVED",
        confidence=0.5,
        attributes={"role": "enterprise", "level": "unresolved"},
    )


def product_page_facts(entry: RegistryEntry, probes: list[ProbeRecord] | None = None) -> list[Fact]:
    """The three live product-page facts for the entry, each SUPPORTED only on a live 200.

    Every page read is appended to ``probes`` when given (status, final URL, duration), so the
    caller can seal it unhashed; the facts carry the verdict only."""
    probes = [] if probes is None else probes
    homepage = f"{FOSS_HOST}/{entry.family}/{entry.platform}/"
    banner = f"{FOSS_HOST}/media/{entry.family}/{entry.platform}/banner-readme.png"
    return [
        enterprise_fact(entry, probes),
        _lookup(HOMEPAGE_FACT_ID, homepage, "product homepage", probes),
        _lookup(BANNER_FACT_ID, banner, "banner illustration", probes),
    ]


def enterprise_target(facts: tuple[Fact, ...] | list[Fact]) -> Fact | None:
    """The SUPPORTED Enterprise Edition target fact, or None when unresolved or absent."""
    for fact in facts:
        if fact.id == ENTERPRISE_FACT_ID and fact.polarity == "SUPPORTED":
            return fact
    return None


def banner_target(facts: tuple[Fact, ...] | list[Fact]) -> tuple[Fact, Fact] | None:
    """The SUPPORTED banner illustration and homepage facts (README_CONTRACT.md row 3), or None
    when either is unresolved: the banner is then omitted entirely, never unlinked or broken."""
    supported = {fact.id: fact for fact in facts if fact.polarity == "SUPPORTED"}
    banner = supported.get(BANNER_FACT_ID)
    homepage = supported.get(HOMEPAGE_FACT_ID)
    if banner is None or homepage is None:
        return None
    return banner, homepage
