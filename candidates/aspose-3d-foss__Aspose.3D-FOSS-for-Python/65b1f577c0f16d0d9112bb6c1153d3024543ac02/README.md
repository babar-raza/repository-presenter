# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/) ![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

Aspose.3D FOSS for Python is a pure-Python, MIT-licensed library for loading, constructing, and exporting 3D scenes. It reads and writes OBJ, STL, glTF/GLB, COLLADA, and 3MF files, plus imports FBX, through a `Scene`/`Node`/`Mesh` object graph, with no native runtime or external SDK to install. Developers use it to build 3D content programmatically, for example by creating primitives like `Box` or `Sphere`, assigning materials from `aspose.threed.shading`, and saving the result to formats such as `.gltf` or `.stl`. The library supports Python versions 3.7 through 3.12 and requires Python >=3.7.

- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation and Resources](#documentation-and-resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## Key Capabilities

- **Import multiple 3D formats.** Create and edit mesh geometry by adding control points with `Mesh.control_points` and forming polygons with `Mesh.create_polygon`, or convert primitives like `Box` and `Sphere` to editable `Mesh` objects via their `to_mesh` method.
- **Export to interchange formats.** Build a scene graph by attaching `Mesh` entities to `Node` objects using `Node.add_entity` and organizing nodes with `Node.create_child_node` and `Node.child_nodes`, where each node maintains an independent `Transform` for translation, rotation, and scaling.
- **Construct and edit meshes.** Assign materials such as `LambertMaterial`, `PhongMaterial`, or `PbrMaterial` to nodes, configuring diffuse, specular, emissive, and PBR albedo metallic and roughness properties directly on the material object.
- **Assign materials.** Read and write scenes to formats including `.gltf` and `.stl` using `Scene.open` and `Scene.save`, where `Scene.open` auto-detects the format from the file extension or an explicit `FileFormat` argument.
- **Build and traverse scene graphs.** Construct keyframe animations using `AnimationClip`, `AnimationNode`, and `KeyframeSequence`, and store skeletal bind-pose data with `Pose` objects, enabling animation authoring and playback within the scene graph.
- **Triangulate polygonal geometry.** Triangulate arbitrary polygon meshes into triangle fans using `PolygonBuilder`, a real ear-clipping triangulation implementation rather than a naive fan split, ensuring valid geometry for downstream workflows.
- **Create keyframe animations.** Inspect and modify mesh properties such as control points, polygon count, bounding box, and manifold status through `Mesh` members like `Mesh.control_points`, `Mesh.polygon_count`, `Mesh.get_bounding_box`, and `Mesh.is_manifold`.

## Installation

```bash
pip install aspose-3d-foss
```

## Quick Start

Create a simple 3D scene with a box and save it as a GLTF file using Aspose.3D FOSS for Python 26.1.0 on Python 3.7 or later.

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

The following examples demonstrate core workflows: creating primitives, building meshes from control points, assigning materials, and exporting to common 3D formats.

<details>
<summary>Create a sphere with a PBR material and save it as STL.</summary>

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

</details>

<details>
<summary>Build a mesh, assign a PBR material, and export to glTF.</summary>

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

</details>

<details>
<summary>Build a triangle mesh and export it to ASCII STL.</summary>

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

</details>

<details>
<summary>Build a cube mesh and export it to 3MF without compression.</summary>

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

<details>
<summary>Convert a `Box` primitive to a mesh and count control points.</summary>

```python
from aspose.threed.entities import Box

box = Box(10, 20, 30)
mesh = box.to_mesh()
print(f"Control points: {len(mesh.control_points)}")
```

</details>

## API Reference

<details>
<summary>Hub APIs</summary>

- `aspose.threed.Scene`: Create, load, and save 3D scenes with `aspose.threed.Scene`, which provides `Scene.open`() and `Scene.save`() to read and write scene graphs built from `Node` objects, each holding a `Transform`, an optional `Mesh`-derived `Entity`, and zero or more `Material` instances.
- `aspose.threed.Node`: Manage scene hierarchy and transform state with `aspose.threed.Node`, which supports `Node.add_child_node`(), `Node.create_child_node`(), `Node.global_transform`, `Node.material`, and `Node.select_objects`() to build and traverse the scene graph.
- `aspose.threed.Mesh`: Construct and manipulate polygonal geometry with `aspose.threed.Mesh`, which exposes `Mesh.control_points`, `Mesh.polygon_count`, `Mesh.polygons`, and `Mesh.to_mesh`() to define vertex positions and polygon connectivity.
- `aspose.threed.shading`: Define material appearance with `aspose.threed.shading`, which provides material properties such as `diffuse_color`, `metallic_factor`, and `roughness_factor` for rendering.
- `aspose.threed.animation`: Create and manage time-based motion with `aspose.threed.animation`, which supports `AnimationClip` and `AnimationNode` to define keyframe-driven transformations over time.
- `aspose.threed.PolygonBuilder`: Programmatically build polygonal meshes with `aspose.threed.PolygonBuilder`, which offers `PolygonBuilder.begin`(), `PolygonBuilder.add_vertex`(), `PolygonBuilder.create_polygon`(), and `PolygonBuilder.end`() to construct geometry step by step.
- `aspose.threed.entities`: Access and modify geometric primitives and modifiers with `aspose.threed.entities`, which includes utilities like `PolygonModifier` for operations such as triangulation.
- `aspose.threed.formats`: Load and save 3D files in various formats with `aspose.threed.formats`, which provides format-specific load and save options and supports formats such as .obj, `.gltf`, and .dae.
- `aspose.threed.utilities`: Perform common utility operations with `aspose.threed.utilities`, which includes helper classes and functions for vector math and data handling.
- `aspose.threed.AnimationClip`: Define animation sequences with `aspose.threed.AnimationClip`, which holds `AnimationNode` instances and exposes `AnimationClip.name`, `AnimationClip.description`, and `AnimationClip.animations` to manage time-based motion.
- `aspose.threed.AnimationNode`: Represent animated transforms in a scene with `aspose.threed.AnimationNode`, which supports `AnimationClip.create_animation_node`() and stores keyframe-driven transformation data.
- `aspose.threed.KeyframeSequence`: Store and interpolate keyframe data with `aspose.threed.KeyframeSequence`, which defines time-value pairs used by animation nodes to drive smooth transitions.

</details>

## Documentation and Resources

The verified documentation targets explain installation, feature walkthroughs, and task-focused answers for common 3D-processing questions, alongside a full API reference for all 305 public types, current FOSS-edition porting status, release process details, and internal implementation records for supported formats.

- [Getting started guide](https://docs.aspose.org/3d/python/)
- [How-to guides & FAQ](https://kb.aspose.org/3d/python/)
- [Full API reference](https://reference.aspose.org/3d/python/)
- [Implementation progress notes](docs/foss-python-progress.md)
- [Release process](docs/releasing.md)
- [Scene/Node/Entity/Transform](docs/IMPLEMENTATION_SUMMARY.md)
- [OBJ importer](docs/OBJ_IMPORTER_IMPLEMENTATION.md)
- [STL import/export](docs/STL_IMPORT_IMPLEMENTATION.md)
- [FBX parser](docs/FBX_IMPLEMENTATION_SUMMARY.md)
- [PyPI packaging readiness](docs/PYPI_READINESS.md)
- [Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues)

## Scope and Limitations

Aspose.3D FOSS for Python version 26.1.0 supports reading and writing OBJ, STL, glTF, and COLLADA files on Python versions 3.7 through 3.12, and provides utilities to inspect scene graphs, access mesh geometry, and modify polygon topology.

- No file format registers an importer or exporter for PDF, PLY, RVM, U3D, JT, AMF, HTML5, A3DW, USD, or Draco in this build — `PdfSaveOptions`, `PlyLoadOptions`, `DracoSaveOptions`, and similar option classes exist as public types, but `Scene.open`() and `Scene.save`() cannot detect or dispatch any of these extensions and raise an error if you try. FBX support is experimental — `FbxImporter` has a working tokenizer and parser but no bundled test opens a real .fbx file through it, and `FbxExporter.save`() and `save_to_stream()` both raise an error outright, so FBX is import-only at best. COLLADA import works, but COLLADA export is not reachable through `Scene.save`() because `IOService`'s exporter lookup fails before `ColladaExporter` is ever consulted. Always import a format's load/save options class from its own format submodule — for OBJ, STL, glTF, and COLLADA specifically, the top-level package name resolves to a broken duplicate with no working base class, which format detection silently rejects. `Scene.render`() and the entire `aspose.threed.render` module (`Renderer`, `RenderFactory`, `Viewport`, and related classes) raise an error — this library does not render scenes to images. `Texture` and `TextureBase` raise an error on construction, so an image-backed texture cannot be created, but material color and factor properties such as `diffuse_color` and `metallic_factor` work independently of texture assignment. `Watermark.encode_watermark`() and `decode_watermark()` and every `TransformBuilder` method raise an error — build node transforms through `Transform`'s own translation, rotation, and scaling properties instead of the fluent `TransformBuilder` chain. `Mesh.do_boolean`(), `union()`, `difference()`, and `intersect()` raise an error — Boolean or CSG mesh operations are not implemented, even though `BooleanOperator` and `BooleanOperand` exist as configuration holders. `NurbsCurve.evaluate`() and `evaluate_at()` and `NurbsSurface.to_mesh`() raise an error — NURBS curves and surfaces can be configured but not sampled or converted to a `Mesh`. `PointCloud.from_geometry`() and `from_geometry_with_density()` raise an error, and `AxisSystem` raises an error on every method, including construction.

## Development and Testing

Install the package in editable mode and run the test suite using the built-in unittest module with the tests directory.

- `tests/`
- `.github/workflows/`
- `docs/`

Install the repository and run the test suite:

```bash
python3 -m pip install -e .
python3 -m unittest discover tests/
```

## License

Aspose.3D FOSS for Python is released under the MIT License. You may use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software, provided the copyright notice and the permission notice accompany every copy. See [LICENSE](LICENSE).
