"""Offline idempotence and retention harness (TC-IDM-01, plans/reseal-and-refresh/PLAN.md 11A).

Makes "better than the live README" measurable and gates regressions, for both lanes: the
live-first correction lane (``components/readme_correction``) and the regeneration lane. Everything
here is a pure function of README text, facts and a lane callable; nothing reads the network, a
clock or a model, so the default path runs in CI.

* ``corpus``     the 44 live READMEs, frozen with head commit and SHA-256 (``data/idempotence/``)
* ``atoms``      the cut of a README into sentences, items, rows, code, headings, links, images
* ``retention``  (a) what a candidate keeps of the live README and what it loses, with positions
* ``editscript`` (b) how many hunks and changed lines separate the two
* ``introduced`` (c) what the candidate says that neither the live README nor the facts said
* ``lane``       (d) the lane adapter and the fixed-point test ``P(P(x)) = P(x)``
* ``mutations``  (e) controlled defects injected into a conformant README, each expected to be
                 found by exactly one detector
* ``report``     the table for sealed regeneration bundles used by the acceptance reviews

Owner/reviewer tooling (tools/README.md): never imported by src/, never read by a product stage.
"""
