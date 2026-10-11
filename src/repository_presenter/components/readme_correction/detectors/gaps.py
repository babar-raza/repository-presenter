"""Information the live README lacks that no deterministic edit can add: reported, with the facts.

Each of these needs authored prose or a judgement about wording, so this path never writes it; the
regeneration lane, or a maintainer, can. A finding names the class of information and the exact
facts that would fill it, so nothing has to be rediscovered:

* verified examples whose code the README never shows (``example`` facts, SUPPORTED);
* verified public types the README never names (``public_symbol`` class and enum facts);
* verified formats the README never names (``format`` facts);
* the Enterprise Edition paragraph (``link_target:product.enterprise``);
* a third-party notices file the tree holds and the README never mentions.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    Context,
    DetectorResult,
    Finding,
)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NO_DEPENDENCIES = re.compile(
    r"(?i)\b(?:pure[- ]managed|pure[- ]python|dependency[- ]free|zero (?:runtime )?dependencies"
    r"|no (?:runtime |third[- ]party |external |native )*dependencies)\b"
)
_SAMPLE = 8


def _sample(ids: list[str]) -> str:
    shown = ", ".join(ids[:_SAMPLE])
    return shown + (f" (+{len(ids) - _SAMPLE} more)" if len(ids) > _SAMPLE else "")


@detector("report_gaps")
def report_gaps(ctx: Context) -> DetectorResult:
    findings: list[Finding] = []
    readme = ctx.readme
    code = {line.text.strip() for line in ctx.lines if line.in_fence and line.text.strip()}

    unseen = []
    for fact in ctx.facts.by_kind("example"):
        if fact.polarity != "SUPPORTED":
            continue
        shown = [part.strip() for part in fact.value.splitlines() if part.strip()][:2]
        if shown and not all(part in code for part in shown):
            unseen.append(fact.id)
    if unseen:
        findings.append(
            Finding(
                "report_gaps",
                0,
                "",
                f"{len(unseen)} verified example(s) whose code the README never shows; would "
                f"fill Quick Start or Additional Examples: {_sample(unseen)}",
                tuple(unseen[:_SAMPLE]),
            )
        )

    named = set(_IDENTIFIER.findall(readme))
    types = [
        fact
        for fact in ctx.facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
        and (fact.attributes or {}).get("symbol_kind") in {"class", "enum"}
    ]
    absent = [fact.id for fact in types if fact.value.rsplit(".", 1)[-1] not in named]
    if absent:
        findings.append(
            Finding(
                "report_gaps",
                0,
                "",
                f"{len(absent)} of {len(types)} verified public types are named nowhere in the "
                f"README; would fill API Reference: {_sample(absent)}",
                tuple(absent[:_SAMPLE]),
            )
        )

    lowered = readme.lower()
    formats = [
        fact.id
        for fact in ctx.facts.by_kind("format")
        if fact.polarity == "SUPPORTED" and fact.value.lower().lstrip(".") not in lowered
    ]
    if formats:
        findings.append(
            Finding(
                "report_gaps",
                0,
                "",
                f"{len(formats)} verified format(s) named nowhere in the README; would fill At a "
                f"Glance or Key Capabilities: {_sample(formats)}",
                tuple(formats[:_SAMPLE]),
            )
        )

    required = [
        fact
        for fact in ctx.facts.by_kind("dependency")
        if fact.polarity == "SUPPORTED"
        and fact.id != "dependency:none"
        and not fact.id.startswith(("dependency:development.", "dependency:optional."))
    ]
    for line in ctx.lines:
        match = None if line.in_fence or not required else _NO_DEPENDENCIES.search(line.text)
        if match is not None:
            findings.append(
                Finding(
                    "report_gaps",
                    line.number,
                    line.text.strip()[:120],
                    f"the README says {match.group(0)!r}, but the facts list {len(required)} "
                    f"required dependenc(ies): {_sample([f.id for f in required])}",
                    tuple(f.id for f in required[:_SAMPLE]),
                )
            )
    enterprise = ctx.fact("link_target:product.enterprise")
    if enterprise is not None and "enterprise edition" not in lowered:
        findings.append(
            Finding(
                "report_gaps",
                0,
                "",
                "no Enterprise Edition paragraph; would be filled from "
                f"{enterprise.id} ({enterprise.polarity}, {enterprise.value}) and the anchor "
                "rule of the Scope and Limitations closing paragraph",
                (enterprise.id,),
            )
        )

    for notices in ctx.facts.by_kind("third_party_notices"):
        if notices.polarity == "SUPPORTED" and notices.value.lower() not in lowered:
            findings.append(
                Finding(
                    "report_gaps",
                    0,
                    "",
                    f"the tree holds {notices.value} and the README never mentions it "
                    f"({notices.id}); not one of the ten sections, so never added",
                    (notices.id,),
                )
            )
    return DetectorResult(findings=tuple(findings))
