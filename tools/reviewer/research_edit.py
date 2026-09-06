"""Reusable helpers for editing docs/RESEARCH_AND_GUIDELINES.md safely (owner/reviewer tooling).

Written 2026-09-06 after writing the same "anchor-replace text inside a huge single-line YAML flow
scalar, then re-parse the fenced block to prove it still loads" script twice in one session as a
throwaway in the session scratchpad (append_research.py, append_research2.py) — exactly the pattern
this directory exists to stop (see tools/README.md). Any future governance edit of this shape should
import from here instead of writing a new disposable script; extend this module if the shape does
not quite fit, rather than duplicating it elsewhere.

Never imported by src/, never read for an acceptance predicate, never touched by the loop or a lane
(tools/README.md's boundary).
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
RESEARCH = REPO / "docs" / "RESEARCH_AND_GUIDELINES.md"


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


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print(
            "usage: research_edit.py <anchor-file> <replacement-file> <target-file>\n"
            "  reads the anchor and replacement as raw text (no escaping), applies safe_replace,\n"
            "  then validates the G4-W17 YAML block still parses.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    anchor_file, replacement_file, target_file = (Path(p) for p in sys.argv[1:])
    anchor_text = anchor_file.read_text(encoding="utf-8")
    replacement_text = replacement_file.read_text(encoding="utf-8")
    items = replace_and_validate(target_file, anchor_text, replacement_text)
    print(f"ok - {len(items)} items parsed from the validated YAML block")
