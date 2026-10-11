"""Install and release statements the package registry contradicts.

* ``unpublished_install_command``: an install command in the README for a package the registry
  says does not exist (the extractor's own reading: "distribution not found", or a source-only
  install). The honest repair is prose - tell the reader to build from a source checkout - so this
  is reported with the registry evidence, never rewritten. It also blocks inserting an
  Installation section that says "not yet published" beside the very command it contradicts.
* ``stale_phrase``: a future-tense release claim ("landing soon", "coming soon", "once the
  repository is live", "will be published") that the registry already contradicts. Corrected only
  when the registry proves the package IS published and the whole line is nothing but that claim,
  replaced by the verified install command; otherwise reported.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.validation import claims as bc14
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    FALSE_CLAIM_FIX,
    Context,
    DetectorResult,
    Edit,
    Finding,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.facts import Fact
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID

_NOT_FOUND = re.compile(r"(?i)distribution not found|not found|\b404\b|not listed|not published")
_FUTURE = re.compile(
    r"(?i)\b(?:landing soon|coming soon|will (?:soon )?be (?:published|released|available|uploaded)"
    r"|soon be (?:available|published)|once the repository is (?:live|public))\b"
)
_PUBLICATION_WORDS = re.compile(
    r"(?i)\b(?:package|nuget|pypi|npm|maven|crates?|registry|published|release)\b"
)
_WHOLE_LINE = re.compile(
    r"(?i)^(?:the\s+)?(?:nuget|pypi|npm|maven(?: central)?|crates\.io)(?:\s+package)?"
    r"\s+(?:is\s+)?(?:landing|coming)\s+soon\.?$"
)
_REPOSITORY_LIVE = re.compile(r"(?i)once the repository is (?:live|public)")
_SENTENCES = re.compile(r"(?<=[.!?])\s+")


def _install_fact(ctx: Context) -> Fact | None:
    plugin_for(ctx.entry.ecosystem)
    return ctx.fact(spec_for(ctx.entry.ecosystem).install_fact_id)


def registry_says_unpublished(ctx: Context) -> str | None:
    """The registry's reading that the package does not exist, or None when it is (or may be)
    published: a source-only install, or evidence the registry found no distribution."""
    install = _install_fact(ctx)
    if install is None:
        return None
    kind = (install.attributes or {}).get("install_kind")
    for evidence in install.evidence:
        if evidence.detail and _NOT_FOUND.search(evidence.detail) and "registry" in evidence.detail:
            return f"{evidence.path}: {evidence.detail}"
    if kind in {"source", "source_checkout"}:
        return f"{install.id} is a {kind} install: the registry lists no distribution"
    return None


def unpublished_commands(ctx: Context) -> list[tuple[int, str]]:
    """``(line number, line)`` of each install command naming the package the registry lacks."""
    identity = ctx.supported("package:name")
    if identity is None or registry_says_unpublished(ctx) is None:
        return []
    found: list[tuple[int, str]] = []
    for line in ctx.lines:
        if not line.in_fence:
            continue
        targets = bc14._install_targets(line.text)
        coordinate = bc14._maven_target(line.text)
        if coordinate:
            targets.append(coordinate)
        if any(bc14._same_identity(target, identity.value) for target in targets):
            found.append((line.number, line.text.strip()))
    return found


@detector("unpublished_install_command")
def unpublished_install_command(ctx: Context) -> DetectorResult:
    reading = registry_says_unpublished(ctx)
    identity = ctx.supported("package:name")
    install = _install_fact(ctx)
    if reading is None or identity is None or install is None:
        return DetectorResult()
    return DetectorResult(
        findings=tuple(
            Finding(
                "unpublished_install_command",
                number,
                text,
                f"this command installs {identity.value!r}, which the registry does not list "
                f"({reading}); the README should send the reader to a source checkout instead",
                (install.id,),
            )
            for number, text in unpublished_commands(ctx)
        )
    )


@detector("stale_phrase")
def stale_phrase(ctx: Context) -> DetectorResult:
    identity = ctx.supported("package:name")
    published = ctx.supported(PUBLISHED_VERSION_FACT_ID)
    install = _install_fact(ctx)
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence or not _FUTURE.search(line.text):
            continue
        sentence = next((s for s in _SENTENCES.split(line.text) if _FUTURE.search(s)), line.text)
        about_package = (
            _PUBLICATION_WORDS.search(sentence)
            or _REPOSITORY_LIVE.search(sentence)
            or (identity is not None and identity.value.lower() in sentence.lower())
        )
        if not about_package:
            continue
        state = (
            f"the registry lists {identity.value} {published.value}"
            if published is not None and identity is not None
            else registry_says_unpublished(ctx) or "no registry reading"
        )
        command = install.value.splitlines()[0].strip() if install is not None else ""
        if (
            published is not None
            and install is not None
            and command
            and _WHOLE_LINE.match(line.text.strip())
        ):
            start = line.start + (len(line.text) - len(line.text.lstrip()))
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector="stale_phrase",
                    start=start,
                    end=line.end - (len(line.text) - len(line.text.rstrip())),
                    original=line.text.strip(),
                    replacement=f"Install it with `{command}`.",
                    fact_ids=tuple(f.id for f in (published, install) if f is not None),
                    rationale=f"the line promises a package the registry already lists ({state})",
                )
            )
            continue
        findings.append(
            Finding(
                "stale_phrase",
                line.number,
                sentence.strip(),
                f"future-tense release claim ({state}); worth rewording by a maintainer",
                tuple(f.id for f in (published, install) if f is not None),
            )
        )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
