import pathlib
import sys

lines = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()
want = (
    "IGeometry.cs(5,",
    "OgcEsriSrsTransformer.cs(6,",
    "IPolygon.cs(38,",
    "FileDriver.cs(346,",
    "GeoJsonDriver.cs(18,",
    "Geometries" + chr(92) + "Geometry.cs(12,",
)
seen = set()
marker = "-for-.Net" + chr(92)
for line in lines:
    if ": error CS" not in line:
        continue
    head, _, msg = line.partition(": error ")
    loc = head.split(marker, 1)[-1]
    if any(w in loc for w in want):
        code, _, text = msg.partition(": ")
        cut = text.find(" [")
        if cut != -1:
            text = text[:cut]
        key = (loc, code)
        if key in seen:
            continue
        seen.add(key)
        print(f"{loc}: error {code}: {text[:220]}")
