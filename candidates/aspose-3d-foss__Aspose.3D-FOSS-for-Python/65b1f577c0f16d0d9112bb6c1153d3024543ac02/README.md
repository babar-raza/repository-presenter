# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/) ![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

Aspose.3D FOSS for Python is a pure-Python, MIT-licensed library for loading, constructing, and exporting 3D scenes. It reads and writes OBJ, STL, glTF/GLB, COLLADA, and 3MF files, plus imports FBX, through a `Scene`, `Node`, and `Mesh` object graph, with no native runtime or external SDK to install. Developers use it to build 3D content programmatically, for example by creating primitives like `Box` or `Sphere`, assigning materials from `aspose.threed.shading`, and saving to formats such as `.gltf` or `.stl`. The library supports Python versions 3.7 through 3.12 and requires Python >=3.7.

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

- **Load multiple 3D formats.** Create 3D scenes by constructing meshes with control points and polygons, then attach them to scene nodes with materials.
- **Export to common 3D formats.** Export scenes to `.gltf` and `.stl` formats using `FileFormat` and format-specific save options, including binary and ASCII modes.
- **Construct and manipulate meshes.** Inspect mesh geometry by accessing control points, polygon count, and bounding boxes through the `Mesh` API.
- **Assign materials to geometry.** Apply physically based rendering materials with configurable albedo, metallic factor, and roughness factor via the shading module.
- **Build and traverse scene graphs.** Manage scene hierarchy by creating child nodes, setting transforms, and assigning materials to individual entities.
- **Triangulate arbitrary polygons.** Build polygonal meshes programmatically using `PolygonBuilder`-style operations to add control points and create polygons.
- **Create keyframe animations.** Support for 3D formats includes detection, import, and export via `FileFormat.formats`, `FileFormat.get_format_by_extension`, and `FileFormat.create_save_options`.

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

The following examples demonstrate creating meshes, assigning materials, and saving scenes to various 3D formats using aspose-3d-foss.

<details>
<summary>View Additional Examples</summary>

### Create a sphere with a metallic red material and save it as STL

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

### Build a triangle mesh, apply a PBR material, and export to text-based GLTF

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

### Construct a triangle mesh and export it as ASCII STL using a `StringIO` stream

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

### Build a cube mesh and save it as uncompressed 3MF to a `BytesIO` stream

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

### Generate a box mesh and inspect its control point count

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

- `aspose.threed.Scene`: Create, open, and manage 3D scenes using the `aspose.threed.Scene` class, which provides methods like `Scene.open`, `Scene.save`, `Scene.root_node`, `Scene.create_animation_clip`, `Scene.get_animation_clip`, `Scene.clear`, `Scene.sub_scenes`, `Scene.library`, `Scene.asset_info`, `Scene.poses`, and `Scene.render`.
- `aspose.threed.Node`: Navigate and manipulate the scene hierarchy with the `aspose.threed.Node` class, which supports operations such as `Node.add_child_node`, `Node.create_child_node`, `Node.add_entity`, `Node.get_child`, `Node.get_entity`, `Node.child_nodes`, `Node.parent_node`, `Node.entities`, `Node.global_transform`, `Node.evaluate_global_transform`, `Node.get_bounding_box`, `Node.material`, `Node.materials`, `Node.transform`, `Node.visible`, `Node.excluded`, `Node.meta_datas`, `Node.select_objects`, `Node.select_single_object`, and `Node.merge`.
- `aspose.threed.Mesh`: Construct and modify polygonal geometry using the `aspose.threed.Mesh` class, which offers access to `Mesh.control_points`, `Mesh.polygons`, `Mesh.edges`, `Mesh.polygon_count`, `Mesh.get_polygon_size`, `Mesh.get_bounding_box`, `Mesh.triangulate`, `Mesh.to_mesh`, `Mesh.do_boolean`, `Mesh.union`, `Mesh.difference`, `Mesh.intersect`, `Mesh.optimize`, `Mesh.is_manifold`, `Mesh.create_polygon`, and `Mesh.get_entity_renderer_key`.
- `aspose.threed.FileFormat`: Identify and configure supported file formats with the `aspose.threed.FileFormat` class, which includes constants like `FileFormat.WAVEFRONT_OBJ`, `FileFormat.FBX7400ASCII`, `FileFormat.GLTF2`, `FileFormat.MICROSOFT_3MF_FORMAT`, and methods such as `FileFormat.can_import`, `FileFormat.can_export`, `FileFormat.content_type`, `FileFormat.get_format_by_extension`, `FileFormat.create_load_options`, and member `create_save_options`.
- `aspose.threed.shading`: Define material properties and appearance using the `aspose.threed.shading` module, which provides classes and attributes such as member `diffuse_color`, member `metallic_factor`, and member `roughness_factor`.
- `aspose.threed.entities`: Create and modify geometric primitives and shapes using the `aspose.threed.entities` module, which includes utilities like member entity, member `control_points`, member `create_polygon`, and member `create_child_node`.
- `aspose.threed.animation`: Work with animation data using the `aspose.threed.animation` module, which integrates with `Scene.animation_clips` and `Scene.current_animation_clip` to manage time-based transformations and keyframes.
- `aspose.threed.utilities`: Perform common utility operations using the `aspose.threed.utilities` module, which includes helper classes and methods such as member decode, member read, member seek, member getvalue, member loads, member add, member `binary_mode`, and member `BytesIO`.
- `aspose.threed.formats`: Load and save 3D models in various formats using the `aspose.threed.formats` module, which provides format-specific loaders and savers for OBJ, GLTF, and other supported types.
- `aspose.threed.render`: Render 3D scenes to images or video using the `aspose.threed.render` module, which supports rendering from `Scene.render` and integrates with the scene graph and camera configuration.
- `aspose.threed.deformers`: Apply mesh deformation effects using the `aspose.threed.deformers` module, which provides tools for modifying geometry through procedural or skeletal influences.
- `aspose.threed.profiles`: Define and manage cross-section profiles for extrusion and sweep operations using the `aspose.threed.profiles` module.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/3d/python/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/3d/python/)** — The how-to guides and FAQ provide task-focused answers for common 3D-processing questions.
- **[Full API reference](https://reference.aspose.org/3d/python/)** — The full API reference is the complete, browsable reference for all 305 public types. It covers all 652 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- **[Implementation progress notes](docs/foss-python-progress.md)** — The implementation progress notes describe the current FOSS-edition porting status.
- **[Release process](docs/releasing.md)** — The release process explains how a version of aspose-3d-foss is tagged and published to PyPI.
- **[Scene/Node/Entity/Transform](docs/IMPLEMENTATION_SUMMARY.md)** — The internal format-implementation notes cover `Scene`, `Node`, `Entity`, and `Transform` development history.
- **[OBJ importer](docs/OBJ_IMPORTER_IMPLEMENTATION.md)** — The OBJ importer implementation notes describe the historical development of OBJ support.
- **[STL import/export](docs/STL_IMPORT_IMPLEMENTATION.md)** — The STL import implementation notes cover the historical development of STL import and export.
- **[FBX parser](docs/FBX_IMPLEMENTATION_SUMMARY.md)** — The FBX parser implementation notes describe the historical development of FBX support.
- **[PyPI packaging readiness](docs/PYPI_READINESS.md)** — The PyPI packaging readiness notes cover the historical development of PyPI packaging.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues).

## Scope and Limitations

Aspose.3D FOSS for Python version 26.1.0 supports reading and writing OBJ, STL, glTF, and COLLADA files on Python 3.7 through 3.12, and provides core scene graph and mesh manipulation capabilities.

- No file format registers an importer or exporter for PDF, PLY, RVM, U3D, JT, AMF, HTML5, A3DW, USD, or Draco, and attempts to use these formats raise an error. FBX import is experimental and lightly verified, while FBX export is not supported. COLLADA import works but COLLADA export is unreachable through `Scene.save`() due to exporter lookup failure. Load and save options for OBJ, STL, glTF, and COLLADA must be imported from their format-specific submodules, not from the shared top-level `aspose.threed.formats` package. The `aspose.threed.render` module and `Scene.render`() are not supported. `Texture` and `TextureBase` cannot be constructed, so image-backed textures cannot be created. `Watermark.encode_watermark`(), `Watermark.decode_watermark`(), and all `TransformBuilder` methods are not supported. `Mesh.do_boolean`(), `union()`, `difference()`, and `intersect()` are not supported. `NurbsCurve.evaluate`(), `NurbsCurve.evaluate_at`(), and `NurbsSurface.to_mesh`() are not supported. `PointCloud.from_geometry`(), `PointCloud.from_geometry_with_density`(), and `AxisSystem` are not supported.

## Development and Testing

Build and test Aspose.3D FOSS for Python using the assets in the tests/ directory and the CI workflows in .github/workflows/; the package requires Python >=3.7 and supports versions 3.7, 3.8, 3.9, 3.10, 3.11, and 3.12. Run tests with python -m unittest discover tests/; there are 33 real test files.

The suite covers 34 test files under `tests/`. Releases run through the [publish workflow](.github/workflows/publish.yml).

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
