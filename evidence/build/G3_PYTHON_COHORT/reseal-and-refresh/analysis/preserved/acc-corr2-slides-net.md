authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr2-slides-net: aspose-slides-foss/Aspose.Slides-FOSS-for-.NET (registry entry 37, live head 86c441b5)

Reviewer: independent (Sonnet 5.5), read-only; did not author or repair this bundle. Method: acceptance protocol v1.1 (branch wt/lacc-acc01) adapted to a patch. Bundle: `scratchpad/lfix/out/aspose-slides-foss__Aspose.Slides-FOSS-for-.NET/` (code branch wt/lfix-fix01).

**Verdict: FIX_REQUIRED** | minor_major: MAJOR | Diagram redraw is good; the added `docs/` bullet is false and misplaced.

## 1. Confinement (replay)
- Live head: fresh `git clone --depth 1` of `aspose-slides-foss/Aspose.Slides-FOSS-for-.NET`, HEAD `86c441b5d81e707f2ea9e01b197dbb6ff7a3859b` == bundle `source_revision`; `README.original.md` is byte-identical to the live `README.md` blob (`git show HEAD:README.md`).
- Replay: applied ONLY the enumerated `corrections.json` edits (character spans, descending order; each span's `original` matched the live text) to the live blob -> bytes equal to the bundle `README.md` (sha256 `17e8ebe9d10d0d885c55a5e95469f3e62377fe963e78c9c0cd660709d108d741` matches `manifest.corrected_sha256`).
- `README.patch` (`git apply` onto the live blob in a throw-away repo with autocrlf off) reproduces `README.md` byte for byte. LF only; trailing newline preserved; no other line changed (difflib).

## 2. Edit-by-edit verification
| Edit | What it does | Check and evidence | Result |
|---|---|---|---|
| DIAGRAM_FIX L22 | At a glance redrawn LR | Labels (11), titles, edges, order identical. PNG viewed: clean (4 + 4 capability columns). The lead-in and the sentence after the fence are untouched. | PASS |
| MISSING_INFO add_doc_links L522 | inserts `- **[Documentation](docs/)** — documentation kept in this repository.` before `## Contributing` | FAIL. `docs/` in the clone holds exactly three files: `docs/media/banner-readme.png`, `docs/nuget/icon.png`, `docs/nuget/README.md` (the NuGet package readme). It is a media/package-asset folder, not documentation, so the bullet is a false/misleading claim. It is also misplaced: the live section 'Documentation and support' ends with prose and a `---` rule (section L499-521) and the bullet lands after that rule as an orphan list item directly above `## Contributing`; the section already has a `[Documentation](https://docs.aspose.com/slides/net/)` bullet, so the reader now sees two 'Documentation' entries. | FAIL (introduced) |

## 3. At a Glance render
Own render of the bundle's own `README.original.md` and `README.md` fences (not the lane's PNGs; files `scratchpad/acc2/png/Aspose.Slides-FOSS-for-.NET.before.0` and `.after.0`) with the lane's pinned mermaid package and headless Edge: before = vertical, clipped in 5 of 5 fonts; after = horizontal, clipped in 0 of 5 fonts. For the redrawn diagrams the same result holds under mermaid 11.4.1, 11.12.0, 11.17.2 and 12.1.0 (`render_multi.py`: 0 of 5 fonts clipped, horizontal, in all four). Label, title, edge and per-group order equality with the live diagram checked by own regex parse (`cmpdiag.py`, `cmpord.py`).
- Live README links `forum.aspose.com` and uses 'commercial product' wording in its Documentation and support section: inherited blocking-class wording under the protocol, unchanged by the patch.

## 4. Structure, narration, links
- `mech.py` (protocol Appendix A) run on live and corrected files with line numbers normalised: no new forbidden wording, no new dangling lead-ins, no new fence without a language, no new link failure; added links (if any) resolve in the clone. One H1; heading skeleton and order identical to live; every Navigation anchor (where Navigation exists) still resolves; no duplicate H2 introduced.
- Lane's `validation_delta.json`: `introduced: []`, live failures 257 vs corrected failures 262 (BC-07 At a Glance topology failures on a redrawn diagram are either listed under the R7 `allowed` entry or, in the lane's 19:30 regeneration of entries 30-32, no longer produced: BC-07 shows as `resolved`; README content of those regenerated bundles is byte-identical to the one reviewed, same corrected sha256). The validators did not see the defects in sections 2 and 3: they cannot judge command correctness or what a directory contains.

## 5. Findings
| id | kind | severity | section | summary |
|---|---|---|---|---|
| F1 | code_change | MAJOR | Documentation and support | add_doc_links must require markdown documentation files in the directory (not only media/package assets), append inside the existing list, and skip when the section already has a Documentation entry; until then drop the edit (the diagram hunk alone is pushable) |

## 6. Inherited from the live README (not introduced, not edited by the patch)
- No `## Navigation`, `Dependencies` or `API Reference` sections: the live README's own skeleton, which the lane correctly followed.

## 7. Could not verify
- Rendering on github.com itself (own render is headless Edge with four pinned mermaid releases and five stress fonts).
- Anything marked 'not run' above (cmake, mvn, the large Aspose.Words suite).

confidence: high for the defects named; medium for fix scope
