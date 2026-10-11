"""A deterministic quality gate for the text of an upstream issue (TC-ISS-04, G6-W07).

An issue is created by an app on behalf of the owner and read by the maintainers of the target
repository. Their time is the scarce resource, so the text must be one actionable report and must
not leak this system's own machinery. ``issue_quality_findings`` is pure: the same handoff always
gives the same findings, with no network, clock, or model. A handoff with findings is not
approvable text.

The checks (each has a code, a failing fixture and a passing one in
``tests/components/issues/test_quality.py``):

- ``ONE_DEFECT``: the title names one defect (no ``;`` joining two) and the body does not number
  several defects.
- ``NO_REPRODUCTION``: the body carries a reproduction section holding an exact command or a file
  path (a ``path:line`` or ``line N`` pins it further, but a line is only required when known, so
  it is never demanded).
- ``NO_EXPECTED`` / ``NO_ACTUAL``: the body states both the expected and the actual behavior.
- ``TITLE_FORMAT`` / ``TITLE_LENGTH``: ``<product or repository>: <defect statement>``, at most
  ``MAX_TITLE_LENGTH`` characters.
- ``SECRET``: no secret-shaped value (``core/secrets.py``'s pattern set, plus the other common
  token shapes). The finding never echoes the value.
- ``INTERNAL_NAME``: none of this system's artifact names or vocabulary (``upstream-issues.md``,
  ``content-dispositions.json``, ``.clone_cache``, ``reports/``, ``runs/``, ``facts.json``,
  ``dispositions.json``, ``sealed bundle``, check ids such as ``BC-03``, fact ids such as
  ``install_command:pip``, ``validation pipeline``) except the one fingerprint marker that
  ``file.py`` appends and that dedup requires.
- ``EDITION_WORDING``: no edition substitute (``commercial edition``, ``paid version``) and no
  bridge phrasing (``via Java``, ``wrapper``, ``bridge``).
- ``TONE``: no first-person voice, promotional wording, or blame.
- ``NO_REVISION``: the body states the upstream revision the report was verified against: the
  handoff's own ``source_revision``.

Prose checks (``EDITION_WORDING``, ``TONE``) ignore code, blockquotes (quoted README text) and
double-quoted spans, so quoting an upstream line that happens to say "wrapper" is not a finding.
The secret and internal-name scans read everything.

Known limit, by design: the gate checks objective shape, not truth. Whether the defect is real is
the independent reverification's job (``readiness.py``); whether the prose is good is the owner's
read before approving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from repository_presenter.components.issues.model import Handoff
from repository_presenter.core.secrets import redact

MAX_TITLE_LENGTH = 120

Where = Literal["title", "body"]

# Check codes, exported so a caller can group a listing.
CODES = (
    "ONE_DEFECT",
    "NO_REPRODUCTION",
    "NO_EXPECTED",
    "NO_ACTUAL",
    "TITLE_FORMAT",
    "TITLE_LENGTH",
    "SECRET",
    "INTERNAL_NAME",
    "EDITION_WORDING",
    "TONE",
    "NO_REVISION",
)


@dataclass(frozen=True)
class Finding:
    """One failed check. ``message`` never contains the offending secret value."""

    code: str
    where: Where
    message: str

    def __str__(self) -> str:
        return f"{self.code} ({self.where}): {self.message}"


class HandoffQualityError(ValueError):
    """A handoff's issue text fails the quality gate; ``findings`` is the typed reason."""

    def __init__(self, findings: list[Finding]) -> None:
        self.findings = tuple(findings)
        super().__init__(
            "issue text fails the quality gate: " + "; ".join(str(f) for f in self.findings)
        )


# The one marker the filer appends and the dedup search needs (file.py::fingerprint_marker).
_MARKER = re.compile(r"<!--\s*repository-presenter-defect:\s*sha256:[0-9a-f]{64}\s*-->")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE_LINE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_DOUBLE_QUOTED = re.compile(r'"[^"\n]{1,160}"|“[^”\n]{1,160}”')


def _without_fences(text: str) -> tuple[str, list[str]]:
    """``text`` with fenced code blocks removed, and those blocks' contents."""
    kept: list[str] = []
    blocks: list[str] = []
    fence: str | None = None
    current: list[str] = []
    for line in text.splitlines():
        match = _FENCE_LINE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)[0]
                current = []
            else:
                kept.append(line)
        elif match and match.group(1)[0] == fence and line.strip().strip(fence) == "":
            blocks.append("\n".join(current))
            fence = None
        else:
            current.append(line)
    if fence is not None:  # an unterminated fence still counts as a block
        blocks.append("\n".join(current))
    return "\n".join(kept), blocks


def _prose(text: str) -> str:
    """The reader-facing prose of ``text``: no marker, comments, code, blockquotes or quotes."""
    text = _HTML_COMMENT.sub(" ", text)
    text, _ = _without_fences(text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    text = _INLINE_CODE.sub(" ", text)
    return _DOUBLE_QUOTED.sub(" ", text)


# --- individual checks -------------------------------------------------------------------------


def _stem(repository: str) -> str:
    """The product stem of ``owner/Name-FOSS-for-X``: the part of ``Name`` before ``-FOSS``,
    lowercased to letters and digits (``Aspose.3D`` -> ``aspose3d``)."""
    name = repository.split("/", 1)[-1]
    head = re.split(r"(?i)[-_ ]foss\b", name, maxsplit=1)[0]
    return re.sub(r"[^a-z0-9]", "", head.lower())


def _title_findings(handoff: Handoff) -> list[Finding]:
    title = handoff.suggested_issue_title
    findings: list[Finding] = []
    if len(title) > MAX_TITLE_LENGTH:
        findings.append(
            Finding("TITLE_LENGTH", "title", f"{len(title)} characters; the limit is 120")
        )
    prefix, separator, statement = title.partition(": ")
    stem = _stem(handoff.repository)
    normalized = re.sub(r"[^a-z0-9]", "", prefix.lower())
    if not separator or len(statement.strip()) < 10 or "`" in prefix or len(prefix) > 70:
        findings.append(
            Finding(
                "TITLE_FORMAT",
                "title",
                "expected '<product or repository>: <defect statement>' "
                f"(for example '{handoff.repository.split('/', 1)[-1].replace('-', ' ')}: ...')",
            )
        )
    elif not stem or stem not in normalized:
        findings.append(
            Finding(
                "TITLE_FORMAT",
                "title",
                f"the part before ': ' must name the product or repository ('{stem}' is not in it)",
            )
        )
    if ";" in _prose(title):
        findings.append(
            Finding(
                "ONE_DEFECT", "title", "the title joins several defects with ';'; file one each"
            )
        )
    return findings


_DEFECT_HEADING = re.compile(
    r"^#{1,6}\s*(?:defect|issue|problem|bug)\s*(?:#|no\.?)?\s*\d+\b", re.IGNORECASE | re.MULTILINE
)
_REPRODUCTION_CUE = re.compile(r"reproduc|steps to|how to trigger", re.IGNORECASE)
_PATH = re.compile(
    r"(?<![\w/])(?:[\w.@+-]+/)+[\w.@+-]+\.\w{1,8}(?::\d+)?\b"
    r"|(?<![\w/])[\w.@+-]+\.(?:md|toml|json|ya?ml|xml|txt|cfg|ini|cmake|gradle|csproj|sln|py|cs|"
    r"cpp|cc|hpp|h|c|ts|tsx|js|mjs|java|kt|go|rs|rb|php|swift)(?::\d+)?\b"
)
_INLINE_COMMAND = re.compile(r"`[^`\n]*(?:\s|--)[^`\n]*`")
_EXPECTED = re.compile(r"\bexpected\b", re.IGNORECASE)
_ACTUAL = re.compile(r"\b(?:actual|observed)\b", re.IGNORECASE)


def _body_shape_findings(handoff: Handoff) -> list[Finding]:
    body = _MARKER.sub("", handoff.suggested_issue_body)
    findings: list[Finding] = []
    if len(_DEFECT_HEADING.findall(body)) > 1:
        findings.append(
            Finding("ONE_DEFECT", "body", "the body numbers several defects; file one issue each")
        )
    without_fences, blocks = _without_fences(body)
    has_command = any(block.strip() for block in blocks) or bool(
        _INLINE_COMMAND.search(without_fences)
    )
    has_path = bool(_PATH.search(body))
    if not (_REPRODUCTION_CUE.search(body) and (has_command or has_path)):
        findings.append(
            Finding(
                "NO_REPRODUCTION",
                "body",
                "needs a reproduction section with the exact command or the file path "
                "(and line when known)",
            )
        )
    prose = (
        _prose(body)
        + "\n"
        + "\n".join(line for line in without_fences.splitlines() if line.lstrip().startswith("#"))
    )
    if not _EXPECTED.search(prose):
        findings.append(Finding("NO_EXPECTED", "body", "state the expected behavior"))
    if not _ACTUAL.search(prose):
        findings.append(Finding("NO_ACTUAL", "body", "state the actual behavior or result"))
    if handoff.source_revision not in body:
        findings.append(
            Finding(
                "NO_REVISION",
                "body",
                f"state the upstream revision verified against ({handoff.source_revision[:12]}...)",
            )
        )
    return findings


# Secret shapes beyond core/secrets.py's own set (which `redact` applies): the other GitHub token
# prefixes, fine-grained PATs, cloud access keys, private-key blocks, and JWTs.
_EXTRA_SECRET_SHAPES = (
    re.compile(r"(?<![A-Za-z0-9_])(?:gho|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
)


def _has_secret(text: str) -> bool:
    return redact(text) != text or any(shape.search(text) for shape in _EXTRA_SECRET_SHAPES)


_INTERNAL = re.compile(
    r"upstream-issues\.md|content-dispositions(?:\.json)?|\.clone_cache"
    r"|(?<![\w.-])(?:reports|runs)/|\bfacts\.json\b|\bdispositions\.json\b"
    r"|\bsealed[\s-]+bundles?\b|\bcandidate[\s-]+bundles?\b|\bvalidation[\s-]+pipeline\b"
    r"|\bBC-\d{2}\b|\bcausal_stage\b|\bHANDOFF_[A-Z_]+\b|\bNOT_PROCESSABLE\b|\bEXTRACTING\b"
    r"|evidence/(?:upstream-defects|build)\b"
    r"|\b(?:install_command|package|example|license|link|badge):[a-z0-9_.-]+\b"
    r"|repository-presenter(?:'s)?[\s-]+(?:pipeline|validator|validation|ledger|registry|state)\b",
    re.IGNORECASE,
)


def _secret_and_internal_findings(handoff: Handoff) -> list[Finding]:
    findings: list[Finding] = []
    texts: list[tuple[Where, str]] = [
        ("title", handoff.suggested_issue_title),
        ("body", _MARKER.sub("", handoff.suggested_issue_body)),
    ]
    for where, text in texts:
        if _has_secret(text):
            findings.append(
                Finding("SECRET", where, "contains a secret-shaped value (not echoed here)")
            )
        names = sorted({m.group(0) for m in _INTERNAL.finditer(text)}, key=str.lower)
        if names:
            findings.append(
                Finding(
                    "INTERNAL_NAME",
                    where,
                    "names this system's internals, which upstream maintainers cannot use: "
                    + ", ".join(repr(n) for n in names[:5]),
                )
            )
    return findings


_EDITION = re.compile(
    r"\b(?:commercial|on[- ]?premises?|premium|paid|full|licensed|proprietary)[\s-]+"
    r"(?:edition|version)s?\b"
    r"|\bvia\s+(?:the\s+)?(?:java|jvm|jni)\b|\b(?:wrappers?|bridg(?:e|es|ed|ing))\b",
    re.IGNORECASE,
)
_FIRST_PERSON = re.compile(
    r"\bI\b(?!\.)|\b(?:I'm|I've|I'll|we|we're|we've|we'll|our|ours|my)\b", re.IGNORECASE
)
_PROMOTIONAL = re.compile(
    r"\b(?:amazing|awesome|best[- ]in[- ]class|blazing(?:ly)?|cutting[- ]edge|game[- ]chang\w+|"
    r"incredible|powerful|revolutionary|seamless(?:ly)?|world[- ]class|state[- ]of[- ]the[- ]art|"
    r"unmatched|effortless(?:ly)?)\b",
    re.IGNORECASE,
)
_BLAME = re.compile(
    r"\b(?:sloppy|careless(?:ly)?|negligent|lazy|incompeten\w+|unacceptable|embarrassing|"
    r"terrible|awful|shoddy|amateur(?:ish)?|you(?:'ve| have)? (?:failed|forgot|broke|neglected)|"
    r"your (?:fault|mistake)|obviously (?:broken|wrong)|why (?:did|would) (?:you|anyone))\b",
    re.IGNORECASE,
)


def _wording_findings(handoff: Handoff) -> list[Finding]:
    findings: list[Finding] = []
    texts: list[tuple[Where, str]] = [
        ("title", handoff.suggested_issue_title),
        ("body", handoff.suggested_issue_body),
    ]
    for where, text in texts:
        prose = _prose(text)
        edition = sorted({m.group(0).lower() for m in _EDITION.finditer(prose)})
        if edition:
            findings.append(
                Finding(
                    "EDITION_WORDING",
                    where,
                    "edition or bridge wording: " + ", ".join(repr(e) for e in edition[:5]),
                )
            )
        tone = (
            ("first person", _FIRST_PERSON),
            ("promotional", _PROMOTIONAL),
            ("blame", _BLAME),
        )
        for label, pattern in tone:
            hits = sorted({m.group(0).lower() for m in pattern.finditer(prose)})
            if hits:
                findings.append(
                    Finding(
                        "TONE",
                        where,
                        f"{label} language: " + ", ".join(repr(h) for h in hits[:5]),
                    )
                )
    return findings


def issue_quality_findings(handoff: Handoff) -> list[Finding]:
    """Every quality finding for ``handoff``'s suggested title and body; empty means it passes.

    Pure and deterministic: ordered by check, then by where (title before body)."""
    return [
        *_title_findings(handoff),
        *_body_shape_findings(handoff),
        *_secret_and_internal_findings(handoff),
        *_wording_findings(handoff),
    ]


def require_issue_quality(handoff: Handoff) -> None:
    """Raise ``HandoffQualityError`` (with the typed findings) when ``handoff`` fails the gate."""
    findings = issue_quality_findings(handoff)
    if findings:
        raise HandoffQualityError(findings)
