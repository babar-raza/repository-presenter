"""Which package a handoff's evidence says a registry does not have.

A `BC-02` handoff about a missing distribution records the registry URL it probed (`{path: <url>,
detail: "HTTP 404 on ..."}`). The re-detection pass replays exactly that read, so it needs the
`(ecosystem, name)` the URL addresses, whichever registry's URL shape the original reproduction
used. The ecosystem names are the keys `core/package_registry.py` resolves an observer by.

Parsing is pure and offline (no read happens here); a URL no registry owns, or one this module
cannot name a single package from, yields ``None`` and is never guessed at. An evidence entry whose
detail says it is a *control* (a registry read that is expected to succeed, recorded to prove the
probe itself works - the Imaging-.NET handoff's `aspose.imaging` entry) names no defective package.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from repository_presenter.components.issues.model import EvidenceEntry


@dataclass(frozen=True)
class RegistryIdentity:
    """One package on one registry; ``ecosystem`` is a `core/package_registry.py` observer key
    and ``name`` the coordinate that observer takes (a Maven coordinate is ``group:artifact``)."""

    ecosystem: str
    name: str


_Parser = Callable[[list[str]], str | None]


def _pypi(segments: list[str]) -> str | None:
    # /pypi/<name>/json, /pypi/<name>/<version>/json, /project/<name>/
    if len(segments) >= 2 and segments[0] in {"pypi", "project"}:
        return segments[1]
    return None


def _npm_registry(segments: list[str]) -> str | None:
    # registry.npmjs.org/<name>; a scope is its own leading segment (see `registry_identity`)
    if not segments or segments[0].startswith("-"):
        return None
    if segments[0].startswith("@"):
        return f"{segments[0]}/{segments[1]}" if len(segments) >= 2 else None
    return segments[0]


def _npm_site(segments: list[str]) -> str | None:
    # www.npmjs.com/package/<name> or /package/@scope/name
    if len(segments) >= 2 and segments[0] == "package":
        return _npm_registry(segments[1:])
    return None


def _nuget_api(segments: list[str]) -> str | None:
    # api.nuget.org/v3-flatcontainer/<id>/..., /v3/registration*/<id>/...
    if len(segments) >= 2 and segments[0] == "v3-flatcontainer":
        return segments[1].lower()
    if len(segments) >= 3 and segments[0] == "v3" and segments[1].startswith("registration"):
        return segments[2].lower()
    return None


def _nuget_site(segments: list[str]) -> str | None:
    # www.nuget.org/packages/<id>[/<version>]
    if len(segments) >= 2 and segments[0] == "packages":
        return segments[1].lower()
    return None


def _maven_central(segments: list[str]) -> str | None:
    # repo1.maven.org/maven2/<group path>/<artifact>/maven-metadata.xml - the one form whose
    # artifact is unambiguous (a versioned file path cannot say where the group path ends)
    if len(segments) >= 4 and segments[0] == "maven2" and segments[-1] == "maven-metadata.xml":
        return f"{'.'.join(segments[1:-2])}:{segments[-2]}"
    return None


def _maven_site(segments: list[str]) -> str | None:
    # central.sonatype.com/artifact/<group>/<artifact>[/<version>]
    if len(segments) >= 3 and segments[0] == "artifact":
        return f"{segments[1]}:{segments[2]}"
    return None


def _crates(segments: list[str]) -> str | None:
    # crates.io/api/v1/crates/<name>[/...] or the site's crates.io/crates/<name>
    if len(segments) >= 4 and segments[:3] == ["api", "v1", "crates"]:
        return segments[3]
    if len(segments) >= 2 and segments[0] == "crates":
        return segments[1]
    return None


_GO_PROXY_SUFFIXES = {"@v", "@latest"}


def _unescape_go(path: str) -> str:
    """The Go proxy's case-encoding in reverse: ``!a`` is ``A``."""
    return re.sub(r"!([a-z])", lambda m: m.group(1).upper(), path)


def _go_proxy(segments: list[str]) -> str | None:
    # proxy.golang.org/<escaped module>/@v/list | /@v/<version>.info | /@latest
    for index, segment in enumerate(segments):
        if segment in _GO_PROXY_SUFFIXES:
            module = "/".join(segments[:index])
            return _unescape_go(module) if module else None
    return None


def _go_site(segments: list[str]) -> str | None:
    # pkg.go.dev/<module>[@<version>]
    if not segments:
        return None
    module = "/".join(segments).split("@", 1)[0]
    return module or None


# host -> (observer key, how the path names the package). A host appears once, so adding a
# registry is one row; no URL is ever matched by a loose substring.
_HOSTS: dict[str, tuple[str, _Parser]] = {
    "pypi.org": ("python", _pypi),
    "registry.npmjs.org": ("typescript", _npm_registry),
    "www.npmjs.com": ("typescript", _npm_site),
    "api.nuget.org": ("net", _nuget_api),
    "www.nuget.org": ("net", _nuget_site),
    "repo1.maven.org": ("java", _maven_central),
    "central.sonatype.com": ("java", _maven_site),
    "crates.io": ("rust", _crates),
    "proxy.golang.org": ("go", _go_proxy),
    "pkg.go.dev": ("go", _go_site),
}


_CONTROL = re.compile(r"^\s*control\b", re.IGNORECASE)


def registry_identity(url: str) -> RegistryIdentity | None:
    """The package a registry URL addresses, or ``None`` when no registry owns the URL or its path
    names no single package."""
    parts = urlsplit(url.strip())
    if parts.scheme != "https" or parts.hostname is None:
        return None
    entry = _HOSTS.get(parts.hostname.lower())
    if entry is None:
        return None
    ecosystem, parse = entry
    # Decode once, then split: a scoped npm name arrives as ``@scope%2fname`` (one segment) or
    # ``@scope/name`` (two), and both must name the same package.
    segments = [unquote(s) for s in parts.path.split("/") if s]
    if (
        ecosystem == "typescript"
        and segments
        and "/" in segments[0]
        and segments[0].startswith("@")
    ):
        segments = [*segments[0].split("/", 1), *segments[1:]]
    name = parse(segments)
    return RegistryIdentity(ecosystem, name) if name else None


def registry_identities(evidence: Iterable[EvidenceEntry]) -> frozenset[RegistryIdentity]:
    """Every package the evidence's registry URLs address, controls excluded."""
    found: set[RegistryIdentity] = set()
    for entry in evidence:
        if entry.detail is not None and _CONTROL.match(entry.detail):
            continue
        identity = registry_identity(entry.path)
        if identity is not None:
            found.add(identity)
    return frozenset(found)
