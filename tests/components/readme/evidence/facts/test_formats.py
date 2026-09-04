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
    FormatDeclaration,
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


def test_two_static_sources_support_a_format_no_example_executed() -> None:
    # RESEARCH_AND_GUIDELINES.md sections 22.1 and 26: a declaration and a registration together
    # support a pair; either alone, like a failed example alone, leaves it UNRESOLVED.
    candidates = [_candidate(1, 'scene.open("model.obj")\nscene.save("out.fbx")\n', 10)]
    receipts = [_receipt(1, "FAILED")]
    declarations = [
        FormatDeclaration(
            ".obj",
            None,
            "declaration",
            "aspose/FileFormat.py",
            3,
            "FileFormat imports ObjFormat, which states .obj",
        ),
        FormatDeclaration(
            ".obj",
            "input",
            "registration",
            "aspose/formats/__init__.py",
            9,
            "ObjPlugin registered with ObjImporter for ObjFormat, which states .obj",
        ),
        FormatDeclaration(
            ".obj",
            "output",
            "registration",
            "aspose/formats/__init__.py",
            9,
            "ObjPlugin registered with ObjExporter for ObjFormat, which states .obj",
        ),
        FormatDeclaration(
            ".fbx",
            None,
            "declaration",
            "aspose/FileFormat.py",
            4,
            "FileFormat imports FbxFormat, which states .fbx",
        ),
        FormatDeclaration(
            ".fbx",
            "input",
            "registration",
            "aspose/formats/__init__.py",
            10,
            "FbxPlugin registered with FbxImporter for FbxFormat, which states .fbx",
        ),
        FormatDeclaration(
            ".3mf",
            "output",
            "registration",
            "aspose/formats/__init__.py",
            11,
            "ThreeMfPlugin registered with ThreeMfExporter for ThreeMfFormat, which states .3mf",
        ),
    ]
    facts = format_facts(candidates, receipts, format_claims, "examples.json", declarations)
    assert [(f.id, f.polarity) for f in facts] == [
        ("format:input.fbx", "SUPPORTED"),
        ("format:input.obj", "SUPPORTED"),
        ("format:output.3mf", "UNRESOLVED"),
        ("format:output.fbx", "UNRESOLVED"),
        ("format:output.obj", "SUPPORTED"),
    ]
    obj_in = next(f for f in facts if f.id == "format:input.obj")
    assert [e.detail for e in obj_in.evidence] == [
        "line 11; example 1: input .obj",
        "example 1: FAILED; exit 0",
        "line 3; FileFormat imports ObjFormat, which states .obj",
        "line 9; ObjPlugin registered with ObjImporter for ObjFormat, which states .obj",
    ]
    fbx_out = next(f for f in facts if f.id == "format:output.fbx")
    assert [e.path for e in fbx_out.evidence] == ["README.md", "examples.json"]
