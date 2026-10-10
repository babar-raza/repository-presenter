"""Live product-page facts: the Enterprise Edition target, the product homepage, and the banner.

docs/RESEARCH_AND_GUIDELINES.md section 20 adopts the resolution shape, not the data: one live
lookup per candidate, platform first (``products.aspose.com/{family}/{platform}/`` through the
portfolio's known platform slugs) and the family page as the fallback, classified platform,
family, or unresolved. A curated override, then the product's own live slug, then one live
variant; several distinct live platform pages with no rule to pick between them fall back to the
family page rather than being silently chosen. README_CONTRACT.md row 3 needs a
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

# Curated Enterprise Edition platform pages, keyed (family, registry platform) -> slug. Ported
# for the products in progress from aspose.org's data/backlinks/platform_canonical_overrides.yaml
# (migration/reuse-manifest.yaml, record for that file): each is a designated canonical page,
# HTTP-verified live by the source when curated and re-verified live at every run here - an
# override whose page is not live at its own URL is ignored, never trusted. A row is added only
# for a repository being processed, with the evidence in its reuse record.
ENTERPRISE_OVERRIDES: dict[tuple[str, str], str] = {
    ("cells", "python"): "python-net",
    ("pdf", "python"): "python-net",
    ("cells", "go"): "go-cpp",
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


def _destination_slug(family: str, final: str) -> str | None:
    """The platform slug a probed URL finally landed on, or None when it left the family tree."""
    prefix = f"{ENTERPRISE_HOST}/{family}/"
    if not final.startswith(prefix):
        return None
    slug = final[len(prefix) :].split("?", 1)[0].strip("/")
    return slug if slug and "/" not in slug else None


def enterprise_fact(entry: RegistryEntry) -> Fact:
    """The Enterprise Edition target, in the order the portfolio's own link policy resolves it.

    1. A curated override (``ENTERPRISE_OVERRIDES``) whose page is live at its own URL: the
       portfolio's designated Enterprise page for that product, picked over what a bare slug
       redirects to.
    2. The product's own platform slug, live: the URL it finally lands on is the target (a
       slug that redirects to a bridge page such as ``go-cpp`` names that page, never a second
       candidate).
    3. Exactly one other live platform variant.
    4. The family page: always the fallback, including when several distinct platform pages are
       live and no rule picks between them (nothing is chosen, nothing is invented).
    5. Unresolved, recording the status seen.
    """
    slugs = PLATFORM_SLUGS.get(entry.platform, (entry.platform,))
    probed: dict[str, tuple[int | None, str]] = {}
    seen: list[str] = []
    for slug in slugs:
        status, final = _status(f"{ENTERPRISE_HOST}/{entry.family}/{slug}/")
        probed[slug] = (status, final)
        seen.append(f"{slug}: {status if status is not None else final}")

    def platform_level(url: str, how: str) -> Fact:
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            url,
            (Evidence(url, f"HTTP 200; enterprise target; platform level; {how}"),),
            attributes={"role": "enterprise", "level": "platform", "platform": entry.platform},
        )

    override = ENTERPRISE_OVERRIDES.get((entry.family, entry.platform))
    if override is not None:
        status, final = probed.get(override, (None, ""))
        if status == 200 and _destination_slug(entry.family, final) == override:
            return platform_level(
                f"{ENTERPRISE_HOST}/{entry.family}/{override}/",
                f"slug {override}; curated override, live",
            )
    own_status, own_final = probed[slugs[0]]
    if own_status == 200:
        landed = _destination_slug(entry.family, own_final)
        if landed is not None:
            suffix = "" if landed == slugs[0] else f"; {slugs[0]} lands on it"
            return platform_level(
                f"{ENTERPRISE_HOST}/{entry.family}/{landed}/", f"slug {landed}{suffix}"
            )
    distinct = sorted(
        {
            landed
            for status, final in probed.values()
            if status == 200 and (landed := _destination_slug(entry.family, final)) is not None
        }
    )
    if len(distinct) == 1:
        return platform_level(
            f"{ENTERPRISE_HOST}/{entry.family}/{distinct[0]}/", f"slug {distinct[0]}"
        )
    family_url = f"{ENTERPRISE_HOST}/{entry.family}/"
    status, final = _status(family_url)
    if status == 200:
        ambiguity = f"; ambiguous platform pages {', '.join(distinct)}" if distinct else ""
        return Fact(
            ENTERPRISE_FACT_ID,
            "link_target",
            family_url,
            (
                Evidence(
                    family_url,
                    f"HTTP 200; enterprise target; family level; platform pages "
                    f"{'; '.join(seen)}{ambiguity}",
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
