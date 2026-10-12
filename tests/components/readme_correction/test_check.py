"""The corrected README may not fail a check the live one did not already fail."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme.composition.renderer import line_counts
from repository_presenter.components.readme_correction import check
from repository_presenter.components.readme_correction.apply import apply_edits
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.model import CorrectionResult
from repository_presenter.components.readme_correction.settle import correct_settled

NL = chr(10)

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
    assert delta["revealed"][0]["caused_by"] == ["second_h1"]  # the one structure fix there is


BOTH_STRUCTURE_FIXES = (
    "# Aspose.3D FOSS for Java\n\n## Installation\n\nRun it.\n\n"
    "# A note\n\nPlain words.\n\n"
    "<details>\n<summary>More</summary>\n\nUse it.\n\n## License\n\nMIT.\n"
)


def test_a_revealed_failure_names_the_structure_fix_that_brings_it_alone(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Two structure fixes; the judges find a new failure only once the <details> block is closed.
    # The record must say that fix did it, not leave the pull request to guess between the two.
    ctx = make_context(BOTH_STRUCTURE_FIXES)
    result = correct(ctx)
    fixes = sorted(e.detector for e in result.edits if e.kind == "STRUCTURE_FIX")
    assert fixes == ["second_h1", "unclosed_details"]
    opened = BOTH_STRUCTURE_FIXES.count("</details>")

    def judged(_ctx: Any, text: str, _original: bytes, _revision: str) -> dict[str, list[str]]:
        found = text.count("</details>") > opened
        return {"BC-04": ["code span 'v26' is not a fact value"]} if found else {}

    monkeypatch.setattr(check, "_failures", judged)
    delta = validation_delta(ctx, result, BOTH_STRUCTURE_FIXES.encode())
    assert [i["caused_by"] for i in delta["revealed"]] == [["unclosed_details"]]


def test_a_revealed_failure_no_single_fix_brings_names_every_structure_fix(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = make_context(BOTH_STRUCTURE_FIXES)
    result = correct(ctx)
    opened = BOTH_STRUCTURE_FIXES.count("</details>")

    def judged(_ctx: Any, text: str, _original: bytes, _revision: str) -> dict[str, list[str]]:
        both = text.count("</details>") > opened and "\n## A note\n" in text
        return {"BC-04": ["code span 'v26' is not a fact value"]} if both else {}

    monkeypatch.setattr(check, "_failures", judged)
    delta = validation_delta(ctx, result, BOTH_STRUCTURE_FIXES.encode())
    assert [i["caused_by"] for i in delta["revealed"]] == [["second_h1", "unclosed_details"]]


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


def padded(readme: str, visible: int) -> str:
    """``readme`` with maintainer lines added to a Notes section until it is ``visible`` lines."""
    lines = line_counts(readme)[0]
    filler = NL.join(f"Maintainer line {n}." for n in range(visible - lines - 3))
    return readme.replace(
        "## Installation", "## Notes" + NL + NL + filler + NL + NL + "## Installation", 1
    )


def test_a_diagram_redraw_the_governed_bc07_accepts_brings_no_failure_and_needs_no_allowance(
    make_context: Any,
) -> None:
    ctx = make_context(README_WITH_DIAGRAM)
    result = correct(ctx)
    assert [e.kind for e in result.edits if e.detector == "at_a_glance_diagram"] == ["DIAGRAM_FIX"]
    delta = validation_delta(ctx, result, README_WITH_DIAGRAM.encode())
    assert delta["introduced"] == [] and delta["allowed"] == []
    assert delta["corrected_failures"]["BC-07"] <= delta["live_failures"]["BC-07"]


def test_a_redraw_that_tips_the_visible_budget_is_allowed_under_od06_and_r7(
    make_context: Any,
) -> None:
    tight = padded(README_WITH_DIAGRAM, 299)
    assert line_counts(tight)[0] == 299
    ctx = make_context(tight)
    result, delta = correct_settled(ctx, tight.encode())
    assert [e.kind for e in result.edits if e.detector == "at_a_glance_diagram"] == ["DIAGRAM_FIX"]
    assert line_counts(result.corrected)[0] > 300
    assert delta["introduced"] == []
    (allowed,) = delta["allowed"]
    assert allowed["check"] == "BC-07/visible" and allowed["ruling"] == "OD-06, R7"
    assert "visible lines" in allowed["details"][0] and allowed["extra"] == 1


def test_an_edit_that_lengthens_the_readme_beyond_the_redraw_does_not_ride_the_allowance(
    make_context: Any, make_fact: Any
) -> None:
    tight = padded(README_WITH_DIAGRAM, 299)
    facts = [
        make_fact("build_test_asset:build-command", "mvn -B verify", evidence=(("pom.xml", "x"),)),
        make_fact("build_test_asset:test-command", "mvn test", evidence=(("pom.xml", "x"),)),
    ]
    ctx = make_context(tight, facts)
    result, delta = correct_settled(ctx, tight.encode())
    assert any(e.kind == "DIAGRAM_FIX" for e in result.edits)
    assert delta["introduced"] == []
    redraw_only = line_counts(
        apply_edits(tight, [e for e in result.edits if e.kind == "DIAGRAM_FIX"])[0]
    )[0]
    assert line_counts(result.corrected)[0] <= max(300, redraw_only)  # nothing else grew it


def test_without_the_allowance_a_budget_tipping_redraw_is_dropped_and_reported(
    make_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check, "ALLOWANCES", ())
    tight = padded(README_WITH_DIAGRAM, 299)
    result, delta = correct_settled(make_context(tight), tight.encode())
    assert not any(e.kind == "DIAGRAM_FIX" for e in result.edits)
    assert delta["introduced"] == [] and delta["allowed"] == []
    assert any(
        f.detector == "at_a_glance_diagram" and "visible" in f.reason for f in result.findings
    )


def test_the_allowance_covers_only_its_kind_its_check_and_its_wording() -> None:
    before: dict[str, list[str]] = {}
    visible = {"BC-07/visible": ["303 visible lines of 479 exceed the visible budget 300"]}
    introduced, allowed = check._split_allowed(before, visible, {"DIAGRAM_FIX"})
    assert introduced == [] and allowed[0]["ruling"] == "OD-06, R7"
    introduced, allowed = check._split_allowed(before, visible, {"MISSING_INFO"})
    assert allowed == [] and introduced[0]["check"] == "BC-07/visible"  # another kind
    other_wording = {"BC-07/visible": ["At a Glance is a flowchart TD"]}
    introduced, allowed = check._split_allowed(before, other_wording, {"DIAGRAM_FIX"})
    assert allowed == [] and introduced[0]["details"] == other_wording["BC-07/visible"]
    other_check = {"BC-03": ["303 visible lines of 479 exceed the visible budget 300"]}
    introduced, allowed = check._split_allowed(before, other_check, {"DIAGRAM_FIX"})
    assert allowed == [] and introduced[0]["check"] == "BC-03"


def test_the_bound_flags_a_count_past_what_the_allowed_edit_brought() -> None:
    allowed = [
        {
            "check": "BC-07/visible",
            "extra": 1,
            "details": ["303 visible lines of 479 exceed the visible budget 300"],
        }
    ]
    same = {"BC-07/visible": ["303 visible lines of 480 exceed the visible budget 300"]}
    assert check._grown(allowed, same) == []
    more = {"BC-07/visible": ["305 visible lines of 481 exceed the visible budget 300"]}
    (grown,) = check._grown(allowed, more)
    assert grown["check"] == "BC-07/visible" and "305 visible lines" in grown["details"][0]
    assert check._grown(allowed, {}) == []


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
