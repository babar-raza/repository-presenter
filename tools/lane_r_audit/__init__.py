"""Lane R dependability measurement (G3-W12 card C1): the harness behind the Lane R metrics.

Owner-approved exception to the tools boundary (tools/README.md): written by the loop, imports
``src/`` read-only, and is the source of the G3-W12 exit numbers. It decides nothing for the
product: no state transition, no provider call, no network, no write to a candidate. M1 to M3 and
M9 are read from the 30 sealed bundles pinned at a control revision, through the judge's own clause
readers; M4 and M5 are an independent reference checker that imports no validation, reconciliation
or composition decision logic, so a gate never grades itself.
"""

from __future__ import annotations
