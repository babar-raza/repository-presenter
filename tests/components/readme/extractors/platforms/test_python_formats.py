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
