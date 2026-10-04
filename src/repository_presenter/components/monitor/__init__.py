"""Scheduled drift observation (G7-W06; `docs/EXECUTION_STATE_MACHINE.md` G7 work item 3).

`drift.py` compares each enabled registry repository's upstream default-branch head with the
revision its ``CURRENT`` sealed bundle was built from, and records one status per repository
(``CURRENT``, ``DRIFTED``, ``NO_BUNDLE``, ``UNREACHABLE``). It is read-only: one read-only token,
no provider call, and no write to any repository. Never README-content-specific.
"""
