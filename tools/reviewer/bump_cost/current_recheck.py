# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Offline re-check of every CURRENT sealed bundle under the code on sys.path.

usage: current_recheck.py <code_src> <candidates_dir> <registry.json> <out.json> [--validate]

Pure read: no network, no provider call, writes only <out.json>.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

code_src, cand_dir, registry_path, out_path = sys.argv[1:5]
do_validate = "--validate" in sys.argv
sys.path.insert(0, code_src)

from repository_presenter.components.readme.composition.renderer import (  # noqa: E402
    RENDERER_VERSION,
    render_readme,
)
from repository_presenter.components.readme.extractors.platforms.registry import (  # noqa: E402
    known_ecosystems,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument  # noqa: E402
from repository_presenter.core.registry.models import RegistryEntry  # noqa: E402

known_ecosystems()
candidates = Path(cand_dir)
entries = json.loads(Path(registry_path).read_text("utf-8"))["entries"]


def entry_for(repository):
    row = next(item for item in entries if item["repository"] == repository)
    return RegistryEntry.model_validate(row)


def load_facts(path):
    payload = json.loads(path.read_text("utf-8"))
    facts = []
    for row in payload["facts"]:
        row = dict(row)
        row["evidence"] = tuple(Evidence(**entry) for entry in row.get("evidence", ()))
        row["attributes"] = dict(row.get("attributes") or {})
        facts.append(Fact(**row))
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=tuple(facts),
    )


def read(bundle, name):
    return json.loads((bundle / name).read_text("utf-8"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


result = {"renderer_version": RENDERER_VERSION, "bundles": {}}
try:
    from repository_presenter.components.readme.validation import registry as vreg

    result["validator_version"] = vreg.VALIDATOR_VERSION
except Exception as exc:  # noqa: BLE001
    vreg = None
    result["validator_import_error"] = repr(exc)

for current in sorted(candidates.glob("*/CURRENT")):
    name = current.parent.name
    revision = current.read_text("utf-8").strip()
    bundle = current.parent / revision
    row = {"revision": revision}
    result["bundles"][name] = row
    try:
        facts = load_facts(bundle / "facts.json")
        entry = entry_for(facts.repository)
        plan = read(bundle, "plan.json")
        units = read(bundle, "content_units.json")
        dispositions = read(bundle, "dispositions.json")
        sealed_readme = (bundle / "README.md").read_text("utf-8")
        rendered = render_readme(entry, facts, plan, units, dispositions)
        row["render_sha"] = sha(rendered)
        row["sealed_sha"] = sha(sealed_readme)
        row["render_equal"] = rendered == sealed_readme
        if rendered != sealed_readme:
            a, b = sealed_readme.splitlines(), rendered.splitlines()
            import difflib

            diff = [d for d in difflib.unified_diff(a, b, lineterm="", n=0) if not d.startswith(("---", "+++", "@@"))]
            row["render_diff_lines"] = len(diff)
            row["render_diff_sample"] = diff[:6]
    except Exception as exc:  # noqa: BLE001
        row["render_error"] = repr(exc)[:300]
        continue
    if do_validate and vreg is not None:
        try:
            sealed_validation = read(bundle, "validation.json")
            investigation = read(bundle, "investigation.json") if (bundle / "investigation.json").is_file() else {}
            from repository_presenter.components.readme.composition.authoring import authoring_tasks

            tasks = authoring_tasks(entry, facts, investigation, dispositions, plan)
            # tree: relative link targets of the sealed README + every evidence path (the tree
            # half of BC-06 is source-derived and unchanged by a validator bump)
            import re

            paths = set()
            for target in re.findall(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)", sealed_readme):
                paths.add(target.split("#")[0].strip("/").removeprefix("./"))
            for fact in facts.facts:
                for ev in fact.evidence:
                    p = getattr(ev, "path", None)
                    if p:
                        paths.add(str(p))
            outcomes = {}
            for label, text in (("sealed_bytes", sealed_readme), ("rerendered", rendered)):
                if label == "rerendered" and rendered == sealed_readme:
                    outcomes[label] = "same_as_sealed_bytes"
                    continue
                cand = vreg.Candidate(
                    entry, facts, plan, units, dispositions, text, None,
                    facts.source_revision, None, sorted(paths), tasks,
                )
                with tempfile.TemporaryDirectory() as tmp:
                    doc = vreg.validate_candidate(cand, Path(tmp), [])
                outcomes[label] = {
                    c["id"]: {"v": c["version"], "verdict": c["verdict"], "n": len(c.get("failures", []) or c.get("details", []) or []),
                              "first": (c.get("details") or [""])[0][:160]}
                    for c in doc["checks"]
                }
            row["validation_now"] = outcomes
            row["validation_sealed"] = {
                c["id"]: {"v": c["version"], "verdict": c["verdict"]} for c in sealed_validation["checks"]
            }
        except Exception as exc:  # noqa: BLE001
            import traceback

            row["validate_error"] = (repr(exc) + traceback.format_exc()[-400:])[:900]

Path(out_path).write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
print("ok", len(result["bundles"]))
