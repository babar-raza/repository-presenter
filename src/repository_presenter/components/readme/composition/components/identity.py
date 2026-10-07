"""The identity component: the complete canonical product name the H1 and the prose use.

Derived deterministically from the governed repository name (``Aspose.3D-FOSS-for-Python`` becomes
``Aspose.3D FOSS for Python``): hyphens separate words, dots stay inside the family name, and
nothing is abbreviated. The authoring guard lists the name's tokens as identifiers the prose may
use; the renderer emits it as the only H1.
"""

from __future__ import annotations

import re

from repository_presenter.core.registry.models import RegistryEntry


def product_name(entry: RegistryEntry) -> str:
    return " ".join(part for part in entry.name.split("-") if part)


def product_name_tokens(name: str) -> frozenset[str]:
    """The name's space-separated tokens, each an identifier the prose may spell as written."""
    return frozenset(token for token in name.split(" ") if token)


# A private, self-contained copy of BC-12's own non-canonical-variant matcher
# (validation/registry.py's canonical_name_pattern/_is_technical_identifier), kept separate from
# that governed check rather than imported from it: the two modules already import in the other
# direction (registry.py reads the renderer), so sharing the matcher back would be circular, and
# BC-12 itself is deliberately left untouched by this elision (aspose-psd-foss/
# Aspose.PSD-FOSS-for-Python) - this only needs to recognise the same variants, never judge them.
_NAME_SEPARATOR = r"[\s._-]*"


def _noncanonical_name_pattern(canonical: str) -> re.Pattern[str]:
    segments = [part for part in re.split(r"[\s._-]+", canonical) if part]
    foss = next((i for i, part in enumerate(segments) if part.lower() == "foss"), None)
    head, tail = (segments, []) if foss is None else (segments[: foss + 1], segments[foss + 1 :])
    pattern = _NAME_SEPARATOR.join(re.escape(part) for part in head)
    if tail:
        rest = _NAME_SEPARATOR.join(re.escape(part) for part in tail)
        pattern += f"(?:{_NAME_SEPARATOR}{rest})?"
    return re.compile(r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])", re.IGNORECASE)


_IDENTIFIER_CUE_BEFORE = re.compile(
    r"(?i)\b(?:package|namespace|assembly|module|crate|named|called)\s+(?:`)?$"
)
_IDENTIFIER_CUE_AFTER = re.compile(
    r"(?i)^(?:`)?\s+(?:version|package|namespace|assembly|module|crate)\b"
)


def _is_technical_identifier(found: str, before: str, after: str) -> bool:
    if any(character.isspace() for character in found):
        return False
    if "-" in found or "_" in found:
        return True
    return bool(_IDENTIFIER_CUE_BEFORE.search(before) or _IDENTIFIER_CUE_AFTER.match(after))


_ELISION_MARK = "…"  # "…"


def elide_noncanonical(text: str, canonical: str) -> tuple[str, tuple[str, ...]]:
    """``text`` with every forbidden non-canonical variant of ``canonical`` (BC-12's own match -
    a different separator, case, or a missing/extra segment, never a technical identifier)
    replaced by an ellipsis, plus the variants removed, in the order found.

    A verbatim-quoted upstream string - a docstring, a code comment - cited as evidence is
    content the repair loop may never rewrite (BC-12 refuses that outright). So the composer
    calls this before such a quote enters the page, eliding only the offending substring and
    keeping the rest of the quote's own words, rather than let a non-canonical name ride a
    citation onto the rendered page and fail BC-12 unrepairably
    (aspose-psd-foss/Aspose.PSD-FOSS-for-Python).
    """
    pattern = _noncanonical_name_pattern(canonical)
    removed: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        found = match.group(0)
        if found == canonical:
            return found
        before = text[max(0, match.start() - 24) : match.start()]
        after = text[match.end() : match.end() + 24]
        if _is_technical_identifier(found, before, after):
            return found
        removed.append(found)
        return _ELISION_MARK

    elided = pattern.sub(_replace, text)
    return elided, tuple(removed)
