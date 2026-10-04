## Scope and Limitations

Aspose.3D FOSS for TypeScript provides basic 3D scene loading and saving for common formats such as OBJ, GLTF, and STL, with support for reading and writing files directly through `Node`'s file system.

- The package is installed by cloning the repository and running npm install followed by npm run build, and the resulting build is not distributed via npm, so consumers must build from source.
- The `FileSystem` virtualization abstraction, including `FileSystem.readFile`, `FileSystem.writeFile`, and `FileSystem.createZipFileSystem`, is entirely unimplemented and throws errors in this FOSS build.
- Rendering, 3MF import and export, and text watermarking are not functional in this FOSS build, and `Scene.render()` throws an error when called.
- `Mesh` Boolean operations, `Mesh.optimize`, `Mesh.isManifold`, `VertexElement.setIndices`, `VertexElement.clear`, `Node.selectSingleObject`, and `Node.selectObjects` all throw errors indicating they are not implemented in this FOSS build.
- OBJ import does not assign per-face materials from the source file, and OBJ export only writes geometry attached at the top of the scene graph while omitting geometry attached via child nodes.
- Binary GLB export fails for non-empty meshes, and re-importing a scene exported to glTF can produce extra duplicate top-level nodes not present in the original.

These limitations don't apply to [Aspose.3D — Enterprise Edition](https://products.aspose.com/3d/). Aspose.3D FOSS for TypeScript provides open-source access to core 3D file format capabilities; the commercial Aspose.3D commercial edition extends this with additional formats, advanced rendering, and cloud-based processing features.

## Development and Testing
