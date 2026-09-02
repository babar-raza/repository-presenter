"""Format facts: an example's claim, polarised by that example's receipt."""

from __future__ import annotations

from repository_presenter.components.readme.evidence.facts.formats import format_facts
from repository_presenter.components.readme.extractors.platforms.python_formats import (
    format_claims,
)
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FixtureBinding,
)


def _candidate(ordinal: int, code: str, start_line: int) -> ExampleCandidate:
    end = start_line + code.count("\n") + 1
    return ExampleCandidate(
        ordinal, "python", code, "README.md", start_line, end, f"inherited_unit:{ordinal:03d}"
    )


def _receipt(ordinal: int, outcome: str, **kwargs: object) -> ExampleReceipt:
    return ExampleReceipt(ordinal, outcome, 0, "", "", "exit 0", **kwargs)  # type: ignore[arg-type]


def test_executed_examples_support_their_formats_and_unverified_ones_leave_them_open() -> None:
    candidates = [
        _candidate(1, 'scene.open("model.obj")\nscene.save("out.stl")\n', 10),
        _candidate(2, 'scene.open("mesh.stl")\nscene.save("mesh.glb")\n', 20),
        _candidate(3, 'scene.save("cube.stl")\n', 30),
    ]
    receipts = [
        _receipt(1, "EXECUTED", fixtures=(FixtureBinding("model.obj", "tests/data/model.obj"),)),
        _receipt(2, "NEEDS_INPUT"),
        _receipt(3, "FAILED"),
    ]
    facts = format_facts(candidates, receipts, format_claims, "examples.json")
    assert [(f.id, f.value, f.polarity, f.confidence) for f in facts] == [
        ("format:input.obj", ".obj", "SUPPORTED", 1.0),
        ("format:input.stl", ".stl", "UNRESOLVED", 0.5),
        ("format:output.glb", ".glb", "UNRESOLVED", 0.5),
        ("format:output.stl", ".stl", "SUPPORTED", 1.0),
    ]
    obj = facts[0]
    assert [(e.path, e.detail) for e in obj.evidence] == [
        ("README.md", "line 11; example 1: input .obj"),
        ("examples.json", "example 1: EXECUTED; exit 0"),
        ("tests/data/model.obj", "staged as model.obj; example 1 read it: EXECUTED"),
    ]
    stl_out = facts[3]
    assert [e.detail for e in stl_out.evidence] == [
        "line 12; example 1: output .stl",
        "example 1: EXECUTED; exit 0",
        "line 31; example 3: output .stl",
        "example 3: FAILED; exit 0",
    ]
    assert format_facts(candidates, receipts, format_claims, "examples.json") == facts


def test_no_receipt_means_not_verified_and_no_examples_mean_no_facts() -> None:
    candidates = [_candidate(1, 'scene.save("out.stl")\n', 1)]
    facts = format_facts(candidates, [], format_claims, "examples.json")
    assert [(f.id, f.polarity) for f in facts] == [("format:output.stl", "UNRESOLVED")]
    assert facts[0].evidence[1].detail == "example 1: NOT_VERIFIED; no verification receipt"
    assert format_facts([], [], format_claims, "examples.json") == []
