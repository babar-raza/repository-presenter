"""Package version and install-name claims the facts positively contradict (BC-14, with spans).

``validation/claims.py`` (BC-14) already decides which statements a fact contradicts but reports
only a line. This module reuses its recognizers (the package-name pattern, the version tail, the
install-command grammar) to find the exact characters, so the correction fixes precisely what BC-14
would flag and ``claim_findings`` on the corrected text agrees (tests/.../test_claims.py).

Two deliberate differences from BC-14, both toward refusing to edit:

* A version is corrected only against ``package:published_version``, the registry's current stable
  release. BC-14 falls back to the manifest's version when no registry reading exists; a
  correction never does, because a manifest ahead of the registry is a maintainer's true statement
  (Aspose.Slides for Java: the tree is 26.8.0, Maven Central holds 26.7.0, and the README says so).
* ``>=`` floors and unattached version mentions ("`26.7.0` predates a fix") are never touched.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme.validation import claims as bc14
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    FALSE_CLAIM_FIX,
    Context,
    DetectorResult,
    Edit,
    Finding,
    ReadmeLine,
)
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID


def _strip_ticks(text: str) -> tuple[str, list[int]]:
    """``text`` without backticks, and for each remaining character its offset in ``text``."""
    kept: list[str] = []
    origin: list[int] = []
    for index, char in enumerate(text):
        if char != "`":
            kept.append(char)
            origin.append(index)
    origin.append(len(text))
    return "".join(kept), origin


def _attached(line: ReadmeLine, names: list[str]) -> list[tuple[int, int, str]]:
    """``(start, end, version)`` in the README text of each version BC-14 sees attached to a
    package name on ``line``."""
    cleaned, origin = _strip_ticks(line.text)
    found: dict[tuple[int, int], str] = {}
    for name in names:
        for match in bc14._name_pattern(name).finditer(cleaned):
            window = cleaned[match.end() : match.end() + 90]
            tail = bc14._TAIL.match(window)
            if tail is None:
                continue
            first = match.end() + tail.start("version")
            last = match.end() + tail.end("version")
            span = (line.start + origin[first], line.start + origin[last])
            found[span] = tail.group("version")
    return [(start, end, version) for (start, end), version in sorted(found.items())]


@detector("claim_version")
def claim_version(ctx: Context) -> DetectorResult:
    identity = ctx.supported("package:name")
    published = ctx.supported(PUBLISHED_VERSION_FACT_ID)
    if identity is None or published is None:
        return DetectorResult()
    expected = bc14._normal_version(published.value)
    names = bc14._names(identity.value)
    spans: dict[tuple[int, int], str] = {}
    for line in ctx.lines:
        for start, end, version in _attached(line, names):
            spans[(start, end)] = version
    for pair in bc14._POM_PAIR.finditer(ctx.readme):
        if any(bc14._name_pattern(name).fullmatch(pair.group("name")) for name in names):
            spans[(pair.start("version"), pair.end("version"))] = pair.group("version")
    edits = [
        Edit(
            kind=FALSE_CLAIM_FIX,
            detector="claim_version",
            start=start,
            end=end,
            original=ctx.readme[start:end],
            replacement=expected,
            fact_ids=(identity.id, published.id),
            rationale=(
                f"{identity.value} is shown at version {version}, but the registry's current "
                f"stable release is {expected}"
            ),
        )
        for (start, end), version in sorted(spans.items())
        if bc14._normal_version(version) != expected
    ]
    return DetectorResult(edits=tuple(edits))


@detector("claim_identity")
def claim_identity(ctx: Context) -> DetectorResult:
    """An install command naming a near-miss of the package identity (BC-14 rule c)."""
    identity = ctx.supported("package:name")
    if identity is None or not any(
        identity.value in fact.value
        for fact in ctx.facts.by_kind("install_command")
        if fact.polarity == "SUPPORTED"
    ):
        return DetectorResult()
    dependencies = {
        bc14._pep503(match.group(0))
        for fact in ctx.facts.by_kind("dependency")
        if (match := bc14._REQUIREMENT_NAME.match(fact.value))
    }
    stem = bc14._stem(identity.value)
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if not line.in_fence:
            continue
        targets = bc14._install_targets(line.text)
        coordinate = bc14._maven_target(line.text)
        if coordinate:
            targets.append(coordinate)
        for target in dict.fromkeys(targets):
            if bc14._same_identity(target, identity.value) or bc14._pep503(target) in dependencies:
                continue
            candidate = bc14._stem(target)
            if not (
                candidate and stem and (candidate.startswith(stem) or stem.startswith(candidate))
            ):
                continue
            hits = list(re.finditer(rf"(?<![\w.-]){re.escape(target)}(?![\w-])", line.text))
            reason = (
                f"the install command names {target!r}, but the package identity is "
                f"{identity.value!r}"
            )
            if len(hits) != 1:
                findings.append(Finding("claim_identity", line.number, line.text, reason))
                continue
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector="claim_identity",
                    start=line.start + hits[0].start(),
                    end=line.start + hits[0].end(),
                    original=target,
                    replacement=identity.value,
                    fact_ids=(identity.id,),
                    rationale=reason,
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))


@detector("claim_publication")
def claim_publication(ctx: Context) -> DetectorResult:
    """A sentence saying the package is unpublished while the registry lists it.

    Reported, never edited: the honest replacement is prose, and prose is not this path's to write.
    """
    identity = ctx.supported("package:name")
    published = ctx.supported(PUBLISHED_VERSION_FACT_ID)
    if identity is None or published is None:
        return DetectorResult()
    findings = tuple(
        Finding(
            "claim_publication",
            finding.line + 1,
            ctx.lines[finding.line].text,
            finding.detail,
            (identity.id, published.id),
        )
        for finding in bc14.claim_findings(ctx.readme, ctx.facts)
        if "is not published" in finding.detail
    )
    return DetectorResult(findings=findings)
