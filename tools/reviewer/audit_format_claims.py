"""Audit every sealed candidate for a format fact whose own evidence cites an example's
examples.json outcome that the stored receipt no longer agrees with.

Scope note (PHASE0/TB-10+RC-07): this covers only the landed reachable-AST-statement shape from
TB-02 part 1 (`python_formats.py::format_claims`'s `_reachable_nodes` BFS, which already excludes
dead code from producing a claim at extraction time - docs/DECISION_LOG.md 2026-09-09 19:20). It
does not attempt TB-02 part 2 (fixture-to-input-claim binding), which was implemented, checked
against real portfolio data, found to wrongly downgrade two genuinely-true SUPPORTED facts, and
reverted before ever landing - re-deriving that reverted rule here would reintroduce the same false
positives this rule exists to avoid. A sealed bundle carries no source snapshot to re-run
`_reachable_nodes` against, so this checks the one thing the bundle itself records: that a format
fact's own "example N: OUTCOME" evidence detail (evidence/facts/formats.py) still matches what
examples.json says for that ordinal - drift here means the fact went stale relative to its own
cited receipt, independent of any AST-reachability question.

Usage: python tools/reviewer/audit_format_claims.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = REPO_ROOT / "candidates"
_EXAMPLE_OUTCOME = re.compile(r"^example (\d+): (\w+)")


def audit_one(manifest_dir: Path) -> list[str]:
    facts_path = manifest_dir / "facts.json"
    examples_path = manifest_dir / "examples.json"
    if not facts_path.exists() or not examples_path.exists():
        return [f"missing facts.json or examples.json in {manifest_dir}"]
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    receipts = json.loads(examples_path.read_text(encoding="utf-8"))
    by_ordinal = {r.get("ordinal"): r.get("outcome") for r in receipts}
    findings: list[str] = []
    for fact in facts.get("facts", []):
        if fact.get("kind") != "format":
            continue
        for evidence in fact.get("evidence", []):
            if evidence.get("path") != "examples.json":
                continue
            match = _EXAMPLE_OUTCOME.match(evidence.get("detail") or "")
            if not match:
                continue
            ordinal, claimed = int(match.group(1)), match.group(2)
            actual = by_ordinal.get(ordinal)
            if actual is not None and actual != claimed:
                findings.append(
                    f"{fact.get('id')}: evidence claims example {ordinal} was {claimed!r} but "
                    f"examples.json now records {actual!r}"
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
