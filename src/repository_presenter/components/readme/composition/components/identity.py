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


# What a variant may sit beside without being a spelling of the product name: it continues, or is
# continued by, a longer dotted/slashed/scoped identifier (``Aspose.Pdf.Foss.Tests``,
# ``src/Aspose.Pdf.Foss/Scene.cs``, ``Aspose::Pdf::Foss``), or a "for <something>" tail the
# canonical name does not have (``Aspose.3D FOSS for Java``), which is another product's name.
_IDENTIFIER_CONTINUES = re.compile(r"^(?:\.[A-Za-z0-9_]|[/\\_]|::)")
_IDENTIFIER_CONTINUED = re.compile(r"(?:[A-Za-z0-9_]\.|[/\\_]|::)$")
_ANOTHER_TAIL = re.compile(r"^\s+for\b", re.IGNORECASE)
# Spans the renderer and the readers treat as code: left exactly as the author wrote them.
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)


def _is_spelling_of_the_name(found: str, canonical: str, before: str, after: str) -> bool:
    """Whether ``found`` (BC-12's own variant match) stands for the product name in running prose,
    as opposed to the canonical name itself, a technical identifier or part of a longer one."""
    if found == canonical or _is_technical_identifier(found, before, after):
        return False
    if _IDENTIFIER_CONTINUES.match(after) or _IDENTIFIER_CONTINUED.search(before[-2:]):
        return False
    return _ANOTHER_TAIL.match(after) is None


def canonicalise_name_variants(text: str, canonical: str) -> str:
    """``text`` with every separator, case or suffix variant of ``canonical`` that stands for the
    product name in running prose rewritten to ``canonical``.

    The model shortens the name ("usage in Aspose.3D FOSS.", "between Aspose.PSD FOSS and the
    original ...") and BC-12 refuses it; the repair loop asks for a rewrite three times and the
    variant comes back (3D-.NET limitation:6, PSD-Python's TestAsposeCompatibility row, 2026-10-10
    baseline). The canonical name is a function of the registry name alone, so the code owns this
    spelling exactly as it owns a code span and an abbreviation's case, and the correction is
    made where the prose is authored (``authoring.unit_checks``). BC-12 itself is unchanged and
    still judges the result.

    Left alone, because they are not spellings of the product name: the canonical name, a slug
    with a hyphen or underscore, a name beside a package or namespace cue, a longer dotted or
    slashed identifier that starts with the family name (a project, a type, a path), a name
    followed by another "for <platform>", and anything inside a code span or fence.
    """
    pattern = _noncanonical_name_pattern(canonical)

    def _rewrite(segment: str, base: int) -> str:
        def _replace(match: re.Match[str]) -> str:
            start, end = base + match.start(), base + match.end()
            before, after = text[max(0, start - 24) : start], text[end : end + 24]
            if _is_spelling_of_the_name(match.group(0), canonical, before, after):
                return canonical
            return match.group(0)

        return pattern.sub(_replace, segment)

    out: list[str] = []
    cursor = 0
    for code in _CODE.finditer(text):
        out.append(_rewrite(text[cursor : code.start()], cursor))
        out.append(code.group(0))
        cursor = code.end()
    out.append(_rewrite(text[cursor:], cursor))
    return "".join(out)


def spells_the_product(token: str, canonical: str) -> bool:
    """Whether the whole ``token`` is a separator, case or suffix variant of ``canonical`` (BC-12's
    own match), so that admitting it as a spellable identifier would put a short name for the
    product into running prose inside a code span, where BC-12 does not look."""
    return _noncanonical_name_pattern(canonical).fullmatch(token) is not None
