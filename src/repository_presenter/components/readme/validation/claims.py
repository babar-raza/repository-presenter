"""BC-14: a version, install command, or publication statement equals what the facts say.

Sealed READMEs carried claims no fact supported: an install version the registry never listed
(`org.aspose:aspose-slides-foss:26.8.0` while Maven Central holds 26.7.0), a renamed package
(`pip install aspose-note` after the package became `aspose-note-foss`), "not published" for a
package a registry lists. Each is a statement a reader acts on, and each is decidable from facts.

The check is conservative by construction: it flags only a statement a fact positively contradicts,
and judges nothing it has no fact for. A registry that could not be read leaves no
`package:published_version` fact, so a version is then held to the manifest alone and the
candidate records a pending note (`claim_notes`) instead of failing.

Three rules, all deterministic and independent of the LLM:

(a) Versions. A version attached to the package name or an install command - ``name==1.2``,
    ``name@1.2``, ``group:artifact:1.2``, ``name version 1.2``, ``--version 1.2``,
    ``Version="1.2"`` - must equal the registry's current stable release when that fact exists,
    else the manifest's version.
(b) Publication. A sentence saying the package is "not (yet) published" must agree with the
    install command's registry observation; it is flagged only when a registry reading says the
    distribution is published.
(c) Identity. An install command whose package is a near-miss of the package identity fact (the
    same name without ``-foss``, a prefix, a different separator) is flagged; an unrelated package
    (a test runner) and a declared dependency are not.

This module imports nothing from `validation/registry.py`: it reports a line index and a causal
stage, and the registry maps the line to its shell section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID

_VERSION = r"v?\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.]*[0-9A-Za-z])?"
_VERSION_RE = re.compile(_VERSION)
_SOURCE_KINDS = frozenset({"source", "source_checkout"})
_SEPARATORS = re.compile(r"[-_.]+")
_STEM_SPLIT = re.compile(r"[-_.:/@]+")
_REQUIREMENT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")

# What may follow a package name for a version to be "attached" to it.
_TAIL = re.compile(
    rf"""^
    (?:
        [`'"*)\s]*(?:@|==|=|:|~=)\s*[\^~]?v?          # name@1.2  name==1.2  g:a:1.2
      | [`'"*)\s]*(?:[\w-]+[\s,]+){{0,4}}(?:version|release)\s+[`'"]?v?   # name ... version 1.2
      | \s+(?:--version|-v)[\s=]+[`'"]?v?             # dotnet add package N --version 1.2
      | ["']?\s+Version\s*=\s*["']v?                  # <PackageReference Include="N" Version="1.2"
      | \s*=\s*["']\^?~?v?                            # name = "1.2"   (Cargo.toml)
      | [`'"*)\s]+v?                                  # name 1.2
    )
    (?P<version>{_VERSION.removeprefix("v?")})
    """,
    re.VERBOSE | re.IGNORECASE,
)
_POM_PAIR = re.compile(
    rf"<artifactId>\s*(?P<name>[^<\s]+)\s*</artifactId>\s*<version>\s*(?P<version>{_VERSION})\s*"
    r"</version>"
)

_NOT_PUBLISHED = re.compile(
    r"""(?ix)
    \b(?:
        unpublished
      | not \s+ (?:yet \s+)? (?:been \s+)? (?:published|released)
      | not \s+ (?:yet \s+)? (?:available|listed) \s+ (?:on|in|from) \s+
        (?:any \s+ |the \s+)? (?:package \s+ )?(?:registry|pypi|nuget|npm|maven|crates\.io)
    )\b"""
)
_PACKAGE_CONTEXT = re.compile(
    r"(?i)\b(?:package|library|sdk|registry|pypi|nuget|npm|maven|crates\.io)\b"
)
_SENTENCES = re.compile(r"(?<=[.!?])\s+")
_REGISTRY_FOUND = re.compile(r"package registry: found")

_INSTALL_VERBS = (
    re.compile(r"^(?:python3?\s+-m\s+)?pip3?\s+install\b(?P<rest>.*)$"),
    re.compile(r"^(?:npm\s+(?:install|i|add)|yarn\s+add|pnpm\s+(?:add|install))\b(?P<rest>.*)$"),
    re.compile(r"^dotnet\s+add\s+(?:\S+\s+)?package\b(?P<rest>.*)$"),
    re.compile(r"^(?:Install-Package|nuget\s+install)\b(?P<rest>.*)$", re.IGNORECASE),
    re.compile(r"^cargo\s+add\b(?P<rest>.*)$"),
    re.compile(r"^go\s+(?:get|install)\b(?P<rest>.*)$"),
)
# Flags that consume the next token, so it is not mistaken for a package.
_VALUE_FLAGS = frozenset(
    {
        "-r", "-c", "-e", "-i", "-f", "-t", "-v", "-s", "-p", "-F", "-n", "-d",
        "--requirement", "--constraint", "--editable", "--index-url", "--extra-index-url",
        "--find-links", "--target", "--prefix", "--root", "--registry", "--version",
        "--framework", "--source", "--project", "--features", "--git", "--path", "--branch",
        "--tag", "--rev", "--package",
    }
)  # fmt: skip
_PROMPT = re.compile(r"^(?:[$>]\s+|PS>\s+)")


@dataclass(frozen=True)
class ClaimFinding:
    """One statement a fact contradicts: where, which stage owns the defect, and why."""

    line: int
    stage: str  # "EXTRACTING" (a fact carries the defect) or "COMPOSING" (only the prose does)
    detail: str


def _fact(facts: FactsDocument, fact_id: str) -> Fact | None:
    return next((f for f in facts.facts if f.id == fact_id and f.polarity == "SUPPORTED"), None)


def _normal_version(version: str) -> str:
    return version.strip().removeprefix("v").removeprefix("V")


def _pep503(name: str) -> str:
    return _SEPARATORS.sub("-", name).lower()


def _stem(name: str) -> str:
    return "".join(part for part in _STEM_SPLIT.split(name.lower()) if part and part != "foss")


def _names(identity: str) -> list[str]:
    """The spellings a README gives the package: the whole identity and a Maven artifactId."""
    names = [identity]
    if ":" in identity:
        names.append(identity.split(":", 1)[1])
    return names


def _name_pattern(name: str) -> re.Pattern[str]:
    body = "".join("[-_.]" if ch in "-_." else re.escape(ch) for ch in name)
    return re.compile(rf"(?<![A-Za-z0-9_.-]){body}(?![A-Za-z0-9_-]|\.[A-Za-z0-9])", re.IGNORECASE)


@dataclass(frozen=True)
class _Line:
    index: int
    text: str
    in_fence: bool


def _lines(readme: str) -> list[_Line]:
    lines: list[_Line] = []
    inside = False
    for index, raw in enumerate(readme.splitlines()):
        stripped = raw.strip()
        if stripped.startswith(("```", "~~~")):
            inside = not inside
            lines.append(_Line(index, raw, True))
            continue
        lines.append(_Line(index, raw, inside))
    return lines


def _attached_versions(line: str, names: list[str]) -> list[str]:
    """Every version a README line attaches to one of ``names``."""
    cleaned = line.replace("`", "")
    found: list[str] = []
    for name in names:
        for match in _name_pattern(name).finditer(cleaned):
            tail = _TAIL.match(cleaned[match.end() : match.end() + 90])
            if tail:
                found.append(tail.group("version"))
    return list(dict.fromkeys(found))


def _pom_versions(readme: str, names: list[str]) -> list[tuple[int, str]]:
    """(line, version) of each ``<artifactId>name</artifactId><version>v</version>`` pair - the
    one shape whose name and version sit on different lines."""
    found: list[tuple[int, str]] = []
    for pair in _POM_PAIR.finditer(readme):
        if any(_name_pattern(name).fullmatch(pair.group("name")) for name in names):
            found.append((readme.count("\n", 0, pair.start("version")), pair.group("version")))
    return found


def _version_findings(
    readme: str, lines: list[_Line], facts: FactsDocument, identity: Fact
) -> tuple[list[ClaimFinding], bool]:
    """(rule (a) findings, whether any version was attached to the package at all)."""
    published = _fact(facts, PUBLISHED_VERSION_FACT_ID)
    manifest = _fact(facts, "package:version")
    expected, source = (
        (published.value, "the registry's current stable release")
        if published
        else (manifest.value, "the manifest's version")
        if manifest
        else (None, "")
    )
    install_values = " ".join(f.value for f in facts.by_kind("install_command"))
    findings: list[ClaimFinding] = []
    names = _names(identity.value)
    shown = [(line.index, v) for line in lines for v in _attached_versions(line.text, names)]
    shown.extend(_pom_versions(readme, names))
    for index, version in shown:
        if expected is None or _normal_version(version) == _normal_version(expected):
            continue
        # The offending text sits in an install fact's own value: the defect is upstream of
        # the prose, and recomposing the section cannot fix it.
        stage = "EXTRACTING" if version in install_values else "COMPOSING"
        findings.append(
            ClaimFinding(
                index,
                stage,
                f"{identity.value} is shown at version {version}, but {source} is {expected}",
            )
        )
    return findings, bool(shown)


def _positive_registry_reading(facts: FactsDocument) -> bool:
    """Whether a registry reading says the distribution is published."""
    if _fact(facts, PUBLISHED_VERSION_FACT_ID):
        return True
    for fact in facts.by_kind("install_command"):
        if (fact.attributes or {}).get("install_kind") in _SOURCE_KINDS:
            continue
        details = " ".join(e.detail or "" for e in fact.evidence)
        if _REGISTRY_FOUND.search(details) and "manifest version not published" not in details:
            return True
    return False


def _publication_findings(
    lines: list[_Line], facts: FactsDocument, identity: Fact
) -> list[ClaimFinding]:
    if not _positive_registry_reading(facts):
        return []
    patterns = [_name_pattern(name) for name in _names(identity.value)]
    findings: list[ClaimFinding] = []
    for line in lines:
        if line.in_fence:
            continue
        for sentence in _SENTENCES.split(line.text.replace("`", "")):
            if _NOT_PUBLISHED.search(sentence) and (
                _PACKAGE_CONTEXT.search(sentence) or any(p.search(sentence) for p in patterns)
            ):
                findings.append(
                    ClaimFinding(
                        line.index,
                        "COMPOSING",
                        f"the README says the package is not published ({sentence.strip()!r}), "
                        "but a package-registry reading lists it",
                    )
                )
                break
    return findings


def _install_targets(command: str) -> list[str]:
    """The package names on one install command line, versions and extras removed."""
    command = _PROMPT.sub("", command.strip())
    for verb in _INSTALL_VERBS:
        matched = verb.match(command)
        if matched is None:
            continue
        targets: list[str] = []
        tokens = matched.group("rest").split()
        skip = False
        for token in tokens:
            if skip:
                skip = False
                continue
            if token.startswith("-"):
                skip = token in _VALUE_FLAGS and "=" not in token
                continue
            if token in {".", ".."} or "://" in token or token.startswith(("git+", "./", "../")):
                continue
            token = token.strip("\"'")
            if token.startswith("@"):  # an npm scope: @scope/name[@version]
                name, _, _ = token[1:].partition("@")
                targets.append("@" + name)
                continue
            name = re.split(r"==|~=|>=|<=|!=|@|=|:(?=\d)|\[", token, maxsplit=1)[0]
            module = name.startswith(("github.com/", "golang.org/"))
            if module or (name and not name.startswith((".", "/")) and "/" not in name):
                targets.append(name)
        return targets
    return []


def _maven_target(command: str) -> str | None:
    matched = re.search(r"-Dartifact=([\w.-]+:[\w.-]+)", command)
    return matched.group(1) if matched else None


def _same_identity(target: str, identity: str) -> bool:
    return _pep503(target) == _pep503(identity) or target.lower() == identity.lower()


def _identity_findings(
    lines: list[_Line], facts: FactsDocument, identity: Fact
) -> list[ClaimFinding]:
    dependencies = {
        _pep503(match.group(0))
        for fact in facts.by_kind("dependency")
        if (match := _REQUIREMENT_NAME.match(fact.value))
    }
    stem = _stem(identity.value)
    install_values = " ".join(f.value for f in facts.by_kind("install_command"))
    findings: list[ClaimFinding] = []
    for line in lines:
        if not line.in_fence:
            continue
        targets = _install_targets(line.text)
        coordinate = _maven_target(line.text)
        if coordinate:
            targets.append(coordinate)
        for target in targets:
            if _same_identity(target, identity.value) or _pep503(target) in dependencies:
                continue
            candidate = _stem(target)
            if candidate and stem and (candidate.startswith(stem) or stem.startswith(candidate)):
                stage = "EXTRACTING" if target in install_values else "COMPOSING"
                findings.append(
                    ClaimFinding(
                        line.index,
                        stage,
                        f"the install command names {target!r}, but the package identity is "
                        f"{identity.value!r}",
                    )
                )
    return findings


def claim_findings(readme: str, facts: FactsDocument) -> list[ClaimFinding]:
    """Every statement in ``readme`` that a fact in ``facts`` positively contradicts."""
    identity = _fact(facts, "package:name")
    if identity is None:
        return []
    lines = _lines(readme)
    versions, _ = _version_findings(readme, lines, facts, identity)
    return [
        *versions,
        *_publication_findings(lines, facts, identity),
        *_identity_findings(lines, facts, identity),
    ]


def claim_notes(readme: str, facts: FactsDocument) -> list[str]:
    """A pending note when a version is shown but no registry reading backs or refutes it."""
    identity = _fact(facts, "package:name")
    if identity is None or _fact(facts, PUBLISHED_VERSION_FACT_ID) is not None:
        return []
    _, attached = _version_findings(readme, _lines(readme), facts, identity)
    if not attached:
        return []
    return [
        "BC-14 pending: the README shows a package version, but no registry reading of the "
        f"current release ({PUBLISHED_VERSION_FACT_ID}) exists (registry unreachable, package "
        "unpublished, or no registry for this ecosystem); the version was held to the manifest only"
    ]
