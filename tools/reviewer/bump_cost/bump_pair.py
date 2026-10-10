# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""One side (pre or post) of a bump measurement: run selected deterministic stages offline.

usage: bump_pair.py <src> <candidates_dir> <registry.json> <out.json> <render:0|1> <checks comma list|->

Reads every CURRENT bundle under <candidates_dir>; renders (optional) and runs the named blocking
checks only, over the sealed README bytes. Pure read; writes only <out.json>.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import sys
import tempfile
import traceback
from pathlib import Path

src, cand_dir, registry_path, out_path, do_render, checks_arg = sys.argv[1:7]
sys.path.insert(0, src)

from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems  # noqa: E402
from repository_presenter.core.facts import Evidence, Fact, FactsDocument  # noqa: E402
from repository_presenter.core.registry.models import RegistryEntry  # noqa: E402

known_ecosystems()
wanted = [c for c in checks_arg.split(",") if c and c != "-"]
entries = json.loads(Path(registry_path).read_text("utf-8"))["entries"]


def load_facts(path):
    payload = json.loads(path.read_text("utf-8"))
    facts = []
    for row in payload["facts"]:
        row = dict(row)
        row["evidence"] = tuple(Evidence(**e) for e in row.get("evidence", ()))
        row["attributes"] = dict(row.get("attributes") or {})
        facts.append(Fact(**row))
    return FactsDocument(repository=payload["repository"], source_revision=payload["source_revision"], facts=tuple(facts))


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


vreg = None
if wanted:
    from repository_presenter.components.readme.validation import registry as vreg
    from repository_presenter.components.readme.composition.authoring import authoring_tasks

    vreg.BLOCKING_CHECKS = tuple(c for c in vreg.BLOCKING_CHECKS if c.id in wanted)
if do_render == "1":
    from repository_presenter.components.readme.composition.renderer import RENDERER_VERSION, render_readme
result = {}
for current in sorted(Path(cand_dir).glob("*/CURRENT")):
    name = current.parent.name
    revision = current.read_text("utf-8").strip()
    bundle = current.parent / revision
    row = result.setdefault(name, {"revision": revision})
    try:
        manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
        row["state"] = manifest.get("state")
        facts = load_facts(bundle / "facts.json")
        entry = RegistryEntry.model_validate(next(i for i in entries if i["repository"] == facts.repository))
        R = lambda n: json.loads((bundle / n).read_text("utf-8"))
        plan, units, disp = R("plan.json"), R("content_units.json"), R("dispositions.json")
        sealed = (bundle / "README.md").read_text("utf-8")
        row["sealed_sha"] = sha(sealed)
        if do_render == "1":
            rendered = render_readme(entry, facts, plan, units, disp)
            row["render_sha"] = sha(rendered)
            row["renderer_version"] = RENDERER_VERSION
        if wanted:
            inv = R("investigation.json") if (bundle / "investigation.json").is_file() else {}
            tasks = authoring_tasks(entry, facts, inv, disp, plan)
            paths = set()
            for t in re.findall(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)", sealed):
                paths.add(t.split("#")[0].strip("/").removeprefix("./"))
            for f in facts.facts:
                for ev in f.evidence:
                    p = getattr(ev, "path", None)
                    if p:
                        paths.add(str(p))
            kw = dict(entry=entry, facts=facts, plan=plan, units=units, dispositions=disp, readme=sealed,
                      original_readme=None, source_revision=facts.source_revision, readme_sha256=None,
                      tree_paths=sorted(paths), tasks=tasks)
            fields = {f.name for f in dataclasses.fields(vreg.Candidate)}
            cand = vreg.Candidate(**{k: v for k, v in kw.items() if k in fields})
            with tempfile.TemporaryDirectory() as tmp:
                doc = vreg.validate_candidate(cand, Path(tmp), [])
            row["checks"] = {
                c["id"]: {"v": c["version"], "verdict": c["verdict"], "n": len(c.get("details") or []),
                          "h": sha(json.dumps(c.get("details") or [], sort_keys=True))[:12],
                          "first": ((c.get("details") or [""])[0])[:140]}
                for c in doc["checks"]
            }
            row["validator_version"] = doc.get("validator_version")
    except Exception as exc:  # noqa: BLE001
        row["error"] = (repr(exc) + traceback.format_exc()[-300:])[:700]
Path(out_path).write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
print("ok", len(result))
