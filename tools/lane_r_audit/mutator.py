"""The seeded mutator: one defect injected into one clean unit of a pinned candidate.

Each mutation turns a clean LLM-owned unit (the twin) into an injected one by changing a version,
a package name or adding a claim the cited facts cannot carry: a count, a format, a capability, a
polarity flip, a formatting lead-in, a scraped-text fragment, prose built from member names. The
choice of unit and of text is a function of the seed, so ``corpus build`` is reproducible and
``corpus check`` can prove the committed cases are what the builder produces.

A mutation returns the injected text or ``None`` when the unit cannot carry that defect (no version
to bump, no package token). It never reads a detector: whether a detector catches a mutant is what
the corpus measures, not an input to it.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable

from . import detectors

_VERSION_TOKEN = re.compile(r"(?<![\w.])(\d+\.\d+(?:\.\d+)?)(?![\w.])")
_PACKAGE = re.compile(r"\b(aspose-[a-z0-9]+(?:-[a-z0-9]+)*-foss)\b")

# formats and capabilities no cited fact of a unit would state (the cases only use them in units
# whose cited facts are identity, package or symbol kinds; the builder checks the twin is silent)
_ABSENT_FORMATS = ("ODT", "EPUB", "XLSM", "DOCX export", "PSD", "HEIC", "WebP", "JPEG 2000")
_COUNT_SENTENCES = (
    "The repository ships {n} test files covering these scenarios.",
    "The public surface exposes {n} documented classes.",
    "The suite runs {n} automated checks on every commit.",
    "More than {n} examples are included in the repository.",
)
_CAPABILITY_SENTENCES = (
    "It also supports {fmt} import and export.",
    "The library provides {fmt} conversion out of the box.",
    "Batch processing of {fmt} files is included.",
)
_FORMATTING_TAILS = (
    ("dangling", " Run the test suite:"),
    ("split_spec", "\n\n- `<145`\n- `numpy>=1.24`"),
    ("badge", "\n\n![Python](https://img.shields.io/badge/python-3.10%2C%3C3.13%2B-blue.svg)"),
)
_SCRAPED_TAILS = (
    " The  contains the transformation matrix for a node.",
    "\n\n- `width`: Defined as `: number`.",
    " A  curve consists of a set of points in the edge of the shape.",
)
_SYMBOL_TAILS = (
    " The examples demonstrate member AUTO, member H, member data and member render.",
    " Tests exercise member Open, member Close, member Save and member Load.",
)


def bump_version(version: str, rng: random.Random) -> str:
    parts = [int(p) for p in version.split(".")]
    index = rng.choice([len(parts) - 1, max(len(parts) - 2, 0)])
    parts[index] += rng.choice([1, 2, 3])
    for tail in range(index + 1, len(parts)):
        parts[tail] = 0
    return ".".join(str(p) for p in parts)


def version(text: str, rng: random.Random, supported: set[str]) -> str | None:
    """Change a version the cited facts support to one they do not."""
    candidates = [m for m in _VERSION_TOKEN.finditer(text) if m.group(1) in supported]
    if not candidates:
        return None
    match = rng.choice(candidates)
    changed = bump_version(match.group(1), rng)
    if changed in supported:
        return None
    return text[: match.start(1)] + changed + text[match.end(1) :]


def identifier(text: str, rng: random.Random, supported: set[str]) -> str | None:
    """Drop ``-foss`` from a supported package name (the rename error of Q_claims class D)."""
    hits = [m for m in _PACKAGE.finditer(text) if m.group(1) in supported]
    if not hits:
        return None
    match = rng.choice(hits)
    return text[: match.start(1)] + match.group(1)[: -len("-foss")] + text[match.end(1) :]


def count(text: str, rng: random.Random, supported: set[str]) -> str | None:
    number = rng.randrange(41, 400)
    if str(number) in supported:
        return None
    return text.rstrip() + " " + rng.choice(_COUNT_SENTENCES).format(n=number)


def invented_capability(text: str, rng: random.Random, supported: set[str]) -> str | None:
    fmt = rng.choice(_ABSENT_FORMATS)
    if fmt.casefold() in supported:
        return None
    return text.rstrip() + " " + rng.choice(_CAPABILITY_SENTENCES).format(fmt=fmt)


def formatting(text: str, rng: random.Random, supported: set[str]) -> str | None:
    _, tail = rng.choice(_FORMATTING_TAILS)
    return text.rstrip() + tail


def scraped_text(text: str, rng: random.Random, supported: set[str]) -> str | None:
    return text.rstrip() + rng.choice(_SCRAPED_TAILS)


def symbol_prose(text: str, rng: random.Random, supported: set[str]) -> str | None:
    return text.rstrip() + rng.choice(_SYMBOL_TAILS)


def polarity(text: str, rng: random.Random, negated: list[str]) -> str | None:
    """Assert, in a positive sentence, a token a live 'not supported' unit names."""
    if not negated:
        return None
    token = rng.choice(negated)
    return text.rstrip() + f" It supports {token} out of the box."


Mutation = Callable[[str, random.Random, set[str]], str | None]

MUTATIONS: dict[str, Mutation] = {
    detectors.VERSION: version,
    detectors.IDENTIFIER: identifier,
    detectors.COUNT: count,
    detectors.INVENTED_CAPABILITY: invented_capability,
    detectors.FORMATTING: formatting,
    detectors.SCRAPED_TEXT: scraped_text,
    detectors.SYMBOL_PROSE: symbol_prose,
}
