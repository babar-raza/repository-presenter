"""Phase 1: derive a candidate description/topics/homepage from already-verified facts, and diff
it against Phase 0's GitHub observation (docs/investigations/02-repo-metadata-community-files.md
section 5). Never writes anything - no ``PATCH``/``PUT`` call exists in this module or anywhere
this module reaches.

Every proposed value traces to a fact this project already extracted and verified, so it can never
assert something the README does not already support (AGENTS.md "Truth and README Content"):

- ``description`` is the first sentence of the *sealed* candidate README's own opening paragraph -
  text a full validation/independent-review pass already accepted. This module makes no new LLM
  call and writes no new prose; editorial composition stays the LLM's job
  (AGENTS.md "Agentic and Deterministic Boundary"), and this is a deterministic re-use of already
  reviewed text, not a new composition.
- ``topics`` is a small, deterministic recombination of already-``SUPPORTED`` ``identity:platform``
  (or ``identity:ecosystem`` when platform is absent), ``identity:family``, and ``license:spdx``
  facts, plus the two constant, always-true labels ``aspose`` and ``foss``.
- ``homepage`` is the already-``SUPPORTED`` ``link_target:product.homepage`` fact
  (``components/readme/evidence/facts/product_pages.py``), unchanged - never re-derived.

A repository with no sealed candidate yet, or whose product-homepage lookup was never
``SUPPORTED``, gets ``None`` for the corresponding field rather than a guess - the same
"insufficient_evidence over fabrication" discipline README composition already follows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repository_presenter.core.facts import FactsDocument

DESCRIPTION_MAX_LENGTH = 350  # GitHub's own field limit
HOMEPAGE_FACT_ID = "link_target:product.homepage"
STATIC_TOPICS: tuple[str, ...] = ("aspose", "foss")

_BACKTICK = re.compile(r"`([^`]+)`")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_NOT_TOPIC_CHAR = re.compile(r"[^a-z0-9-]+")
_DASH_RUN = re.compile(r"-{2,}")


@dataclass(frozen=True)
class ProposedRepoMetadata:
    """One candidate value per field, each with the fact ID(s)/source it traces to (or ``None``
    when there is nothing safe to propose)."""

    description: str | None
    description_source: str | None
    topics: tuple[str, ...]
    topics_sources: tuple[str, ...]
    homepage: str | None
    homepage_source: str | None


@dataclass(frozen=True)
class RepoMetadataDiff:
    """The proposal against Phase 0's observation, field by field."""

    repository: str
    proposed: ProposedRepoMetadata
    observed_description: str | None
    observed_homepage: str | None
    observed_topics: tuple[str, ...]
    description_changed: bool
    homepage_changed: bool
    topics_changed: bool

    @property
    def has_changes(self) -> bool:
        return self.description_changed or self.homepage_changed or self.topics_changed


def _clean_inline_markdown(text: str) -> str:
    text = _MD_LINK.sub(r"\1", text)
    text = _BACKTICK.sub(r"\1", text)
    return " ".join(text.split())


def opening_paragraph(readme_text: str) -> str | None:
    """The first block of plain prose in the document: after the H1 and any badge/banner lines
    (a line that is only image/link markdown), before the first ``##`` heading. ``None`` when no
    such block exists (e.g. a README with no H1, or one with no prose before its first section)."""
    lines = readme_text.splitlines()
    body: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not started:
            if stripped.startswith("# "):
                started = True
            continue
        body.append(line)
    if not body:
        return None
    paragraphs: list[str] = []
    current: list[str] = []
    for line in body:
        if line.strip():
            current.append(line.strip())
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    is_badge_or_image_only = re.compile(r"^(\[!\[.*\]\(.*\)\]\(.*\)|!\[.*\]\(.*\)|\s*)+$")
    for paragraph in paragraphs:
        if paragraph and not is_badge_or_image_only.match(paragraph):
            return paragraph
    return None


def propose_description(readme_text: str | None) -> tuple[str | None, str | None]:
    """The first sentence of the opening paragraph, or ``(None, reason)`` when there is none, or
    it would not fit GitHub's own ``description`` length limit unmodified."""
    if readme_text is None:
        return None, "no sealed candidate README to derive a description from"
    paragraph = opening_paragraph(readme_text)
    if paragraph is None:
        return None, "no opening paragraph found before the first section heading"
    cleaned = _clean_inline_markdown(paragraph)
    sentences = _SENTENCE_SPLIT.split(cleaned)
    first = sentences[0].strip() if sentences else ""
    if not first:
        return None, "opening paragraph's first sentence is empty after cleanup"
    if len(first) > DESCRIPTION_MAX_LENGTH:
        return None, (
            f"opening sentence is {len(first)} chars, over the {DESCRIPTION_MAX_LENGTH} limit"
        )
    return first, "sealed README opening paragraph, first sentence"


def _topic_slug(value: str) -> str:
    lowered = value.strip().lower().replace(".", "-").replace("_", "-").replace("+", "-")
    slug = _NOT_TOPIC_CHAR.sub("-", lowered).strip("-")
    return _DASH_RUN.sub("-", slug)


def propose_topics(facts: FactsDocument) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Deterministic topics from already-``SUPPORTED`` identity/license facts plus the constant
    ``aspose``/``foss`` labels. Order is stable: platform/ecosystem, family, license, then the
    constants, de-duplicated on first occurrence."""
    supported = {f.id: f for f in facts.facts if f.polarity == "SUPPORTED"}
    ordered_ids: list[str] = []
    values: list[str] = []
    platform = supported.get("identity:platform") or supported.get("identity:ecosystem")
    if platform is not None:
        values.append(platform.value)
        ordered_ids.append(platform.id)
    family = supported.get("identity:family")
    if family is not None:
        values.append(family.value)
        ordered_ids.append(family.id)
    license_fact = supported.get("license:spdx")
    if license_fact is not None:
        values.append(license_fact.value)
        ordered_ids.append(license_fact.id)
    values.extend(STATIC_TOPICS)
    topics: list[str] = []
    seen: set[str] = set()
    for value in values:
        slug = _topic_slug(value)
        if slug and slug not in seen:
            seen.add(slug)
            topics.append(slug)
    return tuple(topics), tuple(ordered_ids)


def propose_homepage(facts: FactsDocument) -> tuple[str | None, str | None]:
    """The already-verified product-homepage fact, unchanged, or ``(None, None)`` when it was
    never ``SUPPORTED`` (unresolved live lookup, or the extractor never ran for this repository)."""
    for fact in facts.facts:
        if fact.id == HOMEPAGE_FACT_ID and fact.polarity == "SUPPORTED":
            return fact.value, fact.id
    return None, None


def build_proposal(facts: FactsDocument, readme_text: str | None) -> ProposedRepoMetadata:
    """Every field's candidate value, each independently derived - a missing README affects only
    ``description``, never ``topics`` or ``homepage``."""
    description, description_source = propose_description(readme_text)
    topics, topics_sources = propose_topics(facts)
    homepage, homepage_source = propose_homepage(facts)
    return ProposedRepoMetadata(
        description=description,
        description_source=description_source,
        topics=topics,
        topics_sources=topics_sources,
        homepage=homepage,
        homepage_source=homepage_source,
    )


def diff_against_observed(
    repository: str,
    proposed: ProposedRepoMetadata,
    observed_description: str | None,
    observed_homepage: str | None,
    observed_topics: tuple[str, ...],
) -> RepoMetadataDiff:
    """Compare ``proposed`` against Phase 0's observation. Topics compare as sets - GitHub topic
    order carries no meaning; description and homepage compare exactly.

    A field this module could not safely propose (``None``) is never treated as "matches" or
    "differs" from an observed value - it is simply not proposed, and is reported as unchanged
    (nothing to diff), never as a phantom change.
    """
    description_changed = (
        proposed.description is not None and proposed.description != observed_description
    )
    homepage_changed = proposed.homepage is not None and proposed.homepage != observed_homepage
    topics_changed = bool(proposed.topics) and set(proposed.topics) != set(observed_topics)
    return RepoMetadataDiff(
        repository=repository,
        proposed=proposed,
        observed_description=observed_description,
        observed_homepage=observed_homepage,
        observed_topics=observed_topics,
        description_changed=description_changed,
        homepage_changed=homepage_changed,
        topics_changed=topics_changed,
    )
