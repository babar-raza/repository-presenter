# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Record-level history: for every commit in the window, the CURRENT bundle population and what the
stale rule (core.candidates.stale_candidates) says about it under the constants in force.

Output: hist.json = {"commits": [...], "bump_rows": [...], "series": [...]}.
"""
import ast
import json
import os
import subprocess
import sys

OUT = os.environ.get("BUMP_COST_OUT", os.getcwd())
B = "src/repository_presenter/components/readme/"
FILES = {
    B + "composition/renderer.py": ["RENDERER_VERSION"],
    B + "composition/authoring.py": ["NORMALISATION_VERSION"],
    B + "review/independent/review.py": ["REVIEWER_LOGIC_VERSION"],
    B + "validation/registry.py": ["VALIDATOR_VERSION", "CHECKS"],
    B + "composition/components/shell.py": ["SHELL_VERSION"],
}
SINCE = "2026-09-19"


def run(args, inp=None):
    r = subprocess.run(["git", *args], capture_output=True, input=inp, stdin=None if inp else subprocess.DEVNULL)
    return r.stdout if r.returncode == 0 else None


def versions(text, consts):
    out = {}
    if text is None:
        return out
    tree = ast.parse(text)
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
            if "id" in f and "version" in f:
                out["Check:" + f["id"]] = f["version"]
    return out


def constants_at(rev):
    state = {}
    for path, consts in FILES.items():
        blob = run(["show", f"{rev}:{path}"])
        state.update(versions(blob.decode("utf-8") if blob else None, consts))
    return state


# commits in the window, oldest first
log = run(["log", "--reverse", f"--since={SINCE}", "--format=%H|%h|%ad|%s", "--date=iso-strict"]).decode().strip().splitlines()
commits = [dict(zip(("H", "h", "date", "subject"), l.split("|", 3))) for l in log]
base = run(["rev-parse", commits[0]["H"] + "~1"]).decode().strip()

blob_cache = {}


class Batch:
    def __init__(self):
        self.p = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, sha):
        if sha in blob_cache:
            return blob_cache[sha]
        self.p.stdin.write(sha.encode() + b"\n")
        self.p.stdin.flush()
        header = self.p.stdout.readline().split()
        size = int(header[2])
        data = self.p.stdout.read(size + 1)[:size]
        blob_cache[sha] = data
        return data


batch = Batch()


def population(rev):
    """{repo_dir: (revision, deps_dict_without_facts, state, sealed_at)} for the CURRENT bundles at rev."""
    out = run(["ls-tree", "-r", rev, "--", "candidates"])
    if not out:
        return {}
    files = {}
    for line in out.decode().splitlines():
        meta, path = line.split("\t", 1)
        files[path] = meta.split()[2]
    pop = {}
    for path, sha in files.items():
        parts = path.split("/")
        if len(parts) == 3 and parts[2] == "CURRENT":
            d = parts[1]
            revn = batch.get(sha).decode().strip()
            dep = files.get(f"candidates/{d}/{revn}/dependencies.json")
            man = files.get(f"candidates/{d}/{revn}/manifest.json")
            if dep is None or man is None:
                continue
            cache_key = ("dep", dep)
            if cache_key not in blob_cache:
                deps = json.loads(batch.get(dep))
                deps.pop("facts", None)
                blob_cache[cache_key] = deps
            manifest = json.loads(batch.get(man))
            pop[d] = (revn, blob_cache[cache_key], manifest.get("state"), manifest.get("sealed_at"))
    return pop


def stale_reasons(deps, cons):
    reasons = []
    comps = deps.get("components") or {}
    for name, key in (("shell", "SHELL_VERSION"), ("renderer", "RENDERER_VERSION"), ("normalisation", "NORMALISATION_VERSION"), ("reviewer_logic", "REVIEWER_LOGIC_VERSION")):
        rec = comps.get(name)
        if rec is not None and key in cons and rec != cons[key]:
            reasons.append(f"components.{name}")
    vals = deps.get("validators") or {}
    for k, v in cons.items():
        if k.startswith("Check:"):
            rec = vals.get(k[6:])
            if rec is not None and rec != v:
                reasons.append(f"validators.{k[6:]}")
    rv = deps.get("validator_version")
    if rv is not None and "VALIDATOR_VERSION" in cons and rv != cons["VALIDATOR_VERSION"]:
        reasons.append("validator_version")
    return reasons


series = []
bump_rows = []
prev_cons = constants_at(base)
prev_rev = base
for c in commits:
    H = c["H"]
    cons = constants_at(H)
    touched_candidates = run(["diff", "--name-only", f"{prev_rev}", H, "--", "candidates"])
    changed = {k: (prev_cons.get(k), cons.get(k)) for k in set(prev_cons) | set(cons) if prev_cons.get(k) != cons.get(k)}
    if changed or touched_candidates:
        pop_before = population(prev_rev)
        pop_after = population(H)
        def counts(pop, cs):
            ready = [d for d, v in pop.items() if v[2] == "READY_FOR_PROPOSAL"]
            stale = [d for d in ready if stale_reasons(pop[d][1], cs)]
            return len(pop), len(ready), len(stale)
        nb = counts(pop_before, prev_cons)
        mid = counts(pop_before, cons)  # same population, new constants: the bump's own effect
        na = counts(pop_after, cons)
        row = {
            "H": H, "h": c["h"], "date": c["date"], "subject": c["subject"],
            "bumps": {k: list(v) for k, v in sorted(changed.items())},
            "pop_before": nb[0], "ready_before": nb[1], "stale_before": nb[2],
            "stale_after_same_pop": mid[2],
            "newly_staled": [d for d in pop_before if pop_before[d][2] == "READY_FOR_PROPOSAL" and stale_reasons(pop_before[d][1], cons) and not stale_reasons(pop_before[d][1], prev_cons)],
            "pop_after": na[0], "ready_after": na[1], "stale_after": na[2],
            "candidates_touched": bool(touched_candidates),
        }
        # which constants staled each newly-staled bundle
        row["newly_staled_reasons"] = {
            d: sorted(set(stale_reasons(pop_before[d][1], cons)) - set(stale_reasons(pop_before[d][1], prev_cons)))
            for d in row["newly_staled"]
        }
        series.append(row)
        print(c["h"], c["date"][:10], len(changed), "ready", nb[1], "stale_before", nb[2], "->", mid[2], "| after pop", na[1], "stale", na[2], file=sys.stderr, flush=True)
    prev_cons = cons
    prev_rev = H
json.dump({"commits": commits, "series": series}, open(os.path.join(OUT, "hist.json"), "w"), indent=1)
print("done", len(series))
