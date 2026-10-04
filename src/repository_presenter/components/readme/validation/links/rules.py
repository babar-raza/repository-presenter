"""The pure rules behind BC-06's link ceilings and Enterprise anchor and BC-07's badge row.

Each function takes plain values and returns the problems it finds as sentences; the checks in
``registry.py`` wrap them as routed failures. Nothing here reads a file, the network, or a clock.

The rules, each with the ``plans/idea.md`` line it enforces:

* Aspose-link ceilings: "Otherwise the system derives conservative maxima deterministically from
  the README's visible content size and verified code examples. Every slot is a ceiling, not a
  target" (``composition/link_budget.py`` derives them; ``readme_link_budget`` measures the
  rendered document).
* Enterprise anchor: "Aspose.com product links use natural explanatory prose and an informative
  full-featured ... Enterprise Edition anchor below the fold."
* Badge row: "one compact badge row in a stable order: package or release, platform/runtime, real
  build status, license, then contributors when those slots are supported. Badges may be omitted
  when their claims or targets are unavailable, but they may not be duplicated, split across
  multiple header rows, or fabricated merely to fill the row."
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from repository_presenter.components.readme.composition.link_budget import (
    LinkBudget,
    code_sha256,
    measure_content,
    resolve_link_budget,
)
from repository_presenter.components.readme.composition.policy import PlanningPolicy
from repository_presenter.components.readme.composition.renderer import BADGE_ORDER
from repository_presenter.core.facts import FactsDocument

# The markers an example fact's evidence carries once it has actually run (BC-03's own list).
EXECUTION_MARKERS = (": EXECUTED", ": COMPILED")
_BADGE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\)")
_IMAGE_URL = re.compile(r"!\[[^\]]*\]\(([^)\s]*)")
_ANCHOR = re.compile(r"^full-featured \S.* — Enterprise Edition$")


def verified_example_hashes(facts: FactsDocument) -> set[str]:
    """The normalized digests of every example that actually ran at this revision."""
    return {
        code_sha256(fact.value)
        for fact in facts.by_kind("example")
        if fact.polarity == "SUPPORTED"
        and any(
            marker in (evidence.detail or "")
            for evidence in fact.evidence
            for marker in EXECUTION_MARKERS
        )
    }


def readme_link_budget(readme: str, facts: FactsDocument, policy: PlanningPolicy) -> LinkBudget:
    """The exact per-slot Aspose-link ceilings of this rendered document."""
    return resolve_link_budget(
        measure_content(readme, verified_example_hashes(facts)),
        policy.link_allocation,
        policy.aspose_links_max,
    )


def badge_slot(token: str) -> str | None:
    """The slot a rendered badge occupies, read off its image URL; ``None`` when unrecognized."""
    match = _IMAGE_URL.search(token)
    if match is None:
        return None
    url = match.group(1)
    if "/actions/workflows/" in url and url.split("?", 1)[0].endswith("/badge.svg"):
        return "build"
    if "img.shields.io/github/contributors" in url:
        return "contributors"
    if "img.shields.io/badge/License-" in url:
        return "license"
    if "img.shields.io/badge/" in url:
        return "runtime"
    if url.startswith("https://"):
        return "package"
    return None


def badge_problems(row: str, expected: Sequence[tuple[str, str]]) -> list[str]:
    """Why the badge ``row`` breaks the contract, against the badges the facts support.

    ``expected`` is what the renderer derives from verified facts, ``(slot, markdown)`` in
    ``BADGE_ORDER``. A badge may be missing (omission is allowed); it may not repeat a slot, sit
    out of order, or differ from the supported badge for its slot, because a badge no fact
    supports is a fabricated one.
    """
    supported = dict(expected)
    problems: list[str] = []
    seen: list[str] = []
    for token in _BADGE.findall(row):
        slot = badge_slot(token)
        if slot is None:
            problems.append(f"badge {token[:60]!r} fills no recognized slot")
            continue
        if slot in seen:
            problems.append(f"duplicate {slot} badge")
        seen.append(slot)
        if slot not in supported:
            problems.append(f"{slot} badge is not supported by any verified fact: {token[:80]!r}")
        elif token != supported[slot]:
            problems.append(f"{slot} badge differs from the verified one: {token[:80]!r}")
    ranks = [BADGE_ORDER.index(slot) for slot in seen]
    if ranks != sorted(ranks):
        problems.append(
            f"badge order {', '.join(seen)} breaks the stable order {', '.join(BADGE_ORDER)}"
        )
    return problems


def enterprise_anchor_problems(readme: str, target: str | None, included: bool) -> list[str]:
    """The Enterprise Edition anchor must open ``full-featured``, name the product, and end
    ``Enterprise Edition``, and link the verified target; required whenever the plan includes
    the section and the target is verified."""
    if target is None or not included:
        return []
    anchors = [
        text for text, href in re.findall(r"\[([^\]]+)\]\(([^)\s]+)\)", readme) if href == target
    ]
    if any(_ANCHOR.fullmatch(text) for text in anchors):
        return []
    if anchors:
        return [
            "the Enterprise Edition link text must read 'full-featured <product> — "
            f"Enterprise Edition'; found {anchors[0]!r}"
        ]
    return [f"the verified Enterprise Edition target {target} is not linked from the document"]
