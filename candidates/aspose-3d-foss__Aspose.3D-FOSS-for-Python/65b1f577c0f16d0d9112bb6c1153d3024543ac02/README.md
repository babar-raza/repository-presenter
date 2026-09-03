# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/) ![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

Aspose.3D FOSS for Python is a pure-Python, MIT-licensed library for loading, constructing, and exporting 3D scenes. It reads and writes OBJ, STL, glTF, COLLADA, and 3MF files, plus imports FBX, through a `Scene`, `Node`, and `Mesh` object graph, with no native runtime or external SDK to install. Developers use it to build 3D content programmatically, for example by creating primitives like `Box` or `Sphere`, assigning materials from `aspose.threed.shading`, and saving to formats such as `.gltf` or `.stl`. The library supports Python versions 3.7 through 3.12 and requires Python >=3.7.

## Navigation

- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation and Resources](#documentation-and-resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## Key Capabilities

- **Load multiple 3D formats.** Import OBJ, STL, glTF, COLLADA, and 3MF files with `Scene.open`() and auto-detection from file extension or explicit `FileFormat`.
- **Export to common 3D formats.** Build custom meshes programmatically by adding control points and polygons via the `aspose.threed.Mesh` class, then assign them to nodes and export to formats like `.stl` or 3MF using appropriate save options.
- **Construct and manipulate meshes.** Inspect mesh geometry by accessing control points and polygon counts, and compute bounding boxes or edge information using methods provided by the `aspose.threed.Mesh` class.
- **Assign materials to geometry.** Manage scene hierarchy and node properties such as transform, material, visibility, and child relationships using the `aspose.threed.Node` class and its methods.
- **Build and traverse scene graphs.** Apply geometric transformations to nodes using the `aspose.threed.Transform` class to adjust translation, rotation, and scaling without altering the underlying entity.
- **Triangulate arbitrary polygons.** Construct polygons from control points using the `aspose.threed.PolygonBuilder` pattern, enabling precise mesh definition for complex shapes before attaching them to scene nodes.
- **Create keyframe animations.** Define and manipulate animation data using classes like `aspose.threed.AnimationClip`, `aspose.threed.AnimationNode`, and `aspose.threed.KeyframeSequence` to support time-based scene changes.
- **Convert primitives to meshes.** Inspect scene structure and node relationships using the `aspose.threed.Pose` class and related APIs to evaluate global transforms and extract spatial information.

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

Create a scene, add a box entity with a Lambert material, and save it as a GLTF file using Aspose.3D FOSS for Python version 26.1.0 on Python 3.7 or later.

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

The following examples demonstrate creating geometry, applying materials, and saving to various formats using Aspose.3D FOSS for Python.

<details>
<summary>Create a sphere with `PbrMaterial` and save to STL.</summary>

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
<summary>Build a triangle mesh, assign `PbrMaterial`, and export to GLTF text.</summary>

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
<summary>Generate a triangle mesh and save as ASCII STL using `StringIO`.</summary>

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
<summary>Construct a `Box` entity and inspect its `control_points` count.</summary>

```python
from aspose.threed.entities import Box

box = Box(10, 20, 30)
mesh = box.to_mesh()
print(f"Control points: {len(mesh.control_points)}")
```

</details>

<details>
<summary>Build a cube mesh and save to 3MF without compression.</summary>

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

- `aspose.threed.Scene`: Create, open, and save 3D scenes using the `aspose.threed.Scene` class, which provides methods like `Scene.open`, `Scene.save`, `Scene.root_node`, `Scene.create_animation_clip`, `Scene.get_animation_clip`, `Scene.clear`, `Scene.sub_scenes`, `Scene.library`, `Scene.poses`, `Scene.asset_info`, and `Scene.render`.
- `aspose.threed.Node`: Manage scene hierarchy and transform entities with the `aspose.threed.Node` class, which supports adding child nodes via `Node.add_child_node` and `Node.create_child_node`, assigning entities and materials via `Node.entity` and `Node.material`, and querying transforms and visibility via `Node.global_transform`, `Node.get_bounding_box`, `Node.visible`, `Node.child_nodes`, `Node.parent_node`, `Node.entities`, `Node.get_entity`, `Node.select_objects`, `Node.select_single_object`, `Node.merge`, `Node.meta_datas`, `Node.asset_info`, and `Node.excluded`.
- `aspose.threed.Mesh`: Construct and manipulate polygonal geometry using the `aspose.threed.Mesh` class, which exposes control points via `Mesh.control_points`, polygons via `Mesh.polygons` and `Mesh.create_polygon`, and provides operations like `Mesh.triangulate`, `Mesh.optimize`, `Mesh.get_bounding_box`, `Mesh.polygon_count`, `Mesh.edges`, `Mesh.is_manifold`, `Mesh.union`, `Mesh.intersect`, `Mesh.difference`, `Mesh.do_boolean`, `Mesh.get_polygon_size`, `Mesh.to_mesh`, and `Mesh.get_entity_renderer_key`.
- `aspose.threed.shading`: Define material properties for 3D models using the `aspose.threed.shading` module, which includes classes like `LambertMaterial` and `PbrMaterial` that expose attributes such as `diffuse_color`, `metallic_factor`, and `roughness_factor`.
- `aspose.threed.FileFormat`: Detect and configure format-specific import and export behavior using the `aspose.threed.FileFormat` class, which provides methods like `FileFormat.get_format_by_extension`, `FileFormat.can_import`, `FileFormat.can_export`, `FileFormat.content_type`, `FileFormat.create_load_options`, and constants such as `FileFormat.FBX7400ASCII`, `FileFormat.GLTF2`, `FileFormat.MICROSOFT_3MF_FORMAT`, and `FileFormat.WAVEFRONT_OBJ`.
- `aspose.threed.AnimationClip`: Create and manage animation sequences using the `aspose.threed.AnimationClip` class, which represents a named collection of keyframe data and integrates with `Scene.animation_clips` and `Scene.current_animation_clip`.
- `aspose.threed.PolygonBuilder`: Build polygonal meshes programmatically using the `aspose.threed.PolygonBuilder` class, which simplifies the creation of complex geometry by accumulating control points and polygon definitions before producing a final `Mesh`.
- `aspose.threed.entities`: Generate standard geometric primitives such as `Box`, `Sphere`, and `Cylinder` using the `aspose.threed.entities` module, which provides classes that expose a `to_mesh` method to convert the primitive into a `Mesh` instance.
- `aspose.threed.utilities`: Work with mathematical types and helper utilities using the `aspose.threed.utilities` module, which includes `Vector3` and `Vector4` for representing 3D points and homogeneous coordinates.
- `aspose.threed.formats`: Configure format-specific save options using classes in the `aspose.threed.formats` module, such as `GltfSaveOptions` and `ThreeMfSaveOptions`, which expose properties like `binary_mode` and `enable_compression`.
- `aspose.threed.animation`: Define and evaluate time-based transformations using the `aspose.threed.animation` module, which includes `AnimationNode` and `KeyframeSequence` for constructing and querying animated behavior.
- `aspose.threed.deformers`: Apply mesh deformation effects using the `aspose.threed.deformers` module, which provides classes for modifying geometry through procedural or skeletal deformation techniques.

</details>

## Documentation and Resources

The verified documentation for aspose-3d-foss targets users of version 26.1.0 on Python 3.7 through 3.12, explaining how to load, inspect, and convert 3D scenes using APIs such as `Scene`, `root_node`, `child_nodes`, entity, `control_points`, `polygon_count`, and `to_mesh`.

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

Aspose.3D FOSS for Python version 26.1.0 supports reading and writing OBJ, STL, glTF, and COLLADA files on Python 3.7 through 3.12, and provides core scene graph and mesh manipulation capabilities.

- No file format registers an importer or exporter for PDF, PLY, RVM, U3D, JT, AMF, HTML5, A3DW, USD, or Draco, and attempts to use these formats raise an error. FBX import is experimental and lightly verified, while FBX export is not supported. COLLADA import works but COLLADA export is unreachable through `Scene.save`() due to exporter lookup failure. Load and save options for OBJ, STL, glTF, and COLLADA must be imported from their format-specific submodules, not from the shared top-level `aspose.threed.formats` package. The `aspose.threed.render` module and `Scene.render`() are not supported. `Texture` and `TextureBase` cannot be constructed, so image-backed textures cannot be created. `Watermark.encode_watermark`(), `Watermark.decode_watermark`(), and all `TransformBuilder` methods are not supported. `Mesh.do_boolean`(), `union()`, `difference()`, and `intersect()` are not supported. `NurbsCurve.evaluate`(), `NurbsCurve.evaluate_at`(), and `NurbsSurface.to_mesh`() are not supported. `PointCloud.from_geometry`(), `PointCloud.from_geometry_with_density`(), and `AxisSystem` are not supported.

## Development and Testing

Build and test Aspose.3D FOSS for Python using the assets in the tests/ directory and the CI workflows in .github/workflows/; the package requires Python >=3.7 and supports versions 3.7, 3.8, 3.9, 3.10, 3.11, and 3.12.

- `tests/`
- `.github/workflows/`
- `docs/`

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
