authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr6-3d-net: aspose-3d-foss/Aspose.3D-FOSS-for-.NET (run 20261012-90a5a934) HOLD (owner-recorded, re-confirmed)

Patch 2401 bytes (+24/-19), diagram only, byte-identical to the run reviewed last time (README.md, README.original.md, README.patch); replay exact, idempotent, deterministic; renders clean on 11.4.1 and 12.1.0; PR text regenerates byte for byte and passes the scripted checks. Head 52b0f00e is still the live head today (read-only `gh api`).

Hold (`data/correction_holds.json`, `README_ADVERTISES_UNSUPPORTED_FORMATS`) re-confirmed at the same head: `IOService.cs` lines 67 and 88 still read `_ => throw new NotSupportedException(...)` for any format outside the switch, while the README diagram republished by the redraw labels U3D, RVM, AMF and HTML5. Pair the diagram PR with an issue (or a README correction) naming the formats the code rejects. The bundle is unchanged; only the sending is held.
