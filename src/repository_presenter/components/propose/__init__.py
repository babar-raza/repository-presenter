"""README-proposal PR effect (G6-W02; `docs/EXECUTION_STATE_MACHINE.md` G6; `docs/STATE_MACHINE.md`
sections 11-12's proposal and effect-authorization machines).

`effect.py` is the one gated write this package exists for: given a sealed candidate's README text
and a `core/authorization/proposal.py::ProposalAuthorization` binding it, create or update the one
stable presenter branch and its one open pull request on the target repository - idempotently, with
a fresh source-revision recheck immediately before the write, and reconciliation of a lost response
before ever retrying. Mirrors `components/issues/file.py` and `components/metadata/apply.py`'s own
gated-write pattern exactly: an owner-controlled authorization environment flag never inferred from
credential presence, a write-scoped token distinct from the read-only `GH_TOKEN`
(`GH_PROPOSAL_WRITE_TOKEN`), and every early refusal making no network call at all.
"""

from __future__ import annotations
