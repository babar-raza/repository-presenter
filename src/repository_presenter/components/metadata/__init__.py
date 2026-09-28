"""Repo metadata: capture, proposal, and a gated apply (workstream 2, docs/PRODUCTION_ROADMAP.md).

Phase 0 (``capture.py``) reads GitHub's current ``description``/``homepage``/``topics`` for a
registry repository, read-only. Phase 1 (``proposal.py``) derives a candidate value for each from
facts this project already extracted and verified, and diffs it against the Phase 0 observation.
Phase 2 (``apply.py``) can ``PATCH``/``PUT`` that diff to GitHub - but only past two independent,
explicit gates (an owner-controlled authorization signal, and a write-scoped token distinct from
the read-only ``GH_TOKEN`` the first two phases use); neither gate is set anywhere in this
project's own environment today, so it is built and tested, never fired
(docs/DECISION_LOG.md, 2026-09-17 17:05 UTC ruling and the entry recording ``apply.py`` itself).
"""

from __future__ import annotations
