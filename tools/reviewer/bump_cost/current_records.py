# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Current-state grouping: per CURRENT bundle, every dependency record that differs from the running
code, plus the dry-run routing. Pure read.  usage: current_records.py <root> <out.json>"""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from repository_presenter.cli import PROMPTS_DIRNAME  # noqa: E402
from repository_presenter.components.readme.bundle.dry_run import code_derived_dependencies, portfolio_routing  # noqa: E402
from repository_presenter.components.readme.bundle.evaluation import evaluate  # noqa: E402
from repository_presenter.components.readme.bundle.seal import code_dependencies  # noqa: E402
from repository_presenter.core.llm.prompts import load_manifests  # noqa: E402

current = code_dependencies(load_manifests(root / PROMPTS_DIRNAME))
rows = {}
for r in portfolio_routing(root, current):
    bundle = root / "candidates" / r.repository_dir / r.revision
    sealed = json.loads((bundle / "dependencies.json").read_text("utf-8"))
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    ev = evaluate(sealed, code_derived_dependencies(sealed, current))
    rows[r.repository_dir] = {
        "revision": r.revision,
        "state": r.state,
        "sealed_at": manifest.get("sealed_at"),
        "changed": [
            {"dependency": c.dependency, "detail": c.detail, "scope": c.scope, "reopens": c.reopens}
            for c in ev.changes
        ],
        "scopes": list(r.routing.scopes),
        "would_become": r.would_become,
        "stage": r.routing.stage,
        "recorded": {
            "components": sealed.get("components"),
            "validator_version": sealed.get("validator_version"),
            "contract_version": sealed.get("contract_version"),
            "acceptance_profile_version": sealed.get("acceptance_profile_version"),
            "policy": sealed.get("policy"),
            "prompt_versions": {k: v.get("version") for k, v in (sealed.get("prompts") or {}).items()},
            "extractor_version": (sealed.get("environment") or {}).get("extractor_version"),
            "inherited_units_version": (sealed.get("environment") or {}).get("inherited_units_version"),
        },
    }
json.dump({"current": {k: v for k, v in current.items()}, "bundles": rows}, open(sys.argv[2], "w"), indent=1, sort_keys=True, default=str)
print(len(rows))
