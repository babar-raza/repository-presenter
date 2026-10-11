"""The corrected README may not fail a check the live one did not already fail."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme_correction import check
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.model import CorrectionResult

README = """# Aspose.3D FOSS for Java

## Installation

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

## License

This project is licensed under the [MIT License](LICENSE).
"""


def test_a_correction_that_fixes_a_blocking_claim_introduces_nothing_and_resolves_it(
    make_context: Any,
) -> None:
    ctx = make_context(README)
    result = correct(ctx)
    delta = validation_delta(ctx, result, README.encode())
    assert delta["introduced"] == []
    assert {"check": "BC-14", "fewer": 1} in delta["resolved"]
    assert "BC-14" not in delta["corrected_failures"]


def test_a_text_that_adds_a_failure_is_reported_as_introduced(make_context: Any) -> None:
    ctx = make_context(README)
    worse = (
        README.replace("26.5.0", "26.6.0")
        + "\nStill 26.9.9 elsewhere: org.aspose:aspose-3d-foss:26.9.9\n"
    )
    delta = validation_delta(ctx, CorrectionResult(README, worse), README.encode())
    assert delta["introduced"] and delta["introduced"][0]["check"] == "BC-14"


def test_failures_the_live_readme_already_had_do_not_block_a_correction(make_context: Any) -> None:
    ctx = make_context(README + "\nSee the commercial-edition page.\n")
    delta = validation_delta(ctx, CorrectionResult(ctx.readme, ctx.readme), ctx.readme.encode())
    assert delta["introduced"] == [] and delta["corrected_failures"] == delta["live_failures"]


README_WITH_SECOND_H1 = (
    "# Aspose.3D FOSS for Java\n\n## Installation\n\nRun it.\n\n"
    "# Pin the `v26` module path.\n\nUse `v26` again.\n\n## License\n\nMIT.\n"
)


def test_text_a_structure_fix_merely_re_sections_is_revealed_not_introduced(
    make_context: Any,
) -> None:
    # Demoting the second H1 starts a new section in the judges' segmentation, so a code span the
    # maintainers wrote inside the deterministic Installation section is judged for the first
    # time. That failure was in the maintainers' text: "revealed", not "introduced".
    readme = README_WITH_SECOND_H1
    ctx = make_context(readme)
    result = correct(ctx)
    assert [e.detector for e in result.edits if e.detector == "second_h1"]
    delta = validation_delta(ctx, result, readme.encode())
    assert delta["introduced"] == []
    assert delta["revealed"] and delta["revealed"][0]["check"] == "BC-04"


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

README_WITH_DIAGRAM = (
    "# Aspose.3D FOSS for Java\n\n## At a Glance\n\n```mermaid\n"
    + DIAGRAM
    + "```\n\n## Installation\n\nmvn install\n"
)


def test_a_diagram_rebuild_is_judged_by_the_typed_r7_allowance_not_waved_through(
    make_context: Any,
) -> None:
    ctx = make_context(README_WITH_DIAGRAM)
    result = correct(ctx)
    assert [e.kind for e in result.edits if e.detector == "at_a_glance_diagram"] == ["DIAGRAM_FIX"]
    delta = validation_delta(ctx, result, README_WITH_DIAGRAM.encode())
    assert delta["introduced"] == []
    (allowed,) = delta["allowed"]
    assert allowed["check"] == "BC-07" and allowed["ruling"] == "R7"
    assert allowed["extra"] == len(allowed["details"]) >= 1
    assert all(detail.startswith("At a Glance") for detail in allowed["details"])
    assert (
        delta["corrected_failures"]["BC-07"] == delta["live_failures"]["BC-07"] + allowed["extra"]
    )


def test_without_the_allowance_the_same_rebuild_introduces_those_bc07_failures(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check, "ALLOWANCES", ())
    ctx = make_context(README_WITH_DIAGRAM)
    delta = validation_delta(ctx, correct(ctx), README_WITH_DIAGRAM.encode())
    assert [item["check"] for item in delta["introduced"]] == ["BC-07"] and delta["allowed"] == []


def test_the_allowance_covers_only_its_kind_its_check_and_its_wording() -> None:
    before: dict[str, list[str]] = {}
    at_a_glance = {"BC-07": ["At a Glance is a flowchart TD"]}
    introduced, allowed = check._split_allowed(before, at_a_glance, {"DIAGRAM_FIX"})
    assert introduced == [] and allowed[0]["ruling"] == "R7"
    introduced, allowed = check._split_allowed(before, at_a_glance, {"MISSING_INFO"})
    assert allowed == [] and introduced[0]["check"] == "BC-07"  # another kind is not covered
    other_wording = {"BC-07": ["Quick Start has 400 visible lines"]}
    introduced, allowed = check._split_allowed(before, other_wording, {"DIAGRAM_FIX"})
    assert allowed == [] and introduced[0]["details"] == other_wording["BC-07"]
    other_check = {"BC-03": ["At a Glance mentions an unsupported claim"]}
    introduced, allowed = check._split_allowed(before, other_check, {"DIAGRAM_FIX"})
    assert allowed == [] and introduced[0]["check"] == "BC-03"
    mixed = {"BC-07": ["At a Glance is a flowchart TD", "Quick Start has 400 visible lines"]}
    introduced, allowed = check._split_allowed(before, mixed, {"DIAGRAM_FIX"})
    assert allowed[0]["extra"] == 1 and introduced[0]["details"] == [mixed["BC-07"][1]]


def test_a_failure_another_edit_adds_beside_a_rebuild_is_still_introduced(
    make_context: Any,
) -> None:
    ctx = make_context(README_WITH_DIAGRAM)
    result = correct(ctx)
    worse = result.corrected + "\nStill 26.9.9 elsewhere: org.aspose:aspose-3d-foss:26.9.9\n"
    forged = CorrectionResult(
        result.original, worse, result.edits, result.output_spans, result.findings
    )
    delta = validation_delta(ctx, forged, README_WITH_DIAGRAM.encode())
    assert [item["check"] for item in delta["introduced"]] == ["BC-14"]
    assert delta["allowed"]  # the rebuild's own allowance is still reported
