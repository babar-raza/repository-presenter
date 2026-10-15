authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr6-tex-python: aspose-tex-foss/Aspose.TeX-FOSS-for-Python (run 20261012-90a5a934) HOLD (owner-recorded, re-confirmed)

Patch 1620 bytes (+13/-10), diagram only, byte-identical to the run reviewed last time; replay exact, idempotent, deterministic; renders clean on 11.4.1 and 12.1.0; PR text passes the scripted checks. Head 181015d2 is still the live head today.

Hold (`UPSTREAM_SOURCE_DOES_NOT_PARSE`) re-confirmed: `ast.parse` on the tarball of 181015d2 fails on 102 of 119 `.py` files (IndentationError, for example `run_hello.py` and `tests/test_active_chars.py`), so the library cannot be imported. The recorded reason says "35 of 45 source files" next to "102 of 119 .py files" (two counts of one defect; the PR text carries neither). Pair with the upstream-defect issue.
