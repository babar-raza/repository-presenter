# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
import glob
import json
import os
import sys

SP = os.environ.get("BUMP_COST_OUT", os.getcwd())
out = []
for f in sorted(glob.glob(SP + "/w/results/*.m.json")):
    r = json.load(open(f))
    pre, post = r["pre"], r["post"]
    item = r["item"]
    h8 = r["h"][:8]
    if pre is None or post is None:
        out.append({"h": h8, "error": (r.get("pre_err") or "")[-200:] + (r.get("post_err") or "")[-200:]})
        continue
    n = len(pre)
    ready = [k for k, v in pre.items() if v.get("state") == "READY_FOR_PROPOSAL"]
    render_changed = []
    check_changed = {}
    errs = 0
    for k in pre:
        a, b = pre[k], post.get(k, {})
        if a.get("error") or b.get("error"):
            errs += 1
            continue
        if item["render"] and a.get("render_sha") != b.get("render_sha"):
            render_changed.append(k)
        for cid, ca in (a.get("checks") or {}).items():
            cb = (b.get("checks") or {}).get(cid)
            if cb is None:
                continue
            if (ca["verdict"], ca["h"]) != (cb["verdict"], cb["h"]):
                check_changed.setdefault(cid, []).append((k, ca["verdict"], cb["verdict"]))
    out.append({
        "h": h8, "n": n, "ready": len(ready), "errors": errs,
        "render_changed": len(render_changed) if item["render"] else None,
        "render_changed_names": render_changed,
        "check_changed": {c: [(x[0][:40], x[1], x[2]) for x in v] for c, v in check_changed.items()},
    })
json.dump(out, open(SP + "/analysis.json", "w"), indent=1)
for o in out:
    print(o["h"], {k: v for k, v in o.items() if k not in ("h", "render_changed_names", "check_changed")},
          {c: (len(v), sorted({(x[1], x[2]) for x in v})) for c, v in o.get("check_changed", {}).items()})
