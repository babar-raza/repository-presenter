# Part of docs/investigations/13-bump-cost-and-recheck-design.md (2026-10-10). Owner/reviewer
# measurement tooling (tools/README.md): read-only, no provider call, no network, writes only
# the files it is told to. Not imported by src/.
"""Assemble evidence/bump-cost/*.csv and its manifest from the raw measurement outputs.

usage: build_evidence.py <work> <outdir>

<work> holds, produced by the sibling scripts (each documents its own usage):
  timeline.json   bump_timeline.py          hist.json   bump_history.py
  now.json        current_recheck.py        today.json  current_records.py
  status.json     `repository-presenter status --stale --json`
  inh.json        inherited_probe.py        rev.json    reviewer_probe.py
  w/results/*.m.json   bump_drive.py (pre/post runs of each bump commit; analyze_pairs.py summarises)
"""
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

work, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
L = lambda n: json.load(open(os.path.join(work, n), encoding="utf-8"))
timeline = L("timeline.json")  # [date, H, key, old, new, subject]
hist = L("hist.json")["series"]
now = L("now.json")["bundles"]
today = L("today.json")
status = L("status.json")
inh = L("inh.json")["bundles"]
rev = L("rev.json")["bundles"]
by_hist = {r["H"]: r for r in hist}
results = {}
for f in glob.glob(os.path.join(work, "w", "results", "*.m.json")):
    r = json.load(open(f))
    results[r["h"]] = r

CLAIM = {
    "9596a923": "re-checked, never blanket-invalidated (reviewer_logic reopens COMPOSING)",
    "ef2ee5e1": "silent about sealed bundles",
    "84546aa0": "silent about sealed bundles (recover= path)",
    "fadb0017": "silent about sealed bundles (repair path only)",
    "0f523a34": "version bump discipline caught the change; no statement on sealed bundles",
    "d8b3a9de": "silent about sealed bundles (loosens an identifier check)",
    "ffb1476f": "silent about sealed bundles (recover= path)",
    "a14a22fe": "silent about sealed bundles (packet content)",
    "03110a4b": "silent about sealed bundles (repair lever)",
    "ae6c4373": "silent about sealed bundles (paraphrase ratio)",
    "af08a2ea": "sealed candidates reopen VALIDATING/REVIEWING; reseal lanes cover the backlog",
    "d842b7b0": "every sealed candidate re-checks via VALID_UPDATE_AVAILABLE, never blanket invalidation; zero false positives on all 34 sealed READMEs",
    "12eefef1": "ACCEPTANCE_PROFILE_VERSION stays 1 because a bump would reopen REVIEWING for every sealed candidate; sealed candidates record a pending update with proof retained",
    "1c188006": "feedback-only (message text); no statement on sealed bundles",
    "268faac3": "changes bytes of any candidate whose required section has no supporting fact; sealed candidates must read as stale",
    "2dba63e8": "no sealed plan changes; of 3017 units in candidates/ none changes verdict",
    "48201b67": "19 sealed READMEs carry the lowercase phrase; no sealed bundle edited or re-sealed",
    "599659d2": "silent about sealed bundles (schema empty-enum)",
    "761f3b30": "24 sealed bundles recorded in KNOWN_BLOCKED_STALE (their fresh render differs by design)",
    "7e567085": "independent_review requests re-key for sealed bundles, which are re-sealed, never blanket-invalidated",
    "7e56716e": "silent about sealed bundles (abbreviation spelling in titles)",
    "8f30d5d5": "silent about sealed bundles (.NET install fallback)",
    "a47336f6": "silent about sealed bundles (loosens the strays check)",
    "cdaf793d": "silent about sealed bundles (loosens BC-06 scheme test)",
    "ce355281": "silent about sealed bundles (carry rule for development_testing)",
    "38defe4f": "measured offline: 23 of 29 sealed bundles have scope supersessions and 19 carry an uncarried unit; sections re-authored at next seal; sealed bundles not rewritten",
    "65b96971": "sealed candidates held 93 deferred units; classes derived from them",
    "75b5cf73": "22 of 29 CURRENT bundles would newly fail BC-07; none invalidated; each re-renders to a passing document with no provider call",
    "89c9f2af": "bundles sealed under 6 read as stale and record a pending presentation update with proof retained; nothing is invalidated",
    "9cc25fc0": "silent about sealed bundles (repair packet)",
    "2d380177": "silent about sealed bundles (re-ask text, recovery path)",
    "5e5cb3c7": "renderer: the composed page's own text changes; validator: advisory_notes content changes",
    "99320d8a": "behaviour unchanged from the original commit; versions re-derived from main",
    "a1e6f797": "changes what BC-07 accepts (loosens: zero badges allowed when no badge-worthy fact)",
    "ae8620a4": "silent about sealed bundles (citable set fix)",
    "cc5a4e9e": "silent about sealed bundles (repair route)",
    "feab4437": "typed second-reader trigger; sealed bundles carry the old second_reader shape",
    "5cffa343": "silent about sealed bundles (error message names the real section)",
    "8faea803": "only a repository's next extraction run sees the split; no already-sealed candidate's unit numbering changes retroactively",
    "14cdd181": "silent about sealed bundles (restated absence claims)",
}
MEASURE_NOTE = {
    "REVIEWER_LOGIC_VERSION": "reviewer fold stack; replay needs the raw review reads (retained in 6 of 30 CURRENT bundles); cumulative replay v14/15 -> v18 on those bundles: identical verdict and findings",
    "ACCEPTANCE_PROFILE_VERSION": "label only; no blocking check reads the profile",
    "CONTRACT_VERSION": "label only; the checks are versioned separately",
    "INHERITED_UNITS_VERSION": "extraction scope; offline regeneration from the original README (reverse of README.patch)",
}

def pr_of(subject):
    m = re.search(r"\(#(\d+)\)\s*$", subject)
    return m.group(1) if m else ""

# ---------- bump_timeline.csv
with open(os.path.join(outdir, "bump_timeline.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["date", "commit", "pr", "constant", "old", "new", "subject"])
    for d, H, k, o, n, s in timeline:
        w.writerow([d, H[:8], pr_of(s), k, o, n, s])

# ---------- bump_cost.csv  (one row per bump commit)
groups = {}
for d, H, k, o, n, s in timeline:
    g = groups.setdefault(H, {"date": d, "subject": s, "k": {}})
    g["k"][k] = (o, n)
rows = []
for H, g in groups.items():
    h8 = H[:8]
    kinds = []
    ks = g["k"]
    if "RENDERER_VERSION" in ks: kinds.append("renderer")
    if "NORMALISATION_VERSION" in ks: kinds.append("normalisation")
    if "REVIEWER_LOGIC_VERSION" in ks: kinds.append("reviewer_logic")
    if any(x.startswith("Check:") for x in ks) or "VALIDATOR_VERSION" in ks: kinds.append("validator")
    if "CONTRACT_VERSION" in ks or "ACCEPTANCE_PROFILE_VERSION" in ks or "PROFILE_VERSION" in ks: kinds.append("contract_label")
    if "INHERITED_UNITS_VERSION" in ks: kinds.append("extraction_environment")
    desc = "; ".join(f"{k.replace('_VERSION','').replace('Check:','')} {o or '-'}->{n or '-'}" for k, (o, n) in sorted(ks.items()))
    hs = by_hist.get(H)
    pop = hs["pop_before"] if hs else ""
    ready = hs["ready_before"] if hs else ""
    sb = hs["stale_before"] if hs else ""
    sa = hs["stale_after_same_pop"] if hs else ""
    newly = len(hs["newly_staled"]) if hs else ""
    res = results.get(H)
    meas = "not measured"
    measured_n = changed = tightened = loosened = text_only = unchanged = ""
    what = ""
    value_changed = "no" if h8 == "12eefef1" else "yes"
    if res and res.get("pre") and res.get("post"):
        pre, post = res["pre"], res["post"]
        item = res["item"]
        n_ok = n_tight = n_loose = n_text = 0
        names = {}
        def bump(label):
            names[label] = names.get(label, 0) + 1
        for b in pre:
            a, c = pre[b], post.get(b, {})
            if a.get("error") or c.get("error"):
                continue
            n_ok += 1
            tight = loose = text = False
            if item["render"] and a.get("render_sha") != c.get("render_sha"):
                bump("render bytes differ"); tight = True  # a different README is a content change either way
            for cid in sorted(set(a.get("checks") or {}) | set(c.get("checks") or {})):
                ca = (a.get("checks") or {}).get(cid)
                cb = (c.get("checks") or {}).get(cid)
                if ca is None:
                    if cb["verdict"] == "FAIL":
                        bump(cid + " new check fails"); tight = True
                    continue
                if cb is None:
                    continue
                if ca["verdict"] != cb["verdict"]:
                    if cb["verdict"] == "FAIL":
                        bump(cid + " PASS->FAIL"); tight = True
                    else:
                        bump(cid + " FAIL->PASS"); loose = True
                elif ca["h"] != cb["h"]:
                    if cb["verdict"] == "FAIL" and cb["n"] > ca["n"]:
                        bump(cid + " more failures"); tight = True
                    elif cb["n"] < ca["n"]:
                        bump(cid + " fewer failures"); loose = True
                    else:
                        bump(cid + " detail text only"); text = True
            n_tight += tight
            n_loose += (loose and not tight)
            n_text += (text and not tight and not loose)
        measured_n, tightened, loosened, text_only = n_ok, n_tight, n_loose, n_text
        changed = n_tight + n_loose
        unchanged = n_ok - changed - n_text
        what = "; ".join(f"{k}: {v}" for k, v in sorted(names.items())) or "no difference"
        dims = (["render"] if item["render"] else []) + [c for c in item["checks"].split(",") if c != "-"]
        meas = "re-run pre/post: " + ",".join(dims)
    else:
        for k in ks:
            if k in MEASURE_NOTE:
                meas = "not replayable offline for the historical population: " + MEASURE_NOTE[k]
        if h8 == "12eefef1":
            meas = "not a bump: ACCEPTANCE_PROFILE_VERSION became an alias of PROFILE_VERSION; the value stayed 1"
    if h8 == "8faea803":
        what = "regeneration on today's 30 bundles: 4 differ (2 of the 24 recording v1, 2 recording none)"
    if h8 == "af08a2ea":
        pop, ready = 26, 24
    if h8 == "8faea803":
        pop, ready = 30, 29
    if h8 == "12eefef1":
        pop, ready = 27, 26
    rows.append({
        "date": g["date"], "commit": h8, "pr": pr_of(g["subject"]), "kinds": "+".join(kinds), "bumps": desc,
        "value_changed": value_changed,
        "population_before": pop, "ready_before": ready, "stale_by_record_before": sb, "stale_by_record_after": sa,
        "newly_staled_by_record": newly, "measurement": meas, "bundles_measured": measured_n,
        "bundles_outcome_changed": changed, "of_which_stricter": tightened, "of_which_looser_only": loosened,
        "detail_text_only": text_only, "bundles_unchanged": unchanged, "what_changed": what,
        "message_claim": CLAIM.get(h8, ""), "subject": g["subject"],
    })
rows.sort(key=lambda r: (r["date"], r["commit"]))
with open(os.path.join(outdir, "bump_cost.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

# ---------- bump_cost_per_bundle.csv (long form: only the cells that differ between the pre and post run;
# every other measured bundle of a commit is unchanged, and bump_cost.csv counts them)
with open(os.path.join(outdir, "bump_cost_per_bundle.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["commit", "bundle", "manifest_state", "dimension", "pre", "post", "changed"])
    for H, res in sorted(results.items(), key=lambda kv: groups[kv[0]]["date"]):
        if not (res.get("pre") and res.get("post")):
            continue
        for b in sorted(res["pre"]):
            a, c = res["pre"][b], res["post"].get(b, {})
            if a.get("error") or c.get("error"):
                w.writerow([H[:8], b, a.get("state", ""), "error", (a.get("error") or "")[:80], (c.get("error") or "")[:80], ""])
                continue
            if res["item"]["render"] and a["render_sha"] != c["render_sha"]:
                w.writerow([H[:8], b, a.get("state"), "render", a["render_sha"][:12], c["render_sha"][:12], 1])
            for cid in sorted(set(a.get("checks") or {}) | set(c.get("checks") or {})):
                ca = (a.get("checks") or {}).get(cid)
                cb = (c.get("checks") or {}).get(cid)
                if ca is None:
                    if cb["verdict"] == "FAIL":
                        w.writerow([H[:8], b, a.get("state"), cid, "(absent)", cb["verdict"] + ":" + cb["h"], 1])
                elif cb is None:
                    w.writerow([H[:8], b, a.get("state"), cid, ca["verdict"], "(absent)", 1])
                elif (ca["verdict"], ca["h"]) != (cb["verdict"], cb["h"]):
                    w.writerow([H[:8], b, a.get("state"), cid, ca["verdict"] + ":" + ca["h"], cb["verdict"] + ":" + cb["h"], 1])

# ---------- status_series.csv
with open(os.path.join(outdir, "status_series.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["date", "commit", "bumps", "population_before", "ready_before", "stale_before", "stale_after_same_population", "newly_staled_by_bump", "population_after", "ready_after", "stale_after", "candidates_changed", "subject"])
    for r in hist:
        b = ";".join(f"{k.replace('_VERSION','').replace('Check:','')}:{v[0]}>{v[1]}" for k, v in r["bumps"].items())
        w.writerow([r["date"][:10], r["h"], b, r["pop_before"], r["ready_before"], r["stale_before"], r["stale_after_same_pop"], len(r["newly_staled"]), r["pop_after"], r["ready_after"], r["stale_after"], int(r["candidates_touched"]), r["subject"]])

# ---------- current_state_per_bundle.csv
cur = today["current"]
stale_by_dir = {s["repository_dir"]: s["reasons"] for s in status["stale"]}
header = ["bundle", "revision", "manifest_state", "sealed_at", "differing_records_stale_rule", "normalisation", "renderer", "reviewer_logic", "shell", "validator_version", "checks_behind", "contract_version", "acceptance_profile_version", "inherited_units_version", "prompts_changed", "dry_run_state", "dry_run_scopes", "render_equal", "render_diff_lines", "fail_on_sealed_bytes", "fail_on_rerendered_bytes", "recheck_class"]
out_rows = []
for b, t in sorted(today["bundles"].items()):
    rec = t["recorded"]
    comps = rec["components"] or {}
    n = now.get(b, {})
    vn = n.get("validation_now", {})
    sealed_fail = sorted(k for k, v in (vn.get("sealed_bytes") or {}).items() if v["verdict"] == "FAIL")
    rr = vn.get("rerendered")
    rr_fail = sealed_fail if rr == "same_as_sealed_bytes" else sorted(k for k, v in (rr or {}).items() if v["verdict"] == "FAIL")
    equal = n.get("render_equal")
    if not t["changed"] and equal:
        klass = "CURRENT"
    elif equal and not sealed_fail:
        klass = "RECHECK_CURRENT"
    elif not rr_fail:
        klass = "UPDATE_RERENDER_ONLY"
    else:
        klass = "UPDATE_RECOMPOSE"
    reasons = stale_by_dir.get(b, [])
    behind = sorted(x.split(" ")[0].replace("validators.", "") for x in reasons if x.startswith("validators."))
    def dv(c):
        return f"{comps.get(c)}->{cur['components'][c]}" if comps.get(c) != cur["components"][c] else "same"
    out_rows.append([
        b, t["revision"], t["state"], t["sealed_at"], len(reasons), dv("normalisation"), dv("renderer"), dv("reviewer_logic"), dv("shell"),
        f"{rec['validator_version']}->{cur['validator_version']}" if rec["validator_version"] != cur["validator_version"] else "same",
        " ".join(behind), f"{rec['contract_version']}->{cur['contract_version']}" if rec["contract_version"] != cur["contract_version"] else "same",
        f"{rec['acceptance_profile_version']}->{cur['acceptance_profile_version']}" if rec["acceptance_profile_version"] != cur["acceptance_profile_version"] else "same",
        f"{rec['inherited_units_version']}->{cur['environment']['inherited_units_version']}" if rec["inherited_units_version"] != cur["environment"]["inherited_units_version"] else "same",
        " ".join(sorted(c["dependency"].split(".", 1)[1] for c in t["changed"] if c["dependency"].startswith("prompts."))),
        t["would_become"], " ".join(t["scopes"]), equal, n.get("render_diff_lines", 0), " ".join(sealed_fail), " ".join(rr_fail), klass,
    ])
with open(os.path.join(outdir, "current_state_per_bundle.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(header)
    w.writerows(out_rows)

# ---------- recheck_probes.csv (inherited units + reviewer replay, per bundle)
with open(os.path.join(outdir, "recheck_probes.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["bundle", "probe", "result", "detail"])
    for b in sorted(today["bundles"]):
        i = inh.get(b, {})
        w.writerow([b, "inherited_units_regeneration", "identical" if i.get("identical") else ("differs" if "identical" in i else "error"),
                    f"sealed={i.get('sealed_units')} regenerated={i.get('regen_units')} added={i.get('n_added')} removed={i.get('n_removed')} altered={i.get('n_altered')}"])
        r = rev.get(b)
        if r:
            w.writerow([b, "reviewer_replay", "identical" if r.get("match_any_order") else "differs", f"sealed_logic={r.get('sealed_logic_version')} replay_logic={L('rev.json')['reviewer_logic_version']} reads={r.get('reads')}"])
        else:
            w.writerow([b, "reviewer_replay", "not_replayable", "no raw independent_review reads in the bundle"])

# ---------- manifest
files = sorted(glob.glob(os.path.join(outdir, "*.csv")))
man = {
    "schema_version": 1,
    "kind": "bump_cost_measurement",
    "recorded_at": "2026-10-10",
    "control_revision": subprocess.run(["git", "merge-base", "HEAD", "origin/main"], capture_output=True, text=True).stdout.strip(),
    "window": "commits since 2026-09-19 on the first-parent history of main",
    "redaction": "no credentials, tokens or provider output; fields are version literals, commit ids, bundle directory names, counts and check verdicts",
    "files": {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in files},
}
with open(os.path.join(outdir, "manifest.json"), "w", newline="\n") as handle:
    json.dump(man, handle, indent=1, sort_keys=True)
    handle.write("\n")
print("wrote", len(files), "csv;", len(rows), "bump rows")
