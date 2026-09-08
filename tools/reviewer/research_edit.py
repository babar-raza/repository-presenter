"""Reusable helpers for editing docs/RESEARCH_AND_GUIDELINES.md and docs/DECISION_LOG.md safely
(owner/reviewer tooling).

Written 2026-09-06 after writing the same "anchor-replace text inside a huge single-line YAML flow
scalar, then re-parse the fenced block to prove it still loads" script twice in one session as a
throwaway in the session scratchpad (append_research.py, append_research2.py) — exactly the pattern
this directory exists to stop (see tools/README.md). Any future governance edit of this shape should
import from here instead of writing a new disposable script; extend this module if the shape does
not quite fit, rather than duplicating it elsewhere.

`append_entry` was added 2026-09-08 for the same reason, one shape late: ten near-identical
"read the whole file, concatenate a new dated entry, write it back" scratchpad throwaways
(add_r6_report.py, add_item44.py, add_items_37_39.py, and seven more) had accumulated across one
session appending to what was then RESEARCH_AND_GUIDELINES.md §31 — the exact duplication this file
exists to stop, just for the append shape rather than the anchor-replace one. §31 moved to its own
file (docs/DECISION_LOG.md) the same day, since it was 43% of RESEARCH_AND_GUIDELINES.md's bytes and
the only section still growing every session.

Never imported by src/, never read for an acceptance predicate, never touched by the loop or a lane
(tools/README.md's boundary).
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
RESEARCH = REPO / "docs" / "RESEARCH_AND_GUIDELINES.md"
DECISION_LOG = REPO / "docs" / "DECISION_LOG.md"


def append_entry(path: Path, entry_text: str) -> str:
    """Append `entry_text` to `path` as a new entry, separated from what precedes it by exactly
    one blank line, and return the new text. Writes with `newline="\\n"` (Windows trap,
    `project/loop-prompt.md` §3). `entry_text` should not itself carry leading/trailing blank
    lines - this function owns the separator so entries stay consistently spaced regardless of
    how the file currently ends."""
    text = path.read_text(encoding="utf-8")
    body = entry_text.strip("\n")
    new_text = text.rstrip("\n") + "\n\n" + body + "\n"
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return new_text


def safe_replace(path: Path, anchor: str, replacement: str, expected_count: int = 1) -> str:
    """Replace `anchor` with `replacement` in `path`, asserting it occurs exactly `expected_count`
    times first. Writes the result back with `newline="\\n"` (Windows trap, `project/loop-prompt.md`
    §3) and returns the new text. Raises AssertionError, not a silent no-op, on a count mismatch —
    the file may have moved under a concurrent writer since it was last read."""
    text = path.read_text(encoding="utf-8")
    found = text.count(anchor)
    if found != expected_count:
        raise AssertionError(
            f"anchor found {found} times in {path}, expected {expected_count} "
            "(the file may have changed since you last read it - re-read before retrying)"
        )
    text = text.replace(anchor, replacement, expected_count)
    path.write_text(text, encoding="utf-8", newline="\n")
    return text


def load_yaml_block(text: str, id_marker: str) -> dict[str, dict]:
    """Find the fenced code block containing `id_marker` (e.g. "- id: G4-W17"), YAML-parse it, and
    return {item_id: item_dict}. Raises if the marker or its enclosing fence is missing, or the
    block no longer parses - the caller's edit broke it and must not be committed."""
    idx = text.find(id_marker)
    if idx < 0:
        raise AssertionError(f"{id_marker!r} not found")
    start = text.rfind("```", 0, idx)
    end = text.find("```", idx)
    if start < 0 or end < 0:
        raise AssertionError(f"no enclosing ``` fence found around {id_marker!r}")
    block = text[start + 3 : end]
    first_line, _, rest = block.partition("\n")
    body = rest if first_line.strip() in ("yaml", "yml") else block
    data = yaml.safe_load(body)
    return {item["id"]: item for item in data}


def replace_and_validate(
    path: Path,
    anchor: str,
    replacement: str,
    *,
    id_marker: str = "- id: G4-W17",
    expected_count: int = 1,
) -> dict[str, dict]:
    """`safe_replace` then `load_yaml_block` on the result, so a broken edit is caught before it is
    ever staged. Returns the parsed items dict on success."""
    text = safe_replace(path, anchor, replacement, expected_count)
    return load_yaml_block(text, id_marker)


_USAGE = (
    "usage: research_edit.py replace <anchor-file> <replacement-file> <target-file>\n"
    "         reads the anchor and replacement as raw text (no escaping), applies safe_replace,\n"
    "         then validates the G4-W17 YAML block still parses.\n"
    "       research_edit.py append <entry-file> <target-file>\n"
    "         reads the entry as raw text and appends it to target-file, separated from what\n"
    "         precedes it by exactly one blank line.\n"
)

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if args and args[0] == "append" and len(args) == 3:
        entry_file, target_file = Path(args[1]), Path(args[2])
        entry_text = entry_file.read_text(encoding="utf-8")
        append_entry(target_file, entry_text)
        print(f"ok - entry appended to {target_file}")
    elif args and args[0] == "replace" and len(args) == 4:
        anchor_file, replacement_file, target_file = (Path(p) for p in args[1:])
        anchor_text = anchor_file.read_text(encoding="utf-8")
        replacement_text = replacement_file.read_text(encoding="utf-8")
        items = replace_and_validate(target_file, anchor_text, replacement_text)
        print(f"ok - {len(items)} items parsed from the validated YAML block")
    else:
        print(_USAGE, file=sys.stderr)
        raise SystemExit(2)
