"""The At a Glance diagram detector: redrawn when the horizontal contract accepts it."""

from __future__ import annotations

from typing import Any

import pytest

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
from repository_presenter.components.readme_diagram import (
    contract,
    lint_source,
    parse,
    rebuild_readme,
)

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


def fixed(readme: str, edits: Any) -> str:
    kept, _ = order_edits(edits)
    corrected, spans = apply_edits(readme, kept)
    assert confinement_violations(readme, corrected, kept, spans) == []
    return corrected


def test_the_defective_diagram_is_reported_when_the_contract_rejects_the_rebuild(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_validator_accepts", lambda body, has_inputs: False)
    result = at_a_glance_diagram(make_context(README))
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.detector == DETECTOR and finding.line == 6
    assert finding.text == "flowchart TD"
    assert "ORIENTATION_VERTICAL" in finding.reason and "CLIP_HTML_LABELS" in finding.reason
    assert "the horizontal At a Glance contract rejects the redrawn diagram" in finding.reason


def test_the_horizontal_contract_is_asked_not_the_running_bc07(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    def asked(body: str, has_inputs: bool) -> list[Any]:
        calls.append((body, has_inputs))
        return []

    monkeypatch.setattr(contract, "topology_failures", asked)
    assert diagram._validator_accepts("x", True) is True
    monkeypatch.setattr(contract, "topology_failures", lambda body, has_inputs: ["no"])
    assert diagram._validator_accepts("x", False) is False
    assert calls == [("x", True)]


def test_the_rebuilt_diagram_passes_the_real_contract_without_any_patching(
    make_context: Any,
) -> None:
    result = at_a_glance_diagram(make_context(README))
    assert result.findings == () and len(result.edits) == 1
    assert contract.topology_failures(result.edits[0].replacement, True) == []


def test_a_conforming_diagram_other_diagrams_and_indented_fences_are_left_alone(
    make_context: Any,
) -> None:
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


def test_the_diagram_is_redrawn_in_one_edit_and_nothing_else_changes(
    make_context: Any,
) -> None:
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


def test_a_second_run_over_the_corrected_readme_finds_nothing(make_context: Any) -> None:
    first = at_a_glance_diagram(make_context(README))
    corrected = fixed(README, first.edits)
    again = at_a_glance_diagram(make_context(corrected))
    assert again.edits == () and again.findings == ()


def test_crlf_line_endings_are_kept(make_context: Any) -> None:
    readme = README.replace("\n", "\r\n")
    result = at_a_glance_diagram(make_context(readme))
    corrected = fixed(readme, result.edits)
    assert "\n" not in corrected.replace("\r\n", "")
    assert at_a_glance_diagram(make_context(corrected)).edits == ()
