authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr5-tex-python: aspose-tex-foss/Aspose.TeX-FOSS-for-Python (run 20261012-0f6828d3) HOLD (owner-recorded, re-confirmed)

Patch 1620 bytes (+13/-10), correct and byte-identical to the run reviewed last time; PR text clean (diagram-only template). Hold reason: `UPSTREAM_SOURCE_DOES_NOT_PARSE`. Re-checked: head still 181015d2; `ast.parse` fails on 102 of 119 `.py` files in the clone. The recorded `hold_reason` text says "35 of 45 source files" beside "102 of 119 .py files"; neither number is in the PR text. Do not send without the paired upstream-defect issue.
