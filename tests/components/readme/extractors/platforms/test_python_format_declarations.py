"""Static format declarations: FileFormat's format classes and the plugin registrations, from
syntax trees; a stub importer or exporter registers nothing for its direction."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.extractors.platforms.python_format_declarations import (
    format_declarations,
)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _product(tmp_path: Path) -> list[str]:
    files = {
        "pkg/__init__.py": "from .FileFormat import FileFormat\n",
        "pkg/FileFormat.py": (
            "class FileFormat:\n"
            "    @staticmethod\n"
            "    def get_format_by_extension(ext):\n"
            "        if ext == 'obj':\n"
            "            from .formats.obj.ObjFormat import ObjFormat\n"
            "            return ObjFormat()\n"
            "        if ext == 'fbx':\n"
            "            from .formats.fbx.FbxFormat import FbxFormat\n"
            "            return FbxFormat()\n"
            "        return None\n"
        ),
        "pkg/formats/__init__.py": (
            "from .IOService import IOService\n"
            "from .obj.ObjPlugin import ObjPlugin\n"
            "from .fbx.FbxPlugin import FbxPlugin\n"
            "\n\ndef _register_plugins():\n"
            "    io_service = IOService()\n"
            "    io_service.register_plugin(ObjPlugin())\n"
            "    io_service.register_plugin(FbxPlugin())\n"
            "\n\n_register_plugins()\n"
        ),
        "pkg/formats/IOService.py": (
            "class IOService:\n    def register_plugin(self, plugin):\n        pass\n"
        ),
        "pkg/formats/obj/__init__.py": "",
        "pkg/formats/obj/ObjFormat.py": (
            "class ObjFormat:\n    @property\n    def extension(self):\n        return 'obj'\n\n"
            "    @property\n    def extensions(self):\n        return ['obj']\n"
        ),
        "pkg/formats/obj/ObjImporter.py": (
            "class ObjImporter:\n    def import_scene(self, scene, stream, options):\n"
            "        scene.nodes.append(stream.read())\n"
        ),
        "pkg/formats/obj/ObjExporter.py": (
            "class ObjExporter:\n    def export(self, scene, stream, options):\n"
            "        stream.write(b'o')\n"
        ),
        "pkg/formats/obj/ObjPlugin.py": (
            "class ObjPlugin:\n    def __init__(self):\n"
            "        from .ObjImporter import ObjImporter\n"
            "        from .ObjExporter import ObjExporter\n"
            "        self._importer = ObjImporter()\n"
            "        self._exporter = ObjExporter()\n\n"
            "    def get_file_format(self):\n        from .ObjFormat import ObjFormat\n"
            "        return ObjFormat()\n"
        ),
        "pkg/formats/fbx/__init__.py": "",
        "pkg/formats/fbx/FbxFormat.py": (
            "class FbxFormat:\n    @property\n    def extensions(self):\n        return ['fbx']\n"
        ),
        "pkg/formats/fbx/FbxImporter.py": (
            "class FbxImporter:\n    def import_scene(self, scene, stream, options):\n"
            "        scene.nodes.append(1)\n"
        ),
        "pkg/formats/fbx/FbxExporter.py": (
            "class FbxExporter:\n    def save(self, filename, scene, options=None):\n"
            "        raise NotImplementedError('FBX export is not implemented')\n\n"
            "    def save_to_stream(self, stream, scene, options=None):\n"
            "        raise NotImplementedError('FBX export is not implemented')\n"
        ),
        "pkg/formats/fbx/FbxPlugin.py": (
            "class FbxPlugin:\n    def __init__(self):\n"
            "        from .FbxImporter import FbxImporter\n"
            "        from .FbxExporter import FbxExporter\n"
            "        self._importer = FbxImporter()\n"
            "        self._exporter = FbxExporter()\n\n"
            "    def get_file_format(self):\n        from .FbxFormat import FbxFormat\n"
            "        return FbxFormat()\n"
        ),
    }
    for relative, text in files.items():
        _write(tmp_path, relative, text)
    return sorted(files)


def test_declarations_and_registrations_come_from_the_trees_with_stubs_registering_nothing(
    tmp_path: Path,
) -> None:
    declarations = format_declarations(tmp_path, _product(tmp_path))
    assert [(d.kind, d.direction, d.extension) for d in declarations] == [
        ("declaration", None, ".fbx"),
        ("declaration", None, ".obj"),
        ("registration", "input", ".fbx"),
        ("registration", "input", ".obj"),
        ("registration", "output", ".obj"),
    ]
    obj_declaration = declarations[1]
    assert (obj_declaration.source_path, obj_declaration.line) == ("pkg/FileFormat.py", 5)
    assert obj_declaration.detail == "FileFormat imports ObjFormat, which states .obj"
    obj_output = declarations[4]
    assert (obj_output.source_path, obj_output.line) == ("pkg/formats/__init__.py", 8)
    assert obj_output.detail == (
        "ObjPlugin (pkg/formats/obj/ObjPlugin.py) registered with ObjExporter for ObjFormat, "
        "which states .obj"
    )
    # The FBX exporter only raises NotImplementedError: no output registration for .fbx.
    assert not any(d.direction == "output" and d.extension == ".fbx" for d in declarations)


def test_a_tree_without_declarations_yields_nothing(tmp_path: Path) -> None:
    _write(tmp_path, "pkg/__init__.py", "class Scene:\n    pass\n")
    assert format_declarations(tmp_path, ["pkg/__init__.py", "README.md"]) == []
