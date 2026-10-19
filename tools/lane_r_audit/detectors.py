"""The detector registry behind M4 to M6: one interface, many detectors.

A detector reads a ``Subject`` (one text and what is known about it) and returns the findings it
makes, an empty list meaning it passes the text. Detectors are registered, never branched on:
adding one is adding a row to ``REGISTRY``. ``gate`` marks a detector that IS an existing pipeline
gate (BC-04, BC-14, the reviewer): the corpus catch rate of the gates is the M6 baseline (M6d for
the deterministic ones). The others are the independent reference detectors; they show what a gate
could catch and where it disagrees, and no metric of theirs is a gate's own.

Catch is differential (``corpus.py``): a detector catches a case when it fires on the injected text
and not on the clean twin.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import claims_ref, lint

# defect classes of the corpus (docs: evidence/lane-r-dependability/Q_claims.md section 1)
VERSION = "version"
FORMATTING = "formatting"
SCRAPED_TEXT = "scraped_text"
COUNT = "count"
SYMBOL_PROSE = "symbol_prose"
INVENTED_CAPABILITY = "invented_capability"
POLARITY = "polarity_contradiction"
DROPPED_CONTENT = "dropped_content"
IDENTIFIER = "wrong_identifier"
CLASSES: tuple[str, ...] = (
    VERSION,
    COUNT,
    FORMATTING,
    SCRAPED_TEXT,
    SYMBOL_PROSE,
    INVENTED_CAPABILITY,
    POLARITY,
    DROPPED_CONTENT,
    IDENTIFIER,
)
# floors proposed in G3-W12 (changeable only by an owner decision): class -> minimum catch rate
FLOORS: dict[str, float] = {
    VERSION: 0.95,
    FORMATTING: 0.95,
    SCRAPED_TEXT: 0.95,
    COUNT: 0.95,
    SYMBOL_PROSE: 0.95,
    INVENTED_CAPABILITY: 0.90,
    POLARITY: 0.90,
}


@dataclass(frozen=True)
class Subject:
    """What a detector is shown: one text in its setting."""

    text: str
    level: str  # "unit" (LLM-owned prose), "readme" (a README fragment) or "ledger"
    section: str = ""
    slot: str = ""
    cited: tuple[str, ...] = ()
    facts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    inherited: Mapping[str, str] = field(default_factory=dict)  # unit id -> live text
    ledger: Mapping[str, Any] = field(default_factory=dict)  # a ledger case's row


@dataclass(frozen=True)
class Detector:
    id: str
    classes: tuple[str, ...]
    run: Callable[[Subject], list[str]]
    gate: bool = False  # an existing pipeline gate: its catch rate is the M6 baseline
    deterministic: bool = True  # False for the reviewer (live, never in CI, never ratcheted)


REGISTRY: dict[str, Detector] = {}


def register(detector: Detector) -> Detector:
    if detector.id in REGISTRY:
        raise ValueError(f"detector {detector.id} is already registered")
    REGISTRY[detector.id] = detector
    return detector


# --- the independent reference detectors --------------------------------------------------------


def _m4(subject: Subject, kinds: Sequence[str]) -> list[str]:
    if subject.level != "unit":
        return []
    found = claims_ref.escapes(subject.text, subject.cited, subject.facts)
    return [f"{e.cls}:{e.token}" for e in found if e.cls in kinds]


def _lint(subject: Subject, rules: Sequence[str]) -> list[str]:
    return [f"{h.rule}:{h.excerpt}" for h in lint.lint(subject.text) if h.rule in rules]


_TRIGGER = re.compile(
    r"(?i)\b(?:supports?|support for|adds|includes?|provides?|enables?|not supported|"
    r"not functional|unsupported|free|commercial|enterprise)\b"
)
_WEAK_KINDS = frozenset({"identity", "package", "public_symbol", "link_target"})


def _capability(subject: Subject) -> list[str]:
    """A capability, edition or support sentence whose every cited fact is identity, package or
    symbol: nothing cited says what the product does (the C2 lexicon fallback, as a detector)."""
    if subject.level != "unit":
        return []
    kinds = {str(subject.facts.get(i, {}).get("kind", "unknown")) for i in subject.cited}
    if kinds - _WEAK_KINDS:
        return []
    return [f"trigger:{m.group(0)}" for m in _TRIGGER.finditer(subject.text)][:3]


_NEGATIVE = re.compile(
    r"(?i)\b(?:not (?:supported|functional|implemented|available)|unsupported|"
    r"(?:does|do) not support|no support for|cannot)\b"
)
_POSITIVE = re.compile(
    r"(?i)\b(?:supports?|support for|including|such as|handles?|can (?:read|write|open|convert)|"
    r"reads?|writes?|opens?|converts?|works? with|offers?)\b"
)
_NAMED = re.compile(r"\b[A-Z][A-Z0-9]{2,}\b|\b[A-Za-z]+[A-Z]\w+\b|\b[A-Za-z]+\.[A-Za-z]\w+\b")


def _polarity(subject: Subject) -> list[str]:
    """A token that a live 'not supported' unit names is asserted positively in this prose."""
    if subject.level != "unit" or not subject.inherited:
        return []
    named: set[str] = set()
    for text in subject.inherited.values():
        if _NEGATIVE.search(text):
            named |= {m.group(0) for m in _NAMED.finditer(text)}
    found: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", subject.text):
        if _POSITIVE.search(sentence) and not _NEGATIVE.search(sentence):
            found += [
                f"asserted:{t}"
                for t in sorted(named)
                if re.search(rf"\b{re.escape(t)}\b", sentence)
            ]
    return found


_MEMBER = re.compile(r"\bmembers? `?[A-Za-z_]\w*`?")


def _symbol_prose(subject: Subject) -> list[str]:
    """Prose built from API member names outside the API reference ('member AUTO, member H')."""
    if subject.level != "unit" or subject.section == "api_reference":
        return []
    members = _MEMBER.findall(subject.text)
    if len(members) >= 2:
        return [f"members:{len(members)}"]
    loose = [
        e
        for e in claims_ref.escapes(subject.text, subject.cited, subject.facts, strict=True)
        if e.cls == claims_ref.IDENTIFIER
    ]
    return [f"identifiers:{len(loose)}"] if len(loose) >= 3 else []


def _ledger(subject: Subject) -> list[str]:
    """A removed live unit with no computed CONTRADICTED evidence, or a kept unit not printed."""
    row = subject.ledger
    if subject.level != "ledger" or not row:
        return []
    disposition = row.get("disposition")
    if row.get("printed"):
        return []
    if disposition in ("OMIT_UNSUPPORTED", "VERIFIED_REWRITE", "CORRECT_WITH_EVIDENCE"):
        return [] if row.get("contradicted") else [f"{disposition}:no_contradicted_evidence"]
    if disposition == "SUPERSEDE_REDUNDANT":
        return [] if float(row.get("coverage", 0.0)) >= 0.8 else ["SUPERSEDE:coverage<0.8"]
    return [f"{disposition}:not_accounted"]


register(Detector("ref_version", (VERSION,), lambda s: _m4(s, (claims_ref.VERSION,))))
register(Detector("ref_count", (COUNT,), lambda s: _m4(s, (claims_ref.NUMBER,))))
register(
    Detector(
        "ref_identifier",
        (IDENTIFIER, INVENTED_CAPABILITY, POLARITY),
        lambda s: _m4(s, (claims_ref.IDENTIFIER, claims_ref.PACKAGE, claims_ref.FORMAT)),
    )
)
register(
    Detector(
        "ref_lint_formatting",
        (FORMATTING,),
        lambda s: _lint(s, (lint.DANGLING_COLON, lint.SPLIT_SPEC, lint.BADGE_SYNTAX)),
    )
)
register(
    Detector("ref_lint_scraped", (SCRAPED_TEXT,), lambda s: _lint(s, (lint.XML_DOC_FRAGMENT,)))
)
register(Detector("ref_capability", (INVENTED_CAPABILITY,), _capability))
register(Detector("ref_polarity", (POLARITY,), _polarity))
register(Detector("ref_symbol_prose", (SYMBOL_PROSE,), _symbol_prose))
register(Detector("ref_ledger", (DROPPED_CONTENT,), _ledger))


def reference_detectors() -> list[Detector]:
    return [d for d in REGISTRY.values() if not d.gate]


def gate_detectors() -> list[Detector]:
    return [d for d in REGISTRY.values() if d.gate]
