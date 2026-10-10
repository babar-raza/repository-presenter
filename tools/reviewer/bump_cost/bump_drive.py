# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Pre/post measurement of bump commits.  usage: bump_drive.py <repo_root> <workdir> <plan.json> [workers]

plan.json: [{"h": "<full sha>", "render": 0|1, "checks": "BC-06,BC-07"|"-"}, ...]
For each commit H: export H~1 (candidates, registry, src) and H (src); run mb.py on both code trees
against the H~1 candidates; write <workdir>/results/<h8>.json with both sides.
"""
import json
import os
import subprocess
import sys
import tarfile
import io
from concurrent.futures import ThreadPoolExecutor

repo, work, plan_path = sys.argv[1:4]
workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
os.makedirs(os.path.join(work, "results"), exist_ok=True)


def export(rev, paths, dest):
    os.makedirs(dest, exist_ok=True)
    p = subprocess.run(["git", "-C", repo, "archive", rev, *paths], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[:300])
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tf:
        tf.extractall(dest, filter="data")


def one(item):
    H = item["h"]
    h8 = H[:8]
    out = os.path.join(work, "results", h8 + "." + item.get("tag", "x") + ".json")
    if os.path.exists(out):
        return h8, "cached"
    P = H + "~1"
    d = os.path.join(work, "x_" + h8)
    export(P, ["candidates", "data/registry.json", "src"], os.path.join(d, "pre"))
    export(H, ["src"], os.path.join(d, "post"))
    res = {"h": H, "item": item}
    for side in ("pre", "post"):
        o = os.path.join(d, side + ".json")
        p = subprocess.run(
            [PY, os.path.join(HERE, "bump_pair.py"), os.path.join(d, side, "src"), os.path.join(d, "pre", "candidates"),
             os.path.join(d, "pre", "data", "registry.json"), o, str(item["render"]), item["checks"]],
            capture_output=True, text=True, stdin=subprocess.DEVNULL)
        res[side + "_rc"] = p.returncode
        res[side + "_err"] = p.stderr[-500:]
        res[side] = json.load(open(o)) if os.path.exists(o) else None
    json.dump(res, open(out, "w"), indent=1)
    return h8, "ok"


plan = json.load(open(plan_path))
with ThreadPoolExecutor(workers) as ex:
    for r in ex.map(one, plan):
        print(r, flush=True)
