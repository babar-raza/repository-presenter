authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr6-font-python: aspose-font-foss/Aspose.Font-FOSS-for-Python (run 20261012-90a5a934) FIX_REQUIRED (PR text only; patch verified)

Not in the owner's first wave. Patch 387 bytes (+5/-0), head adf4885a (live today), `README.original.md` equals the live blob, patch applies byte for byte, idempotent, deterministic. One edit: a new `## Documentation & Resources` section (two links) before `## Development`, line 547. No diagram edit (the only content-only PR).

## Patch: verified

- `CHANGELOG.md` (1374 bytes, "All notable public changes ... are recorded here") and `SECURITY.md` (731 bytes, "Reporting a Vulnerability") exist at the pinned revision (fresh shallow clone), non-empty, and read like their labels ("release history", "how to report a vulnerability").
- The README names neither file anywhere else (whole-file grep); the section sits at depth 0 between `## MCP Server` and `## Development`; no new broken anchors; the README has no contents list.
- Delta: live 178, corrected 178 (identical per check), introduced none.

## Defect in the generated text

The lead says: "The README has no `Documentation & Resources` section. We added one that states what the repository's own files declare (cited below), with an item for it in the contents list." This README has no contents list and the patch adds no contents item (one edit, `missing_sections` / `MISSING_SECTION`, no `MISSING_INFO`). The sentence is fixed text for every inserted section (`_lead`, branch `sections`) and is right only for Cells-.NET and Cells-Cpp, whose `Navigation` item is a second edit. "states what the repository's own files declare" is also an odd description of two links.

Fix (generator): print the contents-list clause only when a contents item is added; describe a links section as "links to files the repository holds". Suggested title: `docs(readme): add Changelog and Security policy links in a Documentation & Resources section` (92 characters); lead: "The README does not link `CHANGELOG.md` or `SECURITY.md`, which the repository holds. We add a short `Documentation & Resources` section that links both."
