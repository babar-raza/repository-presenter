"""License, public-type-count and test-file-count statements the facts positively contradict.

Each detector reads a README sentence of a fixed grammar, compares the number or name it states
with the value a verified fact (or a recount of the pinned tree) gives, and edits only that token.
A sentence that does not match the grammar, a claim with no fact, or two sources that disagree with
each other are left alone and, where useful, reported as a finding.
"""

from __future__ import annotations

import posixpath
import re

from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    FALSE_CLAIM_FIX,
    Context,
    DetectorResult,
    Edit,
    Finding,
)

# ---------------------------------------------------------------------------------- license
#: spdx id -> (the display name a sentence uses, the spellings a README gives it).
_LICENSES: dict[str, tuple[str, str]] = {
    "MIT": ("MIT License", r"MIT(?:[ ]License)?"),
    "Apache-2.0": (
        "Apache License 2.0",
        r"Apache(?:[ -]License)?(?:,?[ ]Version)?[ -]2(?:\.0)?(?:[ ]License)?",
    ),
    "BSD-3-Clause": (
        "BSD 3-Clause License",
        r"(?:3-Clause[ ]BSD|BSD[ -]3-Clause)(?:[ ]License)?",
    ),
    "BSD-2-Clause": (
        "BSD 2-Clause License",
        r"(?:2-Clause[ ]BSD|BSD[ -]2-Clause)(?:[ ]License)?",
    ),
    "GPL-3.0": (
        "GNU General Public License v3.0",
        r"(?:GNU[ ]General[ ]Public[ ]License,?[ ](?:version[ ]|v)3(?:\.0)?|GPL[ -]?v?3(?:\.0)?)",
    ),
    "GPL-2.0": (
        "GNU General Public License v2.0",
        r"(?:GNU[ ]General[ ]Public[ ]License,?[ ](?:version[ ]|v)2(?:\.0)?|GPL[ -]?v?2(?:\.0)?)",
    ),
    "LGPL-3.0": (
        "GNU Lesser General Public License v3.0",
        r"(?:GNU[ ]Lesser[ ]General[ ]Public[ ]License,?[ ](?:version[ ]|v)3(?:\.0)?"
        r"|LGPL[ -]?v?3(?:\.0)?)",
    ),
    "MPL-2.0": (
        "Mozilla Public License 2.0",
        r"(?:Mozilla[ ]Public[ ]License[ ]2(?:\.0)?|MPL[ -]2(?:\.0)?)",
    ),
    "ISC": ("ISC License", r"ISC(?:[ ]License)?"),
    "Unlicense": ("Unlicense", r"The[ ]Unlicense|Unlicense"),
}
_STATES = re.compile(r"(?i)\b(?:licensed|released|distributed|available)\s+under\b")
_ALTERNATIVE = re.compile(r"(?i)\b(?:or|and|dual|both)\b|/")
_SENTENCE_END = re.compile(r"(?<=[A-Za-z0-9)\]])\.(?=\s|$)")
_LINK_TARGET = re.compile(r"\]\([^)]*\)")


@detector("claim_license")
def claim_license(ctx: Context) -> DetectorResult:
    spdx = ctx.supported("license:spdx")
    if spdx is None or spdx.value not in _LICENSES:
        return DetectorResult()
    display = _LICENSES[spdx.value][0]
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence:
            continue
        said = _STATES.search(line.text)
        if said is None:
            continue
        tail = _SENTENCE_END.split(line.text[said.end() :], maxsplit=1)[0]
        found: list[tuple[int, int, str]] = []
        for key, (_name, spelling) in _LICENSES.items():
            for match in re.finditer(rf"(?<![\w-])(?:{spelling})(?![\w-])", tail):
                found.append((match.start(), match.end(), key))
        if not found:
            continue
        reason = f"the README says it is licensed under {tail[found[0][0] : found[0][1]]!r}"
        distinct = {key for _s, _e, key in found}
        visible = _LINK_TARGET.sub("]", tail[: max(end for _s, end, _k in found)])
        if len(distinct) != 1 or _ALTERNATIVE.search(visible):
            findings.append(
                Finding("claim_license", line.number, line.text, reason + " (ambiguous)")
            )
            continue
        start, end, key = max(found, key=lambda item: item[1] - item[0])
        if key == spdx.value:
            continue
        absolute = line.start + said.end() + start
        edits.append(
            Edit(
                kind=FALSE_CLAIM_FIX,
                detector="claim_license",
                start=absolute,
                end=line.start + said.end() + end,
                original=ctx.readme[absolute : line.start + said.end() + end],
                replacement=display,
                fact_ids=(spdx.id,),
                rationale=f"{reason}, but the license text at the pinned revision states "
                f"{spdx.value}",
            )
        )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))


# ------------------------------------------------------------------------- public type count
_TYPE_COUNT = re.compile(
    r"(?<![\w.])(?P<n>\d{1,3}(?:,\d{3})+|\d+)(?P<tail>\s+(?:verified\s+)?public\s+types?\b)",
    re.IGNORECASE,
)
_SURFACE_COUNT = re.compile(
    r"(?i)\bpublic\s+surface\s+has\s+(?P<n>\d{1,3}(?:,\d{3})+|\d+)\s+types?\b"
)


#: A path segment that marks a symbol as example, test or documentation code rather than library
#: surface (measured: Aspose.Words for Python's 198 verified types include nine ApiExamples
#: classes).
_NON_LIBRARY = frozenset(
    {
        "tests",
        "test",
        "examples",
        "example",
        "apiexamples",
        "samples",
        "sample",
        "docs",
        "benchmarks",
    }
)


@detector("claim_public_types")
def claim_public_types(ctx: Context) -> DetectorResult:
    """ "N public types" against the number of SUPPORTED class and enum symbols, the definition the
    renderer counts by (``renderer_sentences``) - corrected only when that count does not depend on
    whether example and test code is included, so the README is never moved from one defensible
    figure to another; a stale number with two candidate figures is reported, not edited."""
    types = [
        fact
        for fact in ctx.facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
        and (fact.attributes or {}).get("symbol_kind") in {"class", "enum"}
    ]
    if not types:
        return DetectorResult()
    count = len(types)
    library = sum(
        1
        for fact in types
        if not _NON_LIBRARY.intersection(
            part.lower() for part in fact.evidence[0].path.split("/")[:-1]
        )
    )
    sample = tuple(sorted(fact.id for fact in types)[:5])
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence or line.text.lstrip().startswith("|"):
            continue
        for pattern in (_TYPE_COUNT, _SURFACE_COUNT):
            for match in pattern.finditer(line.text):
                stated = match.group("n")
                if int(stated.replace(",", "")) in {count, library}:
                    continue
                reason = (
                    f"the README states {stated} public types; the verified facts hold {count} "
                    f"SUPPORTED class and enum symbols ({library} outside example and test code)"
                )
                if count != library:
                    findings.append(
                        Finding("claim_public_types", line.number, line.text, reason, sample)
                    )
                    continue
                shown = f"{count:,}" if "," in stated else str(count)
                edits.append(
                    Edit(
                        kind=FALSE_CLAIM_FIX,
                        detector="claim_public_types",
                        start=line.start + match.start("n"),
                        end=line.start + match.end("n"),
                        original=stated,
                        replacement=shown,
                        fact_ids=sample,
                        rationale=reason + " (first five cited)",
                    )
                )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))


# ---------------------------------------------------------------------------- test file count
_TEST_FILES = re.compile(r"(?<![\w.])(?P<n>\d+)(?P<tail>\s+test\s+files?\b)", re.IGNORECASE)
_FILE_COUNT = re.compile(r"^(\d+) files\b")
_TEST_FILE_NAME = re.compile(
    r"""(?ix)
    ^(?: test_.*\.py | .*_test\.py | .*tests?\.(?:java|cs|kt|scala) | test.*\.(?:java|cpp|cc)
      | .*\.(?:test|spec)\.(?:ts|tsx|js|jsx|mjs) | .*_test\.(?:go|cc|cpp|c) )$"""
)


def _test_files(tree: tuple[str, ...], directory: str) -> list[str]:
    prefix = directory if directory.endswith("/") else directory + "/"
    return [
        path
        for path in tree
        if path.startswith(prefix)
        and (_TEST_FILE_NAME.match(posixpath.basename(path)) or path.endswith(".rs"))
    ]


@detector("claim_test_files")
def claim_test_files(ctx: Context) -> DetectorResult:
    """ "N test files" against the suite size, only where two independent derivations agree.

    The fact's own count (every file under the test directory) is recounted from the tracked tree
    by file-name convention; a README number is corrected only when both give the same figure, so
    a fact that counts helpers or fixtures as tests (measured on three portfolio repositories)
    can never turn a true statement false."""
    tests = ctx.supported("build_test_asset:tests")
    if tests is None:
        return DetectorResult()
    counts = [
        int(match.group(1))
        for evidence in tests.evidence
        if (match := _FILE_COUNT.match(evidence.detail or "")) is not None
    ]
    if not counts:
        return DetectorResult()
    fact_count = counts[-1]
    recount = len(_test_files(ctx.tree_paths, tests.value))
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence:
            continue
        for match in _TEST_FILES.finditer(line.text):
            stated = int(match.group("n"))
            if stated == fact_count:
                continue
            reason = (
                f"the README states {stated} test files; the verified suite under "
                f"`{tests.value}` holds {fact_count} files (recount by file name: {recount})"
            )
            if recount != fact_count:
                findings.append(
                    Finding(
                        "claim_test_files",
                        line.number,
                        line.text,
                        reason + "; the two disagree",
                        (tests.id,),
                    )
                )
                continue
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector="claim_test_files",
                    start=line.start + match.start("n"),
                    end=line.start + match.end("n"),
                    original=match.group("n"),
                    replacement=str(fact_count),
                    fact_ids=(tests.id,),
                    rationale=reason,
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
