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

Nothing here calls `gh issue create`/`close` or any other GitHub Issues write endpoint; that stays
gated on the separate authorization `AGENTS.md`'s Security and Effects section requires.
"""

from __future__ import annotations
