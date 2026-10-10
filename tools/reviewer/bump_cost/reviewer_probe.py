# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Offline replay of the reviewer's deterministic fold stack (review_document) from the raw
independent_review reads a bundle retains in raw_calls.json, under the running code, compared with
the sealed review.json.  usage: reviewer_probe.py <root> <out.json>   Pure read; no provider call."""
import itertools
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from repository_presenter.components.readme.composition.renderer import renderer_sentences  # noqa: E402
from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems  # noqa: E402
from repository_presenter.components.readme.review.independent.review import (  # noqa: E402
    REVIEWER_LOGIC_VERSION,
    review_document,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument  # noqa: E402
from repository_presenter.core.llm.prompts import load_manifests  # noqa: E402
from repository_presenter.core.registry.models import RegistryEntry  # noqa: E402

known_ecosystems()
manifests = load_manifests(root / "prompts")
entries = json.loads((root / "data" / "registry.json").read_text("utf-8"))["entries"]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reverse_patch import reverse_apply  # noqa: E402


def load_facts(path):
    payload = json.loads(path.read_text("utf-8"))
    facts = []
    for row in payload["facts"]:
        row = dict(row)
        row["evidence"] = tuple(Evidence(**e) for e in row.get("evidence", ()))
        row["attributes"] = dict(row.get("attributes") or {})
        facts.append(Fact(**row))
    return FactsDocument(repository=payload["repository"], source_revision=payload["source_revision"], facts=tuple(facts))


def sig(doc):
    return {
        "verdict": doc.get("verdict"),
        "as_returned": doc.get("verdict_as_returned"),
        "blocking": sorted(f["id"] for f in doc.get("findings", [])),
        "advisory": sorted(f["id"] for f in doc.get("advisory", [])),
    }


out = {"reviewer_logic_version": REVIEWER_LOGIC_VERSION, "bundles": {}}
for cur in sorted((root / "candidates").glob("*/CURRENT")):
    name = cur.parent.name
    rev = cur.read_text("utf-8").strip()
    b = cur.parent / rev
    if not (b / "raw_calls.json").is_file():
        continue
    row = out["bundles"].setdefault(name, {})
    try:
        raw = json.loads((b / "raw_calls.json").read_text("utf-8"))
        calls = raw.get("calls", raw)
        reads = [v["output"] for v in calls.values() if v.get("job") == "independent_review"]
        sealed = json.loads((b / "review.json").read_text("utf-8"))
        facts = load_facts(b / "facts.json")
        entry = RegistryEntry.model_validate(next(i for i in entries if i["repository"] == facts.repository))
        plan = json.loads((b / "plan.json").read_text("utf-8"))
        units = json.loads((b / "content_units.json").read_text("utf-8"))
        disp = json.loads((b / "dispositions.json").read_text("utf-8"))
        readme = (b / "README.md").read_text("utf-8")
        original = reverse_apply(readme, (b / "README.patch").read_text("utf-8"))
        rendered = renderer_sentences(entry, facts, plan, units, disp)
        trigger = (sealed.get("second_reader") or {}).get("trigger")
        row["reads"] = len(reads)
        row["sealed"] = sig(sealed)
        row["replays"] = []
        for order in itertools.permutations(range(len(reads))):
            first = reads[order[0]]
            second = reads[order[1]] if len(reads) > 1 and (sealed.get("second_reader") or {}).get("read") not in (False, 1) else None
            doc = review_document(
                first, manifests["independent_review"], manifests["section_authoring"],
                sealed["readme_sha256"], candidate_readme=readme, facts=facts, original_readme=original,
                rendered=rendered, second=second, units=units, dispositions=disp, trigger=trigger,
            )
            row["replays"].append({"order": list(order), **sig(doc)})
            if len(reads) < 2:
                break
        row["match_any_order"] = any(r["verdict"] == row["sealed"]["verdict"] and r["blocking"] == row["sealed"]["blocking"] and r["advisory"] == row["sealed"]["advisory"] for r in row["replays"])
        row["sealed_logic_version"] = (json.loads((b / "dependencies.json").read_text("utf-8")).get("components") or {}).get("reviewer_logic")
    except Exception as exc:  # noqa: BLE001
        import traceback

        row["error"] = (repr(exc) + traceback.format_exc()[-500:])[:900]
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
for n, r in out["bundles"].items():
    print(n[:50].ljust(50), r.get("sealed_logic_version"), "->", out["reviewer_logic_version"], "match:", r.get("match_any_order"), r.get("error", "")[:300])
