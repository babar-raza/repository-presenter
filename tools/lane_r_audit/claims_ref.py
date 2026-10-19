"""M4: claim escapes. An independent reference checker over LLM-owned prose.

An escape is a token class instance in a content unit's text that no fact the unit cites supports:
a version, a number, an identifier, a package name or a format name whose normalised form is not a
token of the value, the attributes or the id of a cited fact of a kind other than ``identity``.
(``public_symbol`` facts count: the unit may name what a cited symbol names; the strict reading
that also drops them is reported beside it as ``strict``.)

This module reads the content units and facts as data and imports nothing from validation,
reconciliation or composition, so the C2 gate and this metric cannot share a defect. Where the two
disagree on the corpus the disagreement is a finding for the owner, not an automatic failure.
It does not judge meaning: whether a sentence entails what its facts say is the reviewer's work
(M6r) and the polarity and capability detectors' (``detectors.py``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

VERSION = "version"
NUMBER = "number"
IDENTIFIER = "identifier"
PACKAGE = "package"
FORMAT = "format"
CLASSES: tuple[str, ...] = (VERSION, NUMBER, IDENTIFIER, PACKAGE, FORMAT)

# Names of file and data formats a README states support for. Matched as whole words; upper case
# as written (DOCX), or the listed spelling. Extending this is data, not logic.
FORMAT_LEXICON: tuple[str, ...] = (
    "DOCX", "DOC", "RTF", "ODT", "OTT", "EPUB", "XPS", "MHTML", "HTML", "XHTML", "MD", "TXT",
    "PDF", "XLSX", "XLS", "XLSM", "XLSB", "ODS", "CSV", "TSV", "PPTX", "PPT", "ODP", "PNG",
    "JPEG", "JPG", "GIF", "BMP", "TIFF", "WEBP", "SVG", "EMF", "WMF", "PSD", "DICOM", "JSON",
    "XML", "YAML", "EML", "MSG", "PST", "OST", "MBOX", "EMLX", "VCF", "ICS", "FBX", "GLTF",
    "GLB", "OBJ", "STL", "PLY", "DAE", "3MF", "DRACO", "COLLADA", "DXF", "DWG", "GML",
    "GEOJSON", "SHP", "KML", "TEX", "LATEX", "MARKDOWN", "OOXML", "ONE", "ZIP", "RAR",
)  # fmt: skip
# Brand and platform words with inner capitals that are not code identifiers.
BRANDS = frozenset(
    {"github", "gitlab", "pypi", "nuget", "javascript", "typescript", "openxml", "macos",
     "ios", "cmake", "powershell", "vscode", "intellij", "youtube", "linkedin", "webassembly",
     "asposefoss", "postscript", "truetype", "opentype", "onenote", "powerpoint", "acroform"}
)  # fmt: skip

_VERSION = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.]+)?)(?![\w])")
_NUMBER = re.compile(r"(?<![\w.$])(\d[\d,]*)(?![\w]|\.\d)")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_DOTTED = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
_CAMEL = re.compile(r"\b(?:[A-Za-z]*[a-z][A-Z]\w*|[A-Z]{2,}[a-z]\w*)\b")
_SNAKE = re.compile(r"\b[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+\b")
_HYPHEN_PACKAGE = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b")
_INSTALLED = re.compile(
    r"(?:pip install|npm install|npm i|cargo add|go get|dotnet add package)"
    r"\s+([A-Za-z0-9][\w.\-/\[\]]*)"
)
_NOT_A_PACKAGE = frozenset(
    {"to", "the", "a", "an", "it", "from", "with", "using", "via", "and", "or", "of"}
)
_NOT_AN_IDENTIFIER = re.compile(
    r"(?i)^(?:e\.g|i\.e|etc|vs|[\w-]+\.(?:md|txt|json|ya?ml|toml|cfg|ini|py|cs|js|ts|java|go|rs|cpp|h|hpp|xml|csproj|sln|html|com|org|io|net|dev|gradle|lock|png|svg))$"
)
_WORD = re.compile(r"[A-Za-z0-9]+")
_FORMAT = re.compile(r"(?<![\w.])(" + "|".join(re.escape(f) for f in FORMAT_LEXICON) + r")(?![\w])")


@dataclass(frozen=True)
class Escape:
    unit: str  # "<section>/<slot>"
    cls: str
    token: str
    cited: tuple[str, ...]


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _strings(item)


def _keys(text: str) -> set[str]:
    """The comparison forms of a text: each alphanumeric word, each dotted/hyphenated/underscored
    run whole, and every version, all lower case and with a leading ``v`` removed."""
    lowered = text.casefold()
    found = set(_WORD.findall(lowered))
    for match in re.finditer(r"[a-z0-9_]+(?:[.\-/][a-z0-9_]+)+", lowered):
        found.add(match.group(0))
        found.update(match.group(0).replace("/", ".").split("."))
    found.update(match.group(1) for match in _VERSION.finditer(lowered))
    return found


def support(
    facts: Mapping[str, Mapping[str, Any]], cited: Iterable[str], *, strict: bool = False
) -> set[str]:
    """Comparison forms of what the cited facts say (identity facts never support a claim)."""
    keys: set[str] = set()
    for fact_id in cited:
        fact = facts.get(fact_id)
        if fact is None or fact.get("kind") == "identity":
            continue
        if strict and fact.get("kind") == "public_symbol":
            continue
        for text in (*_strings(fact.get("value")), *_strings(fact.get("attributes")), fact_id):
            keys |= _keys(text)
    return keys


def _tokens(text: str) -> list[tuple[str, str]]:
    """(class, token) pairs for every checkable token of a prose text."""
    found: list[tuple[str, str]] = []
    pending = _CODE_SPAN.sub(lambda m: found.append((IDENTIFIER, m.group(1))) or " ", text)
    for match in _VERSION.finditer(pending):
        found.append((VERSION, match.group(1)))
    unversioned = _VERSION.sub(" ", pending)
    found.extend((NUMBER, m.group(1).replace(",", "")) for m in _NUMBER.finditer(unversioned))
    prose = re.sub(r"https?://\S+", " ", unversioned)
    found.extend((FORMAT, m.group(1)) for m in _FORMAT.finditer(prose))
    for pattern in (_DOTTED, _CAMEL, _SNAKE):
        found.extend(
            (IDENTIFIER, m.group(0))
            for m in pattern.finditer(prose)
            if not _NOT_AN_IDENTIFIER.match(m.group(0))
            and not re.fullmatch(r"[A-Z]{2,}s", m.group(0))
        )
    found.extend(
        (PACKAGE, m.group(1)) for m in _INSTALLED.finditer(text) if m.group(1) not in _NOT_A_PACKAGE
    )
    found.extend(
        (PACKAGE, m.group(0))
        for m in _HYPHEN_PACKAGE.finditer(prose)
        if m.group(0).startswith("aspose-")
    )
    return found


def _supported(cls: str, token: str, keys: set[str]) -> bool:
    form = token.casefold().lstrip("v") if cls == VERSION else token.casefold()
    if cls == IDENTIFIER and form in BRANDS:
        return True
    if cls == PACKAGE:  # a rename ('aspose-note' for 'aspose-note-foss') must not pass by parts
        return form in keys
    if cls == IDENTIFIER:
        parts = [p for p in re.split(r"[.\-/\s()\[\]<>,:]+", form) if p]
        return form in keys or (bool(parts) and all(p in keys for p in parts))
    return form in keys


def escapes(
    text: str,
    cited: Iterable[str],
    facts: Mapping[str, Mapping[str, Any]],
    *,
    unit: str = "",
    strict: bool = False,
) -> list[Escape]:
    """Every token of ``text`` that the cited facts do not support (distinct per class)."""
    cited = tuple(cited)
    keys = support(facts, cited, strict=strict)
    seen: set[tuple[str, str]] = set()
    out: list[Escape] = []
    for cls, token in _tokens(text):
        if (cls, token) in seen:
            continue
        seen.add((cls, token))
        if not _supported(cls, token, keys):
            out.append(Escape(unit, cls, token, cited))
    return out


def bundle_escapes(
    units: Iterable[Mapping[str, Any]],
    facts: Mapping[str, Mapping[str, Any]],
    *,
    strict: bool = False,
) -> list[Escape]:
    """M4 over a bundle's LLM-owned content units."""
    found: list[Escape] = []
    for unit in units:
        label = f"{unit.get('section')}/{unit.get('slot')}"
        found.extend(
            escapes(
                str(unit.get("text", "")),
                unit.get("fact_ids") or [],
                facts,
                unit=label,
                strict=strict,
            )
        )
    return found
