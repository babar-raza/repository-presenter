"""Audit every sealed candidate for a review.json that claims a second independent read
(`second_reader.read == true`) without calls.jsonl's own provider-call ledger backing it up.

Checked directly against every real sealed candidate before choosing the key (PHASE0/TB-10+RC-07):
`calls.jsonl` entries for `job == "independent_review"` carry both `request_sha256` (varies across
a logical call's own retries and cache lookups) and `logical_call_id` (stable per distinct reviewer
invocation - one value for the first read, a second for the corroborating read). Across all nine
sealed manifest directories, the count of distinct `logical_call_id` values for that job matches
`second_reader.read` exactly: 1 wherever it's `false`, 2 wherever it's `true` - `request_sha256`'s
distinct count does not (it also grows with retries within a single reader). A terminal outcome is
`success` or `cache_reuse`; `cache_stale`/`response_invalid` are non-terminal retries and are
excluded so a failed-then-retried single call cannot masquerade as a second reader.

Usage: python tools/reviewer/audit_second_reader_ledger.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = REPO_ROOT / "candidates"
_TERMINAL_OUTCOMES = {"success", "cache_reuse"}


def audit_one(manifest_dir: Path) -> list[str]:
    review_path = manifest_dir / "review.json"
    calls_path = manifest_dir / "calls.jsonl"
    if not review_path.exists() or not calls_path.exists():
        return [f"missing review.json or calls.jsonl in {manifest_dir}"]
    review = json.loads(review_path.read_text(encoding="utf-8"))
    second_reader = review.get("second_reader") or {}
    if not second_reader.get("read"):
        return []
    logical_ids: set[str] = set()
    for line in calls_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        call = json.loads(line)
        if (
            call.get("job") == "independent_review"
            and call.get("outcome") in _TERMINAL_OUTCOMES
        ):
            logical_ids.add(call.get("logical_call_id"))
    if len(logical_ids) < 2:
        message = (
            "review.json claims second_reader.read=true but calls.jsonl's independent_review "
            f"ledger shows only {len(logical_ids)} distinct logical_call_id "
            f"(terminal outcomes {sorted(_TERMINAL_OUTCOMES)})"
        )
        return [message]
    return []


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
