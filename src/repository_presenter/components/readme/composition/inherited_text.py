"""Maintainer wording the deterministic renderer keeps where facts alone would drop it.

Two sections render from facts and used to supersede the inherited unit that sits in them, even
when the unit said more than the facts do (docs/DECISION_LOG.md, 2026-10-10, cells/python parity):

* Dependencies: the maintainers explain what each dependency is for ("``pycryptodome`` >=3.15.0 -
  AES encryption/decryption used by ``XLSXEncryptor``..."). The dependency fact carries the name
  and version only, so the explanation was lost. ``dependency_purposes`` returns it for a
  dependency the maintainers' own list explains, and only when every identifier the explanation
  names resolves to a verified symbol (the same admission ``RenderContext.prose`` applies), so
  nothing unverifiable is carried onto the page.
* Additional Examples: the maintainers' task heading over an example ("Add Data Validation
  (Dropdown List)") is theirs; the authored slot sentence only stands in when the README had none.
  ``inherited_example_heading`` finds the heading above the example's own source code block.

Both read only SUPPORTED ``inherited_unit`` facts and are pure functions of the facts document.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from repository_presenter.core.facts import Fact, FactsDocument

# "- `name` >=1.2 - description" and "- `name>=1.2` - description": the leading code span names the
# package, an optional version specifier may follow outside it, then a dash (em, en, or hyphen
# set off by spaces) and the explanation.
_ITEM = re.compile(
    r"^`(?P<name>[A-Za-z0-9_.\-]+)(?:[<>=!~][^`]*)?`"
    r"(?:\s*(?:[<>=!~]=?|==)\s*[\w.*]+(?:\s*,\s*(?:[<>=!~]=?|==)\s*[\w.*]+)*)?"
    r"\s+[\u2014\u2013-]\s+(?P<text>\S.*)$"
)
_CODE_SPAN = re.compile(r"`([^`]+)`")
_NAME = re.compile(r"[A-Za-z0-9_.\-]+")
_SOURCE_CODE_UNIT = re.compile(r"unit (inherited_unit:\d{3}(?:\.\d{3})?\.code_block)")
_HEADING = re.compile(r"^(#{3,6})\s+(?P<text>\S.*?)\s*#*\s*$")


def _section_path(fact: Fact) -> list[str]:
    return [part.strip() for part in str((fact.attributes or {}).get("section", "")).split(" > ")]


def _list_items(value: str) -> list[str]:
    """A markdown list's items, each continuation line folded into its item."""
    items: list[str] = []
    for line in value.splitlines():
        if re.match(r"^\s{0,3}[-*+]\s+", line):
            items.append(re.sub(r"^\s{0,3}[-*+]\s+", "", line).strip())
        elif items and line.strip():
            items[-1] += " " + line.strip()
    return items


def dependency_name(value: str) -> str:
    """The package name of a dependency fact value (``olefile>=0.46`` -> ``olefile``)."""
    match = _NAME.match(value.strip())
    return (match.group(0) if match else value).lower().replace("_", "-")


def dependency_purposes(facts: FactsDocument, resolves: Callable[[str], bool]) -> dict[str, str]:
    """Package name -> the maintainers' explanation of it, from their own Dependencies lists.

    ``resolves`` says whether a code-span identifier in the explanation is a verified one; an
    explanation naming any identifier that does not resolve is dropped whole, never trimmed.
    """
    purposes: dict[str, str] = {}
    for unit in facts.by_kind("inherited_unit"):
        if unit.polarity != "SUPPORTED" or not unit.id.endswith(".list"):
            continue
        if not any("dependenc" in part.lower() for part in _section_path(unit)):
            continue
        for item in _list_items(unit.value):
            match = _ITEM.match(item)
            if match is None:
                continue
            name = dependency_name(match.group("name"))
            text = match.group("text").strip()
            identifiers = _CODE_SPAN.findall(text)
            if name in purposes or not all(resolves(token) for token in identifiers):
                continue
            purposes[name] = text
    return purposes


def inherited_example_heading(facts: FactsDocument, example: Fact) -> str | None:
    """The maintainers' heading over ``example``'s own source code block, or None.

    The example fact records the inherited code block it came from; that block's section path
    ends in the heading it sat under. Only a sub-section heading (level three or deeper) counts:
    a shell section's own heading ("Quick Start") names the section, not the example.
    """
    for evidence in example.evidence:
        match = _SOURCE_CODE_UNIT.search(evidence.detail or "")
        if match is None:
            continue
        code = next((f for f in facts.by_kind("inherited_unit") if f.id == match.group(1)), None)
        if code is None or code.polarity != "SUPPORTED":
            return None
        path = _section_path(code)
        if len(path) < 3:
            return None
        title = path[-1]
        for heading in facts.by_kind("inherited_unit"):
            if heading.polarity != "SUPPORTED" or not heading.id.endswith(".heading"):
                continue
            found = _HEADING.match(heading.value.strip())
            if found is not None and found.group("text") == title:
                return title
        return None
    return None


_CAPABILITY_HEADINGS = frozenset({"key capabilities", "capabilities", "key features", "features"})


def inherited_capability_count(facts: FactsDocument) -> int:
    """How many capabilities the existing README lists under its capabilities or features
    heading: the items of its SUPPORTED list units there (a bullet is one capability)."""
    by_id = {unit.id: unit for unit in facts.by_kind("inherited_unit")}
    return sum(
        len(_list_items(by_id[unit_id].value)) for unit_id in inherited_capability_unit_ids(facts)
    )


def inherited_capability_unit_ids(facts: FactsDocument) -> list[str]:
    """The SUPPORTED list units of the existing README's capabilities or features section."""
    return [
        unit.id
        for unit in facts.by_kind("inherited_unit")
        if unit.polarity == "SUPPORTED"
        and unit.id.endswith(".list")
        and _section_path(unit)[-1].lower() in _CAPABILITY_HEADINGS
    ]
