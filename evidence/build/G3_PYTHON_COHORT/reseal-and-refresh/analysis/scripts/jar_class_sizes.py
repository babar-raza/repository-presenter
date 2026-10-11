"""List the FileFormat loader/saver classes in a jar with their uncompressed sizes.

Usage: python -I jar_class_sizes.py <jar>
"""

import sys
import zipfile

z = zipfile.ZipFile(sys.argv[1])
for info in sorted(z.infolist(), key=lambda i: i.filename):
    name = info.filename
    if "FileFormat$" in name and any(k in name for k in ("Loader", "Saver")):
        print(f"{info.file_size:7d} bytes  {name}")
readers_writers = [
    i.filename for i in z.infolist() if "Reader" in i.filename or "Writer" in i.filename
]
print("entries with Reader/Writer in the name:", readers_writers[:10])
