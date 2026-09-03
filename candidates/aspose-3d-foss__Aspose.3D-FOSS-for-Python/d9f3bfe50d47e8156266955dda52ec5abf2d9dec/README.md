# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/) ![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

Aspose.3D FOSS for Python is a free, open-source, pure-Python library for building, reading, and writing 3D scenes through an Aspose.3D-compatible API. It models a scene graph of nodes, meshes, cameras, lights, and materials, and moves that graph in and out of OBJ, STL, glTF, COLLADA, and 3MF files with no native dependencies to compile or install. Developers use it to create procedural geometry like `Box`, `Cylinder`, and `Sphere` primitives, apply materials from `aspose.threed.shading`, and manage animations with `aspose.threed.animation` classes. The package requires Python >=3.7 and supports versions 3.7, 3.8, 3.9, 3.10, 3.11, and 3.12, and its current version is 26.1.0.

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

- **Build 3D scenes programmatically.** Create 3D scenes programmatically using the `Scene` class, add hierarchical nodes with `Node`, and define geometry with `Mesh`, `Camera`, and `Light` entities.
- **Import multiple 3D formats.** Import files in OBJ, STL, glTF 2.0, GLB, COLLADA, and 3MF formats into a unified `Scene` model using `Scene.open` or `Scene.from_file`.
- **Export to common 3D formats.** Export scenes to OBJ, STL, glTF, GLB, or 3MF formats using `Scene.save` with format-specific save options created via `FileFormat.get_format_by_extension`.
- **Assign materials to scene entities.** Assign Lambert, Phong, or PBR metallic-roughness materials to nodes, including glTF material properties such as `metallic_factor` and `roughness_factor`.
- **Work with math utilities.** Convert built-in parametric primitives like `Box`, `Cylinder`, `Sphere`, `Torus`, `Pyramid`, and `Dish` into triangulated `Mesh` objects using the `to_mesh` method.
- **Support animation with keyframes.** Animate scene properties using keyframe sequences with `AnimationClip`, `KeyframeSequence.add`, and `KeyFrame`, binding them to node or material properties.

## Installation

```bash
pip install aspose-3d-foss
```

## Quick Start

Create a triangle mesh and save it as ASCII STL using the aspose-3d-foss package version 26.1.0 on Python 3.7 or later, leveraging `StringIO` and the `FileFormat.get_format_by_extension` and `create_save_options` members to configure the output stream and format options.

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

## Additional Examples

The examples below demonstrate building meshes from scratch, assigning PBR materials, and exporting to additional formats like glTF and 3MF.

<details>
<summary>Assign a PBR material and export to glTF</summary>

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
<summary>Convert a parametric primitive to a mesh</summary>

```python
from aspose.threed.entities import Box

box = Box(10, 20, 30)
mesh = box.to_mesh()
print(f"Control points: {len(mesh.control_points)}")
```

</details>

<details>
<summary>Build a cube and export it to 3MF</summary>

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

- `aspose.threed`: The `aspose.threed` module provides core scene graph types including `Scene`, `Node`, and `Mesh`, with `Scene.open`() and `Scene.save`() handling file I/O using format-specific options such as `ObjLoadOptions` and `GltfSaveOptions`, and `Scene.animation_clips` exposing a list of `AnimationClip` objects.
- `aspose.threed.entities`: The `aspose.threed.entities` module exposes mesh and primitive types such as `Box`, `Camera`, and `Light`, where `Box.to_mesh`() converts parameterized primitives to `Mesh` instances and `Camera`/`Light` expose geometric properties like `near_plane` and `far_plane`.
- `aspose.threed.shading`: The `aspose.threed.shading` module defines material types including `PhongMaterial` and `PbrMaterial`, with `PbrMaterial` exposing `metallic_factor` and `roughness_factor` for physically based rendering.
- `aspose.threed.formats`: The `aspose.threed.formats` module provides format-specific load and save options such as `ObjLoadOptions` and `GltfSaveOptions`, with `FileFormat.get_format_by_extension`() enabling format detection by file extension.
- `aspose.threed.utilities`: The `aspose.threed.utilities` module supplies math types including `Vector3`, `Matrix4`, and `Quaternion`, supporting operations like normalize, dot product, and slerp interpolation.
- `aspose.threed.animation`: The `aspose.threed.animation` module supports animation via `AnimationClip`, `AnimationNode`, and `KeyframeSequence`, where `Scene.create_animation_clip`() creates clips and `KeyframeSequence.add`() inserts keyframes with interpolation control.

</details>

- `Scene`
  - `open(file_or_stream, options)`, `save(file_or_stream, format_or_options)`, `from_file(file_name)`
  - `root_node`, `sub_scenes`, `asset_info`, `animation_clips`
  - `create_animation_clip(name)`, `clear()`
- `Node`
  - `create_child_node(node_name, entity, material) -> 'Node'`
  - `add_entity(entity)`, `add_child_node(node)`, `merge(node)`
  - `entity`, `entities`, `material`, `materials`, `child_nodes`, `parent_node`
  - `transform`, `global_transform`, `visible`, `excluded`
  - `evaluate_global_transform(with_geometric_transform)`, `get_bounding_box()`
- `Entity` (base of `Mesh` and the primitive shapes)
  - `get_bounding_box()`, `parent_node`, `parent_nodes`, `excluded`, `name`
- `Transform` / `GlobalTransform`
  - `translation`, `scaling`, `rotation`, `euler_angles`, `transform_matrix`
  - `set_translation(tx, ty, tz)`, `set_scale(sx, sy, sz)`, `set_rotation(rw, rx, ry, rz)`

- `Mesh(name)`
  - `control_points: ArrayListAdapter[Vector4]`, `polygon_count`, `polygons`
  - `create_polygon(*indices)`, `triangulate()`, `get_bounding_box()`
- `Box`, `Cylinder`, `Sphere`, `Torus`, `Pyramid`, `Dish`, `Circle`, `Ellipse`, `Frustum`
  - each exposes `to_mesh() -> 'Mesh'` to convert the parameterized primitive into a concrete mesh
- `Camera`, `Light`
  - `near_plane`, `far_plane`, `field_of_view`, `direction`, `target`, `up`

- `Material` (base) — `get_texture(slot_name)`, `set_texture(slot_name, texture)`
- `LambertMaterial` — `emissive_color`, `ambient_color`, `diffuse_color`, `transparent_color`, `transparency`
- `PhongMaterial(LambertMaterial)` — adds `specular_color`, `specular_factor`, `shininess`, `reflection_color`
- `PbrMaterial` — `albedo`, `metallic_factor`, `roughness_factor`, `albedo_texture`, `normal_texture`, `occlusion_texture`, `emissive_texture`, `emissive_color`

- `ObjLoadOptions` — `flip_coordinate_system`, `enable_materials`, `scale`, `normalize_normal`
- `ObjSaveOptions` — `apply_unit_scale`, `point_cloud`, `verbose`, `serialize_w`,
  `enable_materials`, `flip_coordinate_system`, `axis_system`
- `StlLoadOptions` / `StlSaveOptions` — `binary_mode` (save only), `scale`, `flip_coordinate_system`
- `GltfLoadOptions` / `GltfSaveOptions` — `binary_mode` (save only), `flip_tex_coord_v`
- `ColladaLoadOptions` / `ColladaSaveOptions` — `flip_coordinate_system`, `enable_materials`
  (save only), `indented` (save only)
- `ThreeMfLoadOptions` / `ThreeMfSaveOptions` — `flip_coordinate_system`, `enable_compression`
  (save only), `build_all` (save only), `pretty_print` (save only), `unit` (save only)
- `FbxLoadOptions` / `FbxSaveOptions` — `compatible_mode`, `export_textures`, `embed_textures` (see [Scope and limitations](#scope-and-limitations))
- `FileFormat` — `detect(stream, file_name)`, `get_format_by_extension(extension_name)`, `can_import`, `can_export`

- `Vector2`, `Vector3`, `Vector4` — `x`/`y`/`z`/`w`, `length`, `normalize()`, `dot()`, `cross()`
- `Matrix4` — `translate()`, `scale()`, `rotate()`, `decompose()`, `inverse()`, `get_identity()`
- `Quaternion` — `slerp(t, v1, v2)`, `to_matrix()`, `from_euler_angle()`, `from_angle_axis()`
- `BoundingBox` — `minimum`, `maximum`, `center`, `size`, `merge()`, `contains()`

- `AnimationClip` — `create_animation_node(name) -> AnimationNode`, `animations`, `start`, `stop`
- `AnimationNode` — `create_bind_point(obj, prop_name)`, `get_keyframe_sequence(target, prop_name,
  channel_name, create)`, `bind_points`, `sub_animations`
- `AnimationChannel` (extends `KeyframeSequence`) — `component_type`, `default_value`,
  `keyframe_sequence`
- `KeyframeSequence` — `add(time, value, interpolation)`, `key_frames`, `pre_behavior`/
  `post_behavior` (`Extrapolation`)
- `KeyFrame` — `time`, `value`, `interpolation` (`Interpolation`), tangent/weight fields
  (`tangent_weight_mode`, `step_mode`, `tension`, `continuity`, `bias`)
- `BindPoint`, `Interpolation`, `Extrapolation`/`ExtrapolationType`, `StepMode`, `WeightedMode`

- `ImportException`, `ExportException`, `ParseException`, `InvalidOperationException`

## Documentation and Resources

The verified documentation targets explain how to install and use Aspose.3D FOSS for Python to load, convert, and manipulate 3D files, with links to a getting started guide, task-focused how-to guides, and a full API reference covering all 303 public types.

- [Getting started guide](https://docs.aspose.org/3d/python/)
- [How-to guides & FAQ](https://kb.aspose.org/3d/python/)
- [Full API reference](https://reference.aspose.org/3d/python/)
- [Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues)

- **[Getting started guide](https://docs.aspose.org/3d/python/)** — installation, key capabilities,
  and links to detailed developer guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/3d/python/)** — task-focused how-to guides for
  loading, converting, and manipulating 3D files with the pip-installable library.
- **[Full API reference](https://reference.aspose.org/3d/python/)** — the complete, browsable
  reference for all 303 public types (the [API reference](#api-reference) section above covers
  the essentials).
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues) on GitHub.

## Scope and Limitations

Aspose.3D FOSS for Python focuses on scene-graph modeling and the OBJ, STL, glTF, COLLADA, and 3MF format pipelines, reading, building, and writing 3D scene data without rendering or rasterizing scenes, and does not implement the `aspose.threed.render` module or its related classes, nor does it support `Mesh` boolean operations or NURBS curve/surface evaluation.

- COLLADA import works, but COLLADA export is not currently reachable through the public `Scene.save`() API — the exporter dispatcher registers `FbxExporter` ahead of the Collada plugin and raises an exception before the real Collada exporter is ever reached, even though a working implementation exists in the source tree.
- FBX support is more limited than the other formats: the FBX tokenizer and parser are exercised by the test suite, but `FbxExporter.save`() and `FbxExporter.save_to_stream`() raise an exception, and full round-trip FBX import/export is not covered by the bundled tests the way OBJ, STL, glTF, COLLADA, and 3MF are.
- The `aspose.threed.render` module (`Renderer`, `IRenderWindow`, `IBuffer`, `ICommandList`, `ITexture2D`, and related classes) is not implemented, `Mesh` boolean operations (union, difference, intersect, `do_boolean`) and NURBS curve/surface evaluation (`NurbsCurve.evaluate`, `NurbsSurface.to_mesh`) also raise an exception.

This project focuses on scene-graph modeling and the OBJ, STL, glTF, COLLADA, and 3MF format
pipelines. The `aspose.threed.render` module (`Renderer`, `IRenderWindow`, `IBuffer`,
`ICommandList`, `ITexture2D`, and related classes) is not implemented — this library reads,
builds, and writes 3D scene data, it does not render or rasterize scenes. `Mesh` boolean
operations (`union`, `difference`, `intersect`, `do_boolean`) and NURBS curve/surface evaluation
(`NurbsCurve.evaluate`, `NurbsSurface.to_mesh`) also raise `NotImplementedError`.

FBX support is more limited than the other formats: the FBX tokenizer and parser are exercised by
the test suite, but `FbxExporter.save()` and `FbxExporter.save_to_stream()` raise
`NotImplementedError`, and full round-trip FBX import/export is not covered by the bundled tests
the way OBJ, STL, glTF, COLLADA, and 3MF are. Treat FBX as experimental and prefer the other
formats when round-trip fidelity matters.

COLLADA import works, but COLLADA export is not currently reachable through the public
`Scene.save()` API — the exporter dispatcher registers `FbxExporter` ahead of the Collada plugin
and raises `NotImplementedError` before the real Collada exporter is ever reached, even though a
working implementation exists in the source tree.

## Development and Testing

Clone the repository, install it in editable mode, and run the test suite with python -m unittest discover tests/ or a single test file with python -m unittest tests.

- `tests/`
- `.github/workflows/`
- `docs/`

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git
cd Aspose.3D-FOSS-for-Python
pip install -e .
python -m unittest discover tests/
```

Run a single test file:

```bash
python -m unittest tests.test_obj_importer
```

## License

Aspose.3D FOSS for Python is released under the MIT License. You may use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software, provided the copyright notice and the permission notice accompany every copy. See [LICENSE](LICENSE).
