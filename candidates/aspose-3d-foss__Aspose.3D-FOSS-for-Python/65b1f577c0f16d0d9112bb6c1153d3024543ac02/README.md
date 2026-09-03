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

The aspose-3d-foss package exposes `aspose.threed.Scene` as the primary entry point for loading, saving, and manipulating 3D scenes, and `aspose.threed.FileFormat` for working with supported file formats. `Scene` provides methods like `Scene.open` and `Scene.save` to handle 3D content, while `FileFormat` exposes format-specific capabilities such as `FileFormat.get_format_by_extension`.

The verified public surface has 343 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `A3DObject` | Defined as class A3DObject(INamedObject). |
| `AnimationChannel` | Defined as class AnimationChannel(KeyframeSequence). |
| `AnimationClip` | Defined as class AnimationClip(SceneObject). |
| `AnimationNode` | Defined as class AnimationNode(A3DObject). |
| `ArrayListAdapter` | Adapter class that wraps List[T] and implements IArrayList[T]. |
| `AssetInfo` | Defined as class AssetInfo(A3DObject). |
| `Axis` | The coordinate axis. |
| `AxisSystem` | Axis system is an combination of coordinate system, up vector and front vector. |
| `BindPoint` | Defined as class BindPoint(A3DObject). |
| `BonePose` | Defined as class BonePose(A3DObject). |
| `BoundingBox2D` | The axis-aligned bounding box for Vector2 |
| `BoundingBoxExtent` | The extent of the bounding box |
| `Box` | Defined as class Box(Primitive). |
| `Camera` | Defined as class Camera(Entity). |
| `Circle` | Defined as class Circle(Primitive). |
| `ComposeOrder` | The order to compose transform matrix |
| `CoordinateSystem` | The left handed or right handed coordinate system. |
| `Curve` | Defined as class Curve(Entity). |
| `CustomObject` | Defined as class CustomObject(A3DObject). |
| `Cylinder` | Defined as class Cylinder(Primitive). |
| `Dish` | Defined as class Dish(Primitive). |
| `Ellipse` | Defined as class Ellipse(Primitive). |
| `Entity` | Defined as class Entity(SceneObject). |
| `ExportException` | Exceptions when Aspose.3D failed to export the scene to file. |
| `Extrapolation` | Defined as class Extrapolation. |
| `FMatrix4` | Matrix 4x4 with all component in float type |
| `FileContentType` | File content type |
| `FileFormat` | Defined as class FileFormat. |
| `FileFormatType` | File format type |
| `Frustum` | Defined as class Frustum(Primitive). |
| `Geometry` | Defined as class Geometry(Entity). |
| `GlobalTransform` | Defined as class GlobalTransform. |
| `Group` | A Group represents the logical relationships of Node. |
| `INamedObject` | Defined as class INamedObject. |
| `IOExtension` | Utilities to write matrix/vector to binary writer |
| `ImageRenderOptions` | Defined as class ImageRenderOptions(A3DObject). |
| `ImportException` | Exception when Aspose.3D failed to open the specified source. |
| `KeyFrame` | Defined as class KeyFrame. |
| `KeyframeSequence` | Defined as class KeyframeSequence(A3DObject). |
| `Light` | Defined as class Light(Camera). |
| `LinearExtrusion` | Defined as class LinearExtrusion(Entity). |
| `MathUtils` | A set of useful mathematical utilities. |
| `Mesh` | Defined as class Mesh(Geometry). |
| `Node` | Defined as class Node(SceneObject). |
| `ParseException` | Exception when Aspose.3D failed to parse the input. |
| `Plane` | Defined as class Plane(Primitive). |
| `PolygonBuilder` | Defined as class PolygonBuilder. |
| `Pose` | Defined as class Pose(A3DObject, INamedObject). |
| `Primitive` | Defined as class Primitive(Geometry). |
| `Property` | Defined as class Property. |
| `PropertyCollection` | Defined as class PropertyCollection. |
| `PropertyFlags` | Property's flags |
| `Rect` | A class to represent the rectangle |
| `RelativeRectangle` | Relative rectangle |
| `RotationOrder` | The order controls which rx ry rz are applied in the transformation matrix. |
| `Scene` | Defined as class Scene(SceneObject). |
| `SceneObject` | Defined as class SceneObject(A3DObject). |
| `SemanticAttribute` | Allow user to use their own structure for static declaration of VertexDeclaration |
| `Sphere` | Defined as class Sphere(Primitive). |
| `Transform` | Defined as class Transform(A3DObject). |
| `TransformBuilder` | The TransformBuilder is used to build transform matrix by a chain of transformations. |
| `TrialException` | This is raised in Scene.Open/Scene.Save when no licenses are applied. |
| `Vertex` | Vertex reference, used to access the raw vertex in TriMesh. |
| `VertexDeclaration` | The declaration of a custom defined vertex's structure |
| `VertexField` | Vertex's field memory layout description. |
| `VertexFieldDataType` | Vertex field's data type |
| `VertexFieldSemantic` | The semantic of the vertex field |
| `Bone` | Defined as class Bone(A3DObject). |
| `BoneLinkMode` | Defined as class BoneLinkMode. |
| `Deformer` | Defined as class Deformer(A3DObject). |
| `MorphTargetChannel` | Defined as class MorphTargetChannel(A3DObject). |
| `MorphTargetDeformer` | Defined as class MorphTargetDeformer(Deformer). |
| `SkinDeformer` | Defined as class SkinDeformer(Deformer). |
| `ApertureMode` | Camera aperture modes. |
| `BooleanOperand` | This class encapsulates the transformed mesh as Boolean operation's operand. |
| `BooleanOperation` | Defined as class BooleanOperation. |
| `BooleanOperator` | Boolean operator allows you to apply Boolean operation on two IMeshConvertible instances. |
| `CompositeCurve` | A CompositeCurve is consisting of several curve segments. |
| `CurveDimension` | Defined as class CurveDimension. |
| `EndPoint` | The end point to trim the curve, can be a parameter value or a Cartesian point. |
| `HalfSpace` | HalfSpace represents a infinity space which is split by a plane, this can be used with BooleanOperator |
| `IIndexedVertexElement` | Defined as class IIndexedVertexElement. |
| `IMeshConvertible` | Entities that implemented this interface can be converted to Mesh |
| `IOrientable` | Orientable entities shall implement this interface. |
| `LightType` | Light types. |
| `Line` | A polyline is a path defined by a set of points with control_points, and connected by segments. |
| `MappingMode` | Defined as class MappingMode. |
| `NurbsCurve` | Defined as class NurbsCurve(Curve). |
| `NurbsDirection` | Defined as class NurbsDirection. |
| `NurbsSurface` | Defined as class NurbsSurface(Geometry). |
| `NurbsType` | Defined as class NurbsType. |
| `Patch` | Defined as class Patch(Geometry). |
| `PatchDirection` | Defined as class PatchDirection. |
| `PatchDirectionType` | Defined as class PatchDirectionType. |
| `PointCloud` | Defined as class PointCloud. |
| `InvalidOperationException` | Defined as class InvalidOperationException(Exception). |
| `PolygonModifier` | Defined as class PolygonModifier. |
| `ProjectionType` | Camera's projection types. |
| `Pyramid` | Parameterized pyramid. |
| `RectangularTorus` | Parameterized rectangular torus entity. |
| `ReferenceMode` | Defined as class ReferenceMode. |
| `RevolvedAreaSolid` | RevolvedAreaSolid entity. |
| `RotationMode` | The frustum's rotation mode. |
| `Shape` | Base class for all shape entities. |
| `Skeleton` | The Skeleton is mainly used by CAD software to help designer to manipulate the transformation of skeletal structure, it's usually useless outside the CAD softwares. |
| `SkeletonType` | Skeleton type enum. |
| `SplitMeshPolicy` | Share vertex/control point data between sub-meshes or each sub-mesh has its own compacted data. |
| `SweptAreaSolid` | SweptAreaSolid entity. |
| `TextureMapping` | Defined as class TextureMapping. |
| `Torus` | Parameterized torus entity. |
| `TransformedCurve` | TransformedCurve entity. |
| `TriMesh` | TriMesh is a triangle mesh that stores triangles. |
| `TrimmedCurve` | TrimmedCurve entity. |
| `VertexElement` | Defined as class VertexElement. |
| `VertexElementBinormal` | Defined as class VertexElementBinormal(VertexElementFVector). |
| `VertexElementDoublesTemplate` | A helper class for defining concrete implementations. |
| `VertexElementEdgeCrease` | Defines the edge crease values for specified components. |
| `VertexElementFVector` | Defined as class VertexElementFVector(VertexElement). |
| `VertexElementHole` | Defines the hole information for specified components. |
| `VertexElementIntsTemplate` | A helper class for defining concrete implementations with int data. |
| `VertexElementMaterial` | Defines the material for specified components. |
| `VertexElementNormal` | Defined as class VertexElementNormal(VertexElementFVector). |
| `VertexElementPolygonGroup` | Defines the polygon group for specified components. |
| `VertexElementSmoothingGroup` | Defined as class VertexElementSmoothingGroup(VertexElementIntsTemplate). |
| `VertexElementSpecular` | Defines the specular color for specified components. |
| `VertexElementTangent` | Defined as class VertexElementTangent(VertexElementFVector). |
| `VertexElementTemplate` | A helper class for defining concrete implementations of vertex elements with typed data. |
| `VertexElementType` | Defined as class VertexElementType. |
| `VertexElementUV` | Defined as class VertexElementUV(VertexElementFVector). |
| `VertexElementUserData` | Defines the user data for specified components. |
| `VertexElementVector4` | Defines the vector4 data for specified components. |
| `VertexElementVertexColor` | Defined as class VertexElementVertexColor(VertexElementFVector). |
| `VertexElementVertexCrease` | Defines the vertex crease values for specified components. |
| `VertexElementVisibility` | Defines the visibility for specified components. |
| `VertexElementWeight` | Defines the weight for specified components. |
| `A3dwSaveOptions` | Save options for A3DW |
| `AmfSaveOptions` | Save options for AMF |
| `BasicLoadOptions` | Simple LoadOptions subclass for basic loading options. |
| `ColladaLoadOptions` | Defined as class ColladaLoadOptions(LoadOptions). |
| `ColladaLoadOptions` | Load options for Collada |
| `ColladaSaveOptions` | Defined as class ColladaSaveOptions(SaveOptions). |
| `ColladaSaveOptions` | Save options for collada |
| `ColladaTransformStyle` | The node's transformation style of node |
| `Discreet3dsLoadOptions` | Load options for Discreet 3DS |
| `Discreet3dsSaveOptions` | Save options for Discreet 3DS |
| `DracoCompressionLevel` | Compression level for draco file |
| `DracoFormat` | Google Draco format |
| `DracoSaveOptions` | Save options for Draco |
| `Exporter` | Defined as class Exporter. |
| `FbxLoadOptions` | Defined as class FbxLoadOptions(LoadOptions). |
| `FbxLoadOptions` | Load options for FBX |
| `FbxSaveOptions` | Defined as class FbxSaveOptions(SaveOptions). |
| `FbxSaveOptions` | Save options for FBX |
| `FormatDetector` | Defined as class FormatDetector. |
| `GltfEmbeddedImageFormat` | Embedded image format for GLTF |
| `GltfLoadOptions` | Defined as class GltfLoadOptions(LoadOptions). |
| `GltfLoadOptions` | Load options for glTF |
| `GltfSaveOptions` | Defined as class GltfSaveOptions(SaveOptions). |
| `GltfSaveOptions` | Save options for glTF |
| `Html5SaveOptions` | Save options for HTML5 |
| `IOConfig` | Defined as class IOConfig. |
| `IOService` | Defined as class IOService. |
| `Importer` | Defined as class Importer. |
| `JtLoadOptions` | Load options for JT |
| `LoadOptions` | Defined as class LoadOptions(IOConfig). |
| `Microsoft3MFFormat` | Microsoft 3MF format |
| `Microsoft3MFSaveOptions` | Save options for Microsoft 3MF |
| `ObjLoadOptions` | Defined as class ObjLoadOptions(LoadOptions). |
| `ObjLoadOptions` | Load options for OBJ |
| `ObjSaveOptions` | Defined as class ObjSaveOptions(SaveOptions). |
| `ObjSaveOptions` | Save options for OBJ |
| `PdfFormat` | Adobe's Portable Document Format |
| `PdfLightingScheme` | Lighting scheme for PDF export |
| `PdfLoadOptions` | Load options for PDF |
| `PdfRenderMode` | Render mode for PDF export |
| `PdfSaveOptions` | Save options for PDF |
| `Plugin` | Defined as class Plugin(ABC). |
| `PlyFormat` | PLY format |
| `PlyLoadOptions` | Load options for PLY |
| `PlySaveOptions` | Save options for PLY |
| `RvmFormat` | RVM format |
| `RvmLoadOptions` | Load options for RVM |
| `RvmSaveOptions` | Save options for RVM |
| `SaveOptions` | Defined as class SaveOptions(IOConfig). |
| `StlLoadOptions` | Defined as class StlLoadOptions(LoadOptions). |
| `StlLoadOptions` | Load options for STL |
| `StlSaveOptions` | Defined as class StlSaveOptions(SaveOptions). |
| `StlSaveOptions` | Save options for STL |
| `ThreeMfFormat` | Defined as class ThreeMfFormat. |
| `ThreeMfLoadOptions` | Defined as class ThreeMfLoadOptions(LoadOptions). |
| `ThreeMfSaveOptions` | Defined as class ThreeMfSaveOptions(SaveOptions). |
| `U3dLoadOptions` | Load options for U3D |
| `U3dSaveOptions` | Save options for U3D |
| `UsdSaveOptions` | Save options for USD |
| `XLoadOptions` | Load options for X format |
| `ColladaExporter` | Defined as class ColladaExporter(Exporter). |
| `ColladaFormat` | Defined as class ColladaFormat(FileFormat). |
| `ColladaFormatDetector` | Defined as class ColladaFormatDetector(FormatDetector). |
| `ColladaImporter` | Defined as class ColladaImporter(Importer). |
| `ColladaPlugin` | Defined as class ColladaPlugin(Plugin). |
| `ColladaTransformStyle` | Defined as class ColladaTransformStyle. |
| `FbxExporter` | Defined as class FbxExporter(Exporter). |
| `FbxFormat` | Defined as class FbxFormat(FileFormat). |
| `FbxFormatDetector` | Defined as class FbxFormatDetector(FormatDetector). |
| `FbxImporter` | Defined as class FbxImporter(Importer). |
| `FbxPlugin` | Defined as class FbxPlugin(Plugin). |
| `BinaryTokenizer` | Defined as class BinaryTokenizer. |
| `Token` | Defined as class Token. |
| `TokenType` | Defined as class TokenType. |
| `FbxElement` | Defined as class FbxElement. |
| `FbxParser` | Defined as class FbxParser. |
| `FbxScope` | Defined as class FbxScope. |
| `FbxTokenizer` | Defined as class FbxTokenizer. |
| `Token` | Defined as class Token. |
| `TokenType` | Defined as class TokenType. |
| `GltfExporter` | Defined as class GltfExporter(Exporter). |
| `GltfFormat` | Defined as class GltfFormat. |
| `GltfFormatDetector` | Defined as class GltfFormatDetector(FormatDetector). |
| `GltfImporter` | Defined as class GltfImporter(Importer). |
| `GltfPlugin` | Defined as class GltfPlugin(Plugin). |
| `ObjExporter` | Defined as class ObjExporter(Exporter). |
| `ObjFormat` | Defined as class ObjFormat(FileFormat). |
| `ObjFormatDetector` | Defined as class ObjFormatDetector(FormatDetector). |
| `ObjImporter` | Defined as class ObjImporter(Importer). |
| `ObjPlugin` | Defined as class ObjPlugin(Plugin). |
| `StlExporter` | Defined as class StlExporter(Exporter). |
| `StlFormat` | Defined as class StlFormat. |
| `StlFormatDetector` | Defined as class StlFormatDetector(FormatDetector). |
| `StlImporter` | Defined as class StlImporter(Importer). |
| `StlPlugin` | Defined as class StlPlugin(Plugin). |
| `ThreeMfExporter` | Defined as class ThreeMfExporter(Exporter). |
| `ThreeMfFormatDetector` | Defined as class ThreeMfFormatDetector(FormatDetector). |
| `ThreeMfImporter` | Defined as class ThreeMfImporter(Importer). |
| `ThreeMfPlugin` | Defined as class ThreeMfPlugin(Plugin). |
| `ArbitraryProfile` | This class allows you to construct a 2D profile directly from arbitrary curve. |
| `CShape` | IFC compatible C-shape profile that defined by parameters. |
| `CenterLineProfile` | IFC compatible center line profile. |
| `CircleShape` | IFC compatible circle profile. |
| `EllipseShape` | IFC compatible ellipse profile. |
| `FontFile` | Font file contains definitions for glyphs, this is used to create text profile. |
| `HShape` | IFC compatible H-shape profile. |
| `HollowCircleShape` | IFC compatible hollow circle profile. |
| `HollowRectangleShape` | IFC compatible hollow rectangular shape with both inner/outer rounding corners. |
| `LShape` | IFC compatible L-shape profile that defined by parameters. |
| `MirroredProfile` | IFC compatible mirror profile. |
| `ParameterizedProfile` | The base class of all parameterized profiles. |
| `Profile` | 2D Profile in xy plane. |
| `RectangleShape` | IFC compatible rectangle profile. |
| `TShape` | IFC compatible T-shape defined by parameters. |
| `Text` | Text profile, this profile describes contours using font and text. |
| `TrapeziumShape` | IFC compatible Trapezium shape defined by parameters. |
| `UShape` | IFC compatible U-shape defined by parameters. |
| `ZShape` | IFC compatible Z-shape profile that defined by parameters. |
| `BlendFactor` | Blend factor specify pixel arithmetic. |
| `CompareFunction` | Compare function for depth/stencil testing. |
| `CubeFace` | Cube face enumeration. |
| `CullFaceMode` | Cull face mode for face culling. |
| `DescriptorSetUpdater` | Descriptor set updater for shader resources. |
| `DrawOperation` | Draw operation type. |
| `DriverException` | Exception thrown when rendering driver fails. |
| `EntityRenderer` | Base class for rendering entities. |
| `EntityRendererFeatures` | Features supported by an entity renderer. |
| `EntityRendererKey` | The key of registered entity renderer. |
| `FrontFace` | Front face winding order. |
| `GLSLSource` | GLSL shader source. |
| `IBuffer` | Interface for vertex/index buffer. |
| `ICommandList` | Interface for command list. |
| `IDescriptorSet` | Interface for descriptor set. |
| `IIndexBuffer` | Interface for index buffer. |
| `IPipeline` | Interface for graphics pipeline. |
| `IRenderQueue` | Interface for render queue. |
| `IRenderTarget` | Interface for render target. |
| `IRenderTexture` | Interface for render texture. |
| `IRenderWindow` | Interface for render window. |
| `ITexture1D` | Interface for 1D texture. |
| `ITexture2D` | Interface for 2D texture. |
| `ITextureCodec` | Interface for texture codec. |
| `ITextureCubemap` | Interface for cubemap texture. |
| `ITextureDecoder` | Interface for texture decoder. |
| `ITextureEncoder` | Interface for texture encoder. |
| `ITextureUnit` | Interface for texture unit. |
| `IVertexBuffer` | Interface for vertex buffer. |
| `IndexDataType` | Data type for indices. |
| `InitializationException` | Exception thrown when rendering initialization fails. |
| `PixelFormat` | Pixel format for render targets. |
| `PixelMapMode` | Pixel mapping mode. |
| `PixelMapping` | Pixel mapping configuration. |
| `PolygonMode` | Polygon rendering mode. |
| `PostProcessing` | Post-processing effect. |
| `PresetShaders` | Predefined shaders. |
| `PushConstant` | Push constant for shaders. |
| `RenderFactory` | RenderFactory creates all resources that represented in rendering pipeline. |
| `RenderParameters` | Parameters for rendering. |
| `RenderQueueGroupId` | Render queue group ID. |
| `RenderResource` | Base class for render resources. |
| `RenderStage` | Render stage in the pipeline. |
| `RenderState` | Render state configuration. |
| `Renderer` | The context about renderer. |
| `RendererVariableManager` | Manages renderer variables. |
| `SPIRVSource` | SPIRV shader source. |
| `ShaderException` | Exception thrown when shader compilation/linking fails. |
| `ShaderProgram` | Shader program. |
| `ShaderSet` | Set of shaders for rendering. |
| `ShaderSource` | Shader source code. |
| `ShaderStage` | Shader stage. |
| `ShaderVariable` | Shader variable. |
| `StencilAction` | Stencil action. |
| `StencilState` | Stencil state configuration. |
| `TextureCodec` | Texture codec. |
| `TextureData` | Texture data. |
| `TextureType` | Texture type. |
| `Viewport` | Viewport for rendering. |
| `WindowHandle` | Window handle for render window. |
| `AlphaSource` | Source of alpha channel for textures. |
| `LambertMaterial` | Defined as class LambertMaterial(Material). |
| `Material` | Defined as class Material(A3DObject). |
| `PbrMaterial` | Defined as class PbrMaterial(Material). |
| `PbrSpecularMaterial` | Material for physically based rendering based on diffuse color/specular/glossiness. |
| `PhongMaterial` | Defined as class PhongMaterial(LambertMaterial). |
| `ShaderMaterial` | A shader material allows to describe the material by external rendering engine or shader language. |
| `ShaderTechnique` | A technique in shader material describes the concrete rendering details. |
| `Texture` | This class defines the texture from an external file. |
| `TextureBase` | Base class for all texture types. |
| `TextureFilter` | Texture filter type. |
| `TextureSlot` | Texture slot name. |
| `WrapMode` | Wrap mode for texture coordinates. |
| `ArrayListAdapter` | Adapter class that wraps List[T] and implements IList[T] compatible interface. |
| `BoundingBox` | Defined as class BoundingBox. |
| `FVector2` | Defined as class FVector2. |
| `FVector3` | Defined as class FVector3. |
| `FVector4` | Defined as class FVector4. |
| `FileSystem` | File system encapsulation. |
| `Matrix4` | Defined as class Matrix4. |
| `Quaternion` | Defined as class Quaternion. |
| `Vector2` | Defined as class Vector2. |
| `Vector3` | Defined as class Vector3. |
| `Vector4` | Defined as class Vector4. |
| `Watermark` | Utility to encode/decode blind watermark to/from a mesh. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `ExtrapolationType` | Defined as class ExtrapolationType(Enum). |
| `Interpolation` | Defined as class Interpolation(Enum). |
| `PoseType` | Defined as class PoseType(Enum). |
| `StepMode` | Defined as class StepMode(Enum). |
| `WeightedMode` | Defined as class WeightedMode(Enum). |

#### Detailed Member Reference

### Scene

`Scene` serves as the root container for a 3D scene graph, offering `Scene.root_node` to access the top-level `Node`, `Scene.animation_clips` to manage animation data, `Scene.sub_scenes` for hierarchical organization, and `Scene.render` for exporting to supported formats.

- `animation_clips`: Defined as def animation_clips(self) -> List['AnimationClip'].
- `asset_info`: Defined as def asset_info(self) -> AssetInfo.
- `clear`: Defined as def clear(self).
- `create_animation_clip`: Defined as def create_animation_clip(self, name: str) -> 'AnimationClip'.
- `current_animation_clip`: Defined as def current_animation_clip(self) -> Optional['AnimationClip'].
- `from_file`: Defined as def from_file(file_name: str).
- `get_animation_clip`: Defined as def get_animation_clip(self, name: str) -> Optional['AnimationClip'].
- `library`: Defined as def library(self) -> List[CustomObject].
- `open`: Defined as def open(self, file_or_stream, options=None).
- `poses`: Defined as def poses(self) -> List.
- `render`: Defined as def render(self, camera, file_name_or_bitmap, size=None, format=None, options=None).
- `root_node`: Defined as def root_node(self).
- `save`: Defined as def save(self, file_or_stream, format_or_options=None).
- `sub_scenes`: Defined as def sub_scenes(self) -> List['Scene'].

### Node

`Node` represents an element in the scene hierarchy, exposing `Node.transform` for position and orientation, `Node.entities` for holding `Mesh`-derived objects, `Node.child_nodes` for tree traversal, and `Node.material` for assigning visual properties.

- `add_child_node`: Defined as def add_child_node(self, node: 'Node').
- `add_entity`: Defined as def add_entity(self, entity: 'Entity').
- `asset_info`: Defined as def asset_info(self).
- `child_nodes`: Defined as def child_nodes(self) -> List['Node'].
- `create_child_node`: Defined as def create_child_node(self, node_name: Optional[str]=None, entity=None, material=None) -> 'Node'.
- `entities`: Defined as def entities(self) -> List['Entity'].
- `entity`: Defined as def entity(self) -> Optional['Entity'].
- `evaluate_global_transform`: Defined as def evaluate_global_transform(self, with_geometric_transform: bool) -> Matrix4.
- `excluded`: Defined as def excluded(self) -> bool.
- `get_bounding_box`: Defined as def get_bounding_box(self) -> BoundingBox.
- `get_child`: Defined as def get_child(self, index_or_name).
- `get_entity`: Defined as def get_entity(self, entity_type: type).
- `global_transform`: Defined as def global_transform(self) -> GlobalTransform.
- `material`: Defined as def material(self) -> Optional['Material'].
- `materials`: Defined as def materials(self) -> List['Material'].
- `merge`: Defined as def merge(self, node: 'Node').
- `meta_datas`: Defined as def meta_datas(self) -> List.
- `parent_node`: Defined as def parent_node(self) -> Optional['Node'].
- `select_objects`: Defined as def select_objects(self, path: str).
- `select_single_object`: Defined as def select_single_object(self, path: str).
- `transform`: Defined as def transform(self) -> Transform.
- `visible`: Defined as def visible(self) -> bool.

### Mesh

`Mesh` stores geometric data such as `control_points` and polygon definitions, and supports conversion from primitives via methods like `to_mesh`, enabling procedural geometry creation and manipulation.

- `control_points`: Defined as def control_points(self) -> ArrayListAdapter[Vector4].
- `create_polygon`: Defined as def create_polygon(self, *args).
- `difference`: Defined as def difference(a: 'Mesh', b: 'Mesh') -> 'Mesh'.
- `do_boolean`: Defined as def do_boolean(op: BooleanOperation, a: 'Mesh', transform_a: Optional[Matrix4], b: 'Mesh', transform_b: Optional[Matrix4]) -> 'Mesh'.
- `edges`: Defined as def edges(self) -> ArrayListAdapter[int].
- `get_bounding_box`: Defined as def get_bounding_box(self).
- `get_entity_renderer_key`: Defined as def get_entity_renderer_key(self).
- `get_polygon_size`: Defined as def get_polygon_size(self, index: int) -> int.
- `intersect`: Defined as def intersect(a: 'Mesh', b: 'Mesh') -> 'Mesh'.
- `is_manifold`: Defined as def is_manifold(self) -> bool.
- `optimize`: Defined as def optimize(self, vertex_elements: bool=False, tolerance_control_point: float=1e-09, tolerance_normal: float=1e-09, tolerance_uv: float=1e-09) -> 'Mesh'.
- `polygon_count`: Defined as def polygon_count(self) -> int.
- `polygons`: Defined as def polygons(self) -> List[List[int]].
- `to_mesh`: Defined as def to_mesh(self) -> 'Mesh'.
- `triangulate`: Defined as def triangulate(self) -> 'Mesh'.
- `union`: Defined as def union(a: 'Mesh', b: 'Mesh') -> 'Mesh'.

### shading

The shading module provides `Material` definitions for surface appearance, including properties like `diffuse_color`, `metallic_factor`, and `roughness_factor` to control rendering behavior.

### entities

The entities module includes `Primitive` classes and `PolygonBuilder` to construct geometry programmatically, supporting operations like `create_polygon` and add to build meshes from scratch.

### animation

The animation module supports keyframe-based animation through `AnimationClip`, with `Scene.current_animation_clip` and `Scene.create_animation_clip` enabling scene-level animation management.

### formats

The formats module exposes `FileFormat` instances for supported 3D formats, including `FileFormat.FBX7400ASCII`, `FileFormat.GLTF2`, `FileFormat.WAVEFRONT_OBJ`, and `FileFormat.MICROSOFT_3MF_FORMAT`, with `FileFormat.can_import` and `FileFormat.can_export` indicating format capabilities.

### utilities

The utilities module provides helper classes like `MathUtils` for common operations and supports in-memory I/O via members such as `BytesIO` and `StringIO` for streaming operations.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/3d/python/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/3d/python/)** — The how-to guides and FAQ provide task-focused answers for common 3D-processing questions.
- **[Full API reference](https://reference.aspose.org/3d/python/)** — The full API reference offers the complete, browsable reference for all 343 verified public types. It covers all 343 verified public types; the [API Reference](#api-reference) section above covers the essentials.
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
