"""Format claims come from statement syntax: a verb-bearing statement and its extension literal."""

from __future__ import annotations

from repository_presenter.components.readme.extractors.platforms.python_formats import (
    format_claims,
)
from repository_presenter.core.examples import FormatClaim

CANARY_STYLE = """from aspose.threed import Scene, FileFormat
from aspose.threed.formats.gltf import GltfSaveOptions

scene = Scene()
scene.open("model.obj", options)
options = FileFormat.get_format_by_extension(".stl").create_save_options()
options = GltfSaveOptions(FileFormat.get_format_by_extension(".gltf"))
scene.save("mesh.glb", options)
scene.save("again.glb")
"""


def test_claims_pair_each_extension_literal_with_its_statement_verb() -> None:
    assert format_claims(CANARY_STYLE) == [
        FormatClaim(".obj", "input", 5),
        FormatClaim(".stl", "output", 6),
        FormatClaim(".gltf", "output", 7),
        FormatClaim(".glb", "output", 8),
    ]


def test_statements_without_one_direction_claim_nothing() -> None:
    assert format_claims('name = "model.obj"\n') == []
    assert format_claims('converted = save(load("a.obj"), "b.stl")\n') == []
    assert format_claims('print("x.stl")\n') == []
    assert format_claims('exec(open("script.py").read())\n') == []
    assert format_claims("def broken(:\n") == []


def test_nested_statements_are_read_on_their_own() -> None:
    code = (
        "for path in paths:\n"
        '    with open("scene.dae") as handle:\n'
        "        scene.save(handle)\n"
        "    if ok:\n"
        '        exporter.write("out.3mf")\n'
    )
    assert format_claims(code) == [
        FormatClaim(".dae", "input", 2),
        FormatClaim(".3mf", "output", 5),
    ]


def test_a_statically_dead_branch_claims_nothing() -> None:
    """TB-02, external review D2, 2026-09-08: `ast.walk` visits every node regardless of
    reachability, so a branch that can never run - `if False:`/`if 0:`, the exact shape used to
    reproduce and confirm this gap - claimed a format the example could never actually produce.
    A narrow, named exclusion, not a full reachability analysis: an `if` gated on a runtime
    condition still claims normally, in both its body and its else."""
    dead = 'if False:\n    scene.save("never-produced.pdf")\nscene.save("real.glb")\n'
    assert format_claims(dead) == [FormatClaim(".glb", "output", 3)]
    assert format_claims('if 0:\n    scene.save("never.pdf")\n') == []
    live = 'if condition:\n    scene.save("a.glb")\nelse:\n    scene.save("b.glb")\n'
    assert format_claims(live) == [
        FormatClaim(".glb", "output", 2),
    ]


def test_a_function_defined_but_never_called_claims_nothing() -> None:
    """The same reachability gap TB-02 fixes for `if False:`, for a helper nothing in the
    example ever calls - a narrow, name-reference check, not a call-graph analysis: a function
    called anywhere, including conditionally, still claims normally."""
    code = (
        'def unused():\n    scene.save("never-produced.pdf")\n\n'
        'def used():\n    scene.save("real.glb")\n\n'
        "used()\n"
    )
    assert format_claims(code) == [FormatClaim(".glb", "output", 5)]
    assert format_claims('def helper():\n    scene.save("dead.pdf")\n') == []
    called = 'def helper():\n    scene.save("live.glb")\n\nif condition:\n    helper()\n'
    assert format_claims(called) == [FormatClaim(".glb", "output", 2)]
