"""README examples the repository itself refutes: reported, never edited.

The example verifier compiles or runs every README code block at the pinned revision; a block that
fails is a CONTRADICTED ``example`` fact. The honest repair is code (a missing include, a renamed
member) that only a maintainer or a model can write, so this path lists it with the line range and
the compiler's own message, and leaves the README exactly as written.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import Context, DetectorResult, Finding
from repository_presenter.core.facts import Fact

_LINES = re.compile(r"^lines (\d+)(?:-(\d+))?;")
_MESSAGE_LIMIT = 200
_PARSE_ERROR = re.compile(r"IndentationError|SyntaxError")
_UPSTREAM_THRESHOLD = 3
_SAMPLE = 6
_NO_DIAGNOSTIC = " (no compiler diagnostic: the toolchain or environment may be at fault)"


@detector("failing_example")
def failing_example(ctx: Context) -> DetectorResult:
    findings: list[Finding] = []
    parse_failures: list[Fact] = []
    for fact in ctx.facts.by_kind("example"):
        if fact.polarity != "CONTRADICTED" or not fact.evidence:
            continue
        where = _LINES.match(fact.evidence[0].detail or "")
        outcome = next(
            (e.detail for e in fact.evidence[1:] if e.detail and "FAILED" in e.detail), None
        )
        if where is None or outcome is None:
            continue
        span = where.group(1) + (f"-{where.group(2)}" if where.group(2) else "")
        if _PARSE_ERROR.search(outcome):
            parse_failures.append(fact)
        findings.append(
            Finding(
                "failing_example",
                int(where.group(1)),
                fact.value.splitlines()[0][:80] if fact.value else "",
                f"the example verifier recorded a failure for the example on lines {span}: "
                f"{outcome[:_MESSAGE_LIMIT]}"
                + (_NO_DIAGNOSTIC if "without naming" in outcome else ""),
                (fact.id,),
            )
        )
    if len(parse_failures) >= _UPSTREAM_THRESHOLD:
        findings.append(
            Finding(
                "failing_example",
                0,
                "",
                f"{len(parse_failures)} examples fail with a syntax or indentation error: the "
                "library source itself may not parse (an upstream defect for an issue to the "
                "maintainers, not a README edit): "
                + ", ".join(f.id for f in parse_failures[:_SAMPLE]),
                tuple(f.id for f in parse_failures[:_SAMPLE]),
            )
        )
    return DetectorResult(findings=tuple(findings))
