# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/) ![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

Aspose.3D FOSS for Python is a pure-Python, MIT-licensed library for loading, constructing, and exporting 3D scenes. It reads and writes OBJ, STL, glTF/GLB, COLLADA, and 3MF files, plus imports FBX, through a `Scene`, `Node`, and `Mesh` object graph, with no native runtime or external SDK to install. Developers use it to build 3D content programmatically, for example by creating primitives like `Box` or `Sphere`, assigning materials, and saving to formats such as `.gltf` or `.stl`. The library supports Python versions 3.7 through 3.12 and requires Python >=3.7.

## Navigation

- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## Key Capabilities

- **Load multiple 3D formats.** Create and edit mesh geometry by adding control points and polygons with `Mesh.control_points` and `Mesh.create_polygon`, or convert primitives like `Box` and `Sphere` to editable `Mesh` objects with `to_mesh`.
- **Export to common 3D formats.** Build a scene graph by attaching entities to nodes with `Node.create_child_node`, and inspect or modify each node's position and orientation through its `Transform` property.
- **Construct and manipulate meshes.** Assign materials such as `LambertMaterial` or `PbrMaterial` to nodes, setting diffuse color, metallic factor, and roughness factor to control how light interacts with the geometry.
- **Assign materials to geometry.** Import and export scenes to formats including OBJ, STL, glTF/GLB, and 3MF using `FileFormat.get_format_by_extension` and format-specific save options like `GltfSaveOptions` and `ThreeMfSaveOptions`.
- **Build and traverse scene graphs.** Construct parameterized primitives such as `Box` and `Sphere`, then call their `to_mesh` method to produce editable `Mesh` geometry with control points and polygons.
- **Triangulate arbitrary polygons.** Build keyframe animations using `AnimationClip`, `AnimationNode`, and `KeyframeSequence` to define time-based transformations, and store skeletal bind-pose data with `Pose`.
- **Create keyframe animations.** Inspect mesh properties such as control points, polygon count, and bounding box with `Mesh.control_points`, `Mesh.polygon_count`, and `Mesh.get_bounding_box` to analyze geometry structure.
- **Convert primitives to editable meshes.** Traverse the scene graph by accessing `Node.child_nodes` and `Node.parent_node`, and query global transformations with `Node.evaluate_global_transform` to understand spatial relationships.

## Installation

Install the published package from PyPI (`aspose-3d-foss`, version 26.1.0):

```bash
pip install aspose-3d-foss
```

To work from a source checkout instead, install the clone with pip:

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git
cd Aspose.3D-FOSS-for-Python
pip install .
```

Verify the install:

```bash
python -c "import aspose.threed"
```

The package supports Python 3.7, 3.8, 3.9, 3.10, 3.11, and 3.12 and declares `python_requires` as `>=3.7`.

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `setup.py`, the `install_requires` list is empty.

### Native and System Requirements

- Requires Python 3.7 or later (`python_requires=">=3.7"` in `setup.py`).

### Development Dependencies

- `pytest>=7.0.0` (extra `dev`)

## Quick Start

Import an OBJ file and inspect its geometry, or build a scene from scratch and export it to glTF.

```python
from aspose.threed import Scene
from aspose.threed.entities import Box
from aspose.threed.shading import LambertMaterial
from aspose.threed.utilities import Vector3

scene = Scene()
box = Box(length=2.0, width=1.0, height=1.0)
material = LambertMaterial()
material.diffuse_color = Vector3(0.2, 0.6, 0.9)

scene.root_node.create_child_node("Crate", entity=box.to_mesh(), material=material)
scene.save("crate.gltf")
```

## Additional Examples

The following examples demonstrate core workflows in Aspose.3D FOSS for Python, including mesh construction, material assignment, and format conversion.

<details>
<summary>View Additional Examples</summary>

### Create a sphere with a PBR material and save it as STL

```python
from aspose.threed import Scene
from aspose.threed.entities import Sphere
from aspose.threed.shading import PbrMaterial
from aspose.threed.utilities import Vector3

scene = Scene()
sphere = Sphere()
material = PbrMaterial(albedo=Vector3(0.8, 0.1, 0.1))
material.metallic_factor = 0.9
material.roughness_factor = 0.2

scene.root_node.create_child_node("Ball", entity=sphere.to_mesh(), material=material)
scene.save("ball.stl")
```

### Build a mesh, assign a PBR material, and export to glTF JSON

```python
import io
import json
from aspose.threed import Scene, FileFormat
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector3, Vector4
from aspose.threed.formats.gltf import GltfSaveOptions
from aspose.threed.shading import PbrMaterial

scene = Scene()
mesh = Mesh("TestMesh")
mesh.control_points.add(Vector4(0.0, 0.0, 0.0, 1.0))
mesh.control_points.add(Vector4(1.0, 0.0, 0.0, 1.0))
mesh.control_points.add(Vector4(0.0, 1.0, 0.0, 1.0))
mesh.create_polygon(0, 1, 2)

albedo = Vector3(0.8, 0.2, 0.3)
material = PbrMaterial("RedMaterial", albedo)
material.metallic_factor = 0.5
material.roughness_factor = 0.7

node = scene.root_node.create_child_node("TestNode")
node.entity = mesh
node.material = material

stream = io.BytesIO()
# Pass the detected FileFormat into the constructor explicitly: unlike
# StlFormat, GltfFormat.create_save_options() does not set file_format on the
# options it returns, and a bare stream (no filename) gives scene.save()
# nothing else to detect the format from.
options = GltfSaveOptions(FileFormat.get_format_by_extension(".gltf"))
options.binary_mode = False
scene.save(stream, options)

stream.seek(0)
gltf_data = json.loads(stream.read().decode("utf-8"))
print(gltf_data["materials"][0]["pbrMetallicRoughness"])
```

### Construct a triangle mesh and export it to ASCII STL

```python
import io
from aspose.threed import Scene, FileFormat
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4

scene = Scene()
mesh = Mesh("triangle")
mesh.control_points.add(Vector4(0.0, 0.0, 0.0, 1.0))
mesh.control_points.add(Vector4(1.0, 0.0, 0.0, 1.0))
mesh.control_points.add(Vector4(1.0, 1.0, 0.0, 1.0))
mesh.create_polygon(0, 1, 2)

node = scene.root_node.create_child_node("triangle_node")
node.entity = mesh

stream = io.StringIO()
# Use FileFormat.get_format_by_extension(...).create_save_options() rather than
# StlSaveOptions() directly: a default-constructed options object has no
# file_format set, and scene.save() cannot infer the format from a bare stream
# (only filename-based saves fall back to extension detection).
options = FileFormat.get_format_by_extension(".stl").create_save_options()
options.binary_mode = False
scene.save(stream, options)
print(stream.getvalue())
```

### Convert a `Box` primitive to a mesh and count control points

```python
from aspose.threed.entities import Box

box = Box(10, 20, 30)
mesh = box.to_mesh()
print(f"Control points: {len(mesh.control_points)}")
```

### Build a cube mesh and export it to uncompressed 3MF

```python
import io
from aspose.threed import Scene
from aspose.threed.entities import Mesh
from aspose.threed.utilities import Vector4
from aspose.threed.formats import ThreeMfSaveOptions

scene = Scene()
mesh = Mesh("cube")
for point in [
    Vector4(0, 0, 0, 1), Vector4(1, 0, 0, 1), Vector4(1, 1, 0, 1), Vector4(0, 1, 0, 1),
    Vector4(0, 0, 1, 1), Vector4(1, 0, 1, 1), Vector4(1, 1, 1, 1), Vector4(0, 1, 1, 1),
]:
    mesh.control_points.add(point)

mesh.create_polygon(0, 1, 2)
mesh.create_polygon(0, 2, 3)
mesh.create_polygon(4, 7, 6)
mesh.create_polygon(4, 6, 5)
mesh.create_polygon(0, 4, 5)
mesh.create_polygon(0, 5, 1)
mesh.create_polygon(2, 6, 7)
mesh.create_polygon(2, 7, 3)
mesh.create_polygon(0, 3, 7)
mesh.create_polygon(0, 7, 4)
mesh.create_polygon(1, 5, 6)
mesh.create_polygon(1, 6, 2)

node = scene.root_node.create_child_node("cube")
node.entity = mesh

stream = io.BytesIO()
options = ThreeMfSaveOptions()
options.enable_compression = False
scene.save(stream, options)
```

</details>

## API Reference

<details>
<summary>Hub APIs</summary>

- `aspose.threed.Scene`: Create, open, and save 3D scenes with `aspose.threed.Scene`, which provides `Scene.open`, `Scene.save`, `Scene.from_file`, `Scene.root_node`, `Scene.animation_clips`, `Scene.sub_scenes`, `Scene.library`, `Scene.clear`, `Scene.get_animation_clip`, `Scene.create_animation_clip`, `Scene.current_animation_clip`, `Scene.poses`, `Scene.asset_info`, and `Scene.render`.
- `aspose.threed.Node`: Manage scene hierarchy and transform with `aspose.threed.Node`, which supports `Node.create_child_node`, `Node.child_nodes`, `Node.parent_node`, `Node.entities`, `Node.entity`, `Node.add_entity`, `Node.transform`, `Node.global_transform`, `Node.evaluate_global_transform`, `Node.material`, `Node.materials`, `Node.visible`, `Node.excluded`, `Node.get_bounding_box`, `Node.get_child`, `Node.select_objects`, `Node.select_single_object`, `Node.meta_datas`, `Node.asset_info`, and `Node.merge`.
- `aspose.threed.Mesh`: Construct and inspect polygonal geometry with `aspose.threed.Mesh`, which exposes `Mesh.control_points`, `Mesh.to_mesh`, and `Mesh.polygon_count`.
- `aspose.threed.shading`: Define surface appearance with `aspose.threed.shading.Material`, which supports `Material.diffuse_color`, `Material.metallic_factor`, and `Material.roughness_factor`.
- `aspose.threed.entities`: Create and modify geometric primitives and polygonal data using `aspose.threed.entities`, which includes `aspose.threed.Primitive` and `PolygonBuilder` with member `create_polygon` and member add.
- `aspose.threed.animation`: Handle time-based motion with `aspose.threed.animation`, which provides `aspose.threed.AnimationClip` and `Scene.animation_clips` for managing clip-based animations.
- `aspose.threed.formats`: Discover, detect, and convert between file formats with `FileFormat`, which supports `FileFormat.FBX7400ASCII`, `FileFormat.GLTF2`, `FileFormat.MICROSOFT_3MF_FORMAT`, `FileFormat.WAVEFRONT_OBJ`, `FileFormat.detect`, `FileFormat.get_format_by_extension`, `FileFormat.formats`, `FileFormat.can_import`, `FileFormat.can_export`, `FileFormat.extension`, `FileFormat.extensions`, `FileFormat.file_format_type`, `FileFormat.version`, `FileFormat.content_type`, `FileFormat.create_load_options`, and `FileFormat.create_save_options`.
- `aspose.threed.utilities`: Perform common mathematical and utility operations with `aspose.threed.utilities`, which includes `aspose.threed.MathUtils` and helper members such as member decode, member getvalue, member seek, member read, member `binary_mode`, member `BytesIO`, and member `StringIO`.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/3d/python/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/3d/python/)** — The how-to guides and FAQ provide task-focused answers for common 3D-processing questions.
- **[Full API reference](https://reference.aspose.org/3d/python/)** — The full API reference offers the complete, browsable reference for all 305 public types. It covers all 343 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- **[Implementation progress notes](docs/foss-python-progress.md)** — The implementation progress notes describe the current FOSS-edition porting status.
- **[Release process](docs/releasing.md)** — The release process document explains how a version of aspose-3d-foss is tagged and published to PyPI.
- **[Scene/Node/Entity/Transform](docs/IMPLEMENTATION_SUMMARY.md)** — The implementation summary covers `Scene`, `Node`, `Entity`, and `Transform` internals.
- **[OBJ importer](docs/OBJ_IMPORTER_IMPLEMENTATION.md)** — The OBJ importer implementation notes describe the historical development of OBJ support.
- **[STL import/export](docs/STL_IMPORT_IMPLEMENTATION.md)** — The STL import implementation notes describe the historical development of STL import and export.
- **[FBX parser](docs/FBX_IMPLEMENTATION_SUMMARY.md)** — The FBX implementation summary describes the historical development of the FBX parser.
- **[PyPI packaging readiness](docs/PYPI_READINESS.md)** — The PyPI readiness notes describe packaging requirements and status for distribution.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues).

## Scope and Limitations

Aspose.3D FOSS for Python version 26.1.0 supports reading and writing OBJ, STL, glTF, and COLLADA files, and provides basic scene graph inspection and node manipulation through the `Scene`, `Node`, and `Entity` APIs.

- No file format registers an importer or exporter for PDF, PLY, RVM, U3D, JT, AMF, HTML5, A3DW, USD, or Draco in this build — `PdfSaveOptions`, `PlyLoadOptions`, `DracoSaveOptions`, and similar option classes exist as public types, but `Scene.open`()/`Scene.save`() cannot detect or dispatch any of these extensions, and raise a RuntimeError if you try.
- FBX support is experimental: `FbxImporter` has a real, working ASCII/binary tokenizer and parser, but no bundled test opens a real .fbx fixture through it, and `FbxExporter.save`()/`save_to_stream()` both raise NotImplementedError outright, so FBX is import-only at best.
- COLLADA import works, but COLLADA export is not reachable through `Scene.save`() because `IOService`'s exporter lookup walks its registered exporters in order and reaches `FbxExporter` (whose `supports_format()` is unimplemented and raises unconditionally) before it ever reaches `ColladaExporter`, so the lookup itself fails before a real, working `ColladaExporter` is ever consulted.
- The entire `aspose.threed.render` module (`Renderer`, `RenderFactory`, `Viewport`, and related classes) raises NotImplementedError, so this library does not render scenes to images.
- Boolean/CSG mesh operations are not implemented: `Mesh.do_boolean`(), `union()`, `difference()`, and `intersect()` raise NotImplementedError, even though `BooleanOperator` and `BooleanOperand` exist as configuration holders.
- NURBS curves and surfaces can be configured but not sampled or converted to a `Mesh` because `NurbsCurve.evaluate`()/`evaluate_at()` and `NurbsSurface.to_mesh`() raise NotImplementedError.

## Development and Testing

Install the package in editable mode and run the test suite using the discover command against the tests directory.

The suite covers 34 test files under `tests/`. Releases run through the [publish workflow](.github/workflows/publish.yml).

```bash
python3 -m pip install -e .
python3 -m unittest discover tests/
```

```bash
python -m unittest tests.test_obj_importer
```

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
