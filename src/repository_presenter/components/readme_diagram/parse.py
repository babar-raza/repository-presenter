"""Read an At a Glance Mermaid source into its meaning (``Glance``) and how it is drawn.

The parser is closed on purpose. It accepts only the shape the renderer has always written - the
``Starting Points`` / ``Core Capabilities`` / ``Outputs`` groups, the product node, optional
``direction`` lines, optional ``~~~`` order pins inside a group, the one visible chain edge - and
raises ``NotAGlanceError`` for anything else, so a diagram a maintainer drew by hand is never
reinterpreted. Labels come back as plain text: ``<br/>`` and runs of whitespace are drawing, not
meaning, and are folded to single spaces.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from repository_presenter.components.readme_diagram.model import Glance, NotAGlanceError

STARTING_POINTS = "StartingPoints"
CAPABILITIES = "Capabilities"
OUTPUTS = "Outputs"
PRODUCT = "PRODUCT"
GROUP_IDS = (STARTING_POINTS, CAPABILITIES, OUTPUTS)

_TYPE = re.compile(r"^(?:flowchart|graph)\s+(TD|TB|BT|LR|RL)$")
_SUBGRAPH = re.compile(r'^subgraph\s+(\w+)\s*\[\s*"([^"]*)"\s*\]$')
_DIRECTION = re.compile(r"^direction\s+(TD|TB|BT|LR|RL)$")
_NODE = re.compile(r'^(\w+)\s*\[\s*"([^"]*)"\s*\]$')
_VISIBLE_EDGE = re.compile(r"^\w+(?:\s*-->\s*\w+)+$")
_INVISIBLE_EDGE = re.compile(r"^\w+(?:\s*~~~\s*\w+)+$")
_INIT = re.compile(r"^%%\{\s*(?:init|initialize)\s*:\s*(\{.*\})\s*\}%%$")
BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
_NUMBER = re.compile(r"(\d+)$")


@dataclass
class _Container:
    ident: str | None
    title: str
    direction: str | None = None
    nodes: list[tuple[str, str]] = field(default_factory=list)  # (id, raw label)
    children: list[_Container] = field(default_factory=list)
    pinned: bool = False


@dataclass(frozen=True)
class Parsed:
    """An At a Glance source read two ways: what it says, and how it is drawn."""

    glance: Glance
    root_direction: str
    init: dict[str, Any]
    #: Direction written in each group (``StartingPoints``, ``Capabilities``, ``capl``, ...).
    group_direction: dict[str, str | None]
    #: Groups of two or more nodes whose reading order is pinned with ``~~~`` edges.
    pinned: frozenset[str]
    #: Node id to the label exactly as written (``<br/>`` kept).
    raw_labels: dict[str, str]
    #: Ids of the capability column groups in the order they are declared (empty: one column).
    declared_columns: tuple[str, ...]


_ENTITIES = (("#lt;", "<"), ("#gt;", ">"), ("#amp;", "&"))


def clean_label(raw: str) -> str:
    """The text of a label: breaks folded to spaces, whitespace collapsed, entities decoded."""
    text = re.sub(r"\s+", " ", BREAK_TAG.sub(" ", raw)).strip()
    for entity, char in _ENTITIES:
        text = text.replace(entity, char)
    return text


def _merge(target: dict[str, Any], extra: dict[str, Any]) -> None:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = value


def _statements(body: str) -> list[str]:
    out: list[str] = []
    for line in body.splitlines():
        text = line.strip()
        if not text or (text.startswith("%%") and not text.startswith("%%{")):
            continue
        out.append(text)
    return out


def _read_structure(body: str) -> tuple[_Container, str, dict[str, Any], list[str] | None]:
    root = _Container(None, "")
    stack = [root]
    direction: str | None = None
    init: dict[str, Any] = {}
    chain: list[str] | None = None
    for text in _statements(body):
        if text.startswith("%%{"):
            match = _INIT.match(text)
            if match is None:
                raise NotAGlanceError(f"unsupported directive {text[:60]!r}")
            try:
                loaded = json.loads(match.group(1))
            except ValueError as error:
                raise NotAGlanceError(f"init directive is not JSON: {error}") from error
            if not isinstance(loaded, dict):
                raise NotAGlanceError("init directive is not an object")
            _merge(init, loaded)
            continue
        if direction is None:
            kind = _TYPE.match(text)
            if kind is None:
                raise NotAGlanceError(f"no flowchart declaration before {text[:60]!r}")
            direction = kind.group(1)
            continue
        top = stack[-1]
        if (match := _SUBGRAPH.match(text)) is not None:
            container = _Container(match.group(1), match.group(2))
            top.children.append(container)
            stack.append(container)
        elif (match := _DIRECTION.match(text)) is not None:
            if top.ident is None:
                raise NotAGlanceError("a direction statement outside a subgraph")
            top.direction = match.group(1)
        elif text == "end":
            if len(stack) == 1:
                raise NotAGlanceError("end without a subgraph")
            stack.pop()
        elif (match := _NODE.match(text)) is not None:
            top.nodes.append((match.group(1), match.group(2)))
        elif _VISIBLE_EDGE.match(text):
            if len(stack) != 1 or chain is not None:
                raise NotAGlanceError(f"unexpected edge {text!r}")
            chain = [part.strip() for part in text.split("-->")]
        elif _INVISIBLE_EDGE.match(text):
            pins = [part.strip() for part in text.split("~~~")]
            if pins != [ident for ident, _ in top.nodes][: len(pins)] or len(pins) < 2:
                raise NotAGlanceError(f"an order pin that is not a group's own chain: {text!r}")
            top.pinned = len(pins) == len(top.nodes) or top.pinned
        else:
            raise NotAGlanceError(f"unsupported statement {text[:60]!r}")
    if direction is None:
        raise NotAGlanceError("no flowchart declaration")
    if len(stack) != 1:
        raise NotAGlanceError("a subgraph is never closed")
    return root, direction, init, chain


def _ordinal(ident: str) -> int | None:
    match = _NUMBER.search(ident)
    return int(match.group(1)) if match else None


def _titles(groups: dict[str | None, _Container]) -> dict[str, str]:
    """The group titles the source writes, under the ``Glance`` field each belongs to."""
    fields = {
        STARTING_POINTS: "starting_title",
        CAPABILITIES: "capabilities_title",
        OUTPUTS: "outputs_title",
    }
    return {fields[name]: clean_label(group.title) for name, group in groups.items() if name}


def _node_labels(container: _Container) -> tuple[str, ...]:
    return tuple(clean_label(raw) for _, raw in container.nodes)


def parse(body: str) -> Parsed:
    """The At a Glance diagram ``body`` says and how it draws it; ``NotAGlanceError`` otherwise."""
    root, direction, init, chain = _read_structure(body)
    groups = {child.ident: child for child in root.children}
    if len(groups) != len(root.children) or not set(groups) <= set(GROUP_IDS):
        raise NotAGlanceError("a subgraph outside Starting Points, Core Capabilities, Outputs")
    if any(not group.title.strip() for group in groups.values()):
        raise NotAGlanceError("a group without a title")
    if CAPABILITIES not in groups:
        raise NotAGlanceError("no Core Capabilities group")
    products = [(ident, raw) for ident, raw in root.nodes if ident == PRODUCT]
    if len(products) != 1 or len(root.nodes) != 1:
        raise NotAGlanceError("the root holds anything but the one product node")

    present = [name for name in GROUP_IDS if name in groups]
    expected = [
        *(["StartingPoints"] if STARTING_POINTS in groups else []),
        PRODUCT,
        CAPABILITIES,
        *(["Outputs"] if OUTPUTS in groups else []),
    ]
    if chain != expected:
        raise NotAGlanceError(f"the chain is {chain}, not {expected}")

    for name in (STARTING_POINTS, OUTPUTS):
        group = groups.get(name)
        if group is not None and (group.children or not group.nodes):
            raise NotAGlanceError(f"{name} is not a plain list of nodes")

    capabilities = groups[CAPABILITIES]
    column_groups = capabilities.children
    if column_groups and capabilities.nodes:
        raise NotAGlanceError("Core Capabilities mixes nodes and column groups")
    if len(column_groups) > 2:
        raise NotAGlanceError("more than two capability columns")
    if any(column.children or column.title.strip() for column in column_groups):
        raise NotAGlanceError("a capability column that is titled or nested")

    group_direction: dict[str, str | None] = {}
    pinned: set[str] = set()
    raw_labels: dict[str, str] = dict(root.nodes)
    for name in present:
        group = groups[name]
        group_direction[name] = group.direction
        if group.pinned:
            pinned.add(name)
        raw_labels.update(dict(group.nodes))
    columns: list[_Container]
    if column_groups:
        columns = sorted(
            column_groups,
            key=lambda column: min((_ordinal(i) or 0 for i, _ in column.nodes), default=0),
        )
        if any(not column.nodes for column in columns):
            raise NotAGlanceError("an empty capability column")
        for column in column_groups:
            assert column.ident is not None
            group_direction[column.ident] = column.direction
            if column.pinned:
                pinned.add(column.ident)
            raw_labels.update(dict(column.nodes))
    else:
        columns = [capabilities]
        if not capabilities.nodes:
            raise NotAGlanceError("Core Capabilities holds no capability")

    ids = [i for box in (root, *groups.values(), *column_groups) for i, _ in box.nodes]
    if len(set(ids)) != len(ids):
        raise NotAGlanceError("a node id is used twice")

    glance = Glance(
        product=clean_label(products[0][1]),
        starting_points=_node_labels(groups[STARTING_POINTS]) if STARTING_POINTS in groups else (),
        capability_columns=tuple(_node_labels(column) for column in columns),
        outputs=_node_labels(groups[OUTPUTS]) if OUTPUTS in groups else (),
        **_titles(groups),
    )
    if not glance.product or not all(glance.labels):
        raise NotAGlanceError("a node with an empty label")
    return Parsed(
        glance=glance,
        root_direction=direction,
        init=init,
        group_direction=group_direction,
        pinned=frozenset(pinned),
        raw_labels=raw_labels,
        declared_columns=tuple(c.ident for c in column_groups if c.ident is not None),
    )
