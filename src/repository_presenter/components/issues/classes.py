"""The defect-class registry: which kinds of upstream defect this system can detect on its own.

Until G6-W07 a handoff's ``triggering_check`` named a ``BC-*`` validation check or
``NOT_PROCESSABLE``, and ``draft.py`` drafted only ``BC-02``. The four lane reviews and the issue
inventory (``docs/investigations/03-issue-tracking.md``) found real upstream defects that no check
names: a license that exists only under ``License/`` or not at all, a manifest that still carries
``yourorg`` URLs and an author called ``SID``, a README that is 69 bytes. This module is where each
such kind is declared once:

- a **detector**: a pure function from an ``Observation`` (the pinned file list plus the text of
  the few files it needs) to findings. No network, clock, model or filesystem; the same
  observation always gives the same findings in the same order;
- a **redetector**: how a later pass asks whether the defect still fires at the repository's
  current revision. Detectable classes share one (``_redetect_class``: re-read the tree, rebuild
  the observation, run the detector, compare fingerprints) registered in ``redetect.py`` under the
  class id; the three classes that reuse existing evidence name the existing check id instead;
- an **issue template** (``IssueTemplate``): the fixed prose around the fields a detector fills;
- a **severity**, used only to order findings; and
- a **fingerprint basis**: what the detector's ``signature`` is made of, so the dedup key
  (``fingerprint``) is stable under rewording and does not move when an unrelated field is fixed.

Classes register by decorator (``@defect_class``) the way redetectors register in ``redetect.py``;
there is no ``if/elif`` chain. A detectable class's handoff carries the class id as its
``triggering_check.id`` and in ``defect_class``, so it cannot collide with a ``BC-*`` fingerprint
(the fingerprint hashes the check id) and the existing redetector dispatch needs nothing new.

``SOURCE_UNPARSEABLE``, ``BUILD_OR_TESTS_FAIL``, ``EXAMPLE_FAILS`` and ``INSTALL_FAILS`` need
evidence only a measured build, a measured example run or a source parse can give, so they have no
facts-only detector here; they are declared with the existing check (``NOT_PROCESSABLE``,
``BC-02``, ``BC-03``) whose handoff and redetector already carry them, and the registry says so
rather than leaving them out.

Detectors read only data the pipeline already has: the tree listing, and the text of the root
README, the root license and the manifests (read through one callable, so a clone and a GitHub
read feed the same code). They never import an extractor.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Literal

from repository_presenter.components.issues import redetect as _redetect
from repository_presenter.components.issues.model import (
    DEFECT_CLASSES,
    EvidenceEntry,
    Handoff,
)
from repository_presenter.components.readme.evidence.facts.license import (
    classify_declaration,
    classify_license_text,
)
from repository_presenter.core.snapshot.inventory import README_FILENAMES

Severity = Literal["high", "medium", "low"]
_SEVERITY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}

# What a detector may need read besides the tree listing; the generic redetector fetches only
# these, so a class that needs nothing costs one tree read.
NEED_README = "readme"
NEED_LICENSE = "license"
NEED_MANIFESTS = "manifests"

MAX_FILE_BYTES = 1_000_000
MAX_MANIFESTS = 5
MAX_MANIFEST_FIELDS = 400
# A README at or under this size, saying nothing a visitor can act on, is a placeholder
# (Aspose.PSD-FOSS-for-Python: 69 bytes, "FOSS version of Aspose.PSD for Python").
PLACEHOLDER_README_MAX_BYTES = 200
PLACEHOLDER_README_MAX_WORDS = 12


# --- the observation -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestMetadata:
    """One manifest's leaf string values, flattened to ``(dotted key, value)`` in document order."""

    path: str
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Observation:
    """Everything a detector may read about one repository at one pinned revision."""

    repository: str
    source_revision: str
    tree_paths: tuple[str, ...]
    readme_text: str | None = None
    license_texts: Mapping[str, str] = field(default_factory=dict)
    manifests: tuple[ManifestMetadata, ...] = ()
    # Tree files a reader tried and failed to read: a detector that finds nothing while one of
    # these exists cannot say the defect is gone, and the redetector reports it inconclusive.
    unreadable: tuple[str, ...] = ()

    @property
    def root_entries(self) -> tuple[str, ...]:
        return tuple(sorted({p.split("/", 1)[0] for p in self.tree_paths}))


@dataclass(frozen=True)
class DefectFinding:
    """One defect a detector found: the stable ``signature`` the dedup key is made from, the
    defect statement the title carries, the fields the template fills, and the evidence."""

    defect_class: str
    signature: str
    statement: str
    claim: str
    fields: Mapping[str, str]
    evidence: tuple[EvidenceEntry, ...]


Detector = Callable[[Observation], list[DefectFinding]]


@dataclass(frozen=True)
class IssueTemplate:
    """The fixed prose of an issue, as ``str.format`` strings over ``DefectFinding.fields`` plus
    ``repository``, ``revision`` and ``product``. ``steps`` is the body of the reproduction code
    block."""

    summary: str
    steps: str
    expected: str
    actual: str


@dataclass(frozen=True)
class DefectClass:
    id: str
    severity: Severity
    fingerprint_basis: str
    # The ``triggering_check.id`` whose registered redetector replays this class's handoffs: the
    # class's own id for a detectable class, an existing check id for a mapped one.
    redetector: str
    detector: Detector | None = None
    template: IssueTemplate | None = None
    needs: frozenset[str] = frozenset()

    @property
    def detector_name(self) -> str | None:
        return None if self.detector is None else self.detector.__name__


REGISTRY: dict[str, DefectClass] = {}


def _replay(handoff: Handoff, reads: _redetect.RedetectionReads) -> _redetect.RedetectionResult:
    return _redetect_class(handoff, reads)


def fingerprint(repository: str, check_id: str, signature: str) -> str:
    """sha256 of ``{repository, triggering_check.id, signature}``: the dedup key of
    ``schemas/upstream-defect-handoff.schema.json``."""
    digest = hashlib.sha256(f"{repository}\n{check_id}\n{signature}".encode()).hexdigest()
    return f"sha256:{digest}"


def defect_class(
    class_id: str,
    *,
    severity: Severity,
    fingerprint_basis: str,
    template: IssueTemplate,
    needs: frozenset[str] = frozenset(),
) -> Callable[[Detector], Detector]:
    """Register a detector as the class ``class_id``, and the shared redetector under its id."""

    def _decorator(fn: Detector) -> Detector:
        if class_id not in DEFECT_CLASSES:
            raise ValueError(f"{class_id!r} is not a defect class the handoff schema admits")
        if class_id in REGISTRY:
            raise ValueError(f"defect class {class_id!r} is registered twice")
        REGISTRY[class_id] = DefectClass(
            id=class_id,
            severity=severity,
            fingerprint_basis=fingerprint_basis,
            redetector=class_id,
            detector=fn,
            template=template,
            needs=needs,
        )
        _redetect.register(class_id)(_replay)
        return fn

    return _decorator


def declare_mapped(
    class_id: str, *, severity: Severity, redetector: str, fingerprint_basis: str
) -> None:
    """Declare a class with no facts-only detector, carried by an existing check's handoff."""
    if class_id not in DEFECT_CLASSES:
        raise ValueError(f"{class_id!r} is not a defect class the handoff schema admits")
    REGISTRY[class_id] = DefectClass(
        id=class_id,
        severity=severity,
        fingerprint_basis=fingerprint_basis,
        redetector=redetector,
    )


# --- reading the files a detector needs ----------------------------------------------------------

_LICENSE_NAME = re.compile(r"^(?:licen[sc]e|copying|unlicense)(?:[-_.][\w.-]*)?$", re.IGNORECASE)
# A path under one of these is not the repository's own license (a vendored dependency's, a
# generated doc site's).
_NOT_OWN = frozenset(
    {
        "node_modules", "vendor", "third_party", "third-party", "thirdparty", "external", "deps",
        "dist", "build", "bin", "obj", "docs", "doc", "apidocs", "legal", "legacy", "samples",
        "examples", "tests", "test",
    }
)  # fmt: skip
_MANIFEST_NAME = re.compile(
    r"(?:^|/)(?:[^/]+\.(?:csproj|fsproj|vbproj|props)|package\.json|pyproject\.toml|Cargo\.toml"
    r"|pom\.xml)$",
    re.IGNORECASE,
)
_NON_PACKAGE_DIR = re.compile(
    r"(?:^|[._-])(?:tests?|samples?|examples?|docs?|benchmarks?)(?:$|[._-])", re.IGNORECASE
)
_DEPENDENCY_SECTIONS = frozenset(
    {
        "dependencies", "devdependencies", "peerdependencies", "optionaldependencies",
        "dev-dependencies", "build-dependencies", "scripts", "optional-dependencies",
        "dependency-groups",
    }
)  # fmt: skip
_XML_LEAF = re.compile(r"<([A-Za-z][\w.-]*)>([^<>]*)</\1>")


def root_license_paths(tree_paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(p for p in tree_paths if "/" not in p and _LICENSE_NAME.match(p)))


def elsewhere_license_paths(tree_paths: tuple[str, ...]) -> tuple[str, ...]:
    """License files below the root that plausibly are the repository's own: shallow, and not
    under a vendored, generated or sample directory. Shallowest first, then by path."""
    found = []
    for path in tree_paths:
        parts = PurePosixPath(path).parts
        if len(parts) < 2 or len(parts) > 3 or not _LICENSE_NAME.match(parts[-1]):
            continue
        if any(part.lower() in _NOT_OWN for part in parts[:-1]):
            continue
        found.append(path)
    return tuple(sorted(found, key=lambda p: (p.count("/"), p)))


def root_readme_path(tree_paths: tuple[str, ...]) -> str | None:
    root = sorted(p for p in tree_paths if "/" not in p and p.lower() in README_FILENAMES)
    return root[0] if root else None


def candidate_manifests(
    tree_paths: tuple[str, ...], hints: tuple[str, ...] = ()
) -> tuple[str, ...]:
    """The manifests whose metadata a detector reads: ``hints`` that are in the tree first (the
    one the pipeline's plugin chose, or one a handoff's evidence cites), then the shallowest
    package manifests, never one under a test, sample, example or vendored directory."""
    in_tree = set(tree_paths)
    chosen = [h for h in hints if h in in_tree and _MANIFEST_NAME.search(h)]
    rest = []
    for path in tree_paths:
        parts = PurePosixPath(path).parts
        if not _MANIFEST_NAME.search(path) or path in chosen or len(parts) > 3:
            continue
        if any(part.lower() in _NOT_OWN or _NON_PACKAGE_DIR.search(part) for part in parts[:-1]):
            continue
        if len(parts) > 1 and _NON_PACKAGE_DIR.search(PurePosixPath(parts[-1]).stem):
            continue
        rest.append(path)
    rest.sort(key=lambda p: (p.count("/"), p))
    return tuple(dict.fromkeys([*chosen, *rest]))[:MAX_MANIFESTS]


def _flatten(value: object, prefix: str, out: list[tuple[str, str]]) -> None:
    if len(out) >= MAX_MANIFEST_FIELDS:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _DEPENDENCY_SECTIONS:
                continue
            _flatten(child, f"{prefix}.{key}" if prefix else str(key), out)
    elif isinstance(value, list):
        for index, child in enumerate(value[:20]):
            _flatten(child, f"{prefix}.{index}", out)
    elif isinstance(value, str) and value.strip():
        out.append((prefix, value.strip()))


def parse_manifest_metadata(path: str, text: str) -> ManifestMetadata:
    """The manifest's leaf string values; a manifest that does not parse yields no fields (a
    detector then says nothing about it). XML manifests are read by tag, never by an XML parser,
    so an untrusted file's entity tricks never run."""
    out: list[tuple[str, str]] = []
    text = text.removeprefix("﻿")
    name = PurePosixPath(path).name.lower()
    try:
        if name.endswith(".json"):
            _flatten(json.loads(text), "", out)
        elif name.endswith(".toml"):
            _flatten(tomllib.loads(text), "", out)
        else:
            out.extend((m.group(1), m.group(2).strip()) for m in _XML_LEAF.finditer(text))
            out = [(k, v) for k, v in out if v][:MAX_MANIFEST_FIELDS]
    except (ValueError, tomllib.TOMLDecodeError):
        out = []
    return ManifestMetadata(path=path, fields=tuple(out))


def build_observation(
    repository: str,
    source_revision: str,
    tree_paths: tuple[str, ...],
    read_text: Callable[[str], str | None],
    *,
    needs: frozenset[str] = frozenset({NEED_README, NEED_LICENSE, NEED_MANIFESTS}),
    manifest_hints: tuple[str, ...] = (),
) -> Observation:
    """An ``Observation`` from a tree listing and one way to read a file at that revision (a
    clone, or the GitHub contents API): ``read_text(path)`` is the text, or ``None`` when it could
    not be read."""
    unreadable: list[str] = []

    def read(path: str) -> str | None:
        text = read_text(path)
        if text is None:
            unreadable.append(path)
        return text

    readme_path = root_readme_path(tree_paths)
    readme_text = read(readme_path) if NEED_README in needs and readme_path else None
    license_texts: dict[str, str] = {}
    if NEED_LICENSE in needs:
        for path in root_license_paths(tree_paths)[:3]:
            text = read(path)
            if text is not None:
                license_texts[path] = text
    manifests: list[ManifestMetadata] = []
    if NEED_MANIFESTS in needs:
        for path in candidate_manifests(tree_paths, manifest_hints):
            text = read(path)
            if text is not None:
                manifests.append(parse_manifest_metadata(path, text))
    return Observation(
        repository=repository,
        source_revision=source_revision,
        tree_paths=tuple(tree_paths),
        readme_text=readme_text,
        license_texts=license_texts,
        manifests=tuple(manifests),
        unreadable=tuple(unreadable),
    )


def observation_from_clone(
    repository: str,
    source_revision: str,
    clone_path: Path,
    tree_paths: tuple[str, ...],
    *,
    manifest: Path | None = None,
) -> Observation:
    """The observation ``present`` already has the inputs for: the verified clone and its tree
    listing, with the manifest the plugin chose read first."""
    root = clone_path.resolve()

    def read(path: str) -> str | None:
        target = (root / path).resolve()
        try:
            target.relative_to(root)
            if not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
                return None
            # Bytes, not text mode: a README's size is the file's own, not a translated one.
            return target.read_bytes().decode("utf-8", errors="replace")
        except (OSError, ValueError):
            return None

    hints: tuple[str, ...] = ()
    if manifest is not None:
        try:
            hints = (manifest.resolve().relative_to(root).as_posix(),)
        except ValueError:
            hints = ()
    return build_observation(
        repository, source_revision, tuple(tree_paths), read, manifest_hints=hints
    )


# --- detectors -----------------------------------------------------------------------------------


def _ls_tree(revision: str) -> str:
    return f"git ls-tree --name-only {revision}"


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def _tick(text: str) -> str:
    return text.replace("`", "'")


def _declared_licenses(observation: Observation) -> list[tuple[str, str, str]]:
    """``(manifest path, raw declaration, SPDX id)`` for each manifest license declaration that
    names a known license."""
    found = []
    for manifest in observation.manifests:
        for key, value in manifest.fields:
            parts = key.lower().split(".")
            is_declaration = parts[-1] in {"license", "packagelicenseexpression"} or parts[-2:] == [
                "license",
                "text",
            ]
            spdx = classify_declaration(value) if is_declaration else None
            if spdx is not None:
                found.append((manifest.path, value, spdx))
    return found


@defect_class(
    "LICENSE_MISSING_ROOT",
    severity="high",
    fingerprint_basis="the repository alone: one root-license defect per repository, whether the "
    "license is absent or sits in a sub-folder, so adding a folder never mints a second report",
    needs=frozenset({NEED_MANIFESTS}),
    template=IssueTemplate(
        summary="At revision `{revision}` the repository has no license file at its root{detail}.",
        steps=_ls_tree("{revision}") + "\n" + "gh api repos/{repository} --jq .license",
        expected=(
            "A license file at the repository root (for example `LICENSE`), so GitHub license "
            "detection and package scanners, which read only the root, can identify the license."
        ),
        actual="{actual}",
    ),
)
def detect_license_missing_root(observation: Observation) -> list[DefectFinding]:
    tree = observation.tree_paths
    if not tree or root_license_paths(tree):
        return []
    elsewhere = elsewhere_license_paths(tree)
    declared = _declared_licenses(observation)
    revision = observation.source_revision
    evidence = [
        EvidenceEntry(path=_ls_tree(revision), detail="no license file among the root entries")
    ]
    if elsewhere:
        moved = elsewhere[0]
        folder = moved.rsplit("/", 1)[0]
        statement = f"the license file is only in {folder}/, not at the repository root"
        actual = (
            f"The only license file is `{moved}`; the root listing has none, so the repository "
            "page shows no license."
        )
        detail = f", only `{moved}`"
        evidence.append(EvidenceEntry(path=moved, detail="the only license file in the tree"))
    else:
        statement = "no license file at the repository root"
        actual = "The root listing has no license file, and none exists elsewhere in the tree."
        detail = ""
    if declared:
        manifest_path, raw, _ = declared[0]
        actual += f" `{manifest_path}` declares the license as `{_tick(raw)}`."
        evidence.append(EvidenceEntry(path=manifest_path, detail=f"declares license {raw}"))
    claim = f"At revision {revision}, {observation.repository} has no license file at its root" + (
        f" (the only one is {elsewhere[0]})." if elsewhere else "."
    )
    return [
        DefectFinding(
            defect_class="LICENSE_MISSING_ROOT",
            signature="no license file at the root",
            statement=statement,
            claim=claim,
            fields={"detail": detail, "actual": actual},
            evidence=tuple(evidence),
        )
    ]


@defect_class(
    "LICENSE_MISMATCH",
    severity="high",
    fingerprint_basis="the root license file, the manifest and the two license identifiers they "
    "state; fixing either side changes the signature, so a fixed mismatch never matches again",
    needs=frozenset({NEED_LICENSE, NEED_MANIFESTS}),
    template=IssueTemplate(
        summary=(
            "At revision `{revision}` the license file `{license_path}` states {file_spdx}, while "
            "`{manifest_path}` declares {declared_spdx}."
        ),
        steps="head -n 5 {license_path}\ngrep -n -i license {manifest_path}",
        expected="The license file and the manifest name the same license.",
        actual=(
            "- `{license_path}`: the text is the {file_spdx} license.\n"
            "- `{manifest_path}`: declares `{declared}`, which is {declared_spdx}."
        ),
    ),
)
def detect_license_mismatch(observation: Observation) -> list[DefectFinding]:
    revision = observation.source_revision
    findings = []
    for license_path, text in sorted(observation.license_texts.items()):
        file_spdx = classify_license_text(text)
        if file_spdx is None:
            continue
        for manifest_path, raw, declared_spdx in _declared_licenses(observation):
            if declared_spdx == file_spdx:
                continue
            findings.append(
                DefectFinding(
                    defect_class="LICENSE_MISMATCH",
                    signature=f"{license_path}:{file_spdx} != {manifest_path}:{declared_spdx}",
                    statement=f"{license_path} is {file_spdx} but "
                    f"{PurePosixPath(manifest_path).name}"
                    f" declares {declared_spdx}",
                    claim=(
                        f"At revision {revision}, {observation.repository}'s {license_path} states "
                        f"{file_spdx} while {manifest_path} declares {declared_spdx}."
                    ),
                    fields={
                        "license_path": license_path,
                        "file_spdx": file_spdx,
                        "manifest_path": manifest_path,
                        "declared": _tick(raw),
                        "declared_spdx": declared_spdx,
                    },
                    evidence=(
                        EvidenceEntry(path=license_path, detail=f"license text states {file_spdx}"),
                        EvidenceEntry(path=manifest_path, detail=f"declares license {raw}"),
                    ),
                )
            )
    return findings


# Owners and hosts a template leaves behind. A repository URL on a code host under one of these
# owners is not the project's.
_PLACEHOLDER_OWNERS = frozenset(
    {
        "yourorg", "your-org", "your_org", "yourusername", "your-username", "your_username",
        "yourname", "your-name", "yourcompany", "your-company", "username", "user-name", "owner",
        "org", "organization", "orgname", "org-name", "myorg", "my-org", "myusername", "example",
        "changeme", "todo",
    }
)  # fmt: skip
_PLACEHOLDER_HOSTS = frozenset({"example.com", "www.example.com", "example.org", "example.net"})
_CODE_HOSTS = frozenset({"github.com", "gitlab.com", "bitbucket.org"})
# Author, company and description values that are what a template or a build tool left, not a
# name. "SID" is the account name MSBuild wrote into Aspose.PSD-FOSS-for-.NET's csproj and into
# generated files in its Python sibling.
_PLACEHOLDER_VALUES = frozenset(
    {
        "sid", "your name", "yourname", "your company", "yourcompany", "author", "authors",
        "company", "unknown", "todo", "tbd", "tba", "name", "owner", "anonymous", "n/a", "none",
        "changeme", "fixme", "xxx", "package description", "project description",
        "your description", "description",
    }
)  # fmt: skip
_BRACKETED = re.compile(r"^[<{\[].*[>}\]]$")
_URL_HOST_PATH = re.compile(
    r"^(?:git\+)?(?:[a-z][a-z0-9+.-]*://)?(?:[^/@\s]+@)?(?P<host>[^/:\s]+)[/:](?P<path>\S*)$",
    re.IGNORECASE,
)
_AUTHOR_PARTS = frozenset({"author", "authors", "maintainer", "maintainers", "company", "owners"})
_URL_KEY_NAMES = frozenset({"homepage", "repository", "documentation", "bugs", "issues", "source"})


def _placeholder_url(value: str) -> bool:
    match = _URL_HOST_PATH.match(value.strip())
    if match is None or ("://" not in value and not value.lower().startswith("git@")):
        return False
    host = match.group("host").lower()
    if host in _PLACEHOLDER_HOSTS:
        return True
    if host not in _CODE_HOSTS:
        return False
    owner = match.group("path").strip("/").split("/", 1)[0].lower()
    return owner in _PLACEHOLDER_OWNERS or bool(_BRACKETED.match(owner))


def _placeholder_name(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in _PLACEHOLDER_VALUES or _BRACKETED.match(lowered):
        return True
    email = re.search(r"[\w.+-]+@([\w.-]+)", lowered)
    return bool(email and email.group(1) in _PLACEHOLDER_HOSTS)


def _placeholder_hits(manifest: ManifestMetadata) -> list[tuple[str, str]]:
    hits = []
    for key, value in manifest.fields:
        parts = key.lower().split(".")
        last = parts[-1]
        is_url_key = "url" in last or last in _URL_KEY_NAMES
        is_author = bool(_AUTHOR_PARTS.intersection(parts)) and not is_url_key
        is_description = last == "description"
        if (
            (is_url_key and _placeholder_url(value))
            or (is_author and _placeholder_name(value))
            or (is_description and value.strip().lower() in _PLACEHOLDER_VALUES)
        ):
            hits.append((key, value))
    return hits


@defect_class(
    "MANIFEST_PLACEHOLDER_METADATA",
    severity="low",
    fingerprint_basis="the manifest path alone: fixing one of several placeholders in a file does "
    "not turn the remaining defect into a new report",
    needs=frozenset({NEED_MANIFESTS}),
    template=IssueTemplate(
        summary=(
            "At revision `{revision}` the package manifest `{manifest_path}` carries placeholder "
            "metadata that is published with the package."
        ),
        steps="grep -n {patterns} {manifest_path}",
        expected=(
            "Package metadata names the real project: URLs that point to `{repository}` on "
            "GitHub, and an author or company that identifies the project."
        ),
        actual="{actual}",
    ),
)
def detect_manifest_placeholder_metadata(observation: Observation) -> list[DefectFinding]:
    findings = []
    revision = observation.source_revision
    for manifest in observation.manifests:
        hits = _placeholder_hits(manifest)
        if not hits:
            continue
        shown = hits[:6]
        patterns = " ".join(
            f"-e {shlex.quote(value)}"
            for value in dict.fromkeys(value for _, value in shown)
            if "\n" not in value and len(value) <= 200
        )
        actual = _bullets([f"`{_tick(key)}` is `{_tick(value)}`" for key, value in shown])
        findings.append(
            DefectFinding(
                defect_class="MANIFEST_PLACEHOLDER_METADATA",
                signature=f"placeholder metadata in {manifest.path}",
                statement=f"{PurePosixPath(manifest.path).name} contains placeholder metadata",
                claim=(
                    f"At revision {revision}, {observation.repository}'s {manifest.path} carries "
                    f"placeholder metadata ({', '.join(_tick(k) for k, _ in shown)})."
                ),
                fields={
                    "manifest_path": manifest.path,
                    "patterns": patterns or "-i placeholder",
                    "actual": actual,
                },
                evidence=tuple(
                    EvidenceEntry(path=manifest.path, detail=f"{k} = {v}") for k, v in shown
                ),
            )
        )
    return findings


_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_CONTENT_HINT = re.compile(r"`|https?://|\]\(|\binstall|\busage\b|\bimport\b", re.IGNORECASE)


def _placeholder_readme(text: str) -> bool:
    """A README a visitor can do nothing with: tiny, no code, link, install or usage hint, and
    only a few words beyond its headings. Conservative on purpose: a small README that shows a
    command or a link is never reported."""
    if len(text.encode("utf-8")) > PLACEHOLDER_README_MAX_BYTES or _CONTENT_HINT.search(text):
        return False
    body = " ".join(line for line in text.splitlines() if not _HEADING.match(line))
    return len(body.split()) <= PLACEHOLDER_README_MAX_WORDS


@defect_class(
    "README_MISSING_OR_PLACEHOLDER",
    severity="medium",
    fingerprint_basis="the state and the README path: 'missing', or 'placeholder' plus the path; "
    "a byte count in the title never enters the key",
    needs=frozenset({NEED_README}),
    template=IssueTemplate(
        summary="At revision `{revision}` {summary_tail}",
        steps="{steps}",
        expected=(
            "A README at the repository root that says what the project is, how to install it "
            "and how to use it."
        ),
        actual="{actual}",
    ),
)
def detect_readme_missing_or_placeholder(observation: Observation) -> list[DefectFinding]:
    tree = observation.tree_paths
    if not tree:
        return []
    revision = observation.source_revision
    readme = root_readme_path(tree)
    if readme is None:
        return [
            DefectFinding(
                defect_class="README_MISSING_OR_PLACEHOLDER",
                signature="README missing",
                statement="the repository has no README",
                claim=(
                    f"At revision {revision}, {observation.repository} has no README at its root."
                ),
                fields={
                    "summary_tail": "the repository has no README file at its root.",
                    "steps": _ls_tree(revision),
                    "actual": "The root listing has no README file.",
                },
                evidence=(
                    EvidenceEntry(
                        path=_ls_tree(revision), detail="no README among the root entries"
                    ),
                ),
            )
        ]
    text = observation.readme_text
    if text is None or not _placeholder_readme(text):
        return []
    size = len(text.encode("utf-8"))
    quoted = "\n".join(f"> {line}" for line in text.strip().splitlines())
    return [
        DefectFinding(
            defect_class="README_MISSING_OR_PLACEHOLDER",
            signature=f"README placeholder {readme}",
            statement=f"{readme} is a {size}-byte placeholder with no usable content",
            claim=(
                f"At revision {revision}, {observation.repository}'s {readme} is {size} bytes and "
                "gives a visitor no way to install or use the project."
            ),
            fields={
                "summary_tail": (
                    f"`{readme}` is {size} bytes and says nothing a visitor can act on."
                ),
                "steps": f"git show {revision}:{readme}",
                "actual": f"`{readme}` is {size} bytes and reads:\n\n{quoted}",
            },
            evidence=(EvidenceEntry(path=readme, detail=f"{size} bytes; no install or usage"),),
        )
    ]


# Classes whose evidence only a measured build, example run or source parse can give. Each is
# carried by the existing check's handoff and redetector.
declare_mapped(
    "SOURCE_UNPARSEABLE",
    severity="high",
    redetector="NOT_PROCESSABLE",
    fingerprint_basis="the NOT_PROCESSABLE handoff's own: repository, check id and the paths that "
    "fail to parse",
)
declare_mapped(
    "BUILD_OR_TESTS_FAIL",
    severity="high",
    redetector="BC-02",
    fingerprint_basis="the BC-02 toolchain handoff's own: repository, check id and the failing "
    "build or test command",
)
declare_mapped(
    "EXAMPLE_FAILS",
    severity="medium",
    redetector="BC-03",
    fingerprint_basis="the BC-03 handoff's own: repository, check id and the failing example",
)
declare_mapped(
    "INSTALL_FAILS",
    severity="high",
    redetector="BC-02",
    fingerprint_basis="the BC-02 handoff's own: repository, check id and the install route",
)

if set(REGISTRY) != set(DEFECT_CLASSES):  # pragma: no cover - guarded by a test as well
    raise RuntimeError("the defect-class registry and model.DEFECT_CLASSES disagree")


def detect_all(observation: Observation) -> list[DefectFinding]:
    """Every finding of every registered detector, ordered by severity, class id and signature:
    the same observation always gives the same list."""
    findings: list[DefectFinding] = []
    specs = sorted(REGISTRY.values(), key=lambda s: (_SEVERITY_RANK[s.severity], s.id))
    for spec in specs:
        if spec.detector is not None:
            findings.extend(sorted(spec.detector(observation), key=lambda f: f.signature))
    return findings


# --- the shared redetector -----------------------------------------------------------------------


def _redetect_class(
    handoff: Handoff, reads: _redetect.RedetectionReads
) -> _redetect.RedetectionResult:
    """Re-read the tree (and the few files the class needs) at the repository's current head,
    rebuild the observation, run the class's detector and ask whether it still reports the
    handoff's own fingerprint. Inconclusive, never guessed, when the head, the tree or a needed
    file cannot be read, or when the listing is truncated (absence cannot be proven from it)."""
    spec = REGISTRY[handoff.triggering_check.id]
    head, drifted, error = _redetect._read_head(handoff, reads)
    if head is None or spec.detector is None:
        return _redetect._result(
            handoff,
            revision=None,
            drifted=False,
            still_fires=None,
            note=f"inconclusive: cannot resolve current default-branch revision: {error}",
        )
    tree = reads.fetch_tree(handoff.repository, head)
    if tree.error is not None or tree.truncated or not tree.paths:
        return _redetect._result(
            handoff,
            revision=head,
            drifted=drifted,
            still_fires=None,
            note="inconclusive: the file listing could not be read completely "
            f"({tree.error or 'truncated or empty'})",
        )

    def read(path: str) -> str | None:
        got = reads.fetch_file(handoff.repository, head, path)
        return got.content if got.found else None

    hints = tuple(e.path for e in handoff.evidence)
    observation = build_observation(
        handoff.repository,
        head,
        tuple(tree.paths),
        read,
        needs=spec.needs,
        manifest_hints=hints,
    )
    matching = [
        f
        for f in spec.detector(observation)
        if fingerprint(handoff.repository, spec.id, f.signature) == handoff.defect_fingerprint
    ]
    if matching:
        return _redetect._result(
            handoff,
            revision=head,
            drifted=drifted,
            still_fires=True,
            note=f"still fires: {matching[0].statement}",
            fresh=matching[0].evidence,
        )
    if observation.unreadable:
        return _redetect._result(
            handoff,
            revision=head,
            drifted=drifted,
            still_fires=None,
            note="inconclusive: could not read " + ", ".join(observation.unreadable[:3]),
        )
    return _redetect._result(
        handoff,
        revision=head,
        drifted=drifted,
        still_fires=False,
        note=f"no longer fires: the detector for {spec.id} reports nothing at {head[:12]}",
        fresh=(
            EvidenceEntry(
                path=_ls_tree(head), detail=f"{len(observation.root_entries)} root entries"
            ),
        ),
    )
