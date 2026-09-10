"""Audit every sealed candidate for an install_command fact whose evidence claims "verified
source build" (`validation/registry.py::_check_install`'s BC-02 alternate SUPPORTED path for an
ecosystem with no package registry to confirm against) without any example receipt actually
recording a corroborating build.

`core/examples.py::ExampleReceipt.build_verified` (PHASE0/EVAL-01 companion field, added
2026-09-10) distinguishes a full library build from a bare syntax-check. Sealed bundles predating
that field simply omit the key from every stored receipt in examples.json - checked directly
against both real "verified source build" candidates in the portfolio (aspose-cells-foss for Cpp
and Rust) before writing this: every receipt in both is missing `build_verified` entirely (not
`false`), so a rule that flags a missing key would flag the whole current portfolio's only two
real cases with no defect present. This rule only flags when the key is present somewhere and
never `true` on an EXECUTED receipt - a real, checkable contradiction between the claim and the
ledger, not a schema-age artifact.

Usage: python tools/reviewer/audit_install_claims.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = REPO_ROOT / "candidates"


def audit_one(manifest_dir: Path) -> list[str]:
    facts_path = manifest_dir / "facts.json"
    examples_path = manifest_dir / "examples.json"
    if not facts_path.exists() or not examples_path.exists():
        return [f"missing facts.json or examples.json in {manifest_dir}"]
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    receipts = json.loads(examples_path.read_text(encoding="utf-8"))
    executed = [r for r in receipts if r.get("outcome") == "EXECUTED"]
    recorded = [r.get("build_verified") for r in executed if "build_verified" in r]
    findings: list[str] = []
    for fact in facts.get("facts", []):
        if fact.get("kind") != "install_command" or fact.get("polarity") != "SUPPORTED":
            continue
        details = " ".join(e.get("detail") or "" for e in fact.get("evidence", []))
        if "verified source build" not in details:
            continue
        if recorded and not any(recorded):
            findings.append(
                f"{fact.get('id')}: evidence claims a verified source build but no EXECUTED "
                f"example receipt records build_verified=true ({len(executed)} executed, "
                f"build_verified recorded on {len(recorded)})"
            )
    return findings


def main() -> None:
    manifest_dirs = sorted(p for p in CANDIDATES.glob("*/*") if p.is_dir())
    total = 0
    for manifest_dir in manifest_dirs:
        findings = audit_one(manifest_dir)
        label = f"{manifest_dir.parent.name}/{manifest_dir.name[:12]}"
        if findings:
            total += len(findings)
            print(f"GAP  {label}")
            for finding in findings:
                print(f"       {finding}")
        else:
            print(f"clean {label}")
    print(f"\n{len(manifest_dirs)} manifest directories checked, {total} gap(s) found")


if __name__ == "__main__":
    main()
