"""Parse every .py file under a directory with the standard library ast module.

Usage: python -I ast_parse_all.py <directory>
Prints one line per failing file (path: error text) and a final 'FAILED/TOTAL' summary, then a
per-area breakdown. Exit status 1 when any file fails to parse.
"""

import ast
import collections
import pathlib
import sys


def area_of(rel: str) -> str:
    parts = rel.split("/")
    if len(parts) >= 3:
        return "/".join(parts[:2])
    return parts[0] if len(parts) == 2 else "(root)"


root = pathlib.Path(sys.argv[1])
failed = []
total = 0
by_area: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
for path in sorted(root.rglob("*.py")):
    if ".git" in path.parts:
        continue
    total += 1
    rel = path.relative_to(root).as_posix()
    area = area_of(rel)
    by_area[area][1] += 1
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    except SyntaxError as exc:
        failed.append((rel, f"{type(exc).__name__}: {exc.msg} (line {exc.lineno})"))
        by_area[area][0] += 1
for rel, msg in failed:
    print(f"{rel}: {msg}")
print(f"FAILED/TOTAL: {len(failed)}/{total}")
for area, (bad, count) in sorted(by_area.items()):
    print(f"  {area}: {bad} of {count} fail")
sys.exit(1 if failed else 0)
