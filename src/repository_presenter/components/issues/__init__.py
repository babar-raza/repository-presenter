"""Upstream defect handoffs: dedup ledger and re-detection.

`docs/investigations/03-issue-tracking.md` section 5's evidence-backed handoff artifact
(`schemas/upstream-defect-handoff.schema.json`, `evidence/upstream-defects/<owner>__<name>/
<fingerprint>.json`) already carries the full lifecycle a filer needs (`HANDOFF_PENDING` ->
`HANDOFF_ACKNOWLEDGED` -> `FILED` -> `RESOLVED_UPSTREAM`). This package adds the two read+local-
JSON mechanisms `docs/DECISION_LOG.md`'s 2026-09-17 15:40 UTC ruling named ready for a taskcard,
neither of which needs a GitHub write scope:

- `model.py` — the typed shape of one handoff artifact.
- `ledger.py` — the dedup ledger: the durable `{repository, defect_fingerprint} -> {issue_ref,
  filed_at_revision, last_observed_state}` mapping, built by reading every handoff artifact on
  disk (investigation section 4 point 3).
- `redetect.py` — the re-detection pass: re-evaluate a handoff's own `triggering_check` at the
  repository's current revision and report whether it still fires (investigation section 6).
- `draft.py` — the authoring path: `cli.py::run_present` calls this the moment its own
  validation/invalidation machinery proves a genuine upstream-content defect (currently: `BC-02`
  at `causal_stage EXTRACTING`, backed by a real non-`SUPPORTED` `install_command` fact), so the
  handoff artifact this package's lifecycle already governs gets created automatically instead of
  only through the separate, manually-invoked `redetect-upstream-defects` CLI subcommand.
- `file.py` — the gated write half: files a `HANDOFF_PENDING` handoff as a real
  `POST /repos/{owner}/{repo}/issues` call, and closes a `FILED` handoff whose check no longer
  fires (`PATCH .../issues/{n}`), each only past two independent, explicit gates (an owner-
  controlled authorization variable, and a write-scoped token distinct from the read-only
  `GH_TOKEN` every other module here uses). Filing also rechecks the defect and searches the target
  for the handoff's fingerprint marker, so a fresh checkout cannot file a duplicate. It runs only
  from `.github/workflows/issues-scheduled.yml`'s gated write job.

Every other module here (`model.py`, `ledger.py`, `redetect.py`, `draft.py`) stays read + local-
JSON only and calls no GitHub Issues write endpoint; only `file.py` ever does, and only past its
own gates.
"""

from __future__ import annotations
