"""Live product-page facts: the Enterprise Edition target, the product homepage, and the banner.

docs/RESEARCH_AND_GUIDELINES.md section 20 adopts the resolution shape, not the data: one live
lookup per candidate, platform first (``products.aspose.com/{family}/{platform}/`` through the
portfolio's known platform slugs) and the family page as the fallback, classified platform,
family, or unresolved. Two live platform variants with no rule to pick between them are
ambiguous and stay unresolved rather than silently chosen. README_CONTRACT.md row 3 needs a
verified illustration and homepage for the banner, so the same lookup records the product
homepage on products.aspose.org and its banner image, each SUPPORTED only on a live 200.
Nothing here guesses: an unreachable page is recorded as unresolved with the status seen.
"""

from __future__ import annotations

import httpx

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.core.facts import Evidence, Fact, fact_id
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
    "node": ("nodejs", "nodejs-java", "nodejs-cpp"),
    "php": ("php", "php-java"),
}


def _status(url: str) -> tuple[int | None, str]:
    """The live status of ``url`` and the URL it resolved to; None when unreachable."""
    try:
        status, final = links.fetch_status(url)
    except httpx.HTTPError as exc:
        return None, type(exc).__name__
    return status, final


def _lookup(fact: str, url: str, role: str) -> Fact:
    status, final = _status(url)
    if status == 200:
        return Fact(
            fact,
            "link_target",
            url,
            (Evidence(url, f"HTTP 200; {role}; resolved to {final}"),),
            attributes={"role": role},
        )
    seen = f"HTTP {status}" if status is not None else f"unreachable ({final})"
    return Fact(
        fact,
        "link_target",
        url,
        (Evidence(url, f"{seen}; {role}"),),
        polarity="UNRESOLVED",
        confidence=0.5,
        attributes={"role": role},
    )


def enterprise_fact(entry: RegistryEntry) -> Fact:
    """The Enterprise Edition target: the one live platform page, else the family page, else
    unresolved; two live platform variants are ambiguous and unresolved."""
    slugs = PLATFORM_SLUGS.get(entry.platform, (entry.platform,))
    live: list[tuple[str, str]] = []
    seen: list[str] = []
    for slug in slugs:
        url = f"{ENTERPRISE_HOST}/{entry.family}/{slug}/"
        status, final = _status(url)
        seen.append(f"{slug}: {status if status is not None else final}")
        if status == 200:
            live.append((slug, url))
    if len(live) == 1:
        slug, url = live[0]
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            url,
            (Evidence(url, f"HTTP 200; enterprise target; platform level; slug {slug}"),),
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
    status, final = _status(family_url)
    if status == 200:
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            family_url,
            (
                Evidence(
                    family_url,
                    f"HTTP 200; enterprise target; family level; platform pages {'; '.join(seen)}",
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
                f"{'HTTP ' + str(status) if status is not None else final}; enterprise target; "
                f"platform pages {'; '.join(seen)}",
            ),
        ),
        polarity="UNRESOLVED",
        confidence=0.5,
        attributes={"role": "enterprise", "level": "unresolved"},
    )


def product_page_facts(entry: RegistryEntry) -> list[Fact]:
    """The three live product-page facts for the entry, each SUPPORTED only on a live 200."""
    homepage = f"{FOSS_HOST}/{entry.family}/{entry.platform}/"
    banner = f"{FOSS_HOST}/media/{entry.family}/{entry.platform}/banner-readme.png"
    return [
        enterprise_fact(entry),
        _lookup(HOMEPAGE_FACT_ID, homepage, "product homepage"),
        _lookup(BANNER_FACT_ID, banner, "banner illustration"),
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
