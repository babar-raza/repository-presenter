# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/) ![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

[![Aspose.3D FOSS for Python](https://products.aspose.org/media/3d/python/banner-readme.png)](https://products.aspose.org/3d/python/)

Aspose.3D FOSS for Python is a pure-Python, MIT-licensed library for loading, constructing, and exporting 3D scenes. It reads and writes OBJ, STL, glTF/GLB, COLLADA, and 3MF files, plus imports FBX, through a `Scene`, `Node`, and `Mesh` object graph, with no native runtime or external SDK to install. Developers use it to build 3D content programmatically, for example by creating primitives like `Box` or `Sphere`, assigning materials, and saving to formats such as `.gltf` or `.stl`. The library supports Python versions 3.7 through 3.12 and requires Python >=3.7.

## Navigation

- [At a Glance](#at-a-glance)
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

## At a Glance

```mermaid
flowchart TD
  PRODUCT["Aspose.3D FOSS for Python"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Load multiple 3D formats"]
      c2["Export to common 3D formats"]
      c3["Construct and manipulate meshes"]
      c4["Assign materials to geometry"]
    end
    subgraph capr[" "]
      direction TB
      c5["Build and traverse scene graphs"]
      c6["Triangulate arbitrary polygons"]
      c7["Create keyframe animations"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["glTF or STL file"]
  end
  PRODUCT --> Capabilities --> Outputs
```

## Key Capabilities

- **Load multiple 3D formats.** Create and save 3D scenes to multiple formats including `.gltf` and `.stl` using the `FileFormat` class, which supports format detection, extension mapping, and save options configuration.
- **Export to common 3D formats.** Export scenes to `.gltf` and `.stl` formats by leveraging `FileFormat.get_format_by_extension` and its `create_save_options` method to configure binary or ASCII output modes.
- **Construct and manipulate meshes.** Construct and manipulate `Mesh` objects by adding control points and creating polygons, then inspect properties such as control point count, polygon count, and bounding boxes.
- **Assign materials to geometry.** Apply shading materials like `LambertMaterial` and `PbrMaterial` to 3D entities, setting properties such as `diffuse_color`, `metallic_factor`, and `roughness_factor` for realistic rendering.
- **Build and traverse scene graphs.** Organize scene hierarchy using `Node` objects, attach entities and materials, and compute global transforms and bounding boxes for rendering and spatial queries.
- **Triangulate arbitrary polygons.** Build polygonal geometry programmatically using the `PolygonBuilder` class to define vertices and faces for custom 3D shapes.
- **Create keyframe animations.** Define animation sequences using `AnimationClip`, `AnimationNode`, `KeyframeSequence`, and `Pose` objects to describe time-based transformations and skeletal poses.

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

Open an existing 3D file by passing its path and optional load options to the `Scene.open` method, then inspect its contents through the `root_node` and `child_nodes` hierarchy.

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

The following examples demonstrate creating geometry, applying materials, and saving scenes to various formats using Aspose.3D FOSS for Python.

### Build a triangle mesh with PBR material and export to GLTF text format

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

<details>
<summary>View Additional Examples</summary>

### Create a sphere with PBR material and save it as STL

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

### Generate a triangle mesh and save it as ASCII STL using a `StringIO` stream

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

### Construct a box and inspect its control point count

```python
from aspose.threed.entities import Box

box = Box(10, 20, 30)
mesh = box.to_mesh()
print(f"Control points: {len(mesh.control_points)}")
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

</details>

## API Reference

The aspose-3d-foss package exposes `aspose.threed.Scene` as the primary entry point for loading and saving 3D scenes, and `aspose.threed.Node` as the fundamental building block for constructing scene hierarchies.

The verified public surface has 343 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `A3DObject` | A3DObject represents a base object in the scene hierarchy that supports named properties and can be queried for its properties. |
| `AnimationChannel` | AnimationChannel represents a single animated property channel with a keyframe sequence and a default value. |
| `AnimationClip` | AnimationClip represents a container for animation data with a start and stop time, a description, and a collection of animation nodes. |
| `AnimationNode` | AnimationNode represents a node in the animation hierarchy that can hold bind points and sub-animations. |
| `threed.ArrayListAdapter` | Adapter class that wraps List[T] and implements IArrayList[T]. |
| `AssetInfo` | AssetInfo holds metadata about the 3D asset such as author, creation time, coordinate system, and unit scale factor. |
| `Axis` | The coordinate axis. |
| `AxisSystem` | Axis system is an combination of coordinate system, up vector and front vector. |
| `BindPoint` | BindPoint represents a binding location for animation channels in a bone or joint hierarchy. |
| `BonePose` | BonePose represents the transformation matrix and local flag for a bone at a specific pose. |
| `BoundingBox2D` | The axis-aligned bounding box for Vector2 |
| `BoundingBoxExtent` | The extent of the bounding box |
| `Box` | Box represents a box primitive with configurable length, height, and segment counts. |
| `Camera` | Camera represents a camera entity that defines a view frustum for rendering. |
| `Circle` | Circle represents a circular primitive defined in 3D space. |
| `ComposeOrder` | The order to compose transform matrix |
| `CoordinateSystem` | The left handed or right handed coordinate system. |
| `Curve` | Curve represents a parametric curve entity in 3D space. |
| `CustomObject` | CustomObject represents a user-defined object that extends the base A3DObject functionality. |
| `Cylinder` | Cylinder represents a cylindrical primitive with configurable height and segment counts. |
| `Dish` | Dish represents a dish-shaped primitive with configurable radial and angular segments. |
| `Ellipse` | Ellipse represents an elliptical primitive in 3D space. |
| `Entity` | Entity represents a renderable or manipulable object in the scene that can be assigned to a node. |
| `ExportException` | Exceptions when Aspose.3D failed to export the scene to file. |
| `Extrapolation` | Extrapolation defines how animation values are computed beyond the keyframe range. |
| `FMatrix4` | Matrix 4x4 with all component in float type |
| `FileContentType` | File content type |
| `FileFormat` | FileFormat provides utilities for identifying and working with supported 3D file formats. |
| `FileFormatType` | File format type |
| `Frustum` | Frustum represents a truncated pyramid primitive used for defining camera view volumes. |
| `Geometry` | Geometry represents a geometric entity that can be used to define the shape of a renderable object. |
| `GlobalTransform` | GlobalTransform represents a transformation matrix applied to an object in world space. |
| `Group` | A Group represents the logical relationships of Node. |
| `INamedObject` | INamedObject is an interface for objects that can be identified by a name. |
| `IOExtension` | Utilities to write matrix/vector to binary writer |
| `ImageRenderOptions` | ImageRenderOptions controls how a scene is rendered to an image, including compression and material settings. |
| `ImportException` | Exception when Aspose.3D failed to open the specified source. |
| `KeyFrame` | KeyFrame represents a single keyframe with a time and value for animation interpolation. |
| `KeyframeSequence` | KeyframeSequence represents a sequence of keyframes used to animate a property over time. |
| `Light` | Light represents a light source entity that can be attached to a node in the scene. |
| `LinearExtrusion` | LinearExtrusion represents a 3D shape created by extruding a 2D profile along a straight path. |
| `MathUtils` | A set of useful mathematical utilities. |
| `Mesh` | Mesh represents a polygonal mesh geometry composed of vertices and polygons. |
| `Node` | Node represents a transformable object in the scene hierarchy that can hold an entity and child nodes. |
| `ParseException` | Exception when Aspose.3D failed to parse the input. |
| `Plane` | Plane represents a planar primitive defined by size and segment counts. |
| `PolygonBuilder` | PolygonBuilder provides utilities for constructing polygonal meshes programmatically. |
| `Pose` | Pose represents a collection of bone poses used for skeletal animation. |
| `Primitive` | Primitive represents a basic geometric shape such as a box, cylinder, or sphere. |
| `Property` | Property represents a single named value that can be attached to an object. |
| `PropertyCollection` | PropertyCollection represents a collection of properties associated with an object. |
| `PropertyFlags` | Property's flags |
| `Rect` | A class to represent the rectangle |
| `RelativeRectangle` | Relative rectangle |
| `RotationOrder` | The order controls which rx ry rz are applied in the transformation matrix. |
| `Scene` | Scene represents a complete 3D scene containing nodes, entities, and animation data. |
| `SceneObject` | SceneObject represents an object that belongs to a scene and can be part of the scene hierarchy. |
| `SemanticAttribute` | Allow user to use their own structure for static declaration of VertexDeclaration |
| `Sphere` | The Sphere class represents a sphere primitive in Aspose.3D FOSS for Python. |
| `Transform` | The Transform class represents transformation properties such as translation, rotation, and scaling for 3D objects in Aspose.3D FOSS for Python. |
| `TransformBuilder` | The TransformBuilder is used to build transform matrix by a chain of transformations. |
| `TrialException` | This is raised in Scene.Open/Scene.Save when no licenses are applied. |
| `Vertex` | Vertex reference, used to access the raw vertex in TriMesh. |
| `VertexDeclaration` | The declaration of a custom defined vertex's structure |
| `VertexField` | Vertex's field memory layout description. |
| `VertexFieldDataType` | Vertex field's data type |
| `VertexFieldSemantic` | The semantic of the vertex field |
| `Bone` | The Bone class represents a bone used in skeletal animation within Aspose.3D FOSS for Python. |
| `BoneLinkMode` | The BoneLinkMode class defines enumeration values for bone linking modes in Aspose.3D FOSS for Python. |
| `Deformer` | The Deformer class serves as a base class for mesh deformation operations in Aspose.3D FOSS for Python. |
| `MorphTargetChannel` | The MorphTargetChannel class manages weights and targets for morph target animation in Aspose.3D FOSS for Python. |
| `MorphTargetDeformer` | The MorphTargetDeformer class applies morph target deformations to 3D geometry in Aspose.3D FOSS for Python. |
| `SkinDeformer` | The SkinDeformer class applies skinning deformation using bone influences in Aspose.3D FOSS for Python. |
| `ApertureMode` | Camera aperture modes. |
| `BooleanOperand` | This class encapsulates the transformed mesh as Boolean operation's operand. |
| `BooleanOperation` | The BooleanOperation class represents boolean operations such as union, intersection, and difference in Aspose.3D FOSS for Python. |
| `BooleanOperator` | Boolean operator allows you to apply Boolean operation on two IMeshConvertible instances. |
| `CompositeCurve` | A CompositeCurve is consisting of several curve segments. |
| `CurveDimension` | The CurveDimension class defines the dimensionality of curves in Aspose.3D FOSS for Python. |
| `EndPoint` | The end point to trim the curve, can be a parameter value or a Cartesian point. |
| `HalfSpace` | HalfSpace represents a infinity space which is split by a plane, this can be used with BooleanOperator |
| `IIndexedVertexElement` | The IIndexedVertexElement class provides an interface for indexed vertex elements in Aspose.3D FOSS for Python. |
| `IMeshConvertible` | Entities that implemented this interface can be converted to Mesh |
| `IOrientable` | Orientable entities shall implement this interface. |
| `LightType` | Light types. |
| `Line` | A polyline is a path defined by a set of points with control_points, and connected by segments. |
| `MappingMode` | The MappingMode class defines enumeration values for texture mapping modes in Aspose.3D FOSS for Python. |
| `NurbsCurve` | The NurbsCurve class represents a NURBS curve geometry in Aspose.3D FOSS for Python. |
| `NurbsDirection` | The NurbsDirection class defines properties for a NURBS direction in Aspose.3D FOSS for Python. |
| `NurbsSurface` | The NurbsSurface class represents a NURBS surface geometry in Aspose.3D FOSS for Python. |
| `NurbsType` | The NurbsType class defines enumeration values for NURBS types in Aspose.3D FOSS for Python. |
| `Patch` | The Patch class represents a patch geometry in Aspose.3D FOSS for Python. |
| `PatchDirection` | The PatchDirection class defines properties for patch directions in Aspose.3D FOSS for Python. |
| `PatchDirectionType` | The PatchDirectionType class defines enumeration values for patch direction types in Aspose.3D FOSS for Python. |
| `PointCloud` | The PointCloud class represents a collection of 3D points in Aspose.3D FOSS for Python. |
| `InvalidOperationException` | The InvalidOperationException class is raised when an invalid operation is performed during polygon building in Aspose.3D FOSS for Python. |
| `PolygonModifier` | The PolygonModifier class provides utilities for modifying polygonal meshes in Aspose.3D FOSS for Python. |
| `ProjectionType` | Camera's projection types. |
| `Pyramid` | Parameterized pyramid. |
| `RectangularTorus` | Parameterized rectangular torus entity. |
| `ReferenceMode` | The ReferenceMode class defines enumeration values for reference modes in Aspose.3D FOSS for Python. |
| `RevolvedAreaSolid` | RevolvedAreaSolid entity. |
| `RotationMode` | The frustum's rotation mode. |
| `Shape` | Base class for all shape entities. |
| `Skeleton` | The Skeleton is mainly used by CAD software to help designer to manipulate the transformation of skeletal structure, it's usually useless outside the CAD softwares. |
| `SkeletonType` | Skeleton type enum. |
| `SplitMeshPolicy` | Share vertex/control point data between sub-meshes or each sub-mesh has its own compacted data. |
| `SweptAreaSolid` | SweptAreaSolid entity. |
| `TextureMapping` | The TextureMapping class defines texture mapping configurations in Aspose.3D FOSS for Python. |
| `Torus` | Parameterized torus entity. |
| `TransformedCurve` | TransformedCurve entity. |
| `TriMesh` | TriMesh is a triangle mesh that stores triangles. |
| `TrimmedCurve` | TrimmedCurve entity. |
| `VertexElement` | The VertexElement class represents a generic vertex element in Aspose.3D FOSS for Python. |
| `VertexElementBinormal` | The VertexElementBinormal class represents binormal data for vertices in Aspose.3D FOSS for Python. |
| `VertexElementDoublesTemplate` | A helper class for defining concrete implementations. |
| `VertexElementEdgeCrease` | Defines the edge crease values for specified components. |
| `VertexElementFVector` | The VertexElementFVector class represents floating-point vector vertex data in Aspose.3D FOSS for Python. |
| `VertexElementHole` | Defines the hole information for specified components. |
| `VertexElementIntsTemplate` | A helper class for defining concrete implementations with int data. |
| `VertexElementMaterial` | Defines the material for specified components. |
| `VertexElementNormal` | The VertexElementNormal class represents normal vectors for vertices in Aspose.3D FOSS for Python. |
| `VertexElementPolygonGroup` | Defines the polygon group for specified components. |
| `VertexElementSmoothingGroup` | The VertexElementSmoothingGroup class represents smoothing group data for vertices in Aspose.3D FOSS for Python. |
| `VertexElementSpecular` | Defines the specular color for specified components. |
| `VertexElementTangent` | The VertexElementTangent class represents tangent vectors for vertices in Aspose.3D FOSS for Python. |
| `VertexElementTemplate` | A helper class for defining concrete implementations of vertex elements with typed data. |
| `VertexElementType` | The VertexElementType class defines enumeration values for vertex element types in Aspose.3D FOSS for Python. |
| `VertexElementUV` | The VertexElementUV class represents UV texture coordinate data for vertices in Aspose.3D FOSS for Python. |
| `VertexElementUserData` | Defines the user data for specified components. |
| `VertexElementVector4` | Defines the vector4 data for specified components. |
| `VertexElementVertexColor` | The VertexElementVertexColor class represents vertex color data in Aspose.3D FOSS for Python. |
| `VertexElementVertexCrease` | Defines the vertex crease values for specified components. |
| `VertexElementVisibility` | Defines the visibility for specified components. |
| `VertexElementWeight` | Defines the weight for specified components. |
| `A3dwSaveOptions` | Save options for A3DW |
| `AmfSaveOptions` | Save options for AMF |
| `BasicLoadOptions` | Simple LoadOptions subclass for basic loading options. |
| `formats.ColladaLoadOptions` | The ColladaLoadOptions class specifies options for loading COLLADA files in Aspose.3D FOSS for Python. |
| `ColladaLoadOptions.ColladaLoadOptions` | Load options for Collada |
| `formats.ColladaSaveOptions` | The ColladaSaveOptions class specifies options for saving COLLADA files in Aspose.3D FOSS for Python. |
| `ColladaSaveOptions.ColladaSaveOptions` | Save options for collada |
| `formats.ColladaTransformStyle` | The node's transformation style of node |
| `Discreet3dsLoadOptions` | Load options for Discreet 3DS |
| `Discreet3dsSaveOptions` | Save options for Discreet 3DS |
| `DracoCompressionLevel` | Compression level for draco file |
| `DracoFormat` | Google Draco format |
| `DracoSaveOptions` | Save options for Draco |
| `Exporter` | The Exporter class provides functionality to export 3D scenes to various formats in Aspose.3D FOSS for Python. |
| `formats.FbxLoadOptions` | The FbxLoadOptions class specifies options for loading FBX files in Aspose.3D FOSS for Python. |
| `FbxLoadOptions.FbxLoadOptions` | Load options for FBX |
| `formats.FbxSaveOptions` | The FbxSaveOptions class specifies options for saving FBX files in Aspose.3D FOSS for Python. |
| `FbxSaveOptions.FbxSaveOptions` | Save options for FBX |
| `FormatDetector` | The FormatDetector class provides functionality to detect the file format of a 3D scene file. |
| `GltfEmbeddedImageFormat` | Embedded image format for GLTF |
| `formats.GltfLoadOptions` | The GltfLoadOptions class allows configuration of options when loading glTF files, including flipping the V coordinate of texture coordinates. |
| `GltfLoadOptions.GltfLoadOptions` | Load options for glTF |
| `formats.GltfSaveOptions` | The GltfSaveOptions class allows configuration of options when saving to glTF formats, including binary mode and flipping the V coordinate of texture coordinates. |
| `GltfSaveOptions.GltfSaveOptions` | Save options for glTF |
| `Html5SaveOptions` | Save options for HTML5 |
| `IOConfig` | The IOConfig class provides common configuration properties for input and output operations, such as file name, encoding, file system, and lookup paths. |
| `IOService` | The IOService class provides services for importing, exporting, and detecting 3D file formats, including plugin registration and format detection. |
| `Importer` | The Importer class provides methods to import 3D scenes from supported file formats. |
| `JtLoadOptions` | Load options for JT |
| `LoadOptions` | The LoadOptions class serves as a base class for format-specific options used when loading 3D files. |
| `Microsoft3MFFormat` | Microsoft 3MF format |
| `Microsoft3MFSaveOptions` | Save options for Microsoft 3MF |
| `formats.ObjLoadOptions` | The ObjLoadOptions class allows configuration of options when loading OBJ files, including enabling materials, flipping the coordinate system, normalizing normals, and scaling. |
| `ObjLoadOptions.ObjLoadOptions` | Load options for OBJ |
| `formats.ObjSaveOptions` | The ObjSaveOptions class allows configuration of options when saving to OBJ files, including applying unit scale, setting the axis system, enabling materials, flipping the coordinate system, exporting as a point cloud, serializing the w component, and verbose output. |
| `ObjSaveOptions.ObjSaveOptions` | Save options for OBJ |
| `PdfFormat` | Adobe's Portable Document Format |
| `PdfLightingScheme` | Lighting scheme for PDF export |
| `PdfLoadOptions` | Load options for PDF |
| `PdfRenderMode` | Render mode for PDF export |
| `PdfSaveOptions` | Save options for PDF |
| `Plugin` | The Plugin class serves as a base for plugins that provide support for specific 3D file formats, including importers, exporters, and format detectors. |
| `PlyFormat` | PLY format |
| `PlyLoadOptions` | Load options for PLY |
| `PlySaveOptions` | Save options for PLY |
| `RvmFormat` | RVM format |
| `RvmLoadOptions` | Load options for RVM |
| `RvmSaveOptions` | Save options for RVM |
| `SaveOptions` | The SaveOptions class serves as a base class for format-specific options used when saving 3D files, including exporting textures. |
| `formats.StlLoadOptions` | The StlLoadOptions class allows configuration of options when loading STL files, including flipping the coordinate system and scaling. |
| `StlLoadOptions.StlLoadOptions` | Load options for STL |
| `formats.StlSaveOptions` | The StlSaveOptions class allows configuration of options when saving to STL files, including binary mode, flipping the coordinate system, and scaling. |
| `StlSaveOptions.StlSaveOptions` | Save options for STL |
| `ThreeMfFormat` | The ThreeMfFormat class represents the 3MF file format and provides methods to check import and export support, get format metadata, and manage buildable objects. |
| `ThreeMfLoadOptions` | The ThreeMfLoadOptions class allows configuration of options when loading 3MF files. |
| `ThreeMfSaveOptions` | The ThreeMfSaveOptions class allows configuration of options when saving to 3MF files. |
| `U3dLoadOptions` | Load options for U3D |
| `U3dSaveOptions` | Save options for U3D |
| `UsdSaveOptions` | Save options for USD |
| `XLoadOptions` | Load options for X format |
| `ColladaExporter` | The ColladaExporter class provides functionality to export scenes to the COLLADA format. |
| `ColladaFormat` | The ColladaFormat class represents the COLLADA file format and provides format-specific metadata and capabilities. |
| `ColladaFormatDetector` | The ColladaFormatDetector class provides functionality to detect COLLADA files. |
| `ColladaImporter` | The ColladaImporter class provides functionality to import scenes from the COLLADA format. |
| `ColladaPlugin` | The ColladaPlugin class provides plugin support for the COLLADA format, including importers, exporters, and format detectors. |
| `ColladaTransformStyle.ColladaTransformStyle` | The ColladaTransformStyle class defines how transformations are handled when importing or exporting COLLADA files. |
| `FbxExporter` | The FbxExporter class provides functionality to export scenes to the FBX format. |
| `FbxFormat` | The FbxFormat class represents the FBX file format and provides format-specific metadata and capabilities. |
| `FbxFormatDetector` | The FbxFormatDetector class provides functionality to detect FBX files. |
| `FbxImporter` | The FbxImporter class provides functionality to import scenes from the FBX format. |
| `FbxPlugin` | The FbxPlugin class provides plugin support for the FBX format, including importers, exporters, and format detectors. |
| `BinaryTokenizer` | The BinaryTokenizer class provides tokenization support for parsing binary FBX files. |
| `binary_tokenizer.Token` | The Token class represents a single token in the binary FBX tokenizer. |
| `binary_tokenizer.TokenType` | The TokenType class defines the types of tokens used in the binary FBX tokenizer. |
| `FbxElement` | The FbxElement class represents a parsed element in the FBX file structure. |
| `FbxParser` | The FbxParser class provides functionality to parse FBX files. |
| `FbxScope` | The FbxScope class represents a scope in the FBX file structure during parsing. |
| `FbxTokenizer` | The FbxTokenizer class provides tokenization support for parsing text-based FBX files. |
| `tokenizer.Token` | The Token class represents a single token in the text-based FBX tokenizer. |
| `tokenizer.TokenType` | The TokenType class defines the types of tokens used in the text-based FBX tokenizer. |
| `GltfExporter` | The GltfExporter class provides functionality to export scenes to the glTF format. |
| `GltfFormat` | The GltfFormat class represents the glTF file format and provides format-specific metadata and capabilities. |
| `GltfFormatDetector` | The GltfFormatDetector class provides functionality to detect glTF files. |
| `GltfImporter` | The GltfImporter class provides functionality to import scenes from the glTF format. |
| `GltfPlugin` | GltfPlugin provides support for the GL Transmission Format, enabling import and export of GLTF files through its exporter, importer, and format detector components. |
| `ObjExporter` | ObjExporter converts 3D scenes into the OBJ format by writing geometry and material data to text-based files. |
| `ObjFormat` | ObjFormat represents the OBJ file format, supporting import and export operations with associated metadata such as extensions and content type. |
| `ObjFormatDetector` | ObjFormatDetector identifies OBJ files by inspecting file content to determine format compatibility. |
| `ObjImporter` | ObjImporter reads OBJ files and constructs a 3D scene from their geometry and material definitions. |
| `ObjPlugin` | ObjPlugin serves as the main entry point for handling OBJ files, exposing exporter, importer, format detector, and format metadata. |
| `StlExporter` | StlExporter writes 3D scenes to STL files, supporting both ASCII and binary representations of polygonal meshes. |
| `StlFormat` | StlFormat encapsulates the STL file format, providing metadata and operations for importing and exporting stereolithography files. |
| `StlFormatDetector` | StlFormatDetector determines whether a file is an STL format by analyzing its content structure. |
| `StlImporter` | StlImporter loads STL files into a 3D scene, parsing either ASCII or binary encoded mesh data. |
| `StlPlugin` | StlPlugin acts as the central interface for STL format operations, offering access to exporters, importers, format detectors, and format metadata. |
| `ThreeMfExporter` | ThreeMfExporter exports 3D scenes to the 3MF format, preserving geometry, materials, and scene hierarchy. |
| `ThreeMfFormatDetector` | ThreeMfFormatDetector detects 3MF files by examining their internal structure and content. |
| `ThreeMfImporter` | ThreeMfImporter imports 3MF files into a 3D scene, reconstructing geometry, materials, and scene nodes. |
| `ThreeMfPlugin` | ThreeMfPlugin provides the primary interface for 3MF format support, including exporter, importer, format detector, and format metadata. |
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
| `LambertMaterial` | LambertMaterial defines a non-shiny material model using ambient and diffuse color properties for rendering. |
| `Material` | Material serves as the base class for all material types, providing core shading properties and behavior. |
| `PbrMaterial` | PbrMaterial implements physically based rendering using metallic and roughness factors to simulate realistic surface appearance. |
| `PbrSpecularMaterial` | Material for physically based rendering based on diffuse color/specular/glossiness. |
| `PhongMaterial` | PhongMaterial extends LambertMaterial by adding specular highlights for shiny surface rendering. |
| `ShaderMaterial` | A shader material allows to describe the material by external rendering engine or shader language. |
| `ShaderTechnique` | A technique in shader material describes the concrete rendering details. |
| `Texture` | This class defines the texture from an external file. |
| `TextureBase` | Base class for all texture types. |
| `TextureFilter` | Texture filter type. |
| `TextureSlot` | Texture slot name. |
| `WrapMode` | Wrap mode for texture coordinates. |
| `ArrayListAdapter.ArrayListAdapter` | Adapter class that wraps List[T] and implements IList[T] compatible interface. |
| `BoundingBox` | BoundingBox represents an axis-aligned bounding box used to describe the spatial extent of 3D geometry. |
| `FVector2` | FVector2 stores a pair of single-precision floating-point coordinates for 2D vector operations. |
| `FVector3` | FVector3 stores a triplet of single-precision floating-point values representing a 3D vector or point. |
| `FVector4` | FVector4 stores a quadruplet of single-precision floating-point values, commonly used for homogeneous coordinates or quaternions. |
| `FileSystem` | File system encapsulation. |
| `Matrix4` | Matrix4 represents a 4x4 transformation matrix used for 3D geometry operations such as translation, rotation, and scaling. |
| `Quaternion` | Quaternion provides a mathematical representation for 3D rotations, avoiding gimbal lock and enabling smooth interpolation. |
| `Vector2` | Vector2 stores a pair of double-precision floating-point coordinates for 2D vector operations. |
| `Vector3` | Vector3 stores a triplet of double-precision floating-point values representing a 3D vector or point. |
| `Vector4` | Vector4 stores a quadruplet of double-precision floating-point values, commonly used for homogeneous coordinates or quaternions. |
| `Watermark` | Utility to encode/decode blind watermark to/from a mesh. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `ExtrapolationType` | ExtrapolationType enumerates the possible strategies for extrapolating animation values. |
| `Interpolation` | Interpolation enumerates the methods used to compute values between keyframes. |
| `PoseType` | PoseType enumerates the categories of poses used in skeletal animation. |
| `StepMode` | The StepMode class defines enumeration values for step mode settings in Aspose.3D FOSS for Python. |
| `WeightedMode` | The WeightedMode class defines enumeration values for weighted mode settings in Aspose.3D FOSS for Python. |

#### Detailed Member Reference

### Scene

The `aspose.threed.Scene` class provides methods such as `Scene.open`, `Scene.from_file`, `Scene.save`, `Scene.render`, `Scene.create_animation_clip`, `Scene.get_animation_clip`, `Scene.clear`, `Scene.sub_scenes`, `Scene.root_node`, `Scene.library`, `Scene.asset_info`, `Scene.poses`, and `Scene.current_animation_clip` to manage 3D content.

- `animation_clips`: Defined as `def animation_clips(self) -> List['AnimationClip']`.
- `asset_info`: Defined as `def asset_info(self) -> AssetInfo`.
- `clear`: Defined as `def clear(self)`.
- `create_animation_clip`: Defined as `def create_animation_clip(self, name: str) -> 'AnimationClip'`.
- `current_animation_clip`: Defined as `def current_animation_clip(self) -> Optional['AnimationClip']`.
- `from_file`: Defined as `def from_file(file_name: str)`.
- `get_animation_clip`: Defined as `def get_animation_clip(self, name: str) -> Optional['AnimationClip']`.
- `library`: Defined as `def library(self) -> List[CustomObject]`.
- `open`: Defined as `def open(self, file_or_stream, options=None)`.
- `poses`: Defined as `def poses(self) -> List`.
- `render`: Defined as `def render(self, camera, file_name_or_bitmap, size=None, format=None, options=None)`.
- `root_node`: Defined as `def root_node(self)`.
- `save`: Defined as `def save(self, file_or_stream, format_or_options=None)`.
- `sub_scenes`: Defined as `def sub_scenes(self) -> List['Scene']`.

### Node

The `aspose.threed.Node` class represents nodes in the scene graph and supports operations like `Node.add_child_node`, `Node.create_child_node`, `Node.add_entity`, `Node.entity`, `Node.get_entity`, `Node.child_nodes`, `Node.parent_node`, `Node.transform`, `Node.global_transform`, `Node.material`, `Node.materials`, `Node.get_bounding_box`, `Node.excluded`, `Node.visible`, `Node.meta_datas`, `Node.select_objects`, `Node.select_single_object`, and `Node.merge`.

- `add_child_node`: Defined as `def add_child_node(self, node: 'Node')`.
- `add_entity`: Defined as `def add_entity(self, entity: 'Entity')`.
- `asset_info`: Defined as `def asset_info(self)`.
- `child_nodes`: Defined as `def child_nodes(self) -> List['Node']`.
- `create_child_node`: Defined as `def create_child_node(self, node_name: Optional[str]=None, entity=None, material=None) -> 'Node'`.
- `entities`: Defined as `def entities(self) -> List['Entity']`.
- `entity`: Defined as `def entity(self) -> Optional['Entity']`.
- `evaluate_global_transform`: Defined as `def evaluate_global_transform(self, with_geometric_transform: bool) -> Matrix4`.
- `excluded`: Defined as `def excluded(self) -> bool`.
- `get_bounding_box`: Defined as `def get_bounding_box(self) -> BoundingBox`.
- `get_child`: Defined as `def get_child(self, index_or_name)`.
- `get_entity`: Defined as `def get_entity(self, entity_type: type)`.
- `global_transform`: Defined as `def global_transform(self) -> GlobalTransform`.
- `material`: Defined as `def material(self) -> Optional['Material']`.
- `materials`: Defined as `def materials(self) -> List['Material']`.
- `merge`: Defined as `def merge(self, node: 'Node')`.
- `meta_datas`: Defined as `def meta_datas(self) -> List`.
- `parent_node`: Defined as `def parent_node(self) -> Optional['Node']`.
- `select_objects`: Defined as `def select_objects(self, path: str)`.
- `select_single_object`: Defined as `def select_single_object(self, path: str)`.
- `transform`: Defined as `def transform(self) -> Transform`.
- `visible`: Defined as `def visible(self) -> bool`.

### Mesh

The `aspose.threed.Mesh` class exposes mesh geometry through properties such as `Mesh.control_points`, `Mesh.polygons`, `Mesh.polygon_count`, `Mesh.edges`, `Mesh.get_bounding_box`, `Mesh.get_polygon_size`, `Mesh.is_manifold`, `Mesh.to_mesh`, `Mesh.triangulate`, `Mesh.union`, `Mesh.intersect`, `Mesh.difference`, `Mesh.do_boolean`, `Mesh.optimize`, `Mesh.get_entity_renderer_key`, and `Mesh.create_polygon`.

- `control_points`: Defined as `def control_points(self) -> ArrayListAdapter[Vector4]`.
- `create_polygon`: Defined as `def create_polygon(self, *args)`.
- `difference`: Defined as `def difference(a: 'Mesh', b: 'Mesh') -> 'Mesh'`.
- `do_boolean`: Defined as `def do_boolean(op: BooleanOperation, a: 'Mesh', transform_a: Optional[Matrix4], b: 'Mesh', transform_b: Optional[Matrix4]) -> 'Mesh'`.
- `edges`: Defined as `def edges(self) -> ArrayListAdapter[int]`.
- `get_bounding_box`: Defined as `def get_bounding_box(self)`.
- `get_entity_renderer_key`: Defined as `def get_entity_renderer_key(self)`.
- `get_polygon_size`: Defined as `def get_polygon_size(self, index: int) -> int`.
- `intersect`: Defined as `def intersect(a: 'Mesh', b: 'Mesh') -> 'Mesh'`.
- `is_manifold`: Defined as `def is_manifold(self) -> bool`.
- `optimize`: Defined as `def optimize(self, vertex_elements: bool=False, tolerance_control_point: float=1e-09, tolerance_normal: float=1e-09, tolerance_uv: float=1e-09) -> 'Mesh'`.
- `polygon_count`: Defined as `def polygon_count(self) -> int`.
- `polygons`: Defined as `def polygons(self) -> List[List[int]]`.
- `to_mesh`: Defined as `def to_mesh(self) -> 'Mesh'`.
- `triangulate`: Defined as `def triangulate(self) -> 'Mesh'`.
- `union`: Defined as `def union(a: 'Mesh', b: 'Mesh') -> 'Mesh'`.

### FileFormat

The `aspose.threed.FileFormat` class provides format constants like `FileFormat.FBX7400ASCII`, `FileFormat.GLTF2`, `FileFormat.MICROSOFT_3MF_FORMAT`, and `FileFormat.WAVEFRONT_OBJ`, and methods such as `FileFormat.can_import`, `FileFormat.can_export`, `FileFormat.content_type`, `FileFormat.get_format_by_extension`, `FileFormat.create_load_options`, and `FileFormat.create_save_options`.

- `FBX7400ASCII`: Defined as `def FBX7400ASCII()`.
- `GLTF2`: Defined as `def GLTF2()`.
- `MICROSOFT_3MF_FORMAT`: Defined as `def MICROSOFT_3MF_FORMAT()`.
- `WAVEFRONT_OBJ`: Defined as `def WAVEFRONT_OBJ()`.
- `can_export`: Defined as `def can_export(self) -> bool`.
- `can_import`: Defined as `def can_import(self) -> bool`.
- `content_type`: Defined as `def content_type(self) -> str`.
- `create_load_options`: Defined as `def create_load_options(self) -> 'LoadOptions'`.
- `create_save_options`: Defined as `def create_save_options(self) -> 'SaveOptions'`.
- `detect`: Defined as `def detect(stream: 'io._IOBase'=None, file_name: Optional[str]=None) -> Optional['FileFormat']`.
- `extension`: Defined as `def extension(self) -> str`.
- `extensions`: Defined as `def extensions(self) -> List[str]`.
- `file_format_type`: Defined as `def file_format_type(self)`.
- `formats`: Defined as `def formats(self) -> List['FileFormat']`.
- `get_format_by_extension`: Defined as `def get_format_by_extension(extension_name: str) -> Optional['FileFormat']`.
- `version`: Defined as `def version(self) -> str`.

### shading

The `aspose.threed.shading` module supports material definitions and rendering properties including member `diffuse_color`, member `metallic_factor`, and member `roughness_factor`.

### entities

The `aspose.threed.entities` module provides geometric primitives and utilities such as member entity and member add.

### AnimationClip

The `aspose.threed.AnimationClip` class manages animation data and supports member decode, member read, member seek, and member getvalue.

- `animations`: Defined as `def animations(self) -> List['AnimationNode']`.
- `create_animation_node`: Defined as `def create_animation_node(self, node_name: str) -> 'AnimationNode'`.
- `description`: Defined as `def description(self) -> str`.
- `name`: Defined as `def name(self) -> str`.
- `properties`: Defined as `def properties(self)`.
- `start`: Defined as `def start(self) -> float`.
- `stop`: Defined as `def stop(self) -> float`.

### AnimationNode

The `aspose.threed.AnimationNode` class represents nodes in the animation graph and supports member `create_child_node` and member entity.

- `bind_points`: Defined as `def bind_points(self) -> List['BindPoint']`.
- `create_bind_point`: Defined as `def create_bind_point(self, obj: 'A3DObject', prop_name: str) -> 'BindPoint'`.
- `find_bind_point`: Defined as `def find_bind_point(self, target: 'A3DObject', name: str) -> 'BindPoint'`.
- `get_bind_point`: Defined as `def get_bind_point(self, target: 'A3DObject', prop_name: str, create: bool) -> 'BindPoint'`.
- `get_keyframe_sequence`: Defined as `def get_keyframe_sequence(self, target: 'A3DObject', prop_name: str, channel_name: str=None, create: bool=True) -> 'KeyframeSequence'`.
- `name`: Defined as `def name(self) -> str`.
- `properties`: Defined as `def properties(self)`.
- `sub_animations`: Defined as `def sub_animations(self) -> List['AnimationNode']`.

### KeyframeSequence

The `aspose.threed.KeyframeSequence` class stores keyframe data and supports member `binary_mode`, member `control_points`, and member `create_polygon`.

- `add`: Defined as `def add(self, time: float, value: float, interpolation: Interpolation=Interpolation.LINEAR)`.
- `bind_point`: Defined as `def bind_point(self) -> 'BindPoint'`.
- `key_frames`: Defined as `def key_frames(self) -> List['KeyFrame']`.
- `name`: Defined as `def name(self) -> str`.
- `post_behavior`: Defined as `def post_behavior(self) -> Extrapolation`.
- `pre_behavior`: Defined as `def pre_behavior(self) -> Extrapolation`.
- `properties`: Defined as `def properties(self)`.
- `reset`: Defined as `def reset(self)`.

### Pose

The `aspose.threed.Pose` class represents a pose in the scene and supports member `root_node` and member material.

- `add_bone_pose`: Defined as `def add_bone_pose(self, node: Node, matrix: Matrix4, local_matrix: bool=False)`.
- `bone_poses`: Defined as `def bone_poses(self)`.
- `pose_type`: Defined as `def pose_type(self) -> PoseType`.

### PolygonBuilder

The `aspose.threed.PolygonBuilder` class helps construct polygonal geometry and supports member `create_polygon` and member `to_mesh`.

- `add_vertex`: Defined as `def add_vertex(self, index: int)`.
- `begin`: Defined as `def begin(self)`.
- `end`: Defined as `def end(self)`.

### utilities

The `aspose.threed.utilities` module provides helper types and functions such as member `BytesIO` and member `StringIO`.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/3d/python/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/3d/python/)** — The how-to guides and FAQ provide task-focused answers for common 3D-processing questions.
- **[Full API reference](https://reference.aspose.org/3d/python/)** — The full API reference offers the complete, browsable reference for all 305 public types. It covers all 343 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- **[Implementation progress notes](docs/foss-python-progress.md)** — The implementation progress notes describe the current FOSS-edition porting status.
- **[Release process](docs/releasing.md)** — The release process documentation explains how a version of aspose-3d-foss is tagged and published to PyPI.
- **[Scene/Node/Entity/Transform](docs/IMPLEMENTATION_SUMMARY.md)** — The implementation summary records historical development details for `Scene`, `Node`, `Entity`, and `Transform`.
- **[OBJ importer](docs/OBJ_IMPORTER_IMPLEMENTATION.md)** — The OBJ importer implementation notes record historical development details for OBJ import.
- **[STL import/export](docs/STL_IMPORT_IMPLEMENTATION.md)** — The STL import implementation notes record historical development details for STL import and export.
- **[FBX parser](docs/FBX_IMPLEMENTATION_SUMMARY.md)** — The FBX implementation summary records historical development details for the FBX parser.
- **[PyPI packaging readiness](docs/PYPI_READINESS.md)** — The PyPI readiness notes record historical development details for PyPI packaging readiness.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues).

## Scope and Limitations

Aspose.3D FOSS for Python version 26.1.0 supports reading and writing OBJ, STL, glTF, and COLLADA files, and provides core scene graph and mesh manipulation capabilities for Python 3.7 through 3.12.

- No file format registers an importer or exporter for PDF, PLY, RVM, U3D, JT, AMF, HTML5, A3DW, USD, or Draco in this build — `PdfSaveOptions`, `PlyLoadOptions`, `DracoSaveOptions`, and similar option classes exist as public types, but `Scene.open`() and `Scene.save`() cannot detect or dispatch any of these extensions and raise a RuntimeError if you try, and FBX support is experimental with `FbxExporter.save`() and `save_to_stream()` raising NotImplementedError outright, while COLLADA export is not reachable through `Scene.save`() due to exporter lookup order issues.
- `Scene.render`() and the entire `aspose.threed.render` module (`Renderer`, `RenderFactory`, `Viewport`, and related classes) raise NotImplementedError, and `Texture` and `TextureBase` raise NotImplementedError on construction, so an image-backed texture cannot be created, though material color and factor properties such as `diffuse_color` and `metallic_factor` work independently of texture assignment.
- `Watermark.encode_watermark`() and `decode_watermark()` and every `TransformBuilder` method raise NotImplementedError, so build node transforms through `Transform`'s own translation, rotation, and scaling properties instead of the fluent `TransformBuilder` chain.
- `Mesh.do_boolean`(), `union()`, `difference()`, and `intersect()` raise NotImplementedError, and `NurbsCurve.evaluate`() and `evaluate_at()` and `NurbsSurface.to_mesh`() raise NotImplementedError, so Boolean/CSG mesh operations and NURBS sampling or conversion to a `Mesh` are not implemented.
- `PointCloud.from_geometry`() and `from_geometry_with_density()` raise NotImplementedError, and `AxisSystem` raises NotImplementedError on every method, including construction.
- Always import a format's load/save options class from its own format submodule, never from the shared top-level `aspose.threed.formats` package — for OBJ, STL, glTF, and COLLADA specifically, the top-level package name resolves to a broken duplicate with no working base class, which format detection silently rejects, while 3MF and FBX are unaffected.

These limitations don't apply to [Aspose.3D for Python — Enterprise Edition](https://products.aspose.com/3d/python-net/). The commercial Aspose.3D Enterprise Edition adds support for additional file formats, advanced rendering capabilities, and enterprise-grade features not available in this open-source package.

## Development and Testing

Aspose.3D FOSS for Python version 26.1.0 supports Python versions 3.7 through 3.12 and can be tested using the included test suite.

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
