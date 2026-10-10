# Part of TC-COV-01 (plans: reseal-and-refresh). Owner/reviewer measurement tooling (tools/README.md):
# read-only, no provider call, writes only the files it is told to. Not imported by src/.
"""Render coverage-ranked-gaps.md from the per-unit rows."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from matching import MISSING, NO_BUNDLE, PRESENT_IN_FACTS, PRESENT_IN_README

# What an EXISTING shell-v1 section (docs/README_CONTRACT.md section 2) could render for each gap type
# without a template change. ``fits`` is yes / links-only / partial / no. ``needs`` is what the section
# would still need that is NOT a template change (a fact kind, a verified example, a disposition fix).
FEASIBILITY = {
    "readme_unit": ("depends", "the section the unit belongs to (identity, installation, quick_start, additional_examples, ...)",
                    "not a template gap: the shell has a home for each; the unit is dropped by its disposition (OMIT_UNSUPPORTED, "
                    "SUPERSEDE_REDUNDANT) or by composition. Fix is in verification (toolchain) and reconciliation, not the shell."),
    "test_command": ("yes", "development_testing (row 17: fenced commands from the build files and CI, single-target run)",
                     "a command fact (kind or attributes of build_test_asset) read from CI `run:` steps and manifests"),
    "build_command": ("yes", "development_testing (row 17) and installation source-build fallback (row 8)",
                      "the same command fact; commands are renderer-emitted, never LLM-typed"),
    "ci_matrix": ("yes", "development_testing (row 17: build files and CI) as one sentence; installation (row 8) for supported runtimes",
                  "a matrix fact per workflow axis (os, runtime versions)"),
    "github_release": ("links-only", "documentation_resources (row 15: a verified releases link) and the release sentence in development_testing (row 17)",
                       "a link_target fact for the releases page. The release BODY (highlights) has no row: rendering it is a template change"),
    "target_framework": ("yes", "installation (row 8: one sentence on supported runtimes from manifest facts) and the badges runtime floor (row 2)",
                         "package facts that list every TargetFramework / release / edition, not only the floor"),
    "test_suite": ("yes", "development_testing (row 17: sentence sizing the suite when a test-file count is verified)",
                   "build_test_asset already exists; only the per-root count and the paths to name"),
    "example_file": ("yes", "additional_examples (row 12: task-named ### headings, collapsible)", "verified example facts (execution or compile)"),
    "cli_entry": ("partial", "installation verify line (row 8) and additional_examples (row 12) for a CLI example",
                  "a cli_entry fact and an executed example; a dedicated CLI Usage section would be a plan `deviation` (row 12 note), "
                  "which the contract allows only to preserve a material inherited section"),
    "security_policy": ("links-only", "documentation_resources (row 15: repository-relative links to verified tracked docs)", "a tracked-doc link fact"),
    "contributing": ("links-only", "documentation_resources (row 15: a contributor guide)", "a tracked-doc link fact"),
    "code_of_conduct": ("links-only", "documentation_resources (row 15)", "a tracked-doc link fact"),
    "changelog": ("links-only", "documentation_resources (row 15)", "a tracked-doc link fact"),
    "doc_page": ("links-only", "documentation_resources (row 15: repository-relative links to verified tracked docs)",
                 "a tracked-doc link fact per page; page CONTENT has no row"),
    "root_doc": ("links-only", "documentation_resources (row 15: a publishing or contributor guide, implementation notes)", "a tracked-doc link fact"),
    "license_notice": ("yes", "license (row 20) and third_party_notices (row 19)", "already rendered"),
}

# Gaps the four review reports (scratchpad review-A..D.md) named; the tool must find them.
SANITY = [
    ("Font-FOSS-for-Python", "cli_entry", "aspose-font", "CLI added in 26.10.2: the sealed (older) README already runs `aspose-font` in examples, so only the CLI Usage section is lost"),
    ("Font-FOSS-for-Python", "readme_unit", "CLI Usage", "same CLI, live README section"),
    ("PDF-FOSS-for-.NET", "target_framework", "net10.0", "PDF .NET framework matrix"),
    ("PDF-FOSS-for-.NET", "target_framework", "net9.0", "PDF .NET framework matrix"),
    ("Slides-FOSS-for-.NET", "target_framework", "net10.0", "review: runs on net8.0 only, csproj has net8.0;net10.0"),
    ("Slides-FOSS-for-.NET", "contributing", "CONTRIBUTING.md", "review: Contributing/CHANGELOG/CoC/SECURITY links dropped"),
    ("Slides-FOSS-for-.NET", "security_policy", "SECURITY.md", "review: Contributing/CHANGELOG/CoC/SECURITY links dropped"),
    ("Slides-FOSS-for-Java", "security_policy", "SECURITY.md", "review: SECURITY.md route and unpublished-version warning dropped"),
    ("Slides-FOSS-for-Java", "ci_matrix", "java: 21, 25", "review: build.yml Java 21/25 matrix omitted"),
    ("Slides-FOSS-for-Java", "changelog", "CHANGELOG.md", "review: CHANGELOG link omitted"),
    ("Cells-FOSS-for-Rust", "github_release", "release", "Releases"),
    ("Slides-FOSS-for-Python", "github_release", "release", "Releases"),
]


def _by_repo_type(rows):
    d = defaultdict(list)
    for r in rows:
        d[(r["repository"], r["unit_type"])].append(r)
    return d


def render(gaps, rows, infos, types) -> str:
    bundled = [r for r, i in infos.items() if i["bundle_state"] in ("current", "source_moved")]
    current = {r for r in bundled if infos[r]["bundle_state"] == "current"}
    nobundle = [r for r, i in infos.items() if i["bundle_state"] == "NO_BUNDLE"]
    brt = _by_repo_type(rows)

    stats = []
    for t in types:
        with_units = gap_repos = miss_repos = cur_gap_repos = 0
        units = delivered = facts_only = missing = 0
        for repo in bundled:
            rs = brt.get((repo, t), [])
            if not rs:
                continue
            with_units += 1
            g = [r for r in rs if r["status"] != PRESENT_IN_README]
            m = [r for r in rs if r["status"] == MISSING]
            units += len(rs)
            delivered += len(rs) - len(g)
            facts_only += len([r for r in rs if r["status"] == PRESENT_IN_FACTS])
            missing += len(m)
            if g:
                gap_repos += 1
                cur_gap_repos += repo in current
            if m:
                miss_repos += 1
        nb_units = nb_not_live = nb_repos = 0
        for repo in nobundle:
            rs = brt.get((repo, t), [])
            nl = [r for r in rs if r["in_live_readme"] == "false"]
            nb_units += len(rs)
            nb_not_live += len(nl)
            nb_repos += bool(nl)
        stats.append({"type": t, "with_units": with_units, "gap_repos": gap_repos, "miss_repos": miss_repos,
                      "cur_gap_repos": cur_gap_repos, "units": units, "delivered": delivered,
                      "facts_only": facts_only, "missing": missing, "nb_units": nb_units, "nb_not_live": nb_not_live,
                      "nb_repos": nb_repos})
    ranked = sorted((s for s in stats if s["units"]), key=lambda s: (-s["gap_repos"], -(s["units"] - s["delivered"]), s["type"]))

    L: list[str] = []
    w = L.append
    w("# Clone-information coverage: ranked gaps (TC-COV-01)")
    w("")
    w(f"Measured {date.today().isoformat()} by `tools/reviewer/coverage_inventory/` (read-only, no provider call). "
      "Inputs: a shallow clone of each of the 36 `data/registry.json` repositories at its live default-branch head; the "
      "repository's CURRENT sealed bundle (`candidates/<r>/CURRENT` -> `facts.json`, `README.md`); the live upstream README; "
      "`gh api repos/<r>/releases/latest` (GET). Per-unit rows: `coverage-unit-table.csv`; per repository x unit type: "
      "`coverage-gap-table.csv`.")
    w("")
    w("## Population")
    w("")
    w(f"- {len(infos)} repositories; **{len(bundled)} have a CURRENT sealed bundle** ({len(current)} sealed at the live head, "
      f"{len(bundled) - len(current)} sealed at an older revision, `source_moved`); **{len(nobundle)} have no bundle** "
      f"({', '.join(r.split('/')[1] for r in nobundle)}). Ranking counts the {len(bundled)} bundled repositories; the no-bundle "
      "repositories are shown separately because there is no sealed README to compare.")
    w("- A unit is **delivered** when the sealed README carries it (`PRESENT_IN_README`), **facts only** when the pipeline "
      "ingested it but the README does not (`PRESENT_IN_FACTS`: a composition or disposition loss), **missing** when neither "
      "(`MISSING`: an extractor gap). Every match records its method (`path`, `basename`, `name`, `command`, `pattern`, "
      "`values`, `heading`, `heading+overlap`, `content_overlap`, `dir_pointer`); `dir_pointer` and `heading` are the weak ones.")
    w("")
    w("## Ranked gap types (by number of repositories affected)")
    w("")
    w(f"`affected` = bundled repositories with at least one undelivered (missing or facts-only) unit of the type, out of those that have any unit of it. `current` = the same count restricted to the {len(current)} bundles sealed at the live head (so the gap is not just age).")
    w("")
    w("| rank | gap type | repos affected | of which current-head bundles | repos with a hard MISSING | units undelivered / total | facts-only | missing |")
    w("|---|---|---|---|---|---|---|---|")
    for i, s in enumerate(ranked, 1):
        w(f"| {i} | `{s['type']}` | {s['gap_repos']} / {s['with_units']} | {s['cur_gap_repos']} | {s['miss_repos']} | "
          f"{s['units'] - s['delivered']} / {s['units']} | {s['facts_only']} | {s['missing']} |")
    w("")
    stats_by = {s["type"]: s for s in stats}
    top = ranked[:6]
    w("## Top 6: could an existing template section render it?")
    w("")
    w("Rows refer to `docs/README_CONTRACT.md` section 2. \"Template change\" means a new section id, heading or ordering "
      "(a governed RENDERER/shell change). A new fact kind, an executed example or a disposition fix is not a template change.")
    w("")
    w("| rank | gap type | fits an existing section without a template change? | which section | still needed (not a template change) |")
    w("|---|---|---|---|---|")
    for i, s in enumerate(top, 1):
        fits, where, needs = FEASIBILITY[s["type"]]
        w(f"| {i} | `{s['type']}` ({s['gap_repos']} repos) | **{fits}** | {where} | {needs} |")
    w("")
    rest = [s for s in ranked[6:] if s["gap_repos"]]
    if rest:
        w("Remaining gap types (same judgement):")
        w("")
        for s in rest:
            fits, where, needs = FEASIBILITY[s["type"]]
            w(f"- `{s['type']}` ({s['gap_repos']} repos): **{fits}**; {where}.")
        w("")
    thin = [s["type"] for s in ranked if FEASIBILITY[s["type"]][0] in ("yes", "links-only") and s["type"] not in ("readme_unit", "license_notice")]
    gapset = {t: {r for r in bundled if any(x["status"] != PRESENT_IN_README for x in brt.get((r, t), []))} for t in thin}
    covered: set[str] = set()
    steps = []
    remaining = list(thin)
    while remaining:
        best = max(remaining, key=lambda t: (len(gapset[t] - covered), len(gapset[t])))
        if not gapset[best] - covered:
            break
        covered |= gapset[best]
        steps.append((best, len(gapset[best]), len(covered)))
        remaining.remove(best)
    facts_only_types = [t for t in thin if stats_by[t]["facts_only"] and not stats_by[t]["missing"]]
    extractor_types = [t for t in thin if stats_by[t]["missing"]]
    w("## Cut-1 thin slice")
    w("")
    w("Gap types an existing section can already render (`yes` or `links-only`): "
      + ", ".join(f"`{t}`" for t in thin) + ". Greedy cover of the bundled repositories (each step adds the type touching the most "
      "not-yet-covered repositories):")
    w("")
    w("| step | add gap type | repos it touches | cumulative repos touched |")
    w("|---|---|---|---|")
    for i, (t, n, cum) in enumerate(steps, 1):
        w(f"| {i} | `{t}` | {n} | {cum} / {len(bundled)} |")
    w("")
    w(f"- Needs only a renderer/plan change (the facts already exist, the README just does not carry them): "
      + ", ".join(f"`{t}`" for t in facts_only_types) + ".")
    w("- Needs an extractor fact first (at least one unit is not in `facts.json` at all), still no template change: "
      + ", ".join(f"`{t}`" for t in extractor_types) + ".")
    w("- Left for cut 2 (needs a template change, or a verified example the renderer cannot yet produce): release-note BODY and "
      "doc-page CONTENT (no section) and a dedicated CLI Usage section (only a plan `deviation` today). `readme_unit` losses are a "
      "verification/reconciliation matter, not a shell matter.")
    w("")
    w("## Facts-only rows: the loss is after extraction")
    w("")
    fo = [s for s in ranked if s["facts_only"]]
    w("Types where the pipeline already holds the information in `facts.json` but the README does not carry it "
      "(a renderer/plan fix, no extractor work): " + ", ".join(f"`{s['type']}` ({s['facts_only']} units)" for s in fo) + ".")
    w("")
    w("## Repositories without a bundle (information in the clone that the live README does not carry either)")
    w("")
    w("| gap type | no-bundle repos with a unit absent from the live README | units absent / total |")
    w("|---|---|---|")
    for s in ranked:
        if s["nb_units"]:
            w(f"| `{s['type']}` | {s['nb_repos']} / {len(nobundle)} | {s['nb_not_live']} / {s['nb_units']} |")
    w("")
    w("## Sanity check against the four review reports")
    w("")
    w("| repository | unit type | unit | status in this measurement | what the reviews reported |")
    w("|---|---|---|---|---|")
    for repo_part, t, unit_part, note in SANITY:
        hits = [r for r in rows if repo_part in r["repository"] and r["unit_type"] == t and unit_part in r["unit"]]
        if not hits:
            w(f"| {repo_part} | {t} | {unit_part} | NOT FOUND | {note} |")
        for r in hits[:2]:
            w(f"| {repo_part} | {t} | {r['unit'][:50]} | {r['status']} ({r['method'] or '-'}) | {note} |")
    w("")
    w("## Caveats")
    w("")
    w("- Matching is lexical and approximate (see the method column); a `MISSING` can be an LLM paraphrase the matcher cannot "
      "see, a `PRESENT_IN_README` by `heading` or `dir_pointer` can be a pointer without the information. Counts rank prevalence; "
      "they are not a quality score.")
    w("- A bundle sealed at an older revision (`source_moved`) is compared with the live head: part of its gap is age, which a "
      "reseal closes; the `current` column isolates the gaps that remain on a head-current bundle.")
    w("- Sample programs (`sample_*`, `examples/`, `_examples/`), test runners and benchmarks are excluded from `cli_entry`; "
      "build and test commands are reduced to tool + verb, including commands implied by a manifest (marked `convention` in the detail column).")
    w("")
    return "\n".join(L) + "\n"
