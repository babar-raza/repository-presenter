authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false

# Acceptance protocol calibration (TC-ACC-01-01)

Protocol under test: `decisions/acceptance-protocol.md` (brief version 1). Result: PASSED on the
first run, no protocol repair was needed to detect the two injected defects. Three small
clarifications were made afterwards (section "Changes after calibration"); they do not alter
any detection step.

## Setup

- Base candidate: the sealed bundle of `aspose-email-foss/Aspose.Email-FOSS-for-Python`
  (`candidates/aspose-email-foss__Aspose.Email-FOSS-for-Python/10a906b48c0c11005c4d93b524e4431901c9717c/`).
  It is not one of the two candidates reviewed in TC-ACC-01-02. Its upstream head equals the
  sealed revision, and PyPI lists exactly one release of `aspose-email-foss`, `26.3`.
- Scratch copy (outside the repository, in the session scratchpad `calib/broken/`): the whole
  bundle copied, then only `README.md` altered with exactly two edits.
  1. FALSE VERSION: Installation line `(`aspose-email-foss`, version 26.3)` became `version 26.3.1`
     (plausible, but not published and not in `pyproject.toml`).
  2. DROPPED SECTION: the required `## Dependencies` section and its `- [Dependencies](#dependencies)`
     Navigation entry were deleted.
- The edit changed the README hash on purpose (manifest `015cae25...`, file `d3053db6...`). The
  protocol's section 1 says a hash mismatch is a STOP (DO_NOT_PROPOSE). To test the content
  checks, the calibration prompt told the reviewer to record the mismatch and continue.

## Method

A fresh Sonnet agent that had not seen the edit was given the protocol brief verbatim (Appendix
A included), with `{repo}` and `{bundle path}` substituted and one preamble paragraph that sent
its record to the scratchpad and waived the hash STOP. It had no knowledge of which defects had
been injected. Its record: scratchpad `calib/record-blind.md` (not committed; the findings are
summarised here).

## Outcome

| Injected defect | Caught? | How the protocol caught it |
|---|---|---|
| False version `26.3.1` | YES (B2, category false_claim) | Section 4 registry check: `curl https://pypi.org/pypi/aspose-email-foss/json` gives `info.version` 26.3 and releases `['26.3']`; the clone's `pyproject.toml` also says 26.3. |
| Dropped `Dependencies` section | YES (B3, category template) | Section 5, `mech.py` line `missing required: ['Dependencies']`, plus the live README has the section and the Navigation list lacks it. |
| (not injected) README altered | YES (B1) | Section 1 hash check: file `d3053db6` against manifest `015cae25`; the reviewer also showed that applying `README.patch` to the live README reproduces `015cae25`. |

Independent confirmation by the lane agent that wrote the protocol: `sha256sum` of the scratch README is
`d3053db6...`, the manifest says `015cae25...`, and `mech.py` on the scratch README prints
`missing required: ['Dependencies']` and the version token `26.3.1` at L66.

Verdict returned: DO_NOT_PROPOSE, minor_major MAJOR, net_vs_live worse, confidence high,
18 claims checked, 6 failed. That verdict is the right direction for a tampered bundle.

## Additional true findings on the unmodified candidate

The reviewer also found genuine defects that were already in the sealed Email-Python
candidate, which shows the protocol finds more than the injected ones: the forbidden wording
"Aspose.Email commercial edition" at L338; API signatures printed as `str / None` and
`Path / str` (renderer defect, a redraw would reproduce it, so code_change MAJOR); module
names `email_foss.cfb` / `email_foss.msg` that are not importable (`import email_foss` fails);
a demoted reviewer finding (F01, At a Glance omits CFB input and EML/CFB outputs) that was
true; and dropped test/build commands, CI matrix, six documentation links and two badges
present in the live README. The verifier lane re-confirmed only the forbidden wording, which is in the sealed README
(`grep -i "commercial edition"` matches the Scope paragraph at L349); the other items are the
blind reviewer's findings, not independently re-verified.

## Limits of this calibration

- One broken candidate, two injected defects, one reviewer run. It shows the procedure can
  find a wrong version string and a missing required section. It does not measure how often a
  reviewer misses a subtler false claim.
- The reviewer was told the hash check could be waived, so the hash check is demonstrated
  separately (B1) and not as a substitute for the content checks.
- Run-to-run reviewer variance was not measured. TC-ACC-01-03 should expect small differences
  in the number of spot-checks and have the supervisor re-run a sample of verdicts.

## Changes after calibration (version 1 to 1.1)

Made after reading the calibration output and the two real reviews' first findings; none touches
a step the calibration exercised.

1. Every FAIL or MISLEADING claim is tagged `introduced` (absent from the live README) or
   `inherited` (identical in live). Both block AUTHORIZABLE (the owner's bar is that every claim
   is true); only `introduced` ones count toward the "several" threshold of DO_NOT_PROPOSE.
2. "Several" is defined as three or more independent introduced FAIL or MISLEADING results, or an
   introduced false version/install/published statement together with other blocking findings.
3. `mech.py` flags the word "wrapper" mechanically; the brief now says "wrapper" inside an API
   description of a class is not an implementation bridge unless it says one platform's
   implementation depends on another.
4. For DO_NOT_PROPOSE, `minor_major` states the size of the change needed before the candidate
   could be reconsidered.
