# Part of TC-COV-01 (plans: reseal-and-refresh). Owner/reviewer measurement tooling (tools/README.md):
# read-only, no provider call, writes only the files it is told to. Not imported by src/.
"""Measure, for every registry repository, which clone information the CURRENT sealed bundle carries.

usage: run.py --clones <dir of <owner>__<name> shallow clones> --out <analysis dir>
              [--registry data/registry.json] [--candidates candidates] [--releases <cache dir>]
              [--only owner/name ...]

Network use is limited to read-only ``gh api repos/<r>/releases/latest`` GET requests (cached under
--releases); the clones are made beforehand with ``git clone --depth 1``. Nothing is written to any
repository. Output: coverage-unit-table.csv, coverage-gap-table.csv, coverage-ranked-gaps.md, manifest.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inventory  # noqa: E402
import ranking  # noqa: E402
from matching import (MISSING, NO_BUNDLE, PRESENT_IN_FACTS, PRESENT_IN_README, Corpus, find_hit,  # noqa: E402
                      norm_heading, status_of)

UNIT_TYPES = ["readme_unit", "doc_page", "root_doc", "changelog", "github_release", "contributing", "security_policy",
              "code_of_conduct", "cli_entry", "target_framework", "ci_matrix", "example_file", "test_suite",
              "license_notice", "build_command", "test_command"]
LIST_CAP = 12


def load_bundle(candidates: Path, key: str):
    d = candidates / key
    cur = d / "CURRENT"
    if not cur.is_file():
        return None
    rev = cur.read_text(encoding="utf-8").strip()
    bd = d / rev
    if not (bd / "facts.json").is_file() or not (bd / "README.md").is_file():
        return None
    facts = json.loads((bd / "facts.json").read_text(encoding="utf-8"))
    disp = {}
    if (bd / "dispositions.json").is_file():
        disp = {x["unit_id"]: x for x in json.loads((bd / "dispositions.json").read_text(encoding="utf-8")).get("dispositions", [])}
    return {"revision": rev, "source_revision": facts.get("source_revision"), "facts": facts["facts"],
            "readme": (bd / "README.md").read_text(encoding="utf-8"), "dispositions": disp}


def _flat(v) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def fact_corpora(facts: list[dict]) -> tuple[Corpus, Corpus, list[dict]]:
    """(extracted facts, inherited README units, inherited fact records). public_symbol facts are left
    out of the text: thousands of API names would let any short identifier match by accident."""
    extracted, inherited, units = [], [], []
    for f in facts:
        if f["kind"] == "public_symbol":
            continue
        parts = [_flat(f.get("value")), _flat(f.get("attributes"))]
        parts += [_flat(e.get("path")) + " " + _flat(e.get("detail")) for e in f.get("evidence") or []]
        (inherited if f["kind"] == "inherited_unit" else extracted).append("\n".join(parts))
        if f["kind"] == "inherited_unit":
            units.append(f)
    return Corpus("facts", "\n".join(extracted)), Corpus("inherited", "\n".join(inherited)), units


def get_release(repo: str, cache: Path | None) -> dict | None:
    cf = cache / (repo.replace("/", "__") + ".json") if cache else None
    if cf and cf.is_file():
        return json.loads(cf.read_text(encoding="utf-8")) or None
    r = subprocess.run(["gh", "api", f"repos/{repo}/releases/latest"], capture_output=True, text=True, encoding="utf-8")
    data = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    if cf:
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps({k: data.get(k) for k in ("tag_name", "name", "body", "published_at")} if data else {}), encoding="utf-8")
    return data or None


def inherited_disposition(heading: str, inherited_units, dispositions) -> str:
    """Dispositions the pipeline gave the inherited README units under this section heading."""
    counts: dict[str, int] = {}
    for f in inherited_units:
        if norm_heading(_flat((f.get("attributes") or {}).get("section"))) != heading and not (
                f["id"].endswith(".heading") and norm_heading(_flat(f.get("value"))) == heading):
            continue
        d = dispositions.get(f["id"])
        k = f"{d['disposition']}->{d.get('destination_section') or '-'}" if d else "no_disposition"
        counts[k] = counts.get(k, 0) + 1
    return "; ".join(f"{k} x{v}" for k, v in sorted(counts.items()))


def measure_repo(entry: dict, clone: Path, candidates: Path, releases: Path | None) -> tuple[list[dict], dict]:
    repo = entry["repository"]
    key = repo.replace("/", "__")
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    units, meta = inventory.inventory(clone, get_release(repo, releases))
    bundle = load_bundle(candidates, key)
    live = Corpus("live_readme", meta["readme_text"], chunked=True)
    if bundle:
        sealed = Corpus("sealed_readme", bundle["readme"], chunked=True)
        extracted, inherited, inh_units = fact_corpora(bundle["facts"])
    rows = []
    for u in units:
        in_live = None if u.unit_type == "readme_unit" else bool(find_hit(u, live))
        row = {"repository": repo, "unit_type": u.unit_type, "unit": u.name, "status": "", "size": u.size, "detail": u.detail[:240],
               "in_live_readme": "n/a" if in_live is None else str(in_live).lower(), "matched_in": "", "method": "", "score": "", "disposition": ""}
        if not bundle:
            row["status"] = NO_BUNDLE
        else:
            r_hit = find_hit(u, sealed)
            f_hit = find_hit(u, inherited if u.unit_type == "readme_unit" else extracted)
            row["status"] = status_of(r_hit, f_hit)
            hit = r_hit or f_hit
            if hit:
                row["method"], row["score"] = hit[0], f"{hit[1]:.2f}"
                row["matched_in"] = "sealed_readme" if r_hit else "facts"
            if u.unit_type == "readme_unit" and row["status"] != PRESENT_IN_README:
                row["disposition"] = inherited_disposition(u.heading, inh_units, bundle["dispositions"])
        rows.append(row)
    info = {"repository": repo, "live_head": head, "bundle_revision": bundle["source_revision"] if bundle else "",
            "bundle_state": ("NO_BUNDLE" if not bundle else ("current" if bundle["source_revision"] == head else "source_moved")),
            "readme": meta["readme"] or "", "files": meta["files"]}
    return rows, info


def _names(rows: list[dict]) -> str:
    names = [r["unit"] for r in rows]
    out = " | ".join(names[:LIST_CAP])
    return out + (f" | (+{len(names) - LIST_CAP} more)" if len(names) > LIST_CAP else "")


def gap_rows(all_rows: list[dict], infos: dict[str, dict]) -> list[dict]:
    out = []
    for repo, info in infos.items():
        for t in UNIT_TYPES:
            rs = [r for r in all_rows if r["repository"] == repo and r["unit_type"] == t]
            by = lambda s: [r for r in rs if r["status"] == s]
            methods: dict[str, int] = {}
            for r in rs:
                if r["method"]:
                    methods[r["method"]] = methods.get(r["method"], 0) + 1
            not_live = [r for r in rs if r["in_live_readme"] == "false"]
            out.append({
                "repository": repo, "bundle_state": info["bundle_state"], "live_head": info["live_head"][:12],
                "bundle_source_revision": info["bundle_revision"][:12], "unit_type": t, "units": len(rs),
                "present_in_readme": len(by(PRESENT_IN_README)), "present_in_facts_only": len(by(PRESENT_IN_FACTS)),
                "missing": len(by(MISSING)), "no_bundle": len(by(NO_BUNDLE)),
                "not_in_live_readme": len(not_live) if t != "readme_unit" else "n/a",
                "missing_names": _names(by(MISSING) + by(NO_BUNDLE)) if t != "readme_unit" or not info["bundle_state"] == "NO_BUNDLE" else "",
                "facts_only_names": _names(by(PRESENT_IN_FACTS)),
                "match_methods": ";".join(f"{k}:{v}" for k, v in sorted(methods.items())),
            })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clones", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--registry", default="data/registry.json")
    ap.add_argument("--candidates", default="candidates")
    ap.add_argument("--releases", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--control-revision", default="")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    entries = json.loads(Path(a.registry).read_text(encoding="utf-8"))["entries"]
    all_rows: list[dict] = []
    infos: dict[str, dict] = {}
    for e in entries:
        if a.only and e["repository"] not in a.only:
            continue
        clone = Path(a.clones) / e["repository"].replace("/", "__")
        if not clone.is_dir():
            infos[e["repository"]] = {"repository": e["repository"], "live_head": "", "bundle_revision": "", "bundle_state": "NO_CLONE", "readme": "", "files": 0}
            continue
        rows, info = measure_repo(e, clone, Path(a.candidates), Path(a.releases) if a.releases else None)
        all_rows += rows
        infos[e["repository"]] = info
        print(f"{e['repository']}: {len(rows)} units, bundle={info['bundle_state']}", file=sys.stderr)
    gaps = gap_rows(all_rows, infos)
    write_csv(out / "coverage-unit-table.csv", all_rows)
    write_csv(out / "coverage-gap-table.csv", gaps)
    (out / "coverage-ranked-gaps.md").write_text(ranking.render(gaps, all_rows, infos, UNIT_TYPES), encoding="utf-8", newline="\n")
    files = ["coverage-unit-table.csv", "coverage-gap-table.csv", "coverage-ranked-gaps.md"]
    manifest = {"kind": "clone_information_coverage", "recorded_at": date.today().isoformat(), "control_revision": a.control_revision,
                "repositories": {r: {"live_head": i["live_head"], "bundle_source_revision": i["bundle_revision"], "bundle_state": i["bundle_state"]}
                                 for r, i in infos.items()},
                "files": {f: hashlib.sha256((out / f).read_bytes()).hexdigest() for f in files},
                "redaction": "no credentials, tokens or provider output; fields are repository paths, counts, unit names and revision ids",
                "schema_version": 1}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
