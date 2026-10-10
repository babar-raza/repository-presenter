# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Every bump of a governed version constant since 2026-09-19: (date, commit, constant, old, new, subject).
usage: run from a checkout; BUMP_COST_OUT=<dir> receives timeline.json; stdout is `|`-separated rows."""
import ast
import json
import os
import subprocess
import sys
OUT = os.environ.get("BUMP_COST_OUT", os.getcwd())
B = "src/repository_presenter/components/readme/"
FILES = {
 B+"composition/renderer.py": ["RENDERER_VERSION"],
 B+"composition/authoring.py": ["NORMALISATION_VERSION"],
 B+"review/independent/review.py": ["REVIEWER_LOGIC_VERSION"],
 B+"validation/registry.py": ["VALIDATOR_VERSION", "CHECKS"],
 B+"bundle/seal.py": ["CONTRACT_VERSION", "ACCEPTANCE_PROFILE_VERSION"],
 B+"review/acceptance/profile.py": ["PROFILE_VERSION"],
 B+"composition/components/shell.py": ["SHELL_VERSION"],
 B+"composition/policy.py": ["POLICY_VERSION"],
 B+"extractors/surface/extractor.py": ["EXTRACTOR_VERSION"],
 B+"evidence/facts/inherited.py": ["INHERITED_UNITS_VERSION"],
}

def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
    return r.stdout if r.returncode == 0 else None

def versions(text, consts):
    out = {}
    if text is None:
        return out
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in consts:
                    out[t.id] = str(node.value.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Check" and "CHECKS" in consts:
            f = {}
            for pos, name in ((0, "id"), (1, "version")):
                if len(node.args) > pos and isinstance(node.args[pos], ast.Constant):
                    f[name] = str(node.args[pos].value)
            for kw in node.keywords:
                if kw.arg in ("id", "version") and isinstance(kw.value, ast.Constant):
                    f[kw.arg] = str(kw.value.value)
            if "id" in f and "version" in f:
                out["Check:" + f["id"]] = f["version"]
    return out

rows = []
for path, consts in FILES.items():
    log = git("log", "--since=2026-09-19", "--format=%H|%h|%ad|%s", "--date=short", "--", path).strip().splitlines()
    print(path, len(log), file=sys.stderr, flush=True)
    for line in reversed(log):
        H, h, d, s = line.split("|", 3)
        new = git("show", f"{H}:{path}")
        old = git("show", f"{H}~1:{path}")
        vn, vo = versions(new, consts), versions(old, consts)
        for k in sorted(set(vn) | set(vo)):
            if vn.get(k) != vo.get(k):
                rows.append((d, H, k, vo.get(k, ""), vn.get(k, ""), s))
rows.sort(key=lambda r: (r[0], r[1]))
json.dump(rows, open(os.path.join(OUT, "timeline.json"), "w"))
for r in rows:
    print("|".join(r))
