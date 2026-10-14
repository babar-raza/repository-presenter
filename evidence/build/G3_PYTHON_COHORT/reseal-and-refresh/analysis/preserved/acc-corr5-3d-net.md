authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr5-3d-net: aspose-3d-foss/Aspose.3D-FOSS-for-.NET (run 20261012-0f6828d3) HOLD (owner-recorded, re-confirmed)

Patch 2401 bytes (+24/-19), correct and byte-identical to the run reviewed last time; PR text clean (diagram-only template). Hold reason in `corrections.json`: `README_ADVERTISES_UNSUPPORTED_FORMATS`. Re-checked: head still 52b0f00e; `IOService.cs` lines 67 and 88 throw `NotSupportedException` for any format outside the switch; the README diagram labels U3D (lines 34, 56), RVM (36, 58), AMF and HTML5 (59). The redraw republishes those labels verbatim. Do not send without the paired README correction or issue.
