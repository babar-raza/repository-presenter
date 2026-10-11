"""The real-render check: its verdict logic offline, and the live diagrams drawn in a browser.

The first half builds measurement reports by hand and needs nothing installed. The second half
renders for real with the pinned ``mermaid`` releases in a headless Chrome or Edge and skips
unless ``RP_MERMAID_TOOLS`` names an install of ``render/package.json`` (see ``render_check.py``).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme_diagram import (
    Glance,
    balanced_columns,
    build_body,
    parse,
)
from repository_presenter.components.readme_diagram import render_check as rc
from repository_presenter.components.readme_diagram.build import line_budget_px, node_ids
from repository_presenter.components.readme_diagram.geometry import text_px, wrap_label

CAPS = tuple(f"Capability {n} of the product" for n in range(1, 7))
GLANCE = Glance(
    "Aspose.Cells FOSS for Go",
    ("An existing XLSX workbook", "CSV files"),
    balanced_columns(CAPS),
    ("XLSX workbooks",),
)


def _node(glance: Glance, ident: str, label: str, x: float, y: float) -> dict[str, Any]:
    budget = line_budget_px(glance)
    lines = wrap_label(label, budget)
    width = max(text_px(line) for line in lines)
    return {
        "id": ident,
        "text": " ".join(lines),
        "lines": len(lines),
        "mode": "svg",
        "shape": {"x": x, "y": y, "w": width + 24, "h": 20 * len(lines) + 24},
        "text_rect": {"x": x + 12, "y": y + 12, "w": width, "h": 20 * len(lines)},
        "spill_x": 0.0,
        "spill_y": 0.0,
        "clip_x": 0.0,
        "clip_y": 0.0,
    }


def _snapshot(glance: Glance, *, vertical: bool = False, swap: bool = False) -> dict[str, Any]:
    ids = node_ids(glance)
    origin = {"i": (0, 0), "P": (300, 0), "c": (560, 0), "o": (1100, 0)}
    if vertical:
        origin = {"i": (0, 0), "P": (0, 300), "c": (0, 500), "o": (0, 1300)}
    sizes = [len(c) for c in glance.capability_columns]
    nodes = []
    for ident, label in ids.items():
        kind = ident[0]
        gx, gy = origin[kind]
        if kind == "c":
            number = int(ident[1:])
            column = 0 if number <= sizes[0] else 1
            row = number - 1 if column == 0 else number - 1 - sizes[0]
            nodes.append(
                _node(glance, ident, label, gx + 260 * (column ^ int(swap)), gy + row * 70)
            )
        else:
            number = 0 if ident == "PRODUCT" else int(ident[1:]) - 1
            nodes.append(_node(glance, ident, label, gx, gy + number * 70))

    def box(prefix: str) -> dict[str, float]:
        owned = [n["shape"] for n in nodes if n["id"].startswith(prefix)]
        x0 = min(s["x"] for s in owned) - 20
        y0 = min(s["y"] for s in owned) - 30
        return {
            "x": x0,
            "y": y0,
            "w": max(s["x"] + s["w"] for s in owned) + 20 - x0,
            "h": max(s["y"] + s["h"] for s in owned) + 20 - y0,
        }

    shape = {"mode": "svg", "spill_x": 0.0, "spill_y": 0.0, "clip_x": 0.0, "clip_y": 0.0}
    clusters = []
    for ident, title, prefix, present in (
        ("StartingPoints", "Starting Points", "i", bool(glance.starting_points)),
        ("Capabilities", "Core Capabilities", "c", True),
        ("Outputs", "Outputs", "o", bool(glance.outputs)),
    ):
        if present:
            clusters.append({"id": ident, "text": title, "shape": box(prefix), **shape})
    return {"foreign_objects": 0, "nodes": nodes, "clusters": clusters}


def _entry(glance: Glance = GLANCE, **kwargs: Any) -> dict[str, Any]:
    native = _snapshot(glance, **kwargs)
    return {
        "name": "d000",
        "svg": {"w": 1200.0, "h": 600.0},
        "native": native,
        "stress": {font: copy.deepcopy(native) for font in rc.STRESS_FONTS},
    }


def test_a_well_formed_report_has_no_failures() -> None:
    entry = _entry()
    assert rc.orientation(entry) == "horizontal"
    assert rc.check_entry(entry, GLANCE) == []
    assert rc.clipped_fonts(entry) == dict.fromkeys(rc.STRESS_FONTS, 0)


def test_stacked_blocks_are_reported_as_vertical() -> None:
    entry = _entry(vertical=True)
    assert rc.orientation(entry) == "vertical"
    assert any("vertical, not left to right" in f for f in rc.check_entry(entry, GLANCE))


def test_html_label_boxes_are_a_failure_whatever_fits() -> None:
    entry = _entry()
    entry["native"]["foreign_objects"] = 19
    assert any("19 HTML foreignObject" in f for f in rc.check_entry(entry, GLANCE))


def test_a_label_wider_than_its_box_fails_natively_and_in_each_stress_font() -> None:
    entry = _entry()
    entry["native"]["nodes"][3]["spill_x"] = 7.0
    entry["stress"]["Verdana"]["nodes"][4]["clip_y"] = 24.0
    entry["stress"]["Georgia"]["clusters"][0]["spill_x"] = 3.0
    failures = rc.check_entry(entry, GLANCE)
    assert any(f.startswith("native:") and "by 7px" in f for f in failures)
    assert any(f.startswith("in Verdana:") and "by 24px" in f for f in failures)
    assert any(f.startswith("in Georgia:") for f in failures)
    assert rc.clipped_fonts(entry)["Verdana"] == 1 and rc.clipped_fonts(entry)["Arial"] == 0


def test_sub_pixel_rounding_is_not_clipping() -> None:
    entry = _entry()
    entry["native"]["nodes"][0]["spill_x"] = 0.6
    assert rc.check_entry(entry, GLANCE) == []


def test_the_capability_columns_must_stand_left_to_right_in_reading_order() -> None:
    swapped = _entry(swap=True)
    assert any("not to the right of the first" in f for f in rc.check_entry(swapped, GLANCE))
    # Mermaid 12.1 orders sibling columns by its own heuristic: side by side is what is held.
    assert rc.check_entry(swapped, GLANCE, columns_in_order=False) == []
    overlapping = _entry()
    for node in overlapping["native"]["nodes"]:
        if node["id"] in {"c4", "c5", "c6"}:
            node["shape"]["x"] = 560
    assert any(
        "not side by side" in f for f in rc.check_entry(overlapping, GLANCE, columns_in_order=False)
    )


def test_a_column_out_of_reading_order_and_a_missing_node_fail() -> None:
    entry = _entry()
    c1, c2 = (n for n in entry["native"]["nodes"] if n["id"] in {"c1", "c2"})
    c1["shape"]["y"], c2["shape"]["y"] = c2["shape"]["y"], c1["shape"]["y"]
    assert any("reading order" in f for f in rc.check_entry(entry, GLANCE))
    entry = _entry()
    entry["native"]["nodes"] = [n for n in entry["native"]["nodes"] if n["id"] != "o1"]
    assert any("nodes not drawn: ['o1']" in f for f in rc.check_entry(entry, GLANCE))


def test_a_label_drawn_with_other_words_or_fewer_lines_than_the_model_fails() -> None:
    entry = _entry()
    entry["native"]["nodes"][5]["text"] = "something else entirely"
    assert any("draws 'something else entirely'" in f for f in rc.check_entry(entry, GLANCE))
    entry = _entry()
    next(n for n in entry["native"]["nodes"] if n["id"] == "c1")["lines"] = 1
    assert any("c1 is drawn on 1 lines" in f for f in rc.check_entry(entry, GLANCE))


def test_entity_text_and_joined_lines_are_not_a_different_label() -> None:
    glance = Glance("P", (), (("Vec<u8> and more words here", "B", "C"),), ())
    entry = _entry(glance)
    node = next(n for n in entry["native"]["nodes"] if n["id"] == "c1")
    node["text"] = node["text"].replace("<", "&lt;").replace(">", "&gt;")
    for snapshot in entry["stress"].values():
        snapshot["nodes"] = copy.deepcopy(entry["native"]["nodes"])
    assert rc.check_entry(entry, glance) == []


def test_a_font_that_draws_a_label_wider_than_the_model_allows_is_caught() -> None:
    entry = _entry()
    next(n for n in entry["stress"]["Verdana"]["nodes"] if n["id"] == "c2")["text_rect"]["w"] = 900
    assert any("the model allows" in f for f in rc.check_entry(entry, GLANCE))


def test_a_drawing_too_wide_for_a_readme_column_fails() -> None:
    entry = _entry()
    entry["svg"]["w"] = rc.MAX_RENDER_WIDTH + 1
    assert any("wide; a README column" in f for f in rc.check_entry(entry, GLANCE))


def test_a_failed_render_is_a_failure_not_a_pass() -> None:
    assert rc.check_entry({"name": "d000", "error": "Parse error"}, GLANCE) == [
        "render failed: Parse error"
    ]


def test_no_renderer_is_reported_as_none_not_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert rc.find_renderer({}) is None
    tools = {"RP_MERMAID_TOOLS": str(tmp_path)}
    assert rc.find_renderer(tools) is None  # nothing installed there
    (tmp_path / "node_modules" / "puppeteer-core").mkdir(parents=True)
    monkeypatch.setattr(rc.shutil, "which", lambda name: None)
    assert rc.find_renderer(tools) is None  # installed, but no node
    assert rc.find_renderer({**tools, "RP_NODE": "node"}) == rc.Renderer(tmp_path, "node")


# ---- the real render ----------------------------------------------------------------------------

SAMPLE = (
    "aspose-3d-foss__Aspose.3D-FOSS-for-Python",  # two columns of four, one input
    "aspose-words-foss__Aspose.Words-FOSS-for-.NET",  # three inputs, four outputs, two columns
    "aspose-email-foss__Aspose.Email-FOSS-for-Python",  # one column of five
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Rust",  # Vec<u8> in a label
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Java",  # fifteen capabilities, long labels
    "aspose-psd-foss__Aspose.PSD-FOSS-for-Python",  # hand-broken labels
)


def _check(renderer: rc.Renderer, sources: dict[str, str], package: str) -> dict[str, list[str]]:
    glances = {name: parse(body).glance for name, body in sources.items()}
    run = rc.measure(renderer, {n: build_body(g) for n, g in glances.items()}, package=package)
    in_order = not package.endswith("12_1_0")
    return {
        name: rc.check_entry(entry, glances[name], columns_in_order=in_order)
        for name, entry in run.entries.items()
    }


def test_every_live_diagram_rebuilt_renders_horizontally_without_clipping(
    renderer: rc.Renderer, live: dict[str, str]
) -> None:
    failures = {n: f for n, f in _check(renderer, live, "mermaid").items() if f}
    assert failures == {}


@pytest.mark.parametrize("package", rc.PACKAGES[1:])
def test_the_same_holds_on_older_and_newer_mermaid_releases(
    renderer: rc.Renderer, live: dict[str, str], package: str
) -> None:
    if package not in rc.installed_packages(renderer):
        pytest.skip(f"{package} is not installed in the tool directory")
    sample = {name: live[name] for name in SAMPLE}
    without_inputs = next(n for n, s in live.items() if not parse(s).glance.starting_points)
    sample[without_inputs] = live[without_inputs]
    failures = {n: f for n, f in _check(renderer, sample, package).items() if f}
    assert failures == {}


def test_the_live_originals_fail_the_same_check(
    renderer: rc.Renderer, live: dict[str, str]
) -> None:
    """The check bites: the diagrams as the maintainers hold them are vertical and clip."""
    names = SAMPLE[:3]
    glances = {name: parse(live[name]).glance for name in names}
    run = rc.measure(renderer, {name: live[name] for name in names})
    for name, entry in run.entries.items():
        failures = rc.check_entry(entry, glances[name])
        assert rc.orientation(entry) == "vertical", name
        assert any("vertical, not left to right" in f for f in failures), name
        assert any("foreignObject" in f for f in failures), name
        clipped = rc.clipped_fonts(entry)
        assert sum(1 for count in clipped.values() if count) >= 2, (name, clipped)
        assert any(f.startswith("in ") and "exceeds its box" in f for f in failures), name


def test_the_shipped_pins_are_the_releases_the_investigation_measured(
    renderer: rc.Renderer,
) -> None:
    run = rc.measure(renderer, {"x": build_body(GLANCE)}, package="mermaid")
    assert run.mermaid == "11.17.2"


# ---- a word split across two lines --------------------------------------------------------------
def test_a_word_broken_across_two_lines_is_told_from_a_break_between_words() -> None:
    label = "An existing XLSX workbook (including password-protected)"
    assert (
        rc.split_words(label, ["An existing XLSX", "workbook (including", "password-protected)"])
        == []
    )
    broken = rc.split_words(
        label, ["An existing XLSX", "workbook (including", "password-protec", "ted)"]
    )
    assert broken == ["password-protec", "ted)"]


def test_a_node_drawn_with_a_split_word_fails_the_entry_on_any_release() -> None:
    entry = _entry()
    node = next(n for n in entry["native"]["nodes"] if n["id"] == "c1")
    label = node_ids(GLANCE)["c1"]
    node["line_texts"] = [label[:6], label[6:]]  # breaks "Capability" in the middle
    assert any("breaks a word across lines" in f for f in rc.check_entry(entry, GLANCE))
    node["line_texts"] = [" ".join(label.split()[:2]), " ".join(label.split()[2:])]
    assert not any("breaks a word" in f for f in rc.check_entry(entry, GLANCE))


def test_no_live_diagram_rebuilt_splits_a_word_on_any_installed_release(
    renderer: rc.Renderer, live: dict[str, str]
) -> None:
    glances = {name: parse(body).glance for name, body in live.items()}
    for package in rc.installed_packages(renderer):
        run = rc.measure(
            renderer,
            {n: build_body(g) for n, g in glances.items()},
            package=package,
            fonts=("Arial",),
        )
        splits = {
            name: rc._split_failures(entry, glances[name]) for name, entry in run.entries.items()
        }
        assert {n: s for n, s in splits.items() if s} == {}, package


def test_without_the_wrapping_width_mermaid_12_breaks_words_and_the_check_sees_it(
    renderer: rc.Renderer, live: dict[str, str]
) -> None:
    if "mermaid_12_1_0" not in rc.installed_packages(renderer):
        pytest.skip("mermaid 12.1.0 is not installed in the tool directory")
    glances = {name: parse(body).glance for name, body in live.items()}
    old = {n: build_body(g).replace(', "wrappingWidth": 400', "") for n, g in glances.items()}
    assert all("wrappingWidth" not in body for body in old.values())
    run = rc.measure(renderer, old, package="mermaid_12_1_0", fonts=("Arial",))
    broken = [n for n, e in run.entries.items() if rc._split_failures(e, glances[n])]
    assert broken, "the negative control found no split word: the check would not bite"
