# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
import re
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def reverse_apply(new_text: str, patch: str) -> str:
    new_lines = new_text.splitlines(keepends=True)
    old: list[str] = []
    pos = 0
    lines = patch.splitlines(keepends=True)
    i = 0
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1
    while i < len(lines):
        m = HUNK.match(lines[i])
        if not m:
            i += 1
            continue
        c, d = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
        start = c if d == 0 else c - 1
        old.extend(new_lines[pos:start])
        pos = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            ln = lines[i]
            tag, body = ln[:1], ln[1:]
            if tag == " ":
                old.append(body)
                pos += 1
            elif tag == "-":
                old.append(body)
            elif tag == "+":
                pos += 1
            i += 1
    old.extend(new_lines[pos:])
    return "".join(old)


