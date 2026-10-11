"""The At a Glance diagram detector: redrawn when the horizontal contract accepts it."""

from __future__ import annotations

from pathlib import Path
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


def test_the_defective_diagram_is_reported_when_the_rebuild_would_fail_the_contract_anew(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diagram, "_introduced", lambda live, after, has_inputs: ["a new failure"])
    result = at_a_glance_diagram(make_context(README))
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.detector == DETECTOR and finding.line == 6
    assert finding.text == "flowchart TD"
    assert "ORIENTATION_VERTICAL" in finding.reason and "CLIP_HTML_LABELS" in finding.reason
    assert "would fail it anew: a new failure" in finding.reason


def test_the_horizontal_contract_is_asked_and_only_what_is_new_to_it_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Failure:
        def __init__(self, message: str) -> None:
            self.message = message

    asked: list[tuple[str, bool]] = []

    def judge(body: str, has_inputs: bool) -> list[Any]:
        asked.append((body, has_inputs))
        return [Failure("old ceiling")] + ([Failure("new one")] if body == "after" else [])

    monkeypatch.setattr(contract, "topology_failures", judge)
    assert diagram._introduced("live", "after", True) == ["new one"]
    assert diagram._kept_ceilings("live", "after", True) == 1
    assert diagram._introduced("live", "live", True) == []
    assert asked[0] == ("live", True) and asked[1] == ("after", True)


def test_the_rebuilt_diagram_passes_the_real_contract_without_any_patching(
    make_context: Any,
) -> None:
    result = at_a_glance_diagram(make_context(README))
    assert result.findings == () and len(result.edits) == 1
    assert contract.topology_failures(result.edits[0].replacement, True) == []
    assert "ceiling" not in result.edits[0].rationale


FIXTURES = Path(__file__).parents[2] / "readme_diagram" / "fixtures" / "live"


def test_a_diagram_whose_content_exceeds_the_regeneration_ceilings_is_still_redrawn(
    make_context: Any,
) -> None:
    # Cells for Java lists 15 capabilities where the contract writes at most 8: the maintainers'
    # words stay, only the drawing changes, and the edit says so.
    body = (FIXTURES / "aspose-cells-foss__Aspose.Cells-FOSS-for-Java.mmd").read_text(
        encoding="utf-8"
    )
    head = chr(10).join(["# Aspose.Cells FOSS for Java", "", "## At a Glance", "", "```mermaid"])
    readme = head + chr(10) + body.rstrip(chr(10)) + chr(10) + "```" + chr(10)
    live = contract.topology_failures(body, True)
    assert any("at most 8" in failure.message for failure in live)
    result = at_a_glance_diagram(make_context(readme))
    assert result.findings == () and len(result.edits) == 1
    (edit,) = result.edits
    assert "regeneration ceiling" in edit.rationale
    after = contract.topology_failures(edit.replacement, True)
    assert {f.message for f in after} <= {f.message for f in live}
    assert all(f.stage == "PLANNING" for f in after)  # no composing failure is left


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


def test_a_label_with_angle_brackets_is_not_redrawn_because_no_encoding_is_portable(
    make_context: Any,
) -> None:
    # Measured on Mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 with htmlLabels off: `#lt;`, `#60;`
    # and `&lt;` show as literal entity text before 11.14, and a raw `<u8>` is dropped as a tag.
    risky = README.replace("Polygon triangulation", "Vec<u8> buffers")
    result = at_a_glance_diagram(make_context(risky))
    assert result.edits == ()
    (finding,) = result.findings
    assert "holds & < or >" in finding.reason and "11.4.1" in finding.reason
