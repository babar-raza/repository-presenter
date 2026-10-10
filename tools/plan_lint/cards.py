"""Parse the taskcards out of a plan file (card TC-LNT-01-01).

Cards live once, as fenced ``yaml`` blocks in the plan; each block that is a YAML *list* of
mappings is a card block (the plan's leading header block is a mapping and is ignored). The tree is
parent -> child -> micro-step; a micro-step is one ``"op | target | done-when"`` string whose ID is
derived from its 1-based position, never stored (reordering a child's steps is a new child).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PARENT_ID = re.compile(r"^TC-([A-Z][A-Z0-9]*)-(\d{2})$")
CHILD_ID = re.compile(r"^TC-([A-Z][A-Z0-9]*)-(\d{2})-(\d{2})$")
MICRO_ID = re.compile(r"^MS-([A-Z][A-Z0-9]*)-(\d{2})-(\d{2})-(\d{2})$")
REQ_ID = re.compile(r"^REQ-([A-Z][A-Z0-9]*)-(\d{2})$")
ITEM_ID = re.compile(r"^G[0-7]-W[0-9]{2}$")

OPS = ("inspect", "create", "edit", "run", "validate", "record", "decide-owner", "package")

_FENCE = re.compile(r"^```yaml[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}[ \t]+(?:\d+\.[ \t]+)?Requirements\b.*$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)
_REQ_TOKEN = re.compile(r"REQ-([A-Z][A-Z0-9]*)-(\d{2})(?:…(\d{2}))?")


@dataclass(frozen=True)
class Step:
    """One micro-step: its derived ID plus the three parts of its triple (None when malformed)."""

    id: str
    raw: Any
    op: str | None
    target: str | None
    done_when: str | None


@dataclass
class Child:
    id: str
    title: str
    steps: list[Step]
    raw: dict[str, Any]
    kind: str = ""
    optional: bool = False
    produces: list[str] = field(default_factory=list)
    write: list[str] | None = None


@dataclass
class Parent:
    id: str
    title: str
    reqs: list[str]
    item: str
    lane: str
    depends: list[str]
    governed: bool | None
    ground: str | None
    write: list[str]
    forbidden: list[str]
    children: list[Child]
    raw: dict[str, Any]
    optional: bool = False


@dataclass
class Plan:
    parents: list[Parent]
    defined_reqs: set[str]
    has_requirements_section: bool
    problems: list[str] = field(default_factory=list)  # structural parse problems
    # Hot files a header mapping names under `serialised_paths:` (only the supervisor writes them,
    # one at a time): a parallel write overlap wholly inside one is waived by the lint.
    serialised_paths: list[str] = field(default_factory=list)

    def parent(self, card_id: str) -> Parent | None:
        return next((p for p in self.parents if p.id == card_id), None)

    def child(self, card_id: str) -> Child | None:
        return next((c for p in self.parents for c in p.children if c.id == card_id), None)

    def parent_of(self, card_id: str) -> Parent | None:
        """The parent that owns ``card_id`` (itself if a parent, its parent if a child)."""
        direct = self.parent(card_id)
        if direct is not None:
            return direct
        return next((p for p in self.parents for c in p.children if c.id == card_id), None)


def expand_requirements(text: str) -> set[str]:
    """Every REQ ID named in ``text``; ``REQ-ISS-01…11`` (U+2026) expands to 01..11."""
    found: set[str] = set()
    for match in _REQ_TOKEN.finditer(text):
        area, first, last = match.group(1), int(match.group(2)), match.group(3)
        for number in range(first, int(last) + 1 if last else first + 1):
            found.add(f"REQ-{area}-{number:02d}")
    return found


def _requirements_section(text: str) -> str | None:
    heading = _HEADING.search(text)
    if heading is None:
        return None
    rest = text[heading.end() :]
    following = _NEXT_HEADING.search(rest)
    return rest[: following.start()] if following else rest


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item if isinstance(item, str) else repr(item) for item in value]
    return [repr(value)]


def _step(child_id: str, position: int, raw: Any) -> Step:
    micro = child_id.replace("TC-", "MS-", 1) + f"-{position:02d}"
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.split(" | ")]
        if len(parts) == 3 and all(parts):
            return Step(micro, raw, parts[0], parts[1], parts[2])
    return Step(micro, raw, None, None, None)


def _child(raw: dict[str, Any]) -> Child:
    child_id = str(raw.get("id", ""))
    steps = raw.get("steps")
    paths = raw.get("paths")
    write = _strings(paths.get("write")) if isinstance(paths, dict) and "write" in paths else None
    return Child(
        id=child_id,
        title=str(raw.get("title", "")),
        steps=[_step(child_id, i, s) for i, s in enumerate(steps, 1)]
        if isinstance(steps, list)
        else [],
        raw=raw,
        kind=str(raw.get("kind", "")),
        optional=raw.get("optional") is True,
        produces=_strings(raw.get("produces")),
        write=write,
    )


def _parent(raw: dict[str, Any]) -> Parent:
    paths = raw.get("paths") if isinstance(raw.get("paths"), dict) else {}
    children = raw.get("children")
    ground = raw.get("ground")
    governed = raw.get("governed")
    return Parent(
        id=str(raw.get("id", "")),
        title=str(raw.get("title", "")),
        reqs=_strings(raw.get("reqs")),
        item=str(raw.get("item", "")),
        lane=str(raw.get("lane", "")),
        depends=_strings(raw.get("depends")),
        governed=governed if isinstance(governed, bool) else None,
        ground=ground if isinstance(ground, str) else None,
        write=_strings(paths.get("write")),
        forbidden=_strings(paths.get("forbidden")),
        children=[_child(c) for c in children if isinstance(c, dict)]
        if isinstance(children, list)
        else [],
        raw=raw,
        optional=raw.get("optional") is True,
    )


def parse_plan_text(text: str) -> Plan:
    """Parse every card block of ``text``; structural problems are recorded, never raised."""
    parents: list[Parent] = []
    problems: list[str] = []
    serialised: list[str] = []
    for index, block in enumerate(_FENCE.finditer(text), 1):
        try:
            loaded = yaml.safe_load(block.group(1))
        except yaml.YAMLError as error:
            problems.append(f"yaml block {index} does not parse: {str(error).splitlines()[0]}")
            continue
        if isinstance(loaded, dict):
            serialised.extend(_strings(loaded.get("serialised_paths")))
        if not isinstance(loaded, list):
            continue  # the header mapping or any non-card block
        for entry in loaded:
            if isinstance(entry, dict):
                parents.append(_parent(entry))
            else:
                problems.append(f"yaml block {index} holds a list entry that is not a card")
    section = _requirements_section(text)
    return Plan(
        parents=parents,
        defined_reqs=expand_requirements(section) if section is not None else set(),
        has_requirements_section=section is not None,
        problems=problems,
        serialised_paths=serialised,
    )


def parse_plan(path: Path) -> Plan:
    return parse_plan_text(path.read_text(encoding="utf-8"))
