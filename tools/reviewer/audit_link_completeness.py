"""Audit every sealed candidate for the VERIFIED_REWRITE link-completeness gap fixed in
planning.py (2026-09-08): a disposition naming link_target facts for its re-authored unit whose
ids never reached plan.json's own "links" list. test_sealed_bytes.py cannot see this - it renders
from the sealed plan.json as-is, so a plan that already dropped the links renders "consistently"
with itself. This walks every candidates/*/*/ manifest directory directly against dispositions.json
and plan.json to find any sealed candidate carrying the same gap the fix now prevents going
forward, so the fix's effect is checked globally, not just on the candidate that surfaced it.

Usage: python tools/reviewer/audit_link_completeness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = REPO_ROOT / "candidates"


def audit_one(manifest_dir: Path) -> list[str]:
    dispositions_path = manifest_dir / "dispositions.json"
    plan_path = manifest_dir / "plan.json"
    if not dispositions_path.exists() or not plan_path.exists():
        return [f"missing dispositions.json or plan.json in {manifest_dir}"]
    dispositions = json.loads(dispositions_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    planned_ids = {str(link.get("link_fact_id")) for link in plan.get("links", [])}
    gaps: list[str] = []
    for entry in dispositions.get("dispositions", []):
        if entry.get("disposition") != "VERIFIED_REWRITE":
            continue
        destination = entry.get("destination_section")
        if not destination:
            continue
        for fact_id in entry.get("fact_ids") or []:
            fact_id = str(fact_id)
            if fact_id.startswith("link_target:") and fact_id not in planned_ids:
                gaps.append(
                    f"{entry.get('unit_id')}: {fact_id} disposed VERIFIED_REWRITE to "
                    f"{destination!r} but absent from plan.json's links"
                )
    return gaps


def main() -> None:
    manifest_dirs = sorted(p for p in CANDIDATES.glob("*/*") if p.is_dir())
    total_gaps = 0
    for manifest_dir in manifest_dirs:
        gaps = audit_one(manifest_dir)
        label = f"{manifest_dir.parent.name}/{manifest_dir.name[:12]}"
        if gaps:
            total_gaps += len(gaps)
            print(f"GAP  {label}")
            for gap in gaps:
                print(f"       {gap}")
        else:
            print(f"clean {label}")
    print(f"\n{len(manifest_dirs)} manifest directories checked, {total_gaps} gap(s) found")


if __name__ == "__main__":
    main()
