# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Offline re-check of the inherited-units extraction scope: reconstruct the original README by
reverse-applying README.patch to the sealed README.md, regenerate the inherited_unit facts under the
running code, and compare them with the sealed facts.json (id, value). Pure read.

usage: inherited_probe.py <root> <out.json>"""
import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from repository_presenter.components.readme.evidence.facts.inherited import (  # noqa: E402
    INHERITED_UNITS_VERSION,
    inherited_unit_facts,
)
from repository_presenter.core.facts import Evidence, Fact  # noqa: E402

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def reverse_apply(new_text: str, patch: str) -> str:
    new_lines = new_text.splitlines(keepends=True)
    old: list[str] = []
    pos = 0
    lines = patch.splitlines(keepends=True)
    i = 0
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1
    while i < len(lines):
        m = HUNK.match(lines[i])
        if not m:
            i += 1
            continue
        c, d = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
        start = c if d == 0 else c - 1
        old.extend(new_lines[pos:start])
        pos = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            ln = lines[i]
            tag, body = ln[:1], ln[1:]
            if tag == " ":
                old.append(body)
                pos += 1
            elif tag == "-":
                old.append(body)
            elif tag == "+":
                pos += 1
            i += 1
    old.extend(new_lines[pos:])
    return "".join(old)


out = {"inherited_units_version": INHERITED_UNITS_VERSION, "bundles": {}}
for cur in sorted((root / "candidates").glob("*/CURRENT")):
    name = cur.parent.name
    rev = cur.read_text("utf-8").strip()
    b = cur.parent / rev
    row = out["bundles"].setdefault(name, {})
    try:
        facts_doc = json.loads((b / "facts.json").read_text("utf-8"))
        readme = (b / "README.md").read_text("utf-8")
        patch = (b / "README.patch").read_text("utf-8")
        original = reverse_apply(readme, patch)
        symbols = []
        sealed = {}
        for f in facts_doc["facts"]:
            if f["kind"] == "public_symbol":
                f2 = dict(f)
                f2["evidence"] = tuple(Evidence(**e) for e in f2.get("evidence", ()))
                f2["attributes"] = dict(f2.get("attributes") or {})
                symbols.append(Fact(**f2))
            if f["kind"] == "inherited_unit":
                sealed[f["id"]] = f["value"]
        evid = next((e["path"] for f in facts_doc["facts"] if f["kind"] == "inherited_unit" for e in f["evidence"]), "README.md")
        regen = {f.id: f.value for f in inherited_unit_facts(evid, original.encode("utf-8"), symbols)}
        row["sealed_units"] = len(sealed)
        row["regen_units"] = len(regen)
        row["identical"] = sealed == regen
        row["added"] = sorted(set(regen) - set(sealed))[:5]
        row["removed"] = sorted(set(sealed) - set(regen))[:5]
        row["altered"] = sorted(k for k in set(sealed) & set(regen) if sealed[k] != regen[k])[:5]
        row["n_added"] = len(set(regen) - set(sealed))
        row["n_removed"] = len(set(sealed) - set(regen))
        row["n_altered"] = sum(1 for k in set(sealed) & set(regen) if sealed[k] != regen[k])
        row["original_sha"] = hashlib.sha256(original.encode()).hexdigest()[:12]
    except Exception as exc:  # noqa: BLE001
        row["error"] = repr(exc)[:300]
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
for n, r in out["bundles"].items():
    print(n[:50].ljust(50), r.get("sealed_units"), r.get("regen_units"), r.get("identical"), r.get("error", ""), r.get("added", "")[:2], r.get("altered", "")[:2])
