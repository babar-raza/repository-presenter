"""Repo metadata: capture and proposal only (workstream 2, docs/PRODUCTION_ROADMAP.md).

Phase 0 (``capture.py``) reads GitHub's current ``description``/``homepage``/``topics`` for a
registry repository, read-only. Phase 1 (``proposal.py``) derives a candidate value for each from
facts this project already extracted and verified, and diffs it against the Phase 0 observation.

Neither module ever writes to GitHub. ``PATCH /repos/{owner}/{repo}`` and
``PUT /repos/{owner}/{repo}/topics`` stay gated on ``OWNER-04``/G5's ``Administration: write``
scope (docs/DECISION_LOG.md, 2026-09-17 17:05 UTC ruling); this component is the read+proposal
half only.
"""

from __future__ import annotations
