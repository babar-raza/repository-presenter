"""D14 (mechanical template filling): a deterministic, LLM-free checker over a candidate README.

Rule (PROPOSAL, awaiting owner ratification with the rest of the profile; see ``profile.py``):
a prose section of the candidate is TEMPLATED when

1. its body, with the product name and version replaced by placeholders and normalized for case
   and whitespace, is identical to the body of a same-heading section of a reference README of
   another repository (the template corpus), and
2. it contains no repository-specific fact token from the evidence. Fact tokens are the
   identifiers, package names, commands, and paths of the immutable upstream revision; the product
   name and version never count as facts.

Verdicts:

- ``DISQUALIFIED``: at least one section is TEMPLATED. The evidence names each one.
- ``PASS``: every judged section is either unmatched or names a repository fact.
- ``UNEVALUATED``: the checker cannot judge. This happens when the evidence has no product name or
  no usable fact token, when the template corpus is empty, or when no section has at least
  ``MIN_WORDS`` words. Missing input is never read as a pass.

This module does not read ``RATIFIED``, does not change ``profile.py``, and is not wired into the
scorer. Its inputs are supplied by the caller.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from repository_presenter.components.readme.review.acceptance.text_checks import Line, scan

MIN_WORDS = (
    8  # PROPOSAL: shorter sections (for example a bare heading and one line) are not judged.
)
MIN_FACT_TOKEN_LENGTH = 3  # PROPOSAL: shorter tokens match too much prose to prove a repo fact.

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_WORD = re.compile(r"[A-Za-z0-9][\w.+-]*")
_PRODUCT_PLACEHOLDER = "<product>"
_VERSION_PLACEHOLDER = "<version>"


class Verdict(StrEnum):
    PASS = "PASS"
    DISQUALIFIED = "DISQUALIFIED"
    UNEVALUATED = "UNEVALUATED"


@dataclass(frozen=True)
class Evidence:
    """Repository-specific inputs. ``fact_tokens`` come from the immutable upstream revision."""

    product_name: str
    version: str
    fact_tokens: frozenset[str]


@dataclass(frozen=True)
class ReferenceSection:
    """A section of another repository's README, with that repository's own product and version."""

    heading: str
    body: str
    product_name: str
    version: str


@dataclass(frozen=True)
class TemplateResult:
    verdict: Verdict
    evidence: tuple[str, ...]


def check_template_filling(
    readme: str, evidence: Evidence, corpus: Sequence[ReferenceSection]
) -> TemplateResult:
    """Judge a candidate README's prose sections against the template corpus."""
    product = evidence.product_name.strip()
    if not product:
        return _unevaluated("evidence has no product name")
    tokens = _specific_tokens(evidence)
    if not tokens:
        return _unevaluated("evidence has no repository-specific fact token of usable length")
    if not corpus:
        return _unevaluated("no reference README corpus was supplied")

    index: dict[tuple[str, str], list[int]] = {}
    for position, reference in enumerate(corpus):
        if not reference.body.strip():
            continue
        key = _key(reference.heading, reference.body, reference.product_name, reference.version)
        index.setdefault(key, []).append(position)

    judged = 0
    templated: list[str] = []
    exempt: list[str] = []
    for heading, body in _sections(scan(readme)):
        if len(_WORD.findall(body)) < MIN_WORDS:
            continue
        judged += 1
        matches = index.get(_key(heading, body, evidence.product_name, evidence.version))
        if not matches:
            continue
        label = f"section '{heading or '(before first heading)'}' matches reference {matches[0]}"
        if _names_fact(body, tokens):
            exempt.append(f"{label} but names a repository fact")
        else:
            templated.append(f"{label} after masking product and version, with no repository fact")

    if judged == 0:
        return _unevaluated(f"no section has at least {MIN_WORDS} words")
    if templated:
        return TemplateResult(Verdict.DISQUALIFIED, tuple(templated))
    notes = (f"judged {judged} section(s)", *exempt)
    return TemplateResult(Verdict.PASS, notes)


def _unevaluated(reason: str) -> TemplateResult:
    return TemplateResult(Verdict.UNEVALUATED, (f"cannot judge: {reason}",))


def _specific_tokens(evidence: Evidence) -> frozenset[str]:
    excluded = {evidence.product_name.strip().lower(), evidence.version.strip().lower()}
    return frozenset(
        token.strip().lower()
        for token in evidence.fact_tokens
        if len(token.strip()) >= MIN_FACT_TOKEN_LENGTH and token.strip().lower() not in excluded
    )


def _names_fact(body: str, tokens: Iterable[str]) -> bool:
    lowered = body.lower()
    return any(
        re.search(rf"(?<![\w.-]){re.escape(token)}(?![\w-])", lowered) is not None
        for token in tokens
    )


def _key(heading: str, body: str, product: str, version: str) -> tuple[str, str]:
    return _normalize(heading), _normalize(_mask(body, product, version))


def _mask(text: str, product: str, version: str) -> str:
    masked = text
    if product.strip():
        masked = re.sub(re.escape(product.strip()), _PRODUCT_PLACEHOLDER, masked, flags=re.I)
    if version.strip():
        masked = re.sub(re.escape(version.strip()), _VERSION_PLACEHOLDER, masked, flags=re.I)
    return masked


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _sections(lines: Sequence[Line]) -> list[tuple[str, str]]:
    """Split on heading lines of any level. A line inside a fence is never a heading. Each section
    body keeps its code lines, because a command in a code block is a repository fact."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in lines:
        match = None if line.code else _HEADING.match(line.text)
        if match:
            sections.append((match.group(1).strip(), []))
        else:
            sections[-1][1].append(line.text)
    return [(heading, "\n".join(body)) for heading, body in sections]
