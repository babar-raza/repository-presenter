"""The sending order, the recorded holds, the typed reason an entry has nothing to send, and the
real-render record kept in the bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme_correction import render as render_module
from repository_presenter.components.readme_correction.model import (
    DIAGRAM_FIX,
    FALSE_CLAIM_FIX,
    CorrectionResult,
    Edit,
    Finding,
)
from repository_presenter.components.readme_correction.render import measure_diagrams
from repository_presenter.components.readme_correction.send import (
    NO_PUSH_REASONS,
    load_holds,
    send_plan,
)
from repository_presenter.components.readme_diagram import render_check as check

TEX = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
THREE_D_NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
PLAIN = "aspose-words-foss/Aspose.Words-FOSS-for-Python"


def test_content_corrections_go_first_and_diagram_only_ones_second() -> None:
    assert send_plan(PLAIN, {FALSE_CLAIM_FIX, DIAGRAM_FIX}, [])["pr_order"] == 1
    assert send_plan(PLAIN, {FALSE_CLAIM_FIX}, [])["pr_order"] == 1
    assert send_plan(PLAIN, {DIAGRAM_FIX}, [])["pr_order"] == 2
    nothing = send_plan(PLAIN, set(), [])
    assert nothing["pr_order"] is None and nothing["no_push_reason"] == "NO_DETECTOR_FIRED"


def test_the_only_change_being_an_unportable_diagram_is_its_own_typed_reason() -> None:
    held = Finding(
        "at_a_glance_diagram", 9, "", "x", report_only_reason="DIAGRAM_LABEL_NOT_PORTABLE"
    )
    plan = send_plan(PLAIN, set(), [held])
    assert plan["no_push_reason"] == "ONLY_CHANGE_UNPORTABLE_DIAGRAM"
    assert plan["no_push_reason"] in NO_PUSH_REASONS


def test_the_recorded_holds_are_typed_and_paired_with_an_issue() -> None:
    holds = load_holds()
    assert {TEX, THREE_D_NET} <= set(holds)
    for repository in (TEX, THREE_D_NET):
        plan = send_plan(repository, {DIAGRAM_FIX}, [])
        hold = plan["hold_reason"]
        assert plan["pr_order"] == 2  # a hold changes whether it is sent now, not the bundle
        assert hold["reason_code"].isupper() and hold["pair_with"] and hold["recorded"]
    assert send_plan(PLAIN, {DIAGRAM_FIX}, [])["hold_reason"] is None


def test_a_hold_without_a_code_a_reason_or_a_pairing_is_a_defect_in_the_data(
    tmp_path: Path,
) -> None:
    path = tmp_path / "holds.json"
    entry = {"repository": "o/r", "reason_code": "X", "reason": "r", "pair_with": "an issue"}
    path.write_text(json.dumps({"holds": [entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match="recorded"):
        load_holds(path)
    entry["recorded"] = "2026-10-11"
    path.write_text(json.dumps({"holds": [entry, entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match="twice"):
        load_holds(path)


def test_a_bundle_records_its_sending_plan(tmp_path: Path, make_context: Any) -> None:
    from repository_presenter.components.readme_correction import bundle as files
    from repository_presenter.components.readme_correction.settle import correct_settled

    readme = "# P" + chr(10) + chr(10) + "## Installation" + chr(10) + chr(10) + "x" + chr(10)
    ctx = make_context(readme)
    result, delta = correct_settled(ctx, readme.encode())
    files.write_bundle(ctx, readme.encode(), result, delta, tmp_path / "b")
    document = json.loads((tmp_path / "b" / files.CORRECTIONS_NAME).read_text(encoding="utf-8"))
    assert set(document["send"]) == {"pr_order", "hold_reason", "no_push_reason"}


def test_a_result_without_a_diagram_has_no_render_record() -> None:
    assert measure_diagrams(CorrectionResult("a", "a")) is None


def _redraw(replacement: str) -> CorrectionResult:
    edit = Edit(
        kind=DIAGRAM_FIX,
        detector="at_a_glance_diagram",
        start=0,
        end=3,
        original="old",
        replacement=replacement,
        fact_ids=(),
        locators=("README.md:2",),
        rationale="r",
    )
    return CorrectionResult("old", replacement, [edit])


def test_without_a_renderer_the_record_says_so_and_claims_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(render_module.check, "find_renderer", lambda: None)
    record = measure_diagrams(_redraw("flowchart LR" + chr(10)))
    assert record is not None and record["status"] == "not_run" and "renderer" in record["reason"]


def test_with_a_renderer_each_redrawn_diagram_is_recorded_on_every_release() -> None:
    renderer = check.find_renderer()
    if renderer is None:
        pytest.skip("no Mermaid renderer installed (RP_MERMAID_TOOLS)")
    from repository_presenter.components.readme_diagram import build_body, parse

    fixture = Path(__file__).parents[1] / "readme_diagram" / "fixtures" / "live"
    body = next(fixture.glob("*Java.mmd")).read_text(encoding="utf-8")
    record = measure_diagrams(_redraw(build_body(parse(body).glance)))
    assert record is not None and record["status"] == "verified"
    assert len(record["releases"]) >= 3  # the older, the latest and 12.x when installed
    (diagram,) = record["diagrams"]
    assert diagram == {"horizontal": True, "clipped_fonts": 0, "word_splits": 0, "problems": 0}
