"""Audit every sealed candidate for VERIFIED_PRESERVE "list" units placed verbatim into
api_reference whose disposition cites only module-granularity public_symbol facts (never a
class/enum fact individually). Such a unit's overlap with the deterministic Core API table is
invisible to placement.py's planned_fact_ids/renderer_fact_ids, which track only the plan's own
selected "hub" symbols - so a legacy README's whole member-by-member API reference can be
preserved verbatim alongside the freshly authored table + hub sections, duplicating it.

Measured 2026-09-08 on aspose-email-foss/Aspose.Email-FOSS-for-Python: five preserved "list"
units (the module's entire High-Level/Low-Level/Enumerations/Exceptions member breakdown) each
cite only ``public_symbol:email_foss.msg`` or ``public_symbol:email_foss.cfb`` - never an
individual class - so none registered as overlapping the table's per-class rows, and review
correctly rejected the result (BC-10) every time; the repair loop cannot fix it because the
offending text is placed, not authored (targeted_repair only revises S3-S6 stage output).

This is a diagnostic sweep, not a fix - see docs/RESEARCH_AND_GUIDELINES.md for why a safe,
general fix is not available without either a live re-dispositioning call or risking silent data
loss on a legitimately preserved module-level paragraph.

Usage: python tools/reviewer/audit_preserved_api_lists.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = REPO_ROOT / "candidates"
_MODULE_LEVEL_ONLY_SUSPECT = "module-level fact(s) only, no individual class/enum cited"


def audit_one(manifest_dir: Path) -> list[str]:
    dispositions_path = manifest_dir / "dispositions.json"
    facts_path = manifest_dir / "facts.json"
    if not dispositions_path.exists() or not facts_path.exists():
        return [f"missing dispositions.json or facts.json in {manifest_dir}"]
    dispositions = json.loads(dispositions_path.read_text(encoding="utf-8"))
    facts = {f["id"]: f for f in json.loads(facts_path.read_text(encoding="utf-8"))["facts"]}
    findings: list[str] = []
    for entry in dispositions.get("dispositions", []):
        if entry.get("destination_section") != "api_reference":
            continue
        if entry.get("disposition") != "VERIFIED_PRESERVE":
            continue
        unit_id = str(entry.get("unit_id", ""))
        if not unit_id.endswith(".list"):
            continue
        fact_ids = entry.get("fact_ids") or []
        kinds = {
            (facts[fid].get("attributes") or {}).get("symbol_kind", "")
            for fid in fact_ids
            if fid in facts
        }
        if kinds and kinds.issubset({"module", "package"}):
            findings.append(f"{unit_id}: cites only {sorted(kinds)} ({_MODULE_LEVEL_ONLY_SUSPECT})")
    return findings


def main() -> None:
    manifest_dirs = sorted(p for p in CANDIDATES.glob("*/*") if p.is_dir())
    total = 0
    for manifest_dir in manifest_dirs:
        findings = audit_one(manifest_dir)
        label = f"{manifest_dir.parent.name}/{manifest_dir.name[:12]}"
        if findings:
            total += len(findings)
            print(f"SUSPECT {label}")
            for finding in findings:
                print(f"          {finding}")
        else:
            print(f"clean   {label}")
    print(f"\n{len(manifest_dirs)} manifest directories checked, {total} suspect unit(s) found")


if __name__ == "__main__":
    main()
