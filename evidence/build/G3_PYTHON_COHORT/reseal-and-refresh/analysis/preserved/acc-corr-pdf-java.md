authoritative_plan: plans/reseal-and-refresh/PLAN.md
artifact_role: analysis_or_evidence_only
execution_authority: false
preserved_from: session scratchpad, 2026-10-13 (TC-WKR-03-01); content unchanged below this header

# acc-corr-pdf-java: Aspose.PDF-FOSS-for-Java (live head 736cedaa)

Reviewer: independent (Sonnet 5.5). Read-only. Bundle: `scratchpad/lfix/out/aspose-pdf-foss__Aspose.PDF-FOSS-for-Java/`.
Clone: `scratchpad/acccorr/clones/Aspose.PDF-FOSS-for-Java`, HEAD 736cedaa == bundle `source_revision`.

**Verdict: PUSHABLE.** Two-line version bump, fully verified. Frame it as "update the install snippet to the current release", not as fixing a wrong version.

## 1. Edit confinement
- `README.original.md` == live blob (e0f09405...); corrected sha matches `corrections.json`.
- Replay of the two `FALSE_CLAIM_FIX` edits reproduces `README.md`. difflib: two single-line replacements (L121 `<version>26.6.0</version>` -> `26.9.0`; L128 `implementation 'org.aspose:aspose-pdf-foss:26.6.0'` -> `26.9.0`), 1675 lines before and after, nothing else touched. `grep -n '26\.[0-9]'` finds no other version string in the README (no jar names, no badge pin). LF-only.

## 2. Claim checks
| # | Claim | Check | Result |
|---|---|---|---|
| 1 | README pins 26.6.0 | live L121, L128 | PASS (as before-state) |
| 2 | 26.9.0 is the current stable release on Maven Central | `https://repo1.maven.org/maven2/org/aspose/aspose-pdf-foss/maven-metadata.xml`: `latest`=`release`=26.9.0, versions 26.6.0, 26.8.0, 26.9.0, lastUpdated 2026-10-07; `.../26.9.0/aspose-pdf-foss-26.9.0.pom` and `.jar` both HTTP 200 | PASS |
| 3 | Equals the repo's own version | `pom.xml` L6 `<version>26.9.0</version>`; groupId `org.aspose`, artifactId `aspose-pdf-foss` match the snippet | PASS |
| 4 | Was "26.6.0" false? | `.../26.6.0/aspose-pdf-foss-26.6.0.pom` HTTP 200: the old version is still published | It is a stale pin, not a falsehood (the lane says so itself in section 5 of its report) |
| 5 | Build-from-source block unchanged | `mvn clean install` | n/a |

## 3. Render and style
- Fences unchanged and closed; one H1; no new text, so nothing to be inconsistent in tone. This is the smallest respectful PR possible; any maintainer would merge it. Maintainers may bump this on each release anyway; the PR is still correct on the day it is opened (re-verify the head and the registry immediately before the effect).

## 4. Not addressed (separate content concern)
- `claim_public_types` L330: README states 1026 public types, lane's facts hold 1181 class and enum symbols. I did not independently recount; left unedited (correct decision: the definition of "public type" is disputed).

## 5. Fixes
None required. confidence: high.
