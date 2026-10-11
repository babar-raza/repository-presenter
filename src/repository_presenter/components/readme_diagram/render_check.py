"""The real-render check: draw the diagram in a browser and measure what a reader would see.

``geometry.py`` and ``lint.py`` model clipping and orientation; this module settles them by
rendering. ``render/measure.mjs`` (Node, the pinned ``mermaid`` package, headless Chrome or Edge)
renders each source and reports every node and cluster box and label box, natively and again with
the page forced into each of several wider fonts (the way a hosted renderer ends up clipping text
measured in a different font). ``check_entry`` turns that report into failures:

* no HTML ``foreignObject`` label is left (``htmlLabels: false`` was honoured);
* Starting Points, the product, Core Capabilities and Outputs sit left to right and side by side;
* every node is where the contract puts it: one input/capability/output column top to bottom in
  reading order, two capability columns left to right, every label's text intact and drawn on the
  lines the width model gave it;
* no label's text exceeds its box, natively or in any stress font.

The renderer is optional tooling: ``find_renderer`` returns ``None`` unless ``RP_MERMAID_TOOLS``
names a directory installed from ``render/package.json`` and a ``node`` is on ``PATH`` (or
``RP_NODE``), and the tests that need it skip. Nothing here uses the network: the page is built in
memory and the browser is only asked to draw it.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_diagram.build import line_budget_px, node_ids
from repository_presenter.components.readme_diagram.geometry import text_px, wrap_label
from repository_presenter.components.readme_diagram.model import Glance

MEASURE_SCRIPT = Path(__file__).parent / "render" / "measure.mjs"
#: The browser fonts the page is forced into after the diagram is measured.
STRESS_FONTS = ("Arial", "Verdana", "Tahoma", "Segoe UI", "Georgia")
#: The stress fonts the width model's envelope was measured in: in these, no label's drawn text may
#: be wider than the model says (Georgia was not measured; it is only held to fitting its box).
ENVELOPE_FONTS = ("Arial", "Verdana", "Tahoma", "Segoe UI")
#: The mermaid packages ``render/package.json`` installs; the first is the one the project targets.
PACKAGES = ("mermaid", "mermaid_11_4_1", "mermaid_11_12_0", "mermaid_12_1_0")
#: A diagram wider than this is shrunk past reading by a README column.
MAX_RENDER_WIDTH = 1600
#: How far a label may exceed its box before it is called clipped (sub-pixel rounding).
TOLERANCE_PX = 1.0


class RenderError(RuntimeError):
    """The renderer could not produce a measurement (not a failed check)."""


@dataclass(frozen=True)
class Renderer:
    tools: Path
    node: str


@dataclass(frozen=True)
class RenderRun:
    """One ``measure`` call: the mermaid release and browser used, and one entry per source."""

    mermaid: str
    browser: str
    entries: dict[str, dict[str, Any]]


def find_renderer(environ: Mapping[str, str] | None = None) -> Renderer | None:
    """The installed renderer, or ``None`` when this machine has none."""
    env = os.environ if environ is None else environ
    tools = env.get("RP_MERMAID_TOOLS")
    if not tools or not (Path(tools) / "node_modules" / "puppeteer-core").is_dir():
        return None
    node = env.get("RP_NODE") or shutil.which("node")
    if not node:
        return None
    return Renderer(Path(tools), node)


def installed_packages(renderer: Renderer) -> tuple[str, ...]:
    """The mermaid releases of ``PACKAGES`` present in the tool directory."""
    modules = renderer.tools / "node_modules"
    return tuple(
        name for name in PACKAGES if (modules / name / "dist" / "mermaid.min.js").is_file()
    )


def measure(
    renderer: Renderer,
    sources: Mapping[str, str],
    *,
    package: str = "mermaid",
    fonts: tuple[str, ...] = STRESS_FONTS,
    png_dir: Path | None = None,
    environ: Mapping[str, str] | None = None,
    timeout: float = 900,
) -> RenderRun:
    """Render every source (name to Mermaid text) and measure it; one browser launch in all."""
    env = dict(os.environ if environ is None else environ)
    env["RP_MERMAID_TOOLS"] = str(renderer.tools)
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        names: dict[str, str] = {}
        paths: list[str] = []
        for index, (name, text) in enumerate(sources.items()):
            key = f"d{index:03d}"
            names[key] = name
            path = root / f"{key}.mmd"
            path.write_text(text, encoding="utf-8", newline="\n")
            paths.append(str(path))
        out = root / "result.json"
        command = [
            renderer.node,
            str(MEASURE_SCRIPT),
            "--out",
            str(out),
            "--package",
            package,
            "--fonts",
            ",".join(fonts),
        ]
        if png_dir is not None:
            command += ["--png-dir", str(png_dir)]
        done = subprocess.run(
            [*command, *paths],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            check=False,
        )
        if done.returncode != 0 or not out.is_file():
            raise RenderError(f"measure.mjs failed ({done.returncode}): {done.stderr[-400:]}")
        report = json.loads(out.read_text(encoding="utf-8"))
    entries = {names[entry["name"]]: entry for entry in report["results"]}
    return RenderRun(str(report["mermaid"]), str(report["browser"]), entries)


def _rect(shape: Mapping[str, float]) -> tuple[float, float, float, float]:
    return shape["x"], shape["y"], shape["x"] + shape["w"], shape["y"] + shape["h"]


def orientation(entry: Mapping[str, Any]) -> str:
    """``horizontal`` when the mother blocks sit left to right side by side, ``vertical`` when
    stacked top to bottom, ``mixed`` otherwise, ``n/a`` with fewer than two blocks."""
    shapes = {c["id"]: c["shape"] for c in entry["native"]["clusters"]}
    blocks = [shapes[k] for k in ("StartingPoints", "Capabilities", "Outputs") if k in shapes]
    if len(blocks) < 2:
        return "n/a"

    def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    pairs = list(pairwise(blocks))
    horizontal = all(
        _rect(a)[2] <= _rect(b)[0] + 2
        and overlap(_rect(a)[1], _rect(a)[3], _rect(b)[1], _rect(b)[3]) > 0.3 * min(a["h"], b["h"])
        for a, b in pairs
    )
    vertical = all(
        _rect(a)[3] <= _rect(b)[1] + 2
        and overlap(_rect(a)[0], _rect(a)[2], _rect(b)[0], _rect(b)[2]) > 0.1 * min(a["w"], b["w"])
        for a, b in pairs
    )
    return "horizontal" if horizontal else ("vertical" if vertical else "mixed")


def spills(snapshot: Mapping[str, Any]) -> list[str]:
    """Every node or cluster whose label text exceeds its box (or its HTML clip box)."""
    found = []
    for item in (*snapshot["nodes"], *snapshot["clusters"]):
        over = max(item["spill_x"], item["spill_y"], item["clip_x"], item["clip_y"])
        if over > TOLERANCE_PX:
            found.append(f"{item['id'] or 'cluster'} by {over:.0f}px")
    return found


def clipped_fonts(entry: Mapping[str, Any]) -> dict[str, int]:
    """For each stress font, how many labels exceed their box in it."""
    return {font: len(spills(snapshot)) for font, snapshot in entry["stress"].items()}


def _squash(text: str) -> str:
    """``text`` with entities decoded and whitespace removed: SVG text joins its lines with no
    space, and Mermaid before 11.14 draws ``&``, ``<`` and ``>`` as entity text."""
    return re.sub(r"\s+", "", html.unescape(text))


def split_words(label: str, drawn_lines: list[str]) -> list[str]:
    """The words of ``label`` that ``drawn_lines`` (what the browser drew, line by line) break in
    the middle: the lines read back as words differ from the label's words by a split token
    ("password-protec" / "ted)"). Empty when every break falls between words."""
    wanted = label.split()
    drawn = " ".join(drawn_lines).split()
    if drawn == wanted:
        return []
    pieces = set(drawn) - set(wanted)
    return sorted(pieces) or ["(words differ)"]


def _split_failures(entry: Mapping[str, Any], glance: Glance) -> list[str]:
    """Every label (node or group title) drawn with a word broken across two lines, on this
    release. Nodes are held to their own label, group titles to one of the diagram's titles."""
    native = entry["native"]
    failures: list[str] = []
    expected = node_ids(glance)
    for node in native["nodes"]:
        lines = node.get("line_texts")
        label = expected.get(node["id"])
        if not lines or label is None:
            continue
        broken = split_words(html.unescape(label), [html.unescape(line) for line in lines])
        if broken:
            failures.append(f"{node['id']} breaks a word across lines: {broken}")
    titles = [html.unescape(title).split() for title in glance.titles]
    for cluster in native["clusters"]:
        lines = cluster.get("line_texts")
        if not lines or not titles:
            continue
        drawn = " ".join(html.unescape(line) for line in lines).split()
        if drawn and drawn not in titles:
            failures.append(f"{cluster['id'] or 'cluster'} breaks a word across lines: {drawn}")
    return failures


def _column_failures(
    group: str, ids: list[str], nodes: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    boxes = [_rect(nodes[i]["shape"]) for i in ids if i in nodes]
    if not boxes or len(boxes) != len(ids):
        return []  # a missing node is reported by the id check
    failures = []
    for (_, top_a, _, bottom_a), (_, top_b, _, _) in pairwise(boxes):
        if top_b < bottom_a - 1 or top_b <= top_a:
            failures.append(f"{group}: {ids} are not in reading order from top to bottom")
            break
    left = max(box[0] for box in boxes)
    right = min(box[2] for box in boxes)
    if left >= right:
        failures.append(f"{group}: {ids} do not share one column")
    return failures


def _model_failures(entry: Mapping[str, Any], glance: Glance) -> list[str]:
    """Where the browser draws a label wider than ``geometry.text_px`` says it can be.

    The width model is the envelope of the measured fonts, so in each of them the drawn text of a
    node (its widest line) must not exceed the model's widest line plus a pixel of rounding."""
    budget = line_budget_px(glance)
    failures: list[str] = []
    for font in ENVELOPE_FONTS:
        snapshot = entry["stress"].get(font)
        if snapshot is None:
            continue
        for node in snapshot["nodes"]:
            label = node_ids(glance).get(node["id"])
            if label is None:
                continue
            widest = max(text_px(line) for line in wrap_label(label, budget))
            if node["text_rect"]["w"] > widest + 1.0:
                failures.append(
                    f"in {font}: {node['id']} is drawn {node['text_rect']['w']:.0f}px wide, "
                    f"the model allows {widest:.0f}px"
                )
    return failures


def check_entry(
    entry: Mapping[str, Any], glance: Glance, *, columns_in_order: bool = True
) -> list[str]:
    """Every way the render of ``glance`` falls short of the contract; empty means it holds.

    ``columns_in_order`` is the one release-dependent expectation: the first capability column is
    drawn left of the second. It holds on every Mermaid 11 release measured; Mermaid 12.1 orders
    two sibling columns by its own heuristic (20 of 23 reversed), so a 12.x run passes ``False``
    and is held only to the two columns standing side by side."""
    if entry.get("error"):
        return [f"render failed: {entry['error']}"]
    native = entry["native"]
    failures: list[str] = []
    if native["foreign_objects"]:
        failures.append(
            f"{native['foreign_objects']} HTML foreignObject label boxes drawn: htmlLabels was "
            "not honoured, so a wider font clips them"
        )
    if (shape := orientation(entry)) not in {"horizontal", "n/a"}:
        failures.append(f"the mother blocks are {shape}, not left to right")
    nodes = {n["id"]: n for n in native["nodes"]}
    expected = node_ids(glance)
    missing = sorted(set(expected) - set(nodes))
    if missing:
        failures.append(f"nodes not drawn: {missing}")
    budget = line_budget_px(glance)
    for ident, label in expected.items():
        node = nodes.get(ident)
        if node is None:
            continue
        if _squash(node["text"]) != _squash(label):
            failures.append(f"{ident} draws {node['text']!r}, not {label!r}")
        want = len(wrap_label(label, budget))
        if node["lines"] < want:
            failures.append(f"{ident} is drawn on {node['lines']} lines, the model gives {want}")
    inputs = [f"i{n}" for n in range(1, len(glance.starting_points) + 1)]
    outputs = [f"o{n}" for n in range(1, len(glance.outputs) + 1)]
    failures += _column_failures("Starting Points", inputs, nodes)
    failures += _column_failures("Outputs", outputs, nodes)
    first = 1
    column_ids: list[list[str]] = []
    for column in glance.capability_columns:
        column_ids.append([f"c{n}" for n in range(first, first + len(column))])
        first += len(column)
    for index, ids in enumerate(column_ids):
        failures += _column_failures(f"capability column {index + 1}", ids, nodes)
    if len(column_ids) == 2 and all(i in nodes for ids in column_ids for i in ids):
        left_boxes = [_rect(nodes[i]["shape"]) for i in column_ids[0]]
        right_boxes = [_rect(nodes[i]["shape"]) for i in column_ids[1]]
        first_right = max(b[2] for b in left_boxes)
        second_left = min(b[0] for b in right_boxes)
        second_right = max(b[2] for b in right_boxes)
        first_left = min(b[0] for b in left_boxes)
        if columns_in_order and first_right > second_left:
            failures.append("the second capability column is not to the right of the first")
        elif not columns_in_order and first_right > second_left and second_right > first_left:
            failures.append("the two capability columns are not side by side")
    failures += _split_failures(entry, glance)
    failures += _model_failures(entry, glance)
    failures += [f"native: {item} exceeds its box" for item in spills(native)]
    for font, snapshot in entry["stress"].items():
        failures += [f"in {font}: {item} exceeds its box" for item in spills(snapshot)]
    if entry["svg"]["w"] > MAX_RENDER_WIDTH:
        failures.append(
            f"the drawing is {entry['svg']['w']:.0f}px wide; a README column shrinks it too far"
        )
    return failures
