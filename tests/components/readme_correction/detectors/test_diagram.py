"""The At a Glance diagram detector: redrawn when allowed, reported while it is not."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme.validation import registry as validation
from repository_presenter.components.readme_correction import model
from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
    order_edits,
)
from repository_presenter.components.readme_correction.detectors import diagram
from repository_presenter.components.readme_correction.detectors.diagram import (
    DETECTOR,
    at_a_glance_diagram,
)
from repository_presenter.components.readme_diagram import lint_source, parse, rebuild_readme

DIAGRAM = """\
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing OBJ, STL, or 3MF file"]
  end
  PRODUCT["Aspose.3D FOSS for Java"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Scene-graph construction and traversal"]
      c2["Mesh authoring and editing"]
      c3["Parameterized primitive geometry"]
    end
    subgraph capr[" "]
      direction TB
      c4["Lambert, Phong, and PBR material assignment"]
      c5["Polygon triangulation"]
      c6["Keyframe animation and skeletal pose data"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["OBJ, STL, or 3MF file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""

README = (
    "# Aspose.3D FOSS for Java\n\n## At a Glance\n\n```mermaid\n"
    + DIAGRAM
    + "```\n\n## Installation\n\nmvn install\n"
)

needs_the_shape = pytest.mark.skipif(
    not hasattr(model, "DIAGRAM_FIX"),
    reason="this build has no model.DIAGRAM_FIX correction kind yet",
)


def fixed(readme: str, edits: Any) -> str:
    kept, _ = order_edits(edits)
    corrected, spans = apply_edits(readme, kept)
    assert confinement_violations(readme, corrected, kept, spans) == []
    return corrected


def test_the_defective_diagram_is_reported_with_the_reason_it_is_not_yet_edited(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: False)
    result = at_a_glance_diagram(make_context(README))
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.detector == DETECTOR and finding.line == 6
    assert finding.text == "flowchart TD"
    assert "ORIENTATION_VERTICAL" in finding.reason and "CLIP_HTML_LABELS" in finding.reason
    assert "the running BC-07 still requires the vertical `flowchart TD` drawing" in finding.reason


def test_without_the_correction_shape_the_diagram_is_reported_even_if_the_validator_accepts(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: True)
    monkeypatch.delattr(model, "DIAGRAM_FIX", raising=False)
    result = at_a_glance_diagram(make_context(README))
    assert result.edits == ()
    assert "no correction kind that replaces a whole diagram body" in result.findings[0].reason


def test_the_validator_is_asked_directly_and_a_missing_probe_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    def accepts(body: str, has_inputs: bool) -> list[Any]:
        calls.append((body, has_inputs))
        return []

    monkeypatch.setattr(validation, "_topology_failures", accepts)
    assert diagram._validator_accepts("x", True) is True
    monkeypatch.setattr(validation, "_topology_failures", lambda body, has_inputs: ["no"])
    assert diagram._validator_accepts("x", False) is False
    assert calls == [("x", True)]
    monkeypatch.delattr(validation, "_topology_failures")
    assert diagram._validator_accepts("x", True) is False


def test_a_conforming_diagram_other_diagrams_and_indented_fences_are_left_alone(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: True)
    conforming = rebuild_readme(README).text
    for readme in (
        conforming,
        "# P\n\n```mermaid\nsequenceDiagram\n  A->>B: hi\n```\n",
        "# P\n\n- item\n\n  ```mermaid\n"
        + "".join(f"  {x}\n" for x in DIAGRAM.splitlines())
        + "  ```\n",
        "# P\n\nNo diagram here.\n",
    ):
        result = at_a_glance_diagram(make_context(readme))
        assert result.edits == () and result.findings == ()


@needs_the_shape
def test_the_diagram_is_redrawn_in_one_edit_and_nothing_else_changes(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: True)
    result = at_a_glance_diagram(make_context(README))
    assert result.findings == ()
    (edit,) = result.edits
    assert edit.kind == model.DIAGRAM_FIX and edit.detector == DETECTOR
    assert edit.original == DIAGRAM and edit.locators == ("README.md:6",)
    assert README[edit.start : edit.end] == DIAGRAM
    corrected = fixed(README, result.edits)
    assert corrected == rebuild_readme(README).text
    assert corrected.startswith(README[: edit.start]) and corrected.endswith(README[edit.end :])
    body = corrected.split("```mermaid\n", 1)[1].split("```\n", 1)[0]
    assert lint_source(body).conforming
    assert parse(body).glance == parse(DIAGRAM).glance


@needs_the_shape
def test_a_second_run_over_the_corrected_readme_finds_nothing(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: True)
    first = at_a_glance_diagram(make_context(README))
    corrected = fixed(README, first.edits)
    again = at_a_glance_diagram(make_context(corrected))
    assert again.edits == () and again.findings == ()


@needs_the_shape
def test_crlf_line_endings_are_kept(make_context: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: True)
    readme = README.replace("\n", "\r\n")
    result = at_a_glance_diagram(make_context(readme))
    corrected = fixed(readme, result.edits)
    assert "\n" not in corrected.replace("\r\n", "")
    assert at_a_glance_diagram(make_context(corrected)).edits == ()
