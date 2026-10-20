"""A correction bundle keeps non-ASCII text exactly: an em dash in a diagram label, an accented
letter, a CJK character are the same bytes in ``README.md``, ``README.patch`` and
``corrections.json`` (an edit's span and replacement), and the gate's recomputation agrees.

Every file is written and read as UTF-8 by explicit codec, so the result does not depend on the
host's default encoding (a cp1252 console reads ``—`` as ``â€”`` only if it decodes UTF-8 bytes
with the wrong codec; the bytes on disk are right). ``PYTHONUTF8`` is cleared in the subprocess
test to prove it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.model import DIAGRAM_FIX
from support import REPO_ROOT

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
NON_ASCII = ("—", "é", "日")  # em dash, e acute, a CJK character
DIAGRAM = """flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing OBJ file"]
    i2["Nothing — authored from scratch"]
  end
  PRODUCT["Aspose.3D FOSS for Java"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Scene-graph construction and traversal"]
      c2["Café mesh authoring and editing"]
      c3["日本語 primitive geometry"]
    end
    subgraph capr[" "]
      direction TB
      c4["Lambert, Phong, and PBR material assignment"]
      c5["Polygon triangulation"]
      c6["Keyframe animation and skeletal pose data"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["OBJ, STL, or 3MF file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""
README = f"""# Aspose.3D FOSS for Java — café 日本

Opening the maintainers wrote.

## At a Glance

```mermaid
{DIAGRAM}```

## Installation

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

## Dependencies

None.

## License

MIT.
"""


def test_non_ascii_survives_the_bundle_byte_for_byte_and_the_gate_agrees(
    tmp_path: Path, make_context: Any
) -> None:
    original = README.encode("utf-8")
    ctx = make_context(README)
    result = correct(ctx)
    diagram_edits = [edit for edit in result.edits if edit.kind == DIAGRAM_FIX]
    assert diagram_edits, "the control needs a diagram edit that carries the em dash"
    assert all(mark in diagram_edits[0].original for mark in NON_ASCII)
    assert "—" in diagram_edits[0].replacement
    directory = tmp_path / "bundle"
    delta = validation_delta(ctx, result, original)
    files.write_bundle(ctx, original, result, delta, directory)

    readme = (directory / files.README_NAME).read_bytes()
    assert readme == result.corrected.encode("utf-8")
    assert (directory / files.ORIGINAL_NAME).read_bytes() == original
    raw = (directory / files.CORRECTIONS_NAME).read_bytes()
    assert "—".encode() in raw  # stored as UTF-8, not escaped and not mis-decoded
    assert "â€”".encode() not in raw  # the cp1252 reading of an em dash
    assert b"\xc3\xa2\xe2\x82\xac" not in raw and b"\xc3\xa2\xe2\x82\xac" not in readme
    document = json.loads(raw.decode("utf-8"))
    for record in document["edits"]:
        stored = record["start"], record["end"], record["original"], record["replacement"]
        assert ctx.readme[stored[0] : stored[1]] == stored[2]
    stored_diagram = next(e for e in document["edits"] if e["kind"] == DIAGRAM_FIX)
    assert stored_diagram["original"] == diagram_edits[0].original
    assert stored_diagram["replacement"] == diagram_edits[0].replacement
    assert "Nothing —" in stored_diagram["original"]
    # the patch carries the same characters the README does
    patch = (directory / files.PATCH_NAME).read_bytes().decode("utf-8")
    assert "—" in patch and "日" in patch
    assert patch == files.render_patch(README, result.corrected)
    # the sealed digests are over exactly those bytes
    manifest = json.loads((directory / files.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["corrected_sha256"] == files.sha256(readme)
    assert manifest["files"][files.CORRECTIONS_NAME]["sha256"] == files.sha256(raw)
    # the gate recomputes from the bundle's bytes alone and reproduces README.md exactly
    candidate = load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT)
    assert candidate.readme_text.encode("utf-8") == readme


def test_every_committed_bundle_still_passes_the_gate_and_holds_no_misdecoded_text() -> None:
    """A change to a detector's output must not break a sealed bundle: the gate re-derives each one
    (an older bundle records no ``rendering`` and is re-derived the way it was written)."""
    bundles = sorted(
        path for run in (REPO_ROOT / "corrections").iterdir() for path in run.iterdir()
    )
    assert bundles
    for bundle in bundles:
        repository = bundle.name.replace("__", "/", 1)
        load_proposable_correction(bundle, repository, root=REPO_ROOT, require_sums=True)
        for name in (files.README_NAME, files.CORRECTIONS_NAME, files.PATCH_NAME):
            assert b"\xc3\xa2\xe2\x82\xac" not in (bundle / name).read_bytes(), (bundle.name, name)


def test_the_bundle_is_the_same_bytes_whatever_the_hosts_default_encoding(
    tmp_path: Path,
) -> None:
    """A fresh interpreter with UTF-8 mode off (the Windows default, cp1252) writes the same
    ``corrections.json`` as one with it on: no write or read relies on the locale codec."""
    script = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            "from conftest import context",
            "import test_bundle_encoding as t",
            "from repository_presenter.components.readme_correction import bundle as files",
            "from repository_presenter.components.readme_correction.check import validation_delta",
            "from repository_presenter.components.readme_correction.engine import correct",
            "ctx = context(t.README)",
            "result = correct(ctx)",
            "data = t.README.encode('utf-8')",
            "delta = validation_delta(ctx, result, data)",
            "files.write_bundle(ctx, data, result, delta, Path(sys.argv[1]))",
        ]
    )
    outputs = []
    for mode in ("0", "1"):
        out = tmp_path / f"utf8-{mode}"
        env = {key: value for key, value in os.environ.items() if key != "PYTHONUTF8"}
        env["PYTHONUTF8"] = mode
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(REPO_ROOT / "src"),
                str(REPO_ROOT / "tests" / "components" / "readme_correction"),
                str(REPO_ROOT / "tests"),
            ]
        )
        done = subprocess.run(
            [sys.executable, "-c", script, str(out)],
            env=env,
            capture_output=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
        outputs.append(out)
    for name in (files.CORRECTIONS_NAME, files.README_NAME, files.PATCH_NAME, files.MANIFEST_NAME):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes(), name
