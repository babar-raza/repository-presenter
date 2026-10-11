"""BC-14: a version, install command, or publication statement equals what the facts say.

Sealed READMEs carried claims no fact supported: an install version the registry never listed
(`org.aspose:aspose-slides-foss:26.8.0` while Maven Central holds 26.7.0), a renamed package
(`pip install aspose-note` after the package became `aspose-note-foss`), "not published" for a
package a registry lists. Each is a statement a reader acts on, and each is decidable from facts.

The check is conservative by construction: it flags only a statement a fact positively contradicts,
and judges nothing it has no fact for. A registry that could not be read leaves no
`package:published_version` fact, so a version is then held to the manifest alone and the
candidate records a pending note (`claim_notes`) instead of failing.

Five rules, all deterministic and independent of the LLM:

(a) Versions. A version attached to the package name or an install command - ``name==1.2``,
    ``name@1.2``, ``group:artifact:1.2``, ``name version 1.2``, ``--version 1.2``,
    ``Version="1.2"`` - must equal the registry's current stable release when that fact exists,
    else the manifest's version. A CMake ``find_package(Name 1.2 ...)`` is a *request* for a
    compatible version, not a release the README shows: it is held to what CMake would accept
    (the release satisfies it), and ``EXACT`` to equality (Slides-Cpp, wave 6: ``26.9`` for the
    release ``26.9.0`` was read as a wrong release).
(b) Publication. A sentence saying the package is "not (yet) published" must agree with the
    install command's registry observation; it is flagged only when a registry reading says the
    distribution is published - the registry's current release, an install command's own
    observation, or a distribution fact a registry confirmed as this repository's (Slides-Cpp:
    "not yet published on any package registry" beside a NuGet package NuGet lists, wave 3). The
    sentence is read whole, across the physical lines a paragraph wraps it over, and only when it
    is about this package: one that names a different package id and not this package's names
    (3D-.NET, wave 6: the converter tool "is not published to NuGet") is a statement no fact
    covers, so it is not judged.
(c) Identity. An install command whose package is a near-miss of the package identity fact (the
    same name without ``-foss``, a prefix, a different separator) is flagged; an unrelated package
    (a test runner), a declared dependency, and a distribution fact a registry confirmed as this
    repository's own (``package:distribution.*``) are not. A Go package path *below* the module
    path (or one an ``import_path`` fact names) is the module's own path, not a near-miss of it
    (Cells-Go, wave 6).
(d) Exclusivity. A sentence calling a release the "sole", "only" or "first" published version
    (or saying "no other versions" exist) must agree with the registry's version count; the
    current release alone cannot back it.

(e) Licence. The licence is stated once, by the licence fact (the License section renders it from
    the LICENSE file's own text). A sentence that names a ``LicenseRef-`` identifier, or says the
    project is licensed or distributed under a recognised licence other than the one the licence
    fact states, is flagged: Note-Python's Scope read "distributed under the LicenseRef-Aspose-
    Split license" (pyproject metadata) beside an MIT LICENSE file and an MIT License section.

This module imports nothing from `validation/registry.py`: it reports a line index and a causal
stage, and the registry maps the line to its shell section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repository_presenter.components.readme.evidence.facts.license import classify_license_text
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.package_registry import (
    DISTRIBUTION_FACT_PREFIX,
    PUBLISHED_VERSION_FACT_ID,
)

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
# A markdown block opener: a list item, heading, quote, table row or HTML tag starts a new
# paragraph, so a sentence is never joined across two bullets.
_BLOCK_START = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|#{1,6}\s|>|\||<)")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
# A code span that names a package or project rather than a file: one token carrying a separator.
_PACKAGE_ID_SPAN = re.compile(r"^@?[A-Za-z][\w@-]*(?:[./\\:-][\w@-]+)+$")
_DOCUMENT_OR_SOURCE_FILE = re.compile(
    r"(?i)\.(?:md|txt|rst|json|toml|ya?ml|cfg|ini|lock|py|ts|js|cs|java|go|rs|cpp|h|hpp|sh|ps1)$"
)
_GO_MODULE_PATH = re.compile(r"^[\w.-]+\.[A-Za-z]{2,}/\S+$")
# `find_package(Name 1.2 [EXACT] ...)`: a request for a version, not a release the README shows.
_CMAKE_REQUEST = re.compile(
    r"(?i)\b(?:find_package|find_dependency)\s*\(\s*(?P<name>[\w.+-]+)\s+"
    r"(?P<version>\d+(?:\.\d+)*)(?P<rest>[^)\n]*)"
)
_NUMERIC_VERSION = re.compile(r"\d+(?:\.\d+)*")
_REGISTRY_FOUND = re.compile(r"package registry: found")

# "26.7.0 is the sole published version", "the first release", "no other versions": a statement
# that the registry holds exactly one version, or which one came first. Only a registry reading
# that lists every version can back it; the current release alone cannot (rule (d)).
_EXCLUSIVE_VERSION = re.compile(
    r"""(?ix)
    \b(?:sole|only|single|lone|first|initial|inaugural|one\s+and\s+only)\s+
        (?:(?:currently\s+)?(?:published|released|available|public|stable|registry)\s+){0,2}
        (?:version|release)s?\b
  | \bno\s+(?:other|earlier|previous|prior|older|newer|later)\s+
        (?:(?:published|released)\s+)?(?:versions?|releases?)\b
    """
)
_PUBLICATION_WORDS = re.compile(
    r"(?i)\b(?:published|publish|released|registry|pypi|nuget|npm|maven|crates\.io)\b"
)

# A custom SPDX reference names a licence only the repository's own metadata defines.
_LICENSE_REF = re.compile(r"\bLicenseRef-[A-Za-z0-9.-]+")
_LICENSED_UNDER = re.compile(
    r"(?i)\b(?:licensed|distributed|released|available)\s+under\s+(?:the\s+)?"
    r"(?P<name>[A-Za-z][\w.+ -]{1,40}?)\s+licen[cs]e\b"
)

# A sentence about someone else's licence (a dependency, bundled font or optional extra) is not a
# statement of this project's.
_ABOUT_OTHERS = re.compile(
    r"(?i)third[- ]party|dependenc|bundl|vendor|embed|\bfonts?\b|optional|\bextras?\b|incorporat"
    r"|derived|\bcontains?\b|\bincludes?\b"
)

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
    """Every version a README line attaches to one of ``names``.

    A ``find_package(Name 1.2 ...)`` request is not attached: it asks for a version rather than
    showing a release, and ``_cmake_requests`` judges it by what CMake would accept."""
    cleaned = line.replace("`", "")
    requested = {m.start("name") for m in _CMAKE_REQUEST.finditer(cleaned)}
    found: list[str] = []
    for name in names:
        for match in _name_pattern(name).finditer(cleaned):
            if match.start() in requested:
                continue
            tail = _TAIL.match(cleaned[match.end() : match.end() + 90])
            if tail:
                found.append(tail.group("version"))
    return list(dict.fromkeys(found))


def _cmake_requests(line: str, names: list[str]) -> list[tuple[str, bool]]:
    """(version, exact) of each ``find_package(<one of names> <version> [EXACT] ...)`` on a line."""
    patterns = [_name_pattern(name) for name in names]
    found: list[tuple[str, bool]] = []
    for match in _CMAKE_REQUEST.finditer(line.replace("`", "")):
        if any(p.fullmatch(match.group("name")) for p in patterns):
            exact = re.search(r"(?i)\bEXACT\b", match.group("rest")) is not None
            found.append((match.group("version"), exact))
    return list(dict.fromkeys(found))


def _components(version: str) -> tuple[int, ...] | None:
    """The numeric dotted prefix of a release (``26.9.0``, ``v26.7.1-rc1`` -> 26.7.1), or None."""
    matched = _NUMERIC_VERSION.match(_normal_version(version))
    return tuple(int(part) for part in matched.group(0).split(".")) if matched else None


def _request_satisfied(requested: str, exact: bool, release: str) -> bool:
    """Whether CMake would accept ``release`` for ``find_package(Name <requested> [EXACT])``.

    A plain request is a floor on a compatible release: the same leading (major) number and not
    newer than the release, so ``26.9`` and ``26.5`` are met by 26.9.0 and ``26.10``, ``26.9.1``
    and an older year are not. ``EXACT`` is equality, missing trailing components being zero.
    Either side that is not a plain dotted number cannot be judged and is taken as satisfied."""
    want, have = _components(requested), _components(release)
    if want is None or have is None:
        return True
    width = max(len(want), len(have))
    want = want + (0,) * (width - len(want))
    have = have + (0,) * (width - len(have))
    return want == have if exact else want[0] == have[0] and want <= have


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
    requests = [
        (line.index, version, exact)
        for line in lines
        for version, exact in _cmake_requests(line.text, names)
    ]
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
    for index, version, exact in requests:
        if expected is None or _request_satisfied(version, exact, expected):
            continue
        stage = "EXTRACTING" if version in install_values else "COMPOSING"
        findings.append(
            ClaimFinding(
                index,
                stage,
                f"{identity.value} is requested at version {version}"
                f"{' (EXACT)' if exact else ''} by find_package, but {source} is {expected}, "
                "which does not satisfy it",
            )
        )
    return findings, bool(shown or requests)


def _positive_registry_reading(facts: FactsDocument) -> bool:
    """Whether a registry reading says the distribution is published: the registry's current
    release, a distribution a registry confirmed as this repository's own (a C++ library's NuGet
    package, ``package:distribution.*``), or an install command's own registry observation."""
    if _fact(facts, PUBLISHED_VERSION_FACT_ID):
        return True
    if any(
        fact.id.startswith(DISTRIBUTION_FACT_PREFIX) and fact.polarity == "SUPPORTED"
        for fact in facts.facts
    ):
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
    # Every name a registry reading covers: the identity, and a distribution a registry confirmed
    # as this repository's own. A sentence naming one of them is about this package.
    known = patterns + [
        _name_pattern(fact.value)
        for fact in facts.facts
        if fact.id.startswith(DISTRIBUTION_FACT_PREFIX) and fact.polarity == "SUPPORTED"
    ]
    findings: list[ClaimFinding] = []
    flagged: set[int] = set()
    for paragraph in _paragraphs(lines):
        for begin, end in _sentence_spans(paragraph.text):
            sentence = paragraph.text[begin:end]
            plain = sentence.replace("`", "")
            if not _NOT_PUBLISHED.search(plain) or not (
                _PACKAGE_CONTEXT.search(plain) or any(p.search(plain) for p in patterns)
            ):
                continue
            if _names_another_package(sentence, known):
                continue  # about a package no registry reading here covers: nothing contradicts it
            raw = _NOT_PUBLISHED.search(sentence)
            index = paragraph.line_at(begin + (raw.start() if raw else 0))
            if index in flagged:
                continue
            flagged.add(index)
            findings.append(
                ClaimFinding(
                    index,
                    "COMPOSING",
                    f"the README says the package is not published ({plain.strip()!r}), "
                    "but a package-registry reading lists it",
                )
            )
    return sorted(findings, key=lambda finding: finding.line)


@dataclass(frozen=True)
class _Paragraph:
    """A run of prose lines read as one text: a sentence wrapped over lines keeps its subject."""

    text: str
    starts: tuple[tuple[int, int], ...]  # (offset of a line's text within ``text``, its index)

    def line_at(self, offset: int) -> int:
        index = self.starts[0][1]
        for start, line in self.starts:
            if start > offset:
                break
            index = line
        return index


def _paragraphs(lines: list[_Line]) -> list[_Paragraph]:
    """The prose paragraphs of a README: runs of non-blank, non-fenced lines, a list item,
    heading, quote, table row or tag starting a new one."""
    paragraphs: list[_Paragraph] = []
    text = ""
    starts: list[tuple[int, int]] = []

    def flush() -> None:
        nonlocal text, starts
        if starts:
            paragraphs.append(_Paragraph(text, tuple(starts)))
        text, starts = "", []

    for line in lines:
        stripped = line.text.strip()
        if line.in_fence or not stripped:
            flush()
            continue
        if _BLOCK_START.match(line.text):
            flush()
        if starts:
            text += " "
        starts.append((len(text), line.index))
        text += stripped
    flush()
    return paragraphs


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    begin = 0
    for boundary in _SENTENCES.finditer(text):
        spans.append((begin, boundary.start()))
        begin = boundary.end()
    spans.append((begin, len(text)))
    return spans


def _names_another_package(sentence: str, known: list[re.Pattern[str]]) -> bool:
    """Whether a sentence is about a package or project that is not this one.

    It names a package id or project path in a code span (``Aspose.3D.Converter``,
    ``src/converter/Converter.csproj``) and none of this package's names. A registry reading
    covers only the package it read, so a "not published" sentence about the converter beside the
    library is not a statement it contradicts. A sentence that names this package, or names no
    other, is judged as before."""
    if any(pattern.search(sentence.replace("`", "")) for pattern in known):
        return False
    return any(
        _PACKAGE_ID_SPAN.match(token) and not _DOCUMENT_OR_SOURCE_FILE.search(token)
        for token in (span.strip() for span in _CODE_SPAN.findall(sentence))
    )


def _exclusivity_findings(lines: list[_Line], facts: FactsDocument) -> list[ClaimFinding]:
    """Rule (d): "the sole published version" is held to the registry's whole version list.

    Measured on the wave-3 reseal (f69f75c7, 2026-10-11): Aspose.Cells FOSS for Java was sealed
    saying 26.7.0 "is the sole published version" while Maven Central lists 26.5.0 and 26.7.0.
    The registry reading that backs rule (a) names the current release only; whether it is the
    only one is a different fact, ``package:published_version``'s ``version_count``. A statement
    of exclusivity (or of which release came first) passes only when that count is exactly one;
    with a reading but no count it is unverifiable, and an unverifiable exclusivity claim is a
    claim no fact supports, so the sentence is to be rephrased rather than judged. Without any
    reading the rule is silent, as rule (b) is: this check flags only against a reading.
    """
    published = _fact(facts, PUBLISHED_VERSION_FACT_ID)
    if published is None:
        return []  # no registry reading at all: nothing to hold the sentence to (see rule (b))
    count = (published.attributes or {}).get("version_count")
    if count == "1":
        return []
    findings: list[ClaimFinding] = []
    for line in lines:
        if line.in_fence:
            continue
        for sentence in _SENTENCES.split(line.text.replace("`", "")):
            if _EXCLUSIVE_VERSION.search(sentence) and _PUBLICATION_WORDS.search(sentence):
                basis = (
                    f"the registry lists {count} versions"
                    if count
                    else "no registry reading lists every published version"
                )
                findings.append(
                    ClaimFinding(
                        line.index,
                        "COMPOSING",
                        f"the README says which published version is the only or first one "
                        f"({sentence.strip()!r}), but {basis}; state the current release "
                        "without claiming exclusivity",
                    )
                )
                break
    return findings


def _license_findings(lines: list[_Line], facts: FactsDocument) -> list[ClaimFinding]:
    """Rule (e): the licence is whatever the licence fact states, and is stated once.

    Judged only against a SUPPORTED ``license:spdx`` fact (the LICENSE file's text, or a manifest
    declaration when the repository ships no file). A ``LicenseRef-`` identifier is never a
    statement a reader can use; "licensed/distributed under the X license" is flagged only when X
    classifies as a different known licence than the fact's. Silent without the fact."""
    spdx = _fact(facts, "license:spdx")
    if spdx is None or spdx.value == "UNCLASSIFIED":
        return []
    findings: list[ClaimFinding] = []
    for line in lines:
        if line.in_fence:
            continue
        for sentence in _SENTENCES.split(line.text.replace("`", "")):
            reference = _LICENSE_REF.search(sentence)
            stated = _LICENSED_UNDER.search(sentence)
            other = (
                classify_license_text(f"{stated.group('name')} license")
                if stated and not _ABOUT_OTHERS.search(sentence)
                else None
            )
            if reference is not None or (other is not None and other != spdx.value):
                named = reference.group(0) if reference is not None else other
                findings.append(
                    ClaimFinding(
                        line.index,
                        "COMPOSING",
                        f"the README names the licence {named!r} ({sentence.strip()!r}), but the "
                        f"licence fact states {spdx.value}; state the licence once, as the "
                        "License section does",
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


def _inside_module(target: str, identity: str, import_paths: set[str]) -> bool:
    """Whether a Go install target is a package of the module the identity names.

    A Go module owns every path below its own: ``go get <module>/aspose/cells_foss`` installs a
    package of module ``<module>`` and is the form the README's own import line names, so it is
    the same identity, not a near-miss of it. Only a host-first module path qualifies (an npm
    scope or a Maven coordinate has no such prefix rule), and only a path *below* it: the module
    without its ``/v26`` major suffix, or a sibling that merely starts with the same letters, is
    still a near-miss. A path an ``import_path`` fact names is the fact-backed package path, but
    only for a Go module: a Python import name that differs from its distribution is a real
    near-miss as an install target."""
    if not _GO_MODULE_PATH.match(identity):
        return False
    lowered = target.lower()
    return lowered in import_paths or lowered.startswith(identity.lower().rstrip("/") + "/")


def _identity_findings(
    lines: list[_Line], facts: FactsDocument, identity: Fact
) -> list[ClaimFinding]:
    dependencies = {
        _pep503(match.group(0))
        for fact in facts.by_kind("dependency")
        if (match := _REQUIREMENT_NAME.match(fact.value))
    }
    # A distribution the repository's own README names and a registry confirmed as this
    # repository's (a C++ library's NuGet package; its manifest names only a CMake project) is a
    # second fact-backed identity, so an install command naming it is not a near-miss of the first.
    distributions = {
        _pep503(fact.value)
        for fact in facts.facts
        if fact.id.startswith(DISTRIBUTION_FACT_PREFIX) and fact.polarity == "SUPPORTED"
    }
    import_paths = {
        fact.value.lower() for fact in facts.by_kind("import_path") if fact.polarity == "SUPPORTED"
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
            if (
                _same_identity(target, identity.value)
                or _inside_module(target, identity.value, import_paths)
                or _pep503(target) in dependencies
                or _pep503(target) in distributions
            ):
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
        *_exclusivity_findings(lines, facts),
        *_identity_findings(lines, facts, identity),
        *_license_findings(lines, facts),
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
